"""
Hardening Scanner - Orchestrates D3FEND compliance checks

Scans CPG database for D3FEND Source Code Hardening compliance,
combining generic checks with domain-specific patterns from plugins.
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .base import (
    HardeningCheck,
    HardeningCategory,
    HardeningSeverity,
    HardeningFinding,
    D3FEND_TECHNIQUES,
)
from .d3fend_checks import (
    HARDENING_CHECKS,
    D3FEND_TECHNIQUE_IDS,
    get_all_checks,
    get_checks_for_language,
    get_checks_by_category,
    get_checks_by_d3fend_id,
)

logger = logging.getLogger(__name__)


class HardeningScanner:
    """
    Scans CPG for D3FEND Source Code Hardening compliance.

    Responsibilities:
    - Load hardening checks from registry + domain plugin
    - Execute CPGQL queries for each check
    - Filter by language scope
    - Generate HardeningFinding results
    - Compute compliance scores

    Usage:
        with CPGQueryService() as cpg:
            scanner = HardeningScanner(cpg, language="c")

            # Run all checks
            findings = scanner.scan_all(limit_per_check=50)

            # Run specific D3FEND techniques
            findings = scanner.scan_by_d3fend_id(["D3-VI", "D3-NPC"])

            # Get compliance score
            scores = scanner.get_compliance_score(findings)
    """

    def __init__(self, cpg_service: Any, language: str = "c"):
        """
        Initialize the hardening scanner.

        Args:
            cpg_service: CPG query service with execute_query method
            language: Target language for filtering checks ("c", "cpp", etc.)
        """
        self.cpg = cpg_service
        self.language = language.lower()
        self._checks: Dict[str, HardeningCheck] = {}
        self._domain_checks: Dict[str, HardeningCheck] = {}
        self._load_checks()

    def _load_checks(self) -> None:
        """Load hardening checks from generic registry and domain plugin."""
        # 1. Start with generic checks filtered by language
        for check in get_checks_for_language(self.language):
            self._checks[check.id] = check

        logger.debug(f"Loaded {len(self._checks)} generic checks for language '{self.language}'")

        # 2. Load domain-specific checks via plugin
        try:
            from src.domains import DomainRegistry
            domain = DomainRegistry.get_active_or_none()
            if domain and hasattr(domain, 'get_hardening_patterns'):
                domain_patterns = domain.get_hardening_patterns()
                for pattern in domain_patterns:
                    check = self._pattern_to_check(pattern)
                    if check and check.applies_to_language(self.language):
                        self._domain_checks[check.id] = check
                        # Domain checks override generic with same D3FEND ID prefix
                        self._checks[check.id] = check

                logger.debug(f"Loaded {len(self._domain_checks)} domain-specific hardening patterns")
        except ImportError:
            logger.debug("Domain registry not available, using generic checks only")
        except Exception as e:
            logger.warning(f"Failed to load domain hardening patterns: {e}")

    def _pattern_to_check(self, pattern: Dict[str, Any]) -> Optional[HardeningCheck]:
        """Convert a domain plugin pattern dict to HardeningCheck."""
        try:
            # Map category string to enum
            category_str = pattern.get("category", "").lower()
            category_map = {
                "initialization": HardeningCategory.INITIALIZATION,
                "credential_mgmt": HardeningCategory.CREDENTIAL_MANAGEMENT,
                "credential_management": HardeningCategory.CREDENTIAL_MANAGEMENT,
                "integer_safety": HardeningCategory.INTEGER_SAFETY,
                "pointer_safety": HardeningCategory.POINTER_SAFETY,
                "memory_safety": HardeningCategory.MEMORY_SAFETY,
                "library_safety": HardeningCategory.LIBRARY_SAFETY,
                "type_safety": HardeningCategory.TYPE_SAFETY,
                "domain_validation": HardeningCategory.DOMAIN_VALIDATION,
                "operational": HardeningCategory.OPERATIONAL_VALIDATION,
                "operational_validation": HardeningCategory.OPERATIONAL_VALIDATION,
            }
            category = category_map.get(category_str, HardeningCategory.DOMAIN_VALIDATION)

            # Map severity string to enum
            severity_str = pattern.get("severity", "medium").lower()
            severity_map = {
                "critical": HardeningSeverity.CRITICAL,
                "high": HardeningSeverity.HIGH,
                "medium": HardeningSeverity.MEDIUM,
                "low": HardeningSeverity.LOW,
                "info": HardeningSeverity.INFO,
            }
            severity = severity_map.get(severity_str, HardeningSeverity.MEDIUM)

            return HardeningCheck(
                id=pattern.get("id", ""),
                d3fend_id=pattern.get("d3fend_id", ""),
                d3fend_name=pattern.get("d3fend_name", ""),
                category=category,
                severity=severity,
                description=pattern.get("description", ""),
                cpgql_query=pattern.get("cpgql_query", ""),
                cwe_ids=pattern.get("cwe_ids", []),
                language_scope=pattern.get("language_scope", ["*"]),
                indicators=pattern.get("indicators", []),
                good_patterns=pattern.get("good_patterns", []),
                remediation=pattern.get("remediation", ""),
                example_code=pattern.get("example_code", ""),
                confidence_weight=pattern.get("confidence_weight", 1.0),
            )
        except Exception as e:
            logger.warning(f"Failed to convert pattern to check: {e}")
            return None

    def _execute_check(
        self,
        check: HardeningCheck,
        limit: int = 50
    ) -> List[HardeningFinding]:
        """
        Execute a single hardening check against the CPG.

        Args:
            check: The hardening check to execute
            limit: Maximum number of findings to return

        Returns:
            List of HardeningFinding objects
        """
        findings = []

        try:
            # Append LIMIT if not present
            query = check.cpgql_query.strip()
            if not query.upper().endswith(f"LIMIT {limit}"):
                if "LIMIT" in query.upper():
                    # Replace existing limit
                    import re
                    query = re.sub(r'LIMIT\s+\d+', f'LIMIT {limit}', query, flags=re.IGNORECASE)
                else:
                    query = f"{query}\nLIMIT {limit}"

            # Execute query
            rows = self.cpg.execute_query(query)

            # Convert rows to findings
            for row in rows:
                finding = HardeningFinding.from_check_and_row(
                    check=check,
                    row=row,
                    confidence=1.0
                )
                findings.append(finding)

            logger.debug(f"Check {check.id} found {len(findings)} issues")

        except Exception as e:
            logger.warning(f"Check {check.id} failed: {e}")

        return findings

    def scan_all(self, limit_per_check: int = 50) -> List[HardeningFinding]:
        """
        Run all applicable hardening checks.

        Args:
            limit_per_check: Maximum findings per check

        Returns:
            List of all findings across all checks
        """
        all_findings = []

        for check_id, check in self._checks.items():
            # Skip duplicate IDs (e.g., D3-VI and D3-VI-001 point to same check)
            if check_id != check.id:
                continue

            findings = self._execute_check(check, limit=limit_per_check)
            all_findings.extend(findings)

        logger.info(f"HardeningScanner: {len(all_findings)} total findings from {len(self._checks)} checks")
        return all_findings

    def scan_by_d3fend_id(
        self,
        d3fend_ids: List[str],
        limit: int = 50
    ) -> List[HardeningFinding]:
        """
        Run checks for specific D3FEND technique IDs.

        Args:
            d3fend_ids: List of D3FEND IDs (e.g., ["D3-VI", "D3-NPC"])
            limit: Maximum findings per check

        Returns:
            List of findings for the specified techniques
        """
        all_findings = []
        processed_ids = set()

        for d3fend_id in d3fend_ids:
            # Find all checks with this D3FEND ID
            for check_id, check in self._checks.items():
                if check.d3fend_id == d3fend_id and check.id not in processed_ids:
                    processed_ids.add(check.id)
                    findings = self._execute_check(check, limit=limit)
                    all_findings.extend(findings)

        logger.info(f"HardeningScanner: {len(all_findings)} findings for D3FEND IDs: {d3fend_ids}")
        return all_findings

    def scan_by_category(
        self,
        category: HardeningCategory,
        limit: int = 50
    ) -> List[HardeningFinding]:
        """
        Run checks for a specific category.

        Args:
            category: Hardening category to scan
            limit: Maximum findings per check

        Returns:
            List of findings for the specified category
        """
        all_findings = []
        processed_ids = set()

        for check_id, check in self._checks.items():
            if check.category == category and check.id not in processed_ids:
                processed_ids.add(check.id)
                findings = self._execute_check(check, limit=limit)
                all_findings.extend(findings)

        logger.info(f"HardeningScanner: {len(all_findings)} findings for category: {category.value}")
        return all_findings

    def scan_by_severity(
        self,
        min_severity: HardeningSeverity,
        limit: int = 50
    ) -> List[HardeningFinding]:
        """
        Run checks at or above a minimum severity level.

        Args:
            min_severity: Minimum severity to include
            limit: Maximum findings per check

        Returns:
            List of findings at or above the specified severity
        """
        severity_order = [
            HardeningSeverity.CRITICAL,
            HardeningSeverity.HIGH,
            HardeningSeverity.MEDIUM,
            HardeningSeverity.LOW,
            HardeningSeverity.INFO,
        ]
        min_index = severity_order.index(min_severity)
        included_severities = set(severity_order[:min_index + 1])

        all_findings = []
        processed_ids = set()

        for check_id, check in self._checks.items():
            if check.severity in included_severities and check.id not in processed_ids:
                processed_ids.add(check.id)
                findings = self._execute_check(check, limit=limit)
                all_findings.extend(findings)

        logger.info(f"HardeningScanner: {len(all_findings)} findings at severity >= {min_severity.value}")
        return all_findings

    def get_compliance_score(
        self,
        findings: List[HardeningFinding]
    ) -> Dict[str, Any]:
        """
        Calculate compliance scores from findings.

        Args:
            findings: List of hardening findings

        Returns:
            Dictionary with compliance metrics:
            - overall_score: 0-100 overall compliance score
            - by_category: scores per category
            - by_d3fend: scores per D3FEND technique
            - by_severity: counts per severity level
        """
        # Count findings by various dimensions
        by_category: Dict[str, int] = defaultdict(int)
        by_d3fend: Dict[str, int] = defaultdict(int)
        by_severity: Dict[str, int] = defaultdict(int)

        for finding in findings:
            by_category[finding.category] += 1
            by_d3fend[finding.d3fend_id] += 1
            by_severity[finding.severity] += 1

        # Weight findings by severity for overall score
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1,
            "info": 0.5,
        }

        total_weight = sum(
            severity_weights.get(f.severity, 1) * f.confidence
            for f in findings
        )

        # Calculate overall score (inverse - more findings = lower score)
        # Use a logarithmic scale to prevent extreme values
        import math
        if total_weight == 0:
            overall_score = 100.0
        else:
            # Score decreases as weighted findings increase
            overall_score = max(0, 100 - (20 * math.log10(1 + total_weight)))

        # Calculate category scores
        category_scores = {}
        total_checks = len([c for c in self._checks.values() if c.id == c.id])  # unique checks
        for cat in HardeningCategory:
            cat_checks = [c for c in self._checks.values() if c.category == cat and c.id == c.id]
            cat_findings = by_category.get(cat.value, 0)
            if cat_checks:
                # Higher findings = lower compliance
                category_scores[cat.value] = max(0, 100 - (cat_findings * 10))
            else:
                category_scores[cat.value] = 100.0  # No checks = fully compliant

        # Calculate D3FEND technique scores
        d3fend_scores = {}
        for technique_id in D3FEND_TECHNIQUE_IDS:
            tech_findings = by_d3fend.get(technique_id, 0)
            d3fend_scores[technique_id] = max(0, 100 - (tech_findings * 10))

        return {
            "overall_score": round(overall_score, 1),
            "total_findings": len(findings),
            "by_category": dict(by_category),
            "by_d3fend": dict(by_d3fend),
            "by_severity": dict(by_severity),
            "category_scores": category_scores,
            "d3fend_scores": d3fend_scores,
        }

    def get_checks_summary(self) -> Dict[str, Any]:
        """
        Get summary of available checks.

        Returns:
            Dictionary with check counts by category and D3FEND ID
        """
        by_category: Dict[str, int] = defaultdict(int)
        by_d3fend: Dict[str, int] = defaultdict(int)
        unique_ids = set()

        for check_id, check in self._checks.items():
            if check.id not in unique_ids:
                unique_ids.add(check.id)
                by_category[check.category.value] += 1
                by_d3fend[check.d3fend_id] += 1

        return {
            "total_checks": len(unique_ids),
            "language": self.language,
            "by_category": dict(by_category),
            "by_d3fend": dict(by_d3fend),
            "domain_checks": len(self._domain_checks),
        }

    def get_remediation_report(
        self,
        findings: List[HardeningFinding]
    ) -> str:
        """
        Generate a remediation report from findings.

        Args:
            findings: List of hardening findings

        Returns:
            Markdown-formatted remediation report
        """
        if not findings:
            return "# Hardening Compliance Report\n\nNo issues found. All D3FEND checks passed."

        # Group findings by D3FEND technique
        by_technique: Dict[str, List[HardeningFinding]] = defaultdict(list)
        for finding in findings:
            by_technique[finding.d3fend_id].append(finding)

        lines = ["# D3FEND Source Code Hardening Report\n"]

        # Summary
        scores = self.get_compliance_score(findings)
        lines.append(f"## Summary\n")
        lines.append(f"- **Overall Compliance Score**: {scores['overall_score']}%")
        lines.append(f"- **Total Findings**: {len(findings)}")
        lines.append(f"- **Critical**: {scores['by_severity'].get('critical', 0)}")
        lines.append(f"- **High**: {scores['by_severity'].get('high', 0)}")
        lines.append(f"- **Medium**: {scores['by_severity'].get('medium', 0)}")
        lines.append(f"- **Low**: {scores['by_severity'].get('low', 0)}\n")

        # Findings by technique
        lines.append("## Findings by D3FEND Technique\n")

        for technique_id in D3FEND_TECHNIQUE_IDS:
            tech_findings = by_technique.get(technique_id, [])
            if not tech_findings:
                continue

            tech_info = D3FEND_TECHNIQUES.get(technique_id, {})
            tech_name = tech_info.get("name", technique_id)

            lines.append(f"### {technique_id}: {tech_name}\n")
            lines.append(f"**Findings**: {len(tech_findings)}\n")

            # Show first few findings
            for finding in tech_findings[:5]:
                lines.append(f"- **{finding.method_name}** ({finding.filename}:{finding.line_number})")
                lines.append(f"  - Severity: {finding.severity}")
                if finding.cwe_ids:
                    lines.append(f"  - CWE: {', '.join(finding.cwe_ids)}")

            if len(tech_findings) > 5:
                lines.append(f"- ... and {len(tech_findings) - 5} more\n")

            # Remediation guidance
            if tech_findings and tech_findings[0].remediation:
                lines.append(f"\n**Remediation**:\n{tech_findings[0].remediation}\n")

        return "\n".join(lines)
