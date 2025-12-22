"""
PR Comment Formatter for Patch Review Output.

Formats review verdicts for inline comments on GitHub Pull Requests
and GitLab Merge Requests.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from ..models import (
    ReviewVerdict,
    Finding,
    Severity,
    Recommendation,
    FindingCategory,
)

logger = logging.getLogger(__name__)


@dataclass
class InlineComment:
    """Represents an inline comment on a specific line."""
    filepath: str
    line_number: int
    body: str
    severity: Severity
    side: str = "RIGHT"  # LEFT for deletions, RIGHT for additions
    start_line: Optional[int] = None  # For multi-line comments


@dataclass
class ReviewComment:
    """Represents the main review comment."""
    body: str
    event: str  # APPROVE, REQUEST_CHANGES, COMMENT
    comments: List[InlineComment] = field(default_factory=list)


class PRCommentFormatter:
    """
    Formats review verdicts for GitHub/GitLab PR comments.

    Generates:
    - Main review summary comment
    - Inline comments on specific lines
    - Suggestion blocks for fixes
    """

    # Severity emoji mapping
    SEVERITY_EMOJI = {
        Severity.CRITICAL: "🔴",
        Severity.HIGH: "🟠",
        Severity.MEDIUM: "🟡",
        Severity.LOW: "🟢",
        Severity.INFO: "ℹ️"
    }

    # Map recommendation to GitHub review event
    RECOMMENDATION_TO_EVENT = {
        Recommendation.APPROVE: "APPROVE",
        Recommendation.COMMENT: "COMMENT",
        Recommendation.REQUEST_CHANGES: "REQUEST_CHANGES",
        Recommendation.BLOCK: "REQUEST_CHANGES"
    }

    def __init__(
        self,
        max_inline_comments: int = 25,
        include_code_suggestions: bool = True,
        collapse_low_severity: bool = True
    ):
        """
        Initialize the PR comment formatter.

        Args:
            max_inline_comments: Maximum number of inline comments
            include_code_suggestions: Whether to include fix suggestions
            collapse_low_severity: Whether to collapse low/info findings
        """
        self.max_inline_comments = max_inline_comments
        self.include_code_suggestions = include_code_suggestions
        self.collapse_low_severity = collapse_low_severity

    def format_github_review(self, verdict: ReviewVerdict) -> ReviewComment:
        """
        Format as GitHub pull request review.

        Args:
            verdict: The review verdict

        Returns:
            ReviewComment with body and inline comments
        """
        # Generate main review body
        body = self._format_review_body(verdict)

        # Generate inline comments
        inline_comments = self._generate_inline_comments(verdict)

        # Determine review event
        event = self.RECOMMENDATION_TO_EVENT.get(
            verdict.recommendation,
            "COMMENT"
        )

        return ReviewComment(
            body=body,
            event=event,
            comments=inline_comments
        )

    def format_gitlab_review(self, verdict: ReviewVerdict) -> Dict:
        """
        Format as GitLab merge request review.

        Args:
            verdict: The review verdict

        Returns:
            Dictionary with GitLab-specific format
        """
        body = self._format_review_body(verdict)
        inline_comments = self._generate_inline_comments(verdict)

        # GitLab uses different structure
        discussions = []
        for comment in inline_comments:
            discussions.append({
                "body": comment.body,
                "position": {
                    "new_path": comment.filepath,
                    "new_line": comment.line_number,
                    "position_type": "text"
                }
            })

        return {
            "body": body,
            "discussions": discussions,
            "approved": verdict.recommendation == Recommendation.APPROVE
        }

    def _format_review_body(self, verdict: ReviewVerdict) -> str:
        """Format the main review comment body."""
        lines = []

        # Header with verdict
        emoji = self._get_recommendation_emoji(verdict.recommendation)
        lines.append(f"## {emoji} Code Review: {verdict.recommendation.value.upper()}")
        lines.append("")

        # Score summary
        lines.append(f"**Overall Score:** {verdict.overall_score:.0f}/100")
        lines.append("")

        # Category scores in compact format
        lines.append("| Category | Score |")
        lines.append("|----------|-------|")
        lines.append(f"| 🔒 Security | {verdict.security.score:.0f} |")
        lines.append(f"| ⚡ Performance | {verdict.performance.score:.0f} |")
        lines.append(f"| 🐛 Error Risk | {verdict.error.score:.0f} |")
        lines.append(f"| 🏗️ Architecture | {verdict.architecture.score:.0f} |")
        lines.append("")

        # Finding summary
        if verdict.all_findings:
            lines.append("### Findings")
            lines.append("")

            # Group by severity
            if verdict.critical_count > 0:
                lines.append(f"🔴 **{verdict.critical_count} Critical** - Must fix before merge")
            if verdict.high_count > 0:
                lines.append(f"🟠 **{verdict.high_count} High** - Should be addressed")
            if verdict.medium_count > 0:
                lines.append(f"🟡 **{verdict.medium_count} Medium** - Consider fixing")
            if verdict.low_count > 0:
                lines.append(f"🟢 **{verdict.low_count} Low** - Optional improvements")
            lines.append("")

        # Key concerns (if blocking)
        if verdict.recommendation in [Recommendation.BLOCK, Recommendation.REQUEST_CHANGES]:
            lines.append("### ⚠️ Required Changes")
            lines.append("")

            # List critical/high findings
            for finding in verdict.all_findings:
                if finding.severity in [Severity.CRITICAL, Severity.HIGH]:
                    emoji = self.SEVERITY_EMOJI.get(finding.severity, "")
                    lines.append(f"- {emoji} **{finding.title}** at `{finding.location}`")

            lines.append("")

        # Collapsible section for medium/low findings
        medium_low = [
            f for f in verdict.all_findings
            if f.severity in [Severity.MEDIUM, Severity.LOW]
        ]
        if medium_low and self.collapse_low_severity:
            lines.append("<details>")
            lines.append(f"<summary>📋 {len(medium_low)} additional findings (click to expand)</summary>")
            lines.append("")
            for finding in medium_low[:10]:
                emoji = self.SEVERITY_EMOJI.get(finding.severity, "")
                lines.append(f"- {emoji} {finding.title} at `{finding.location}`")
            if len(medium_low) > 10:
                lines.append(f"- ... and {len(medium_low) - 10} more")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Reviewed in {verdict.review_time_seconds:.1f}s by CPG Code Review*")

        return "\n".join(lines)

    def _generate_inline_comments(
        self,
        verdict: ReviewVerdict
    ) -> List[InlineComment]:
        """Generate inline comments for findings."""
        comments = []

        # Sort by severity (critical first)
        sorted_findings = sorted(
            verdict.all_findings,
            key=lambda f: (
                0 if f.severity == Severity.CRITICAL else
                1 if f.severity == Severity.HIGH else
                2 if f.severity == Severity.MEDIUM else
                3
            )
        )

        for finding in sorted_findings:
            if len(comments) >= self.max_inline_comments:
                break

            # Parse location
            filepath, line_number = self._parse_location(finding.location)
            if not filepath or not line_number:
                continue

            # Format comment body
            body = self._format_inline_comment_body(finding)

            comments.append(InlineComment(
                filepath=filepath,
                line_number=line_number,
                body=body,
                severity=finding.severity
            ))

        return comments

    def _format_inline_comment_body(self, finding: Finding) -> str:
        """Format the body of an inline comment."""
        lines = []

        # Header with severity
        emoji = self.SEVERITY_EMOJI.get(finding.severity, "")
        lines.append(f"### {emoji} {finding.severity.value.upper()}: {finding.title}")
        lines.append("")

        # Description
        lines.append(finding.description)
        lines.append("")

        # CWE reference for security issues
        if finding.cwe_id:
            cwe_num = finding.cwe_id.split("-")[1] if "-" in finding.cwe_id else finding.cwe_id
            lines.append(f"📚 [{finding.cwe_id}](https://cwe.mitre.org/data/definitions/{cwe_num}.html)")
            lines.append("")

        # Recommendation
        if finding.recommendation:
            lines.append("**💡 Recommendation:**")
            lines.append(finding.recommendation)
            lines.append("")

        # Confidence indicator
        if finding.confidence:
            confidence_bar = "█" * int(finding.confidence * 5) + "░" * (5 - int(finding.confidence * 5))
            lines.append(f"*Confidence: {confidence_bar} ({finding.confidence:.0%})*")

        return "\n".join(lines)

    def _parse_location(self, location: str) -> Tuple[Optional[str], Optional[int]]:
        """Parse filepath and line number from location string."""
        if not location:
            return None, None

        # Handle "filepath:line" format
        if ":" in location:
            parts = location.rsplit(":", 1)
            filepath = parts[0]
            try:
                line_number = int(parts[1])
                return filepath, line_number
            except ValueError:
                return filepath, None

        return location, None

    def _get_recommendation_emoji(self, recommendation: Recommendation) -> str:
        """Get emoji for recommendation."""
        emoji_map = {
            Recommendation.APPROVE: "✅",
            Recommendation.COMMENT: "💬",
            Recommendation.REQUEST_CHANGES: "⚠️",
            Recommendation.BLOCK: "🚫"
        }
        return emoji_map.get(recommendation, "")

    def format_suggestion_block(
        self,
        original_code: str,
        suggested_code: str,
        explanation: str
    ) -> str:
        """
        Format a code suggestion block (GitHub-style).

        Args:
            original_code: The original code
            suggested_code: The suggested replacement
            explanation: Explanation of the change

        Returns:
            Markdown string with suggestion block
        """
        lines = []

        lines.append(explanation)
        lines.append("")
        lines.append("```suggestion")
        lines.append(suggested_code)
        lines.append("```")

        return "\n".join(lines)

    def format_check_run_summary(self, verdict: ReviewVerdict) -> Dict:
        """
        Format as GitHub Check Run summary.

        Args:
            verdict: The review verdict

        Returns:
            Dictionary for GitHub Check Run API
        """
        # Determine conclusion
        if verdict.recommendation == Recommendation.APPROVE:
            conclusion = "success"
        elif verdict.recommendation == Recommendation.COMMENT:
            conclusion = "neutral"
        else:
            conclusion = "failure"

        # Build annotations
        annotations = []
        for finding in verdict.all_findings[:50]:  # GitHub limit
            filepath, line = self._parse_location(finding.location)
            if filepath and line:
                level_map = {
                    Severity.CRITICAL: "failure",
                    Severity.HIGH: "failure",
                    Severity.MEDIUM: "warning",
                    Severity.LOW: "notice",
                    Severity.INFO: "notice"
                }
                annotations.append({
                    "path": filepath,
                    "start_line": line,
                    "end_line": line,
                    "annotation_level": level_map.get(finding.severity, "notice"),
                    "message": finding.description,
                    "title": finding.title
                })

        return {
            "name": "CPG Code Review",
            "head_sha": verdict.patch_id,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": f"Score: {verdict.overall_score:.0f}/100 - {verdict.recommendation.value}",
                "summary": self._format_check_summary(verdict),
                "annotations": annotations
            }
        }

    def _format_check_summary(self, verdict: ReviewVerdict) -> str:
        """Format summary for check run."""
        lines = []

        lines.append(f"**Overall Score:** {verdict.overall_score:.0f}/100")
        lines.append("")
        lines.append("| Category | Score |")
        lines.append("|----------|-------|")
        lines.append(f"| Security | {verdict.security.score:.0f} |")
        lines.append(f"| Performance | {verdict.performance.score:.0f} |")
        lines.append(f"| Error Risk | {verdict.error.score:.0f} |")
        lines.append(f"| Architecture | {verdict.architecture.score:.0f} |")
        lines.append("")

        if verdict.critical_count > 0:
            lines.append(f"⚠️ **{verdict.critical_count} critical issues** require attention")

        return "\n".join(lines)
