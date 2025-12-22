"""
Refactoring Patterns - Modular Pattern Definitions

This package contains code smell and technical debt patterns organized by category.
Each module contains related patterns with CPGQL queries for detection.

Pattern Categories:
- bloaters: God Class, Long Method, Long Parameter List
- dead_code: All dead code detection patterns
- complexity: High Complexity, Deep Nesting
- duplicates: Duplicate Code detection
- documentation: TODO/FIXME tracking
"""

from typing import Dict
from .._base import RefactoringPattern

# Import pattern registries from each module
from .bloaters import BLOATER_PATTERNS
from .dead_code import DEAD_CODE_PATTERNS
from .complexity import COMPLEXITY_PATTERNS
from .duplicates import DUPLICATE_PATTERNS
from .documentation import DOCUMENTATION_PATTERNS

# Aggregate all patterns into a single registry
ALL_PATTERNS: Dict[str, RefactoringPattern] = {
    **BLOATER_PATTERNS,
    **DEAD_CODE_PATTERNS,
    **COMPLEXITY_PATTERNS,
    **DUPLICATE_PATTERNS,
    **DOCUMENTATION_PATTERNS,
}

__all__ = [
    'ALL_PATTERNS',
    'BLOATER_PATTERNS',
    'DEAD_CODE_PATTERNS',
    'COMPLEXITY_PATTERNS',
    'DUPLICATE_PATTERNS',
    'DOCUMENTATION_PATTERNS',
]
