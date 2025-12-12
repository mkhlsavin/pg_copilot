"""
Project Repository.

Provides data access for project operations.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.database.models import Project, ProjectGroup, UserGroupAccess


class ProjectRepository:
    """
    Project repository for database operations.

    Handles CRUD operations for projects within groups.
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
        group_id: UUID,
        name: str,
        db_path: Optional[str] = None,
        cpg_path: Optional[str] = None,
        source_path: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Project:
        """
        Create a new project in a group.

        Args:
            group_id: Group ID
            name: Project name (unique within group)
            db_path: Path to DuckDB file
            cpg_path: Path to CPG file
            source_path: Path to source code
            language: Programming language
            description: Project description
            metadata: Additional metadata

        Returns:
            Created project
        """
        project = Project(
            group_id=group_id,
            name=name,
            db_path=db_path,
            cpg_path=cpg_path,
            source_path=source_path,
            language=language,
            description=description,
            project_metadata=metadata or {},
        )

        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)

        return project

    async def get_by_id(
        self,
        project_id: UUID,
        include_group: bool = False,
    ) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project ID
            include_group: Include related group

        Returns:
            Project or None
        """
        query = select(Project).where(Project.id == project_id)

        if include_group:
            query = query.options(selectinload(Project.group))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        group_id: UUID,
        name: str,
    ) -> Optional[Project]:
        """
        Get project by name within a group.

        Args:
            group_id: Group ID
            name: Project name

        Returns:
            Project or None
        """
        query = select(Project).where(
            Project.group_id == group_id,
            Project.name == name,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_group(
        self,
        group_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        """
        Get all projects in a group.

        Args:
            group_id: Group ID
            limit: Maximum projects
            offset: Skip count

        Returns:
            List of projects
        """
        query = (
            select(Project)
            .where(Project.group_id == group_id)
            .order_by(Project.name.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_group(self, group_id: UUID) -> int:
        """
        Count projects in a group.

        Args:
            group_id: Group ID

        Returns:
            Project count
        """
        query = select(func.count(Project.id)).where(Project.group_id == group_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_active_project(self, group_id: UUID) -> Optional[Project]:
        """
        Get the active project in a group.

        Args:
            group_id: Group ID

        Returns:
            Active project or None
        """
        query = select(Project).where(
            Project.group_id == group_id,
            Project.is_active == True,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def set_active(self, project_id: UUID) -> Optional[Project]:
        """
        Set a project as active (deactivates others in the group).

        Args:
            project_id: Project ID to activate

        Returns:
            Activated project or None
        """
        # Get the project to find its group
        project = await self.get_by_id(project_id)
        if not project:
            return None

        # Deactivate all projects in the group
        await self.db.execute(
            update(Project)
            .where(Project.group_id == project.group_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )

        # Activate the specified project
        await self.db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(is_active=True, updated_at=datetime.now(UTC))
        )

        return await self.get_by_id(project_id)

    async def update(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        db_path: Optional[str] = None,
        cpg_path: Optional[str] = None,
        source_path: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Project]:
        """
        Update a project.

        Args:
            project_id: Project ID
            name: New name
            db_path: New DuckDB path
            cpg_path: New CPG path
            source_path: New source path
            language: New language
            description: New description
            metadata: New metadata

        Returns:
            Updated project or None
        """
        updates = {"updated_at": datetime.now(UTC)}

        if name is not None:
            updates["name"] = name
        if db_path is not None:
            updates["db_path"] = db_path
        if cpg_path is not None:
            updates["cpg_path"] = cpg_path
        if source_path is not None:
            updates["source_path"] = source_path
        if language is not None:
            updates["language"] = language
        if description is not None:
            updates["description"] = description
        if metadata is not None:
            updates["project_metadata"] = metadata

        await self.db.execute(
            update(Project).where(Project.id == project_id).values(**updates)
        )

        return await self.get_by_id(project_id)

    async def delete(self, project_id: UUID) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project ID

        Returns:
            True if deleted
        """
        result = await self.db.execute(
            delete(Project).where(Project.id == project_id)
        )
        return result.rowcount > 0

    async def get_user_projects(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        """
        Get all projects accessible by a user (through their groups).

        Args:
            user_id: User ID
            limit: Maximum projects
            offset: Skip count

        Returns:
            List of projects
        """
        query = (
            select(Project)
            .join(ProjectGroup, Project.group_id == ProjectGroup.id)
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(UserGroupAccess.user_id == user_id)
            .order_by(ProjectGroup.name.asc(), Project.name.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_projects(self, user_id: UUID) -> int:
        """
        Count projects accessible by a user.

        Args:
            user_id: User ID

        Returns:
            Project count
        """
        query = (
            select(func.count(Project.id))
            .join(ProjectGroup, Project.group_id == ProjectGroup.id)
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(UserGroupAccess.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_active_user_project(self, user_id: UUID) -> Optional[Project]:
        """
        Get the active project for a user across all their groups.

        Args:
            user_id: User ID

        Returns:
            Active project or None (returns first active if multiple)
        """
        query = (
            select(Project)
            .join(ProjectGroup, Project.group_id == ProjectGroup.id)
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(
                UserGroupAccess.user_id == user_id,
                Project.is_active == True,
            )
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def user_has_access(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Check if a user has access to a project.

        Args:
            project_id: Project ID
            user_id: User ID

        Returns:
            True if user has access
        """
        query = (
            select(func.count(Project.id))
            .join(ProjectGroup, Project.group_id == ProjectGroup.id)
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(
                Project.id == project_id,
                UserGroupAccess.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
