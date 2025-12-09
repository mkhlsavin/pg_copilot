"""
Authentication Models.

Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Token Models
class TokenRequest(BaseModel):
    """Request for JWT token."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Response with JWT tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Request to refresh token."""

    refresh_token: str


# API Key Models
class ApiKeyCreate(BaseModel):
    """Request to create API key."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(default=365, ge=1, le=3650)
    scopes: List[str] = Field(default=["scenarios:read", "query:execute"])


class ApiKeyResponse(BaseModel):
    """Response with API key info."""

    id: UUID
    name: str
    prefix: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_revoked: bool


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response when API key is created (includes full key)."""

    key: str  # Full API key, only shown once


# User Models
class UserCreate(BaseModel):
    """Request to create user."""

    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)
    role: str = "analyst"


class UserUpdate(BaseModel):
    """Request to update user."""

    email: Optional[EmailStr] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    """Response with user info."""

    id: UUID
    username: str
    email: Optional[str]
    role: str
    auth_provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PasswordChange(BaseModel):
    """Request to change password."""

    old_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Request to reset password (admin)."""

    new_password: str = Field(..., min_length=8)


# OAuth Models
class OAuthProviderInfo(BaseModel):
    """OAuth provider information."""

    name: str
    display_name: str
    enabled: bool


class OAuthLoginResponse(BaseModel):
    """Response from OAuth login."""

    authorization_url: str
    state: str


# LDAP Models
class LDAPLoginRequest(BaseModel):
    """Request for LDAP login."""

    username: str
    password: str
