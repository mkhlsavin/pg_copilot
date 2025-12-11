"""
Tests for Authentication Router.

Tests for POST /auth/token, POST /auth/refresh, DELETE /auth/logout,
POST /auth/api-keys, GET /auth/api-keys, DELETE /auth/api-keys/{key_id},
GET /auth/oauth/providers, GET /auth/oauth/{provider},
GET /auth/oauth/{provider}/callback, POST /auth/ldap
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User, ApiKey, UserRole
from src.api.auth.api_keys import generate_api_key, hash_api_key
from tests.api.conftest import API_V1_PREFIX


class TestLoginEndpoint:
    """Tests for POST /auth/token endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        async_client: AsyncClient,
        test_user: User,
    ):
        """Test successful login returns tokens."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={"username": "testuser", "password": "testpassword123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_invalid_username(self, async_client: AsyncClient):
        """Test login with non-existent username."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={"username": "nonexistent", "password": "password123"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        test_user: User,
    ):
        """Test login with wrong password."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        async_client: AsyncClient,
        inactive_user: User,
    ):
        """Test login with inactive user."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={"username": "inactive", "password": "inactivepassword123"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_empty_username(self, async_client: AsyncClient):
        """Test login with empty username."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={"username": "", "password": "password123"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, async_client: AsyncClient):
        """Test login with missing fields."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/token",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestRefreshTokenEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        refresh_token_fixture: str,
    ):
        """Test successful token refresh."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": refresh_token_fixture},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different
        assert data["refresh_token"] != refresh_token_fixture

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_empty_token(self, async_client: AsyncClient):
        """Test refresh with empty token."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": ""},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutEndpoint:
    """Tests for DELETE /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful logout."""
        response = await async_client.delete(
            f"{API_V1_PREFIX}/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, async_client_no_auth: AsyncClient):
        """Test logout without authentication."""
        response = await async_client_no_auth.delete(f"{API_V1_PREFIX}/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestApiKeyEndpoints:
    """Tests for API key management endpoints."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful API key creation."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/api-keys",
            headers=auth_headers,
            json={
                "name": "Test API Key",
                "expires_days": 30,
                "scopes": ["scenarios:read"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test API Key"
        assert "key" in data  # Key only returned on creation
        assert "prefix" in data
        assert len(data["prefix"]) == 8

    @pytest.mark.asyncio
    async def test_create_api_key_default_values(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test API key creation with default values."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/api-keys",
            headers=auth_headers,
            json={"name": "Default API Key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Default API Key"
        assert data["scopes"] == ["scenarios:read", "query:execute"]

    @pytest.mark.asyncio
    async def test_create_api_key_unauthenticated(self, async_client_no_auth: AsyncClient):
        """Test API key creation without authentication."""
        response = await async_client_no_auth.post(
            f"{API_V1_PREFIX}/auth/api-keys",
            json={"name": "Test Key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_api_keys_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test listing API keys."""
        # Create an API key first
        full_key, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Existing Key",
            key_hash=key_hash,
            prefix=prefix,
            scopes=["scenarios:read"],
            created_at=datetime.utcnow(),
        )
        test_session.add(api_key)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/auth/api-keys",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Key value should not be in list response
        for key in data:
            assert "key" not in key or key.get("key") is None

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test listing API keys when none exist."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/auth/api-keys",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test revoking an API key."""
        # Create an API key first
        full_key, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Key to Revoke",
            key_hash=key_hash,
            prefix=prefix,
            scopes=["scenarios:read"],
            created_at=datetime.utcnow(),
        )
        test_session.add(api_key)
        await test_session.commit()

        response = await async_client.delete(
            f"{API_V1_PREFIX}/auth/api-keys/{api_key.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "revoked" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test revoking non-existent API key."""
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"{API_V1_PREFIX}/auth/api-keys/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_revoke_api_key_invalid_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test revoking API key with invalid ID format."""
        response = await async_client.delete(
            f"{API_V1_PREFIX}/auth/api-keys/invalid-id",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_revoke_other_user_api_key(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test that user cannot revoke another user's API key."""
        # Create API key for admin user
        full_key, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            id=uuid.uuid4(),
            user_id=admin_user.id,  # Belongs to admin, not test_user
            name="Admin's Key",
            key_hash=key_hash,
            prefix=prefix,
            scopes=["scenarios:read"],
            created_at=datetime.utcnow(),
        )
        test_session.add(api_key)
        await test_session.commit()

        # Try to revoke with test_user's credentials
        response = await async_client.delete(
            f"{API_V1_PREFIX}/auth/api-keys/{api_key.id}",
            headers=auth_headers,  # test_user's headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestOAuthEndpoints:
    """Tests for OAuth endpoints."""

    @pytest.mark.asyncio
    async def test_list_oauth_providers(self, async_client: AsyncClient):
        """Test listing OAuth providers."""
        response = await async_client.get(f"{API_V1_PREFIX}/auth/oauth/providers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

        # Check expected providers exist
        provider_names = [p["name"] for p in data]
        assert "github" in provider_names
        assert "google" in provider_names

        # All should be disabled (not yet integrated)
        for provider in data:
            assert provider["enabled"] is False

    @pytest.mark.asyncio
    async def test_oauth_start_not_implemented(self, async_client: AsyncClient):
        """Test OAuth start returns not implemented."""
        response = await async_client.get(f"{API_V1_PREFIX}/auth/oauth/github")

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert "not yet integrated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_callback_not_implemented(self, async_client: AsyncClient):
        """Test OAuth callback returns not implemented."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/auth/oauth/github/callback",
            params={"code": "test_code", "state": "test_state"},
        )

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestLDAPEndpoint:
    """Tests for LDAP authentication endpoint."""

    @pytest.mark.asyncio
    async def test_ldap_login_not_implemented(self, async_client: AsyncClient):
        """Test LDAP login returns not implemented."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/auth/ldap",
            json={"username": "ldapuser", "password": "ldappassword"},
        )

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert "not yet integrated" in response.json()["detail"].lower()
