"""
Tests for hypothesis generation data models.

Tests for:
- Severity enum
- ValidationStatus enum
- EvaluationStrategy enum
- CWEEntry dataclass
- CAPECPattern dataclass
- LanguagePattern dataclass
- Evidence dataclass
- SecurityHypothesis dataclass
- HypothesisBatch dataclass
- ValidationResults dataclass
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.security.hypothesis.models import (
    Severity,
    ValidationStatus,
    EvaluationStrategy,
    CWEEntry,
    CAPECPattern,
    LanguagePattern,
    Evidence,
    SecurityHypothesis,
    HypothesisBatch,
    ValidationResults,
)


# =============================================================================
# Severity Enum Tests
# =============================================================================

class TestSeverityEnum:
    """Tests for Severity enumeration."""

    def test_severity_values(self):
        """Test all severity values exist."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_severity_count(self):
        """Test total number of severity levels."""
        assert len(Severity) == 5

    def test_severity_is_str_enum(self):
        """Test Severity is a string enum."""
        assert isinstance(Severity.CRITICAL, str)
        assert Severity.CRITICAL.value == "critical"

    def test_severity_comparison(self):
        """Test severity string comparison."""
        assert Severity.CRITICAL == "critical"
        assert Severity.HIGH == "high"

    def test_severity_from_string(self):
        """Test creating severity from string."""
        assert Severity("critical") == Severity.CRITICAL
        assert Severity("high") == Severity.HIGH


# =============================================================================
# ValidationStatus Enum Tests
# =============================================================================

class TestValidationStatusEnum:
    """Tests for ValidationStatus enumeration."""

    def test_validation_status_values(self):
        """Test all validation status values."""
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.IN_PROGRESS.value == "in_progress"
        assert ValidationStatus.CONFIRMED.value == "confirmed"
        assert ValidationStatus.REJECTED.value == "rejected"
        assert ValidationStatus.INCONCLUSIVE.value == "inconclusive"

    def test_validation_status_count(self):
        """Test total number of validation statuses."""
        assert len(ValidationStatus) == 5

    def test_validation_status_is_str_enum(self):
        """Test ValidationStatus is a string enum."""
        assert isinstance(ValidationStatus.PENDING, str)
        assert ValidationStatus.PENDING.value == "pending"


# =============================================================================
# EvaluationStrategy Enum Tests
# =============================================================================

class TestEvaluationStrategyEnum:
    """Tests for EvaluationStrategy enumeration."""

    def test_evaluation_strategy_values(self):
        """Test all evaluation strategy values."""
        assert EvaluationStrategy.BY_VALUE.value == "BY_VALUE"
        assert EvaluationStrategy.BY_REFERENCE.value == "BY_REFERENCE"
        assert EvaluationStrategy.BY_SHARING.value == "BY_SHARING"

    def test_evaluation_strategy_count(self):
        """Test total number of evaluation strategies."""
        assert len(EvaluationStrategy) == 3


# =============================================================================
# CWEEntry Tests
# =============================================================================

class TestCWEEntry:
    """Tests for CWEEntry dataclass."""

    def test_cwe_entry_creation(self, sample_cwe_entry):
        """Test creating a CWE entry."""
        assert sample_cwe_entry.id == "CWE-120"
        assert sample_cwe_entry.name == "Buffer Copy without Checking Size of Input"
        assert sample_cwe_entry.severity == Severity.CRITICAL
        assert sample_cwe_entry.cvss_base == 9.8
        assert "C" in sample_cwe_entry.languages
        assert sample_cwe_entry.prevalence == 0.85
        assert sample_cwe_entry.exploitability == 0.90

    def test_cwe_numeric_id(self, sample_cwe_entry):
        """Test numeric_id property extracts integer."""
        assert sample_cwe_entry.numeric_id == 120

    def test_cwe_numeric_id_various(self):
        """Test numeric_id with various CWE IDs."""
        cwe = CWEEntry(
            id="CWE-787",
            name="Test",
            description="Test",
            severity=Severity.HIGH,
            cvss_base=7.0,
            languages=["C"],
            prevalence=0.5,
            exploitability=0.5,
        )
        assert cwe.numeric_id == 787

    def test_cwe_risk_score(self, sample_cwe_entry):
        """Test risk_score calculation."""
        # risk = prevalence * exploitability * (cvss_base / 10)
        expected = 0.85 * 0.90 * (9.8 / 10.0)
        assert abs(sample_cwe_entry.risk_score - expected) < 0.001

    def test_cwe_risk_score_low(self, sample_cwe_entry_low):
        """Test risk_score for low severity CWE."""
        expected = 0.55 * 0.50 * (3.3 / 10.0)
        assert abs(sample_cwe_entry_low.risk_score - expected) < 0.001

    def test_cwe_related_cwes(self, sample_cwe_entry):
        """Test related CWEs list."""
        assert "CWE-119" in sample_cwe_entry.related_cwes
        assert "CWE-787" in sample_cwe_entry.related_cwes

    def test_cwe_capec_ids(self, sample_cwe_entry):
        """Test CAPEC IDs list."""
        assert "CAPEC-100" in sample_cwe_entry.capec_ids
        assert "CAPEC-123" in sample_cwe_entry.capec_ids

    def test_cwe_default_lists(self):
        """Test CWE entry with default empty lists."""
        cwe = CWEEntry(
            id="CWE-1",
            name="Test",
            description="Test",
            severity=Severity.LOW,
            cvss_base=1.0,
            languages=["C"],
            prevalence=0.1,
            exploitability=0.1,
        )
        assert cwe.related_cwes == []
        assert cwe.capec_ids == []
        assert cwe.mitigations == []
        assert cwe.detection_methods == []


# =============================================================================
# CAPECPattern Tests
# =============================================================================

class TestCAPECPattern:
    """Tests for CAPECPattern dataclass."""

    def test_capec_creation(self, sample_capec_pattern):
        """Test creating a CAPEC pattern."""
        assert sample_capec_pattern.id == "CAPEC-100"
        assert sample_capec_pattern.name == "Overflow Buffers"
        assert sample_capec_pattern.typical_severity == Severity.CRITICAL
        assert sample_capec_pattern.likelihood == 0.75
        assert sample_capec_pattern.skill_level == "Medium"

    def test_capec_numeric_id(self, sample_capec_pattern):
        """Test numeric_id property."""
        assert sample_capec_pattern.numeric_id == 100

    def test_capec_numeric_id_various(self):
        """Test numeric_id with various CAPEC IDs."""
        capec = CAPECPattern(
            id="CAPEC-242",
            name="Test",
            description="Test",
            related_cwes=["CWE-94"],
        )
        assert capec.numeric_id == 242

    def test_capec_related_cwes(self, sample_capec_pattern):
        """Test related CWEs in CAPEC."""
        assert "CWE-120" in sample_capec_pattern.related_cwes
        assert "CWE-119" in sample_capec_pattern.related_cwes

    def test_capec_attack_steps(self, sample_capec_pattern):
        """Test attack steps list."""
        assert len(sample_capec_pattern.attack_steps) == 4
        assert "Identify buffer input" in sample_capec_pattern.attack_steps

    def test_capec_prerequisites(self, sample_capec_pattern):
        """Test prerequisites list."""
        assert "Accessible buffer input" in sample_capec_pattern.prerequisites

    def test_capec_default_values(self):
        """Test CAPEC with default values."""
        capec = CAPECPattern(
            id="CAPEC-1",
            name="Test",
            description="Test",
            related_cwes=["CWE-1"],
        )
        assert capec.typical_severity == Severity.HIGH
        assert capec.likelihood == 0.5
        assert capec.skill_level == "Medium"
        assert capec.attack_steps == []
        assert capec.prerequisites == []


# =============================================================================
# LanguagePattern Tests
# =============================================================================

class TestLanguagePattern:
    """Tests for LanguagePattern dataclass."""

    def test_language_pattern_creation(self, sample_language_pattern):
        """Test creating a language pattern."""
        assert sample_language_pattern.language == "C"
        assert sample_language_pattern.category == "buffer_overflow"
        assert "strcpy" in sample_language_pattern.sinks
        assert "recv" in sample_language_pattern.sources
        assert "strlcpy" in sample_language_pattern.sanitizers

    def test_language_pattern_related_cwes(self, sample_language_pattern):
        """Test related CWEs in language pattern."""
        assert "CWE-120" in sample_language_pattern.related_cwes

    def test_language_pattern_examples(self, sample_language_pattern):
        """Test examples list."""
        assert len(sample_language_pattern.examples) > 0

    def test_language_pattern_defaults(self):
        """Test language pattern with defaults."""
        pattern = LanguagePattern(
            language="Python",
            category="injection",
            sinks=["eval"],
            sources=["input"],
            sanitizers=[],
            related_cwes=["CWE-94"],
        )
        assert pattern.description == ""
        assert pattern.examples == []


# =============================================================================
# Evidence Tests
# =============================================================================

class TestEvidence:
    """Tests for Evidence dataclass."""

    def test_evidence_creation(self, sample_evidence):
        """Test creating evidence."""
        assert sample_evidence.id == "ev-001"
        assert sample_evidence.hypothesis_id == "hyp-001"
        assert sample_evidence.result_count == 5
        assert sample_evidence.confidence == 0.85
        assert len(sample_evidence.findings) == 2

    def test_evidence_is_positive_true(self, sample_evidence):
        """Test is_positive returns True for positive evidence."""
        # result_count > 0 and confidence > 0.5
        assert sample_evidence.is_positive is True

    def test_evidence_is_positive_no_results(self, sample_evidence_negative):
        """Test is_positive returns False when no results."""
        assert sample_evidence_negative.result_count == 0
        assert sample_evidence_negative.is_positive is False

    def test_evidence_is_positive_low_confidence(self, sample_evidence_low_confidence):
        """Test is_positive returns False with low confidence."""
        # result_count > 0 but confidence <= 0.5
        assert sample_evidence_low_confidence.result_count > 0
        assert sample_evidence_low_confidence.confidence <= 0.5
        assert sample_evidence_low_confidence.is_positive is False

    def test_evidence_file_info(self, sample_evidence):
        """Test file information fields."""
        assert sample_evidence.filename == "utils.c"
        assert sample_evidence.line_number == 42
        assert "strcpy" in sample_evidence.code_snippet

    def test_evidence_timestamp(self, sample_evidence):
        """Test timestamp is set."""
        assert sample_evidence.timestamp is not None
        assert isinstance(sample_evidence.timestamp, datetime)

    def test_evidence_defaults(self):
        """Test evidence with default values."""
        evidence = Evidence(
            id="ev-test",
            hypothesis_id="hyp-test",
            query_executed="SELECT 1",
            result_count=0,
            findings=[],
        )
        assert evidence.filename is None
        assert evidence.line_number is None
        assert evidence.code_snippet is None
        assert evidence.confidence == 0.5
        assert evidence.notes == ""


# =============================================================================
# SecurityHypothesis Tests
# =============================================================================

class TestSecurityHypothesis:
    """Tests for SecurityHypothesis dataclass."""

    def test_hypothesis_creation(self, sample_hypothesis):
        """Test creating a hypothesis."""
        assert sample_hypothesis.id == "hyp-001"
        assert "strcpy" in sample_hypothesis.hypothesis_text
        assert "CWE-120" in sample_hypothesis.cwe_ids
        assert "CAPEC-100" in sample_hypothesis.capec_ids
        assert sample_hypothesis.language == "C"
        assert sample_hypothesis.category == "buffer_overflow"

    def test_hypothesis_patterns(self, sample_hypothesis):
        """Test source/sink/sanitizer patterns."""
        assert "recv" in sample_hypothesis.source_patterns
        assert "strcpy" in sample_hypothesis.sink_patterns
        assert "strlcpy" in sample_hypothesis.sanitizer_patterns

    def test_hypothesis_scoring(self, sample_hypothesis):
        """Test scoring fields."""
        assert sample_hypothesis.priority_score == 0.85
        assert sample_hypothesis.cwe_frequency_score == 0.9
        assert sample_hypothesis.attack_similarity_score == 0.8
        assert sample_hypothesis.codebase_exposure_score == 0.7

    def test_hypothesis_is_confirmed_true(self, sample_hypothesis_confirmed):
        """Test is_confirmed returns True for confirmed hypothesis."""
        assert sample_hypothesis_confirmed.is_confirmed is True

    def test_hypothesis_is_confirmed_false(self, sample_hypothesis):
        """Test is_confirmed returns False for pending hypothesis."""
        assert sample_hypothesis.validation_status == ValidationStatus.PENDING
        assert sample_hypothesis.is_confirmed is False

    def test_hypothesis_is_confirmed_rejected(self, sample_hypothesis_rejected):
        """Test is_confirmed returns False for rejected hypothesis."""
        assert sample_hypothesis_rejected.is_confirmed is False

    def test_hypothesis_has_evidence_true(self, sample_hypothesis_confirmed, sample_evidence):
        """Test has_evidence returns True with positive evidence."""
        assert sample_hypothesis_confirmed.has_evidence is True

    def test_hypothesis_has_evidence_false_empty(self, sample_hypothesis):
        """Test has_evidence returns False with no evidence."""
        assert len(sample_hypothesis.evidence) == 0
        assert sample_hypothesis.has_evidence is False

    def test_hypothesis_has_evidence_false_negative(self, sample_evidence_negative):
        """Test has_evidence returns False with only negative evidence."""
        hyp = SecurityHypothesis(
            id="hyp-test",
            hypothesis_text="Test hypothesis",
            cwe_ids=["CWE-120"],
            capec_ids=["CAPEC-100"],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        hyp.evidence = [sample_evidence_negative]
        assert hyp.has_evidence is False

    def test_hypothesis_add_evidence(self, sample_hypothesis, sample_evidence):
        """Test add_evidence method."""
        initial_confidence = sample_hypothesis.confidence
        sample_hypothesis.add_evidence(sample_evidence)

        assert len(sample_hypothesis.evidence) == 1
        assert sample_hypothesis.evidence[0] == sample_evidence
        # Confidence should increase for positive evidence
        assert sample_hypothesis.confidence > initial_confidence

    def test_hypothesis_add_evidence_increases_confidence(self, sample_hypothesis, sample_evidence):
        """Test that adding positive evidence increases confidence."""
        sample_hypothesis.confidence = 0.5
        sample_hypothesis.add_evidence(sample_evidence)
        # confidence += 0.1 * evidence.confidence = 0.1 * 0.85 = 0.085
        expected = 0.5 + 0.1 * sample_evidence.confidence
        assert abs(sample_hypothesis.confidence - expected) < 0.001

    def test_hypothesis_add_evidence_caps_at_one(self, sample_hypothesis, sample_evidence):
        """Test that confidence is capped at 1.0."""
        sample_hypothesis.confidence = 0.95
        sample_hypothesis.add_evidence(sample_evidence)
        assert sample_hypothesis.confidence <= 1.0

    def test_hypothesis_add_multiple_evidence(self, sample_hypothesis, sample_evidence):
        """Test adding multiple evidence items."""
        evidence2 = Evidence(
            id="ev-002",
            hypothesis_id="hyp-001",
            query_executed="SELECT 1",
            result_count=3,
            findings=[{"test": "data"}],
            confidence=0.7,
        )
        sample_hypothesis.add_evidence(sample_evidence)
        sample_hypothesis.add_evidence(evidence2)
        assert len(sample_hypothesis.evidence) == 2

    def test_hypothesis_tags(self, sample_hypothesis):
        """Test tags field."""
        assert "postgresql" in sample_hypothesis.tags
        assert "memory-safety" in sample_hypothesis.tags

    def test_hypothesis_defaults(self):
        """Test hypothesis with default values."""
        hyp = SecurityHypothesis(
            id="hyp-default",
            hypothesis_text="Test",
            cwe_ids=["CWE-1"],
            capec_ids=[],
            language="C",
            category="test",
            source_patterns=[],
            sink_patterns=[],
            sanitizer_patterns=[],
        )
        assert hyp.priority_score == 0.0
        assert hyp.confidence == 0.0
        assert hyp.sql_query is None
        assert hyp.evidence == []
        assert hyp.validation_status == ValidationStatus.PENDING
        assert hyp.validated_at is None
        assert hyp.tags == []
        assert hyp.notes == ""


# =============================================================================
# HypothesisBatch Tests
# =============================================================================

class TestHypothesisBatch:
    """Tests for HypothesisBatch dataclass."""

    def test_batch_creation(self, sample_batch):
        """Test creating a hypothesis batch."""
        assert sample_batch.id == "batch-001"
        assert sample_batch.name == "PostgreSQL 17.5 Security Audit"
        assert sample_batch.target_project == "postgresql-17.5"
        assert len(sample_batch.hypotheses) == 3

    def test_batch_total_count(self, sample_batch):
        """Test total_count property."""
        assert sample_batch.total_count == 3

    def test_batch_confirmed_count(self, sample_batch):
        """Test confirmed_count property."""
        # Only sample_hypothesis is not rejected/pending but also not confirmed
        # We need to check the actual statuses
        confirmed = sum(1 for h in sample_batch.hypotheses if h.is_confirmed)
        assert sample_batch.confirmed_count == confirmed

    def test_batch_confirmed_count_with_confirmed(self, sample_batch_with_confirmed):
        """Test confirmed_count with confirmed hypotheses."""
        assert sample_batch_with_confirmed.confirmed_count == 2

    def test_batch_pending_count(self, sample_batch):
        """Test pending_count property."""
        pending = sum(
            1 for h in sample_batch.hypotheses
            if h.validation_status == ValidationStatus.PENDING
        )
        assert sample_batch.pending_count == pending

    def test_batch_get_by_cwe_found(self, sample_batch):
        """Test get_by_cwe returns matching hypotheses."""
        results = sample_batch.get_by_cwe("CWE-120")
        assert len(results) >= 1
        for h in results:
            assert "CWE-120" in h.cwe_ids

    def test_batch_get_by_cwe_not_found(self, sample_batch):
        """Test get_by_cwe returns empty for non-existent CWE."""
        results = sample_batch.get_by_cwe("CWE-999")
        assert results == []

    def test_batch_get_top_priority(self, sample_batch):
        """Test get_top_priority returns sorted hypotheses."""
        top = sample_batch.get_top_priority(n=2)
        assert len(top) == 2
        # Should be sorted by priority_score descending
        assert top[0].priority_score >= top[1].priority_score

    def test_batch_get_top_priority_all(self, sample_batch):
        """Test get_top_priority with n larger than batch size."""
        top = sample_batch.get_top_priority(n=100)
        assert len(top) == 3  # Only 3 hypotheses in batch

    def test_batch_get_top_priority_default(self, sample_batch):
        """Test get_top_priority with default n=10."""
        top = sample_batch.get_top_priority()
        assert len(top) <= 10

    def test_batch_created_at(self, sample_batch):
        """Test created_at timestamp is set."""
        assert sample_batch.created_at is not None
        assert isinstance(sample_batch.created_at, datetime)


# =============================================================================
# ValidationResults Tests
# =============================================================================

class TestValidationResults:
    """Tests for ValidationResults dataclass."""

    def test_validation_results_creation(self, sample_validation_results):
        """Test creating validation results."""
        assert sample_validation_results.batch_id == "batch-001"
        assert sample_validation_results.total_hypotheses == 100
        assert sample_validation_results.executed_queries == 95

    def test_validation_results_cve_tracking(self, sample_validation_results):
        """Test CVE tracking fields."""
        assert "CVE-2025-8713" in sample_validation_results.cves_found
        assert "CVE-2025-8714" in sample_validation_results.cves_found
        assert "CVE-2025-8715" in sample_validation_results.cves_missed

    def test_detection_rate(self, sample_validation_results):
        """Test detection_rate calculation."""
        # 2 found / (2 found + 1 missed) = 2/3
        expected = 2 / 3
        assert abs(sample_validation_results.detection_rate - expected) < 0.001

    def test_detection_rate_perfect(self, sample_validation_results_perfect):
        """Test detection_rate when all CVEs found."""
        assert sample_validation_results_perfect.detection_rate == 1.0

    def test_detection_rate_zero(self):
        """Test detection_rate with no CVEs."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=10,
            executed_queries=10,
            cves_found=[],
            cves_missed=[],
        )
        assert results.detection_rate == 0.0

    def test_precision(self, sample_validation_results):
        """Test precision calculation."""
        # TP / (TP + FP) = 30 / (30 + 10) = 0.75
        expected = 30 / (30 + 10)
        assert abs(sample_validation_results.precision - expected) < 0.001

    def test_precision_perfect(self, sample_validation_results_perfect):
        """Test precision when no false positives."""
        assert sample_validation_results_perfect.precision == 1.0

    def test_precision_zero_denominator(self, sample_validation_results_empty):
        """Test precision when TP + FP = 0."""
        assert sample_validation_results_empty.precision == 0.0

    def test_recall(self, sample_validation_results):
        """Test recall calculation."""
        # TP / (TP + FN) = 30 / (30 + 5) = 0.857...
        expected = 30 / (30 + 5)
        assert abs(sample_validation_results.recall - expected) < 0.001

    def test_recall_perfect(self, sample_validation_results_perfect):
        """Test recall when no false negatives."""
        assert sample_validation_results_perfect.recall == 1.0

    def test_recall_zero_denominator(self, sample_validation_results_empty):
        """Test recall when TP + FN = 0."""
        assert sample_validation_results_empty.recall == 0.0

    def test_f1_score(self, sample_validation_results):
        """Test F1 score calculation."""
        p = sample_validation_results.precision
        r = sample_validation_results.recall
        expected = 2 * (p * r) / (p + r)
        assert abs(sample_validation_results.f1_score - expected) < 0.001

    def test_f1_score_perfect(self, sample_validation_results_perfect):
        """Test F1 score when precision and recall are 1.0."""
        assert sample_validation_results_perfect.f1_score == 1.0

    def test_f1_score_zero(self, sample_validation_results_empty):
        """Test F1 score when precision + recall = 0."""
        assert sample_validation_results_empty.f1_score == 0.0

    def test_hypothesis_accuracy(self, sample_validation_results):
        """Test hypothesis_accuracy calculation."""
        # confirmed / (confirmed + rejected) = 35 / (35 + 50) = 0.41...
        expected = 35 / (35 + 50)
        assert abs(sample_validation_results.hypothesis_accuracy - expected) < 0.001

    def test_hypothesis_accuracy_perfect(self, sample_validation_results_perfect):
        """Test hypothesis_accuracy when all confirmed."""
        assert sample_validation_results_perfect.hypothesis_accuracy == 1.0

    def test_hypothesis_accuracy_zero_denominator(self, sample_validation_results_empty):
        """Test hypothesis_accuracy when no confirmed or rejected."""
        assert sample_validation_results_empty.hypothesis_accuracy == 0.0

    def test_total_time(self, sample_validation_results):
        """Test total_time_sec calculation."""
        expected = 15.5 + 45.2
        assert abs(sample_validation_results.total_time_sec - expected) < 0.001

    def test_timestamps(self, sample_validation_results):
        """Test timestamp fields."""
        assert sample_validation_results.started_at is not None
        assert sample_validation_results.completed_at is None  # Default

    def test_default_values(self, sample_validation_results_empty):
        """Test default values for empty results."""
        assert sample_validation_results_empty.cves_found == []
        assert sample_validation_results_empty.cves_missed == []
        assert sample_validation_results_empty.true_positives == 0
        assert sample_validation_results_empty.false_positives == 0
        assert sample_validation_results_empty.false_negatives == 0
        assert sample_validation_results_empty.generation_time_sec == 0.0
        assert sample_validation_results_empty.execution_time_sec == 0.0
