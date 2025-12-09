"""
Statistics Repository.

Provides data access for statistics and metrics collection.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import (
    User,
    Session,
    DialogueTurn,
    BackgroundJob,
    JobStatus,
)


class StatsRepository:
    """
    Statistics repository for collecting metrics from the database.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Database session
        """
        self.db = session

    # User Statistics

    async def count_users(self, active_only: bool = True) -> int:
        """Count total users."""
        query = select(func.count(User.id))
        if active_only:
            query = query.where(User.is_active == True)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_active_users(self, hours: int = 24) -> int:
        """Count users active in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(func.count(func.distinct(Session.user_id))).where(
            Session.updated_at >= cutoff
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_new_users(self, days: int = 7) -> int:
        """Count users created in the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = select(func.count(User.id)).where(User.created_at >= cutoff)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # Session Statistics

    async def count_sessions(self) -> int:
        """Count total sessions."""
        query = select(func.count(Session.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_active_sessions(self, hours: int = 1) -> int:
        """Count sessions active in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(func.count(Session.id)).where(Session.updated_at >= cutoff)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # Job Statistics

    async def count_jobs_by_status(self) -> Dict[str, int]:
        """Count jobs grouped by status."""
        query = select(
            BackgroundJob.status,
            func.count(BackgroundJob.id).label("count"),
        ).group_by(BackgroundJob.status)

        result = await self.db.execute(query)
        rows = result.all()

        return {row.status.value: row.count for row in rows}

    async def count_active_jobs(self) -> int:
        """Count currently running jobs."""
        query = select(func.count(BackgroundJob.id)).where(
            BackgroundJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    # Scenario Statistics

    async def get_scenario_usage(self) -> Dict[str, int]:
        """Get scenario usage counts from dialogue turns."""
        query = (
            select(
                DialogueTurn.scenario_id,
                func.count(DialogueTurn.id).label("count"),
            )
            .where(DialogueTurn.scenario_id.isnot(None))
            .group_by(DialogueTurn.scenario_id)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return {row.scenario_id: row.count for row in rows}

    async def get_scenario_usage_period(
        self,
        days: int = 30,
    ) -> Dict[str, int]:
        """Get scenario usage counts for a period."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                DialogueTurn.scenario_id,
                func.count(DialogueTurn.id).label("count"),
            )
            .where(
                DialogueTurn.scenario_id.isnot(None),
                DialogueTurn.timestamp >= cutoff,
            )
            .group_by(DialogueTurn.scenario_id)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return {row.scenario_id: row.count for row in rows}

    # Dialogue Statistics

    async def count_total_turns(self) -> int:
        """Count total dialogue turns (as proxy for requests)."""
        query = select(func.count(DialogueTurn.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_turns_period(self, days: int = 1) -> int:
        """Count turns in the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = select(func.count(DialogueTurn.id)).where(
            DialogueTurn.timestamp >= cutoff
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    # Combined Metrics

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get combined system metrics."""
        total_requests = await self.count_total_turns()
        active_sessions = await self.count_active_sessions(hours=1)
        active_jobs = await self.count_active_jobs()
        scenarios_usage = await self.get_scenario_usage()

        return {
            "total_requests": total_requests,
            "active_sessions": active_sessions,
            "active_jobs": active_jobs,
            "cache_hit_rate": 0.0,  # Would need cache instrumentation
            "avg_response_time_ms": 0.0,  # Would need timing middleware
            "scenarios_usage": scenarios_usage,
        }

    async def get_user_statistics(self) -> Dict[str, int]:
        """Get user-related statistics."""
        total = await self.count_users()
        active_24h = await self.count_active_users(hours=24)
        active_7d = await self.count_active_users(hours=168)  # 7 * 24
        new_7d = await self.count_new_users(days=7)

        return {
            "total_users": total,
            "active_users_24h": active_24h,
            "active_users_7d": active_7d,
            "new_users_7d": new_7d,
        }

    async def get_scenario_statistics(self) -> Dict[str, Any]:
        """Get scenario-related statistics."""
        all_time = await self.get_scenario_usage()
        last_30d = await self.get_scenario_usage_period(days=30)
        last_7d = await self.get_scenario_usage_period(days=7)
        total = await self.count_total_turns()

        return {
            "scenarios": {
                "all_time": all_time,
                "last_30_days": last_30d,
                "last_7_days": last_7d,
            },
            "total_queries": total,
            "period": "all_time",
        }
