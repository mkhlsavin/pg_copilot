"""
Verdict Aggregator for Patch Review System.

Aggregates individual verdicts (security, performance, error, architecture)
into a unified review verdict with overall recommendations.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

import duckdb

from ..models import (
    PatchContext,
    DeltaCPG,
    Finding,
    Severity,
    Recommendation,
    SecurityVerdict,
    PerformanceVerdict,
    ErrorVerdict,
    ArchitectureVerdict,
    ReviewVerdict,
    ReviewPolicy,
    ReviewSession,
    ReviewStatus,
    FindingCategory,
)
from ..analyzers import (
    PatchCallGraphAnalyzer,
    PatchDataFlowAnalyzer,
    PatchControlFlowAnalyzer,
    PatchDependencyAnalyzer,
)
from ..verdicts import (
    SecurityVerdictGenerator,
    PerformanceVerdictGenerator,
    ErrorVerdictGenerator,
    ArchitectureVerdictGenerator,
)

logger = logging.getLogger(__name__)


@dataclass
class AggregationConfig:
    """Configuration for verdict aggregation."""
    # Weight for each category in overall score (should sum to 1.0)
    security_weight: float = 0.35
    performance_weight: float = 0.20
    error_weight: float = 0.25
    architecture_weight: float = 0.20

    # Thresholds for recommendations
    block_threshold: float = 40.0  # Below this = BLOCK
    request_changes_threshold: float = 60.0  # Below this = REQUEST_CHANGES
    comment_threshold: float = 80.0  # Below this = COMMENT

    # Override rules (these override score-based decisions)
    block_on_critical: bool = True  # Block if any critical finding
    block_on_high_count: int = 5  # Block if this many high findings
    block_on_security_critical: bool = True  # Always block on security critical


class VerdictAggregator:
    """
    Aggregates individual category verdicts into a unified review.

    Responsibilities:
    - Run all analyzers and verdict generators
    - Combine scores with configurable weights
    - Apply policy rules for final recommendation
    - Generate unified review verdict
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        config: Optional[AggregationConfig] = None,
        policy: Optional[ReviewPolicy] = None
    ):
        """
        Initialize the verdict aggregator.

        Args:
            conn: DuckDB connection with CPG loaded
            config: Aggregation configuration
            policy: Review policy for blocking decisions
        """
        self.conn = conn
        self.config = config or AggregationConfig()
        self.policy = policy or self._default_policy()

        # Initialize analyzers
        self.call_graph_analyzer = PatchCallGraphAnalyzer(conn)
        self.dataflow_analyzer = PatchDataFlowAnalyzer(conn)
        self.control_flow_analyzer = PatchControlFlowAnalyzer(conn)
        self.dependency_analyzer = PatchDependencyAnalyzer(conn)

        # Initialize verdict generators
        self.security_generator = SecurityVerdictGenerator(conn)
        self.performance_generator = PerformanceVerdictGenerator(conn)
        self.error_generator = ErrorVerdictGenerator(conn)
        self.architecture_generator = ArchitectureVerdictGenerator(conn)

    def _default_policy(self) -> ReviewPolicy:
        """Create default review policy."""
        return ReviewPolicy(
            block_on_critical_security=True,
            block_on_high_security=False,
            block_on_critical_errors=True,
            block_on_breaking_changes=False,
            min_score_to_approve=70.0,
            min_score_to_comment=60.0,
            max_critical_findings=0,
            max_high_findings=5,
            max_complexity_increase=20
        )

    def generate_review(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        session: Optional[ReviewSession] = None
    ) -> ReviewVerdict:
        """
        Generate complete review verdict for the patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes
            session: Optional review session for tracking

        Returns:
            Complete review verdict with all category verdicts
        """
        logger.info(f"Generating review for patch {patch.patch_id}")
        start_time = datetime.now()

        # Run all analyzers first (they're shared between verdict generators)
        logger.debug("Running impact analyzers...")
        call_graph_result = self.call_graph_analyzer.analyze_call_graph_impact(
            patch, delta_cpg
        )
        dataflow_result = self.dataflow_analyzer.analyze_dataflow_changes(
            patch, delta_cpg
        )
        control_flow_result = self.control_flow_analyzer.analyze_control_flow_changes(
            patch, delta_cpg
        )
        dependency_result = self.dependency_analyzer.analyze_dependency_changes(
            patch, delta_cpg
        )

        # Generate individual verdicts
        logger.debug("Generating security verdict...")
        security_verdict = self.security_generator.generate_verdict(
            patch, delta_cpg, dataflow_result
        )

        logger.debug("Generating performance verdict...")
        performance_verdict = self.performance_generator.generate_verdict(
            patch, delta_cpg, control_flow_result, call_graph_result
        )

        logger.debug("Generating error verdict...")
        error_verdict = self.error_generator.generate_verdict(
            patch, delta_cpg, control_flow_result
        )

        logger.debug("Generating architecture verdict...")
        architecture_verdict = self.architecture_generator.generate_verdict(
            patch, delta_cpg, call_graph_result, dependency_result
        )

        # Aggregate scores
        overall_score = self._calculate_overall_score(
            security_verdict,
            performance_verdict,
            error_verdict,
            architecture_verdict
        )

        # Combine all findings
        all_findings = self._combine_findings(
            security_verdict.findings,
            performance_verdict.findings,
            error_verdict.findings,
            architecture_verdict.findings
        )

        # Count findings by severity
        severity_counts = self._count_by_severity(all_findings)

        # Determine recommendation
        recommendation = self._determine_recommendation(
            overall_score,
            security_verdict,
            performance_verdict,
            error_verdict,
            architecture_verdict,
            severity_counts
        )

        # Calculate blast radius
        blast_radius_score = architecture_verdict.blast_radius_score

        # Generate summary
        summary = self._generate_summary(
            patch,
            overall_score,
            recommendation,
            severity_counts,
            security_verdict,
            performance_verdict,
            error_verdict,
            architecture_verdict
        )

        review_time = (datetime.now() - start_time).total_seconds()

        verdict = ReviewVerdict(
            patch_id=patch.patch_id,
            overall_score=overall_score,
            recommendation=recommendation,
            security=security_verdict,
            performance=performance_verdict,
            error=error_verdict,
            architecture=architecture_verdict,
            all_findings=all_findings,
            critical_count=severity_counts.get(Severity.CRITICAL, 0),
            high_count=severity_counts.get(Severity.HIGH, 0),
            medium_count=severity_counts.get(Severity.MEDIUM, 0),
            low_count=severity_counts.get(Severity.LOW, 0),
            blast_radius_score=blast_radius_score,
            review_time_seconds=review_time,
            summary=summary,
            reviewed_at=datetime.now()
        )

        logger.info(
            f"Review complete: score={overall_score:.2f}, "
            f"recommendation={recommendation.value}, "
            f"time={review_time:.2f}s"
        )

        return verdict

    def _calculate_overall_score(
        self,
        security: SecurityVerdict,
        performance: PerformanceVerdict,
        error: ErrorVerdict,
        architecture: ArchitectureVerdict
    ) -> float:
        """Calculate weighted overall score."""
        score = (
            security.score * self.config.security_weight +
            performance.score * self.config.performance_weight +
            error.score * self.config.error_weight +
            architecture.score * self.config.architecture_weight
        )
        return round(score, 2)

    def _combine_findings(self, *finding_lists: List[Finding]) -> List[Finding]:
        """Combine and deduplicate findings from all categories."""
        all_findings: List[Finding] = []
        seen_locations: set = set()

        for findings in finding_lists:
            for finding in findings:
                # Simple deduplication by location + title
                key = f"{finding.location}:{finding.title}"
                if key not in seen_locations:
                    seen_locations.add(key)
                    all_findings.append(finding)

        # Sort by severity (critical first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 5))

        return all_findings

    def _count_by_severity(self, findings: List[Finding]) -> Dict[Severity, int]:
        """Count findings by severity."""
        counts: Dict[Severity, int] = {}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def _determine_recommendation(
        self,
        overall_score: float,
        security: SecurityVerdict,
        performance: PerformanceVerdict,
        error: ErrorVerdict,
        architecture: ArchitectureVerdict,
        severity_counts: Dict[Severity, int]
    ) -> Recommendation:
        """Determine final recommendation based on scores and policy."""
        critical_count = severity_counts.get(Severity.CRITICAL, 0)
        high_count = severity_counts.get(Severity.HIGH, 0)

        # Policy-based overrides
        if self.config.block_on_critical and critical_count > 0:
            return Recommendation.BLOCK

        if self.config.block_on_security_critical and security.critical_count > 0:
            return Recommendation.BLOCK

        if high_count >= self.config.block_on_high_count:
            return Recommendation.BLOCK

        # Check if scores are critically low (use min_score thresholds)
        # Security below comment threshold is a blocking issue
        if security.score < self.policy.min_score_to_comment:
            return Recommendation.BLOCK

        # Error handling issues below comment threshold need changes
        if error.score < self.policy.min_score_to_comment:
            return Recommendation.REQUEST_CHANGES

        # Score-based recommendations
        if overall_score < self.config.block_threshold:
            return Recommendation.BLOCK
        elif overall_score < self.config.request_changes_threshold:
            return Recommendation.REQUEST_CHANGES
        elif overall_score < self.config.comment_threshold:
            return Recommendation.COMMENT
        else:
            return Recommendation.APPROVE

    def _generate_summary(
        self,
        patch: PatchContext,
        overall_score: float,
        recommendation: Recommendation,
        severity_counts: Dict[Severity, int],
        security: SecurityVerdict,
        performance: PerformanceVerdict,
        error: ErrorVerdict,
        architecture: ArchitectureVerdict
    ) -> str:
        """Generate human-readable summary of the review."""
        lines = []

        # Header
        emoji_map = {
            Recommendation.APPROVE: "✅",
            Recommendation.COMMENT: "💬",
            Recommendation.REQUEST_CHANGES: "⚠️",
            Recommendation.BLOCK: "🚫"
        }
        emoji = emoji_map.get(recommendation, "")
        lines.append(f"{emoji} **Review Verdict: {recommendation.value.upper()}**")
        lines.append("")

        # Overall score
        lines.append(f"**Overall Score:** {overall_score:.0f}/100")
        lines.append("")

        # Category scores
        lines.append("### Category Scores")
        lines.append(f"- Security: {security.score:.0f}/100 ({security.critical_count}C/{security.high_count}H)")
        lines.append(f"- Performance: {performance.score:.0f}/100")
        lines.append(f"- Error Risk: {error.score:.0f}/100")
        lines.append(f"- Architecture: {architecture.score:.0f}/100")
        lines.append("")

        # Finding summary
        total_findings = sum(severity_counts.values())
        if total_findings > 0:
            lines.append("### Findings Summary")
            if severity_counts.get(Severity.CRITICAL, 0) > 0:
                lines.append(f"- 🔴 Critical: {severity_counts[Severity.CRITICAL]}")
            if severity_counts.get(Severity.HIGH, 0) > 0:
                lines.append(f"- 🟠 High: {severity_counts[Severity.HIGH]}")
            if severity_counts.get(Severity.MEDIUM, 0) > 0:
                lines.append(f"- 🟡 Medium: {severity_counts[Severity.MEDIUM]}")
            if severity_counts.get(Severity.LOW, 0) > 0:
                lines.append(f"- 🟢 Low: {severity_counts[Severity.LOW]}")
            lines.append("")

        # Key concerns
        concerns = []
        if security.critical_count > 0:
            concerns.append(f"{security.critical_count} critical security vulnerabilities")
        if architecture.breaking_changes > 0:
            concerns.append(f"{architecture.breaking_changes} breaking changes")
        if architecture.circular_dependencies > 0:
            concerns.append(f"{architecture.circular_dependencies} circular dependencies")
        if performance.hot_paths_affected > 0:
            concerns.append(f"{performance.hot_paths_affected} hot paths affected")

        if concerns:
            lines.append("### Key Concerns")
            for concern in concerns:
                lines.append(f"- {concern}")
            lines.append("")

        # Patch stats
        lines.append("### Patch Statistics")
        lines.append(f"- Files changed: {len(patch.files)}")
        lines.append(f"- Methods changed: {len(patch.changed_methods)}")
        lines.append(f"- Lines added: {patch.total_additions}")
        lines.append(f"- Lines deleted: {patch.total_deletions}")

        return "\n".join(lines)

    def store_review(self, verdict: ReviewVerdict, session: ReviewSession) -> None:
        """
        Store review results in the database.

        Args:
            verdict: The review verdict
            session: The review session
        """
        try:
            # Update session status
            self.conn.execute("""
                UPDATE review_sessions
                SET status = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    verdict = ?
                WHERE session_id = ?
            """, [
                ReviewStatus.COMPLETED.value,
                verdict.to_dict() if hasattr(verdict, 'to_dict') else str(verdict),
                session.session_id
            ])

            # Store in review history
            self.conn.execute("""
                INSERT INTO review_history (
                    patch_id, session_id, overall_score,
                    security_score, performance_score, error_score, architecture_score,
                    recommendation, critical_count, high_count, medium_count, low_count,
                    blast_radius_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                verdict.patch_id,
                session.session_id,
                verdict.overall_score,
                verdict.security.score,
                verdict.performance.score,
                verdict.error.score,
                verdict.architecture.score,
                verdict.recommendation.value,
                verdict.critical_count,
                verdict.high_count,
                verdict.medium_count,
                verdict.low_count,
                verdict.blast_radius_score
            ])

            # Store findings
            for finding in verdict.all_findings:
                self.conn.execute("""
                    INSERT INTO review_findings (
                        id, session_id, category, severity, title,
                        description, location, code_snippet, recommendation,
                        confidence, pattern_id, cwe_id, is_new
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{session.session_id}_{hash(f'{finding.location}:{finding.title}')}",
                    session.session_id,
                    finding.category.value,
                    finding.severity.value,
                    finding.title,
                    finding.description,
                    finding.location,
                    finding.code_snippet,
                    finding.recommendation,
                    finding.confidence,
                    finding.pattern_id,
                    finding.cwe_id,
                    finding.is_new
                ])

            logger.info(f"Stored review results for session {session.session_id}")

        except Exception as e:
            logger.error(f"Failed to store review results: {e}")
            raise

    def get_review_history(
        self,
        patch_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get review history for trending analysis.

        Args:
            patch_id: Optional filter by patch ID
            limit: Maximum number of results

        Returns:
            List of historical review summaries
        """
        if patch_id:
            query = """
                SELECT * FROM review_history
                WHERE patch_id = ?
                ORDER BY reviewed_at DESC
                LIMIT ?
            """
            result = self.conn.execute(query, [patch_id, limit]).fetchall()
        else:
            query = """
                SELECT * FROM review_history
                ORDER BY reviewed_at DESC
                LIMIT ?
            """
            result = self.conn.execute(query, [limit]).fetchall()

        columns = [
            'id', 'patch_id', 'session_id', 'overall_score',
            'security_score', 'performance_score', 'error_score', 'architecture_score',
            'recommendation', 'critical_count', 'high_count', 'medium_count', 'low_count',
            'blast_radius_score', 'reviewed_at'
        ]

        return [dict(zip(columns, row)) for row in result]
