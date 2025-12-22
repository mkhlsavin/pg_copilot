"""
Cross-Repository Analysis Module - Scenario 10

Provides automated cross-repository analysis for:
- Repository discovery and indexing
- Code duplication detection
- Inter-repository dependencies
- Consolidation opportunities

Components:
- RepositoryIndexer: Catalog and index multiple repositories
- CrossRepoAnalyzer: Detect code duplication across repos
- DependencyMapper: Map inter-repository dependencies

Usage:
    from src.cross_repo import (
        RepositoryIndexer,
        CrossRepoAnalyzer,
        DependencyMapper,
        DuplicationSeverity
    )
"""

# Pattern exports
from .repo_patterns import (
    RepositoryInfo,
    CodeInstance,
    CodeDuplication,
    DependencyCall,
    CrossRepoDependency,
    ConsolidationOpportunity,
    ConsolidationReport,
    DuplicationSeverity,
    DependencyType,
    RiskLevel,
    DUPLICATION_PATTERNS,
    DEPENDENCY_PATTERNS,
    calculate_similarity,
    classify_duplication_severity,
    calculate_coupling_score,
    classify_risk_level,
)

# Agent exports
from .cross_repo_agents import (
    RepositoryIndexer,
    CrossRepoAnalyzer,
    DependencyMapper,
)

__all__ = [
    # Enums
    'DuplicationSeverity',
    'DependencyType',
    'RiskLevel',

    # Data structures
    'RepositoryInfo',
    'CodeInstance',
    'CodeDuplication',
    'DependencyCall',
    'CrossRepoDependency',
    'ConsolidationOpportunity',
    'ConsolidationReport',

    # Pattern libraries
    'DUPLICATION_PATTERNS',
    'DEPENDENCY_PATTERNS',

    # Helper functions
    'calculate_similarity',
    'classify_duplication_severity',
    'calculate_coupling_score',
    'classify_risk_level',

    # Agents
    'RepositoryIndexer',
    'CrossRepoAnalyzer',
    'DependencyMapper',
]
