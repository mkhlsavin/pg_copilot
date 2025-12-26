"""
Health check router.

Provides health endpoint for container orchestration.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter()


@router.get(
    "",
    summary="Health Check",
    description="Returns service health status",
    response_model=Dict[str, Any],
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Health status with service information
    """
    settings = get_settings()

    return {
        "status": "healthy",
        "service": "codegraph-leads",
        "version": "1.0.0",
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "notifications": {
            "email": settings.email_enabled,
            "telegram": settings.telegram_enabled,
        },
    }
