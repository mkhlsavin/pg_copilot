"""Refactoring Agents Package.

Specialized agents for code smell detection, impact analysis,
and refactoring planning.

Main components:
- TechnicalDebtDetector: Detect code smells using pattern library
- DeadCodeDetector: Specialized agent for dead code detection
- ImpactAnalyzer: Analyze change impact and dependencies
- RefactoringPlanner: Create prioritized refactoring plans

Example usage:
    from src.refactoring.agents import (
        TechnicalDebtDetector,
        ImpactAnalyzer,
        RefactoringPlanner,
        run_complete_refactoring_analysis,
    )

    # Run complete analysis
    report, tasks = run_complete_refactoring_analysis()

    # Or use individual agents
    with TechnicalDebtDetector() as detector:
        findings = detector.detect_all_smells()
"""

from .models import (
    CodeSmellFinding,
    DeadCodeFinding,
    DependencyInfo,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
)
from .debt_detector import TechnicalDebtDetector
from .dead_code import DeadCodeDetector
from .impact import ImpactAnalyzer
from .planner import RefactoringPlanner, run_complete_refactoring_analysis

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
