"""
Compliance Patterns Library - Scenario 8: Regulatory Compliance

Defines compliance rules for:
- License compliance (SPDX, GPL conflicts, missing headers)
- Data privacy (GDPR, HIPAA, PII handling)
- Security compliance (hardcoded secrets, banned APIs)
- Coding standards (naming conventions, documentation)

Author: Compliance Team
Date: 2025-11-22
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


# ============================================================================
# ENUMS
# ============================================================================

class ComplianceSeverity(Enum):
    """Severity of compliance violation"""
    CRITICAL = "critical"    # Legal/regulatory risk
    HIGH = "high"            # Must fix before release
    MEDIUM = "medium"        # Should fix
    LOW = "low"              # Nice to have
    INFO = "info"            # Informational


class ComplianceCategory(Enum):
    """Category of compliance rule"""
    LICENSE = "license"
    PRIVACY = "privacy"
    SECURITY = "security"
    STANDARDS = "standards"
    DOCUMENTATION = "documentation"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ComplianceRule:
    """
    A compliance rule definition.

    Attributes:
        rule_id: Unique identifier
        name: Human-readable name
        category: Rule category
        severity: Violation severity
        description: What this rule checks
        pattern: Detection pattern (regex or SQL)
        remediation: How to fix violations
        references: Regulatory references
    """
    rule_id: str
    name: str
    category: ComplianceCategory
    severity: ComplianceSeverity
    description: str
    pattern: str
    remediation: str
    references: List[str]


# ============================================================================
# LICENSE COMPLIANCE RULES
# ============================================================================

LICENSE_RULES = {
    "MISSING_LICENSE_HEADER": ComplianceRule(
        rule_id="LIC-001",
        name="Missing License Header",
        category=ComplianceCategory.LICENSE,
        severity=ComplianceSeverity.HIGH,
        description="Source file missing license header",
        pattern=r"^(?!.*(?:Copyright|License|SPDX-License-Identifier)).*",
        remediation="Add appropriate license header at top of file",
        references=[
            "https://spdx.org/licenses/",
            "https://opensource.org/licenses"
        ]
    ),

    "GPL_CONFLICT": ComplianceRule(
        rule_id="LIC-002",
        name="GPL License Conflict",
        category=ComplianceCategory.LICENSE,
        severity=ComplianceSeverity.CRITICAL,
        description="GPL-licensed code in proprietary codebase",
        pattern=r"(?i)(GPL|GNU General Public License)",
        remediation="Remove GPL code or relicense project as GPL",
        references=[
            "https://www.gnu.org/licenses/gpl-faq.html",
            "https://opensource.org/licenses/gpl-license"
        ]
    ),

    "INCOMPATIBLE_LICENSES": ComplianceRule(
        rule_id="LIC-003",
        name="Incompatible License Combination",
        category=ComplianceCategory.LICENSE,
        severity=ComplianceSeverity.CRITICAL,
        description="Mixing incompatible licenses (e.g., Apache 2.0 + GPL 2.0)",
        pattern=r"(?i)(Apache-2\.0.*GPL-2\.0|GPL-2\.0.*Apache-2\.0)",
        remediation="Ensure all dependencies use compatible licenses",
        references=[
            "https://www.apache.org/licenses/GPL-compatibility.html"
        ]
    ),

    "UNLICENSED_DEPENDENCY": ComplianceRule(
        rule_id="LIC-004",
        name="Unlicensed Dependency",
        category=ComplianceCategory.LICENSE,
        severity=ComplianceSeverity.HIGH,
        description="Third-party dependency without clear license",
        pattern=r"(?i)(no license|unlicensed|license unknown)",
        remediation="Contact dependency maintainer for license clarification",
        references=[
            "https://choosealicense.com/"
        ]
    ),
}


# ============================================================================
# PRIVACY COMPLIANCE RULES (GDPR, HIPAA)
# ============================================================================

PRIVACY_RULES = {
    "PII_WITHOUT_ENCRYPTION": ComplianceRule(
        rule_id="PII-001",
        name="PII Without Encryption",
        category=ComplianceCategory.PRIVACY,
        severity=ComplianceSeverity.CRITICAL,
        description="Personally Identifiable Information stored without encryption",
        pattern="""
        -- Find variables/fields storing PII without encryption
        SELECT
            l.name,
            l.filename,
            l.line_number
        FROM nodes_local l
        WHERE (
            l.name ILIKE '%email%' OR
            l.name ILIKE '%ssn%' OR
            l.name ILIKE '%password%' OR
            l.name ILIKE '%credit_card%' OR
            l.name ILIKE '%phone%'
        )
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call c
            WHERE c.name ILIKE '%encrypt%'
            AND c.line_number BETWEEN l.line_number - 5 AND l.line_number + 5
        )
        LIMIT 20
        """,
        remediation="Encrypt PII data at rest and in transit",
        references=[
            "https://gdpr.eu/encryption/",
            "https://www.hhs.gov/hipaa/for-professionals/security/index.html"
        ]
    ),

    "MISSING_DATA_RETENTION": ComplianceRule(
        rule_id="PII-002",
        name="Missing Data Retention Policy",
        category=ComplianceCategory.PRIVACY,
        severity=ComplianceSeverity.HIGH,
        description="Data storage without retention/deletion mechanism",
        pattern="""
        -- Find database inserts without corresponding delete logic
        SELECT DISTINCT
            m.name,
            m.filename,
            m.line_number
        FROM nodes_method m
        WHERE EXISTS (
            SELECT 1 FROM nodes_call c
            WHERE c.name ILIKE '%insert%' OR c.name ILIKE '%save%'
        )
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call c2
            WHERE c2.name ILIKE '%delete%' OR c2.name ILIKE '%expire%' OR c2.name ILIKE '%purge%'
        )
        LIMIT 20
        """,
        remediation="Implement data retention and deletion policies per GDPR Article 5",
        references=[
            "https://gdpr.eu/article-5-how-to-process-personal-data/",
            "https://gdpr.eu/right-to-be-forgotten/"
        ]
    ),

    "LOGGING_SENSITIVE_DATA": ComplianceRule(
        rule_id="PII-003",
        name="Logging Sensitive Data",
        category=ComplianceCategory.PRIVACY,
        severity=ComplianceSeverity.CRITICAL,
        description="Sensitive data (PII, passwords) logged to files",
        pattern="""
        -- Find logging statements with sensitive variables
        SELECT
            c.name,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE (
            c.name ILIKE '%log%' OR
            c.name ILIKE '%print%' OR
            c.name ILIKE '%debug%'
        )
        AND (
            c.code ILIKE '%password%' OR
            c.code ILIKE '%ssn%' OR
            c.code ILIKE '%credit_card%' OR
            c.code ILIKE '%secret%' OR
            c.code ILIKE '%token%'
        )
        LIMIT 20
        """,
        remediation="Remove sensitive data from logs or mask/redact before logging",
        references=[
            "https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure"
        ]
    ),

    "MISSING_CONSENT_CHECK": ComplianceRule(
        rule_id="PII-004",
        name="Missing User Consent Check",
        category=ComplianceCategory.PRIVACY,
        severity=ComplianceSeverity.HIGH,
        description="Data collection without user consent verification",
        pattern="""
        -- Find data collection without consent check
        SELECT
            m.name,
            m.filename,
            m.line_number
        FROM nodes_method m
        WHERE EXISTS (
            SELECT 1 FROM nodes_call c
            WHERE (c.name ILIKE '%collect%' OR c.name ILIKE '%track%')
        )
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call c2
            WHERE c2.name ILIKE '%consent%' OR c2.name ILIKE '%permission%'
        )
        LIMIT 20
        """,
        remediation="Implement consent collection per GDPR Article 7",
        references=[
            "https://gdpr.eu/article-7-how-to-get-consent-to-collect-personal-data/"
        ]
    ),
}


# ============================================================================
# SECURITY COMPLIANCE RULES
# ============================================================================

SECURITY_RULES = {
    "HARDCODED_CREDENTIALS": ComplianceRule(
        rule_id="SEC-001",
        name="Hardcoded Credentials",
        category=ComplianceCategory.SECURITY,
        severity=ComplianceSeverity.CRITICAL,
        description="Hardcoded passwords, API keys, or secrets in code",
        pattern=r'(?i)(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
        remediation="Use environment variables or secure key management (e.g., HashiCorp Vault)",
        references=[
            "https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication",
            "https://cwe.mitre.org/data/definitions/798.html"
        ]
    ),

    "BANNED_CRYPTO_ALGORITHM": ComplianceRule(
        rule_id="SEC-002",
        name="Banned Cryptographic Algorithm",
        category=ComplianceCategory.SECURITY,
        severity=ComplianceSeverity.CRITICAL,
        description="Use of weak/banned crypto (MD5, SHA1, DES)",
        pattern="""
        -- Find usage of weak crypto algorithms
        SELECT
            c.name,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE
            c.name ILIKE '%md5%' OR
            c.name ILIKE '%sha1%' OR
            c.name ILIKE '%des%' OR
            c.code ILIKE '%MD5%' OR
            c.code ILIKE '%SHA1%' OR
            c.code ILIKE '%DES%'
        LIMIT 20
        """,
        remediation="Use approved algorithms: AES-256, SHA-256, SHA-384, SHA-512",
        references=[
            "https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines",
            "https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure"
        ]
    ),

    "INSUFFICIENT_RANDOMNESS": ComplianceRule(
        rule_id="SEC-003",
        name="Insufficient Randomness",
        category=ComplianceCategory.SECURITY,
        severity=ComplianceSeverity.HIGH,
        description="Use of weak random number generator for security purposes",
        pattern="""
        -- Find non-cryptographic random usage in security context
        SELECT
            c.name,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE (
            c.name ILIKE '%rand%' AND
            NOT c.name ILIKE '%crypto%'
        )
        AND (
            c.code ILIKE '%token%' OR
            c.code ILIKE '%session%' OR
            c.code ILIKE '%key%' OR
            c.code ILIKE '%nonce%'
        )
        LIMIT 20
        """,
        remediation="Use cryptographically secure random: os.urandom(), secrets module (Python)",
        references=[
            "https://cwe.mitre.org/data/definitions/338.html"
        ]
    ),

    "MISSING_INPUT_VALIDATION": ComplianceRule(
        rule_id="SEC-004",
        name="Missing Input Validation",
        category=ComplianceCategory.SECURITY,
        severity=ComplianceSeverity.HIGH,
        description="User input used without validation/sanitization",
        pattern="""
        -- Find user input without validation
        SELECT
            p.name,
            p.filename,
            p.line_number
        FROM nodes_method_parameter_in p
        WHERE NOT EXISTS (
            SELECT 1 FROM nodes_call c
            WHERE (
                c.name ILIKE '%validate%' OR
                c.name ILIKE '%sanitize%' OR
                c.name ILIKE '%escape%'
            )
        )
        LIMIT 20
        """,
        remediation="Validate and sanitize all user inputs",
        references=[
            "https://owasp.org/www-project-top-ten/2017/A1_2017-Injection"
        ]
    ),
}


# ============================================================================
# CODING STANDARDS RULES
# ============================================================================

STANDARDS_RULES = {
    "MISSING_DOCSTRING": ComplianceRule(
        rule_id="STD-001",
        name="Missing Function Documentation",
        category=ComplianceCategory.DOCUMENTATION,
        severity=ComplianceSeverity.MEDIUM,
        description="Public function/method without docstring",
        pattern="""
        -- Find public methods without documentation
        SELECT
            m.name,
            m.filename,
            m.line_number
        FROM nodes_method m
        WHERE NOT EXISTS (
            SELECT 1 FROM nodes_comment c
            WHERE c.line_number BETWEEN m.line_number - 5 AND m.line_number + 5
        )
        AND m.name NOT LIKE '__%'
        LIMIT 20
        """,
        remediation="Add docstring describing purpose, parameters, and return value",
        references=[
            "https://peps.python.org/pep-0257/",
            "https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings"
        ]
    ),

    "POOR_NAMING_CONVENTION": ComplianceRule(
        rule_id="STD-002",
        name="Poor Naming Convention",
        category=ComplianceCategory.STANDARDS,
        severity=ComplianceSeverity.LOW,
        description="Variable/function naming doesn't follow conventions",
        pattern=r"^[a-z][a-z0-9]*$",  # Simple snake_case check
        remediation="Follow language-specific naming conventions (snake_case for Python, camelCase for Java)",
        references=[
            "https://peps.python.org/pep-0008/#naming-conventions",
            "https://google.github.io/styleguide/"
        ]
    ),

    "EXCESSIVE_COMPLEXITY": ComplianceRule(
        rule_id="STD-003",
        name="Excessive Cyclomatic Complexity",
        category=ComplianceCategory.STANDARDS,
        severity=ComplianceSeverity.MEDIUM,
        description="Function complexity exceeds threshold (>20)",
        pattern="""
        -- Find methods with high complexity
        SELECT
            m.name,
            m.filename,
            m.line_number,
            t.value AS complexity
        FROM nodes_method m
        JOIN edges_tagged_by e ON e.src = m.id
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'cyclomatic-complexity'
        AND CAST(t.value AS INTEGER) > 20
        LIMIT 20
        """,
        remediation="Refactor into smaller, single-purpose functions",
        references=[
            "https://en.wikipedia.org/wiki/Cyclomatic_complexity",
            "https://refactoring.guru/extract-method"
        ]
    ),

    "MAGIC_NUMBERS": ComplianceRule(
        rule_id="STD-004",
        name="Magic Numbers",
        category=ComplianceCategory.STANDARDS,
        severity=ComplianceSeverity.LOW,
        description="Unexplained numeric literals in code",
        pattern=r"\b(?<![\w.])\d{2,}(?![\w.])\b",  # Numbers with 2+ digits
        remediation="Extract to named constants with descriptive names",
        references=[
            "https://refactoring.guru/replace-magic-number-with-symbolic-constant"
        ]
    ),
}


# ============================================================================
# ALL COMPLIANCE RULES
# ============================================================================

ALL_COMPLIANCE_RULES = {
    **LICENSE_RULES,
    **PRIVACY_RULES,
    **SECURITY_RULES,
    **STANDARDS_RULES,
}


def get_rules_by_category(category: ComplianceCategory) -> Dict[str, ComplianceRule]:
    """Get all rules for a specific category"""
    return {
        rule_id: rule
        for rule_id, rule in ALL_COMPLIANCE_RULES.items()
        if rule.category == category
    }


def get_rules_by_severity(min_severity: ComplianceSeverity) -> Dict[str, ComplianceRule]:
    """Get all rules meeting minimum severity"""
    severity_order = {
        ComplianceSeverity.INFO: 0,
        ComplianceSeverity.LOW: 1,
        ComplianceSeverity.MEDIUM: 2,
        ComplianceSeverity.HIGH: 3,
        ComplianceSeverity.CRITICAL: 4,
    }

    min_level = severity_order[min_severity]

    return {
        rule_id: rule
        for rule_id, rule in ALL_COMPLIANCE_RULES.items()
        if severity_order[rule.severity] >= min_level
    }
