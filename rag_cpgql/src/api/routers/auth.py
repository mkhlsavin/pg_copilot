"""
Authentication Router.

Provides endpoints for JWT authentication, API keys, OAuth, and LDAP.
"""

import logging
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
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
from src.api.auth.oauth import (
    get_oauth_manager,
    setup_oauth_providers,
    OAuthError,
    OAuthUser,
)
from src.api.auth.ldap_auth import (
    get_ldap_authenticator,
    setup_ldap_authenticator,
    LDAPError,
)
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


# OAuth state storage (in production, use Redis or database)
_oauth_states: Dict[str, Dict[str, Any]] = {}


# OAuth
@router.get(
    "/oauth/providers",
    response_model=List[OAuthProviderInfo],
    summary="List OAuth providers",
    description="Get list of available OAuth providers.",
)
async def list_oauth_providers(request: Request) -> List[OAuthProviderInfo]:
    """
    List available OAuth providers.

    Returns:
        List of OAuth provider info with authorization URLs
    """
    manager = get_oauth_manager()
    providers = []

    for name in ["github", "google", "gitlab", "keycloak"]:
        provider = manager.get_provider(name)
        if provider:
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)
            redirect_uri = str(request.url_for("oauth_callback", provider=name))
            auth_url = provider.get_authorization_url(redirect_uri, state)

            providers.append(OAuthProviderInfo(
                name=name,
                enabled=True,
                authorize_url=auth_url,
            ))
        else:
            providers.append(OAuthProviderInfo(name=name, enabled=False))

    return providers


@router.get(
    "/oauth/{provider}",
    summary="Start OAuth flow",
    description="Redirect to OAuth provider for authentication.",
)
async def oauth_start(provider: str, request: Request) -> RedirectResponse:
    """
    Start OAuth authentication flow.

    Args:
        provider: OAuth provider name

    Returns:
        Redirect to OAuth provider
    """
    manager = get_oauth_manager()
    oauth_provider = manager.get_provider(provider)

    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' not configured. "
                   f"Available providers: {manager.list_providers()}",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))

    # Store state (in production, use Redis with TTL)
    _oauth_states[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri,
    }

    auth_url = oauth_provider.get_authorization_url(redirect_uri, state)
    logger.info(f"Starting OAuth flow for provider: {provider}")

    return RedirectResponse(url=auth_url)


@router.get(
    "/oauth/{provider}/callback",
    response_model=TokenResponse,
    summary="OAuth callback",
    description="Handle OAuth callback from provider.",
)
async def oauth_callback(
    provider: str,
    request: Request,
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
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
    # Verify state (CSRF protection)
    if not state or state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    state_data = _oauth_states.pop(state)
    if state_data["provider"] != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch in state",
        )

    manager = get_oauth_manager()
    oauth_provider = manager.get_provider(provider)

    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' not configured",
        )

    try:
        # Exchange code for tokens
        tokens = await oauth_provider.exchange_code(code, state_data["redirect_uri"])
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token in OAuth response",
            )

        # Get user info from provider
        oauth_user = await oauth_provider.get_user_info(access_token)

        # Find or create user in database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_oauth(provider, oauth_user.external_id)

        if not user:
            # Create new user from OAuth data
            user = await user_repo.create_oauth_user(
                provider=provider,
                external_id=oauth_user.external_id,
                username=oauth_user.username,
                email=oauth_user.email,
                display_name=oauth_user.name,
            )
            await db.commit()
            logger.info(f"Created new user from OAuth: {oauth_user.username}")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        # Create JWT tokens
        jwt_access_token = create_access_token(
            user_id=str(user.id),
            scopes=["scenarios:read", "query:execute"],
            role=user.role.value,
        )
        refresh_token = create_refresh_token(user_id=str(user.id))

        logger.info(f"OAuth login successful: {oauth_user.username} via {provider}")

        return TokenResponse(
            access_token=jwt_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,
        )

    except OAuthError as e:
        logger.error(f"OAuth error for {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# LDAP
@router.post(
    "/ldap",
    response_model=TokenResponse,
    summary="LDAP authentication",
    description="Authenticate using LDAP/Active Directory.",
)
async def ldap_login(
    request: LDAPAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate using LDAP.

    Args:
        request: LDAP credentials

    Returns:
        JWT tokens
    """
    authenticator = get_ldap_authenticator()

    if not authenticator or not authenticator.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP authentication is not configured. "
                   "Set LDAP_SERVER and other LDAP_* environment variables.",
        )

    try:
        # Authenticate against LDAP
        ldap_user = await authenticator.authenticate(request.username, request.password)

        if not ldap_user:
            logger.warning(f"LDAP authentication failed for user: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid LDAP credentials",
            )

        # Find or create user in database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_ldap_dn(ldap_user.dn)

        if not user:
            # Map LDAP groups to application role
            role_str = authenticator.map_groups_to_role(ldap_user.groups)
            # Convert string role to UserRole enum
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.ANALYST  # Default fallback

            # Create new user from LDAP data
            user = await user_repo.create_ldap_user(
                ldap_dn=ldap_user.dn,
                username=ldap_user.username,
                email=ldap_user.email,
                display_name=ldap_user.display_name,
                role=role,
            )
            await db.commit()
            logger.info(f"Created new user from LDAP: {ldap_user.username}")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        # Create JWT tokens
        access_token = create_access_token(
            user_id=str(user.id),
            scopes=["scenarios:read", "query:execute"],
            role=user.role.value,
        )
        refresh_token = create_refresh_token(user_id=str(user.id))

        logger.info(f"LDAP login successful: {ldap_user.username}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,
        )

    except LDAPError as e:
        logger.error(f"LDAP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get(
    "/ldap/status",
    summary="LDAP status",
    description="Check LDAP connection status.",
)
async def ldap_status() -> Dict[str, Any]:
    """
    Check LDAP connection status.

    Returns:
        LDAP status information
    """
    authenticator = get_ldap_authenticator()

    if not authenticator:
        return {
            "enabled": False,
            "available": False,
            "message": "LDAP not configured",
        }

    if not authenticator.is_available:
        return {
            "enabled": True,
            "available": False,
            "message": "LDAP configured but ldap3 library not installed",
        }

    # Test connection
    try:
        connected = await authenticator.test_connection()
        return {
            "enabled": True,
            "available": True,
            "connected": connected,
            "server": authenticator.config.server,
        }
    except Exception as e:
        return {
            "enabled": True,
            "available": True,
            "connected": False,
            "error": str(e),
        }
