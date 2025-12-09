"""
Security Patterns - Modular Pattern Library

This package organizes security vulnerability patterns by category:
- injection: SQL injection, command injection
- memory: Buffer overflows, use-after-free, memory leaks, etc.
- crypto: Weak cryptography, insufficient entropy, cleartext storage
- auth: Missing authentication, hardcoded secrets, privilege escalation
- input_validation: Integer overflow, tainted input, format string, etc.
- concurrency: Race conditions, file races
- python_django: Python/Django specific patterns (web vulnerabilities)
"""

from .injection import INJECTION_PATTERNS
from .memory import MEMORY_PATTERNS
from .crypto import CRYPTO_PATTERNS
from .auth import AUTH_PATTERNS
from .input_validation import INPUT_VALIDATION_PATTERNS
from .concurrency import CONCURRENCY_PATTERNS
from .python_django import PYTHON_DJANGO_PATTERNS, FILE_PATTERNS

# Aggregate all C/C++ patterns
ALL_PATTERNS = {
    **INJECTION_PATTERNS,
    **MEMORY_PATTERNS,
    **CRYPTO_PATTERNS,
    **AUTH_PATTERNS,
    **INPUT_VALIDATION_PATTERNS,
    **CONCURRENCY_PATTERNS,
}

# Aggregate all patterns including Python/Django
ALL_PATTERNS_WITH_PYTHON = {
    **ALL_PATTERNS,
    **PYTHON_DJANGO_PATTERNS,
}

__all__ = [
    'INJECTION_PATTERNS',
    'MEMORY_PATTERNS',
    'CRYPTO_PATTERNS',
    'AUTH_PATTERNS',
    'INPUT_VALIDATION_PATTERNS',
    'CONCURRENCY_PATTERNS',
    'PYTHON_DJANGO_PATTERNS',
    'FILE_PATTERNS',
    'ALL_PATTERNS',
    'ALL_PATTERNS_WITH_PYTHON',
]
