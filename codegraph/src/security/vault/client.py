"""
HashiCorp Vault Client.

Provides secure access to secrets stored in HashiCorp Vault.
Supports multiple authentication methods.
"""

import logging
import os
from typing import Any, Dict, Optional

from ..config import VaultConfig

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Base exception for Vault operations."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class VaultClient:
    """
    HashiCorp Vault client with support for multiple auth methods.

    Features:
    - Token, AppRole, and Kubernetes authentication
    - KV v2 secret engine support
    - Automatic token renewal
    - Graceful fallback to environment variables
    """

    def __init__(self, config: VaultConfig):
        """
        Initialize Vault client.

        Args:
            config: Vault configuration
        """
        self._config = config
        self._client = None
        self._enabled = config.enabled

        if not self._enabled:
            logger.info("Vault integration disabled, using environment variables")
            return

        try:
            self._initialize_client()
        except Exception as e:
            logger.warning(f"Vault initialization failed: {e}, falling back to env vars")
            self._enabled = False

    def _initialize_client(self) -> None:
        """Initialize hvac client with authentication."""
        try:
            import hvac
        except ImportError:
            raise VaultError(
                "hvac library not installed. Install with: pip install hvac"
            )

        # Get timeout and verify settings with defaults
        timeout = getattr(self._config, 'timeout_seconds', 30)
        verify = getattr(self._config, 'tls_verify', True)

        self._client = hvac.Client(
            url=self._config.url,
            timeout=timeout,
            verify=verify,
            namespace=getattr(self._config, 'namespace', None),
        )

        # Authenticate based on method (string comparison)
        auth_method = self._config.auth_method.lower()
        if auth_method == "token":
            self._auth_token()
        elif auth_method == "approle":
            self._auth_approle()
        elif auth_method == "kubernetes":
            self._auth_kubernetes()
        else:
            raise VaultError(f"Unsupported auth method: {self._config.auth_method}")

        if not self._client.is_authenticated():
            raise VaultError("Vault authentication failed")

        logger.info(f"Vault client authenticated: {self._config.url}")

    def _auth_token(self) -> None:
        """Authenticate with token."""
        # Get token from config nested structure or env var
        token = None
        if hasattr(self._config, 'token') and self._config.token:
            if hasattr(self._config.token, 'value'):
                token = self._config.token.value
            else:
                token = self._config.token
        token = token or os.environ.get("VAULT_TOKEN")

        if not token:
            raise VaultError("VAULT_TOKEN not set")
        self._client.token = token

    def _auth_approle(self) -> None:
        """Authenticate with AppRole."""
        # Get role_id and secret_id from config nested structure or env vars
        role_id = None
        secret_id = None

        if hasattr(self._config, 'approle') and self._config.approle:
            role_id = getattr(self._config.approle, 'role_id', None)
            secret_id = getattr(self._config.approle, 'secret_id', None)

        role_id = role_id or os.environ.get("VAULT_ROLE_ID")
        secret_id = secret_id or os.environ.get("VAULT_SECRET_ID")

        if not role_id or not secret_id:
            raise VaultError("VAULT_ROLE_ID or VAULT_SECRET_ID not set")

        mount_point = "approle"  # Default mount point

        response = self._client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id,
            mount_point=mount_point,
        )
        self._client.token = response["auth"]["client_token"]

    def _auth_kubernetes(self) -> None:
        """Authenticate with Kubernetes service account."""
        role = None
        jwt_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"

        if hasattr(self._config, 'kubernetes') and self._config.kubernetes:
            role = getattr(self._config.kubernetes, 'role', None)
            jwt_path = getattr(self._config.kubernetes, 'jwt_path', jwt_path)

        if not role:
            raise VaultError("Kubernetes role not configured")

        # Read service account token from mounted path
        try:
            with open(jwt_path, "r") as f:
                jwt = f.read().strip()
        except FileNotFoundError:
            raise VaultError(f"Kubernetes JWT not found at {jwt_path}")

        mount_point = "kubernetes"  # Default mount point

        response = self._client.auth.kubernetes.login(
            role=role,
            jwt=jwt,
            mount_point=mount_point,
        )
        self._client.token = response["auth"]["client_token"]

    def read_secret(
        self,
        path: str,
        version: Optional[int] = None,
        mount_point: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Read secret from Vault KV v2.

        Args:
            path: Secret path (without mount point prefix)
            version: Specific version to read (None for latest)
            mount_point: KV mount point (default from config)

        Returns:
            Secret data dictionary

        Raises:
            VaultError: If secret cannot be read
        """
        if not self._enabled:
            return self._read_from_env(path)

        try:
            mount = mount_point or self._config.secrets_mount_point
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                version=version,
                mount_point=mount,
            )
            return response["data"]["data"]
        except Exception as e:
            logger.error(f"Failed to read secret '{path}': {e}")
            raise VaultError(f"Failed to read secret: {path}", e)

    def write_secret(
        self,
        path: str,
        data: Dict[str, Any],
        mount_point: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Write secret to Vault KV v2.

        Args:
            path: Secret path
            data: Secret data to write
            mount_point: KV mount point (default from config)

        Returns:
            Write response metadata
        """
        if not self._enabled:
            raise VaultError("Cannot write secrets when Vault is disabled")

        try:
            mount = mount_point or self._config.secrets_mount_point
            response = self._client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=data,
                mount_point=mount,
            )
            logger.info(f"Secret written: {path}")
            return response["data"]
        except Exception as e:
            logger.error(f"Failed to write secret '{path}': {e}")
            raise VaultError(f"Failed to write secret: {path}", e)

    def delete_secret(
        self,
        path: str,
        versions: Optional[list] = None,
        mount_point: Optional[str] = None,
    ) -> None:
        """
        Delete secret from Vault.

        Args:
            path: Secret path
            versions: Specific versions to delete (None for all)
            mount_point: KV mount point
        """
        if not self._enabled:
            raise VaultError("Cannot delete secrets when Vault is disabled")

        try:
            mount = mount_point or self._config.secrets_mount_point
            if versions:
                self._client.secrets.kv.v2.delete_secret_versions(
                    path=path,
                    versions=versions,
                    mount_point=mount,
                )
            else:
                self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=path,
                    mount_point=mount,
                )
            logger.info(f"Secret deleted: {path}")
        except Exception as e:
            logger.error(f"Failed to delete secret '{path}': {e}")
            raise VaultError(f"Failed to delete secret: {path}", e)

    def get_llm_credentials(self) -> Dict[str, str]:
        """
        Get LLM provider credentials.

        Returns:
            Dictionary with provider credentials:
            - gigachat_api_key
            - openai_api_key
            - anthropic_api_key
            etc.
        """
        if not self._enabled:
            return self._get_llm_credentials_from_env()

        try:
            path = self._config.llm_secrets_path
            return self.read_secret(path)
        except VaultError:
            logger.warning("Falling back to environment variables for LLM credentials")
            return self._get_llm_credentials_from_env()

    def _get_llm_credentials_from_env(self) -> Dict[str, str]:
        """Get LLM credentials from environment variables."""
        credentials = {}

        # GigaChat
        if os.environ.get("GIGACHAT_CREDENTIALS"):
            credentials["gigachat_credentials"] = os.environ["GIGACHAT_CREDENTIALS"]
        if os.environ.get("GIGACHAT_API_KEY"):
            credentials["gigachat_api_key"] = os.environ["GIGACHAT_API_KEY"]

        # OpenAI
        if os.environ.get("OPENAI_API_KEY"):
            credentials["openai_api_key"] = os.environ["OPENAI_API_KEY"]

        # Anthropic
        if os.environ.get("ANTHROPIC_API_KEY"):
            credentials["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]

        # Azure OpenAI
        if os.environ.get("AZURE_OPENAI_API_KEY"):
            credentials["azure_openai_api_key"] = os.environ["AZURE_OPENAI_API_KEY"]
        if os.environ.get("AZURE_OPENAI_ENDPOINT"):
            credentials["azure_openai_endpoint"] = os.environ["AZURE_OPENAI_ENDPOINT"]

        return credentials

    def _read_from_env(self, path: str) -> Dict[str, Any]:
        """
        Read secrets from environment when Vault is disabled.

        Maps path to environment variables.
        """
        # Map common paths to environment variables
        env_mapping = {
            "llm": self._get_llm_credentials_from_env,
            "codegraph/llm": self._get_llm_credentials_from_env,
        }

        # Check if path has a handler
        path_key = path.split("/")[-1] if "/" in path else path
        handler = env_mapping.get(path_key)

        if handler:
            return handler()

        # Generic fallback: convert path to env var prefix
        prefix = path.upper().replace("/", "_").replace("-", "_")
        result = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                short_key = key[len(prefix) + 1:].lower() if key.startswith(prefix + "_") else key.lower()
                result[short_key] = value

        return result

    def renew_token(self) -> bool:
        """
        Renew the current token.

        Returns:
            True if renewal successful
        """
        if not self._enabled or not self._client:
            return False

        try:
            self._client.auth.token.renew_self()
            logger.debug("Vault token renewed")
            return True
        except Exception as e:
            logger.warning(f"Token renewal failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        if not self._enabled:
            return True  # Using env vars

        return self._client is not None and self._client.is_authenticated()

    @property
    def is_enabled(self) -> bool:
        """Check if Vault integration is enabled."""
        return self._enabled

    def close(self) -> None:
        """Close the Vault client."""
        if self._client:
            # hvac doesn't require explicit close
            self._client = None
            logger.debug("Vault client closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
