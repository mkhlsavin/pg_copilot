"""
Automated Patch-Based Code Review System

This module provides comprehensive patch review capabilities:
- Multi-source patch parsing (git diff, GitHub PR, GitLab MR)
- Delta CPG generation (virtual graph overlay)
- Impact analysis (call graph, data flow, control flow, dependency)
- Verdict generation (security, performance, errors, architecture)
- Configurable review policies and output formats

Usage:
    from src.patch_review import ReviewWorkflow, PatchParser, ReviewPolicy
    import duckdb

    # Connect to CPG database
    conn = duckdb.connect('cpg.duckdb')

    # Create workflow
    workflow = ReviewWorkflow(conn)

    # Review a git diff
    verdict = workflow.run('git_diff', {'diff': diff_text})

    # Or review a GitHub PR
    verdict = workflow.run('github_pr', {'pr_number': 123, ...})

    # Format output
    from src.patch_review.formatters import MarkdownFormatter
    report = MarkdownFormatter().format_full_report(verdict)
"""

from src.patch_review.models import (
    # Enums
    ChangeType,
    Severity,
    Recommendation,
    FindingCategory,
    ReviewStatus,

    # Patch representation
    HunkChange,
    FileDiff,
    ChangedMethod,
    PatchContext,

    # Delta CPG
    DeltaNode,
    DeltaEdge,
    DeltaCPG,

    # Impact analysis
    BlastRadius,
    RippleEffect,
    BreakingChange,
    TaintPathFinding,
    SanitizationBypass,

    # Findings and verdicts
    Finding,
    SecurityVerdict,
    PerformanceVerdict,
    ErrorVerdict,
    ArchitectureVerdict,
    ComplexityDelta,

    # Policy and final verdict
    PolicyRule,
    ReviewPolicy,
    ReviewVerdict,
    ReviewSession,
)

# Core components
from src.patch_review.patch_parser import PatchParser
from src.patch_review.delta_cpg_generator import DeltaCPGGenerator

# Workflow
from src.patch_review.workflow import ReviewWorkflow

# Aggregation
from src.patch_review.aggregation import VerdictAggregator, AggregationConfig

# Integrations
from src.patch_review.integrations import (
    GitHubIntegration,
    GitHubConfig,
    GitLabIntegration,
    GitLabConfig,
)

# Formatters
from src.patch_review.formatters import (
    JSONFormatter,
    MarkdownFormatter,
    PRCommentFormatter,
)

__all__ = [
    # Enums
    'ChangeType',
    'Severity',
    'Recommendation',
    'FindingCategory',
    'ReviewStatus',

    # Patch representation
    'HunkChange',
    'FileDiff',
    'ChangedMethod',
    'PatchContext',

    # Delta CPG
    'DeltaNode',
    'DeltaEdge',
    'DeltaCPG',

    # Impact analysis
    'BlastRadius',
    'RippleEffect',
    'BreakingChange',
    'TaintPathFinding',
    'SanitizationBypass',

    # Findings and verdicts
    'Finding',
    'SecurityVerdict',
    'PerformanceVerdict',
    'ErrorVerdict',
    'ArchitectureVerdict',
    'ComplexityDelta',

    # Policy and final verdict
    'PolicyRule',
    'ReviewPolicy',
    'ReviewVerdict',
    'ReviewSession',

    # Core components
    'PatchParser',
    'DeltaCPGGenerator',

    # Workflow
    'ReviewWorkflow',

    # Aggregation
    'VerdictAggregator',
    'AggregationConfig',

    # Integrations
    'GitHubIntegration',
    'GitHubConfig',
    'GitLabIntegration',
    'GitLabConfig',

    # Formatters
    'JSONFormatter',
    'MarkdownFormatter',
    'PRCommentFormatter',
]

__version__ = '0.1.0'
