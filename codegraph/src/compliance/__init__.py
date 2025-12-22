"""
Compliance Module - Scenario 8: Regulatory Compliance

Provides automated compliance checking for:
- License compliance (SPDX, GPL conflicts)
- Data privacy (GDPR, HIPAA)
- Security standards (OWASP, CWE)
- Coding standards (documentation, naming, complexity)

Components:
- LicenseDetector: License scanning and conflict detection
- ComplianceValidator: Privacy and security validation
- StandardsChecker: Coding standards enforcement

Usage:
    from src.compliance import (
        LicenseDetector,
        ComplianceValidator,
        StandardsChecker,
        ComplianceSeverity,
        ComplianceCategory
    )
"""

# Pattern exports
from .compliance_patterns import (
    ComplianceRule,
    ComplianceSeverity,
    ComplianceCategory,
    LICENSE_RULES,
    PRIVACY_RULES,
    SECURITY_RULES,
    STANDARDS_RULES,
    ALL_COMPLIANCE_RULES,
    get_rules_by_category,
    get_rules_by_severity,
)

# Agent exports
from .compliance_agents import (
    ComplianceViolation,
    LicenseInfo,
    ComplianceReport,
    LicenseDetector,
    ComplianceValidator,
    StandardsChecker,
)

__all__ = [
    # Enums
    'ComplianceSeverity',
    'ComplianceCategory',

    # Data structures
    'ComplianceRule',
    'ComplianceViolation',
    'LicenseInfo',
    'ComplianceReport',

    # Pattern libraries
    'LICENSE_RULES',
    'PRIVACY_RULES',
    'SECURITY_RULES',
    'STANDARDS_RULES',
    'ALL_COMPLIANCE_RULES',

    # Helper functions
    'get_rules_by_category',
    'get_rules_by_severity',

    # Agents
    'LicenseDetector',
    'ComplianceValidator',
    'StandardsChecker',
]
