"""
Unit tests for RAGAS Feedback Loop

Tests:
- Evaluation result creation
- Database storage
- Trend analysis
- Degradation detection
- Summary statistics

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import pytest
import os
import time
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.feedback_loop import (
    RAGASFeedbackLoop,
    EvaluationResult,
    DegradationAlert,
    MetricsTrend,
    AlertSeverity,
    get_feedback_loop,
    evaluate_and_store,
    check_quality_health,
)


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_creation(self):
        """Test creating evaluation result."""
        result = EvaluationResult(
            timestamp=datetime.now(),
            scenario="security",
            question="How do I find vulnerabilities?",
            answer="Use the security scanner...",
            faithfulness=0.85,
            answer_relevancy=0.90,
            context_precision=0.75,
            context_recall=0.80,
            overall_score=0.825,
            latency_ms=150.0,
            contexts=["Context 1", "Context 2"],
            metadata={"intent": "security_audit"}
        )

        assert result.scenario == "security"
        assert result.faithfulness == 0.85
        assert result.overall_score == 0.825
        assert len(result.contexts) == 2

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = EvaluationResult(
            timestamp=datetime.now(),
            scenario="test",
            question="Test?",
            answer="Answer",
            faithfulness=0.8,
            answer_relevancy=0.9,
            context_precision=0.7,
            context_recall=0.75,
            overall_score=0.79,
            latency_ms=100.0
        )

        data = result.to_dict()

        assert "timestamp" in data
        assert data["scenario"] == "test"
        assert data["faithfulness"] == 0.8
        assert isinstance(data["timestamp"], str)  # ISO format


class TestDegradationAlert:
    """Test DegradationAlert dataclass."""

    def test_creation(self):
        """Test creating degradation alert."""
        alert = DegradationAlert(
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            metric="faithfulness",
            current_value=0.75,
            baseline_value=0.85,
            threshold=0.05,
            message="Faithfulness degraded"
        )

        assert alert.severity == AlertSeverity.WARNING
        assert alert.metric == "faithfulness"
        assert alert.current_value == 0.75

    def test_to_dict(self):
        """Test serialization."""
        alert = DegradationAlert(
            timestamp=datetime.now(),
            severity=AlertSeverity.CRITICAL,
            metric="overall",
            current_value=0.5,
            baseline_value=0.8,
            threshold=0.1,
            message="Test"
        )

        data = alert.to_dict()

        assert data["severity"] == "critical"
        assert data["metric"] == "overall"


class TestMetricsTrend:
    """Test MetricsTrend dataclass."""

    def test_creation(self):
        """Test creating metrics trend."""
        trend = MetricsTrend(
            dates=["2025-11-20", "2025-11-21"],
            faithfulness=[0.8, 0.85],
            answer_relevancy=[0.9, 0.88],
            context_precision=[0.7, 0.75],
            context_recall=[0.8, 0.82],
            overall=[0.8, 0.825],
            sample_counts=[10, 15]
        )

        assert len(trend.dates) == 2
        assert trend.faithfulness[1] == 0.85

    def test_to_dict(self):
        """Test serialization."""
        trend = MetricsTrend(
            dates=["2025-11-20"],
            faithfulness=[0.8],
            answer_relevancy=[0.9],
            context_precision=[0.7],
            context_recall=[0.8],
            overall=[0.8],
            sample_counts=[10]
        )

        data = trend.to_dict()

        assert "dates" in data
        assert len(data["faithfulness"]) == 1


class TestRAGASFeedbackLoop:
    """Test RAGASFeedbackLoop class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def feedback_loop(self, temp_db):
        """Create feedback loop with temp database."""
        return RAGASFeedbackLoop(db_path=temp_db)

    def test_initialization(self, feedback_loop):
        """Test feedback loop initializes correctly."""
        assert feedback_loop is not None
        assert feedback_loop.degradation_threshold == 0.05
        assert feedback_loop.alert_window == 10

    def test_evaluate_response(self, feedback_loop):
        """Test evaluating a response."""
        result = feedback_loop.evaluate_response(
            question="How does PostgreSQL work?",
            answer="PostgreSQL is a database system that...",
            contexts=["PostgreSQL uses MVCC for concurrency"],
            scenario="onboarding",
            latency_ms=100.0,
            use_ragas=False  # Use custom metrics
        )

        assert isinstance(result, EvaluationResult)
        assert result.scenario == "onboarding"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0

    def test_multiple_evaluations(self, feedback_loop):
        """Test storing multiple evaluations."""
        for i in range(5):
            feedback_loop.evaluate_response(
                question=f"Question {i}?",
                answer=f"Answer {i}",
                contexts=[f"Context {i}"],
                scenario="test",
                use_ragas=False
            )

        stats = feedback_loop.get_summary_stats(days=1)
        assert stats['total_evaluations'] == 5

    def test_get_summary_stats(self, feedback_loop):
        """Test getting summary statistics."""
        # Add some evaluations
        for i in range(3):
            feedback_loop.evaluate_response(
                question=f"Q{i}",
                answer=f"A{i}",
                contexts=["C1", "C2"],
                scenario="security",
                use_ragas=False
            )

        stats = feedback_loop.get_summary_stats(days=7)

        assert stats['total_evaluations'] == 3
        assert 'avg_faithfulness' in stats
        assert 'avg_overall_score' in stats
        assert 'scenarios' in stats
        assert 'security' in stats['scenarios']

    def test_get_metrics_over_time(self, feedback_loop):
        """Test getting metrics trend."""
        # Add evaluations
        for i in range(3):
            feedback_loop.evaluate_response(
                question=f"Q{i}",
                answer=f"A{i}",
                contexts=["C"],
                scenario="test",
                use_ragas=False
            )

        trend = feedback_loop.get_metrics_over_time(days=7)

        assert isinstance(trend, MetricsTrend)
        assert len(trend.dates) >= 1  # At least today

    def test_custom_evaluation_metrics(self, feedback_loop):
        """Test custom evaluation without RAGAS."""
        # High quality response
        result1 = feedback_loop.evaluate_response(
            question="What is memory allocation?",
            answer="Memory allocation is the process of allocating memory for data structures",
            contexts=["Memory allocation involves reserving memory space"],
            scenario="test",
            use_ragas=False
        )

        # Low quality response
        result2 = feedback_loop.evaluate_response(
            question="What is memory allocation?",
            answer="Unknown",
            contexts=[],
            scenario="test",
            use_ragas=False
        )

        # High quality should score better
        assert result1.overall_score >= result2.overall_score

    def test_detect_degradation_no_data(self, feedback_loop):
        """Test degradation detection with insufficient data."""
        alerts = feedback_loop.detect_degradation()
        assert len(alerts) == 0  # Not enough data

    def test_detect_degradation_with_data(self, feedback_loop):
        """Test degradation detection with data."""
        # Add good evaluations (previous window)
        for i in range(10):
            result = EvaluationResult(
                timestamp=datetime.now() - timedelta(hours=2),
                scenario="test",
                question=f"Q{i}",
                answer=f"A{i}",
                faithfulness=0.9,
                answer_relevancy=0.9,
                context_precision=0.9,
                context_recall=0.9,
                overall_score=0.9,
                latency_ms=100.0
            )
            feedback_loop._store_evaluation(result)

        # Add degraded evaluations (recent window)
        for i in range(10):
            result = EvaluationResult(
                timestamp=datetime.now(),
                scenario="test",
                question=f"Q{i}",
                answer=f"A{i}",
                faithfulness=0.6,
                answer_relevancy=0.6,
                context_precision=0.6,
                context_recall=0.6,
                overall_score=0.6,
                latency_ms=100.0
            )
            feedback_loop._store_evaluation(result)

        alerts = feedback_loop.detect_degradation(threshold=0.1)

        assert len(alerts) > 0  # Should detect degradation

    def test_get_recent_alerts(self, feedback_loop):
        """Test getting recent alerts."""
        # Manually store an alert
        alert = DegradationAlert(
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            metric="test",
            current_value=0.5,
            baseline_value=0.8,
            threshold=0.1,
            message="Test alert"
        )
        feedback_loop._store_alert(alert)

        alerts = feedback_loop.get_recent_alerts(limit=5)

        assert len(alerts) == 1
        assert alerts[0].metric == "test"

    def test_is_healthy_no_data(self, feedback_loop):
        """Test health check with no data."""
        is_healthy, message = feedback_loop.is_healthy()
        assert is_healthy is True
        assert "No recent evaluations" in message

    def test_is_healthy_with_data(self, feedback_loop):
        """Test health check with data."""
        # Add good evaluations
        for i in range(3):
            feedback_loop.evaluate_response(
                question=f"Q{i}",
                answer=f"A{i} with good context",
                contexts=["Good context 1", "Good context 2"],
                scenario="test",
                use_ragas=False
            )

        is_healthy, message = feedback_loop.is_healthy(min_score=0.1)
        assert is_healthy is True

    def test_cleanup_old_data(self, feedback_loop):
        """Test cleanup of old data."""
        # Add evaluations
        for i in range(5):
            feedback_loop.evaluate_response(
                question=f"Q{i}",
                answer=f"A{i}",
                contexts=["C"],
                scenario="test",
                use_ragas=False
            )

        # Cleanup (with 0 days keeps nothing)
        feedback_loop.cleanup_old_data(days=0)

        stats = feedback_loop.get_summary_stats(days=1)
        # Recent evaluations should still be there (within same day)
        # This test verifies the cleanup function runs without error


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset global singleton between tests."""
        import src.evaluation.feedback_loop as fl
        fl._feedback_loop = None
        yield
        fl._feedback_loop = None

    def test_get_feedback_loop_singleton(self):
        """Test get_feedback_loop returns singleton."""
        # Use temp file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            loop1 = get_feedback_loop(db_path=path)
            loop2 = get_feedback_loop(db_path=path)
            assert loop1 is loop2
        finally:
            os.unlink(path)

    def test_evaluate_and_store(self):
        """Test evaluate_and_store convenience function."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            # Reset singleton to use temp db
            import src.evaluation.feedback_loop as fl
            fl._feedback_loop = RAGASFeedbackLoop(db_path=path)

            result = evaluate_and_store(
                question="Test question?",
                answer="Test answer",
                contexts=["Context"],
                scenario="test",
                latency_ms=50.0
            )

            assert isinstance(result, EvaluationResult)
        finally:
            os.unlink(path)

    def test_check_quality_health(self):
        """Test check_quality_health function."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            import src.evaluation.feedback_loop as fl
            fl._feedback_loop = RAGASFeedbackLoop(db_path=path)

            is_healthy, message = check_quality_health()
            assert isinstance(is_healthy, bool)
            assert isinstance(message, str)
        finally:
            os.unlink(path)


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
