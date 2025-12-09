"""
LDAP/Active Directory Authentication Module.

Provides LDAP/AD authentication and group synchronization.
"""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from src.api.config import LDAPConfig

logger = logging.getLogger("api.auth.ldap")


class LDAPUser(BaseModel):
    """LDAP user information."""

    dn: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    groups: List[str] = []
    attributes: Dict[str, List[str]] = {}


class LDAPError(Exception):
    """LDAP authentication error."""

    pass


class LDAPAuthenticator:
    """
    LDAP/Active Directory authenticator.

    Handles authentication against LDAP/AD servers.
    """

    def __init__(self, config: LDAPConfig):
        """
        Initialize the LDAP authenticator.

        Args:
            config: LDAP configuration
        """
        self.config = config
        self._connection = None

        # Try to import ldap3
        try:
            import ldap3
            self.ldap3 = ldap3
        except ImportError:
            logger.warning("ldap3 not installed. LDAP authentication will not work.")
            self.ldap3 = None

    @property
    def is_available(self) -> bool:
        """Check if LDAP is available."""
        return self.ldap3 is not None and self.config.enabled

    def _get_server(self):
        """Create LDAP server object."""
        if not self.ldap3:
            raise LDAPError("ldap3 library not installed")

        use_ssl = self.config.server.startswith("ldaps://")
        server_url = self.config.server.replace("ldaps://", "").replace("ldap://", "")

        # Parse host and port
        if ":" in server_url:
            host, port = server_url.split(":", 1)
            port = int(port)
        else:
            host = server_url
            port = 636 if use_ssl else 389

        return self.ldap3.Server(
            host,
            port=port,
            use_ssl=use_ssl,
            get_info=self.ldap3.ALL,
        )

    def _get_service_connection(self):
        """Get service account connection for searches."""
        if not self.ldap3:
            raise LDAPError("ldap3 library not installed")

        server = self._get_server()

        conn = self.ldap3.Connection(
            server,
            user=self.config.bind_user,
            password=self.config.bind_password,
            auto_bind=True,
            read_only=True,
        )

        return conn

    def _build_user_dn(self, username: str) -> str:
        """
        Build user DN from username.

        Args:
            username: Username

        Returns:
            User DN
        """
        # Simple DN construction - may need customization
        return f"CN={username},{self.config.user_search_base}"

    def _build_search_filter(self, username: str) -> str:
        """
        Build LDAP search filter for user.

        Args:
            username: Username

        Returns:
            LDAP search filter
        """
        # Support both sAMAccountName (AD) and uid (standard LDAP)
        return f"(|(sAMAccountName={username})(uid={username})(userPrincipalName={username}))"

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> Optional[LDAPUser]:
        """
        Authenticate user against LDAP.

        Args:
            username: Username
            password: Password

        Returns:
            LDAP user if authenticated, None otherwise

        Raises:
            LDAPError: If connection fails
        """
        if not self.is_available:
            raise LDAPError("LDAP is not available")

        try:
            # First, search for user DN using service account
            user_dn = await self._find_user_dn(username)
            if not user_dn:
                logger.info(f"LDAP user not found: {username}")
                return None

            # Try to bind with user credentials
            server = self._get_server()
            conn = self.ldap3.Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )

            if not conn.bound:
                logger.info(f"LDAP bind failed for user: {username}")
                return None

            conn.unbind()

            # Get user info and groups
            user_info = await self._get_user_info(username)
            if user_info:
                user_info.groups = await self.get_user_groups(username)

            logger.info(f"LDAP authentication successful: {username}")
            return user_info

        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            raise LDAPError(f"Authentication failed: {e}")

    async def _find_user_dn(self, username: str) -> Optional[str]:
        """
        Find user DN by username.

        Args:
            username: Username

        Returns:
            User DN or None
        """
        try:
            conn = self._get_service_connection()
            search_filter = self._build_search_filter(username)

            conn.search(
                search_base=self.config.user_search_base,
                search_filter=search_filter,
                search_scope=self.ldap3.SUBTREE,
                attributes=["distinguishedName"],
            )

            if conn.entries:
                dn = conn.entries[0].entry_dn
                conn.unbind()
                return dn

            conn.unbind()
            return None

        except Exception as e:
            logger.error(f"LDAP user search error: {e}")
            return None

    async def _get_user_info(self, username: str) -> Optional[LDAPUser]:
        """
        Get user information from LDAP.

        Args:
            username: Username

        Returns:
            LDAP user info or None
        """
        try:
            conn = self._get_service_connection()
            search_filter = self._build_search_filter(username)

            conn.search(
                search_base=self.config.user_search_base,
                search_filter=search_filter,
                search_scope=self.ldap3.SUBTREE,
                attributes=[
                    "distinguishedName",
                    "sAMAccountName",
                    "uid",
                    "mail",
                    "displayName",
                    "cn",
                    "memberOf",
                ],
            )

            if not conn.entries:
                conn.unbind()
                return None

            entry = conn.entries[0]
            attributes = entry.entry_attributes_as_dict

            # Extract username (prefer sAMAccountName, then uid)
            extracted_username = (
                attributes.get("sAMAccountName", [None])[0]
                or attributes.get("uid", [None])[0]
                or username
            )

            user = LDAPUser(
                dn=entry.entry_dn,
                username=extracted_username,
                email=attributes.get("mail", [None])[0],
                display_name=attributes.get("displayName", [None])[0]
                or attributes.get("cn", [None])[0],
                attributes=attributes,
            )

            conn.unbind()
            return user

        except Exception as e:
            logger.error(f"LDAP user info error: {e}")
            return None

    async def get_user_groups(self, username: str) -> List[str]:
        """
        Get user's group memberships.

        Args:
            username: Username

        Returns:
            List of group names
        """
        if not self.is_available:
            return []

        try:
            conn = self._get_service_connection()
            search_filter = self._build_search_filter(username)

            conn.search(
                search_base=self.config.user_search_base,
                search_filter=search_filter,
                search_scope=self.ldap3.SUBTREE,
                attributes=["memberOf"],
            )

            groups = []
            if conn.entries:
                member_of = conn.entries[0].entry_attributes_as_dict.get("memberOf", [])
                for group_dn in member_of:
                    # Extract CN from group DN
                    for part in group_dn.split(","):
                        if part.upper().startswith("CN="):
                            groups.append(part[3:])
                            break

            conn.unbind()
            return groups

        except Exception as e:
            logger.error(f"LDAP group search error: {e}")
            return []

    def map_groups_to_role(self, groups: List[str]) -> str:
        """
        Map LDAP groups to application role.

        Args:
            groups: List of LDAP group names

        Returns:
            Application role name
        """
        group_mapping = self.config.group_role_mapping or {}

        # Check groups in order of privilege (highest first)
        for role in ["admin", "reviewer", "analyst", "viewer"]:
            mapped_groups = group_mapping.get(role, [])
            for group in groups:
                if group in mapped_groups:
                    return role

        # Default role
        return "analyst"

    async def test_connection(self) -> bool:
        """
        Test LDAP connection.

        Returns:
            True if connection successful
        """
        if not self.is_available:
            return False

        try:
            conn = self._get_service_connection()
            result = conn.bound
            conn.unbind()
            return result
        except Exception as e:
            logger.error(f"LDAP connection test failed: {e}")
            return False


# Global LDAP authenticator
_ldap_authenticator: Optional[LDAPAuthenticator] = None


def get_ldap_authenticator() -> Optional[LDAPAuthenticator]:
    """Get the global LDAP authenticator instance."""
    return _ldap_authenticator


def setup_ldap_authenticator(config: LDAPConfig) -> Optional[LDAPAuthenticator]:
    """
    Setup LDAP authenticator from configuration.

    Args:
        config: LDAP configuration

    Returns:
        Configured LDAP authenticator or None
    """
    global _ldap_authenticator

    if not config.enabled:
        logger.info("LDAP authentication is disabled")
        return None

    _ldap_authenticator = LDAPAuthenticator(config)

    if not _ldap_authenticator.is_available:
        logger.warning("LDAP authenticator not available (ldap3 not installed)")
        return None

    logger.info(f"LDAP authenticator configured for: {config.server}")
    return _ldap_authenticator
