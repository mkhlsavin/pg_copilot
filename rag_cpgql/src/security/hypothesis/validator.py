"""
Hypothesis Validator for Security Analysis.

Orchestrates the complete hypothesis validation workflow:
1. Generate hypotheses
2. Score and prioritize
3. Synthesize queries
4. Execute against CPG
5. Collect evidence and metrics
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from .models import (
    SecurityHypothesis,
    HypothesisBatch,
    ValidationResults,
    ValidationStatus,
)
from .knowledge_base import SecurityKnowledgeBase, get_knowledge_base
from .hypothesis_generator import HypothesisGenerator
from .multi_criteria_scorer import MultiCriteriaScorer, CodebaseStats
from .query_synthesizer import QuerySynthesizer
from .executor import QueryExecutor

logger = logging.getLogger(__name__)


class HypothesisValidator:
    """Orchestrates hypothesis-driven security analysis.

    Combines all components of the multi-criteria hypothesis generation
    algorithm into a complete validation workflow.
    """

    def __init__(
        self,
        db_path: str,
        knowledge_base: Optional[SecurityKnowledgeBase] = None,
    ):
        """Initialize validator.

        Args:
            db_path: Path to DuckDB CPG database
            knowledge_base: Security knowledge base (uses default if None)
        """
        self.db_path = db_path
        self.kb = knowledge_base or get_knowledge_base()

        # Initialize components
        self.generator = HypothesisGenerator(self.kb)
        self.scorer = MultiCriteriaScorer(self.kb)
        self.synthesizer = QuerySynthesizer()
        self.executor = QueryExecutor(db_path)

    def run_validation(
        self,
        language: str = "C",
        max_hypotheses: int = 50,
        categories: Optional[List[str]] = None,
        target_cves: Optional[List[str]] = None,
        min_priority_score: float = 0.3,
    ) -> ValidationResults:
        """Run complete hypothesis validation workflow.

        Args:
            language: Target language
            max_hypotheses: Maximum hypotheses to generate
            categories: Filter by vulnerability categories
            target_cves: Specific CVEs to target
            min_priority_score: Minimum score threshold for validation

        Returns:
            ValidationResults with comprehensive metrics
        """
        start_time = datetime.utcnow()

        # Initialize results
        results = ValidationResults(
            batch_id=f"validation-{start_time.strftime('%Y%m%d-%H%M%S')}",
            total_hypotheses=0,
            executed_queries=0,
        )

        try:
            # Step 1: Generate hypotheses
            logger.info("Step 1: Generating hypotheses...")
            generation_start = datetime.utcnow()

            hypotheses = self._generate_hypotheses(
                language=language,
                max_hypotheses=max_hypotheses,
                categories=categories,
                target_cves=target_cves,
            )

            results.total_hypotheses = len(hypotheses)
            results.generation_time_sec = (
                datetime.utcnow() - generation_start
            ).total_seconds()

            logger.info(f"Generated {len(hypotheses)} hypotheses")

            # Step 2: Compute codebase stats and score
            logger.info("Step 2: Scoring hypotheses...")
            stats = self._compute_codebase_stats()
            self.scorer.update_codebase_stats(stats)

            hypotheses = self.scorer.score_batch(hypotheses)

            # Filter by minimum priority
            hypotheses = [
                h for h in hypotheses
                if h.priority_score >= min_priority_score
            ]
            logger.info(f"Filtered to {len(hypotheses)} high-priority hypotheses")

            # Step 3: Synthesize queries
            logger.info("Step 3: Synthesizing queries...")
            for h in hypotheses:
                if not h.sql_query:
                    self.synthesizer.synthesize_query(h)

            # Step 4: Execute and validate
            logger.info("Step 4: Executing validation queries...")
            execution_start = datetime.utcnow()

            with self.executor:
                validated = self.executor.validate_batch(hypotheses)

            results.execution_time_sec = (
                datetime.utcnow() - execution_start
            ).total_seconds()
            results.executed_queries = len(validated)

            # Step 5: Compile metrics
            logger.info("Step 5: Computing metrics...")
            self._compile_metrics(results, validated, target_cves)

            results.completed_at = datetime.utcnow()

            logger.info(
                f"Validation complete: "
                f"{results.confirmed_hypotheses} confirmed, "
                f"{results.rejected_hypotheses} rejected"
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise

        return results

    def validate_cve_patterns(
        self,
        cve_ids: List[str],
    ) -> ValidationResults:
        """Validate specifically for known CVE patterns.

        Args:
            cve_ids: List of CVE identifiers to target

        Returns:
            ValidationResults focused on CVE detection
        """
        return self.run_validation(
            language="C",
            max_hypotheses=100,
            target_cves=cve_ids,
            min_priority_score=0.2,  # Lower threshold for CVE-specific
        )

    def _generate_hypotheses(
        self,
        language: str,
        max_hypotheses: int,
        categories: Optional[List[str]],
        target_cves: Optional[List[str]],
    ) -> List[SecurityHypothesis]:
        """Generate hypotheses including CVE-specific ones."""
        hypotheses = []

        # Generate general hypotheses
        general = self.generator.generate_hypotheses(
            language=language,
            max_hypotheses=max_hypotheses,
            categories=categories,
        )
        hypotheses.extend(general)

        # Add CVE-specific hypotheses
        if target_cves:
            for cve_id in target_cves:
                cve_hypos = self.generator.generate_for_cve(cve_id, language)
                hypotheses.extend(cve_hypos)

        return hypotheses

    def _compute_codebase_stats(self) -> CodebaseStats:
        """Compute codebase statistics from CPG database."""
        from .multi_criteria_scorer import compute_codebase_stats_from_duckdb

        try:
            return compute_codebase_stats_from_duckdb(self.db_path)
        except Exception as e:
            logger.warning(f"Could not compute codebase stats: {e}")
            return CodebaseStats()

    def _compile_metrics(
        self,
        results: ValidationResults,
        validated: List[SecurityHypothesis],
        target_cves: Optional[List[str]],
    ) -> None:
        """Compile validation metrics from results."""
        # Count by status
        for h in validated:
            if h.validation_status == ValidationStatus.CONFIRMED:
                results.confirmed_hypotheses += 1
                results.true_positives += 1  # Assume confirmed = TP
            elif h.validation_status == ValidationStatus.REJECTED:
                results.rejected_hypotheses += 1
            else:
                results.inconclusive_hypotheses += 1

        # Check CVE detection
        if target_cves:
            found_cves: Set[str] = set()
            for h in validated:
                if h.validation_status == ValidationStatus.CONFIRMED:
                    for tag in h.tags:
                        if tag.startswith("CVE-") and tag in target_cves:
                            found_cves.add(tag)

            results.cves_found = list(found_cves)
            results.cves_missed = [
                cve for cve in target_cves if cve not in found_cves
            ]

            # Adjust false negatives based on missed CVEs
            results.false_negatives = len(results.cves_missed)


def validate_postgresql_security(
    db_path: str,
    include_known_cves: bool = True,
) -> ValidationResults:
    """Convenience function for PostgreSQL security validation.

    Args:
        db_path: Path to PostgreSQL CPG in DuckDB
        include_known_cves: Include CVE-2025-8713/8714/8715 patterns

    Returns:
        ValidationResults
    """
    validator = HypothesisValidator(db_path)

    target_cves = None
    if include_known_cves:
        target_cves = ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]

    return validator.run_validation(
        language="C",
        max_hypotheses=50,
        categories=[
            "buffer_overflow",
            "command_injection",
            "pg_dump_injection",
            "spi_sql_injection",
            "statistics_disclosure",
            "information_disclosure",
        ],
        target_cves=target_cves,
    )


def generate_validation_report(
    results: ValidationResults,
    hypotheses: List[SecurityHypothesis],
) -> str:
    """Generate a markdown report from validation results.

    Args:
        results: Validation results
        hypotheses: Validated hypotheses

    Returns:
        Markdown report string
    """
    report = []
    report.append("# Security Hypothesis Validation Report\n")
    report.append(f"**Batch ID**: {results.batch_id}")
    report.append(f"**Generated**: {results.started_at.isoformat()}")
    report.append(f"**Completed**: {results.completed_at.isoformat() if results.completed_at else 'N/A'}\n")

    # Summary metrics
    report.append("## Summary\n")
    report.append(f"- Total Hypotheses: {results.total_hypotheses}")
    report.append(f"- Queries Executed: {results.executed_queries}")
    report.append(f"- Confirmed: {results.confirmed_hypotheses}")
    report.append(f"- Rejected: {results.rejected_hypotheses}")
    report.append(f"- Inconclusive: {results.inconclusive_hypotheses}\n")

    # CVE Detection (if applicable)
    if results.cves_found or results.cves_missed:
        report.append("## CVE Detection\n")
        report.append(f"- Detection Rate: {results.detection_rate:.1%}")
        report.append(f"- Found: {', '.join(results.cves_found) or 'None'}")
        report.append(f"- Missed: {', '.join(results.cves_missed) or 'None'}\n")

    # Performance metrics
    report.append("## Performance\n")
    report.append(f"- Generation Time: {results.generation_time_sec:.2f}s")
    report.append(f"- Execution Time: {results.execution_time_sec:.2f}s")
    report.append(f"- Total Time: {results.total_time_sec:.2f}s\n")

    # Quality metrics
    report.append("## Quality Metrics\n")
    report.append(f"- Precision: {results.precision:.1%}")
    report.append(f"- Recall: {results.recall:.1%}")
    report.append(f"- F1 Score: {results.f1_score:.2f}")
    report.append(f"- Hypothesis Accuracy: {results.hypothesis_accuracy:.1%}\n")

    # Confirmed findings
    confirmed = [h for h in hypotheses if h.validation_status == ValidationStatus.CONFIRMED]
    if confirmed:
        report.append("## Confirmed Findings\n")
        for i, h in enumerate(confirmed[:10], 1):
            report.append(f"### {i}. {h.category} ({', '.join(h.cwe_ids[:2])})\n")
            report.append(f"**Priority**: {h.priority_score:.2f}")
            report.append(f"**Hypothesis**: {h.hypothesis_text[:200]}...\n")

            if h.evidence:
                ev = h.evidence[0]
                report.append(f"**Evidence**:")
                report.append(f"- File: {ev.filename or 'N/A'}")
                report.append(f"- Line: {ev.line_number or 'N/A'}")
                report.append(f"- Matches: {ev.result_count}\n")

    return "\n".join(report)
