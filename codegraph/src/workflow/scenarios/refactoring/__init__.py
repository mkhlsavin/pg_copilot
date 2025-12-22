# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
"""
Refactoring Workflow Package.

Provides:
- refactoring_workflow: Main refactoring workflow with code smell detection
- large_scale_refactoring_workflow: Bulk refactoring with ROI analysis
- mass_refactoring_workflow: Symbol/API migrations and rename automation
- Intent detection for dead code queries
- Constants for dead code pattern matching
"""
from .constants import (
    DEAD_CODE_INTENT_MAP,
    DEAD_CODE_PATTERN_CONFIDENCE,
    DEAD_CODE_PATTERN_KEYWORDS,
    DEFAULT_DEAD_CODE_PATTERNS,
)
from .intent_detector import (
    detect_dead_code_intent,
    rank_dead_code_by_confidence,
)
from .mass_migration import mass_migration_workflow
from .workflow import (
    refactoring_workflow,
    large_scale_refactoring_workflow,
    mass_refactoring_workflow,
    is_valid_function_name,
)

__all__ = [
    # Main workflows
    'refactoring_workflow',
    'large_scale_refactoring_workflow',
    'mass_refactoring_workflow',
    'mass_migration_workflow',
    # Constants
    'DEAD_CODE_INTENT_MAP',
    'DEAD_CODE_PATTERN_CONFIDENCE',
    'DEAD_CODE_PATTERN_KEYWORDS',
    'DEFAULT_DEAD_CODE_PATTERNS',
    # Intent detection
    'detect_dead_code_intent',
    'rank_dead_code_by_confidence',
    # Utilities
    'is_valid_function_name',
]
