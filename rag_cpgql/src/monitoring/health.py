"""
Health Check Endpoints for CodeGraph System

Provides:
- Health check endpoint (/health)
- Prometheus metrics endpoint (/metrics)
- Statistics endpoint (/stats)
- Liveness and readiness probes

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Try importing FastAPI and prometheus_client
try:
    from fastapi import FastAPI, Response, HTTPException
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"


# ============================================================================
# HEALTH CHECK DATA STRUCTURES
# ============================================================================

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'latency_ms': round(self.latency_ms, 2),
            'message': self.message,
            'details': self.details,
        }


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0
    version: str = "2.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp,
            'uptime_seconds': round(self.uptime_seconds, 2),
            'version': self.version,
            'components': [c.to_dict() for c in self.components],
        }


# ============================================================================
# HEALTH CHECKER
# ============================================================================

class HealthChecker:
    """
    Health checker for CodeGraph system components.

    Performs health checks on:
    - DuckDB CPG database
    - LLM provider
    - Vector store (optional)
    - Cache (optional)

    Usage:
        checker = HealthChecker()
        checker.register_check("database", check_database_health)
        health = checker.check_health()
    """

    def __init__(self):
        """Initialize health checker."""
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._start_time = time.time()
        self._last_check: Optional[SystemHealth] = None
        self._check_cache_ttl = 5.0  # Cache health check results for 5 seconds

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("database", self._check_database)
        self.register_check("llm", self._check_llm)

    def register_check(self, name: str, check_fn: Callable[[], ComponentHealth]):
        """
        Register a health check function.

        Args:
            name: Name of the component
            check_fn: Function that returns ComponentHealth
        """
        self._checks[name] = check_fn
        logger.debug(f"Registered health check: {name}")

    def unregister_check(self, name: str):
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]

    def check_health(self, use_cache: bool = True) -> SystemHealth:
        """
        Perform all health checks.

        Args:
            use_cache: Whether to use cached results

        Returns:
            SystemHealth with all component statuses
        """
        # Check cache
        if use_cache and self._last_check:
            cache_age = time.time() - self._last_check.timestamp
            if cache_age < self._check_cache_ttl:
                return self._last_check

        # Run all checks
        components = []
        overall_status = HealthStatus.HEALTHY

        for name, check_fn in self._checks.items():
            try:
                component = check_fn()
                components.append(component)

                # Update overall status
                if component.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif component.status == HealthStatus.DEGRADED:
                    if overall_status != HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.DEGRADED

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}"
                ))
                overall_status = HealthStatus.UNHEALTHY

        # Build result
        health = SystemHealth(
            status=overall_status,
            components=components,
            uptime_seconds=time.time() - self._start_time,
        )

        # Cache result
        self._last_check = health

        return health

    def check_liveness(self) -> bool:
        """
        Liveness probe - is the service alive?

        Returns True if the service is running, even if unhealthy.
        """
        return True

    def check_readiness(self) -> bool:
        """
        Readiness probe - is the service ready to accept traffic?

        Returns True only if all critical components are healthy.
        """
        health = self.check_health()
        return health.status != HealthStatus.UNHEALTHY

    # ========================================================================
    # DEFAULT CHECK IMPLEMENTATIONS
    # ========================================================================

    def _check_database(self) -> ComponentHealth:
        """Check DuckDB CPG database health."""
        start_time = time.time()

        try:
            from src.services.cpg_query_service import CPGQueryService

            cpg = CPGQueryService()
            stats = cpg.get_database_stats()
            cpg.close()

            latency = (time.time() - start_time) * 1000

            # Check for minimum data
            method_count = stats.get('method_count', 0)
            if method_count == 0:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Database empty or not imported",
                    details=stats
                )

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=f"Connected, {method_count} methods",
                details=stats
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Connection failed: {str(e)}"
            )

    def _check_llm(self) -> ComponentHealth:
        """Check LLM provider health."""
        start_time = time.time()

        try:
            from src.llm.llm_interface_compat import LLMInterface

            llm = LLMInterface()

            # Quick availability check
            if not llm.is_available():
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=(time.time() - start_time) * 1000,
                    message="LLM provider not available"
                )

            # Test generation
            response = llm.generate_simple("Say 'OK'", max_tokens=10)
            latency = (time.time() - start_time) * 1000

            if response and len(response) > 0:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="LLM responding normally",
                    details={'provider': llm.provider_name if hasattr(llm, 'provider_name') else 'unknown'}
                )
            else:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="LLM returned empty response"
                )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="llm",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"LLM check failed: {str(e)}"
            )


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_health_app(
    health_checker: Optional[HealthChecker] = None,
    title: str = "CodeGraph Health API",
    version: str = "2.0.0"
) -> Optional['FastAPI']:
    """
    Create FastAPI application with health check endpoints.

    Args:
        health_checker: Custom health checker instance
        title: API title
        version: API version

    Returns:
        FastAPI application or None if FastAPI not available
    """
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available, health endpoints disabled")
        return None

    app = FastAPI(title=title, version=version)
    checker = health_checker or HealthChecker()

    @app.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns overall system health and component statuses.
        """
        health = checker.check_health()
        status_code = 200 if health.status != HealthStatus.UNHEALTHY else 503

        return JSONResponse(
            content=health.to_dict(),
            status_code=status_code
        )

    @app.get("/health/live")
    async def liveness_probe():
        """Kubernetes liveness probe."""
        if checker.check_liveness():
            return {"status": "alive"}
        raise HTTPException(status_code=503, detail="Service not alive")

    @app.get("/health/ready")
    async def readiness_probe():
        """Kubernetes readiness probe."""
        if checker.check_readiness():
            return {"status": "ready"}
        raise HTTPException(status_code=503, detail="Service not ready")

    @app.get("/metrics")
    async def prometheus_metrics():
        """
        Prometheus metrics endpoint.

        Returns metrics in Prometheus exposition format.
        """
        if PROMETHEUS_AVAILABLE and generate_latest:
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )
        else:
            # Return basic metrics as JSON
            from src.monitoring.metrics import get_metrics_collector
            collector = get_metrics_collector()
            summary = collector.get_summary()

            return JSONResponse(content=summary.to_dict())

    @app.get("/stats")
    async def statistics():
        """
        Get current system statistics.

        Returns detailed statistics including:
        - Metrics summary
        - Per-scenario stats
        - Cache statistics
        """
        from src.monitoring.metrics import get_metrics_collector

        collector = get_metrics_collector()

        return {
            'summary': collector.get_summary().to_dict(),
            'scenarios': collector.get_scenario_stats(),
            'cache': collector.get_cache_stats(),
            'uptime_seconds': collector.get_uptime_seconds(),
        }

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": title,
            "version": version,
            "endpoints": {
                "/health": "System health check",
                "/health/live": "Liveness probe",
                "/health/ready": "Readiness probe",
                "/metrics": "Prometheus metrics",
                "/stats": "System statistics",
            }
        }

    logger.info(f"Health API created: {title} v{version}")
    return app


# ============================================================================
# STANDALONE HEALTH CHECK FUNCTIONS
# ============================================================================

def check_database_connection() -> bool:
    """
    Quick database connection check.

    Returns:
        True if database is connected
    """
    try:
        from src.services.cpg_query_service import CPGQueryService
        cpg = CPGQueryService()
        cpg.execute_query("SELECT 1")
        cpg.close()
        return True
    except Exception:
        return False


def check_llm_availability() -> bool:
    """
    Quick LLM availability check.

    Returns:
        True if LLM is available
    """
    try:
        from src.llm.llm_interface_compat import LLMInterface
        llm = LLMInterface()
        return llm.is_available()
    except Exception:
        return False


def check_vector_store() -> bool:
    """
    Quick vector store check.

    Returns:
        True if vector store is available (or not configured)
    """
    # Vector store is optional, return True by default
    return True


def get_system_health_summary() -> Dict[str, Any]:
    """
    Get quick system health summary.

    Returns:
        Dictionary with health status
    """
    checker = HealthChecker()
    health = checker.check_health()
    return health.to_dict()


# ============================================================================
# CLI HEALTH CHECK
# ============================================================================

def run_health_check_cli():
    """Run health check from command line."""
    import sys

    print("CodeGraph Health Check")
    print("=" * 50)

    checker = HealthChecker()
    health = checker.check_health(use_cache=False)

    # Print overall status
    status_emoji = {
        HealthStatus.HEALTHY: "OK",
        HealthStatus.DEGRADED: "WARN",
        HealthStatus.UNHEALTHY: "FAIL",
    }

    print(f"\nOverall Status: [{status_emoji[health.status]}] {health.status.value.upper()}")
    print(f"Uptime: {health.uptime_seconds:.2f}s")
    print(f"Version: {health.version}")

    # Print component statuses
    print("\nComponents:")
    print("-" * 50)

    for component in health.components:
        emoji = status_emoji[component.status]
        print(f"  [{emoji}] {component.name}: {component.status.value}")
        print(f"       Latency: {component.latency_ms:.2f}ms")
        if component.message:
            print(f"       Message: {component.message}")

    # Exit code based on health
    if health.status == HealthStatus.UNHEALTHY:
        sys.exit(1)
    elif health.status == HealthStatus.DEGRADED:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_health_check_cli()
