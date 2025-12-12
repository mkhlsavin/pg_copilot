"""
Project Group Repository.

Provides data access for project group operations.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.database.models import ProjectGroup, UserGroupAccess, GroupRole, User


class ProjectGroupRepository:
    """
    Project group repository for database operations.

    Handles CRUD operations for project groups and user access management.
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
        name: str,
        description: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Create a new project group.

        Args:
            name: Group name (unique)
            description: Group description

        Returns:
            Created project group
        """
        group = ProjectGroup(
            name=name,
            description=description,
        )

        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)

        return group

    async def get_by_id(
        self,
        group_id: UUID,
        include_projects: bool = False,
        include_users: bool = False,
    ) -> Optional[ProjectGroup]:
        """
        Get project group by ID.

        Args:
            group_id: Group ID
            include_projects: Include related projects
            include_users: Include related user access

        Returns:
            Project group or None
        """
        query = select(ProjectGroup).where(ProjectGroup.id == group_id)

        if include_projects:
            query = query.options(selectinload(ProjectGroup.projects))
        if include_users:
            query = query.options(selectinload(ProjectGroup.user_access))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[ProjectGroup]:
        """
        Get project group by name.

        Args:
            name: Group name

        Returns:
            Project group or None
        """
        query = select(ProjectGroup).where(ProjectGroup.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ProjectGroup]:
        """
        List all project groups.

        Args:
            limit: Maximum groups
            offset: Skip count

        Returns:
            List of project groups
        """
        query = (
            select(ProjectGroup)
            .order_by(ProjectGroup.name.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """
        Count all project groups.

        Returns:
            Group count
        """
        query = select(func.count(ProjectGroup.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update(
        self,
        group_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[ProjectGroup]:
        """
        Update project group.

        Args:
            group_id: Group ID
            name: New name
            description: New description

        Returns:
            Updated group or None
        """
        updates = {"updated_at": datetime.now(UTC)}

        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description

        await self.db.execute(
            update(ProjectGroup).where(ProjectGroup.id == group_id).values(**updates)
        )

        return await self.get_by_id(group_id)

    async def delete(self, group_id: UUID) -> bool:
        """
        Delete a project group.

        Args:
            group_id: Group ID

        Returns:
            True if deleted
        """
        result = await self.db.execute(
            delete(ProjectGroup).where(ProjectGroup.id == group_id)
        )
        return result.rowcount > 0

    # User access management

    async def add_user(
        self,
        group_id: UUID,
        user_id: UUID,
        role: GroupRole = GroupRole.VIEWER,
    ) -> UserGroupAccess:
        """
        Add user access to a group.

        Args:
            group_id: Group ID
            user_id: User ID
            role: User role in group

        Returns:
            Created user access
        """
        access = UserGroupAccess(
            group_id=group_id,
            user_id=user_id,
            role=role,
        )

        self.db.add(access)
        await self.db.flush()
        await self.db.refresh(access)

        return access

    async def remove_user(self, group_id: UUID, user_id: UUID) -> bool:
        """
        Remove user access from a group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            True if removed
        """
        result = await self.db.execute(
            delete(UserGroupAccess).where(
                UserGroupAccess.group_id == group_id,
                UserGroupAccess.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def update_user_role(
        self,
        group_id: UUID,
        user_id: UUID,
        role: GroupRole,
    ) -> Optional[UserGroupAccess]:
        """
        Update user role in a group.

        Args:
            group_id: Group ID
            user_id: User ID
            role: New role

        Returns:
            Updated access or None
        """
        await self.db.execute(
            update(UserGroupAccess)
            .where(
                UserGroupAccess.group_id == group_id,
                UserGroupAccess.user_id == user_id,
            )
            .values(role=role)
        )

        query = select(UserGroupAccess).where(
            UserGroupAccess.group_id == group_id,
            UserGroupAccess.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_access(
        self,
        group_id: UUID,
        user_id: UUID,
    ) -> Optional[UserGroupAccess]:
        """
        Get user access for a group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            User access or None
        """
        query = select(UserGroupAccess).where(
            UserGroupAccess.group_id == group_id,
            UserGroupAccess.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_users(self, group_id: UUID) -> List[UserGroupAccess]:
        """
        Get all user access records for a group.

        Args:
            group_id: Group ID

        Returns:
            List of user access records
        """
        query = (
            select(UserGroupAccess)
            .where(UserGroupAccess.group_id == group_id)
            .options(selectinload(UserGroupAccess.user))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_groups(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ProjectGroup]:
        """
        Get all groups accessible by a user.

        Args:
            user_id: User ID
            limit: Maximum groups
            offset: Skip count

        Returns:
            List of project groups
        """
        query = (
            select(ProjectGroup)
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(UserGroupAccess.user_id == user_id)
            .order_by(ProjectGroup.name.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_groups(self, user_id: UUID) -> int:
        """
        Count groups accessible by a user.

        Args:
            user_id: User ID

        Returns:
            Group count
        """
        query = (
            select(func.count(ProjectGroup.id))
            .join(UserGroupAccess, ProjectGroup.id == UserGroupAccess.group_id)
            .where(UserGroupAccess.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def has_access(
        self,
        group_id: UUID,
        user_id: UUID,
        min_role: Optional[GroupRole] = None,
    ) -> bool:
        """
        Check if user has access to a group.

        Args:
            group_id: Group ID
            user_id: User ID
            min_role: Minimum required role

        Returns:
            True if user has access
        """
        query = select(UserGroupAccess).where(
            UserGroupAccess.group_id == group_id,
            UserGroupAccess.user_id == user_id,
        )

        result = await self.db.execute(query)
        access = result.scalar_one_or_none()

        if not access:
            return False

        if min_role is None:
            return True

        # Check role hierarchy
        role_hierarchy = {
            GroupRole.VIEWER: 0,
            GroupRole.EDITOR: 1,
            GroupRole.ADMIN: 2,
        }

        return role_hierarchy.get(access.role, 0) >= role_hierarchy.get(min_role, 0)
