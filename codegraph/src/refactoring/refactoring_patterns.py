"""
Refactoring Pattern Library for Code Property Graph Analysis

This module provides backward compatibility by re-exporting from the patterns package.

The patterns package contains modular pattern definitions:
- patterns/bloaters.py - God Class, Long Method, Long Parameter List
- patterns/dead_code.py - Dead Code, Unused Variable, Deprecated Marker, etc.
- patterns/complexity.py - High Complexity, Deep Nesting
- patterns/duplicates.py - Duplicate Code
- patterns/documentation.py - TODO/FIXME patterns

For new code, import directly from src.refactoring.patterns.
"""

from typing import Dict, List, Any

# Import base types from _base module
from ._base import (
    CodeSmellSeverity,
    CodeSmellCategory,
    RefactoringPattern,
)

# Re-export all patterns from the patterns package
from .patterns import (
    ALL_PATTERNS,
    BLOATER_PATTERNS,
    DEAD_CODE_PATTERNS,
    COMPLEXITY_PATTERNS,
    DUPLICATE_PATTERNS,
    DOCUMENTATION_PATTERNS,
)

# Re-export individual patterns for backward compatibility
from .patterns.bloaters import (
    GOD_CLASS_PATTERN,
    LONG_METHOD_PATTERN,
    LONG_PARAMETER_LIST_PATTERN,
)
from .patterns.dead_code import (
    DEAD_CODE_PATTERN,
    DEPRECATED_MARKER_PATTERN,
    DISABLED_CODE_BLOCK_PATTERN,
    UNUSED_VARIABLE_PATTERN,
    EMPTY_STUB_PATTERN,
    ERROR_ONLY_FUNCTION_PATTERN,
    UNREACHABLE_AFTER_RETURN_PATTERN,
    DEAD_ASSIGNMENT_PATTERN,
    INVARIANT_DEAD_CODE_PATTERN,
    DEAD_CALLBACK_PATTERN,
    SINGLE_CALLER_FUNCTION_PATTERN,
    TEST_ONLY_FUNCTION_PATTERN,
    ORPHAN_COMPONENT_PATTERN,
)
from .patterns.complexity import (
    HIGH_COMPLEXITY_PATTERN,
    DEEP_NESTING_PATTERN,
)
from .patterns.duplicates import (
    DUPLICATE_CODE_PATTERN,
)
from .patterns.documentation import (
    TODO_FIXME_PATTERN,
)


# ============================================================================
# PATTERN REGISTRY (for backward compatibility)
# ============================================================================

# All available refactoring patterns - uses ALL_PATTERNS from patterns package
REFACTORING_PATTERNS: Dict[str, RefactoringPattern] = ALL_PATTERNS


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


def get_pattern_by_id(pattern_id: str) -> RefactoringPattern:
    """Get refactoring pattern by ID"""
    return _get_pattern_by_id(REFACTORING_PATTERNS, pattern_id)


def get_patterns_by_category(category: CodeSmellCategory) -> List[RefactoringPattern]:
    """Get all patterns in a specific category"""
    return _get_patterns_by_category(REFACTORING_PATTERNS, category)


def get_patterns_by_severity(severity: CodeSmellSeverity) -> List[RefactoringPattern]:
    """Get all patterns with specific severity"""
    return _get_patterns_by_severity(REFACTORING_PATTERNS, severity)


def get_critical_patterns() -> List[RefactoringPattern]:
    """Get all critical severity patterns"""
    return _get_critical_patterns(REFACTORING_PATTERNS)


def get_all_cpgql_queries() -> Dict[str, str]:
    """Get all CPGQL queries indexed by pattern name"""
    return _get_all_cpgql_queries(REFACTORING_PATTERNS)


def get_pattern_summary() -> Dict[str, Any]:
    """Get summary statistics of refactoring patterns"""
    return _get_pattern_summary(REFACTORING_PATTERNS)


def validate_all_patterns() -> Dict[str, List[str]]:
    """Validate all patterns and return errors by pattern name"""
    return _validate_all_patterns(REFACTORING_PATTERNS)


__all__ = [
    # Base types
    'CodeSmellSeverity',
    'CodeSmellCategory',
    'RefactoringPattern',
    # Pattern registries
    'REFACTORING_PATTERNS',
    'ALL_PATTERNS',
    'BLOATER_PATTERNS',
    'DEAD_CODE_PATTERNS',
    'COMPLEXITY_PATTERNS',
    'DUPLICATE_PATTERNS',
    'DOCUMENTATION_PATTERNS',
    # Individual patterns - Bloaters
    'GOD_CLASS_PATTERN',
    'LONG_METHOD_PATTERN',
    'LONG_PARAMETER_LIST_PATTERN',
    # Individual patterns - Dead Code
    'DEAD_CODE_PATTERN',
    'DEPRECATED_MARKER_PATTERN',
    'DISABLED_CODE_BLOCK_PATTERN',
    'UNUSED_VARIABLE_PATTERN',
    'EMPTY_STUB_PATTERN',
    'ERROR_ONLY_FUNCTION_PATTERN',
    'UNREACHABLE_AFTER_RETURN_PATTERN',
    'DEAD_ASSIGNMENT_PATTERN',
    'INVARIANT_DEAD_CODE_PATTERN',
    'DEAD_CALLBACK_PATTERN',
    'SINGLE_CALLER_FUNCTION_PATTERN',
    'TEST_ONLY_FUNCTION_PATTERN',
    'ORPHAN_COMPONENT_PATTERN',
    # Individual patterns - Complexity
    'HIGH_COMPLEXITY_PATTERN',
    'DEEP_NESTING_PATTERN',
    # Individual patterns - Duplicates
    'DUPLICATE_CODE_PATTERN',
    # Individual patterns - Documentation
    'TODO_FIXME_PATTERN',
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
    print("Refactoring Pattern Library Summary")
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
        print(f"\nAll {len(REFACTORING_PATTERNS)} patterns validated successfully!")
