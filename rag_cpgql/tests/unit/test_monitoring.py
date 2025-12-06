"""
Unit tests for Monitoring Infrastructure

Tests:
- Structured logging
- Prometheus metrics
- Monitoring decorators
- Health checks
- Metrics collector

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import pytest
import time
import threading
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.metrics import (
    StructuredLogger,
    MetricsCollector,
    get_metrics_collector,
    monitor_scenario,
    monitor_agent,
    monitor_cache,
    record_llm_call,
    record_cpg_query,
    record_retrieval,
    SCENARIO_SUCCESS,
    SCENARIO_FAILURE,
    CACHE_HITS,
    CACHE_MISSES,
)

from src.monitoring.health import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    check_database_connection,
    check_llm_availability,
)


class TestStructuredLogger:
    """Test structured logging functionality."""

    def test_logger_initialization(self):
        """Test logger initializes correctly."""
        logger = StructuredLogger("test_component")
        assert logger.name == "test_component"

    def test_info_logging(self, capsys):
        """Test info level logging."""
        logger = StructuredLogger("test")
        logger.info("Test message", key="value")
        # Logger writes to stream, can't easily capture
        # Just verify no exception
        assert True

    def test_error_logging(self):
        """Test error level logging."""
        logger = StructuredLogger("test")
        logger.error("Error message", error_code=500)
        assert True

    def test_timed_operation_success(self):
        """Test timed operation context manager on success."""
        logger = StructuredLogger("test")

        with logger.timed_operation("test_op", context="test"):
            time.sleep(0.01)

        # No exception means success
        assert True

    def test_timed_operation_failure(self):
        """Test timed operation context manager on failure."""
        logger = StructuredLogger("test")

        with pytest.raises(ValueError):
            with logger.timed_operation("failing_op"):
                raise ValueError("Test error")


class TestMetricsCollector:
    """Test MetricsCollector singleton."""

    def test_singleton(self):
        """Test MetricsCollector is singleton."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2

    def test_get_metrics_collector(self):
        """Test get_metrics_collector function."""
        collector = get_metrics_collector()
        assert collector is not None
        assert isinstance(collector, MetricsCollector)

    def test_record_latency(self):
        """Test recording latency."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_latency("test_metric", 0.5)
        collector.record_latency("test_metric", 1.0)

        # Latencies are stored internally
        assert len(collector._latencies["test_metric"]) == 2

    def test_increment_counter(self):
        """Test incrementing counter."""
        collector = MetricsCollector()
        collector.reset()

        collector.increment_counter("test_counter")
        collector.increment_counter("test_counter", 5)

        assert collector._counters["test_counter"] == 6

    def test_set_gauge(self):
        """Test setting gauge."""
        collector = MetricsCollector()
        collector.reset()

        collector.set_gauge("test_gauge", 42.0)
        assert collector._gauges["test_gauge"] == 42.0

        collector.set_gauge("test_gauge", 100.0)
        assert collector._gauges["test_gauge"] == 100.0

    def test_record_scenario(self):
        """Test recording scenario execution."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_scenario("security", success=True, latency=1.5)
        collector.record_scenario("security", success=False, latency=2.0)
        collector.record_scenario("security", success=True, latency=0.5)

        stats = collector._scenario_stats["security"]
        assert stats['success'] == 2
        assert stats['failure'] == 1
        assert len(stats['latencies']) == 3

    def test_record_cache_access(self):
        """Test recording cache access."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_cache_access("query_plan", hit=True)
        collector.record_cache_access("query_plan", hit=True)
        collector.record_cache_access("query_plan", hit=False)

        assert collector._cache_hits["query_plan"] == 2
        assert collector._cache_misses["query_plan"] == 1

    def test_get_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()
        collector.reset()

        # Add some data
        collector.record_scenario("test", success=True, latency=1.0)
        collector.record_scenario("test", success=True, latency=2.0)
        collector.record_scenario("test", success=False, latency=3.0)
        collector.record_cache_access("test_cache", hit=True)
        collector.record_cache_access("test_cache", hit=False)

        summary = collector.get_summary()

        assert summary.total_requests == 3
        assert summary.successful_requests == 2
        assert summary.failed_requests == 1
        assert summary.success_rate == pytest.approx(2/3, rel=0.01)
        assert summary.cache_hit_rate == pytest.approx(0.5, rel=0.01)

    def test_get_scenario_stats(self):
        """Test getting per-scenario statistics."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_scenario("security", success=True, latency=1.0)
        collector.record_scenario("performance", success=False, latency=2.0)

        stats = collector.get_scenario_stats()

        assert "security" in stats
        assert "performance" in stats
        assert stats["security"]["success_count"] == 1
        assert stats["performance"]["failure_count"] == 1

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_cache_access("query", hit=True)
        collector.record_cache_access("query", hit=True)
        collector.record_cache_access("embedding", hit=False)

        stats = collector.get_cache_stats()

        assert "query" in stats
        assert "embedding" in stats
        assert stats["query"]["hit_rate"] == 1.0
        assert stats["embedding"]["hit_rate"] == 0.0

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        collector.record_scenario("test", success=True, latency=1.0)
        collector.record_cache_access("test", hit=True)

        collector.reset()

        summary = collector.get_summary()
        assert summary.total_requests == 0

    def test_uptime(self):
        """Test uptime tracking."""
        collector = MetricsCollector()
        collector.reset()

        time.sleep(0.1)
        uptime = collector.get_uptime_seconds()

        assert uptime >= 0.1


class TestMonitoringDecorators:
    """Test monitoring decorators."""

    def test_monitor_scenario_success(self):
        """Test monitor_scenario decorator on success."""
        @monitor_scenario("test_scenario")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_monitor_scenario_failure(self):
        """Test monitor_scenario decorator on failure."""
        @monitor_scenario("failing_scenario")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_monitor_agent_success(self):
        """Test monitor_agent decorator."""
        @monitor_agent("test_agent", scenario="test")
        def agent_function():
            return {"result": "data"}

        result = agent_function()
        assert result == {"result": "data"}

    def test_monitor_cache_hit(self):
        """Test monitor_cache decorator on hit."""
        @monitor_cache("test_cache")
        def cache_lookup_hit(key):
            return {"data": "cached"}

        result = cache_lookup_hit("key1")
        assert result is not None

    def test_monitor_cache_miss(self):
        """Test monitor_cache decorator on miss."""
        @monitor_cache("test_cache")
        def cache_lookup_miss(key):
            return None

        result = cache_lookup_miss("key1")
        assert result is None


class TestRecordingFunctions:
    """Test metric recording functions."""

    def test_record_llm_call(self):
        """Test recording LLM call metrics."""
        # Should not raise
        record_llm_call(
            model="gigachat",
            operation="generate",
            duration=1.5,
            input_tokens=100,
            output_tokens=50
        )
        assert True

    def test_record_llm_call_with_error(self):
        """Test recording LLM call with error."""
        record_llm_call(
            model="gigachat",
            operation="generate",
            duration=0.5,
            error="timeout"
        )
        assert True

    def test_record_cpg_query(self):
        """Test recording CPG query metrics."""
        record_cpg_query(
            query_type="method_lookup",
            duration=0.1,
            result_count=25
        )
        assert True

    def test_record_retrieval(self):
        """Test recording retrieval metrics."""
        record_retrieval(
            retrieval_type="hybrid",
            duration=0.5,
            result_count=10
        )
        assert True


class TestHealthChecker:
    """Test health checker functionality."""

    def test_health_checker_initialization(self):
        """Test health checker initializes correctly."""
        checker = HealthChecker()
        assert checker is not None
        assert len(checker._checks) >= 2  # database and llm

    def test_register_custom_check(self):
        """Test registering custom health check."""
        checker = HealthChecker()

        def custom_check():
            return ComponentHealth(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="All good"
            )

        checker.register_check("custom", custom_check)
        assert "custom" in checker._checks

    def test_unregister_check(self):
        """Test unregistering health check."""
        checker = HealthChecker()
        initial_count = len(checker._checks)

        checker.register_check("temp", lambda: ComponentHealth(
            name="temp",
            status=HealthStatus.HEALTHY
        ))
        checker.unregister_check("temp")

        assert len(checker._checks) == initial_count

    def test_check_liveness(self):
        """Test liveness probe."""
        checker = HealthChecker()
        assert checker.check_liveness() is True

    def test_component_health_to_dict(self):
        """Test ComponentHealth serialization."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            latency_ms=10.5,
            message="OK",
            details={"key": "value"}
        )

        result = health.to_dict()

        assert result["name"] == "test"
        assert result["status"] == "healthy"
        assert result["latency_ms"] == 10.5
        assert result["message"] == "OK"
        assert result["details"]["key"] == "value"

    def test_system_health_to_dict(self):
        """Test SystemHealth serialization."""
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="llm", status=HealthStatus.DEGRADED),
        ]

        health = SystemHealth(
            status=HealthStatus.DEGRADED,
            components=components,
            uptime_seconds=100.5
        )

        result = health.to_dict()

        assert result["status"] == "degraded"
        assert len(result["components"]) == 2
        assert result["uptime_seconds"] == 100.5


class TestHealthStatus:
    """Test health status enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestThreadSafety:
    """Test thread safety of metrics collection."""

    def test_concurrent_metric_recording(self):
        """Test concurrent metric recording."""
        collector = MetricsCollector()
        collector.reset()
        errors = []

        def record_metrics():
            try:
                for i in range(100):
                    collector.record_scenario(
                        f"scenario_{threading.current_thread().name}",
                        success=True,
                        latency=0.01
                    )
                    collector.record_cache_access("test", hit=i % 2 == 0)
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = [
            threading.Thread(target=record_metrics, name=f"Thread-{i}")
            for i in range(4)
        ]

        # Start all
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0

    def test_concurrent_summary_generation(self):
        """Test concurrent summary generation."""
        collector = MetricsCollector()
        collector.reset()
        errors = []
        summaries = []

        def generate_summary():
            try:
                for _ in range(50):
                    summary = collector.get_summary()
                    summaries.append(summary)
            except Exception as e:
                errors.append(e)

        def record_data():
            try:
                for _ in range(50):
                    collector.record_scenario("test", success=True, latency=0.01)
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = [
            threading.Thread(target=generate_summary),
            threading.Thread(target=generate_summary),
            threading.Thread(target=record_data),
            threading.Thread(target=record_data),
        ]

        # Start all
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0
        assert len(summaries) == 100


class TestMetricsSummary:
    """Test MetricsSummary dataclass."""

    def test_summary_to_dict(self):
        """Test MetricsSummary serialization."""
        collector = MetricsCollector()
        collector.reset()

        collector.record_scenario("test", success=True, latency=1.0)
        summary = collector.get_summary()

        result = summary.to_dict()

        assert "total_requests" in result
        assert "success_rate" in result
        assert "cache_hit_rate" in result
        assert isinstance(result["avg_latency_ms"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
