"""
Code Review Module - Scenario 9: Code Review Automation

Provides automated code review capabilities for pull requests:
- PR diff parsing and change extraction
- CPG context aggregation for changed code
- Automated review comment generation
- Integration with security, performance, architecture, and debt analysis

Components:
- review_agents: PRAnalyzer, ContextAggregator, ReviewReporter

Usage:
    from src.code_review import (
        PRAnalyzer,
        ContextAggregator,
        ReviewReporter,
        ReviewAction
    )
"""

# Agent exports
from .review_agents import (
    # Enums
    ChangeType,
    ReviewSeverity,
    ReviewAction,

    # Data structures
    ChangedFile,
    ChangedMethod,
    MethodContext,
    ReviewFinding,
    ReviewComment,
    ReviewReport,

    # Agents
    PRAnalyzer,
    ContextAggregator,
    ReviewReporter
)

__all__ = [
    # Enums
    'ChangeType',
    'ReviewSeverity',
    'ReviewAction',

    # Data structures
    'ChangedFile',
    'ChangedMethod',
    'MethodContext',
    'ReviewFinding',
    'ReviewComment',
    'ReviewReport',

    # Agents
    'PRAnalyzer',
    'ContextAggregator',
    'ReviewReporter'
]
