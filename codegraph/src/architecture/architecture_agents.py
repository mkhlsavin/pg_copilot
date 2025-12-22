"""Architecture Agents - Backward Compatibility Facade.

This module re-exports from src.architecture.agents for backward compatibility.
New code should import directly from src.architecture.agents.

Example:
    # Old import (still works)
    from src.architecture.architecture_agents import DependencyAnalyzer

    # New import (preferred)
    from src.architecture.agents import DependencyAnalyzer
"""

from src.architecture.agents import (
    # Agents
    DependencyAnalyzer,
    LayerValidator,
    ArchitectureReporter,
    # Models
    ViolationFinding,
    DependencyMetrics,
    DependencyAnalysis,
    LayerRule,
    RemediationAction,
    ArchitectureReport,
)

__all__ = [
    # Agents
    "DependencyAnalyzer",
    "LayerValidator",
    "ArchitectureReporter",
    # Models
    "ViolationFinding",
    "DependencyMetrics",
    "DependencyAnalysis",
    "LayerRule",
    "RemediationAction",
    "ArchitectureReport",
]
