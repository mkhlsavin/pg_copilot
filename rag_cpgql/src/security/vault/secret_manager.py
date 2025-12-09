"""
Secret Manager - Caching and rotation for Vault secrets.

Provides:
- In-memory secret caching with TTL
- Automatic refresh before expiry
- Background rotation support
- Callbacks for secret updates
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .client import VaultClient, VaultError
from ..config import VaultConfig

logger = logging.getLogger(__name__)


@dataclass
class CachedSecret:
    """
    Cached secret with metadata.

    Attributes:
        path: Secret path
        data: Secret data
        fetched_at: When the secret was fetched
        expires_at: When the cache expires
        version: Secret version (if available)
    """

    path: str
    data: Dict[str, Any]
    fetched_at: datetime
    expires_at: datetime
    version: Optional[int] = None

    @property
    def is_expired(self) -> bool:
        """Check if secret has expired."""
        return datetime.utcnow() >= self.expires_at

    @property
    def should_refresh(self) -> bool:
        """Check if secret should be refreshed (within refresh window)."""
        refresh_window = (self.expires_at - self.fetched_at) * 0.2  # Last 20%
        refresh_time = self.expires_at - refresh_window
        return datetime.utcnow() >= refresh_time


class SecretManager:
    """
    Manages secrets with caching and automatic rotation.

    Features:
    - TTL-based caching
    - Background refresh before expiry
    - Rotation callbacks
    - Thread-safe operations
    """

    def __init__(
        self,
        client: VaultClient,
        config: VaultConfig,
        auto_refresh: bool = True,
    ):
        """
        Initialize secret manager.

        Args:
            client: Vault client instance
            config: Vault configuration
            auto_refresh: Enable automatic background refresh
        """
        self._client = client
        self._config = config
        self._cache: Dict[str, CachedSecret] = {}
        self._lock = threading.RLock()
        self._rotation_callbacks: Dict[str, List[Callable]] = {}

        # Background refresh
        self._auto_refresh = auto_refresh
        self._refresh_thread: Optional[threading.Thread] = None
        self._running = False

        if auto_refresh and client.is_enabled:
            self._start_refresh_worker()

    def _start_refresh_worker(self) -> None:
        """Start background refresh worker."""
        if self._running:
            return

        self._running = True
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="secret-refresh",
        )
        self._refresh_thread.start()
        logger.info("Secret refresh worker started")

    def _refresh_loop(self) -> None:
        """Background loop to refresh expiring secrets."""
        while self._running:
            try:
                self._check_and_refresh()
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")

            # Check every 30 seconds
            time.sleep(30)

    def _check_and_refresh(self) -> None:
        """Check and refresh secrets that need it."""
        with self._lock:
            paths_to_refresh = [
                path for path, cached in self._cache.items()
                if cached.should_refresh
            ]

        for path in paths_to_refresh:
            try:
                self._refresh_secret(path)
            except Exception as e:
                logger.error(f"Failed to refresh secret '{path}': {e}")

    def _refresh_secret(self, path: str) -> None:
        """Refresh a single secret."""
        logger.debug(f"Refreshing secret: {path}")

        try:
            data = self._client.read_secret(path)
            cached = self._cache_secret(path, data)

            # Notify callbacks
            callbacks = self._rotation_callbacks.get(path, [])
            for callback in callbacks:
                try:
                    callback(path, data)
                except Exception as e:
                    logger.error(f"Rotation callback error for '{path}': {e}")

            logger.info(f"Secret refreshed: {path}")

        except VaultError as e:
            logger.warning(f"Could not refresh secret '{path}': {e}")

    def _cache_secret(
        self,
        path: str,
        data: Dict[str, Any],
        version: Optional[int] = None,
    ) -> CachedSecret:
        """Cache a secret with TTL."""
        now = datetime.utcnow()
        ttl_seconds = self._config.cache_ttl_seconds

        cached = CachedSecret(
            path=path,
            data=data,
            fetched_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            version=version,
        )

        with self._lock:
            self._cache[path] = cached

        return cached

    def get_secret(
        self,
        path: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get secret, using cache if available.

        Args:
            path: Secret path
            force_refresh: Bypass cache and fetch fresh

        Returns:
            Secret data dictionary
        """
        # Check cache first
        if not force_refresh:
            with self._lock:
                cached = self._cache.get(path)
                if cached and not cached.is_expired:
                    logger.debug(f"Cache hit for: {path}")
                    return cached.data

        # Fetch from Vault
        data = self._client.read_secret(path)
        self._cache_secret(path, data)

        return data

    def get_llm_credentials(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get LLM credentials with caching.

        Args:
            force_refresh: Bypass cache

        Returns:
            LLM provider credentials
        """
        if not self._client.is_enabled:
            return self._client.get_llm_credentials()

        path = self._config.llm_secrets_path
        return self.get_secret(path, force_refresh)

    def invalidate(self, path: str) -> None:
        """
        Invalidate cached secret.

        Args:
            path: Secret path to invalidate
        """
        with self._lock:
            if path in self._cache:
                del self._cache[path]
                logger.debug(f"Cache invalidated: {path}")

    def invalidate_all(self) -> None:
        """Invalidate all cached secrets."""
        with self._lock:
            self._cache.clear()
            logger.info("All secrets cache invalidated")

    def register_rotation_callback(
        self,
        path: str,
        callback: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        """
        Register callback for secret rotation.

        The callback will be called when the secret is refreshed.

        Args:
            path: Secret path
            callback: Function(path, new_data) to call
        """
        with self._lock:
            if path not in self._rotation_callbacks:
                self._rotation_callbacks[path] = []
            self._rotation_callbacks[path].append(callback)

        logger.debug(f"Rotation callback registered for: {path}")

    def unregister_rotation_callback(
        self,
        path: str,
        callback: Callable,
    ) -> bool:
        """
        Unregister a rotation callback.

        Returns:
            True if callback was found and removed
        """
        with self._lock:
            callbacks = self._rotation_callbacks.get(path, [])
            if callback in callbacks:
                callbacks.remove(callback)
                return True
        return False

    def preload(self, paths: List[str]) -> int:
        """
        Preload multiple secrets into cache.

        Args:
            paths: List of secret paths to preload

        Returns:
            Number of secrets successfully loaded
        """
        loaded = 0
        for path in paths:
            try:
                self.get_secret(path)
                loaded += 1
            except VaultError as e:
                logger.warning(f"Could not preload '{path}': {e}")

        logger.info(f"Preloaded {loaded}/{len(paths)} secrets")
        return loaded

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = datetime.utcnow()
            expired = sum(1 for c in self._cache.values() if c.is_expired)
            expiring_soon = sum(1 for c in self._cache.values() if c.should_refresh)

            return {
                "total_cached": len(self._cache),
                "expired": expired,
                "expiring_soon": expiring_soon,
                "paths": list(self._cache.keys()),
                "auto_refresh_enabled": self._auto_refresh,
                "refresh_worker_running": self._running,
            }

    def stop(self) -> None:
        """Stop the secret manager and refresh worker."""
        self._running = False

        if self._refresh_thread:
            self._refresh_thread.join(timeout=5.0)
            self._refresh_thread = None

        self.invalidate_all()
        logger.info("Secret manager stopped")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# Global secret manager instance
_secret_manager: Optional[SecretManager] = None


def init_secret_manager(
    config: VaultConfig,
    auto_refresh: bool = True,
) -> SecretManager:
    """
    Initialize global secret manager.

    Args:
        config: Vault configuration
        auto_refresh: Enable automatic refresh

    Returns:
        SecretManager instance
    """
    global _secret_manager

    client = VaultClient(config)
    _secret_manager = SecretManager(client, config, auto_refresh)

    return _secret_manager


def get_secret_manager() -> Optional[SecretManager]:
    """Get global secret manager instance."""
    return _secret_manager


def get_llm_credentials() -> Dict[str, str]:
    """
    Convenience function to get LLM credentials.

    Uses secret manager if initialized, otherwise falls back
    to direct Vault client or environment variables.
    """
    if _secret_manager:
        return _secret_manager.get_llm_credentials()

    # Fallback to VaultClient with default config
    from ..config import get_security_config
    config = get_security_config()
    client = VaultClient(config.vault)
    return client.get_llm_credentials()
