"""Refactoring Planner Agent.

Creates prioritized refactoring plans with ROI estimation.
"""
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from .models import (
    CodeSmellFinding,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
)
from ..refactoring_patterns import CodeSmellSeverity, CodeSmellCategory
from ...services.cpg_query_service import CPGQueryService
from .debt_detector import TechnicalDebtDetector
from .impact import ImpactAnalyzer

logger = logging.getLogger(__name__)


class RefactoringPlanner:
    """
    Creates prioritized refactoring plans.

    Responsibilities:
    - Prioritize code smells by value and effort
    - Consider change impact and risk
    - Generate actionable refactoring tasks
    - Estimate ROI for refactorings
    """

    def create_refactoring_plan(
        self,
        findings: List[CodeSmellFinding],
        impact_analyses: List[ImpactAnalysis]
    ) -> List[RefactoringTask]:
        """
        Create prioritized refactoring plan.

        Args:
            findings: Code smell findings
            impact_analyses: Impact analyses for findings

        Returns:
            Prioritized list of refactoring tasks
        """
        tasks = []

        # Create impact map for quick lookup
        impact_map = {ia.target_method: ia for ia in impact_analyses}

        for finding in findings:
            impact = impact_map.get(finding.method_name)

            # Calculate priority (1-10, higher = more urgent)
            priority = self._calculate_priority(finding, impact)

            # Calculate estimated value
            value = self._calculate_value(finding, impact)

            # Parse refactoring steps
            steps = self._parse_refactoring_steps(finding.refactoring_technique)

            task = RefactoringTask(
                task_id=finding.finding_id.replace('_', '_TASK_'),
                finding_id=finding.finding_id,
                pattern_name=finding.pattern_name,
                target_method=finding.method_name,
                target_file=finding.filename,
                priority=priority,
                effort_hours=finding.effort_hours,
                impact_score=impact.impact_score if impact else 0.0,
                refactoring_steps=steps,
                dependencies=[],
                estimated_value=value
            )
            tasks.append(task)

        # Sort by priority (highest first), then by ROI (value/effort)
        tasks.sort(
            key=lambda t: (t.priority, t.estimated_value / max(t.effort_hours, 0.1)),
            reverse=True
        )

        logger.info(f"Created refactoring plan with {len(tasks)} tasks")
        return tasks

    def _calculate_priority(
        self,
        finding: CodeSmellFinding,
        impact: Optional[ImpactAnalysis]
    ) -> int:
        """Calculate refactoring priority (1-10)."""
        # Base priority on severity
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2,
            'info': 1
        }

        base_priority = severity_scores.get(finding.severity, 5)

        # Adjust based on impact
        if impact:
            if impact.risk_level == 'low':
                # Low risk = easier to fix = higher priority
                base_priority = min(base_priority + 1, 10)
            elif impact.risk_level == 'high':
                # High risk = more careful = slightly lower priority
                base_priority = max(base_priority - 1, 1)

        # Boost bloaters (they affect many other smells)
        if finding.category == 'bloaters':
            base_priority = min(base_priority + 2, 10)

        return base_priority

    def _calculate_value(
        self,
        finding: CodeSmellFinding,
        impact: Optional[ImpactAnalysis]
    ) -> float:
        """
        Calculate estimated value of fixing this smell.

        Value considers:
        - Severity (higher = more value)
        - Impact (affects more code = more value)
        - Effort (lower effort = better ROI)
        """
        severity_values = {
            'critical': 10.0,
            'high': 7.0,
            'medium': 4.0,
            'low': 2.0,
            'info': 1.0
        }

        base_value = severity_values.get(finding.severity, 5.0)

        # Multiply by impact (affects more code = more valuable to fix)
        if impact:
            impact_multiplier = 1.0 + impact.impact_score
            base_value *= impact_multiplier

        # Category bonuses
        if finding.category in ['bloaters', 'complexity']:
            base_value *= 1.5  # High-value categories

        return base_value

    def _parse_refactoring_steps(self, technique_text: str) -> List[str]:
        """Parse refactoring technique into discrete steps."""
        steps = []
        for line in technique_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-) ')
                if clean:
                    steps.append(clean)
        return steps

    def generate_report(
        self,
        findings: List[CodeSmellFinding],
        impact_analyses: List[ImpactAnalysis],
        tasks: List[RefactoringTask]
    ) -> RefactoringReport:
        """
        Generate comprehensive refactoring report.

        Args:
            findings: Code smell findings
            impact_analyses: Impact analyses
            tasks: Refactoring tasks

        Returns:
            Comprehensive refactoring report
        """
        # Calculate statistics
        by_severity = {}
        for sev in CodeSmellSeverity:
            count = sum(1 for f in findings if f.severity == sev.value)
            if count > 0:
                by_severity[sev.value] = count

        by_category = {}
        for cat in CodeSmellCategory:
            count = sum(1 for f in findings if f.category == cat.value)
            if count > 0:
                by_category[cat.value] = count

        total_effort = sum(t.effort_hours for t in tasks)
        total_value = sum(t.estimated_value for t in tasks)

        # Generate summary
        summary = self._generate_summary(findings, tasks, by_severity)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings, tasks)

        report = RefactoringReport(
            report_id=f"REFACTOR_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            total_smells=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            findings=findings,
            impact_analyses=impact_analyses,
            tasks=tasks,
            total_effort_hours=total_effort,
            estimated_value=total_value,
            summary=summary,
            recommendations=recommendations
        )

        logger.info(f"Generated refactoring report {report.report_id}")
        return report

    def _generate_summary(
        self,
        findings: List[CodeSmellFinding],
        tasks: List[RefactoringTask],
        by_severity: Dict[str, int]
    ) -> str:
        """Generate executive summary."""
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)
        total = len(findings)

        summary_parts = [
            f"Code quality analysis identified {total} code smells."
        ]

        if critical > 0:
            summary_parts.append(
                f"{critical} CRITICAL issues severely impact maintainability."
            )

        if high > 0:
            summary_parts.append(
                f"{high} HIGH severity issues should be addressed soon."
            )

        if tasks:
            total_effort = sum(t.effort_hours for t in tasks)
            summary_parts.append(
                f"Estimated {total_effort:.1f} hours to address all issues."
            )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        findings: List[CodeSmellFinding],
        tasks: List[RefactoringTask]
    ) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        # Identify most common categories
        category_counts = {}
        for finding in findings:
            category_counts[finding.category] = (
                category_counts.get(finding.category, 0) + 1
            )

        # Priority 1: Top priority tasks
        if tasks:
            high_priority = [t for t in tasks if t.priority >= 7]
            if high_priority:
                recommendations.append(
                    f"Start with {len(high_priority)} high-priority refactorings "
                    f"(estimated {sum(t.effort_hours for t in high_priority):.1f} hours)"
                )

        # Priority 2: Most common category
        if category_counts:
            top_category = max(category_counts.items(), key=lambda x: x[1])
            recommendations.append(
                f"Focus on {top_category[0]} ({top_category[1]} instances) "
                f"for systematic improvement"
            )

        # Priority 3: Low-hanging fruit
        quick_wins = [t for t in tasks if t.effort_hours <= 1.0]
        if quick_wins:
            recommendations.append(
                f"Quick wins: {len(quick_wins)} refactorings can be done in <1 hour each"
            )

        # Priority 4: General advice
        recommendations.append(
            "Refactor incrementally: tackle 1-2 smells per sprint"
        )
        recommendations.append(
            "Add tests before refactoring to ensure behavior preservation"
        )

        return recommendations


def run_complete_refactoring_analysis(
    limit_per_pattern: int = 30
) -> Tuple[RefactoringReport, List[RefactoringTask]]:
    """
    Run complete refactoring analysis using all agents.

    Returns:
        (RefactoringReport, List[RefactoringTask])
    """
    logger.info("Starting complete refactoring analysis")

    with CPGQueryService() as cpg:
        # Agent 1: Detect code smells
        detector = TechnicalDebtDetector(cpg)
        findings = detector.detect_all_smells(limit_per_pattern)

        # Agent 2: Analyze impact
        analyzer = ImpactAnalyzer(cpg)
        impact_analyses = analyzer.analyze_bulk_impact(findings, limit=20)

        # Agent 3: Create refactoring plan
        planner = RefactoringPlanner()
        tasks = planner.create_refactoring_plan(findings, impact_analyses)
        report = planner.generate_report(findings, impact_analyses, tasks)

    logger.info("Complete refactoring analysis finished")
    return report, tasks
