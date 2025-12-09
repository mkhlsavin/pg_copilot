"""
API Key Management.

Provides API key generation, validation, and management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ApiKeyInfo(BaseModel):
    """API key information model (without the actual key)."""

    id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_revoked: bool


class ApiKeyWithSecret(ApiKeyInfo):
    """API key with the secret key (only returned on creation)."""

    key: str


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, prefix, key_hash)
    """
    # Generate a random key: prefix + secret
    prefix = f"rag_{secrets.token_hex(4)}"
    secret = secrets.token_hex(24)
    full_key = f"{prefix}_{secret}"

    # Hash the key for storage
    key_hash = hash_api_key(full_key)

    return full_key, prefix, key_hash


def hash_api_key(key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        key: Full API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.

    Args:
        key: API key to verify
        stored_hash: Stored hash to compare against

    Returns:
        True if key matches hash
    """
    return secrets.compare_digest(hash_api_key(key), stored_hash)


def extract_prefix(key: str) -> str:
    """
    Extract the prefix from an API key.

    Args:
        key: Full API key

    Returns:
        Key prefix
    """
    parts = key.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return key[:12]


def is_key_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if an API key has expired.

    Args:
        expires_at: Expiration datetime (None = never expires)

    Returns:
        True if expired
    """
    if expires_at is None:
        return False
    return datetime.utcnow() > expires_at


def calculate_expiration(days: Optional[int] = None) -> Optional[datetime]:
    """
    Calculate expiration datetime.

    Args:
        days: Number of days until expiration (None = never expires)

    Returns:
        Expiration datetime or None
    """
    if days is None or days <= 0:
        return None
    return datetime.utcnow() + timedelta(days=days)


# Repository functions (to be implemented with actual database)

class ApiKeyRepository:
    """
    API Key Repository.

    Handles database operations for API keys.
    """

    async def create(
        self,
        user_id: UUID,
        name: str,
        scopes: List[str],
        expires_days: Optional[int] = 365,
    ) -> ApiKeyWithSecret:
        """
        Create a new API key.

        Args:
            user_id: Owner user ID
            name: Key name/description
            scopes: Permission scopes
            expires_days: Days until expiration

        Returns:
            Created API key with secret
        """
        # Generate key
        full_key, prefix, key_hash = generate_api_key()
        expires_at = calculate_expiration(expires_days)

        # TODO: Store in database
        # key_record = await self.db.create_api_key(...)

        return ApiKeyWithSecret(
            id="placeholder",
            name=name,
            prefix=prefix,
            key=full_key,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_used_at=None,
            is_revoked=False,
        )

    async def validate(self, key: str) -> Optional[ApiKeyInfo]:
        """
        Validate an API key and return its info.

        Args:
            key: API key to validate

        Returns:
            API key info if valid, None otherwise
        """
        prefix = extract_prefix(key)

        # TODO: Look up by prefix in database
        # key_record = await self.db.get_api_key_by_prefix(prefix)

        # if key_record is None:
        #     return None

        # if not verify_api_key(key, key_record.key_hash):
        #     return None

        # if key_record.is_revoked:
        #     return None

        # if is_key_expired(key_record.expires_at):
        #     return None

        # # Update last_used_at
        # await self.db.update_api_key_last_used(key_record.id)

        # return ApiKeyInfo.from_orm(key_record)

        return None  # Placeholder

    async def list_for_user(self, user_id: UUID) -> List[ApiKeyInfo]:
        """
        List all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of API key info (without secrets)
        """
        # TODO: Query database
        return []

    async def revoke(self, key_id: UUID, user_id: UUID) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key ID
            user_id: Owner user ID (for authorization)

        Returns:
            True if revoked successfully
        """
        # TODO: Update database
        return False

    async def delete(self, key_id: UUID, user_id: UUID) -> bool:
        """
        Delete an API key.

        Args:
            key_id: API key ID
            user_id: Owner user ID (for authorization)

        Returns:
            True if deleted successfully
        """
        # TODO: Delete from database
        return False
