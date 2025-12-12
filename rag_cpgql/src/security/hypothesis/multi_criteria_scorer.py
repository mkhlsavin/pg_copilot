"""
Multi-Criteria Scorer for Hypothesis Prioritization.

Implements the scoring formula:
    Priority Score = (CWE_Frequency × 0.40) + (Attack_Similarity × 0.30) + (Codebase_Exposure × 0.30)

With bonus adjustments for:
- Known CVE patterns
- Critical severity
- Recently exploited patterns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .models import SecurityHypothesis, CWEEntry, CAPECPattern
from .knowledge_base import SecurityKnowledgeBase, get_knowledge_base


@dataclass
class CodebaseStats:
    """Statistics about the codebase for exposure scoring.

    These statistics are typically gathered from the CPG database
    via DuckDB queries before scoring.
    """
    # Function counts
    total_methods: int = 0
    total_calls: int = 0

    # Sink/Source presence
    sink_counts: Dict[str, int] = field(default_factory=dict)  # sink_name -> count
    source_counts: Dict[str, int] = field(default_factory=dict)  # source_name -> count
    sanitizer_counts: Dict[str, int] = field(default_factory=dict)  # sanitizer_name -> count

    # Taint flow stats (if available)
    taint_paths: int = 0  # Number of source->sink paths

    # Files with dangerous patterns
    files_with_sinks: Set[str] = field(default_factory=set)
    files_with_sources: Set[str] = field(default_factory=set)

    @property
    def total_sinks(self) -> int:
        """Total count of all sink occurrences."""
        return sum(self.sink_counts.values())

    @property
    def total_sources(self) -> int:
        """Total count of all source occurrences."""
        return sum(self.source_counts.values())

    @property
    def total_sanitizers(self) -> int:
        """Total count of all sanitizer occurrences."""
        return sum(self.sanitizer_counts.values())


class MultiCriteriaScorer:
    """Scores hypotheses using multi-criteria analysis.

    Scoring Formula:
        Priority = (CWE_Freq × 0.40) + (Attack_Sim × 0.30) + (Exposure × 0.30)

    Each component is normalized to [0.0, 1.0] range.
    """

    # Default weights (can be customized)
    DEFAULT_WEIGHTS = {
        'cwe_frequency': 0.40,      # How common is this CWE in CVE database?
        'attack_similarity': 0.30,  # How similar to known attacks?
        'codebase_exposure': 0.30,  # How exposed is the codebase to this?
    }

    # Bonus multipliers
    BONUS_KNOWN_CVE = 1.2          # 20% bonus for matching known CVE patterns
    BONUS_CRITICAL_SEVERITY = 1.1  # 10% bonus for critical severity
    BONUS_RECENT_EXPLOIT = 1.15    # 15% bonus for recently exploited

    # Known CVE patterns for bonus scoring
    KNOWN_CVE_PATTERNS = {
        # CVE-2025-8713, CVE-2025-8714, CVE-2025-8715 patterns
        "pg_dump_injection": ["CVE-2025-8714", "CVE-2025-8715"],
        "statistics_disclosure": ["CVE-2025-8713"],
        # Historical PostgreSQL CVEs
        "buffer_overflow": ["CVE-2023-5868", "CVE-2022-41862"],
        "sql_injection": ["CVE-2023-39417"],
    }

    def __init__(
        self,
        knowledge_base: Optional[SecurityKnowledgeBase] = None,
        weights: Optional[Dict[str, float]] = None,
        codebase_stats: Optional[CodebaseStats] = None,
    ):
        """Initialize scorer.

        Args:
            knowledge_base: Security knowledge base
            weights: Custom scoring weights (must sum to 1.0)
            codebase_stats: Pre-computed codebase statistics
        """
        self.kb = knowledge_base or get_knowledge_base()
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.codebase_stats = codebase_stats or CodebaseStats()

        # Validate weights
        weight_sum = sum(self.weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

    def score_hypothesis(self, hypothesis: SecurityHypothesis) -> float:
        """Calculate priority score for a hypothesis.

        Args:
            hypothesis: The hypothesis to score

        Returns:
            Priority score in range [0.0, 1.0] (may exceed 1.0 with bonuses)
        """
        # Calculate component scores
        cwe_score = self._score_cwe_frequency(hypothesis.cwe_ids)
        attack_score = self._score_attack_similarity(hypothesis.capec_ids)
        exposure_score = self._score_codebase_exposure(hypothesis)

        # Store component scores in hypothesis
        hypothesis.cwe_frequency_score = cwe_score
        hypothesis.attack_similarity_score = attack_score
        hypothesis.codebase_exposure_score = exposure_score

        # Calculate weighted base score
        base_score = (
            cwe_score * self.weights['cwe_frequency'] +
            attack_score * self.weights['attack_similarity'] +
            exposure_score * self.weights['codebase_exposure']
        )

        # Apply bonuses
        final_score = self._apply_bonuses(base_score, hypothesis)

        # Update hypothesis
        hypothesis.priority_score = final_score

        return final_score

    def score_batch(
        self,
        hypotheses: List[SecurityHypothesis],
    ) -> List[SecurityHypothesis]:
        """Score a batch of hypotheses and return sorted by priority.

        Args:
            hypotheses: List of hypotheses to score

        Returns:
            Same list, sorted by priority_score descending
        """
        for h in hypotheses:
            self.score_hypothesis(h)

        return sorted(hypotheses, key=lambda h: h.priority_score, reverse=True)

    def update_codebase_stats(self, stats: CodebaseStats) -> None:
        """Update codebase statistics for exposure scoring.

        Args:
            stats: New codebase statistics
        """
        self.codebase_stats = stats

    def _score_cwe_frequency(self, cwe_ids: List[str]) -> float:
        """Calculate CWE frequency score.

        Based on:
        - CWE prevalence in CVE database
        - CWE exploitability score
        - CVSS base score

        Returns highest score among all CWEs.
        """
        if not cwe_ids:
            return 0.0

        scores = []
        for cwe_id in cwe_ids:
            cwe = self.kb.get_cwe(cwe_id)
            if cwe:
                # Combine prevalence, exploitability, and CVSS
                score = (
                    cwe.prevalence * 0.4 +
                    cwe.exploitability * 0.4 +
                    (cwe.cvss_base / 10.0) * 0.2
                )
                scores.append(score)

        return max(scores) if scores else 0.0

    def _score_attack_similarity(self, capec_ids: List[str]) -> float:
        """Calculate attack similarity score.

        Based on:
        - Attack pattern likelihood
        - Required skill level
        - Historical exploitation

        Returns average score across attack patterns.
        """
        if not capec_ids:
            return 0.5  # Default moderate score

        scores = []
        for capec_id in capec_ids:
            capec = self.kb.get_capec(capec_id)
            if capec:
                # Likelihood score
                likelihood_score = capec.likelihood

                # Skill level adjustment (lower skill = higher score)
                skill_adjustment = {
                    "Low": 1.0,
                    "Medium": 0.8,
                    "High": 0.6,
                    "Expert": 0.4,
                }.get(capec.skill_level, 0.7)

                score = likelihood_score * skill_adjustment
                scores.append(score)

        return sum(scores) / len(scores) if scores else 0.5

    def _score_codebase_exposure(self, hypothesis: SecurityHypothesis) -> float:
        """Calculate codebase exposure score.

        Based on:
        - Presence of sink functions
        - Presence of source functions
        - Absence of sanitizers
        - Number of potential taint paths

        Higher score = more exposed codebase.
        """
        if self.codebase_stats.total_methods == 0:
            # No codebase stats available, return moderate score
            return 0.5

        # Calculate sink exposure
        sink_exposure = 0.0
        for sink in hypothesis.sink_patterns:
            count = self.codebase_stats.sink_counts.get(sink, 0)
            sink_exposure += min(count / 100.0, 1.0)  # Normalize
        sink_exposure = min(sink_exposure / max(len(hypothesis.sink_patterns), 1), 1.0)

        # Calculate source exposure
        source_exposure = 0.0
        for source in hypothesis.source_patterns:
            count = self.codebase_stats.source_counts.get(source, 0)
            source_exposure += min(count / 100.0, 1.0)
        source_exposure = min(source_exposure / max(len(hypothesis.source_patterns), 1), 1.0)

        # Calculate sanitizer coverage (inverted - more sanitizers = lower exposure)
        sanitizer_coverage = 0.0
        for sanitizer in hypothesis.sanitizer_patterns:
            count = self.codebase_stats.sanitizer_counts.get(sanitizer, 0)
            sanitizer_coverage += min(count / 50.0, 1.0)
        if hypothesis.sanitizer_patterns:
            sanitizer_coverage = sanitizer_coverage / len(hypothesis.sanitizer_patterns)

        # Exposure score: high sinks + high sources - sanitizers
        exposure = (sink_exposure * 0.4 + source_exposure * 0.4) * (1.0 - sanitizer_coverage * 0.5)

        # Boost if taint paths exist
        if self.codebase_stats.taint_paths > 0:
            path_boost = min(self.codebase_stats.taint_paths / 100.0, 0.2)
            exposure += path_boost

        return min(exposure, 1.0)

    def _apply_bonuses(
        self,
        base_score: float,
        hypothesis: SecurityHypothesis,
    ) -> float:
        """Apply bonus multipliers to base score."""
        score = base_score

        # Bonus for matching known CVE patterns
        if self._matches_known_cve_pattern(hypothesis):
            score *= self.BONUS_KNOWN_CVE

        # Bonus for critical severity CWEs
        if self._has_critical_severity(hypothesis):
            score *= self.BONUS_CRITICAL_SEVERITY

        # Bonus for CVE-targeted hypotheses
        if "cve-targeted" in hypothesis.tags:
            score *= self.BONUS_RECENT_EXPLOIT

        return score

    def _matches_known_cve_pattern(self, hypothesis: SecurityHypothesis) -> bool:
        """Check if hypothesis matches known CVE patterns."""
        category = hypothesis.category
        if category in self.KNOWN_CVE_PATTERNS:
            return True

        # Check tags for CVE IDs
        for tag in hypothesis.tags:
            if tag.startswith("CVE-"):
                return True

        return False

    def _has_critical_severity(self, hypothesis: SecurityHypothesis) -> bool:
        """Check if any CWE has critical severity."""
        from .models import Severity

        for cwe_id in hypothesis.cwe_ids:
            cwe = self.kb.get_cwe(cwe_id)
            if cwe and cwe.severity == Severity.CRITICAL:
                return True
        return False


def compute_codebase_stats_from_duckdb(db_path: str) -> CodebaseStats:
    """Compute codebase statistics from DuckDB CPG database.

    Args:
        db_path: Path to DuckDB database file

    Returns:
        CodebaseStats with computed values
    """
    import duckdb

    stats = CodebaseStats()

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Total methods
        result = conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()
        stats.total_methods = result[0] if result else 0

        # Total calls
        result = conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()
        stats.total_calls = result[0] if result else 0

        # Count dangerous sinks
        dangerous_sinks = [
            "strcpy", "strcat", "sprintf", "gets", "memcpy",
            "system", "popen", "execl", "execv",
            "printf", "fprintf",
            "appendPQExpBuffer", "SPI_execute", "PQexec",
        ]
        for sink in dangerous_sinks:
            result = conn.execute(
                "SELECT COUNT(*) FROM nodes_call WHERE name = ?",
                [sink]
            ).fetchone()
            if result and result[0] > 0:
                stats.sink_counts[sink] = result[0]

        # Count sources
        sources = [
            "recv", "read", "fgets", "getenv",
            "PQgetvalue", "SPI_getvalue", "getTables",
        ]
        for source in sources:
            result = conn.execute(
                "SELECT COUNT(*) FROM nodes_call WHERE name = ?",
                [source]
            ).fetchone()
            if result and result[0] > 0:
                stats.source_counts[source] = result[0]

        # Count sanitizers
        sanitizers = [
            "strlcpy", "snprintf", "fmtId", "quote_identifier",
            "quote_literal", "pg_class_aclcheck",
        ]
        for san in sanitizers:
            result = conn.execute(
                "SELECT COUNT(*) FROM nodes_call WHERE name = ?",
                [san]
            ).fetchone()
            if result and result[0] > 0:
                stats.sanitizer_counts[san] = result[0]

        conn.close()

    except Exception as e:
        # Return empty stats on error
        pass

    return stats
