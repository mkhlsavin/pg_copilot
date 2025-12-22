"""
Security Pattern Library - Base Types and Utilities

Contains core types, enums, and helper functions for security patterns.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class VulnerabilitySeverity(Enum):
    """Severity levels for security vulnerabilities"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityCategory(Enum):
    """OWASP-based vulnerability categories"""
    INJECTION = "injection"
    BUFFER_OVERFLOW = "buffer_overflow"
    MEMORY_SAFETY = "memory_safety"
    AUTHENTICATION = "authentication"
    ACCESS_CONTROL = "access_control"
    CRYPTOGRAPHY = "cryptography"
    INPUT_VALIDATION = "input_validation"
    RESOURCE_MANAGEMENT = "resource_management"
    CONCURRENCY = "concurrency"
    CONFIGURATION = "configuration"


@dataclass
class SecurityPattern:
    """
    Represents a security vulnerability pattern with detection queries

    Attributes:
        id: Unique pattern identifier
        name: Human-readable pattern name
        category: Vulnerability category
        severity: Default severity level
        description: Detailed vulnerability description
        cpgql_query: DuckDB SQL query for detection
        cwe_ids: Related CWE (Common Weakness Enumeration) identifiers
        remediation: Suggested fix or mitigation
        example_code: Example vulnerable code snippet
        test_cases: List of test scenarios
    """
    id: str
    name: str
    category: VulnerabilityCategory
    severity: VulnerabilitySeverity
    description: str
    cpgql_query: str
    cwe_ids: List[str]
    remediation: str
    example_code: str
    test_cases: List[Dict[str, Any]]


def get_pattern_by_id(patterns: Dict[str, SecurityPattern], pattern_id: str) -> SecurityPattern:
    """Get security pattern by ID"""
    for pattern in patterns.values():
        if pattern.id == pattern_id:
            return pattern
    raise ValueError(f"Pattern not found: {pattern_id}")


def get_patterns_by_category(
    patterns: Dict[str, SecurityPattern],
    category: VulnerabilityCategory
) -> List[SecurityPattern]:
    """Get all patterns in a specific category"""
    return [p for p in patterns.values() if p.category == category]


def get_patterns_by_severity(
    patterns: Dict[str, SecurityPattern],
    severity: VulnerabilitySeverity
) -> List[SecurityPattern]:
    """Get all patterns with specific severity"""
    return [p for p in patterns.values() if p.severity == severity]


def get_critical_patterns(patterns: Dict[str, SecurityPattern]) -> List[SecurityPattern]:
    """Get all critical severity patterns"""
    return get_patterns_by_severity(patterns, VulnerabilitySeverity.CRITICAL)


def get_all_cpgql_queries(patterns: Dict[str, SecurityPattern]) -> Dict[str, str]:
    """Get all CPGQL queries indexed by pattern name"""
    return {name: pattern.cpgql_query for name, pattern in patterns.items()}


def get_pattern_summary(patterns: Dict[str, SecurityPattern]) -> Dict[str, Any]:
    """Get summary statistics of security patterns"""
    return {
        "total_patterns": len(patterns),
        "by_category": {
            cat.value: len(get_patterns_by_category(patterns, cat))
            for cat in VulnerabilityCategory
        },
        "by_severity": {
            sev.value: len(get_patterns_by_severity(patterns, sev))
            for sev in VulnerabilitySeverity
        },
        "critical_count": len(get_critical_patterns(patterns)),
    }


def validate_pattern(pattern: SecurityPattern) -> List[str]:
    """
    Validate a security pattern for completeness
    Returns list of validation errors (empty if valid)
    """
    errors = []

    if not pattern.id:
        errors.append("Missing pattern ID")
    if not pattern.name:
        errors.append("Missing pattern name")
    if not pattern.cpgql_query:
        errors.append("Missing CPGQL query")
    if not pattern.remediation:
        errors.append("Missing remediation guidance")
    if not pattern.cwe_ids:
        errors.append("Missing CWE identifiers")
    if not pattern.example_code:
        errors.append("Missing example code")

    return errors


def validate_all_patterns(patterns: Dict[str, SecurityPattern]) -> Dict[str, List[str]]:
    """Validate all patterns and return errors by pattern name"""
    return {
        name: validate_pattern(pattern)
        for name, pattern in patterns.items()
    }


__all__ = [
    'VulnerabilitySeverity',
    'VulnerabilityCategory',
    'SecurityPattern',
    'get_pattern_by_id',
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_critical_patterns',
    'get_all_cpgql_queries',
    'get_pattern_summary',
    'validate_pattern',
    'validate_all_patterns',
]
