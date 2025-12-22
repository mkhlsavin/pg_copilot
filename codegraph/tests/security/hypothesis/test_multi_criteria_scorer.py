"""
Tests for Multi-Criteria Scorer.

Tests for:
- CodebaseStats dataclass
- MultiCriteriaScorer initialization
- score_hypothesis method
- score_batch method
- Scoring component methods
- Bonus application
- compute_codebase_stats_from_duckdb function
"""

import pytest
from unittest.mock import MagicMock, patch

from src.security.hypothesis.models import (
    SecurityHypothesis,
    Severity,
    ValidationStatus,
)
from src.security.hypothesis.multi_criteria_scorer import (
    CodebaseStats,
    MultiCriteriaScorer,
    compute_codebase_stats_from_duckdb,
)
from src.security.hypothesis.knowledge_base import SecurityKnowledgeBase


# =============================================================================
# CodebaseStats Tests
# =============================================================================

class TestCodebaseStats:
    """Tests for CodebaseStats dataclass."""

    def test_codebase_stats_defaults(self):
        """Test CodebaseStats has correct defaults."""
        stats = CodebaseStats()
        assert stats.total_methods == 0
        assert stats.total_calls == 0
        assert stats.sink_counts == {}
        assert stats.source_counts == {}
        assert stats.sanitizer_counts == {}
        assert stats.taint_paths == 0
        assert stats.files_with_sinks == set()
        assert stats.files_with_sources == set()

    def test_total_sinks_property(self):
        """Test total_sinks property aggregates counts."""
        stats = CodebaseStats(
            sink_counts={"strcpy": 10, "memcpy": 5, "sprintf": 3}
        )
        assert stats.total_sinks == 18

    def test_total_sinks_empty(self):
        """Test total_sinks returns 0 when empty."""
        stats = CodebaseStats()
        assert stats.total_sinks == 0

    def test_total_sources_property(self):
        """Test total_sources property aggregates counts."""
        stats = CodebaseStats(
            source_counts={"recv": 8, "getenv": 12}
        )
        assert stats.total_sources == 20

    def test_total_sources_empty(self):
        """Test total_sources returns 0 when empty."""
        stats = CodebaseStats()
        assert stats.total_sources == 0

    def test_total_sanitizers_property(self):
        """Test total_sanitizers property aggregates counts."""
        stats = CodebaseStats(
            sanitizer_counts={"strlcpy": 25, "snprintf": 50}
        )
        assert stats.total_sanitizers == 75

    def test_total_sanitizers_empty(self):
        """Test total_sanitizers returns 0 when empty."""
        stats = CodebaseStats()
        assert stats.total_sanitizers == 0

    def test_codebase_stats_with_files(self):
        """Test CodebaseStats with file sets."""
        stats = CodebaseStats(
            files_with_sinks={"utils.c", "parser.c"},
            files_with_sources={"network.c"},
        )
        assert len(stats.files_with_sinks) == 2
        assert len(stats.files_with_sources) == 1


# =============================================================================
# MultiCriteriaScorer Initialization Tests
# =============================================================================

class TestMultiCriteriaScorerInit:
    """Tests for MultiCriteriaScorer initialization."""

    def test_init_defaults(self):
        """Test scorer initializes with defaults."""
        scorer = MultiCriteriaScorer()
        assert scorer.kb is not None
        assert scorer.weights == MultiCriteriaScorer.DEFAULT_WEIGHTS
        assert scorer.codebase_stats is not None

    def test_init_custom_knowledge_base(self, mock_knowledge_base):
        """Test scorer accepts custom knowledge base."""
        scorer = MultiCriteriaScorer(knowledge_base=mock_knowledge_base)
        assert scorer.kb is mock_knowledge_base

    def test_init_custom_weights(self):
        """Test scorer accepts custom weights."""
        custom_weights = {
            'cwe_frequency': 0.5,
            'attack_similarity': 0.3,
            'codebase_exposure': 0.2,
        }
        scorer = MultiCriteriaScorer(weights=custom_weights)
        assert scorer.weights == custom_weights

    def test_init_invalid_weights_raises_error(self):
        """Test scorer raises error for invalid weights."""
        invalid_weights = {
            'cwe_frequency': 0.5,
            'attack_similarity': 0.3,
            'codebase_exposure': 0.3,  # Sum = 1.1
        }
        with pytest.raises(ValueError, match="must sum to 1.0"):
            MultiCriteriaScorer(weights=invalid_weights)

    def test_init_custom_codebase_stats(self):
        """Test scorer accepts custom codebase stats."""
        stats = CodebaseStats(total_methods=1000)
        scorer = MultiCriteriaScorer(codebase_stats=stats)
        assert scorer.codebase_stats.total_methods == 1000

    def test_default_weights_sum_to_one(self):
        """Test default weights sum to 1.0."""
        total = sum(MultiCriteriaScorer.DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


# =============================================================================
# score_hypothesis Tests
# =============================================================================

class TestScoreHypothesis:
    """Tests for score_hypothesis method."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return MultiCriteriaScorer()

    def test_score_hypothesis_returns_float(self, scorer, sample_hypothesis):
        """Test score_hypothesis returns a float."""
        score = scorer.score_hypothesis(sample_hypothesis)
        assert isinstance(score, float)

    def test_score_hypothesis_in_range(self, scorer, sample_hypothesis):
        """Test score is in reasonable range."""
        score = scorer.score_hypothesis(sample_hypothesis)
        # May exceed 1.0 with bonuses, but should be positive
        assert score >= 0.0
        assert score < 3.0  # Reasonable upper bound

    def test_score_hypothesis_updates_hypothesis(self, scorer, sample_hypothesis):
        """Test scoring updates hypothesis fields."""
        scorer.score_hypothesis(sample_hypothesis)
        assert sample_hypothesis.priority_score >= 0.0
        assert sample_hypothesis.cwe_frequency_score >= 0.0
        assert sample_hypothesis.attack_similarity_score >= 0.0
        assert sample_hypothesis.codebase_exposure_score >= 0.0

    def test_score_hypothesis_with_no_cwes(self, scorer):
        """Test scoring hypothesis with no CWEs."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=[],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        score = scorer.score_hypothesis(hyp)
        # CWE frequency should be 0
        assert hyp.cwe_frequency_score == 0.0

    def test_score_hypothesis_with_no_capecs(self, scorer):
        """Test scoring hypothesis with no CAPECs."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        score = scorer.score_hypothesis(hyp)
        # Attack similarity should be default 0.5
        assert hyp.attack_similarity_score == 0.5

    def test_higher_risk_cwe_scores_higher(self, scorer):
        """Test hypotheses with higher risk CWEs score higher."""
        # Critical CWE
        hyp_critical = SecurityHypothesis(
            id="critical",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],  # Critical
            capec_ids=["CAPEC-100"],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        # Low severity CWE
        hyp_low = SecurityHypothesis(
            id="low",
            hypothesis_text="Test",
            cwe_ids=["CWE-476"],  # Medium
            capec_ids=[],
            language="C",
            category="null_pointer",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        scorer.score_hypothesis(hyp_critical)
        scorer.score_hypothesis(hyp_low)
        assert hyp_critical.cwe_frequency_score >= hyp_low.cwe_frequency_score


# =============================================================================
# score_batch Tests
# =============================================================================

class TestScoreBatch:
    """Tests for score_batch method."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return MultiCriteriaScorer()

    def test_score_batch_returns_list(self, scorer, sample_hypothesis):
        """Test score_batch returns a list."""
        result = scorer.score_batch([sample_hypothesis])
        assert isinstance(result, list)

    def test_score_batch_returns_same_hypotheses(self, scorer, sample_hypothesis):
        """Test score_batch returns the same hypothesis objects."""
        result = scorer.score_batch([sample_hypothesis])
        assert result[0] is sample_hypothesis

    def test_score_batch_sorted_by_priority(self, scorer):
        """Test batch is sorted by priority descending."""
        hyp1 = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-476"],  # Lower priority
            capec_ids=[],
            language="C",
            category="null_pointer",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        hyp2 = SecurityHypothesis(
            id="2",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],  # Higher priority
            capec_ids=["CAPEC-100"],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        result = scorer.score_batch([hyp1, hyp2])
        assert result[0].priority_score >= result[1].priority_score


# =============================================================================
# Scoring Component Tests
# =============================================================================

class TestScoringComponents:
    """Tests for individual scoring component methods."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return MultiCriteriaScorer()

    def test_score_cwe_frequency_with_valid_cwe(self, scorer):
        """Test _score_cwe_frequency with valid CWE."""
        score = scorer._score_cwe_frequency(["CWE-120"])
        assert score > 0.0
        assert score <= 1.0

    def test_score_cwe_frequency_empty_list(self, scorer):
        """Test _score_cwe_frequency with empty list."""
        score = scorer._score_cwe_frequency([])
        assert score == 0.0

    def test_score_cwe_frequency_unknown_cwe(self, scorer):
        """Test _score_cwe_frequency with unknown CWE."""
        score = scorer._score_cwe_frequency(["CWE-99999"])
        assert score == 0.0

    def test_score_cwe_frequency_multiple_cwes(self, scorer):
        """Test _score_cwe_frequency takes max of multiple CWEs."""
        score_single = scorer._score_cwe_frequency(["CWE-476"])
        score_multiple = scorer._score_cwe_frequency(["CWE-476", "CWE-120"])
        # CWE-120 is more critical, so multiple should be >= single
        assert score_multiple >= score_single

    def test_score_attack_similarity_with_valid_capec(self, scorer):
        """Test _score_attack_similarity with valid CAPEC."""
        score = scorer._score_attack_similarity(["CAPEC-100"])
        assert score > 0.0
        assert score <= 1.0

    def test_score_attack_similarity_empty_list(self, scorer):
        """Test _score_attack_similarity with empty list returns default."""
        score = scorer._score_attack_similarity([])
        assert score == 0.5  # Default moderate score

    def test_score_attack_similarity_unknown_capec(self, scorer):
        """Test _score_attack_similarity with unknown CAPEC."""
        score = scorer._score_attack_similarity(["CAPEC-99999"])
        assert score == 0.5  # Falls back to default

    def test_score_attack_similarity_skill_adjustment(self, scorer):
        """Test attack similarity considers skill level."""
        # CAPEC-88 is Low skill, CAPEC-135 is High skill
        score_low = scorer._score_attack_similarity(["CAPEC-88"])
        score_high = scorer._score_attack_similarity(["CAPEC-135"])
        # Low skill should score higher (easier to exploit)
        assert score_low >= score_high

    def test_score_codebase_exposure_no_stats(self, scorer):
        """Test _score_codebase_exposure returns 0.5 with no stats."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        score = scorer._score_codebase_exposure(hyp)
        assert score == 0.5

    def test_score_codebase_exposure_with_stats(self):
        """Test _score_codebase_exposure with codebase stats."""
        stats = CodebaseStats(
            total_methods=1000,
            sink_counts={"strcpy": 50},
            source_counts={"getenv": 30},
            sanitizer_counts={},
        )
        scorer = MultiCriteriaScorer(codebase_stats=stats)
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        score = scorer._score_codebase_exposure(hyp)
        # Should be higher than default since sinks/sources present
        assert score > 0.0

    def test_score_codebase_exposure_sanitizers_reduce_score(self):
        """Test sanitizers reduce exposure score."""
        stats = CodebaseStats(
            total_methods=1000,
            sink_counts={"strcpy": 50},
            source_counts={"getenv": 30},
            sanitizer_counts={"strlcpy": 100},  # High sanitizer count
        )
        scorer = MultiCriteriaScorer(codebase_stats=stats)
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=["strlcpy"],
        )
        score_with_sanitizer = scorer._score_codebase_exposure(hyp)

        hyp2 = SecurityHypothesis(
            id="test2",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        score_without = scorer._score_codebase_exposure(hyp2)

        assert score_with_sanitizer <= score_without


# =============================================================================
# Bonus Application Tests
# =============================================================================

class TestBonusApplication:
    """Tests for bonus multiplier application."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return MultiCriteriaScorer()

    def test_bonus_for_known_cve_pattern(self, scorer):
        """Test bonus applied for known CVE patterns."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",  # Known CVE pattern
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        assert scorer._matches_known_cve_pattern(hyp) is True

    def test_bonus_for_cve_tag(self, scorer):
        """Test bonus applied when hypothesis has CVE tag."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="unknown",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
            tags=["CVE-2025-8714"],
        )
        assert scorer._matches_known_cve_pattern(hyp) is True

    def test_no_bonus_for_unknown_pattern(self, scorer):
        """Test no bonus for unknown patterns."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="unknown_category",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
            tags=[],
        )
        assert scorer._matches_known_cve_pattern(hyp) is False

    def test_bonus_for_critical_severity(self, scorer):
        """Test _has_critical_severity detects critical CWEs."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],  # Critical severity
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        assert scorer._has_critical_severity(hyp) is True

    def test_no_bonus_for_non_critical_severity(self, scorer):
        """Test _has_critical_severity returns False for non-critical."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-476"],  # Medium severity
            capec_ids=[],
            language="C",
            category="null_pointer",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        assert scorer._has_critical_severity(hyp) is False

    def test_apply_bonuses_accumulates(self, scorer):
        """Test bonuses accumulate multiplicatively."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],  # Critical
            capec_ids=["CAPEC-100"],
            language="C",
            category="buffer_overflow",  # Known CVE pattern
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
            tags=["cve-targeted"],  # Recent exploit bonus
        )
        base_score = 0.5
        final_score = scorer._apply_bonuses(base_score, hyp)
        # Should have BONUS_KNOWN_CVE * BONUS_CRITICAL_SEVERITY * BONUS_RECENT_EXPLOIT
        expected_min = base_score * 1.2 * 1.1 * 1.15
        assert final_score >= expected_min * 0.99  # Allow small floating point error


# =============================================================================
# update_codebase_stats Tests
# =============================================================================

class TestUpdateCodebaseStats:
    """Tests for update_codebase_stats method."""

    def test_update_codebase_stats(self):
        """Test updating codebase stats."""
        scorer = MultiCriteriaScorer()
        new_stats = CodebaseStats(total_methods=5000)
        scorer.update_codebase_stats(new_stats)
        assert scorer.codebase_stats.total_methods == 5000


# =============================================================================
# compute_codebase_stats_from_duckdb Tests
# =============================================================================

class TestComputeCodebaseStatsFromDuckDB:
    """Tests for compute_codebase_stats_from_duckdb function."""

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_returns_codebase_stats(self):
        """Test function returns CodebaseStats."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (0,)
        mock_duckdb.connect.return_value = mock_conn

        stats = compute_codebase_stats_from_duckdb("test.db")
        assert isinstance(stats, CodebaseStats)

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_handles_missing_database(self):
        """Test function handles missing database gracefully."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        # Simulate connection error for missing database
        mock_duckdb.connect.side_effect = Exception("Database not found")

        # Use a path that definitely doesn't exist
        stats = compute_codebase_stats_from_duckdb("/nonexistent/path/to/db.duckdb")
        # Should return empty stats, not raise
        assert isinstance(stats, CodebaseStats)
        assert stats.total_methods == 0

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_computes_method_count(self):
        """Test function computes method count."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (500,)
        mock_duckdb.connect.return_value = mock_conn

        stats = compute_codebase_stats_from_duckdb("test.db")
        assert stats.total_methods == 500
