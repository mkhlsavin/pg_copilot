"""
Statistics Router.

Provides endpoints for system statistics and metrics.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User, UserRole
from src.api.database.repositories.stats_repo import StatsRepository
from src.api.dependencies import get_current_active_user
from src.api.models.common import MetricsResponse

logger = logging.getLogger("api.routers.stats")
router = APIRouter()


# Response Models
class ScenarioStats(BaseModel):
    """Scenario statistics response."""
    scenarios: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Scenario usage by period",
    )
    total_queries: int = Field(..., description="Total queries processed")
    period: str = Field(..., description="Statistics period")


class UserStats(BaseModel):
    """User statistics response."""
    total_users: int = Field(..., description="Total user accounts")
    active_users_24h: int = Field(..., description="Users active in last 24h")
    active_users_7d: int = Field(..., description="Users active in last 7 days")
    new_users_7d: int = Field(..., description="New users in last 7 days")


class PerformanceStats(BaseModel):
    """Performance statistics response."""
    avg_response_time_ms: float = Field(..., description="Average response time")
    p50_response_time_ms: float = Field(..., description="Median response time")
    p95_response_time_ms: float = Field(..., description="95th percentile response time")
    p99_response_time_ms: float = Field(..., description="99th percentile response time")
    requests_per_minute: float = Field(..., description="Request rate")
    error_rate: float = Field(..., description="Error rate percentage")


# Endpoints
@router.get(
    "",
    response_model=MetricsResponse,
    summary="Get system statistics",
    description="Get system-wide statistics and metrics.",
)
async def get_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get system statistics.

    Returns:
        System metrics and statistics
    """
    stats_repo = StatsRepository(db)
    metrics = await stats_repo.get_system_metrics()

    logger.debug(f"Stats requested by user {current_user.username}")

    return MetricsResponse(
        total_requests=metrics["total_requests"],
        active_sessions=metrics["active_sessions"],
        active_jobs=metrics["active_jobs"],
        cache_hit_rate=metrics["cache_hit_rate"],
        avg_response_time_ms=metrics["avg_response_time_ms"],
        scenarios_usage=metrics["scenarios_usage"],
    )


@router.get(
    "/scenarios",
    response_model=ScenarioStats,
    summary="Get scenario statistics",
    description="Get usage statistics per scenario.",
)
async def get_scenario_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioStats:
    """
    Get scenario usage statistics.

    Returns:
        Per-scenario usage metrics
    """
    stats_repo = StatsRepository(db)
    stats = await stats_repo.get_scenario_statistics()

    logger.debug(f"Scenario stats requested by user {current_user.username}")

    return ScenarioStats(
        scenarios=stats["scenarios"],
        total_queries=stats["total_queries"],
        period=stats["period"],
    )


@router.get(
    "/users",
    response_model=UserStats,
    summary="Get user statistics",
    description="Get user activity statistics (admin only).",
)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserStats:
    """
    Get user statistics.

    Requires admin role.

    Returns:
        User activity metrics
    """
    # Admin-only endpoint
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to access user statistics",
        )

    stats_repo = StatsRepository(db)
    stats = await stats_repo.get_user_statistics()

    logger.info(f"User stats requested by admin {current_user.username}")

    return UserStats(
        total_users=stats["total_users"],
        active_users_24h=stats["active_users_24h"],
        active_users_7d=stats["active_users_7d"],
        new_users_7d=stats["new_users_7d"],
    )


@router.get(
    "/performance",
    response_model=PerformanceStats,
    summary="Get performance statistics",
    description="Get system performance metrics.",
)
async def get_performance_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PerformanceStats:
    """
    Get performance statistics.

    Note: Full implementation requires timing middleware integration.
    Currently returns basic metrics.

    Returns:
        Performance metrics
    """
    stats_repo = StatsRepository(db)

    # Calculate basic metrics
    # Full implementation would require:
    # 1. Request timing middleware to track response times
    # 2. Storing timing data in database or metrics store
    # 3. Calculating percentiles from stored data

    # For now, we can derive some metrics from available data
    total_turns = await stats_repo.count_total_turns()
    turns_24h = await stats_repo.count_turns_period(days=1)

    # Approximate requests per minute (from 24h data)
    requests_per_minute = turns_24h / (24 * 60) if turns_24h > 0 else 0.0

    logger.debug(f"Performance stats requested by user {current_user.username}")

    return PerformanceStats(
        avg_response_time_ms=0.0,  # Requires timing middleware
        p50_response_time_ms=0.0,  # Requires timing middleware
        p95_response_time_ms=0.0,  # Requires timing middleware
        p99_response_time_ms=0.0,  # Requires timing middleware
        requests_per_minute=requests_per_minute,
        error_rate=0.0,  # Requires error tracking middleware
    )
