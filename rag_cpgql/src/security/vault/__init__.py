"""
Vault Integration Module.

Provides HashiCorp Vault integration for secrets management:
- Secure credential retrieval
- Secret rotation support
- Multiple auth methods
"""

from .client import VaultClient, VaultError
from .secret_manager import SecretManager, CachedSecret

__all__ = [
    "VaultClient",
    "VaultError",
    "SecretManager",
    "CachedSecret",
]
