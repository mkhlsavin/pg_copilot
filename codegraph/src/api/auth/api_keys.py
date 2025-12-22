"""
API Key Management.

Provides API key generation, validation, and management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

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


# NOTE: ApiKeyRepository is implemented in src/api/database/repositories/api_key_repo.py
# This module contains utility functions for API key operations


async def validate_api_key(
    key: str,
    api_key_repo,
    user_repo,
):
    """
    Validate an API key and return the associated user.

    Args:
        key: Full API key to validate
        api_key_repo: ApiKeyRepository instance
        user_repo: UserRepository instance

    Returns:
        User if valid, None otherwise
    """
    # Extract prefix and lookup key
    prefix = extract_prefix(key)
    api_key = await api_key_repo.get_by_prefix(prefix)

    if not api_key:
        return None

    # Verify the key hash
    if not verify_api_key(key, api_key.key_hash):
        return None

    # Check if revoked
    if api_key.is_revoked:
        return None

    # Check expiration
    if is_key_expired(api_key.expires_at):
        return None

    # Update last used timestamp
    await api_key_repo.update_last_used(api_key.id)

    # Return the associated user
    user = await user_repo.get_by_id(api_key.user_id)
    return user if user and user.is_active else None
