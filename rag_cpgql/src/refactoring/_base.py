"""
Refactoring Pattern Library - Base Types and Utilities

Contains core types, enums, and helper functions for refactoring patterns.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class CodeSmellSeverity(Enum):
    """Severity levels for code smells"""
    CRITICAL = "critical"  # Severely impacts maintainability
    HIGH = "high"          # Major maintainability issues
    MEDIUM = "medium"      # Moderate technical debt
    LOW = "low"            # Minor improvements needed
    INFO = "info"          # Informational only


class CodeSmellCategory(Enum):
    """Categories of code smells (based on Fowler's catalog)"""
    BLOATERS = "bloaters"                    # Long methods, large classes
    OO_ABUSERS = "oo_abusers"               # Switch statements, refused bequest
    CHANGE_PREVENTERS = "change_preventers" # Divergent change, shotgun surgery
    DISPENSABLES = "dispensables"            # Dead code, speculative generality
    COUPLERS = "couplers"                   # Feature envy, inappropriate intimacy
    COMPLEXITY = "complexity"                # Deep nesting, complex conditions
    DOCUMENTATION = "documentation"          # Missing docs, outdated comments


@dataclass
class RefactoringPattern:
    """
    Represents a code smell or technical debt pattern with detection queries

    Attributes:
        id: Unique pattern identifier
        name: Human-readable pattern name
        category: Code smell category
        severity: Default severity level
        description: Detailed smell description
        cpgql_query: DuckDB SQL query for detection
        symptoms: List of symptoms indicating this smell
        refactoring_technique: Recommended refactoring approach
        example_before: Example code with the smell
        example_after: Example refactored code
        effort_estimate: Typical effort to fix (hours)
    """
    id: str
    name: str
    category: CodeSmellCategory
    severity: CodeSmellSeverity
    description: str
    cpgql_query: str
    symptoms: List[str]
    refactoring_technique: str
    example_before: str
    example_after: str
    effort_estimate: float  # hours


def get_pattern_by_id(patterns: Dict[str, RefactoringPattern], pattern_id: str) -> RefactoringPattern:
    """Get refactoring pattern by ID"""
    for pattern in patterns.values():
        if pattern.id == pattern_id:
            return pattern
    raise ValueError(f"Pattern not found: {pattern_id}")


def get_patterns_by_category(
    patterns: Dict[str, RefactoringPattern],
    category: CodeSmellCategory
) -> List[RefactoringPattern]:
    """Get all patterns in a specific category"""
    return [p for p in patterns.values() if p.category == category]


def get_patterns_by_severity(
    patterns: Dict[str, RefactoringPattern],
    severity: CodeSmellSeverity
) -> List[RefactoringPattern]:
    """Get all patterns with specific severity"""
    return [p for p in patterns.values() if p.severity == severity]


def get_critical_patterns(patterns: Dict[str, RefactoringPattern]) -> List[RefactoringPattern]:
    """Get all critical severity patterns"""
    return get_patterns_by_severity(patterns, CodeSmellSeverity.CRITICAL)


def get_all_cpgql_queries(patterns: Dict[str, RefactoringPattern]) -> Dict[str, str]:
    """Get all CPGQL queries indexed by pattern name"""
    return {name: pattern.cpgql_query for name, pattern in patterns.items()}


def get_pattern_summary(patterns: Dict[str, RefactoringPattern]) -> Dict[str, Any]:
    """Get summary statistics of refactoring patterns"""
    return {
        "total_patterns": len(patterns),
        "by_category": {
            cat.value: len(get_patterns_by_category(patterns, cat))
            for cat in CodeSmellCategory
        },
        "by_severity": {
            sev.value: len(get_patterns_by_severity(patterns, sev))
            for sev in CodeSmellSeverity
        },
        "total_effort_hours": sum(p.effort_estimate for p in patterns.values()),
    }


def validate_pattern(pattern: RefactoringPattern) -> List[str]:
    """
    Validate a refactoring pattern for completeness
    Returns list of validation errors (empty if valid)
    """
    errors = []

    if not pattern.id:
        errors.append("Missing pattern ID")
    if not pattern.name:
        errors.append("Missing pattern name")
    if not pattern.cpgql_query:
        errors.append("Missing CPGQL query")
    if not pattern.refactoring_technique:
        errors.append("Missing refactoring technique")
    if not pattern.symptoms:
        errors.append("Missing symptoms list")
    if pattern.effort_estimate <= 0:
        errors.append("Invalid effort estimate")

    return errors


def validate_all_patterns(patterns: Dict[str, RefactoringPattern]) -> Dict[str, List[str]]:
    """Validate all patterns and return errors by pattern name"""
    return {
        name: validate_pattern(pattern)
        for name, pattern in patterns.items()
    }


__all__ = [
    'CodeSmellSeverity',
    'CodeSmellCategory',
    'RefactoringPattern',
    'get_pattern_by_id',
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_critical_patterns',
    'get_all_cpgql_queries',
    'get_pattern_summary',
    'validate_pattern',
    'validate_all_patterns',
]
