# ============================================================================
# BACKWARD COMPATIBILITY FACADE
# ============================================================================
# This file is kept for backward compatibility.
# All functionality has been moved to src/workflow/scenarios/refactoring/ package.
#
# New code should import directly from the package:
#   from src.workflow.scenarios.refactoring import refactoring_workflow
# ============================================================================
"""
Scenario 5: Enhanced Refactoring Assistance with Graph Analysis (Week 6 + Graph Methods)

Backward compatibility facade - imports from refactoring package.
"""
from src.workflow.scenarios.refactoring import (
    # Main workflows
    refactoring_workflow,
    large_scale_refactoring_workflow,
    mass_refactoring_workflow,
    # Constants
    DEAD_CODE_INTENT_MAP,
    DEAD_CODE_PATTERN_CONFIDENCE,
    DEAD_CODE_PATTERN_KEYWORDS,
    # Intent detection
    detect_dead_code_intent,
    rank_dead_code_by_confidence,
)

__all__ = [
    'refactoring_workflow',
    'large_scale_refactoring_workflow',
    'mass_refactoring_workflow',
    'DEAD_CODE_INTENT_MAP',
    'DEAD_CODE_PATTERN_CONFIDENCE',
    'DEAD_CODE_PATTERN_KEYWORDS',
    'detect_dead_code_intent',
    'rank_dead_code_by_confidence',
]
