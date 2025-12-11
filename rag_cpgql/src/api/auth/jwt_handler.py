"""
JWT Token Handler.

Provides JWT token creation, verification, and management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from src.api.config import get_settings


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
# In production, this should use PostgreSQL or Redis

_blacklisted_tokens: set[str] = set()


async def blacklist_token(jti: str) -> None:
    """
    Add a token to the blacklist.

    Args:
        jti: JWT ID to blacklist
    """
    # TODO: Store in PostgreSQL TokenBlacklist table
    _blacklisted_tokens.add(jti)


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        jti: JWT ID to check

    Returns:
        True if blacklisted
    """
    # TODO: Check PostgreSQL TokenBlacklist table
    return jti in _blacklisted_tokens


async def cleanup_expired_blacklist() -> int:
    """
    Remove expired tokens from blacklist.

    Returns:
        Number of tokens removed
    """
    # TODO: Implement cleanup of expired tokens from PostgreSQL
    return 0
