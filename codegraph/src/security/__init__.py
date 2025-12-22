"""
Security Module for CPG Analysis

Provides:
1. Security vulnerability patterns, detection queries, and analysis tools
2. Enterprise LLM Data Protection (DLP, SIEM, Vault)

Week 5: Enhanced Security Audit with Specialized Agents
- SecurityScanner: Query CPG for vulnerabilities
- DataFlowAnalyzer: Trace taint flows
- VulnerabilityReporter: Generate structured reports
- RemediationAdvisor: Suggest fixes

D3FEND Source Code Hardening (hardening submodule):
- HardeningScanner: Scan for D3FEND compliance
- HardeningCheck: Check definitions with CPGQL queries
- HardeningFinding: Compliance violations

Enterprise LLM Security (config, siem, dlp, llm, vault submodules):
- SecureLLMProvider: Security wrapper for LLM providers
- SIEMDispatcher: Real-time log dispatch (SysLog, CEF, LEEF)
- ContentScanner: DLP pattern scanning
- VaultClient: HashiCorp Vault integration
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

# D3FEND Source Code Hardening
from .hardening import (
    HardeningScanner,
    HardeningCheck,
    HardeningCategory,
    HardeningSeverity,
    HardeningFinding,
    D3FEND_TECHNIQUES,
    D3FEND_TECHNIQUE_IDS,
    HARDENING_CHECKS,
    get_check_by_id,
    get_checks_by_category,
    get_checks_by_d3fend_id,
    get_all_checks,
    get_checks_for_language,
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
    # D3FEND Hardening
    "HardeningScanner",
    "HardeningCheck",
    "HardeningCategory",
    "HardeningSeverity",
    "HardeningFinding",
    "D3FEND_TECHNIQUES",
    "D3FEND_TECHNIQUE_IDS",
    "HARDENING_CHECKS",
    "get_check_by_id",
    "get_checks_by_category",
    "get_checks_by_d3fend_id",
    "get_all_checks",
    "get_checks_for_language",
    # Enterprise LLM Security - Config
    "SecurityConfig",
    "SIEMConfig",
    "DLPConfig",
    "DLPAction",
    "VaultConfig",
    "LLMLoggingConfig",
    "get_security_config",
    # Enterprise LLM Security - SIEM
    "SecurityEvent",
    "SecurityEventType",
    "SIEMDispatcher",
    "init_siem_dispatcher",
    "get_siem_dispatcher",
    # Enterprise LLM Security - DLP
    "ContentScanner",
    "ScanResult",
    "DLPBlockedException",
    "DLPMatch",
    # Enterprise LLM Security - LLM
    "SecureLLMProvider",
    "LLMSecurityLogger",
    # Enterprise LLM Security - Vault
    "VaultClient",
    "VaultError",
    "SecretManager",
    # Taint-Verified Scanner
    "TaintVerifiedScanner",
    "SecurityRelevantCallsFilter",
    "VerifiedFinding",
    "PYTHON_TAINT_SOURCES",
    "PYTHON_SQL_SINKS",
    "integrate_with_report_generator",
    # SAST Comparison
    "SASTComparator",
    "SASTFinding",
    "ComparisonResult",
    "install_sast_tools",
    # Report generation
    "SecurityAuditReport",
    "ReportLocalizer",
    "get_localizer",
]


# =============================================================================
# Enterprise LLM Security Imports
# =============================================================================

# Configuration
from .config import (
    SecurityConfig,
    SIEMConfig,
    DLPConfig,
    DLPAction,
    VaultConfig,
    LLMLoggingConfig,
    get_security_config,
)

# SIEM
from .siem import (
    SecurityEvent,
    SecurityEventType,
    SIEMDispatcher,
    init_siem_dispatcher,
    get_siem_dispatcher,
)

# DLP
from .dlp import (
    ContentScanner,
    ScanResult,
    DLPBlockedException,
    DLPMatch,
)

# LLM Security
from .llm import (
    SecureLLMProvider,
    LLMSecurityLogger,
)

# Vault
from .vault import (
    VaultClient,
    VaultError,
    SecretManager,
)

# Taint-Verified Scanner
from .taint_verified_scanner import (
    TaintVerifiedScanner,
    SecurityRelevantCallsFilter,
    VerifiedFinding,
    PYTHON_TAINT_SOURCES,
    PYTHON_SQL_SINKS,
    integrate_with_report_generator,
)

# SAST Comparison
from .sast_comparison import (
    SASTComparator,
    SASTFinding,
    ComparisonResult,
    install_sast_tools,
)

# Report generation
from .report_generator import (
    SecurityAuditReport,
)

from .report_localizer import (
    ReportLocalizer,
    get_localizer,
)
