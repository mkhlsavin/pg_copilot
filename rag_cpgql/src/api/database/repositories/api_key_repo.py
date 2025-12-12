"""
API Key Repository.

Provides data access for API key operations.
"""

from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import ApiKey


class ApiKeyRepository:
    """
    API Key repository for database operations.

    Handles CRUD operations for API keys.
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
        name: str,
        key_hash: str,
        prefix: str,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> ApiKey:
        """
        Create a new API key.

        Args:
            user_id: Owner user ID
            name: Key name
            key_hash: Hashed key value
            prefix: Key prefix for identification
            scopes: Permission scopes
            expires_at: Expiration timestamp

        Returns:
            Created API key
        """
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            scopes=scopes or ["scenarios:read", "query:execute"],
            expires_at=expires_at,
        )

        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)

        return api_key

    async def get_by_id(self, key_id: UUID) -> Optional[ApiKey]:
        """
        Get API key by ID.

        Args:
            key_id: API key ID

        Returns:
            API key or None
        """
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_prefix(self, prefix: str) -> Optional[ApiKey]:
        """
        Get API key by prefix.

        Args:
            prefix: Key prefix

        Returns:
            API key or None
        """
        result = await self.session.execute(
            select(ApiKey).where(
                ApiKey.prefix == prefix,
                ApiKey.is_revoked == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        include_revoked: bool = False,
    ) -> List[ApiKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID
            include_revoked: Include revoked keys

        Returns:
            List of API keys
        """
        query = select(ApiKey).where(ApiKey.user_id == user_id)

        if not include_revoked:
            query = query.where(ApiKey.is_revoked == False)

        query = query.order_by(ApiKey.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_last_used(self, key_id: UUID) -> None:
        """
        Update last used timestamp.

        Args:
            key_id: API key ID
        """
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(last_used_at=datetime.now(UTC))
        )

    async def revoke(self, key_id: UUID) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key ID

        Returns:
            True if revoked
        """
        result = await self.session.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.is_revoked == False)
            .values(is_revoked=True)
        )
        return result.rowcount > 0

    async def delete(self, key_id: UUID) -> bool:
        """
        Delete an API key.

        Args:
            key_id: API key ID

        Returns:
            True if deleted
        """
        result = await self.session.execute(
            delete(ApiKey).where(ApiKey.id == key_id)
        )
        return result.rowcount > 0

    async def delete_by_user(self, user_id: UUID) -> int:
        """
        Delete all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted keys
        """
        result = await self.session.execute(
            delete(ApiKey).where(ApiKey.user_id == user_id)
        )
        return result.rowcount

    async def count_by_user(self, user_id: UUID, active_only: bool = True) -> int:
        """
        Count API keys for a user.

        Args:
            user_id: User ID
            active_only: Only count active (non-revoked) keys

        Returns:
            Key count
        """
        from sqlalchemy import func

        query = select(func.count(ApiKey.id)).where(ApiKey.user_id == user_id)

        if active_only:
            query = query.where(ApiKey.is_revoked == False)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def is_valid(self, key_id: UUID) -> bool:
        """
        Check if an API key is valid (not revoked and not expired).

        Args:
            key_id: API key ID

        Returns:
            True if valid
        """
        result = await self.session.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.is_revoked == False,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        # Check expiration (compare as naive UTC for DB compatibility)
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC).replace(tzinfo=None):
            return False

        return True
