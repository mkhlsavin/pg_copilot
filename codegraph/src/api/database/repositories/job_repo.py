"""
Background Job Repository.

Provides data access for background job operations.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import BackgroundJob, JobStatus, JobType


class JobRepository:
    """
    Background job repository for database operations.

    Handles CRUD operations for background jobs.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        job_type: JobType,
        params: Optional[Dict[str, Any]] = None,
    ) -> BackgroundJob:
        """
        Create a new background job.

        Args:
            user_id: Owner user ID
            job_type: Type of job
            params: Job parameters

        Returns:
            Created job
        """
        job = BackgroundJob(
            user_id=user_id,
            job_type=job_type,
            params=params or {},
        )

        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        return job

    async def get_by_id(self, job_id: UUID) -> Optional[BackgroundJob]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job or None
        """
        result = await self.session.execute(
            select(BackgroundJob).where(BackgroundJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BackgroundJob]:
        """
        Get jobs for a user.

        Args:
            user_id: User ID
            status: Filter by status
            job_type: Filter by type
            limit: Maximum jobs
            offset: Skip count

        Returns:
            List of jobs
        """
        query = select(BackgroundJob).where(BackgroundJob.user_id == user_id)

        if status:
            query = query.where(BackgroundJob.status == status)

        if job_type:
            query = query.where(BackgroundJob.job_type == job_type)

        query = (
            query.order_by(BackgroundJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[BackgroundJob]:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            result: Job result (for completed jobs)
            error: Error message (for failed jobs)

        Returns:
            Updated job or None
        """
        updates = {
            "status": status,
            "updated_at": datetime.now(UTC),
        }

        if progress is not None:
            updates["progress"] = progress

        if result is not None:
            updates["result"] = result

        if error is not None:
            updates["error"] = error

        await self.session.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(**updates)
        )

        return await self.get_by_id(job_id)

    async def update_progress(
        self,
        job_id: UUID,
        progress: int,
    ) -> None:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        await self.session.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(progress=progress, updated_at=datetime.now(UTC))
        )

    async def start(self, job_id: UUID) -> Optional[BackgroundJob]:
        """
        Mark job as running.

        Args:
            job_id: Job ID

        Returns:
            Updated job or None
        """
        return await self.update_status(job_id, JobStatus.RUNNING, progress=0)

    async def complete(
        self,
        job_id: UUID,
        result: Dict[str, Any],
    ) -> Optional[BackgroundJob]:
        """
        Mark job as completed.

        Args:
            job_id: Job ID
            result: Job result

        Returns:
            Updated job or None
        """
        return await self.update_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100,
            result=result,
        )

    async def fail(
        self,
        job_id: UUID,
        error: str,
    ) -> Optional[BackgroundJob]:
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error: Error message

        Returns:
            Updated job or None
        """
        return await self.update_status(
            job_id,
            JobStatus.FAILED,
            error=error,
        )

    async def cancel(self, job_id: UUID) -> Optional[BackgroundJob]:
        """
        Cancel a pending or running job.

        Args:
            job_id: Job ID

        Returns:
            Updated job or None
        """
        await self.session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                BackgroundJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
            )
            .values(status=JobStatus.CANCELLED, updated_at=datetime.now(UTC))
        )
        return await self.get_by_id(job_id)

    async def delete(self, job_id: UUID) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job ID

        Returns:
            True if deleted
        """
        result = await self.session.execute(
            delete(BackgroundJob).where(BackgroundJob.id == job_id)
        )
        return result.rowcount > 0

    async def delete_old_jobs(
        self,
        older_than: datetime,
        statuses: Optional[List[JobStatus]] = None,
    ) -> int:
        """
        Delete old jobs.

        Args:
            older_than: Delete jobs created before this time
            statuses: Only delete jobs with these statuses

        Returns:
            Number of deleted jobs
        """
        query = delete(BackgroundJob).where(
            BackgroundJob.created_at < older_than
        )

        if statuses:
            query = query.where(BackgroundJob.status.in_(statuses))

        result = await self.session.execute(query)
        return result.rowcount

    async def count_by_user(
        self,
        user_id: UUID,
        status: Optional[JobStatus] = None,
    ) -> int:
        """
        Count jobs for a user.

        Args:
            user_id: User ID
            status: Filter by status

        Returns:
            Job count
        """
        from sqlalchemy import func

        query = select(func.count(BackgroundJob.id)).where(
            BackgroundJob.user_id == user_id
        )

        if status:
            query = query.where(BackgroundJob.status == status)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_pending_jobs(
        self,
        job_type: Optional[JobType] = None,
        limit: int = 10,
    ) -> List[BackgroundJob]:
        """
        Get pending jobs for processing.

        Args:
            job_type: Filter by type
            limit: Maximum jobs

        Returns:
            List of pending jobs
        """
        query = select(BackgroundJob).where(
            BackgroundJob.status == JobStatus.PENDING
        )

        if job_type:
            query = query.where(BackgroundJob.job_type == job_type)

        query = query.order_by(BackgroundJob.created_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
