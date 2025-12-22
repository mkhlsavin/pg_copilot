"""
Tests for Hypothesis Validator.

Tests for:
- HypothesisValidator initialization
- run_validation workflow
- validate_cve_patterns method
- _generate_hypotheses method
- _compute_codebase_stats method
- _compile_metrics method
- validate_postgresql_security function
- generate_validation_report function
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

# Mock duckdb module before importing validator
mock_duckdb = MagicMock()
sys.modules['duckdb'] = mock_duckdb

from src.security.hypothesis.validator import (
    HypothesisValidator,
    validate_postgresql_security,
    generate_validation_report,
)
from src.security.hypothesis.models import (
    SecurityHypothesis,
    ValidationResults,
    ValidationStatus,
    Evidence,
)
from src.security.hypothesis.knowledge_base import SecurityKnowledgeBase


# =============================================================================
# HypothesisValidator Initialization Tests
# =============================================================================

class TestHypothesisValidatorInit:
    """Tests for HypothesisValidator initialization."""

    def test_init_sets_db_path(self):
        """Test validator stores db_path."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.db_path == "/path/to/db.duckdb"

    def test_init_uses_default_kb(self):
        """Test validator uses default knowledge base."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.kb is not None

    def test_init_uses_custom_kb(self):
        """Test validator uses provided knowledge base."""
        custom_kb = SecurityKnowledgeBase(providers=[])
        validator = HypothesisValidator("/path/to/db.duckdb", knowledge_base=custom_kb)
        assert validator.kb is custom_kb

    def test_init_creates_generator(self):
        """Test validator creates HypothesisGenerator."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.generator is not None

    def test_init_creates_scorer(self):
        """Test validator creates MultiCriteriaScorer."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.scorer is not None

    def test_init_creates_synthesizer(self):
        """Test validator creates QuerySynthesizer."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.synthesizer is not None

    def test_init_creates_executor(self):
        """Test validator creates QueryExecutor."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        assert validator.executor is not None
        assert validator.executor.db_path == "/path/to/db.duckdb"


# =============================================================================
# run_validation Tests
# =============================================================================

class TestRunValidation:
    """Tests for run_validation method."""

    @pytest.fixture
    def mock_validator(self):
        """Create validator with mocked components."""
        validator = HypothesisValidator("/path/to/db.duckdb")

        # Mock internal components
        validator.generator = MagicMock()
        validator.scorer = MagicMock()
        validator.synthesizer = MagicMock()
        validator.executor = MagicMock()

        # Default mock behaviors
        validator.generator.generate_hypotheses.return_value = []
        validator.generator.generate_for_cve.return_value = []
        validator.scorer.score_batch.return_value = []
        validator.executor.__enter__ = MagicMock(return_value=validator.executor)
        validator.executor.__exit__ = MagicMock(return_value=False)
        validator.executor.validate_batch.return_value = []

        return validator

    def test_run_validation_returns_results(self, mock_validator):
        """Test run_validation returns ValidationResults."""
        result = mock_validator.run_validation()

        assert isinstance(result, ValidationResults)
        assert result.batch_id.startswith("validation-")

    def test_run_validation_calls_generator(self, mock_validator):
        """Test run_validation calls hypothesis generator."""
        mock_validator.run_validation(language="C", max_hypotheses=10)

        mock_validator.generator.generate_hypotheses.assert_called_once()
        call_kwargs = mock_validator.generator.generate_hypotheses.call_args[1]
        assert call_kwargs["language"] == "C"
        assert call_kwargs["max_hypotheses"] == 10

    def test_run_validation_calls_scorer(self, mock_validator):
        """Test run_validation scores hypotheses."""
        hyps = [MagicMock(priority_score=0.8)]
        mock_validator.generator.generate_hypotheses.return_value = hyps
        mock_validator.scorer.score_batch.return_value = hyps

        mock_validator.run_validation()

        mock_validator.scorer.score_batch.assert_called_once_with(hyps)

    def test_run_validation_filters_by_min_priority(self, mock_validator):
        """Test run_validation filters low-priority hypotheses."""
        high_priority = MagicMock(priority_score=0.8, sql_query=None)
        low_priority = MagicMock(priority_score=0.1, sql_query=None)

        mock_validator.generator.generate_hypotheses.return_value = [high_priority, low_priority]
        mock_validator.scorer.score_batch.return_value = [high_priority, low_priority]

        mock_validator.run_validation(min_priority_score=0.5)

        # Only high_priority should be passed to executor
        mock_validator.executor.validate_batch.assert_called_once()
        validated = mock_validator.executor.validate_batch.call_args[0][0]
        assert high_priority in validated
        assert low_priority not in validated

    def test_run_validation_synthesizes_queries(self, mock_validator):
        """Test run_validation synthesizes queries for hypotheses without them."""
        hyp_no_query = MagicMock(priority_score=0.8, sql_query=None)
        hyp_with_query = MagicMock(priority_score=0.8, sql_query="SELECT 1")

        mock_validator.generator.generate_hypotheses.return_value = [hyp_no_query, hyp_with_query]
        mock_validator.scorer.score_batch.return_value = [hyp_no_query, hyp_with_query]

        mock_validator.run_validation()

        # Synthesizer should only be called for hyp without query
        mock_validator.synthesizer.synthesize_query.assert_called_once_with(hyp_no_query)

    def test_run_validation_executes_validation(self, mock_validator):
        """Test run_validation executes queries."""
        hyps = [MagicMock(priority_score=0.8, sql_query="SELECT 1")]
        mock_validator.generator.generate_hypotheses.return_value = hyps
        mock_validator.scorer.score_batch.return_value = hyps

        mock_validator.run_validation()

        mock_validator.executor.validate_batch.assert_called_once()

    def test_run_validation_tracks_timing(self, mock_validator):
        """Test run_validation tracks generation and execution time."""
        result = mock_validator.run_validation()

        assert result.generation_time_sec >= 0
        assert result.execution_time_sec >= 0

    def test_run_validation_with_categories(self, mock_validator):
        """Test run_validation passes categories filter."""
        mock_validator.run_validation(categories=["buffer_overflow", "command_injection"])

        call_kwargs = mock_validator.generator.generate_hypotheses.call_args[1]
        assert call_kwargs["categories"] == ["buffer_overflow", "command_injection"]

    def test_run_validation_with_target_cves(self, mock_validator):
        """Test run_validation generates CVE-specific hypotheses."""
        mock_validator.run_validation(target_cves=["CVE-2025-8713", "CVE-2025-8714"])

        assert mock_validator.generator.generate_for_cve.call_count == 2


# =============================================================================
# validate_cve_patterns Tests
# =============================================================================

class TestValidateCVEPatterns:
    """Tests for validate_cve_patterns method."""

    @pytest.fixture
    def mock_validator(self):
        """Create validator with mocked run_validation."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        validator.run_validation = MagicMock(return_value=ValidationResults(
            batch_id="test",
            total_hypotheses=10,
            executed_queries=10,
        ))
        return validator

    def test_validate_cve_patterns_calls_run_validation(self, mock_validator):
        """Test validate_cve_patterns calls run_validation."""
        mock_validator.validate_cve_patterns(["CVE-2025-8713"])

        mock_validator.run_validation.assert_called_once()

    def test_validate_cve_patterns_passes_cve_ids(self, mock_validator):
        """Test validate_cve_patterns passes CVE IDs."""
        mock_validator.validate_cve_patterns(["CVE-2025-8713", "CVE-2025-8714"])

        call_kwargs = mock_validator.run_validation.call_args[1]
        assert call_kwargs["target_cves"] == ["CVE-2025-8713", "CVE-2025-8714"]

    def test_validate_cve_patterns_uses_higher_max(self, mock_validator):
        """Test validate_cve_patterns uses higher max_hypotheses."""
        mock_validator.validate_cve_patterns(["CVE-2025-8713"])

        call_kwargs = mock_validator.run_validation.call_args[1]
        assert call_kwargs["max_hypotheses"] == 100

    def test_validate_cve_patterns_uses_lower_threshold(self, mock_validator):
        """Test validate_cve_patterns uses lower min_priority_score."""
        mock_validator.validate_cve_patterns(["CVE-2025-8713"])

        call_kwargs = mock_validator.run_validation.call_args[1]
        assert call_kwargs["min_priority_score"] == 0.2


# =============================================================================
# _generate_hypotheses Tests
# =============================================================================

class TestGenerateHypotheses:
    """Tests for _generate_hypotheses method."""

    @pytest.fixture
    def mock_validator(self):
        """Create validator with mocked generator."""
        validator = HypothesisValidator("/path/to/db.duckdb")
        validator.generator = MagicMock()
        validator.generator.generate_hypotheses.return_value = []
        validator.generator.generate_for_cve.return_value = []
        return validator

    def test_generate_hypotheses_calls_generator(self, mock_validator):
        """Test _generate_hypotheses calls generator."""
        mock_validator._generate_hypotheses("C", 50, None, None)

        mock_validator.generator.generate_hypotheses.assert_called_once_with(
            language="C",
            max_hypotheses=50,
            categories=None,
        )

    def test_generate_hypotheses_with_categories(self, mock_validator):
        """Test _generate_hypotheses passes categories."""
        mock_validator._generate_hypotheses("C", 50, ["buffer_overflow"], None)

        call_kwargs = mock_validator.generator.generate_hypotheses.call_args[1]
        assert call_kwargs["categories"] == ["buffer_overflow"]

    def test_generate_hypotheses_adds_cve_hypotheses(self, mock_validator):
        """Test _generate_hypotheses adds CVE-specific hypotheses."""
        general = [MagicMock()]
        cve_specific = [MagicMock(), MagicMock()]

        mock_validator.generator.generate_hypotheses.return_value = general
        mock_validator.generator.generate_for_cve.return_value = cve_specific

        result = mock_validator._generate_hypotheses(
            "C", 50, None, ["CVE-2025-8713"]
        )

        assert len(result) == 3  # 1 general + 2 CVE-specific

    def test_generate_hypotheses_calls_generate_for_cve(self, mock_validator):
        """Test _generate_hypotheses calls generate_for_cve for each CVE."""
        mock_validator._generate_hypotheses(
            "C", 50, None, ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]
        )

        assert mock_validator.generator.generate_for_cve.call_count == 3


# =============================================================================
# _compile_metrics Tests
# =============================================================================

class TestCompileMetrics:
    """Tests for _compile_metrics method."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return HypothesisValidator("/path/to/db.duckdb")

    def test_compile_metrics_counts_confirmed(self, validator):
        """Test _compile_metrics counts confirmed hypotheses."""
        results = ValidationResults(batch_id="test", total_hypotheses=3, executed_queries=3)

        validated = [
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=[]),
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=[]),
            MagicMock(validation_status=ValidationStatus.REJECTED, tags=[]),
        ]

        validator._compile_metrics(results, validated, None)

        assert results.confirmed_hypotheses == 2
        assert results.true_positives == 2

    def test_compile_metrics_counts_rejected(self, validator):
        """Test _compile_metrics counts rejected hypotheses."""
        results = ValidationResults(batch_id="test", total_hypotheses=3, executed_queries=3)

        validated = [
            MagicMock(validation_status=ValidationStatus.REJECTED, tags=[]),
            MagicMock(validation_status=ValidationStatus.REJECTED, tags=[]),
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=[]),
        ]

        validator._compile_metrics(results, validated, None)

        assert results.rejected_hypotheses == 2

    def test_compile_metrics_counts_inconclusive(self, validator):
        """Test _compile_metrics counts inconclusive hypotheses."""
        results = ValidationResults(batch_id="test", total_hypotheses=2, executed_queries=2)

        validated = [
            MagicMock(validation_status=ValidationStatus.INCONCLUSIVE, tags=[]),
            MagicMock(validation_status=ValidationStatus.INCONCLUSIVE, tags=[]),
        ]

        validator._compile_metrics(results, validated, None)

        assert results.inconclusive_hypotheses == 2

    def test_compile_metrics_tracks_cves_found(self, validator):
        """Test _compile_metrics tracks found CVEs."""
        results = ValidationResults(batch_id="test", total_hypotheses=2, executed_queries=2)

        validated = [
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=["CVE-2025-8713"]),
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=["CVE-2025-8714"]),
        ]

        validator._compile_metrics(
            results, validated, ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]
        )

        assert "CVE-2025-8713" in results.cves_found
        assert "CVE-2025-8714" in results.cves_found

    def test_compile_metrics_tracks_cves_missed(self, validator):
        """Test _compile_metrics tracks missed CVEs."""
        results = ValidationResults(batch_id="test", total_hypotheses=1, executed_queries=1)

        validated = [
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=["CVE-2025-8713"]),
        ]

        validator._compile_metrics(
            results, validated, ["CVE-2025-8713", "CVE-2025-8714"]
        )

        assert "CVE-2025-8714" in results.cves_missed

    def test_compile_metrics_ignores_non_target_cves(self, validator):
        """Test _compile_metrics ignores non-target CVE tags."""
        results = ValidationResults(batch_id="test", total_hypotheses=1, executed_queries=1)

        validated = [
            MagicMock(validation_status=ValidationStatus.CONFIRMED, tags=["CVE-2024-9999"]),
        ]

        validator._compile_metrics(
            results, validated, ["CVE-2025-8713"]
        )

        assert results.cves_found == []
        assert "CVE-2025-8713" in results.cves_missed


# =============================================================================
# validate_postgresql_security Tests
# =============================================================================

class TestValidatePostgresqlSecurity:
    """Tests for validate_postgresql_security function."""

    @patch('src.security.hypothesis.validator.HypothesisValidator')
    def test_function_creates_validator(self, mock_class):
        """Test function creates HypothesisValidator."""
        mock_instance = MagicMock()
        mock_instance.run_validation.return_value = ValidationResults(
            batch_id="test", total_hypotheses=0, executed_queries=0
        )
        mock_class.return_value = mock_instance

        validate_postgresql_security("/path/to/db.duckdb")

        mock_class.assert_called_once_with("/path/to/db.duckdb")

    @patch('src.security.hypothesis.validator.HypothesisValidator')
    def test_function_includes_known_cves_by_default(self, mock_class):
        """Test function includes known CVEs by default."""
        mock_instance = MagicMock()
        mock_instance.run_validation.return_value = ValidationResults(
            batch_id="test", total_hypotheses=0, executed_queries=0
        )
        mock_class.return_value = mock_instance

        validate_postgresql_security("/path/to/db.duckdb")

        call_kwargs = mock_instance.run_validation.call_args[1]
        assert call_kwargs["target_cves"] == ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]

    @patch('src.security.hypothesis.validator.HypothesisValidator')
    def test_function_can_exclude_cves(self, mock_class):
        """Test function can exclude known CVEs."""
        mock_instance = MagicMock()
        mock_instance.run_validation.return_value = ValidationResults(
            batch_id="test", total_hypotheses=0, executed_queries=0
        )
        mock_class.return_value = mock_instance

        validate_postgresql_security("/path/to/db.duckdb", include_known_cves=False)

        call_kwargs = mock_instance.run_validation.call_args[1]
        assert call_kwargs["target_cves"] is None

    @patch('src.security.hypothesis.validator.HypothesisValidator')
    def test_function_includes_postgresql_categories(self, mock_class):
        """Test function includes PostgreSQL-specific categories."""
        mock_instance = MagicMock()
        mock_instance.run_validation.return_value = ValidationResults(
            batch_id="test", total_hypotheses=0, executed_queries=0
        )
        mock_class.return_value = mock_instance

        validate_postgresql_security("/path/to/db.duckdb")

        call_kwargs = mock_instance.run_validation.call_args[1]
        assert "pg_dump_injection" in call_kwargs["categories"]
        assert "spi_sql_injection" in call_kwargs["categories"]
        assert "statistics_disclosure" in call_kwargs["categories"]


# =============================================================================
# generate_validation_report Tests
# =============================================================================

class TestGenerateValidationReport:
    """Tests for generate_validation_report function."""

    def test_report_contains_batch_id(self):
        """Test report contains batch ID."""
        results = ValidationResults(
            batch_id="validation-20250101-120000",
            total_hypotheses=10,
            executed_queries=10,
        )

        report = generate_validation_report(results, [])

        assert "validation-20250101-120000" in report

    def test_report_contains_summary(self):
        """Test report contains summary section."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=10,
            executed_queries=8,
            confirmed_hypotheses=3,
            rejected_hypotheses=4,
            inconclusive_hypotheses=1,
        )

        report = generate_validation_report(results, [])

        assert "## Summary" in report
        assert "Total Hypotheses: 10" in report
        assert "Confirmed: 3" in report
        assert "Rejected: 4" in report

    def test_report_contains_cve_detection(self):
        """Test report contains CVE detection section when CVEs are tracked."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=5,
            executed_queries=5,
            cves_found=["CVE-2025-8713"],
            cves_missed=["CVE-2025-8714"],
        )

        report = generate_validation_report(results, [])

        assert "## CVE Detection" in report
        assert "CVE-2025-8713" in report
        assert "CVE-2025-8714" in report

    def test_report_contains_performance(self):
        """Test report contains performance section."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=10,
            executed_queries=10,
            generation_time_sec=1.5,
            execution_time_sec=2.5,
        )

        report = generate_validation_report(results, [])

        assert "## Performance" in report
        assert "Generation Time:" in report
        assert "Execution Time:" in report

    def test_report_contains_quality_metrics(self):
        """Test report contains quality metrics section."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=10,
            executed_queries=10,
            true_positives=5,
            false_positives=1,
            false_negatives=2,
        )

        report = generate_validation_report(results, [])

        assert "## Quality Metrics" in report
        assert "Precision:" in report
        assert "Recall:" in report
        assert "F1 Score:" in report

    def test_report_contains_confirmed_findings(self):
        """Test report contains confirmed findings section."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=1,
            executed_queries=1,
        )

        hyp = SecurityHypothesis(
            id="hyp-001",
            hypothesis_text="Test hypothesis with buffer overflow vulnerability",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=[],
            sink_patterns=[],
            sanitizer_patterns=[],
            priority_score=0.9,
            validation_status=ValidationStatus.CONFIRMED,
            evidence=[Evidence(
                id="ev-001",
                hypothesis_id="hyp-001",
                query_executed="SELECT *",
                result_count=5,
                findings=[],
                filename="test.c",
                line_number=42,
            )],
        )

        report = generate_validation_report(results, [hyp])

        assert "## Confirmed Findings" in report
        assert "buffer_overflow" in report
        assert "CWE-120" in report

    def test_report_limits_confirmed_findings(self):
        """Test report limits confirmed findings to 10."""
        results = ValidationResults(
            batch_id="test",
            total_hypotheses=20,
            executed_queries=20,
        )

        hypotheses = []
        for i in range(15):
            hyp = SecurityHypothesis(
                id=f"hyp-{i:03d}",
                hypothesis_text=f"Hypothesis {i}",
                cwe_ids=["CWE-120"],
                capec_ids=[],
                language="C",
                category="buffer_overflow",
                source_patterns=[],
                sink_patterns=[],
                sanitizer_patterns=[],
                validation_status=ValidationStatus.CONFIRMED,
            )
            hypotheses.append(hyp)

        report = generate_validation_report(results, hypotheses)

        # Should have at most 10 numbered findings
        assert "### 10." in report
        assert "### 11." not in report
