"""
FastAPI Dependencies Module.

Provides common dependencies for FastAPI routes.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User, UserRole
from src.api.database.repositories.user_repo import UserRepository
from src.api.database.repositories.api_key_repo import ApiKeyRepository
from src.api.database.repositories.session_repo import SessionRepository
from src.api.database.repositories.job_repo import JobRepository
from src.api.services.user_service import UserService
from src.api.services.session_service import SessionService
from src.api.services.job_service import JobService
from src.api.auth.jwt_handler import decode_token
from src.api.auth.api_keys import validate_api_key
from src.api.auth.permissions import Permission, has_permission, Role

logger = logging.getLogger("api.dependencies")


# Repository dependencies
async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


async def get_api_key_repo(db: AsyncSession = Depends(get_db)) -> ApiKeyRepository:
    """Get API key repository."""
    return ApiKeyRepository(db)


async def get_session_repo(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    """Get session repository."""
    return SessionRepository(db)


async def get_job_repo(db: AsyncSession = Depends(get_db)) -> JobRepository:
    """Get job repository."""
    return JobRepository(db)


# Service dependencies
async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserService:
    """Get user service."""
    return UserService(user_repo)


async def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
) -> SessionService:
    """Get session service."""
    return SessionService(session_repo)


async def get_job_service(
    job_repo: JobRepository = Depends(get_job_repo),
) -> JobService:
    """Get job service."""
    return JobService(job_repo)


# Authentication dependencies
async def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from JWT token or API key (optional).

    Returns None if no valid authentication is provided.
    """
    user_repo = UserRepository(db)
    api_key_repo = ApiKeyRepository(db)

    # Try JWT token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = decode_token(token)
            if payload:
                user = await user_repo.get_by_id(UUID(payload.sub))
                if user and user.is_active:
                    return user
        except Exception as e:
            logger.debug(f"JWT validation failed: {e}")

    # Try API key
    if x_api_key:
        try:
            user = await validate_api_key(x_api_key, api_key_repo, user_repo)
            if user:
                return user
        except Exception as e:
            logger.debug(f"API key validation failed: {e}")

    return None


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """
    Get current user (required).

    Raises HTTPException if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Raises HTTPException if user is not active.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return user


# Permission dependencies
def require_permission(permission: Permission):
    """
    Create a dependency that requires a specific permission.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """

    async def dependency(user: User = Depends(get_current_active_user)) -> User:
        role = Role(user.role.value)
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return dependency


def require_role(min_role: UserRole):
    """
    Create a dependency that requires a minimum role level.

    Args:
        min_role: Minimum required role

    Returns:
        Dependency function
    """
    role_hierarchy = {
        UserRole.VIEWER: 0,
        UserRole.ANALYST: 1,
        UserRole.REVIEWER: 2,
        UserRole.ADMIN: 3,
    }

    async def dependency(user: User = Depends(get_current_active_user)) -> User:
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(min_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Minimum role required: {min_role.value}",
            )
        return user

    return dependency


# Shorthand dependencies
RequireAdmin = require_role(UserRole.ADMIN)
RequireReviewer = require_role(UserRole.REVIEWER)
RequireAnalyst = require_role(UserRole.ANALYST)

RequireQueryPermission = require_permission(Permission.QUERY_EXECUTE)
RequireReviewPermission = require_permission(Permission.REVIEW_EXECUTE)
RequireSessionPermission = require_permission(Permission.SESSIONS_WRITE)


# Utility dependencies
async def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


async def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"
