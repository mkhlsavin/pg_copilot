"""
Health Check Router.

Provides health check endpoints for monitoring and Kubernetes probes.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.api import __version__
from src.api.database.connection import check_db_connection, DatabaseHealthCheck
from src.api.models.common import HealthStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Server start time (set during module import)
_module_start_time = time.time()


async def check_llm_health(request: Request) -> Dict[str, Any]:
    """
    Check LLM provider health.

    Returns:
        Dict with status and provider details.
    """
    try:
        # Check if LLM provider is configured in app state
        if not hasattr(request.app.state, 'llm_provider') or request.app.state.llm_provider is None:
            return {"status": "unavailable", "provider": "not_configured"}

        if not getattr(request.app.state, 'llm_available', False):
            return {"status": "unavailable", "provider": "not_available"}

        provider = request.app.state.llm_provider
        provider_name = provider.__class__.__name__

        # Check if provider has health check method
        if hasattr(provider, 'is_available') and callable(provider.is_available):
            if provider.is_available():
                return {
                    "status": "healthy",
                    "provider": provider_name,
                    "model": getattr(provider, 'model_name', 'unknown'),
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": provider_name,
                    "error": "Provider reports not available",
                }

        # Default: assume healthy if provider exists
        return {
            "status": "healthy",
            "provider": provider_name,
        }
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_joern_health(request: Request) -> Dict[str, Any]:
    """
    Check Joern server health.

    Returns:
        Dict with status and server details.
    """
    try:
        # Check if Joern config is available in app state
        if not hasattr(request.app.state, 'joern_config') or request.app.state.joern_config is None:
            return {"status": "unavailable", "server": "not_configured"}

        joern_config = request.app.state.joern_config

        # Get endpoint from config
        host = getattr(joern_config, 'host', 'localhost')
        port = getattr(joern_config, 'port', 8080)
        endpoint = getattr(joern_config, 'endpoint', f"{host}:{port}")

        # Ensure endpoint has protocol
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"http://{endpoint}"

        # Try to connect to Joern server
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(endpoint)

                if response.status_code in (200, 404):
                    # Server is responding (404 is OK - means server is up but no root handler)
                    request.app.state.joern_available = True
                    return {
                        "status": "healthy",
                        "server": endpoint,
                        "http_status": response.status_code,
                    }
                else:
                    return {
                        "status": "degraded",
                        "server": endpoint,
                        "http_status": response.status_code,
                    }
            except httpx.ConnectError:
                request.app.state.joern_available = False
                return {
                    "status": "unhealthy",
                    "server": endpoint,
                    "error": "Connection refused",
                }
            except httpx.TimeoutException:
                request.app.state.joern_available = False
                return {
                    "status": "unhealthy",
                    "server": endpoint,
                    "error": "Connection timeout",
                }
    except Exception as e:
        logger.warning(f"Joern health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get(
    "",
    response_model=HealthStatus,
    summary="Full health check",
    description="Returns detailed health status of all system components.",
)
async def health_check(request: Request) -> HealthStatus:
    """
    Perform comprehensive health check.

    Returns status of all system components including database, LLM, and Joern.
    """
    components: Dict[str, Dict[str, Any]] = {}

    # Check database
    db_health = await DatabaseHealthCheck.check()
    components["database"] = db_health

    # Check LLM provider
    components["llm"] = await check_llm_health(request)

    # Check Joern server
    components["joern"] = await check_joern_health(request)

    # Determine overall status
    # Consider "unavailable" as not affecting overall health (optional components)
    critical_statuses = [
        c.get("status") for c in components.values()
        if c.get("status") != "unavailable"
    ]
    all_healthy = all(s == "healthy" for s in critical_statuses) if critical_statuses else True
    overall_status = "healthy" if all_healthy else "degraded"

    # Check if any critical component is down
    if components.get("database", {}).get("status") == "unhealthy":
        overall_status = "unhealthy"

    uptime = time.time() - _module_start_time

    return HealthStatus(
        status=overall_status,
        version=__version__,
        uptime_seconds=uptime,
        timestamp=datetime.utcnow(),
        components=components,
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint. Returns 200 if service is running.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes.

    Simply returns OK if the service is running.
    """
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint. Returns 200 if service is ready to accept traffic.",
)
async def readiness_probe() -> JSONResponse:
    """
    Readiness probe for Kubernetes.

    Checks if the service is ready to accept traffic (database connected, etc.).
    """
    # Check database connection
    db_ok = await check_db_connection()

    if db_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "Database connection failed",
            },
        )


@router.get(
    "/version",
    summary="Get version",
    description="Returns API version information.",
)
async def get_version() -> Dict[str, str]:
    """Get API version information."""
    return {
        "version": __version__,
        "name": "CodeGraph API",
    }
