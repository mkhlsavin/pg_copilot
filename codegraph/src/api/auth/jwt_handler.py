"""
JWT Token Handler.

Provides JWT token creation, verification, and management.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import delete, select

from src.api.config import get_settings

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str  # Subject (user_id)
    jti: str  # JWT ID (unique identifier)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str  # Token type: "access" or "refresh"
    scopes: list[str] = []  # Permission scopes
    role: Optional[str] = None  # User role


class TokenError(Exception):
    """Token-related error."""

    def __init__(self, message: str, code: str = "token_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def create_access_token(
    user_id: str,
    scopes: Optional[list[str]] = None,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT access token.

    Args:
        user_id: User ID to encode in token
        scopes: Permission scopes
        role: User role
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_algorithm and 30)

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = TokenPayload(
        sub=user_id,
        jti=str(uuid.uuid4()),
        exp=expire,
        iat=now,
        type="access",
        scopes=scopes or [],
        role=role,
    )

    # Convert to dict with timestamps for JWT (iat/exp must be Unix timestamps)
    payload_dict = payload.model_dump()
    payload_dict["exp"] = int(expire.timestamp())
    payload_dict["iat"] = int(now.timestamp())

    token = jwt.encode(
        payload_dict,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm or "HS256",
    )

    return token


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT refresh token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    settings = get_settings()

    if expires_delta is None:
        # Default: 7 days
        expires_delta = timedelta(days=7)

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = TokenPayload(
        sub=user_id,
        jti=str(uuid.uuid4()),
        exp=expire,
        iat=now,
        type="refresh",
        scopes=[],
        role=None,
    )

    # Convert to dict with timestamps for JWT (iat/exp must be Unix timestamps)
    payload_dict = payload.model_dump()
    payload_dict["exp"] = int(expire.timestamp())
    payload_dict["iat"] = int(now.timestamp())

    token = jwt.encode(
        payload_dict,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm or "HS256",
    )

    return token


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm or "HS256"],
        )

        return TokenPayload(**payload)

    except JWTError as e:
        raise TokenError(f"Invalid token: {str(e)}", "invalid_token")


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Verify a JWT token and check its type.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)

    # Check token type
    if payload.type != token_type:
        raise TokenError(
            f"Invalid token type. Expected {token_type}, got {payload.type}",
            "wrong_token_type",
        )

    # Check expiration (use timestamp comparison to avoid timezone issues)
    now_timestamp = datetime.utcnow().timestamp()
    exp_timestamp = payload.exp.timestamp() if isinstance(payload.exp, datetime) else payload.exp
    if exp_timestamp < now_timestamp:
        raise TokenError("Token has expired", "token_expired")

    return payload


def get_token_jti(token: str) -> str:
    """
    Extract JTI (JWT ID) from a token without full validation.

    Args:
        token: JWT token string

    Returns:
        JWT ID string
    """
    try:
        # Decode without verification to get JTI
        unverified = jwt.get_unverified_claims(token)
        return unverified.get("jti", "")
    except Exception:
        return ""


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Extract expiration time from a token without full validation.

    Args:
        token: JWT token string

    Returns:
        Expiration datetime or None
    """
    try:
        unverified = jwt.get_unverified_claims(token)
        exp = unverified.get("exp")
        if exp:
            return datetime.fromtimestamp(exp)
        return None
    except Exception:
        return None


# Token blacklist functions (for revocation)
# Uses PostgreSQL for persistence with in-memory cache for performance

_blacklisted_tokens: set[str] = set()


async def blacklist_token(jti: str, expires_at: Optional[datetime] = None) -> None:
    """
    Add a token to the blacklist.

    Stores the token in PostgreSQL for persistence and adds to in-memory
    cache for fast lookups.

    Args:
        jti: JWT ID to blacklist
        expires_at: Token expiration time (for cleanup scheduling)
    """
    from src.api.database.connection import get_db_session
    from src.api.database.models import TokenBlacklist

    # Add to in-memory cache immediately
    _blacklisted_tokens.add(jti)

    # Store in PostgreSQL for persistence
    try:
        async with get_db_session() as db:
            # Check if already exists
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                blacklist_entry = TokenBlacklist(
                    jti=jti,
                    expires_at=expires_at or datetime.utcnow() + timedelta(days=7),
                )
                db.add(blacklist_entry)
                await db.commit()
                logger.debug(f"Token {jti[:8]}... added to blacklist")
    except Exception as e:
        logger.error(f"Failed to store blacklisted token in database: {e}")
        # Token is still in memory cache, so revocation works for this instance


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a token is blacklisted.

    Uses in-memory cache for fast lookups, falls back to database
    for tokens not in cache (e.g., after server restart).

    Args:
        jti: JWT ID to check

    Returns:
        True if blacklisted
    """
    from src.api.database.connection import get_db_session
    from src.api.database.models import TokenBlacklist

    # Fast path: check in-memory cache
    if jti in _blacklisted_tokens:
        return True

    # Slow path: check database (for persistence across restarts)
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            )
            entry = result.scalar_one_or_none()

            if entry is not None:
                # Add to cache for future lookups
                _blacklisted_tokens.add(jti)
                return True
    except Exception as e:
        logger.error(f"Failed to check token blacklist in database: {e}")
        # Conservative: if we can't check DB, rely on memory cache only

    return False


async def cleanup_expired_blacklist() -> int:
    """
    Remove expired tokens from blacklist.

    Deletes tokens from PostgreSQL where expires_at is in the past.
    Should be called periodically (e.g., hourly) via scheduled task.

    Returns:
        Number of tokens removed
    """
    from src.api.database.connection import get_db_session
    from src.api.database.models import TokenBlacklist

    now = datetime.utcnow()
    deleted_count = 0

    try:
        async with get_db_session() as db:
            # Get expired JTIs before deletion (for cache cleanup)
            result = await db.execute(
                select(TokenBlacklist.jti).where(TokenBlacklist.expires_at < now)
            )
            expired_jtis = [row[0] for row in result.fetchall()]

            # Delete from database
            if expired_jtis:
                delete_result = await db.execute(
                    delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
                )
                await db.commit()
                deleted_count = delete_result.rowcount

                # Remove from in-memory cache
                for jti in expired_jtis:
                    _blacklisted_tokens.discard(jti)

                logger.info(f"Cleaned up {deleted_count} expired blacklist entries")
    except Exception as e:
        logger.error(f"Failed to cleanup expired blacklist entries: {e}")

    return deleted_count


async def load_blacklist_cache() -> int:
    """
    Load blacklisted tokens from database into memory cache.

    Should be called during application startup to populate cache
    with tokens blacklisted before the current instance started.

    Returns:
        Number of tokens loaded into cache
    """
    from src.api.database.connection import get_db_session
    from src.api.database.models import TokenBlacklist

    now = datetime.utcnow()
    loaded_count = 0

    try:
        async with get_db_session() as db:
            # Load only non-expired tokens
            result = await db.execute(
                select(TokenBlacklist.jti).where(TokenBlacklist.expires_at >= now)
            )
            for row in result.fetchall():
                _blacklisted_tokens.add(row[0])
                loaded_count += 1

            logger.info(f"Loaded {loaded_count} blacklisted tokens into cache")
    except Exception as e:
        logger.error(f"Failed to load blacklist cache from database: {e}")

    return loaded_count
