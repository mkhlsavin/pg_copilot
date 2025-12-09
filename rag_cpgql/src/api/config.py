"""
API Configuration Module.

Handles all API-specific configuration including auth, rate limiting, CORS, and database settings.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class JWTConfig(BaseModel):
    """JWT authentication configuration."""

    secret_key: str = Field(default="change-me-in-production-use-64-chars-minimum")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration."""

    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    scopes: List[str] = Field(default_factory=list)


class OAuthConfig(BaseModel):
    """OAuth2/OIDC configuration."""

    github: OAuthProviderConfig = Field(default_factory=OAuthProviderConfig)
    google: OAuthProviderConfig = Field(default_factory=OAuthProviderConfig)
    gitlab: OAuthProviderConfig = Field(default_factory=OAuthProviderConfig)
    keycloak: OAuthProviderConfig = Field(default_factory=OAuthProviderConfig)


class LDAPConfig(BaseModel):
    """LDAP/Active Directory configuration."""

    enabled: bool = False
    server: str = ""
    port: int = 389
    use_ssl: bool = False
    base_dn: str = ""
    user_search_base: str = ""
    group_search_base: str = ""
    bind_user: str = ""
    bind_password: str = ""
    user_object_class: str = "person"
    group_object_class: str = "group"
    username_attribute: str = "sAMAccountName"
    email_attribute: str = "mail"
    group_membership_attribute: str = "memberOf"
    role_mapping: Dict[str, str] = Field(default_factory=dict)


class AuthConfig(BaseModel):
    """Authentication configuration."""

    jwt: JWTConfig = Field(default_factory=JWTConfig)
    api_keys_enabled: bool = True
    oauth: OAuthConfig = Field(default_factory=OAuthConfig)
    ldap: LDAPConfig = Field(default_factory=LDAPConfig)


class DemoConfig(BaseModel):
    """Demo endpoint configuration for landing page."""

    enabled: bool = True
    rate_limit: str = "30/minute"  # Configurable rate limit for demo
    allowed_scenarios: List[str] = Field(default_factory=lambda: ["onboarding"])
    max_query_length: int = 500


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = True
    storage: str = "memory"  # "memory" or "redis://localhost:6379"
    default_limits: List[str] = Field(default_factory=lambda: ["100/minute", "1000/hour"])
    endpoint_limits: Dict[str, str] = Field(default_factory=lambda: {
        "/api/v1/review/*": "10/minute",
        "/api/v1/chat": "60/minute",
        "/api/v1/chat/stream": "30/minute",
        "/api/v1/query/execute": "30/minute",
        "/api/v1/demo/chat": "30/minute",
    })


class CORSConfig(BaseModel):
    """CORS configuration."""

    allowed_origins: List[str] = Field(default_factory=lambda: [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    max_age: int = 600


class LoggingConfig(BaseModel):
    """Request logging configuration."""

    request_logging: bool = True
    audit_logging: bool = True
    log_request_body: bool = True
    log_response_body: bool = False
    max_body_log_size: int = 500
    exclude_paths: List[str] = Field(default_factory=lambda: ["/api/v1/health", "/api/v1/metrics"])


class DatabaseConfig(BaseModel):
    """PostgreSQL database configuration."""

    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/rag_cpgql")
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False


class APISettings(BaseSettings):
    """Main API settings with environment variable support."""

    # Server settings
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    workers: int = Field(default=4, alias="API_WORKERS")
    debug: bool = Field(default=False, alias="API_DEBUG")

    # API metadata
    title: str = "RAG-CPGQL API"
    description: str = "REST API for RAG-CPGQL Code Analysis System"
    version: str = "1.0.0"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/rag_cpgql",
        alias="DATABASE_URL"
    )

    # JWT
    jwt_secret: str = Field(
        default="change-me-in-production-use-64-chars-minimum-secret-key",
        alias="API_JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", alias="API_JWT_ALGORITHM")

    # Admin
    admin_username: str = Field(default="admin", alias="API_ADMIN_USERNAME")
    admin_password: str = Field(default="admin", alias="API_ADMIN_PASSWORD")

    # OAuth providers
    oauth_github_client_id: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_ID")
    oauth_github_client_secret: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_SECRET")
    oauth_google_client_id: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_SECRET")
    oauth_keycloak_server_url: str = Field(default="", alias="OAUTH_KEYCLOAK_SERVER_URL")
    oauth_keycloak_realm: str = Field(default="", alias="OAUTH_KEYCLOAK_REALM")
    oauth_keycloak_client_id: str = Field(default="", alias="OAUTH_KEYCLOAK_CLIENT_ID")
    oauth_keycloak_client_secret: str = Field(default="", alias="OAUTH_KEYCLOAK_CLIENT_SECRET")

    # LDAP
    ldap_server: str = Field(default="", alias="LDAP_SERVER")
    ldap_base_dn: str = Field(default="", alias="LDAP_BASE_DN")
    ldap_bind_user: str = Field(default="", alias="LDAP_BIND_USER")
    ldap_bind_password: str = Field(default="", alias="LDAP_BIND_PASSWORD")
    ldap_user_search_base: str = Field(default="", alias="LDAP_USER_SEARCH_BASE")
    ldap_group_search_base: str = Field(default="", alias="LDAP_GROUP_SEARCH_BASE")

    # Rate limiting
    rate_limit_storage: str = Field(default="memory", alias="RATE_LIMIT_STORAGE")

    # Demo settings
    demo_enabled: bool = Field(default=True, alias="DEMO_ENABLED")
    demo_rate_limit: str = Field(default="30/minute", alias="DEMO_RATE_LIMIT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_auth_config(self) -> AuthConfig:
        """Build AuthConfig from settings."""
        jwt_config = JWTConfig(
            secret_key=self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

        oauth_config = OAuthConfig(
            github=OAuthProviderConfig(
                enabled=bool(self.oauth_github_client_id),
                client_id=self.oauth_github_client_id,
                client_secret=self.oauth_github_client_secret,
                authorize_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["user:email"],
            ),
            google=OAuthProviderConfig(
                enabled=bool(self.oauth_google_client_id),
                client_id=self.oauth_google_client_id,
                client_secret=self.oauth_google_client_secret,
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
                scopes=["openid", "email", "profile"],
            ),
            keycloak=OAuthProviderConfig(
                enabled=bool(self.oauth_keycloak_server_url and self.oauth_keycloak_client_id),
                client_id=self.oauth_keycloak_client_id,
                client_secret=self.oauth_keycloak_client_secret,
                authorize_url=f"{self.oauth_keycloak_server_url}/realms/{self.oauth_keycloak_realm}/protocol/openid-connect/auth" if self.oauth_keycloak_server_url else "",
                token_url=f"{self.oauth_keycloak_server_url}/realms/{self.oauth_keycloak_realm}/protocol/openid-connect/token" if self.oauth_keycloak_server_url else "",
                userinfo_url=f"{self.oauth_keycloak_server_url}/realms/{self.oauth_keycloak_realm}/protocol/openid-connect/userinfo" if self.oauth_keycloak_server_url else "",
                scopes=["openid", "email", "profile"],
            ),
        )

        ldap_config = LDAPConfig(
            enabled=bool(self.ldap_server),
            server=self.ldap_server,
            base_dn=self.ldap_base_dn,
            bind_user=self.ldap_bind_user,
            bind_password=self.ldap_bind_password,
            user_search_base=self.ldap_user_search_base,
            group_search_base=self.ldap_group_search_base,
        )

        return AuthConfig(
            jwt=jwt_config,
            oauth=oauth_config,
            ldap=ldap_config,
        )

    def get_database_config(self) -> DatabaseConfig:
        """Build DatabaseConfig from settings."""
        return DatabaseConfig(
            url=self.database_url,
            echo=self.debug,
        )

    def get_rate_limit_config(self) -> RateLimitConfig:
        """Build RateLimitConfig from settings."""
        return RateLimitConfig(
            storage=self.rate_limit_storage,
        )

    def get_demo_config(self) -> DemoConfig:
        """Build DemoConfig from settings."""
        return DemoConfig(
            enabled=self.demo_enabled,
            rate_limit=self.demo_rate_limit,
        )


# Global settings instance
_settings: Optional[APISettings] = None


def get_settings() -> APISettings:
    """Get global API settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


def get_auth_config() -> AuthConfig:
    """Get authentication configuration."""
    return get_settings().get_auth_config()


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return get_settings().get_database_config()


def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limiting configuration."""
    return get_settings().get_rate_limit_config()


def get_demo_config() -> DemoConfig:
    """Get demo endpoint configuration."""
    return get_settings().get_demo_config()
