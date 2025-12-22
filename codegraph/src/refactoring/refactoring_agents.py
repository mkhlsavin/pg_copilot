"""Refactoring Agents - Backward Compatibility Facade.

This module re-exports from src.refactoring.agents for backward compatibility.
New code should import directly from src.refactoring.agents.

Example:
    # Old import (still works)
    from src.refactoring.refactoring_agents import TechnicalDebtDetector

    # New import (preferred)
    from src.refactoring.agents import TechnicalDebtDetector
"""

from src.refactoring.agents import (
    # Data models
    CodeSmellFinding,
    DeadCodeFinding,
    DependencyInfo,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
    # Agents
    TechnicalDebtDetector,
    DeadCodeDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
    # Utility
    run_complete_refactoring_analysis,
)

__all__ = [
    # Data models
    "CodeSmellFinding",
    "DeadCodeFinding",
    "DependencyInfo",
    "ImpactAnalysis",
    "RefactoringTask",
    "RefactoringReport",
    # Agents
    "TechnicalDebtDetector",
    "DeadCodeDetector",
    "ImpactAnalyzer",
    "RefactoringPlanner",
    # Utility
    "run_complete_refactoring_analysis",
]
