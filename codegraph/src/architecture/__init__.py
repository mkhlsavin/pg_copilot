"""
Architecture Module - Scenario 11: Architecture Violation Detection

Provides pattern-based detection of architectural violations including:
- Circular dependencies
- Layering violations
- God modules
- Unstable dependencies
- Feature envy
- Inappropriate intimacy

Components:
- architecture_patterns: Pattern library with 6 violation patterns
- architecture_agents: DependencyAnalyzer, LayerValidator, ArchitectureReporter (coming next)

Usage:
    from src.architecture import (
        ARCHITECTURE_PATTERNS,
        get_pattern,
        DependencyAnalyzer,
        LayerValidator,
        ArchitectureReporter
    )
"""

# Pattern library exports
from .architecture_patterns import (
    # Enums
    ViolationSeverity,
    ViolationCategory,

    # Data structures
    ArchitecturePattern,

    # Patterns
    CIRCULAR_DEPENDENCIES,
    LAYERING_VIOLATIONS,
    GOD_MODULES,
    UNSTABLE_DEPENDENCIES,
    FEATURE_ENVY,
    INAPPROPRIATE_INTIMACY,

    # Pattern collections
    ARCHITECTURE_PATTERNS,
    PATTERNS_BY_ID,
    PATTERNS_BY_CATEGORY,
    PATTERNS_BY_SEVERITY,

    # Utility functions
    get_pattern,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_all_patterns,
    validate_pattern
)

# Agent exports
from .architecture_agents import (
    # Agents
    DependencyAnalyzer,
    LayerValidator,
    ArchitectureReporter,

    # Data structures
    ViolationFinding,
    DependencyMetrics,
    DependencyAnalysis,
    LayerRule,
    RemediationAction,
    ArchitectureReport
)

__all__ = [
    # Enums
    'ViolationSeverity',
    'ViolationCategory',

    # Data structures (patterns)
    'ArchitecturePattern',

    # Patterns
    'CIRCULAR_DEPENDENCIES',
    'LAYERING_VIOLATIONS',
    'GOD_MODULES',
    'UNSTABLE_DEPENDENCIES',
    'FEATURE_ENVY',
    'INAPPROPRIATE_INTIMACY',

    # Pattern collections
    'ARCHITECTURE_PATTERNS',
    'PATTERNS_BY_ID',
    'PATTERNS_BY_CATEGORY',
    'PATTERNS_BY_SEVERITY',

    # Utility functions
    'get_pattern',
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_all_patterns',
    'validate_pattern',

    # Agents
    'DependencyAnalyzer',
    'LayerValidator',
    'ArchitectureReporter',

    # Data structures (agents)
    'ViolationFinding',
    'DependencyMetrics',
    'DependencyAnalysis',
    'LayerRule',
    'RemediationAction',
    'ArchitectureReport'
]
