"""
Authentication Middleware.

Provides FastAPI dependencies for authentication and authorization.
"""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader

from src.api.auth.jwt_handler import (
    TokenPayload,
    TokenError,
    verify_token,
    is_token_blacklisted,
)
from src.api.auth.api_keys import ApiKeyRepository, ApiKeyInfo
from src.api.auth.permissions import Permission, Role, has_permission
from src.api.database.models import User

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthContext:
    """Authentication context containing user info and permissions."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        role: Optional[Role] = None,
        scopes: Optional[List[str]] = None,
        auth_method: str = "none",
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.scopes = scopes or []
        self.auth_method = auth_method  # "jwt", "api_key", "none"

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return has_permission(self.role, permission, self.scopes)


async def get_auth_context(
    request: Request,
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> AuthContext:
    """
    Get authentication context from request.

    Supports both JWT Bearer tokens and API keys.
    Returns unauthenticated context if no credentials provided.

    Args:
        request: FastAPI request
        bearer_token: JWT Bearer token
        api_key: API key from header

    Returns:
        Authentication context
    """
    # Try JWT Bearer token first
    if bearer_token and bearer_token.credentials:
        try:
            payload = verify_token(bearer_token.credentials, "access")

            # Check if token is blacklisted
            if await is_token_blacklisted(payload.jti):
                logger.warning(f"Blacklisted token used: {payload.jti}")
                return AuthContext()

            return AuthContext(
                user_id=payload.sub,
                role=Role(payload.role) if payload.role else None,
                scopes=payload.scopes,
                auth_method="jwt",
            )

        except TokenError as e:
            logger.debug(f"JWT verification failed: {e.message}")
            # Don't raise - fall through to check API key

    # Try API key
    if api_key:
        api_key_repo = ApiKeyRepository()
        key_info = await api_key_repo.validate(api_key)

        if key_info:
            return AuthContext(
                user_id=key_info.id,  # API key ID as user ID
                scopes=key_info.scopes,
                auth_method="api_key",
            )
        else:
            logger.debug("API key validation failed")

    # No valid credentials
    return AuthContext()


async def require_auth(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """
    Require authentication.

    Raises 401 if not authenticated.

    Args:
        auth: Authentication context

    Returns:
        Authenticated context

    Raises:
        HTTPException: If not authenticated
    """
    if not auth.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


def require_permission(permission: Permission):
    """
    Factory for permission requirement dependencies.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_permission(Permission.ADMIN_ALL))])

    Args:
        permission: Required permission

    Returns:
        FastAPI dependency function
    """
    async def check_permission(auth: AuthContext = Depends(require_auth)):
        if not auth.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return auth

    return check_permission


def require_any_permission(*permissions: Permission):
    """
    Factory for requiring any of multiple permissions.

    Args:
        permissions: Required permissions (any one is sufficient)

    Returns:
        FastAPI dependency function
    """
    async def check_permissions(auth: AuthContext = Depends(require_auth)):
        for permission in permissions:
            if auth.has_permission(permission):
                return auth

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: one of {[p.value for p in permissions]} required",
        )

    return check_permissions


def require_role(*roles: Role):
    """
    Factory for role requirement dependencies.

    Args:
        roles: Required roles (any one is sufficient)

    Returns:
        FastAPI dependency function
    """
    async def check_role(auth: AuthContext = Depends(require_auth)):
        if auth.role in roles or auth.role == Role.ADMIN:
            return auth

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: one of {[r.value for r in roles]}",
        )

    return check_role


# Convenience dependencies
async def get_current_user(auth: AuthContext = Depends(require_auth)) -> AuthContext:
    """Get current authenticated user."""
    return auth


async def get_optional_user(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Get current user if authenticated, None otherwise."""
    return auth


# Admin-only dependency
require_admin = require_role(Role.ADMIN)

# Analyst or higher dependency
require_analyst = require_role(Role.ANALYST, Role.REVIEWER, Role.ADMIN)

# Reviewer or higher dependency
require_reviewer = require_role(Role.REVIEWER, Role.ADMIN)
