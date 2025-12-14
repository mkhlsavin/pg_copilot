"""
OAuth2/OIDC Authentication Module.

Provides OAuth authentication for various providers (GitHub, GitLab, Google, Keycloak).

STATUS: IMPLEMENTED - Pending API route integration
This module provides complete OAuth authentication infrastructure.
Integration into API routes is pending. See docs/TECHNICAL_DEBT.md
for integration tasks.

Usage:
    from src.api.auth.oauth import setup_oauth_providers, get_oauth_manager

    # Setup from configuration
    manager = setup_oauth_providers(oauth_config)

    # Get authorization URL
    provider = manager.get_provider("github")
    auth_url = provider.get_authorization_url(redirect_uri, state)

    # Exchange code for user info
    tokens = await provider.exchange_code(code, redirect_uri)
    user = await provider.get_user_info(tokens["access_token"])
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from src.api.config import OAuthProviderConfig

logger = logging.getLogger("api.auth.oauth")


class OAuthUser(BaseModel):
    """OAuth user information."""

    provider: str
    external_id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    raw_data: Dict[str, Any] = {}


class OAuthProvider(ABC):
    """
    Base OAuth2/OIDC provider.

    Handles OAuth flow for external authentication.
    """

    def __init__(self, config: OAuthProviderConfig):
        """
        Initialize the OAuth provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def authorize_url(self) -> str:
        """Authorization endpoint URL."""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """Token endpoint URL."""
        pass

    @property
    @abstractmethod
    def userinfo_url(self) -> str:
        """User info endpoint URL."""
        pass

    @property
    def default_scopes(self) -> List[str]:
        """Default OAuth scopes."""
        return ["openid", "profile", "email"]

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """
        Generate authorization URL.

        Args:
            redirect_uri: Callback URL
            state: CSRF state token
            scopes: OAuth scopes

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(scopes or self.default_scopes),
        }
        return f"{self.authorize_url}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code
            redirect_uri: Callback URL

        Returns:
            Token response

        Raises:
            OAuthError: If exchange fails
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"OAuth token exchange failed: {e}")
            raise OAuthError(f"Token exchange failed: {e}")

    async def get_user_info(self, access_token: str) -> OAuthUser:
        """
        Get user information from provider.

        Args:
            access_token: OAuth access token

        Returns:
            OAuth user information

        Raises:
            OAuthError: If request fails
        """
        try:
            response = await self.client.get(
                self.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_user_info(data)
        except httpx.HTTPError as e:
            logger.error(f"OAuth user info request failed: {e}")
            raise OAuthError(f"User info request failed: {e}")

    @abstractmethod
    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        """Parse provider-specific user info response."""
        pass

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class OAuthError(Exception):
    """OAuth authentication error."""

    pass


class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider."""

    @property
    def name(self) -> str:
        return "github"

    @property
    def authorize_url(self) -> str:
        return "https://github.com/login/oauth/authorize"

    @property
    def token_url(self) -> str:
        return "https://github.com/login/oauth/access_token"

    @property
    def userinfo_url(self) -> str:
        return "https://api.github.com/user"

    @property
    def default_scopes(self) -> List[str]:
        return ["read:user", "user:email"]

    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        return OAuthUser(
            provider=self.name,
            external_id=str(data.get("id")),
            username=data.get("login", ""),
            email=data.get("email"),
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            raw_data=data,
        )


class GitLabOAuth(OAuthProvider):
    """GitLab OAuth provider."""

    def __init__(self, config: OAuthProviderConfig, server_url: str = "https://gitlab.com"):
        super().__init__(config)
        self.server_url = server_url.rstrip("/")

    @property
    def name(self) -> str:
        return "gitlab"

    @property
    def authorize_url(self) -> str:
        return f"{self.server_url}/oauth/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.server_url}/oauth/token"

    @property
    def userinfo_url(self) -> str:
        return f"{self.server_url}/api/v4/user"

    @property
    def default_scopes(self) -> List[str]:
        return ["read_user", "openid", "profile", "email"]

    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        return OAuthUser(
            provider=self.name,
            external_id=str(data.get("id")),
            username=data.get("username", ""),
            email=data.get("email"),
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            raw_data=data,
        )


class GoogleOAuth(OAuthProvider):
    """Google OAuth/OIDC provider."""

    @property
    def name(self) -> str:
        return "google"

    @property
    def authorize_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"

    @property
    def userinfo_url(self) -> str:
        return "https://openidconnect.googleapis.com/v1/userinfo"

    @property
    def default_scopes(self) -> List[str]:
        return ["openid", "profile", "email"]

    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        return OAuthUser(
            provider=self.name,
            external_id=data.get("sub", ""),
            username=data.get("email", "").split("@")[0],
            email=data.get("email"),
            name=data.get("name"),
            avatar_url=data.get("picture"),
            raw_data=data,
        )


class KeycloakOAuth(OAuthProvider):
    """Keycloak OIDC provider."""

    def __init__(
        self,
        config: OAuthProviderConfig,
        server_url: str,
        realm: str,
    ):
        super().__init__(config)
        self.server_url = server_url.rstrip("/")
        self.realm = realm

    @property
    def name(self) -> str:
        return "keycloak"

    @property
    def base_url(self) -> str:
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect"

    @property
    def authorize_url(self) -> str:
        return f"{self.base_url}/auth"

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/token"

    @property
    def userinfo_url(self) -> str:
        return f"{self.base_url}/userinfo"

    @property
    def default_scopes(self) -> List[str]:
        return ["openid", "profile", "email"]

    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        return OAuthUser(
            provider=self.name,
            external_id=data.get("sub", ""),
            username=data.get("preferred_username", ""),
            email=data.get("email"),
            name=data.get("name"),
            raw_data=data,
        )


class OAuthManager:
    """
    OAuth provider manager.

    Manages multiple OAuth providers.
    """

    def __init__(self):
        """Initialize the OAuth manager."""
        self.providers: Dict[str, OAuthProvider] = {}

    def register_provider(self, provider: OAuthProvider) -> None:
        """
        Register an OAuth provider.

        Args:
            provider: OAuth provider instance
        """
        self.providers[provider.name] = provider
        logger.info(f"Registered OAuth provider: {provider.name}")

    def get_provider(self, name: str) -> Optional[OAuthProvider]:
        """
        Get an OAuth provider by name.

        Args:
            name: Provider name

        Returns:
            OAuth provider or None
        """
        return self.providers.get(name)

    def list_providers(self) -> List[str]:
        """
        List available OAuth providers.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())

    async def close_all(self):
        """Close all provider HTTP clients."""
        for provider in self.providers.values():
            await provider.close()


# Global OAuth manager
_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    """Get the global OAuth manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager


def setup_oauth_providers(config: Dict[str, OAuthProviderConfig]) -> OAuthManager:
    """
    Setup OAuth providers from configuration.

    Args:
        config: Provider configurations

    Returns:
        Configured OAuth manager
    """
    manager = get_oauth_manager()

    for name, provider_config in config.items():
        if not provider_config.client_id or not provider_config.client_secret:
            logger.warning(f"Skipping OAuth provider {name}: missing credentials")
            continue

        provider: Optional[OAuthProvider] = None

        if name == "github":
            provider = GitHubOAuth(provider_config)
        elif name == "gitlab":
            server_url = getattr(provider_config, "server_url", "https://gitlab.com")
            provider = GitLabOAuth(provider_config, server_url)
        elif name == "google":
            provider = GoogleOAuth(provider_config)
        elif name == "keycloak":
            server_url = getattr(provider_config, "server_url", "")
            realm = getattr(provider_config, "realm", "master")
            if server_url:
                provider = KeycloakOAuth(provider_config, server_url, realm)
            else:
                logger.warning("Skipping Keycloak: missing server_url")

        if provider:
            manager.register_provider(provider)

    return manager
