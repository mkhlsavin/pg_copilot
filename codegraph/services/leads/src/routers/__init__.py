"""API routers for Leads service."""

from src.routers.health import router as health_router
from src.routers.leads import router as leads_router

__all__ = ["leads_router", "health_router"]
