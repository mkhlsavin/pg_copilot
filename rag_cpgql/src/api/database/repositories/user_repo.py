"""
User Repository.

Provides data access for user operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import User, AuthProvider, UserRole


class UserRepository:
    """
    User repository for database operations.

    Handles CRUD operations for users.
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
        username: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        external_id: Optional[str] = None,
        role: UserRole = UserRole.ANALYST,
    ) -> User:
        """
        Create a new user.

        Args:
            username: Username
            email: Email address
            password_hash: Hashed password (for local auth)
            auth_provider: Authentication provider
            external_id: External provider user ID
            role: User role

        Returns:
            Created user
        """
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            auth_provider=auth_provider,
            external_id=external_id,
            role=role,
        )

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        external_id: str,
        auth_provider: AuthProvider,
    ) -> Optional[User]:
        """
        Get user by external provider ID.

        Args:
            external_id: External provider user ID
            auth_provider: Authentication provider

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(
                User.external_id == external_id,
                User.auth_provider == auth_provider,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = True,
    ) -> List[User]:
        """
        List all users.

        Args:
            limit: Maximum number of users
            offset: Number of users to skip
            active_only: Only return active users

        Returns:
            List of users
        """
        query = select(User)

        if active_only:
            query = query.where(User.is_active == True)

        query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, active_only: bool = True) -> int:
        """
        Count users.

        Args:
            active_only: Only count active users

        Returns:
            User count
        """
        from sqlalchemy import func

        query = select(func.count(User.id))

        if active_only:
            query = query.where(User.is_active == True)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update(
        self,
        user_id: UUID,
        **kwargs,
    ) -> Optional[User]:
        """
        Update user fields.

        Args:
            user_id: User ID
            **kwargs: Fields to update

        Returns:
            Updated user or None
        """
        # Filter out None values and add updated_at
        updates = {k: v for k, v in kwargs.items() if v is not None}
        updates["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(User).where(User.id == user_id).values(**updates)
        )

        return await self.get_by_id(user_id)

    async def update_role(self, user_id: UUID, role: UserRole) -> Optional[User]:
        """
        Update user role.

        Args:
            user_id: User ID
            role: New role

        Returns:
            Updated user or None
        """
        return await self.update(user_id, role=role)

    async def deactivate(self, user_id: UUID) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            Deactivated user or None
        """
        return await self.update(user_id, is_active=False)

    async def activate(self, user_id: UUID) -> Optional[User]:
        """
        Activate a user.

        Args:
            user_id: User ID

        Returns:
            Activated user or None
        """
        return await self.update(user_id, is_active=True)

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        result = await self.session.execute(
            delete(User).where(User.id == user_id)
        )
        return result.rowcount > 0

    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> Optional[User]:
        """
        Update user password.

        Args:
            user_id: User ID
            password_hash: New password hash

        Returns:
            Updated user or None
        """
        return await self.update(user_id, password_hash=password_hash)
