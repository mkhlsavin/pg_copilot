"""
Optimization Advisor Agent for Performance Analysis

Provides optimization recommendations:
- Bottleneck prioritization by impact
- Optimization step generation
- Speedup and effort estimation
- Risk assessment
- Report generation
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .models import (
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    PerformanceReport
)
from ..performance_patterns import BottleneckSeverity, BottleneckCategory

logger = logging.getLogger(__name__)


class OptimizationAdvisor:
    """
    Provides optimization recommendations

    Responsibilities:
    - Prioritize bottlenecks by impact
    - Generate optimization recommendations
    - Estimate speedup and effort
    - Assess implementation risk
    """

    def create_optimization_plan(
        self,
        findings: List[BottleneckFinding],
        resource_analyses: List[ResourceUsage]
    ) -> List[OptimizationRecommendation]:
        """
        Create prioritized optimization plan

        Args:
            findings: Bottleneck findings
            resource_analyses: Resource usage analyses

        Returns:
            Prioritized list of optimization recommendations
        """
        recommendations = []

        # Create resource map for quick lookup
        resource_map = {ra.method_name: ra for ra in resource_analyses}

        for finding in findings:
            resource_usage = resource_map.get(finding.method_name)

            # Calculate priority (1-10)
            priority = self._calculate_priority(finding, resource_usage)

            # Estimate implementation effort
            effort = self._estimate_effort(finding)

            # Assess risk level
            risk = self._assess_risk(finding, resource_usage)

            # Parse optimization steps
            steps = self._parse_optimization_steps(finding.optimization_technique)

            # Generate code example
            code_example = self._generate_code_example(finding)

            recommendation = OptimizationRecommendation(
                recommendation_id=finding.finding_id.replace('_', '_OPT_'),
                finding_id=finding.finding_id,
                pattern_id=finding.pattern_id,
                optimization_steps=steps,
                code_example=code_example,
                estimated_speedup=finding.potential_speedup,
                implementation_effort=effort,
                priority=priority,
                risk_level=risk
            )
            recommendations.append(recommendation)

        # Sort by priority (highest first)
        recommendations.sort(key=lambda r: r.priority, reverse=True)

        logger.info(f"Created optimization plan with {len(recommendations)} recommendations")
        return recommendations

    def _calculate_priority(
        self,
        finding: BottleneckFinding,
        resource_usage: Optional[ResourceUsage]
    ) -> int:
        """Calculate optimization priority (1-10)"""
        # Base priority on severity
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2,
            'info': 1
        }

        base_priority = severity_scores.get(finding.severity, 5)

        # Adjust based on resource intensity
        if resource_usage:
            if resource_usage.resource_intensity > 0.7:
                base_priority = min(base_priority + 2, 10)
            elif resource_usage.resource_intensity > 0.4:
                base_priority = min(base_priority + 1, 10)

        # Boost algorithmic issues (high impact)
        if finding.category == 'algorithmic':
            base_priority = min(base_priority + 1, 10)

        return base_priority

    def _estimate_effort(self, finding: BottleneckFinding) -> str:
        """Estimate implementation effort"""
        # Algorithmic changes often require more effort
        if finding.category in ['algorithmic', 'concurrency']:
            return 'high'
        elif finding.category in ['memory', 'io']:
            return 'medium'
        else:
            return 'low'

    def _assess_risk(
        self,
        finding: BottleneckFinding,
        resource_usage: Optional[ResourceUsage]
    ) -> str:
        """Assess implementation risk"""
        # High complexity = higher risk
        if resource_usage and resource_usage.complexity_score > 20:
            return 'high'
        elif resource_usage and resource_usage.complexity_score > 10:
            return 'medium'
        else:
            return 'low'

    def _parse_optimization_steps(self, technique_text: str) -> List[str]:
        """Parse optimization technique into discrete steps"""
        steps = []
        for line in technique_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-) ')
                if clean:
                    steps.append(clean)
        return steps

    def _generate_code_example(self, finding: BottleneckFinding) -> str:
        """Generate or retrieve code example"""
        # In real implementation, could fetch from pattern library
        return f"// See {finding.pattern_name} pattern for code examples"

    def generate_report(
        self,
        findings: List[BottleneckFinding],
        resource_analyses: List[ResourceUsage],
        recommendations: List[OptimizationRecommendation]
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report

        Args:
            findings: Bottleneck findings
            resource_analyses: Resource analyses
            recommendations: Optimization recommendations

        Returns:
            Comprehensive performance report
        """
        # Calculate statistics
        by_severity = {}
        for sev in BottleneckSeverity:
            count = sum(1 for f in findings if f.severity == sev.value)
            if count > 0:
                by_severity[sev.value] = count

        by_category = {}
        for cat in BottleneckCategory:
            count = sum(1 for f in findings if f.category == cat.value)
            if count > 0:
                by_category[cat.value] = count

        # Aggregate potential speedup
        total_speedup = self._aggregate_speedup(recommendations)

        # Generate summary
        summary = self._generate_summary(findings, recommendations, by_severity)

        # Generate action items
        action_items = self._generate_action_items(recommendations)

        report = PerformanceReport(
            report_id=f"PERFORMANCE_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            total_bottlenecks=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            findings=findings,
            resource_analyses=resource_analyses,
            recommendations=recommendations,
            total_potential_speedup=total_speedup,
            summary=summary,
            action_items=action_items
        )

        logger.info(f"Generated performance report {report.report_id}")
        return report

    def _aggregate_speedup(self, recommendations: List[OptimizationRecommendation]) -> str:
        """Aggregate total potential speedup"""
        # Simplified aggregation
        if not recommendations:
            return "No optimizations identified"

        high_impact = sum(1 for r in recommendations if 'to O(n)' in r.estimated_speedup or '100x' in r.estimated_speedup)
        medium_impact = sum(1 for r in recommendations if '10x' in r.estimated_speedup or '50x' in r.estimated_speedup)

        if high_impact > 0:
            return f"Up to 100x potential speedup ({high_impact} major optimizations)"
        elif medium_impact > 0:
            return f"Up to 50x potential speedup ({medium_impact} significant optimizations)"
        else:
            return f"Up to 10x potential speedup ({len(recommendations)} optimizations)"

    def _generate_summary(
        self,
        findings: List[BottleneckFinding],
        recommendations: List[OptimizationRecommendation],
        by_severity: Dict[str, int]
    ) -> str:
        """Generate executive summary"""
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)
        total = len(findings)

        summary_parts = [
            f"Identified {total} performance bottlenecks.",
            f"Critical: {critical}, High: {high}.",
            f"Top priority: {recommendations[0].pattern_id if recommendations else 'N/A'}."
        ]

        return " ".join(summary_parts)

    def _generate_action_items(self, recommendations: List[OptimizationRecommendation]) -> List[str]:
        """Generate prioritized action items"""
        action_items = []

        # Top 5 priorities
        for rec in recommendations[:5]:
            if rec.optimization_steps:
                action_items.append(f"[Priority {rec.priority}] {rec.optimization_steps[0]}")

        return action_items


__all__ = ['OptimizationAdvisor']
