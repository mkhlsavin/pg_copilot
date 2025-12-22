"""
Markdown Formatter for Patch Review Output.

Formats review verdicts as Markdown for human-readable reports,
documentation, and display in interfaces that support Markdown.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

from ..models import (
    ReviewVerdict,
    Finding,
    Severity,
    Recommendation,
    FindingCategory,
)

logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """
    Formats review verdicts as Markdown.

    Supports multiple output modes:
    - Full report: Complete detailed report
    - Summary: Executive summary
    - Findings table: Tabular findings list
    - Section-based: Individual sections
    """

    # Severity emoji mapping
    SEVERITY_EMOJI = {
        Severity.CRITICAL: "🔴",
        Severity.HIGH: "🟠",
        Severity.MEDIUM: "🟡",
        Severity.LOW: "🟢",
        Severity.INFO: "ℹ️"
    }

    # Recommendation emoji mapping
    RECOMMENDATION_EMOJI = {
        Recommendation.APPROVE: "✅",
        Recommendation.COMMENT: "💬",
        Recommendation.REQUEST_CHANGES: "⚠️",
        Recommendation.BLOCK: "🚫"
    }

    # Category icons
    CATEGORY_ICONS = {
        FindingCategory.SECURITY: "🔒",
        FindingCategory.PERFORMANCE: "⚡",
        FindingCategory.ERROR: "🐛",
        FindingCategory.ARCHITECTURE: "🏗️"
    }

    def format_full_report(self, verdict: ReviewVerdict) -> str:
        """
        Format complete review report.

        Args:
            verdict: The review verdict

        Returns:
            Markdown string with full report
        """
        sections = []

        # Header
        sections.append(self._format_header(verdict))

        # Executive summary
        sections.append(self._format_executive_summary(verdict))

        # Score breakdown
        sections.append(self._format_score_breakdown(verdict))

        # Critical findings (if any)
        critical_findings = [
            f for f in verdict.all_findings
            if f.severity == Severity.CRITICAL
        ]
        if critical_findings:
            sections.append(self._format_critical_findings(critical_findings))

        # Category details
        sections.append(self._format_security_section(verdict))
        sections.append(self._format_performance_section(verdict))
        sections.append(self._format_error_section(verdict))
        sections.append(self._format_architecture_section(verdict))

        # All findings table
        if verdict.all_findings:
            sections.append(self._format_findings_table(verdict.all_findings))

        # Recommendations
        sections.append(self._format_recommendations(verdict))

        # Footer
        sections.append(self._format_footer(verdict))

        return "\n\n".join(sections)

    def format_summary(self, verdict: ReviewVerdict) -> str:
        """
        Format executive summary only.

        Args:
            verdict: The review verdict

        Returns:
            Markdown string with summary
        """
        sections = [
            self._format_header(verdict),
            self._format_executive_summary(verdict),
            self._format_score_breakdown(verdict)
        ]

        return "\n\n".join(sections)

    def format_findings_only(
        self,
        verdict: ReviewVerdict,
        min_severity: Optional[Severity] = None
    ) -> str:
        """
        Format findings list only.

        Args:
            verdict: The review verdict
            min_severity: Minimum severity to include

        Returns:
            Markdown string with findings
        """
        findings = verdict.all_findings

        if min_severity:
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.INFO: 4
            }
            min_level = severity_order.get(min_severity, 4)
            findings = [
                f for f in findings
                if severity_order.get(f.severity, 5) <= min_level
            ]

        if not findings:
            return "No findings to report."

        return self._format_findings_table(findings)

    def _format_header(self, verdict: ReviewVerdict) -> str:
        """Format report header."""
        emoji = self.RECOMMENDATION_EMOJI.get(verdict.recommendation, "")
        return f"""# {emoji} Code Review Report

**Patch ID:** `{verdict.patch_id}`
**Review Date:** {verdict.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if verdict.reviewed_at else 'N/A'}
**Verdict:** **{verdict.recommendation.value.upper()}**"""

    def _format_executive_summary(self, verdict: ReviewVerdict) -> str:
        """Format executive summary section."""
        lines = ["## Executive Summary"]

        # Recommendation
        emoji = self.RECOMMENDATION_EMOJI.get(verdict.recommendation, "")
        lines.append(f"\n{emoji} **Recommendation: {verdict.recommendation.value.upper()}**")

        # Overall score with bar
        score = verdict.overall_score
        filled = int(score / 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"\n**Overall Score:** {score:.0f}/100 [{bar}]")

        # Quick stats
        total_findings = len(verdict.all_findings)
        blocking = verdict.critical_count + verdict.high_count
        lines.append(f"\n**Findings:** {total_findings} total ({blocking} blocking)")

        # Key concerns
        if verdict.critical_count > 0 or verdict.high_count > 0:
            lines.append("\n### ⚠️ Key Concerns")
            if verdict.critical_count > 0:
                lines.append(f"- {verdict.critical_count} critical issue(s) must be fixed")
            if verdict.high_count > 0:
                lines.append(f"- {verdict.high_count} high-severity issue(s) should be addressed")
            if verdict.architecture.breaking_changes > 0:
                lines.append(f"- {verdict.architecture.breaking_changes} breaking change(s) detected")

        return "\n".join(lines)

    def _format_score_breakdown(self, verdict: ReviewVerdict) -> str:
        """Format score breakdown section."""
        lines = ["## Score Breakdown"]
        lines.append("")
        lines.append("| Category | Score | Status |")
        lines.append("|----------|-------|--------|")

        categories = [
            ("🔒 Security", verdict.security.score),
            ("⚡ Performance", verdict.performance.score),
            ("🐛 Error Risk", verdict.error.score),
            ("🏗️ Architecture", verdict.architecture.score),
        ]

        for name, score in categories:
            status = "✅" if score >= 80 else ("⚠️" if score >= 60 else "❌")
            bar = self._score_bar(score)
            lines.append(f"| {name} | {score:.0f}/100 {bar} | {status} |")

        return "\n".join(lines)

    def _format_critical_findings(self, findings: List[Finding]) -> str:
        """Format critical findings section."""
        lines = ["## 🚨 Critical Findings"]
        lines.append("")
        lines.append("> These issues **must be addressed** before the patch can be merged.")
        lines.append("")

        for i, finding in enumerate(findings, 1):
            lines.append(f"### {i}. {finding.title}")
            lines.append("")
            lines.append(f"**Location:** `{finding.location}`")
            lines.append("")
            lines.append(f"**Description:** {finding.description}")
            if finding.code_snippet:
                lines.append("")
                lines.append("```")
                lines.append(finding.code_snippet[:300])
                lines.append("```")
            lines.append("")
            lines.append(f"**Recommendation:** {finding.recommendation}")
            if finding.cwe_id:
                lines.append(f"\n**CWE:** [{finding.cwe_id}](https://cwe.mitre.org/data/definitions/{finding.cwe_id.split('-')[1]}.html)")
            lines.append("")

        return "\n".join(lines)

    def _format_security_section(self, verdict: ReviewVerdict) -> str:
        """Format security section."""
        sec = verdict.security
        lines = ["## 🔒 Security Analysis"]
        lines.append("")
        lines.append(f"**Score:** {sec.score:.0f}/100")
        lines.append("")

        if sec.critical_count > 0 or sec.high_count > 0:
            lines.append("### Vulnerabilities Found")
            lines.append("")

            cwe_ids = getattr(sec, 'cwe_ids', [])
            if cwe_ids:
                lines.append("**CWE IDs:** " + ", ".join(cwe_ids[:5]))
                lines.append("")

            # Group findings by title for vulnerability types
            vuln_types = {}
            for f in sec.findings:
                vuln_types[f.title] = vuln_types.get(f.title, 0) + 1
            if vuln_types:
                lines.append("**Vulnerability Types:**")
                for vtype, count in list(vuln_types.items())[:5]:
                    lines.append(f"- {vtype}: {count}")
                lines.append("")

        else:
            lines.append("✅ No critical or high-severity security issues found.")

        return "\n".join(lines)

    def _format_performance_section(self, verdict: ReviewVerdict) -> str:
        """Format performance section."""
        perf = verdict.performance
        lines = ["## ⚡ Performance Analysis"]
        lines.append("")
        lines.append(f"**Score:** {perf.score:.0f}/100")
        lines.append("")

        metrics = []
        complexity_delta = getattr(perf, 'total_complexity_increase', 0)
        if complexity_delta != 0:
            sign = "+" if complexity_delta > 0 else ""
            metrics.append(f"- Complexity change: {sign}{complexity_delta}")
        new_loops = len(getattr(perf, 'new_loops', []))
        if new_loops > 0:
            metrics.append(f"- New loops introduced: {new_loops}")
        if perf.hot_paths_affected > 0:
            metrics.append(f"- Hot paths affected: {perf.hot_paths_affected}")

        if metrics:
            lines.append("### Metrics")
            lines.extend(metrics)
        else:
            lines.append("✅ No significant performance concerns.")

        if perf.estimated_impact:
            lines.append("")
            lines.append(f"**Estimated Impact:** {perf.estimated_impact}")

        return "\n".join(lines)

    def _format_error_section(self, verdict: ReviewVerdict) -> str:
        """Format error section."""
        err = verdict.error
        lines = ["## 🐛 Error Risk Analysis"]
        lines.append("")
        lines.append(f"**Score:** {err.score:.0f}/100")
        lines.append("")

        issues = []
        null_safety = getattr(err, 'null_safety_issues', [])
        if len(null_safety) > 0:
            issues.append(f"- Null safety issues: {len(null_safety)}")
        error_handling = getattr(err, 'error_handling_issues', [])
        if len(error_handling) > 0:
            issues.append(f"- Exception handling issues: {len(error_handling)}")
        resource_leaks = getattr(err, 'resource_leaks', [])
        if len(resource_leaks) > 0:
            issues.append(f"- Resource management issues: {len(resource_leaks)}")

        if issues:
            lines.append("### Issues Found")
            lines.extend(issues)
        else:
            lines.append("✅ No significant error risks detected.")

        return "\n".join(lines)

    def _format_architecture_section(self, verdict: ReviewVerdict) -> str:
        """Format architecture section."""
        arch = verdict.architecture
        lines = ["## 🏗️ Architecture Analysis"]
        lines.append("")
        lines.append(f"**Score:** {arch.score:.0f}/100")
        lines.append(f"**Blast Radius:** {arch.blast_radius_score:.0f}/100")
        lines.append("")

        concerns = []
        breaking_changes = getattr(arch, 'breaking_changes', 0)
        if breaking_changes > 0:
            concerns.append(f"- Breaking changes: {breaking_changes}")
        circular_deps = getattr(arch, 'circular_dependencies', 0)
        if circular_deps > 0:
            concerns.append(f"- Circular dependencies: {circular_deps}")
        layer_violations = getattr(arch, 'layer_violations', [])
        if len(layer_violations) > 0:
            concerns.append(f"- Layer violations: {len(layer_violations)}")
        new_imports = getattr(arch, 'new_imports', [])
        if len(new_imports) > 0:
            concerns.append(f"- New imports: {len(new_imports)}")

        if concerns:
            lines.append("### Concerns")
            lines.extend(concerns)

        affected_modules = [i.get('module', '') for i in new_imports if isinstance(i, dict)]
        if affected_modules:
            lines.append("")
            lines.append(f"**Affected Modules:** {', '.join(affected_modules[:5])}")

        if not concerns:
            lines.append("✅ Architecture looks good.")

        return "\n".join(lines)

    def _format_findings_table(self, findings: List[Finding]) -> str:
        """Format findings as table."""
        lines = ["## 📋 All Findings"]
        lines.append("")
        lines.append("| Severity | Category | Title | Location |")
        lines.append("|----------|----------|-------|----------|")

        for finding in findings:
            emoji = self.SEVERITY_EMOJI.get(finding.severity, "")
            cat_icon = self.CATEGORY_ICONS.get(finding.category, "")
            location = finding.location[:40] + "..." if len(finding.location) > 40 else finding.location
            title = finding.title[:50] + "..." if len(finding.title) > 50 else finding.title
            lines.append(f"| {emoji} {finding.severity.value} | {cat_icon} {finding.category.value} | {title} | `{location}` |")

        return "\n".join(lines)

    def _format_recommendations(self, verdict: ReviewVerdict) -> str:
        """Format recommendations section."""
        lines = ["## 💡 Recommendations"]
        lines.append("")

        if verdict.recommendation == Recommendation.BLOCK:
            lines.append("### Required Before Merge")
            lines.append("")
            lines.append("1. Fix all critical security vulnerabilities")
            lines.append("2. Address high-severity issues")
            if verdict.architecture.breaking_changes > 0:
                lines.append("3. Document and communicate breaking changes")
            lines.append("")
            lines.append("> ⛔ **This patch cannot be merged in its current state.**")

        elif verdict.recommendation == Recommendation.REQUEST_CHANGES:
            lines.append("### Suggested Changes")
            lines.append("")
            # Generate specific suggestions based on findings
            if verdict.security.high_count > 0:
                lines.append("- Address security concerns before proceeding")
            if verdict.error.high_count > 0:
                lines.append("- Fix error-prone code patterns")
            if verdict.architecture.layer_violations > 0:
                lines.append("- Resolve architectural layer violations")
            lines.append("")
            lines.append("> ⚠️ **Please address these issues before requesting re-review.**")

        elif verdict.recommendation == Recommendation.COMMENT:
            lines.append("### Optional Improvements")
            lines.append("")
            lines.append("The following improvements are suggested but not required:")
            lines.append("")
            for finding in verdict.all_findings[:3]:
                if finding.severity in [Severity.MEDIUM, Severity.LOW]:
                    lines.append(f"- {finding.title}: {finding.recommendation}")
            lines.append("")
            lines.append("> 💬 **This patch can be merged but consider addressing these items.**")

        else:  # APPROVE
            lines.append("✅ **This patch is approved for merge.**")
            lines.append("")
            if verdict.all_findings:
                lines.append("Minor improvements that could be addressed in follow-up:")
                for finding in verdict.all_findings[:2]:
                    lines.append(f"- {finding.title}")

        return "\n".join(lines)

    def _format_footer(self, verdict: ReviewVerdict) -> str:
        """Format report footer."""
        lines = ["---"]
        lines.append("")
        lines.append(f"*Review completed in {verdict.review_time_seconds:.2f} seconds*")
        lines.append("")
        lines.append("*Generated by CPG Code Review System*")

        return "\n".join(lines)

    def _score_bar(self, score: float, width: int = 5) -> str:
        """Generate a small score bar."""
        filled = int((score / 100) * width)
        return "█" * filled + "░" * (width - filled)
