"""
Multi-Criteria Hypothesis Generation for Security Analysis.

This package implements a hypothesis-driven approach to security vulnerability
detection, combining CWE/CAPEC knowledge bases with CPG (Code Property Graph)
analysis via DuckDB SQL/PGQ queries.

Main Components:
- models.py: Data structures (Hypothesis, Evidence, CWE, CAPEC)
- knowledge_base.py: CWE/CAPEC database and language patterns
- hypothesis_generator.py: Hypothesis generation algorithm
- multi_criteria_scorer.py: Priority scoring engine
- query_synthesizer.py: DuckDB SQL/PGQ query generation
- query_templates.py: SQL/PGQ templates by vulnerability type
- executor.py: DuckDB query execution
- validator.py: CVE validation logic
- providers/: Plugin interface for project-specific patterns

Providers (Plugins):
- postgresql/: PostgreSQL-specific patterns and CVE detection

Usage:
    from src.security.hypothesis import (
        SecurityKnowledgeBase,
        SecurityHypothesis,
        HypothesisGenerator,
        MultiCriteriaScorer,
        get_knowledge_base,
    )

    # Get knowledge base (auto-loads registered providers)
    kb = get_knowledge_base()

    # Generate hypotheses for C codebase
    generator = HypothesisGenerator(kb)
    hypotheses = generator.generate_hypotheses(language="C")

    # Score and prioritize
    scorer = MultiCriteriaScorer(kb)
    for h in hypotheses:
        h.priority_score = scorer.score_hypothesis(h)

    # Execute queries against DuckDB CPG
    from src.security.hypothesis.executor import QueryExecutor
    executor = QueryExecutor("postgresql.cpg.duckdb")
    for h in hypotheses[:10]:  # Top 10
        results = executor.execute(h.sql_query)
        if results:
            h.validation_status = ValidationStatus.CONFIRMED
"""

from .models import (
    # Enums
    Severity,
    ValidationStatus,
    EvaluationStrategy,
    # Data Classes
    CWEEntry,
    CAPECPattern,
    LanguagePattern,
    Evidence,
    SecurityHypothesis,
    HypothesisBatch,
    ValidationResults,
)

# Import providers module first to register the provider interface
from .providers import PatternProvider, ProviderRegistry

# Import postgresql to auto-register PostgreSQLPatternProvider
from . import postgresql

from .knowledge_base import (
    # Database dictionaries
    CWE_DATABASE,
    CAPEC_DATABASE,
    C_DANGEROUS_SINKS,
    C_TAINT_SOURCES,
    C_SANITIZERS,
    C_LANGUAGE_PATTERNS,
    # Class and factory
    SecurityKnowledgeBase,
    get_knowledge_base,
)

from .hypothesis_generator import (
    HypothesisGenerator,
    generate_postgresql_hypotheses,
)

from .multi_criteria_scorer import (
    CodebaseStats,
    MultiCriteriaScorer,
    compute_codebase_stats_from_duckdb,
)

from .query_synthesizer import (
    QuerySynthesizer,
    synthesize_queries_for_batch,
)

from .query_templates import (
    SQL_TEMPLATES,
    PGQ_TEMPLATES,
    TEMPLATE_CATEGORIES,
    get_template,
    get_pgq_template,
    get_category_defaults,
)

from .executor import (
    QueryResult,
    QueryExecutor,
)

from .validator import (
    HypothesisValidator,
    validate_postgresql_security,
    generate_validation_report,
)

__all__ = [
    # Enums
    "Severity",
    "ValidationStatus",
    "EvaluationStrategy",
    # Data Classes
    "CWEEntry",
    "CAPECPattern",
    "LanguagePattern",
    "Evidence",
    "SecurityHypothesis",
    "HypothesisBatch",
    "ValidationResults",
    # Providers (Plugin System)
    "PatternProvider",
    "ProviderRegistry",
    # Knowledge Base
    "CWE_DATABASE",
    "CAPEC_DATABASE",
    "C_DANGEROUS_SINKS",
    "C_TAINT_SOURCES",
    "C_SANITIZERS",
    "C_LANGUAGE_PATTERNS",
    "SecurityKnowledgeBase",
    "get_knowledge_base",
    # Hypothesis Generator
    "HypothesisGenerator",
    "generate_postgresql_hypotheses",
    # Multi-Criteria Scorer
    "CodebaseStats",
    "MultiCriteriaScorer",
    "compute_codebase_stats_from_duckdb",
    # Query Synthesizer
    "QuerySynthesizer",
    "synthesize_queries_for_batch",
    # Query Templates
    "SQL_TEMPLATES",
    "PGQ_TEMPLATES",
    "TEMPLATE_CATEGORIES",
    "get_template",
    "get_pgq_template",
    "get_category_defaults",
    # Executor
    "QueryResult",
    "QueryExecutor",
    # Validator
    "HypothesisValidator",
    "validate_postgresql_security",
    "generate_validation_report",
]
