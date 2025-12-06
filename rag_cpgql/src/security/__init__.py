"""
Security Module for CPG Analysis

Provides security vulnerability patterns, detection queries, and analysis tools.

Week 5: Enhanced Security Audit with Specialized Agents
- SecurityScanner: Query CPG for vulnerabilities
- DataFlowAnalyzer: Trace taint flows
- VulnerabilityReporter: Generate structured reports
- RemediationAdvisor: Suggest fixes
"""

from .security_patterns import (
    SecurityPattern,
    VulnerabilitySeverity,
    VulnerabilityCategory,
    SECURITY_PATTERNS,
    get_pattern_by_id,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_critical_patterns,
    get_all_cpgql_queries,
    get_pattern_summary,
    validate_pattern,
    validate_all_patterns,
)

from .security_agents import (
    SecurityScanner,
    DataFlowAnalyzer,
    VulnerabilityReporter,
    RemediationAdvisor,
    SecurityFinding,
    DataFlowPath,
    VulnerabilityReport,
    RemediationAdvice,
    run_complete_security_audit,
)

__all__ = [
    # Patterns
    "SecurityPattern",
    "VulnerabilitySeverity",
    "VulnerabilityCategory",
    "SECURITY_PATTERNS",
    "get_pattern_by_id",
    "get_patterns_by_category",
    "get_patterns_by_severity",
    "get_critical_patterns",
    "get_all_cpgql_queries",
    "get_pattern_summary",
    "validate_pattern",
    "validate_all_patterns",
    # Agents
    "SecurityScanner",
    "DataFlowAnalyzer",
    "VulnerabilityReporter",
    "RemediationAdvisor",
    # Data structures
    "SecurityFinding",
    "DataFlowPath",
    "VulnerabilityReport",
    "RemediationAdvice",
    # Utilities
    "run_complete_security_audit",
]
