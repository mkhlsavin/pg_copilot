"""
Refactoring Module for CPG Analysis

Provides code smell detection, refactoring patterns, and analysis tools.

Week 6: Enhanced Refactoring with Specialized Agents
- TechnicalDebtDetector: Detect code smells using patterns
- ImpactAnalyzer: Analyze change impact and dependencies
- RefactoringPlanner: Create prioritized refactoring plans
"""

from .refactoring_patterns import (
    RefactoringPattern,
    CodeSmellSeverity,
    CodeSmellCategory,
    REFACTORING_PATTERNS,
    get_pattern_by_id,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_critical_patterns,
    get_all_cpgql_queries,
    get_pattern_summary,
    validate_pattern,
    validate_all_patterns,
)

from .refactoring_agents import (
    TechnicalDebtDetector,
    DeadCodeDetector,  # Sprint 1 - Scenario 5 Enhancement
    ImpactAnalyzer,
    RefactoringPlanner,
    CodeSmellFinding,
    DeadCodeFinding,  # Sprint 1 - Scenario 5 Enhancement
    DependencyInfo,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
    run_complete_refactoring_analysis,
)

__all__ = [
    # Patterns
    "RefactoringPattern",
    "CodeSmellSeverity",
    "CodeSmellCategory",
    "REFACTORING_PATTERNS",
    "get_pattern_by_id",
    "get_patterns_by_category",
    "get_patterns_by_severity",
    "get_critical_patterns",
    "get_all_cpgql_queries",
    "get_pattern_summary",
    "validate_pattern",
    "validate_all_patterns",
    # Agents
    "TechnicalDebtDetector",
    "DeadCodeDetector",  # Sprint 1 - Scenario 5 Enhancement
    "ImpactAnalyzer",
    "RefactoringPlanner",
    # Data structures
    "CodeSmellFinding",
    "DeadCodeFinding",  # Sprint 1 - Scenario 5 Enhancement
    "DependencyInfo",
    "ImpactAnalysis",
    "RefactoringTask",
    "RefactoringReport",
    # Utilities
    "run_complete_refactoring_analysis",
]
