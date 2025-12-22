"""
PostgreSQL Project Registry.

Manages projects and import jobs in PostgreSQL database.
Uses existing models from src.api.database.models.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ProjectRegistry:
    """
    Manage projects in PostgreSQL.

    Provides CRUD operations for projects and import jobs.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize project registry.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create_project(
        self,
        name: str,
        group_id: UUID,
        source_path: str,
        cpg_path: str,
        duckdb_path: str,
        language: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a new project record.

        Args:
            name: Project name.
            group_id: Project group ID.
            source_path: Path to source code.
            cpg_path: Path to CPG file.
            duckdb_path: Path to DuckDB file.
            language: Programming language.
            description: Optional project description.
            metadata: Optional metadata dictionary.

        Returns:
            Created Project instance.
        """
        from src.api.database.models import Project

        project = Project(
            name=name,
            group_id=group_id,
            source_path=source_path,
            cpg_path=cpg_path,
            db_path=duckdb_path,
            language=language,
            description=description,
            is_active=False,
            metadata=metadata or {},
        )

        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)

        logger.info(f"Created project: {name} (ID: {project.id})")

        return project

    async def get_project(self, project_id: UUID):
        """
        Get project by ID.

        Args:
            project_id: Project UUID.

        Returns:
            Project instance or None if not found.
        """
        from src.api.database.models import Project

        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_project_by_name(self, name: str, group_id: Optional[UUID] = None):
        """
        Get project by name.

        Args:
            name: Project name.
            group_id: Optional group ID to scope the search.

        Returns:
            Project instance or None if not found.
        """
        from src.api.database.models import Project

        query = select(Project).where(Project.name == name)
        if group_id:
            query = query.where(Project.group_id == group_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        group_id: Optional[UUID] = None,
        language: Optional[str] = None,
        active_only: bool = False,
    ) -> List:
        """
        List all projects.

        Args:
            group_id: Optional group ID to filter by.
            language: Optional language to filter by.
            active_only: Only return active projects.

        Returns:
            List of Project instances.
        """
        from src.api.database.models import Project

        query = select(Project)

        if group_id:
            query = query.where(Project.group_id == group_id)
        if language:
            query = query.where(Project.language == language)
        if active_only:
            query = query.where(Project.is_active == True)

        query = query.order_by(Project.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_project(self, group_id: Optional[UUID] = None):
        """
        Get the currently active project.

        Args:
            group_id: Optional group ID to scope the search.

        Returns:
            Active Project instance or None.
        """
        from src.api.database.models import Project

        query = select(Project).where(Project.is_active == True)
        if group_id:
            query = query.where(Project.group_id == group_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_active_project(self, project_id: UUID) -> bool:
        """
        Set project as active (deactivates others in the same group).

        Args:
            project_id: Project ID to activate.

        Returns:
            True if successful.
        """
        from src.api.database.models import Project

        # Get the project to find its group
        project = await self.get_project(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            return False

        # Deactivate all projects in the same group
        await self.session.execute(
            update(Project)
            .where(Project.group_id == project.group_id)
            .values(is_active=False)
        )

        # Activate the specified project
        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(is_active=True)
        )

        await self.session.commit()

        logger.info(f"Activated project: {project.name} (ID: {project_id})")

        return True

    async def update_project(
        self,
        project_id: UUID,
        **kwargs,
    ):
        """
        Update project fields.

        Args:
            project_id: Project ID.
            **kwargs: Fields to update.

        Returns:
            Updated Project instance.
        """
        from src.api.database.models import Project

        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        await self.session.commit()

        return await self.get_project(project_id)

    async def delete_project(
        self,
        project_id: UUID,
        delete_files: bool = False,
    ) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project ID.
            delete_files: Also delete CPG and DuckDB files.

        Returns:
            True if successful.
        """
        from src.api.database.models import Project

        project = await self.get_project(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            return False

        # Delete files if requested
        if delete_files:
            if project.cpg_path:
                cpg_path = Path(project.cpg_path)
                if cpg_path.exists():
                    cpg_path.unlink()
                    logger.info(f"Deleted CPG file: {cpg_path}")

            if project.db_path:
                db_path = Path(project.db_path)
                if db_path.exists():
                    db_path.unlink()
                    logger.info(f"Deleted DuckDB file: {db_path}")
                # Also delete WAL file if exists
                wal_path = db_path.with_suffix(".duckdb.wal")
                if wal_path.exists():
                    wal_path.unlink()

            if project.source_path:
                source_path = Path(project.source_path)
                if source_path.exists() and source_path.is_dir():
                    shutil.rmtree(source_path)
                    logger.info(f"Deleted source directory: {source_path}")

        # Delete from database
        await self.session.execute(
            delete(Project).where(Project.id == project_id)
        )
        await self.session.commit()

        logger.info(f"Deleted project: {project.name} (ID: {project_id})")

        return True

    # Import Job Methods

    async def create_import_job(
        self,
        user_id: UUID,
        group_id: UUID,
        project_name: str,
        source_url: Optional[str],
        language: Optional[str],
        import_mode: str,
    ):
        """
        Create import job record.

        Args:
            user_id: User ID initiating the import.
            group_id: Target project group ID.
            project_name: Name for the project.
            source_url: Source repository URL.
            language: Programming language (or None for auto-detect).
            import_mode: Import mode (full, selective, incremental).

        Returns:
            Created ImportJob instance.
        """
        from src.api.database.models import ImportJob, ImportStatus, ImportMode

        job = ImportJob(
            user_id=user_id,
            group_id=group_id,
            project_name=project_name,
            source_url=source_url,
            language=language,
            import_mode=ImportMode(import_mode) if isinstance(import_mode, str) else import_mode,
            status=ImportStatus.PENDING,
            progress=0,
            current_step=None,
            steps={},
        )

        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        logger.info(f"Created import job: {project_name} (ID: {job.id})")

        return job

    async def get_import_job(self, job_id: UUID):
        """
        Get import job by ID.

        Args:
            job_id: Import job UUID.

        Returns:
            ImportJob instance or None.
        """
        from src.api.database.models import ImportJob

        result = await self.session.execute(
            select(ImportJob).where(ImportJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_import_jobs(
        self,
        user_id: Optional[UUID] = None,
        group_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List:
        """
        List import jobs.

        Args:
            user_id: Optional user ID to filter by.
            group_id: Optional group ID to filter by.
            status: Optional status to filter by.
            limit: Maximum number of jobs to return.

        Returns:
            List of ImportJob instances.
        """
        from src.api.database.models import ImportJob, ImportStatus

        query = select(ImportJob)

        if user_id:
            query = query.where(ImportJob.user_id == user_id)
        if group_id:
            query = query.where(ImportJob.group_id == group_id)
        if status:
            query = query.where(ImportJob.status == ImportStatus(status))

        query = query.order_by(ImportJob.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_import_job(
        self,
        job_id: UUID,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        steps: Optional[Dict] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict] = None,
    ):
        """
        Update import job progress.

        Args:
            job_id: Import job ID.
            status: New status.
            progress: Progress percentage (0-100).
            current_step: Current step name.
            steps: Step details dictionary.
            error_message: Error message if failed.
            result: Result data if completed.

        Returns:
            Updated ImportJob instance.
        """
        from src.api.database.models import ImportJob, ImportStatus

        update_values = {"updated_at": datetime.utcnow()}

        if status is not None:
            update_values["status"] = ImportStatus(status) if isinstance(status, str) else status
        if progress is not None:
            update_values["progress"] = progress
        if current_step is not None:
            update_values["current_step"] = current_step
        if steps is not None:
            update_values["steps"] = steps
        if error_message is not None:
            update_values["error_message"] = error_message
        if result is not None:
            update_values["result"] = result

        await self.session.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(**update_values)
        )
        await self.session.commit()

        return await self.get_import_job(job_id)

    async def complete_import_job(
        self,
        job_id: UUID,
        project_id: UUID,
        result: Dict[str, Any],
    ):
        """
        Mark import job as completed.

        Args:
            job_id: Import job ID.
            project_id: Created project ID.
            result: Import result data.

        Returns:
            Updated ImportJob instance.
        """
        from src.api.database.models import ImportStatus

        return await self.update_import_job(
            job_id=job_id,
            status=ImportStatus.COMPLETED,
            progress=100,
            current_step="completed",
            result={
                "project_id": str(project_id),
                **result,
            },
        )

    async def fail_import_job(
        self,
        job_id: UUID,
        error_message: str,
    ):
        """
        Mark import job as failed.

        Args:
            job_id: Import job ID.
            error_message: Error description.

        Returns:
            Updated ImportJob instance.
        """
        from src.api.database.models import ImportStatus

        return await self.update_import_job(
            job_id=job_id,
            status=ImportStatus.FAILED,
            error_message=error_message,
        )

    # Project Group Methods

    async def get_or_create_default_group(self, name: str = "default"):
        """
        Get or create a default project group.

        Args:
            name: Group name.

        Returns:
            ProjectGroup instance.
        """
        from src.api.database.models import ProjectGroup

        result = await self.session.execute(
            select(ProjectGroup).where(ProjectGroup.name == name)
        )
        group = result.scalar_one_or_none()

        if not group:
            group = ProjectGroup(
                name=name,
                description="Default project group",
            )
            self.session.add(group)
            await self.session.commit()
            await self.session.refresh(group)
            logger.info(f"Created default project group: {name}")

        return group

    async def list_groups(self) -> List:
        """
        List all project groups.

        Returns:
            List of ProjectGroup instances.
        """
        from src.api.database.models import ProjectGroup

        result = await self.session.execute(
            select(ProjectGroup).order_by(ProjectGroup.name)
        )
        return list(result.scalars().all())
