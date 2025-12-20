"""
Security Patterns - Modular Pattern Library

This package organizes security vulnerability patterns by category and language:

Core Categories (C/C++):
- injection: SQL injection, command injection
- memory: Buffer overflows, use-after-free, memory leaks, etc.
- crypto: Weak cryptography, insufficient entropy, cleartext storage
- auth: Missing authentication, hardcoded secrets, privilege escalation
- input_validation: Integer overflow, tainted input, format string, etc.
- concurrency: Race conditions, file races

Language-Specific Patterns:
- python_django: Python/Django specific patterns (web vulnerabilities)
- javascript: JavaScript/TypeScript patterns (XSS, prototype pollution, etc.)
- go: Go patterns (race conditions, SQL injection, etc.)
- ruby: Ruby/Rails patterns (eval injection, YAML deserialization, etc.)
- csharp: C#/.NET patterns (SQL injection, XSS, deserialization, etc.)
- kotlin: Kotlin/Android patterns (WebView XSS, intent redirection, etc.)
- swift: Swift/iOS patterns (keychain misuse, URL scheme hijacking, etc.)
"""

from .injection import INJECTION_PATTERNS
from .memory import MEMORY_PATTERNS
from .crypto import CRYPTO_PATTERNS
from .auth import AUTH_PATTERNS
from .input_validation import INPUT_VALIDATION_PATTERNS
from .concurrency import CONCURRENCY_PATTERNS
from .python_django import PYTHON_DJANGO_PATTERNS, FILE_PATTERNS

# Language-specific patterns
from .javascript import JAVASCRIPT_PATTERNS
from .go import GO_PATTERNS
from .ruby import RUBY_PATTERNS
from .csharp import CSHARP_PATTERNS
from .kotlin import KOTLIN_PATTERNS
from .swift import SWIFT_PATTERNS
from .java import JAVA_PATTERNS
from .php import PHP_PATTERNS

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

# All language-specific patterns
LANGUAGE_PATTERNS = {
    "c": ALL_PATTERNS,  # C/C++ uses core patterns
    "cpp": ALL_PATTERNS,  # C++ uses core patterns
    "python": PYTHON_DJANGO_PATTERNS,
    "javascript": JAVASCRIPT_PATTERNS,
    "typescript": JAVASCRIPT_PATTERNS,  # Same as JS
    "go": GO_PATTERNS,
    "ruby": RUBY_PATTERNS,
    "csharp": CSHARP_PATTERNS,
    "kotlin": KOTLIN_PATTERNS,
    "swift": SWIFT_PATTERNS,
    "java": JAVA_PATTERNS,
    "java_bytecode": JAVA_PATTERNS,  # Same as Java source
    "php": PHP_PATTERNS,
}

# Complete pattern registry (all languages)
ALL_LANGUAGE_PATTERNS = {
    **ALL_PATTERNS,
    **PYTHON_DJANGO_PATTERNS,
    **JAVASCRIPT_PATTERNS,
    **GO_PATTERNS,
    **RUBY_PATTERNS,
    **CSHARP_PATTERNS,
    **KOTLIN_PATTERNS,
    **SWIFT_PATTERNS,
    **JAVA_PATTERNS,
    **PHP_PATTERNS,
}

__all__ = [
    # Core C/C++ patterns
    'INJECTION_PATTERNS',
    'MEMORY_PATTERNS',
    'CRYPTO_PATTERNS',
    'AUTH_PATTERNS',
    'INPUT_VALIDATION_PATTERNS',
    'CONCURRENCY_PATTERNS',
    # Language-specific patterns
    'PYTHON_DJANGO_PATTERNS',
    'JAVASCRIPT_PATTERNS',
    'GO_PATTERNS',
    'RUBY_PATTERNS',
    'CSHARP_PATTERNS',
    'KOTLIN_PATTERNS',
    'SWIFT_PATTERNS',
    'JAVA_PATTERNS',
    'PHP_PATTERNS',
    # Utilities
    'FILE_PATTERNS',
    'ALL_PATTERNS',
    'ALL_PATTERNS_WITH_PYTHON',
    'LANGUAGE_PATTERNS',
    'ALL_LANGUAGE_PATTERNS',
]
