"""
Job Service Module.

Provides business logic for background job management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from src.api.database.repositories.job_repo import JobRepository
from src.api.database.models import BackgroundJob, JobStatus, JobType

logger = logging.getLogger("api.services.job")


class JobService:
    """
    Background job management service.

    Provides high-level operations for managing background jobs.
    """

    def __init__(self, job_repo: JobRepository):
        """
        Initialize the job service.

        Args:
            job_repo: Job repository
        """
        self.repo = job_repo
        self._ws_manager = None  # Will be set for WebSocket notifications

    def set_websocket_manager(self, ws_manager) -> None:
        """
        Set WebSocket manager for notifications.

        Args:
            ws_manager: WebSocket manager instance
        """
        self._ws_manager = ws_manager

    async def create_job(
        self,
        user_id: UUID,
        job_type: JobType,
        params: Optional[Dict[str, Any]] = None,
    ) -> BackgroundJob:
        """
        Create a new background job.

        Args:
            user_id: User ID
            job_type: Type of job
            params: Job parameters

        Returns:
            Created job
        """
        job = await self.repo.create(
            user_id=user_id,
            job_type=job_type,
            params=params,
        )

        logger.info(f"Created job {job.id} of type {job_type.value} for user {user_id}")
        return job

    async def get_job(
        self,
        job_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[BackgroundJob]:
        """
        Get a job by ID.

        Args:
            job_id: Job ID
            user_id: User ID (for authorization, optional)

        Returns:
            Job or None
        """
        job = await self.repo.get_by_id(job_id)

        # Verify ownership if user_id provided
        if job and user_id and job.user_id != user_id:
            return None

        return job

    async def list_jobs(
        self,
        user_id: UUID,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BackgroundJob]:
        """
        List jobs for a user.

        Args:
            user_id: User ID
            status: Filter by status
            job_type: Filter by type
            limit: Maximum jobs
            offset: Skip count

        Returns:
            List of jobs
        """
        return await self.repo.get_by_user(
            user_id=user_id,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset,
        )

    async def start_job(self, job_id: UUID) -> Optional[BackgroundJob]:
        """
        Mark a job as started.

        Args:
            job_id: Job ID

        Returns:
            Updated job or None
        """
        job = await self.repo.start(job_id)

        if job:
            logger.info(f"Job {job_id} started")
            await self._notify_job_update(job, "started")

        return job

    async def update_progress(
        self,
        job_id: UUID,
        progress: int,
        message: Optional[str] = None,
    ) -> None:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            message: Progress message
        """
        await self.repo.update_progress(job_id, progress)

        # Notify via WebSocket
        job = await self.repo.get_by_id(job_id)
        if job:
            await self._notify_job_update(
                job,
                "progress",
                {"progress": progress, "message": message},
            )

    async def complete_job(
        self,
        job_id: UUID,
        result: Dict[str, Any],
    ) -> Optional[BackgroundJob]:
        """
        Mark a job as completed.

        Args:
            job_id: Job ID
            result: Job result

        Returns:
            Updated job or None
        """
        job = await self.repo.complete(job_id, result)

        if job:
            logger.info(f"Job {job_id} completed")
            await self._notify_job_update(job, "completed", {"result": result})

        return job

    async def fail_job(
        self,
        job_id: UUID,
        error: str,
    ) -> Optional[BackgroundJob]:
        """
        Mark a job as failed.

        Args:
            job_id: Job ID
            error: Error message

        Returns:
            Updated job or None
        """
        job = await self.repo.fail(job_id, error)

        if job:
            logger.error(f"Job {job_id} failed: {error}")
            await self._notify_job_update(job, "failed", {"error": error})

        return job

    async def cancel_job(
        self,
        job_id: UUID,
        user_id: UUID,
    ) -> Optional[BackgroundJob]:
        """
        Cancel a job.

        Args:
            job_id: Job ID
            user_id: User ID (for authorization)

        Returns:
            Cancelled job or None
        """
        # Verify ownership
        job = await self.repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            return None

        # Can only cancel pending or running jobs
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            return None

        job = await self.repo.cancel(job_id)

        if job:
            logger.info(f"Job {job_id} cancelled")
            await self._notify_job_update(job, "cancelled")

        return job

    async def delete_job(
        self,
        job_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted
        """
        # Verify ownership
        job = await self.repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            return False

        result = await self.repo.delete(job_id)

        if result:
            logger.info(f"Job {job_id} deleted")

        return result

    async def cleanup_old_jobs(
        self,
        days: int = 7,
    ) -> int:
        """
        Clean up old completed/failed jobs.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of deleted jobs
        """
        older_than = datetime.utcnow() - timedelta(days=days)

        count = await self.repo.delete_old_jobs(
            older_than=older_than,
            statuses=[JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
        )

        if count > 0:
            logger.info(f"Cleaned up {count} old jobs")

        return count

    async def count_user_jobs(
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
        return await self.repo.count_by_user(user_id, status)

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
        return await self.repo.get_pending_jobs(job_type, limit)

    async def run_job(
        self,
        job_id: UUID,
        handler: Callable[[BackgroundJob], Any],
    ) -> Optional[BackgroundJob]:
        """
        Run a job with the given handler.

        Args:
            job_id: Job ID
            handler: Job handler function

        Returns:
            Completed/failed job
        """
        job = await self.start_job(job_id)
        if not job:
            return None

        try:
            result = await handler(job)
            return await self.complete_job(job_id, result)
        except Exception as e:
            logger.exception(f"Job {job_id} failed with error: {e}")
            return await self.fail_job(job_id, str(e))

    async def _notify_job_update(
        self,
        job: BackgroundJob,
        event: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Send WebSocket notification for job update.

        Args:
            job: Job
            event: Event type
            data: Additional data
        """
        if not self._ws_manager:
            return

        try:
            message = {
                "type": f"job.{event}",
                "payload": {
                    "job_id": str(job.id),
                    "job_type": job.job_type.value,
                    "status": job.status.value,
                    "progress": job.progress,
                    **(data or {}),
                },
            }

            await self._ws_manager.send_to_user(
                str(job.user_id),
                message,
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")
