"""
Security Incident Response Module - Scenario 14

Provides automated security incident response for:
- Vulnerability detection (OWASP Top 10, CVEs)
- Blast radius analysis
- Impact assessment
- Remediation planning

Components:
- CVESearcher: Pattern-based vulnerability detection
- BlastRadiusAnalyzer: Calculate incident impact scope
- RemediationPlanner: Generate patches and remediation plans

Usage:
    from src.security_incident import (
        CVESearcher,
        BlastRadiusAnalyzer,
        RemediationPlanner,
        VulnerabilitySeverity
    )
"""

# Pattern exports
from .vulnerability_patterns import (
    VulnerabilityPattern,
    VulnerabilitySeverity,
    VulnerabilityCategory,
    INJECTION_PATTERNS,
    XSS_PATTERNS,
    AUTH_PATTERNS,
    MEMORY_PATTERNS,
    ALL_VULNERABILITY_PATTERNS,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_owasp_top_10,
)

# Agent exports
from .incident_agents import (
    VulnerabilityFinding,
    BlastRadius,
    RemediationAction,
    IncidentReport,
    CVESearcher,
    BlastRadiusAnalyzer,
    RemediationPlanner,
)

__all__ = [
    # Enums
    'VulnerabilitySeverity',
    'VulnerabilityCategory',

    # Data structures
    'VulnerabilityPattern',
    'VulnerabilityFinding',
    'BlastRadius',
    'RemediationAction',
    'IncidentReport',

    # Pattern libraries
    'INJECTION_PATTERNS',
    'XSS_PATTERNS',
    'AUTH_PATTERNS',
    'MEMORY_PATTERNS',
    'ALL_VULNERABILITY_PATTERNS',

    # Helper functions
    'get_patterns_by_category',
    'get_patterns_by_severity',
    'get_owasp_top_10',

    # Agents
    'CVESearcher',
    'BlastRadiusAnalyzer',
    'RemediationPlanner',
]
