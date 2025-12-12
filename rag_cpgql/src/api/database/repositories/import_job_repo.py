"""
Import Job Repository.

Provides data access for import job operations.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import ImportJob, ImportStatus, ImportMode


class ImportJobRepository:
    """
    Import job repository for database operations.

    Handles CRUD operations for project import jobs.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Database session
        """
        self.db = session

    async def create(
        self,
        user_id: UUID,
        project_name: str,
        group_id: Optional[UUID] = None,
        source_url: Optional[str] = None,
        language: Optional[str] = None,
        import_mode: ImportMode = ImportMode.FULL,
    ) -> ImportJob:
        """
        Create a new import job.

        Args:
            user_id: User ID who initiated the import
            project_name: Name of the project to import
            group_id: Target group ID
            source_url: Source URL (git repository, etc.)
            language: Programming language
            import_mode: Import mode

        Returns:
            Created import job
        """
        job = ImportJob(
            user_id=user_id,
            group_id=group_id,
            project_name=project_name,
            source_url=source_url,
            language=language,
            import_mode=import_mode,
            status=ImportStatus.PENDING,
            steps=[],
        )

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def get_by_id(self, job_id: UUID) -> Optional[ImportJob]:
        """
        Get import job by ID.

        Args:
            job_id: Job ID

        Returns:
            Import job or None
        """
        query = select(ImportJob).where(ImportJob.id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ImportJob]:
        """
        Get import jobs for a user.

        Args:
            user_id: User ID
            limit: Maximum jobs
            offset: Skip count

        Returns:
            List of import jobs
        """
        query = (
            select(ImportJob)
            .where(ImportJob.user_id == user_id)
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_group(
        self,
        group_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ImportJob]:
        """
        Get import jobs for a group.

        Args:
            group_id: Group ID
            limit: Maximum jobs
            offset: Skip count

        Returns:
            List of import jobs
        """
        query = (
            select(ImportJob)
            .where(ImportJob.group_id == group_id)
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: ImportStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ImportJob]:
        """
        Get import jobs by status.

        Args:
            status: Job status
            limit: Maximum jobs
            offset: Skip count

        Returns:
            List of import jobs
        """
        query = (
            select(ImportJob)
            .where(ImportJob.status == status)
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        """
        Count import jobs for a user.

        Args:
            user_id: User ID

        Returns:
            Job count
        """
        query = select(func.count(ImportJob.id)).where(ImportJob.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def start(self, job_id: UUID) -> Optional[ImportJob]:
        """
        Start an import job.

        Args:
            job_id: Job ID

        Returns:
            Updated job or None
        """
        await self.db.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                status=ImportStatus.RUNNING,
                started_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        return await self.get_by_id(job_id)

    async def update_status(
        self,
        job_id: UUID,
        status: ImportStatus,
        current_step: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> Optional[ImportJob]:
        """
        Update import job status.

        Args:
            job_id: Job ID
            status: New status
            current_step: Current step name
            progress: Progress percentage (0-100)

        Returns:
            Updated job or None
        """
        updates = {
            "status": status,
            "updated_at": datetime.now(UTC),
        }

        if current_step is not None:
            updates["current_step"] = current_step
        if progress is not None:
            updates["progress"] = min(100, max(0, progress))

        await self.db.execute(
            update(ImportJob).where(ImportJob.id == job_id).values(**updates)
        )

        return await self.get_by_id(job_id)

    async def update_step(
        self,
        job_id: UUID,
        step_name: str,
        step_status: str,
        step_message: Optional[str] = None,
    ) -> Optional[ImportJob]:
        """
        Update a step in the import job.

        Args:
            job_id: Job ID
            step_name: Step name
            step_status: Step status (pending, running, completed, failed)
            step_message: Optional message

        Returns:
            Updated job or None
        """
        job = await self.get_by_id(job_id)
        if not job:
            return None

        # Get current steps
        steps = job.steps or []

        # Find and update step, or add new one
        step_found = False
        for step in steps:
            if step.get("name") == step_name:
                step["status"] = step_status
                if step_message:
                    step["message"] = step_message
                step["updated_at"] = datetime.now(UTC).isoformat()
                step_found = True
                break

        if not step_found:
            steps.append({
                "name": step_name,
                "status": step_status,
                "message": step_message,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            })

        await self.db.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                steps=steps,
                current_step=step_name,
                updated_at=datetime.now(UTC),
            )
        )

        return await self.get_by_id(job_id)

    async def complete(
        self,
        job_id: UUID,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[ImportJob]:
        """
        Mark import job as completed.

        Args:
            job_id: Job ID
            result: Job result data

        Returns:
            Updated job or None
        """
        await self.db.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                status=ImportStatus.COMPLETED,
                progress=100,
                result=result,
                completed_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        return await self.get_by_id(job_id)

    async def fail(
        self,
        job_id: UUID,
        error_message: str,
    ) -> Optional[ImportJob]:
        """
        Mark import job as failed.

        Args:
            job_id: Job ID
            error_message: Error message

        Returns:
            Updated job or None
        """
        await self.db.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                status=ImportStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        return await self.get_by_id(job_id)

    async def cancel(self, job_id: UUID) -> Optional[ImportJob]:
        """
        Cancel an import job.

        Args:
            job_id: Job ID

        Returns:
            Updated job or None
        """
        await self.db.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                status=ImportStatus.CANCELLED,
                completed_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        return await self.get_by_id(job_id)

    async def delete(self, job_id: UUID) -> bool:
        """
        Delete an import job.

        Args:
            job_id: Job ID

        Returns:
            True if deleted
        """
        result = await self.db.execute(
            delete(ImportJob).where(ImportJob.id == job_id)
        )
        return result.rowcount > 0

    async def cleanup_old_jobs(
        self,
        days: int = 30,
        statuses: Optional[List[ImportStatus]] = None,
    ) -> int:
        """
        Delete old completed/failed jobs.

        Args:
            days: Delete jobs older than this many days
            statuses: Statuses to clean up (default: completed, failed, cancelled)

        Returns:
            Number of deleted jobs
        """
        if statuses is None:
            statuses = [
                ImportStatus.COMPLETED,
                ImportStatus.FAILED,
                ImportStatus.CANCELLED,
            ]

        cutoff = datetime.now(UTC) - timedelta(days=days)

        result = await self.db.execute(
            delete(ImportJob).where(
                ImportJob.status.in_(statuses),
                ImportJob.updated_at < cutoff,
            )
        )

        return result.rowcount
