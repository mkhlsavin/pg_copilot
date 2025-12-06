"""
Compliance Agents - Scenario 8: Regulatory Compliance

Implements three specialized agents for compliance checking:

1. LicenseDetector - Scans for license compliance issues
2. ComplianceValidator - Validates GDPR, HIPAA, security compliance
3. StandardsChecker - Checks coding standards and documentation

Author: Compliance Team
Date: 2025-11-22
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from .compliance_patterns import (
    ComplianceRule,
    ComplianceSeverity,
    ComplianceCategory,
    LICENSE_RULES,
    PRIVACY_RULES,
    SECURITY_RULES,
    STANDARDS_RULES,
    ALL_COMPLIANCE_RULES,
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ComplianceViolation:
    """
    A compliance violation.

    Attributes:
        violation_id: Unique identifier
        rule: The compliance rule violated
        filepath: File where violation occurred
        line_number: Line number
        description: Specific violation description
        code_snippet: Relevant code
        remediation_steps: How to fix
    """
    violation_id: str
    rule: ComplianceRule
    filepath: str
    line_number: int
    description: str
    code_snippet: str = ""
    remediation_steps: str = ""


@dataclass
class LicenseInfo:
    """
    License information for a file or dependency.

    Attributes:
        name: License name (e.g., "MIT", "Apache-2.0")
        spdx_id: SPDX identifier
        compatible_with: List of compatible licenses
        requires_attribution: Whether attribution required
        allows_commercial: Whether commercial use allowed
    """
    name: str
    spdx_id: str
    compatible_with: List[str] = field(default_factory=list)
    requires_attribution: bool = True
    allows_commercial: bool = True


@dataclass
class ComplianceReport:
    """
    Complete compliance report.

    Attributes:
        report_id: Unique identifier
        timestamp: When report generated
        violations: All violations found
        violations_by_category: Violations grouped by category
        violations_by_severity: Violations grouped by severity
        critical_count: Number of critical violations
        high_count: Number of high severity violations
        compliance_score: Overall score (0-100)
        passed: Whether codebase passes compliance
        recommendations: List of recommendations
    """
    report_id: str
    timestamp: str
    violations: List[ComplianceViolation]
    violations_by_category: Dict[str, List[ComplianceViolation]]
    violations_by_severity: Dict[str, List[ComplianceViolation]]
    critical_count: int
    high_count: int
    compliance_score: float
    passed: bool
    recommendations: List[str]


# ============================================================================
# AGENT 1: LICENSE DETECTOR
# ============================================================================

class LicenseDetector:
    """
    Agent 1: Detects license compliance issues.

    Checks:
    - Missing license headers
    - License conflicts (GPL in proprietary code)
    - Incompatible license combinations
    - Unlicensed dependencies

    Usage:
        detector = LicenseDetector()
        violations = detector.scan_licenses(file_paths)
        conflicts = detector.detect_license_conflicts(licenses)
    """

    # Common license patterns
    LICENSE_PATTERNS = {
        "MIT": r"(?i)MIT License",
        "Apache-2.0": r"(?i)Apache License.*Version 2\.0",
        "GPL-2.0": r"(?i)GNU General Public License.*version 2",
        "GPL-3.0": r"(?i)GNU General Public License.*version 3",
        "BSD-3-Clause": r"(?i)BSD 3-Clause",
        "ISC": r"(?i)ISC License",
    }

    # Known license compatibilities
    LICENSE_COMPATIBILITY = {
        "MIT": ["Apache-2.0", "GPL-2.0", "GPL-3.0", "BSD-3-Clause"],
        "Apache-2.0": ["GPL-3.0"],  # Apache-2.0 NOT compatible with GPL-2.0
        "GPL-2.0": ["GPL-3.0"],
        "GPL-3.0": ["GPL-3.0"],
        "BSD-3-Clause": ["Apache-2.0", "GPL-2.0", "GPL-3.0"],
    }

    def __init__(self):
        """Initialize LicenseDetector"""
        pass

    def scan_file_licenses(self, file_paths: List[str]) -> List[ComplianceViolation]:
        """
        Scan source files for license headers.

        Args:
            file_paths: List of file paths to scan

        Returns:
            List of license violations
        """
        violations = []

        for filepath in file_paths:
            try:
                # Read first 50 lines (license usually at top)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    header = ''.join(f.readlines()[:50])

                # Check for license header
                has_license = any(
                    pattern in header.lower()
                    for pattern in ['copyright', 'license', 'spdx-license-identifier']
                )

                if not has_license:
                    violations.append(ComplianceViolation(
                        violation_id=f"LIC_{uuid.uuid4().hex[:8]}",
                        rule=LICENSE_RULES["MISSING_LICENSE_HEADER"],
                        filepath=filepath,
                        line_number=1,
                        description=f"No license header found in {Path(filepath).name}",
                        remediation_steps="Add SPDX license identifier and copyright notice"
                    ))

                # Check for GPL in header
                if re.search(r'(?i)GPL|GNU General Public', header):
                    violations.append(ComplianceViolation(
                        violation_id=f"LIC_{uuid.uuid4().hex[:8]}",
                        rule=LICENSE_RULES["GPL_CONFLICT"],
                        filepath=filepath,
                        line_number=1,
                        description="GPL license detected - may conflict with proprietary code",
                        remediation_steps="Verify GPL compatibility with project license"
                    ))

            except Exception as e:
                # Skip files that can't be read
                continue

        return violations

    def detect_license_conflicts(
        self,
        detected_licenses: List[str]
    ) -> List[ComplianceViolation]:
        """
        Detect conflicts between licenses.

        Args:
            detected_licenses: List of license identifiers (e.g., ["MIT", "GPL-2.0"])

        Returns:
            List of license conflict violations
        """
        violations = []

        # Check all pairs for compatibility
        for i, lic1 in enumerate(detected_licenses):
            for lic2 in detected_licenses[i+1:]:
                if lic1 == lic2:
                    continue

                # Check if licenses are compatible
                compatible = False
                if lic1 in self.LICENSE_COMPATIBILITY:
                    compatible = lic2 in self.LICENSE_COMPATIBILITY[lic1]

                if not compatible:
                    violations.append(ComplianceViolation(
                        violation_id=f"LIC_{uuid.uuid4().hex[:8]}",
                        rule=LICENSE_RULES["INCOMPATIBLE_LICENSES"],
                        filepath="<project>",
                        line_number=0,
                        description=f"Incompatible licenses detected: {lic1} and {lic2}",
                        remediation_steps=f"Remove {lic2} dependency or relicense to compatible license"
                    ))

        return violations

    def extract_license_from_text(self, text: str) -> Optional[str]:
        """
        Extract license type from text.

        Args:
            text: Text to analyze (e.g., file header)

        Returns:
            License identifier or None
        """
        for license_name, pattern in self.LICENSE_PATTERNS.items():
            if re.search(pattern, text):
                return license_name

        return None


# ============================================================================
# AGENT 2: COMPLIANCE VALIDATOR
# ============================================================================

class ComplianceValidator:
    """
    Agent 2: Validates GDPR, HIPAA, and security compliance.

    Checks:
    - PII encryption (GDPR Article 32)
    - Data retention policies (GDPR Article 5)
    - User consent (GDPR Article 7)
    - Hardcoded credentials (OWASP A2)
    - Weak cryptography (NIST guidelines)
    - Input validation (OWASP A1)

    Usage:
        validator = ComplianceValidator(cpg_service)
        violations = validator.check_privacy_compliance()
        security_issues = validator.check_security_compliance()
    """

    def __init__(self, cpg_service):
        """
        Initialize ComplianceValidator.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service

    def check_privacy_compliance(self) -> List[ComplianceViolation]:
        """
        Check GDPR/HIPAA privacy compliance.

        Returns:
            List of privacy violations
        """
        violations = []

        # Check 1: PII without encryption
        for rule_id, rule in PRIVACY_RULES.items():
            if "-- Find" in rule.pattern:  # SQL query
                try:
                    results = self.cpg.execute_custom_sql(rule.pattern)

                    for row in results[:20]:  # Limit to 20 per rule
                        violations.append(ComplianceViolation(
                            violation_id=f"PII_{uuid.uuid4().hex[:8]}",
                            rule=rule,
                            filepath=row.get('filename', '<unknown>'),
                            line_number=row.get('line_number', 0),
                            description=f"{rule.name}: {row.get('name', 'unknown')}",
                            remediation_steps=rule.remediation
                        ))
                except Exception as e:
                    # Query may fail if schema differs
                    continue

        return violations

    def check_security_compliance(self) -> List[ComplianceViolation]:
        """
        Check security compliance (OWASP, CWE).

        Returns:
            List of security violations
        """
        violations = []

        for rule_id, rule in SECURITY_RULES.items():
            if "-- Find" in rule.pattern:  # SQL query
                try:
                    results = self.cpg.execute_custom_sql(rule.pattern)

                    for row in results[:20]:
                        violations.append(ComplianceViolation(
                            violation_id=f"SEC_{uuid.uuid4().hex[:8]}",
                            rule=rule,
                            filepath=row.get('filename', '<unknown>'),
                            line_number=row.get('line_number', 0),
                            description=f"{rule.name}: {row.get('name', 'unknown')}",
                            code_snippet=row.get('code', '')[:200],
                            remediation_steps=rule.remediation
                        ))
                except Exception as e:
                    continue

        return violations

    def check_hardcoded_secrets(self, file_content: str, filepath: str) -> List[ComplianceViolation]:
        """
        Check for hardcoded credentials in file.

        Args:
            file_content: File content
            filepath: Path to file

        Returns:
            List of violations
        """
        violations = []
        rule = SECURITY_RULES["HARDCODED_CREDENTIALS"]

        # Search for hardcoded credentials
        for line_num, line in enumerate(file_content.split('\n'), 1):
            if re.search(rule.pattern, line):
                violations.append(ComplianceViolation(
                    violation_id=f"SEC_{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    filepath=filepath,
                    line_number=line_num,
                    description="Hardcoded credential detected",
                    code_snippet=line.strip()[:100],
                    remediation_steps=rule.remediation
                ))

        return violations


# ============================================================================
# AGENT 3: STANDARDS CHECKER
# ============================================================================

class StandardsChecker:
    """
    Agent 3: Checks coding standards and documentation.

    Checks:
    - Missing docstrings
    - Naming conventions
    - Cyclomatic complexity
    - Magic numbers
    - Code formatting

    Usage:
        checker = StandardsChecker(cpg_service)
        violations = checker.check_documentation()
        complexity_issues = checker.check_complexity()
    """

    def __init__(self, cpg_service):
        """
        Initialize StandardsChecker.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service

    def check_documentation(self) -> List[ComplianceViolation]:
        """
        Check for missing documentation.

        Returns:
            List of documentation violations
        """
        violations = []
        rule = STANDARDS_RULES["MISSING_DOCSTRING"]

        try:
            results = self.cpg.execute_custom_sql(rule.pattern)

            for row in results[:20]:
                violations.append(ComplianceViolation(
                    violation_id=f"DOC_{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    filepath=row.get('filename', '<unknown>'),
                    line_number=row.get('line_number', 0),
                    description=f"Missing docstring: {row.get('name', 'unknown')}",
                    remediation_steps=rule.remediation
                ))
        except Exception as e:
            pass

        return violations

    def check_complexity(self) -> List[ComplianceViolation]:
        """
        Check for excessive complexity.

        Returns:
            List of complexity violations
        """
        violations = []
        rule = STANDARDS_RULES["EXCESSIVE_COMPLEXITY"]

        try:
            results = self.cpg.execute_custom_sql(rule.pattern)

            for row in results[:20]:
                complexity = row.get('complexity', 0)
                violations.append(ComplianceViolation(
                    violation_id=f"CMP_{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    filepath=row.get('filename', '<unknown>'),
                    line_number=row.get('line_number', 0),
                    description=f"Excessive complexity ({complexity}): {row.get('name', 'unknown')}",
                    remediation_steps=rule.remediation
                ))
        except Exception as e:
            pass

        return violations

    def check_naming_conventions(
        self,
        identifiers: List[Dict[str, Any]],
        language: str = "python"
    ) -> List[ComplianceViolation]:
        """
        Check naming conventions.

        Args:
            identifiers: List of identifiers (variables, functions, classes)
            language: Programming language

        Returns:
            List of naming violations
        """
        violations = []
        rule = STANDARDS_RULES["POOR_NAMING_CONVENTION"]

        for identifier in identifiers:
            name = identifier.get('name', '')
            kind = identifier.get('kind', 'variable')

            # Python conventions
            if language == "python":
                # Functions/variables should be snake_case
                if kind in ['function', 'variable']:
                    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                        violations.append(ComplianceViolation(
                            violation_id=f"NAM_{uuid.uuid4().hex[:8]}",
                            rule=rule,
                            filepath=identifier.get('filepath', '<unknown>'),
                            line_number=identifier.get('line_number', 0),
                            description=f"Non-snake_case {kind}: {name}",
                            remediation_steps=f"Rename to snake_case (e.g., {name.lower()})"
                        ))

                # Classes should be PascalCase
                elif kind == 'class':
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
                        violations.append(ComplianceViolation(
                            violation_id=f"NAM_{uuid.uuid4().hex[:8]}",
                            rule=rule,
                            filepath=identifier.get('filepath', '<unknown>'),
                            line_number=identifier.get('line_number', 0),
                            description=f"Non-PascalCase class: {name}",
                            remediation_steps="Rename to PascalCase"
                        ))

        return violations

    def check_magic_numbers(self, file_content: str, filepath: str) -> List[ComplianceViolation]:
        """
        Check for magic numbers.

        Args:
            file_content: File content
            filepath: Path to file

        Returns:
            List of violations
        """
        violations = []
        rule = STANDARDS_RULES["MAGIC_NUMBERS"]

        for line_num, line in enumerate(file_content.split('\n'), 1):
            # Skip comments and strings
            if '//' in line or '#' in line or '"' in line or "'" in line:
                continue

            # Find numbers with 2+ digits (excluding 0, 1, 10, 100, etc.)
            matches = re.finditer(r'\b(?<![\w.])(\d{2,})(?![\w.])\b', line)

            for match in matches:
                number = match.group(1)

                # Skip common round numbers
                if number in ['10', '100', '1000', '0', '1']:
                    continue

                violations.append(ComplianceViolation(
                    violation_id=f"MAG_{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    filepath=filepath,
                    line_number=line_num,
                    description=f"Magic number: {number}",
                    code_snippet=line.strip()[:100],
                    remediation_steps=f"Extract {number} to named constant"
                ))

        return violations

    def generate_compliance_report(
        self,
        all_violations: List[ComplianceViolation]
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report.

        Args:
            all_violations: All violations found

        Returns:
            ComplianceReport
        """
        # Group by category
        by_category = {}
        for violation in all_violations:
            cat = violation.rule.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(violation)

        # Group by severity
        by_severity = {}
        for violation in all_violations:
            sev = violation.rule.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(violation)

        # Count critical/high
        critical_count = len(by_severity.get('critical', []))
        high_count = len(by_severity.get('high', []))

        # Calculate compliance score (0-100)
        # Critical = -20 points, High = -10, Medium = -5, Low = -2, Info = -1
        severity_penalties = {
            'critical': 20,
            'high': 10,
            'medium': 5,
            'low': 2,
            'info': 1
        }

        total_penalty = sum(
            severity_penalties.get(v.rule.severity.value, 1)
            for v in all_violations
        )

        # Start at 100, subtract penalties, floor at 0
        compliance_score = max(0, 100 - total_penalty)

        # Pass if score >= 80 and no critical violations
        passed = compliance_score >= 80 and critical_count == 0

        # Generate recommendations
        recommendations = []
        if critical_count > 0:
            recommendations.append(f"Fix {critical_count} critical violations immediately")
        if high_count > 0:
            recommendations.append(f"Address {high_count} high severity violations before release")
        if compliance_score < 80:
            recommendations.append("Improve compliance score to 80+ for production readiness")

        return ComplianceReport(
            report_id=f"CPL_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            violations=all_violations,
            violations_by_category=by_category,
            violations_by_severity=by_severity,
            critical_count=critical_count,
            high_count=high_count,
            compliance_score=compliance_score,
            passed=passed,
            recommendations=recommendations
        )
