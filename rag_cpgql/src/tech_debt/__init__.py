"""
Technical Debt Module - Scenario 12: Technical Debt Quantification

Provides pattern-based detection and quantification of technical debt including:
- TODO/FIXME comments
- Deprecated API usage
- Code duplication
- Long methods
- Complex methods
- Dead code

Components:
- debt_patterns: Pattern library with 6 debt patterns
- debt_agents: DebtCalculator, PrioritizationEngine, RepaymentPlanner (coming next)

Usage:
    from src.tech_debt import (
        DEBT_PATTERNS,
        get_pattern,
        DebtCalculator,
        PrioritizationEngine,
        RepaymentPlanner
    )
"""

# Pattern library exports
from .debt_patterns import (
    # Enums
    DebtSeverity,
    DebtCategory,

    # Data structures
    DebtPattern,

    # Patterns
    TODO_FIXME_COMMENTS,
    DEPRECATED_API_USAGE,
    CODE_DUPLICATION,
    LONG_METHODS,
    COMPLEX_METHODS,
    DEAD_CODE,

    # Pattern collections
    DEBT_PATTERNS,
    PATTERNS_BY_ID,
    PATTERNS_BY_CATEGORY,
    PATTERNS_BY_SEVERITY,

    # Utility functions
    get_pattern,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_all_patterns,
    calculate_total_effort,
    calculate_debt_ratio
)

# Agent exports
from .debt_agents import (
    # Agents
    DebtCalculator,
    PrioritizationEngine,
    RepaymentPlanner,

    # Data structures
    DebtItem,
    DebtMetrics,
    PrioritizedDebt,
    RepaymentPlan
)

__all__ = [
    # Enums
    'DebtSeverity',
    'DebtCategory',

    # Data structures (patterns)
    'DebtPattern',

    # Patterns
    'TODO_FIXME_COMMENTS',
    'DEPRECATED_API_USAGE',
    'CODE_DUPLICATION',
    'LONG_METHODS',
    'COMPLEX_METHODS',
    'DEAD_CODE',

    # Pattern collections
    'DEBT_PATTERNS',
    'PATTERNS_BY_ID',
    'PATTERNS_BY_CATEGORY',
    'PATTERNS_BY_SEVERITY',

    # Utility functions
    'get_pattern',
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_all_patterns',
    'calculate_total_effort',
    'calculate_debt_ratio',

    # Agents
    'DebtCalculator',
    'PrioritizationEngine',
    'RepaymentPlanner',

    # Data structures (agents)
    'DebtItem',
    'DebtMetrics',
    'PrioritizedDebt',
    'RepaymentPlan'
]
