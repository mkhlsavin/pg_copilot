"""
Health Check Router.

Provides health check endpoints for monitoring and Kubernetes probes.
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.api import __version__
from src.api.database.connection import check_db_connection, DatabaseHealthCheck
from src.api.models.common import HealthStatus

router = APIRouter()

# Server start time (set during module import)
_module_start_time = time.time()


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

    # TODO: Check LLM provider
    components["llm"] = {
        "status": "healthy",
        "provider": "not_configured",
    }

    # TODO: Check Joern server
    components["joern"] = {
        "status": "healthy",
        "server": "not_configured",
    }

    # Determine overall status
    all_healthy = all(
        c.get("status") == "healthy" for c in components.values()
    )
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
        "name": "RAG-CPGQL API",
    }
