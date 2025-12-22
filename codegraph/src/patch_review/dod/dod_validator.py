"""
DoD Validator - Validates Definition of Done against review findings

Validates each DoD item based on:
- Review findings (security, performance, etc.)
- Test results
- Code quality metrics
- Documentation presence
"""

import logging
from typing import Dict, List, Optional, Any

from ..models import (
    DefinitionOfDone,
    DoDItem,
    DoDCriterionType,
    DoDValidationResult,
    ReviewVerdict,
    Finding,
    Severity,
    FindingCategory,
)

logger = logging.getLogger(__name__)


class DoDValidator:
    """
    Validates Definition of Done against code review results.

    Maps review findings to DoD items and determines satisfaction status.
    """

    # Severity thresholds for blocking DoD items
    BLOCKING_SEVERITIES = {Severity.CRITICAL, Severity.HIGH}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DoD validator.

        Args:
            config: Configuration dictionary with:
                - strict_mode: Fail on any finding (default: False)
                - blocking_severities: Severities that block items
        """
        self.config = config or {}
        self.strict_mode = self.config.get('strict_mode', False)
        self.blocking_severities = set(
            self.config.get('blocking_severities', ['critical', 'high'])
        )

    def validate(
        self,
        dod: DefinitionOfDone,
        verdict: ReviewVerdict,
    ) -> DoDValidationResult:
        """
        Validate DoD against review verdict.

        Args:
            dod: Definition of Done to validate
            verdict: Review verdict with findings

        Returns:
            DoDValidationResult with validated items
        """
        validated_items = []
        blocking_failures = []

        for item in dod.items:
            validated_item = self._validate_item(item, verdict)
            validated_items.append(validated_item)

            if validated_item.is_satisfied is False:
                # Check if this failure is blocking
                if self._is_blocking_failure(validated_item, verdict):
                    blocking_failures.append(validated_item)

        # Update DoD with validated items
        validated_dod = DefinitionOfDone(
            items=validated_items,
            source=dod.source,
            format=dod.format,
            confirmed=dod.confirmed,
            generated_from=dod.generated_from,
            raw_text=dod.raw_text,
        )

        # Calculate metrics
        total = len(validated_items)
        satisfied = sum(1 for i in validated_items if i.is_satisfied is True)
        failed = sum(1 for i in validated_items if i.is_satisfied is False)
        pending = sum(1 for i in validated_items if i.is_satisfied is None)

        compliance_score = (satisfied / total * 100) if total > 0 else 100.0

        return DoDValidationResult(
            dod=validated_dod,
            total_items=total,
            satisfied_count=satisfied,
            failed_count=failed,
            pending_count=pending,
            compliance_score=compliance_score,
            blocking_failures=blocking_failures,
        )

    def _validate_item(
        self,
        item: DoDItem,
        verdict: ReviewVerdict,
    ) -> DoDItem:
        """
        Validate a single DoD item.

        Args:
            item: DoD item to validate
            verdict: Review verdict with findings

        Returns:
            DoDItem with updated satisfaction status
        """
        # Get relevant findings for this item type
        relevant_findings = self._get_relevant_findings(item, verdict)

        # Determine satisfaction based on criterion type
        is_satisfied, evidence, finding_ids = self._evaluate_criterion(
            item=item,
            findings=relevant_findings,
            verdict=verdict,
        )

        return DoDItem(
            description=item.description,
            criterion_type=item.criterion_type,
            is_satisfied=is_satisfied,
            evidence=evidence,
            finding_ids=finding_ids,
        )

    def _get_relevant_findings(
        self,
        item: DoDItem,
        verdict: ReviewVerdict,
    ) -> List[Finding]:
        """
        Get findings relevant to a DoD item.

        Args:
            item: DoD item
            verdict: Review verdict

        Returns:
            List of relevant findings
        """
        # Map criterion types to finding categories
        category_mapping = {
            DoDCriterionType.SECURITY: FindingCategory.SECURITY,
            DoDCriterionType.PERFORMANCE: FindingCategory.PERFORMANCE,
            DoDCriterionType.CODE_QUALITY: FindingCategory.ARCHITECTURE,
        }

        category = category_mapping.get(item.criterion_type)
        if category:
            return [f for f in verdict.all_findings if f.category == category]

        # For FUNCTIONAL and others, check all findings
        return verdict.all_findings

    def _evaluate_criterion(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate if a criterion is satisfied.

        Args:
            item: DoD item
            findings: Relevant findings
            verdict: Full verdict

        Returns:
            Tuple of (is_satisfied, evidence, finding_ids)
        """
        finding_ids = []

        if item.criterion_type == DoDCriterionType.SECURITY:
            return self._evaluate_security(item, findings, verdict)

        elif item.criterion_type == DoDCriterionType.TEST:
            return self._evaluate_test(item, findings, verdict)

        elif item.criterion_type == DoDCriterionType.PERFORMANCE:
            return self._evaluate_performance(item, findings, verdict)

        elif item.criterion_type == DoDCriterionType.DOCUMENTATION:
            return self._evaluate_documentation(item, findings, verdict)

        elif item.criterion_type == DoDCriterionType.CODE_QUALITY:
            return self._evaluate_code_quality(item, findings, verdict)

        else:  # FUNCTIONAL
            return self._evaluate_functional(item, findings, verdict)

    def _evaluate_security(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate security criterion.

        Security is satisfied if no critical/high security findings.
        """
        blocking_findings = [
            f for f in findings
            if f.category == FindingCategory.SECURITY
            and f.severity in self.BLOCKING_SEVERITIES
        ]

        if blocking_findings:
            finding_ids = [f.id for f in blocking_findings]
            titles = [f.title for f in blocking_findings[:3]]
            evidence = f"Security issues found: {', '.join(titles)}"
            return False, evidence, finding_ids

        # Check security score
        if verdict.security.score >= 80:
            return True, f"Security score: {verdict.security.score:.1f}/100", []
        elif verdict.security.score >= 60:
            return None, f"Security score borderline: {verdict.security.score:.1f}/100", []
        else:
            return False, f"Low security score: {verdict.security.score:.1f}/100", []

    def _evaluate_test(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate test criterion.

        Test is satisfied if:
        - No test-related error findings
        - Test suggestions are minimal
        """
        # Check for test-related findings
        test_findings = [
            f for f in findings
            if 'test' in f.description.lower() or 'test' in f.title.lower()
        ]

        if test_findings:
            blocking = [f for f in test_findings if f.severity in self.BLOCKING_SEVERITIES]
            if blocking:
                return False, "Test issues found", [f.id for f in blocking]

        # Check error verdict test suggestions
        if verdict.error.test_suggestions:
            if len(verdict.error.test_suggestions) > 3:
                return None, f"{len(verdict.error.test_suggestions)} test suggestions", []

        # Assume satisfied if no negative signals
        return True, "No test issues detected", []

    def _evaluate_performance(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate performance criterion.

        Performance is satisfied if:
        - No critical/high performance findings
        - Performance score is acceptable
        """
        blocking_findings = [
            f for f in findings
            if f.category == FindingCategory.PERFORMANCE
            and f.severity in self.BLOCKING_SEVERITIES
        ]

        if blocking_findings:
            return False, "Performance issues found", [f.id for f in blocking_findings]

        # Check performance score
        if verdict.performance.score >= 70:
            return True, f"Performance score: {verdict.performance.score:.1f}/100", []
        elif verdict.performance.score >= 50:
            return None, f"Performance needs review: {verdict.performance.score:.1f}/100", []
        else:
            return False, f"Poor performance score: {verdict.performance.score:.1f}/100", []

    def _evaluate_documentation(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate documentation criterion.

        Documentation satisfaction is harder to validate automatically.
        Returns None (pending) for manual review unless clear issues.
        """
        # Check for documentation-related findings
        doc_findings = [
            f for f in findings
            if 'doc' in f.description.lower() or 'comment' in f.description.lower()
        ]

        if doc_findings and any(f.severity == Severity.HIGH for f in doc_findings):
            return False, "Documentation issues found", [f.id for f in doc_findings]

        # Can't fully validate automatically
        return None, "Requires manual documentation review", []

    def _evaluate_code_quality(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate code quality criterion.

        Code quality is satisfied if architecture score is good.
        """
        # Check architecture score as proxy for code quality
        if verdict.architecture.score >= 70:
            return True, f"Architecture score: {verdict.architecture.score:.1f}/100", []
        elif verdict.architecture.score >= 50:
            return None, f"Code quality needs review: {verdict.architecture.score:.1f}/100", []
        else:
            arch_findings = [
                f for f in findings
                if f.category == FindingCategory.ARCHITECTURE
            ]
            return False, f"Code quality issues", [f.id for f in arch_findings[:3]]

    def _evaluate_functional(
        self,
        item: DoDItem,
        findings: List[Finding],
        verdict: ReviewVerdict,
    ) -> tuple[Optional[bool], Optional[str], List[str]]:
        """
        Evaluate functional criterion.

        Functional requirements can't be fully validated by static analysis.
        Returns None for manual review unless clear errors found.
        """
        # Check for critical errors that indicate functional issues
        critical_errors = [
            f for f in verdict.error.findings
            if f.severity == Severity.CRITICAL
        ]

        if critical_errors:
            return False, "Critical errors found that may affect functionality", [f.id for f in critical_errors]

        # Check overall score
        if verdict.overall_score >= 60:
            return None, "No blocking issues, manual verification recommended", []
        else:
            return None, f"Low overall score ({verdict.overall_score:.1f}), review needed", []

    def _is_blocking_failure(
        self,
        item: DoDItem,
        verdict: ReviewVerdict,
    ) -> bool:
        """
        Determine if a failed item should block the review.

        Args:
            item: Failed DoD item
            verdict: Review verdict

        Returns:
            True if failure should block
        """
        # Security failures always block
        if item.criterion_type == DoDCriterionType.SECURITY:
            return True

        # Test failures block in strict mode
        if item.criterion_type == DoDCriterionType.TEST and self.strict_mode:
            return True

        # Check if related findings are blocking severity
        for finding_id in item.finding_ids:
            for finding in verdict.all_findings:
                if finding.id == finding_id and finding.severity in self.BLOCKING_SEVERITIES:
                    return True

        return False

    def format_validation_report(
        self,
        result: DoDValidationResult,
    ) -> str:
        """
        Format validation result as markdown report.

        Args:
            result: Validation result

        Returns:
            Markdown formatted report
        """
        lines = [
            "## Definition of Done Validation",
            "",
            f"**Compliance Score:** {result.compliance_score:.1f}%",
            f"**Status:** {'Compliant' if result.is_compliant else 'Non-compliant'}",
            "",
            "### Checklist",
            "",
        ]

        for item in result.dod.items:
            icon = item.status_icon
            lines.append(f"- {icon} **{item.criterion_type.value.title()}**: {item.description}")
            if item.evidence:
                lines.append(f"  - _{item.evidence}_")

        if result.blocking_failures:
            lines.extend([
                "",
                "### Blocking Issues",
                "",
            ])
            for item in result.blocking_failures:
                lines.append(f"- {item.description}")

        lines.extend([
            "",
            "### Summary",
            "",
            f"- Satisfied: {result.satisfied_count}/{result.total_items}",
            f"- Failed: {result.failed_count}/{result.total_items}",
            f"- Pending: {result.pending_count}/{result.total_items}",
        ])

        return "\n".join(lines)
