"""
Authentication Router.

Provides endpoints for JWT authentication, API keys, OAuth, and LDAP.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User, UserRole
from src.api.database.repositories.user_repo import UserRepository
from src.api.database.repositories.api_key_repo import ApiKeyRepository
from src.api.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_jti,
    blacklist_token,
    TokenError,
)
from src.api.auth.api_keys import generate_api_key, calculate_expiration
from src.api.dependencies import get_current_user, get_current_active_user

logger = logging.getLogger("api.routers.auth")
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# Request/Response Models
class TokenRequest(BaseModel):
    """Token request model."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class ApiKeyCreate(BaseModel):
    """API key creation request model."""
    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(default=365, ge=1, le=3650)
    scopes: List[str] = Field(default_factory=lambda: ["scenarios:read", "query:execute"])


class ApiKeyResponse(BaseModel):
    """API key response model."""
    id: str
    name: str
    key: Optional[str] = None  # Only returned on creation
    prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeyListItem(BaseModel):
    """API key list item (without secret)."""
    id: str
    name: str
    prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    is_revoked: bool


class LDAPAuthRequest(BaseModel):
    """LDAP authentication request model."""
    username: str
    password: str


class OAuthProviderInfo(BaseModel):
    """OAuth provider information model."""
    name: str
    enabled: bool
    authorize_url: Optional[str] = None


# Endpoints
@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Get JWT token",
    description="Authenticate with username/password and get JWT tokens.",
)
async def login(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Args:
        request: Username and password

    Returns:
        Access and refresh tokens
    """
    user_repo = UserRepository(db)

    # Find user by username
    user = await user_repo.get_by_username(request.username)

    if not user:
        logger.warning(f"Login attempt for non-existent user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        scopes=["scenarios:read", "query:execute"],
        role=user.role.value,
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    logger.info(f"User logged in: {request.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh JWT token",
    description="Get new access token using refresh token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token.

    Args:
        request: Refresh token

    Returns:
        New access and refresh tokens
    """
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token, token_type="refresh")

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(payload.sub))

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Blacklist old refresh token
        old_jti = get_token_jti(request.refresh_token)
        await blacklist_token(old_jti)

        # Create new tokens
        access_token = create_access_token(
            user_id=str(user.id),
            scopes=["scenarios:read", "query:execute"],
            role=user.role.value,
        )
        new_refresh_token = create_refresh_token(user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800,
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
        )


@router.delete(
    "/logout",
    summary="Logout",
    description="Invalidate current tokens.",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Logout and invalidate tokens.

    Args:
        request: Current request with auth token

    Returns:
        Success message
    """
    # Extract token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        jti = get_token_jti(token)
        if jti:
            await blacklist_token(jti)

    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logged out successfully"}


# API Keys
@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    summary="Create API key",
    description="Generate a new API key for programmatic access.",
)
async def create_api_key(
    request: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Create a new API key.

    Args:
        request: API key creation parameters

    Returns:
        Created API key (key value only shown once)
    """
    api_key_repo = ApiKeyRepository(db)

    # Generate key
    full_key, prefix, key_hash = generate_api_key()
    expires_at = calculate_expiration(request.expires_days)

    # Store in database
    api_key = await api_key_repo.create(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        prefix=prefix,
        scopes=request.scopes,
        expires_at=expires_at,
    )

    await db.commit()

    logger.info(f"API key created: {request.name} for user {current_user.username}")

    return ApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=full_key,  # Return key only on creation
        prefix=prefix,
        scopes=api_key.scopes or [],
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "/api-keys",
    response_model=List[ApiKeyListItem],
    summary="List API keys",
    description="Get all API keys for the current user.",
)
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApiKeyListItem]:
    """
    List all API keys for current user.

    Returns:
        List of API keys (without key values)
    """
    api_key_repo = ApiKeyRepository(db)

    keys = await api_key_repo.get_by_user(current_user.id, include_revoked=True)

    return [
        ApiKeyListItem(
            id=str(key.id),
            name=key.name,
            prefix=key.prefix,
            scopes=key.scopes or [],
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            is_revoked=key.is_revoked,
        )
        for key in keys
    ]


@router.delete(
    "/api-keys/{key_id}",
    summary="Revoke API key",
    description="Revoke an API key.",
)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Revoke an API key.

    Args:
        key_id: API key ID to revoke

    Returns:
        Success message
    """
    api_key_repo = ApiKeyRepository(db)

    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format",
        )

    # Get the key to verify ownership
    api_key = await api_key_repo.get_by_id(key_uuid)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this API key",
        )

    # Revoke the key
    await api_key_repo.revoke(key_uuid)
    await db.commit()

    logger.info(f"API key revoked: {key_id} by user {current_user.username}")

    return {"message": "API key revoked successfully"}


# OAuth
@router.get(
    "/oauth/providers",
    response_model=List[OAuthProviderInfo],
    summary="List OAuth providers",
    description="Get list of available OAuth providers.",
)
async def list_oauth_providers() -> List[OAuthProviderInfo]:
    """
    List available OAuth providers.

    Returns:
        List of OAuth provider info
    """
    # OAuth providers - infrastructure ready, not yet integrated
    return [
        OAuthProviderInfo(name="github", enabled=False),
        OAuthProviderInfo(name="google", enabled=False),
        OAuthProviderInfo(name="gitlab", enabled=False),
        OAuthProviderInfo(name="keycloak", enabled=False),
    ]


@router.get(
    "/oauth/{provider}",
    summary="Start OAuth flow",
    description="Redirect to OAuth provider for authentication.",
)
async def oauth_start(provider: str) -> Dict[str, str]:
    """
    Start OAuth authentication flow.

    Args:
        provider: OAuth provider name

    Returns:
        Redirect URL
    """
    # OAuth infrastructure is ready in src/api/auth/oauth.py
    # but not yet integrated with external providers
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth with {provider} not yet integrated. See docs/TECHNICAL_DEBT.md",
    )


@router.get(
    "/oauth/{provider}/callback",
    summary="OAuth callback",
    description="Handle OAuth callback from provider.",
)
async def oauth_callback(
    provider: str,
    code: str,
    state: Optional[str] = None,
) -> TokenResponse:
    """
    Handle OAuth callback.

    Args:
        provider: OAuth provider name
        code: Authorization code from provider
        state: State parameter for CSRF protection

    Returns:
        JWT tokens
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth callback for {provider} not yet integrated. See docs/TECHNICAL_DEBT.md",
    )


# LDAP
@router.post(
    "/ldap",
    response_model=TokenResponse,
    summary="LDAP authentication",
    description="Authenticate using LDAP/Active Directory.",
)
async def ldap_login(request: LDAPAuthRequest) -> TokenResponse:
    """
    Authenticate using LDAP.

    Args:
        request: LDAP credentials

    Returns:
        JWT tokens
    """
    # LDAP infrastructure is ready in src/api/auth/ldap_auth.py
    # but not yet integrated with LDAP servers
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="LDAP authentication not yet integrated. See docs/TECHNICAL_DEBT.md",
    )
