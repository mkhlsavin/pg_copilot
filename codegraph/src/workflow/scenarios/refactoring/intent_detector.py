# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
"""
Dead Code Intent Detection.

Functions for detecting dead code intent from user queries
and ranking findings by confidence.
"""
from typing import List

from .constants import (
    DEAD_CODE_INTENT_MAP,
    DEAD_CODE_PATTERN_CONFIDENCE,
    DEFAULT_DEAD_CODE_PATTERNS,
)


def detect_dead_code_intent(query: str) -> List[str]:
    """
    Detect dead code intent from query and return relevant patterns.

    Args:
        query: User's dead code query

    Returns:
        List of relevant pattern names, or default patterns for general queries
    """
    query_lower = query.lower()
    matched_patterns = set()

    # Check each intent keyword
    for intent, patterns in DEAD_CODE_INTENT_MAP.items():
        if intent in query_lower:
            matched_patterns.update(patterns)

    # If we found specific patterns, return them
    if matched_patterns:
        return list(matched_patterns)

    # Default patterns for general dead code queries
    return DEFAULT_DEAD_CODE_PATTERNS.copy()


def rank_dead_code_by_confidence(findings: list) -> list:
    """
    Rank dead code findings by pattern confidence.

    Args:
        findings: List of dead code findings

    Returns:
        Sorted list with highest confidence first
    """
    def get_confidence(finding):
        pattern_name = getattr(finding, 'pattern_name', '') or getattr(finding, 'pattern_id', '')
        return DEAD_CODE_PATTERN_CONFIDENCE.get(pattern_name, 0.5)

    return sorted(findings, key=get_confidence, reverse=True)


__all__ = [
    'detect_dead_code_intent',
    'rank_dead_code_by_confidence',
]
