"""
Security Pattern Library for Code Property Graph Analysis

This module provides backward compatibility by re-exporting from the patterns package.

The patterns package contains modular pattern definitions:
- patterns/injection.py - SQL Injection, Command Injection
- patterns/memory.py - Buffer Overflow, Use-After-Free, Memory Leak, etc.
- patterns/crypto.py - Weak Crypto, Insufficient Entropy, Cleartext Storage
- patterns/auth.py - Missing Auth, Hardcoded Secrets, Privilege Escalation
- patterns/input_validation.py - Integer Overflow, Tainted Input, Format String, etc.
- patterns/concurrency.py - Race Condition, File Race

For new code, import directly from src.security.patterns.
"""

from typing import Dict, List, Any

# Import base types from _base module
from ._base import (
    VulnerabilitySeverity,
    VulnerabilityCategory,
    SecurityPattern,
)

# Re-export all patterns from the patterns package
from .patterns import (
    ALL_PATTERNS,
    INJECTION_PATTERNS,
    MEMORY_PATTERNS,
    CRYPTO_PATTERNS,
    AUTH_PATTERNS,
    INPUT_VALIDATION_PATTERNS,
    CONCURRENCY_PATTERNS,
)

# Re-export individual patterns for backward compatibility
from .patterns.injection import (
    SQL_INJECTION_PATTERN,
    COMMAND_INJECTION_PATTERN,
)
from .patterns.memory import (
    BUFFER_OVERFLOW_STRCPY_PATTERN,
    BUFFER_OVERFLOW_SPRINTF_PATTERN,
    USE_AFTER_FREE_PATTERN,
    MEMORY_LEAK_PATTERN,
    NULL_POINTER_DEREFERENCE_PATTERN,
    DOUBLE_FREE_PATTERN,
    RESOURCE_LEAK_PATTERN,
    UNINITIALIZED_VAR_PATTERN,
    ARRAY_BOUNDS_PATTERN,
)
from .patterns.crypto import (
    WEAK_CRYPTO_PATTERN,
    CLEARTEXT_STORAGE_PATTERN,
    INSUFFICIENT_ENTROPY_PATTERN,
    IMPROPER_CERT_PATTERN,
)
from .patterns.auth import (
    HARDCODED_SECRETS_PATTERN,
    MISSING_AUTH_PATTERN,
    PRIV_ESCALATION_PATTERN,
)
from .patterns.input_validation import (
    INTEGER_OVERFLOW_PATTERN,
    TAINTED_INPUT_PATTERN,
    FORMAT_STRING_PATTERN,
    PATH_TRAVERSAL_PATTERN,
    TYPE_CONFUSION_PATTERN,
    INSECURE_DESERIALIZATION_PATTERN,
    SSRF_PATTERN,
)
from .patterns.concurrency import (
    RACE_CONDITION_PATTERN,
    FILE_RACE_PATTERN,
    XXE_PATTERN,
    LOG_INJECTION_PATTERN,
    EXEC_PATH_INJECTION_PATTERN,
)


# ============================================================================
# PATTERN REGISTRY (for backward compatibility)
# ============================================================================

# All available security patterns - uses ALL_PATTERNS from patterns package
SECURITY_PATTERNS: Dict[str, SecurityPattern] = ALL_PATTERNS


# Import utility functions from _base module
from ._base import (
    get_pattern_by_id as _get_pattern_by_id,
    get_patterns_by_category as _get_patterns_by_category,
    get_patterns_by_severity as _get_patterns_by_severity,
    get_critical_patterns as _get_critical_patterns,
    get_all_cpgql_queries as _get_all_cpgql_queries,
    get_pattern_summary as _get_pattern_summary,
    validate_pattern,
    validate_all_patterns as _validate_all_patterns,
)


def get_pattern_by_id(pattern_id: str) -> SecurityPattern:
    """Get security pattern by ID"""
    return _get_pattern_by_id(SECURITY_PATTERNS, pattern_id)


def get_patterns_by_category(category: VulnerabilityCategory) -> List[SecurityPattern]:
    """Get all patterns in a specific category"""
    return _get_patterns_by_category(SECURITY_PATTERNS, category)


def get_patterns_by_severity(severity: VulnerabilitySeverity) -> List[SecurityPattern]:
    """Get all patterns with specific severity"""
    return _get_patterns_by_severity(SECURITY_PATTERNS, severity)


def get_critical_patterns() -> List[SecurityPattern]:
    """Get all critical severity patterns"""
    return _get_critical_patterns(SECURITY_PATTERNS)


def get_all_cpgql_queries() -> Dict[str, str]:
    """Get all CPGQL queries indexed by pattern name"""
    return _get_all_cpgql_queries(SECURITY_PATTERNS)


def get_pattern_summary() -> Dict[str, Any]:
    """Get summary statistics of security patterns"""
    return _get_pattern_summary(SECURITY_PATTERNS)


def validate_all_patterns() -> Dict[str, List[str]]:
    """Validate all patterns and return errors by pattern name"""
    return _validate_all_patterns(SECURITY_PATTERNS)


__all__ = [
    # Base types
    'VulnerabilitySeverity',
    'VulnerabilityCategory',
    'SecurityPattern',
    # Pattern registries
    'SECURITY_PATTERNS',
    'ALL_PATTERNS',
    'INJECTION_PATTERNS',
    'MEMORY_PATTERNS',
    'CRYPTO_PATTERNS',
    'AUTH_PATTERNS',
    'INPUT_VALIDATION_PATTERNS',
    'CONCURRENCY_PATTERNS',
    # Individual patterns - Injection
    'SQL_INJECTION_PATTERN',
    'COMMAND_INJECTION_PATTERN',
    # Individual patterns - Memory
    'BUFFER_OVERFLOW_STRCPY_PATTERN',
    'BUFFER_OVERFLOW_SPRINTF_PATTERN',
    'USE_AFTER_FREE_PATTERN',
    'MEMORY_LEAK_PATTERN',
    'NULL_POINTER_DEREFERENCE_PATTERN',
    'DOUBLE_FREE_PATTERN',
    'RESOURCE_LEAK_PATTERN',
    # Individual patterns - Crypto
    'WEAK_CRYPTO_PATTERN',
    'CLEARTEXT_STORAGE_PATTERN',
    'INSUFFICIENT_ENTROPY_PATTERN',
    'IMPROPER_CERT_PATTERN',
    # Individual patterns - Auth
    'HARDCODED_SECRETS_PATTERN',
    'MISSING_AUTH_PATTERN',
    'PRIV_ESCALATION_PATTERN',
    # Individual patterns - Input Validation
    'INTEGER_OVERFLOW_PATTERN',
    'TAINTED_INPUT_PATTERN',
    'FORMAT_STRING_PATTERN',
    'PATH_TRAVERSAL_PATTERN',
    'ARRAY_BOUNDS_PATTERN',
    'TYPE_CONFUSION_PATTERN',
    'UNINITIALIZED_VAR_PATTERN',
    'INSECURE_DESERIALIZATION_PATTERN',
    'SSRF_PATTERN',
    'XXE_PATTERN',
    'LOG_INJECTION_PATTERN',
    'EXEC_PATH_INJECTION_PATTERN',
    # Individual patterns - Concurrency
    'RACE_CONDITION_PATTERN',
    'FILE_RACE_PATTERN',
    # Utility functions
    'get_pattern_by_id',
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_critical_patterns',
    'get_all_cpgql_queries',
    'get_pattern_summary',
    'validate_pattern',
    'validate_all_patterns',
]


if __name__ == "__main__":
    # Print pattern summary
    summary = get_pattern_summary()
    print("Security Pattern Library Summary")
    print("=" * 50)
    print(f"Total Patterns: {summary['total_patterns']}")
    print(f"\nBy Category:")
    for cat, count in summary['by_category'].items():
        if count > 0:
            print(f"  {cat}: {count}")
    print(f"\nBy Severity:")
    for sev, count in summary['by_severity'].items():
        if count > 0:
            print(f"  {sev}: {count}")

    # Validate all patterns
    validation_results = validate_all_patterns()
    invalid = {k: v for k, v in validation_results.items() if v}
    if invalid:
        print(f"\n{len(invalid)} patterns have validation errors:")
        for name, errors in invalid.items():
            print(f"  {name}: {', '.join(errors)}")
    else:
        print(f"\nAll {len(SECURITY_PATTERNS)} patterns validated successfully!")
