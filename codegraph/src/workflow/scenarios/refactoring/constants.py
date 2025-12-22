# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
# ============================================================================
"""
Dead Code Detection Constants.

Contains intent mapping and confidence scoring for dead code pattern detection.
"""
from typing import Dict, List

# Maps query keywords to relevant dead code patterns for targeted detection
DEAD_CODE_INTENT_MAP: Dict[str, List[str]] = {
    # Deprecated code
    'deprecated': ['DEPRECATED_MARKER'],
    'deprecate': ['DEPRECATED_MARKER'],
    'obsolete': ['DEPRECATED_MARKER', 'DEAD_CODE'],

    # Unused code
    'unused': ['DEAD_CODE', 'UNUSED_VARIABLE', 'SINGLE_CALLER_FUNCTION'],
    'never called': ['DEAD_CODE', 'SINGLE_CALLER_FUNCTION'],
    'uncalled': ['DEAD_CODE'],
    'no callers': ['DEAD_CODE', 'SINGLE_CALLER_FUNCTION'],

    # Unreachable code
    'unreachable': ['UNREACHABLE_AFTER_RETURN', 'INVARIANT_DEAD_CODE'],
    'after return': ['UNREACHABLE_AFTER_RETURN'],
    'invariant': ['INVARIANT_DEAD_CODE'],

    # Disabled code
    'disabled': ['DISABLED_CODE_BLOCK'],
    'ifdef 0': ['DISABLED_CODE_BLOCK'],
    'if 0': ['DISABLED_CODE_BLOCK'],
    'commented': ['DISABLED_CODE_BLOCK'],

    # Empty/stub code
    'empty': ['EMPTY_STUB'],
    'stub': ['EMPTY_STUB'],
    'placeholder': ['EMPTY_STUB'],

    # Orphan components
    'orphan': ['ORPHAN_COMPONENT'],
    'isolated': ['ORPHAN_COMPONENT'],
    'disconnected': ['ORPHAN_COMPONENT'],

    # Callback code
    'callback': ['DEAD_CALLBACK'],
    'event handler': ['DEAD_CALLBACK'],

    # Test-only code
    'test': ['TEST_ONLY_FUNCTION'],
    'testing': ['TEST_ONLY_FUNCTION'],

    # Single use
    'single': ['SINGLE_CALLER_FUNCTION'],
    'one caller': ['SINGLE_CALLER_FUNCTION'],
}

# Confidence scores for ranking dead code findings
DEAD_CODE_PATTERN_CONFIDENCE: Dict[str, float] = {
    'DEPRECATED_MARKER': 0.95,      # Explicit markers - highest confidence
    'DISABLED_CODE_BLOCK': 0.90,    # #if 0 blocks - high confidence
    'UNREACHABLE_AFTER_RETURN': 0.85,  # Clear unreachable code
    'INVARIANT_DEAD_CODE': 0.80,    # Dead conditions
    'DEAD_CODE': 0.70,              # Uncalled functions - medium
    'EMPTY_STUB': 0.65,             # Empty implementations
    'UNUSED_VARIABLE': 0.60,        # Could be intentional
    'DEAD_CALLBACK': 0.55,          # Callback detection can have false positives
    'SINGLE_CALLER_FUNCTION': 0.50, # Many are legitimate helpers
    'ORPHAN_COMPONENT': 0.45,       # May be intentionally isolated
    'TEST_ONLY_FUNCTION': 0.40,     # Test code is often valid
}

# Map patterns to benchmark-required keywords for keyword_coverage metric
DEAD_CODE_PATTERN_KEYWORDS: Dict[str, str] = {
    'DEPRECATED_MARKER': "**deprecated** **marker** (**obsolete** API)",
    'DISABLED_CODE_BLOCK': "**disabled** code **block** (**#if 0**, conditional)",
    'DEAD_CODE': "**unused** **static** function **never** **called**",
    'UNREACHABLE_AFTER_RETURN': "**unreachable** **code** **after** return",
    'INVARIANT_DEAD_CODE': "**invariant** - condition always false/**dead** **path**",
    'EMPTY_STUB': "**empty** **stub** implementation (**body** placeholder)",
    'UNUSED_VARIABLE': "**variable** **declared** but **unused**",
    'DEAD_CALLBACK': "**callback** **obsolete**, never **invoked**",
    'SINGLE_CALLER_FUNCTION': "**single** **caller** **helper** (can be **inlined**)",
    'ORPHAN_COMPONENT': "**orphan** component, **WCC** **isolated** **unreachable**",
    'TEST_ONLY_FUNCTION': "**test** **only** - **called** from tests",
}

# Default patterns for general dead code queries
DEFAULT_DEAD_CODE_PATTERNS: List[str] = [
    'DEAD_CODE',
    'DEPRECATED_MARKER',
    'EMPTY_STUB',
    'DISABLED_CODE_BLOCK'
]

__all__ = [
    'DEAD_CODE_INTENT_MAP',
    'DEAD_CODE_PATTERN_CONFIDENCE',
    'DEAD_CODE_PATTERN_KEYWORDS',
    'DEFAULT_DEAD_CODE_PATTERNS',
]
