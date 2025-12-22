"""Architecture Reporter Agent.

Agent 3: Generates architecture violation reports.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import (
    ViolationFinding,
    DependencyAnalysis,
    RemediationAction,
    ArchitectureReport,
)
from ..architecture_patterns import get_pattern


class ArchitectureReporter:
    """
    Agent 3: Generates architecture violation reports.

    Generates:
    - Structured violation reports
    - Remediation recommendations
    - Priority-based action items
    - Executive summaries

    Usage:
        reporter = ArchitectureReporter()
        report = reporter.generate_report(findings, dependency_analysis, layer_metrics)
        actions = reporter.create_remediation_plan(findings)
    """

    def __init__(self):
        """Initialize ArchitectureReporter."""
        pass

    def generate_report(
        self,
        findings: List[ViolationFinding],
        dependency_analysis: Optional[DependencyAnalysis] = None,
        layer_metrics: Optional[Dict[str, Any]] = None
    ) -> ArchitectureReport:
        """
        Generate comprehensive architecture violation report.

        Args:
            findings: List of violation findings
            dependency_analysis: Dependency metrics (optional)
            layer_metrics: Layer-specific metrics (optional)

        Returns:
            ArchitectureReport with complete analysis
        """
        by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        by_category = {'dependency': 0, 'layering': 0, 'coupling': 0, 'cohesion': 0}

        for finding in findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        remediation_actions = self.create_remediation_plan(findings)
        summary = self._generate_summary(findings, by_severity, by_category, dependency_analysis)
        recommendations = self._generate_recommendations(findings, dependency_analysis)
        action_items = self._generate_action_items(remediation_actions[:5])

        return ArchitectureReport(
            report_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            total_violations=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            findings=findings,
            dependency_analysis=dependency_analysis,
            layer_metrics=layer_metrics,
            remediation_actions=remediation_actions,
            summary=summary,
            recommendations=recommendations,
            action_items=action_items
        )

    def create_remediation_plan(self, findings: List[ViolationFinding]) -> List[RemediationAction]:
        """
        Create prioritized remediation plan from findings.

        Args:
            findings: List of violation findings

        Returns:
            List of RemediationAction objects, sorted by priority
        """
        actions = []

        for finding in findings:
            priority = self._calculate_priority(finding)
            effort = self._estimate_effort(finding)
            risk = self._assess_risk(finding)
            action_desc = self._create_action_description(finding)

            modules_affected = [finding.module_a]
            if finding.module_b:
                modules_affected.append(finding.module_b)

            action = RemediationAction(
                action_id=f"ACTION_{finding.finding_id}",
                finding_id=finding.finding_id,
                priority=priority,
                violation_type=finding.pattern_name,
                action_description=action_desc,
                estimated_effort=effort,
                risk_level=risk,
                modules_affected=modules_affected
            )

            actions.append(action)

        actions.sort(key=lambda a: a.priority, reverse=True)

        return actions

    def _calculate_priority(self, finding: ViolationFinding) -> int:
        """Calculate remediation priority (1-10, 10 = highest)."""
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2
        }
        base_priority = severity_scores.get(finding.severity, 5)

        if finding.category in ['dependency', 'layering']:
            base_priority = min(base_priority + 2, 10)

        if finding.pattern_id == "CIRCULAR_DEPS":
            base_priority = min(base_priority + 1, 10)

        return base_priority

    def _estimate_effort(self, finding: ViolationFinding) -> str:
        """Estimate effort to fix violation."""
        if finding.pattern_id == "CIRCULAR_DEPS":
            return "high"
        elif finding.pattern_id == "LAYER_VIOLATION":
            return "high"
        elif finding.pattern_id == "GOD_MODULE":
            return "high"
        elif finding.pattern_id == "UNSTABLE_DEPS":
            return "medium"
        elif finding.pattern_id == "FEATURE_ENVY":
            return "low"
        elif finding.pattern_id == "INAPPROPRIATE_INTIMACY":
            return "medium"
        else:
            return "medium"

    def _assess_risk(self, finding: ViolationFinding) -> str:
        """Assess risk of fixing violation."""
        if finding.severity == 'critical':
            return "high"
        elif finding.pattern_id in ["CIRCULAR_DEPS", "LAYER_VIOLATION"]:
            return "high"
        elif finding.pattern_id == "GOD_MODULE":
            fan_in = finding.metadata.get('incoming_dependencies', 0)
            if fan_in > 30:
                return "high"
            elif fan_in > 15:
                return "medium"
            else:
                return "low"
        else:
            return "medium"

    def _create_action_description(self, finding: ViolationFinding) -> str:
        """Create actionable description for fixing violation."""
        if finding.pattern_id == "CIRCULAR_DEPS":
            return (
                f"Break circular dependency between {finding.module_a} and {finding.module_b} "
                f"by extracting common code to a shared module or using dependency injection"
            )
        elif finding.pattern_id == "LAYER_VIOLATION":
            return (
                f"Fix layering violation: refactor {finding.module_a} to not call {finding.module_b}, "
                f"use events/callbacks for upward communication"
            )
        elif finding.pattern_id == "GOD_MODULE":
            return (
                f"Split {finding.module_a} into smaller, focused modules "
                f"applying Single Responsibility Principle"
            )
        elif finding.pattern_id == "UNSTABLE_DEPS":
            return (
                f"Invert dependency: {finding.module_a} should define interface, "
                f"{finding.module_b} should implement it"
            )
        elif finding.pattern_id == "FEATURE_ENVY":
            return (
                f"Move envious method from {finding.module_a} to {finding.module_b} "
                f"where the data lives"
            )
        elif finding.pattern_id == "INAPPROPRIATE_INTIMACY":
            return (
                f"Reduce coupling between {finding.module_a} and {finding.module_b} "
                f"by extracting common behavior or using interfaces"
            )
        else:
            return f"Fix {finding.pattern_name} in {finding.module_a}"

    def _generate_summary(
        self,
        findings: List[ViolationFinding],
        by_severity: Dict[str, int],
        by_category: Dict[str, int],
        dependency_analysis: Optional[DependencyAnalysis]
    ) -> str:
        """Generate executive summary."""
        total = len(findings)
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)

        main_category = max(by_category.items(), key=lambda x: x[1])[0] if by_category else 'unknown'

        summary_parts = [
            f"Found {total} architecture violations across the codebase."
        ]

        if critical > 0:
            summary_parts.append(f"{critical} CRITICAL violations require immediate attention.")

        if high > 0:
            summary_parts.append(f"{high} HIGH severity violations need remediation.")

        summary_parts.append(
            f"Primary architectural concern: {main_category} issues "
            f"({by_category.get(main_category, 0)} violations)."
        )

        if dependency_analysis:
            if dependency_analysis.circular_dependency_count > 0:
                summary_parts.append(
                    f"Detected {dependency_analysis.circular_dependency_count} circular dependency chains."
                )
            if dependency_analysis.god_module_count > 0:
                summary_parts.append(
                    f"Identified {dependency_analysis.god_module_count} god modules with excessive coupling."
                )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        findings: List[ViolationFinding],
        dependency_analysis: Optional[DependencyAnalysis]
    ) -> List[str]:
        """Generate top recommendations."""
        recommendations = []

        violation_counts = {}
        for finding in findings:
            violation_counts[finding.pattern_id] = violation_counts.get(finding.pattern_id, 0) + 1

        sorted_violations = sorted(violation_counts.items(), key=lambda x: -x[1])

        for pattern_id, count in sorted_violations[:3]:
            pattern = get_pattern(pattern_id)
            if pattern:
                rec = (
                    f"Address {count} instances of {pattern.name}: "
                    f"{pattern.remediation.split(chr(10))[0].strip()}"
                )
                recommendations.append(rec)

        if dependency_analysis:
            if dependency_analysis.circular_dependency_count > 0:
                recommendations.append(
                    "High priority: Break circular dependencies to enable modular testing and reduce coupling"
                )
            if dependency_analysis.god_module_count > 3:
                recommendations.append(
                    "Refactor god modules by applying Single Responsibility Principle"
                )

        return recommendations[:5]

    def _generate_action_items(self, top_actions: List[RemediationAction]) -> List[str]:
        """Generate actionable items from top remediation actions."""
        action_items = []

        for action in top_actions:
            item = (
                f"[Priority {action.priority}] {action.action_description} "
                f"(effort: {action.estimated_effort}, risk: {action.risk_level})"
            )
            action_items.append(item)

        return action_items
