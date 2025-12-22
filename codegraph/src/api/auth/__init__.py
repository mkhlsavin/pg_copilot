"""
Authentication Package.

Provides JWT, API key, OAuth, and LDAP authentication.
"""

from src.api.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    TokenPayload,
)
from src.api.auth.permissions import Permission, Role, has_permission
from src.api.auth.api_keys import generate_api_key, validate_api_key, hash_api_key
from src.api.auth.oauth import (
    OAuthProvider,
    OAuthManager,
    OAuthUser,
    OAuthError,
    get_oauth_manager,
    setup_oauth_providers,
)
from src.api.auth.ldap_auth import (
    LDAPAuthenticator,
    LDAPUser,
    LDAPError,
    get_ldap_authenticator,
    setup_ldap_authenticator,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    "TokenPayload",
    # Permissions
    "Permission",
    "Role",
    "has_permission",
    # API Keys
    "generate_api_key",
    "validate_api_key",
    "hash_api_key",
    # OAuth
    "OAuthProvider",
    "OAuthManager",
    "OAuthUser",
    "OAuthError",
    "get_oauth_manager",
    "setup_oauth_providers",
    # LDAP
    "LDAPAuthenticator",
    "LDAPUser",
    "LDAPError",
    "get_ldap_authenticator",
    "setup_ldap_authenticator",
]
