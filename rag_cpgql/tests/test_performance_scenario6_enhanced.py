"""
Test Suite for Scenario 6: Performance Optimization (Enhanced)

Phase 5, Week 18 Enhancement Tests
Tests for 12 performance patterns + production-ready profiling features

Test Coverage:
- 12 performance pattern detection (6 original + 6 new)
- cProfile integration
- Memory profiling with tracemalloc
- Performance baseline creation
- Regression detection
- Trend analysis
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import time

from src.performance import (
    # Patterns
    PERFORMANCE_PATTERNS,
    get_pattern_by_id,
    PerformancePattern,
    BottleneckSeverity,
    BottleneckCategory,
    # Agents
    PerformanceProfiler,
    ResourceAnalyzer,
    OptimizationAdvisor,
    # Data structures
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    # Phase 5: Profiling structures
    ProfilingResult,
    MemoryProfilingResult,
    PerformanceBaseline,
    PerformanceTrend,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mock_cpg():
    """Create a mock CPG service for testing"""
    mock_cpg = Mock()
    mock_cpg.__enter__ = Mock(return_value=mock_cpg)
    mock_cpg.__exit__ = Mock(return_value=False)
    return mock_cpg


def create_test_finding(pattern_id: str, severity: str, method_name: str) -> BottleneckFinding:
    """Create a test bottleneck finding"""
    pattern = get_pattern_by_id(pattern_id)
    return BottleneckFinding(
        finding_id=f"{pattern_id}_001",
        pattern_id=pattern_id,
        pattern_name=pattern.name,
        category=pattern.category.value,
        severity=severity,
        method_id=1,
        method_name=method_name,
        filename="test.py",
        line_number=10,
        code_snippet="def test(): pass",
        description=pattern.description,
        symptoms=pattern.symptoms,
        optimization_technique=pattern.optimization_technique,
        potential_speedup=pattern.potential_speedup,
        metadata={}
    )


# ============================================================================
# TEST PERFORMANCE PATTERNS (12 TOTAL)
# ============================================================================

class TestPerformancePatterns:
    """Test performance pattern library"""

    def test_total_pattern_count(self):
        """Test that we have 12 total patterns (6 original + 6 new)"""
        print("\n[TEST 1] Verifying total pattern count...")

        assert len(PERFORMANCE_PATTERNS) == 12, "Should have 12 patterns total"

        # Original 6 patterns (Phase 2)
        assert "NESTED_LOOPS" in PERFORMANCE_PATTERNS
        assert "EXPENSIVE_LOOP_OPS" in PERFORMANCE_PATTERNS
        assert "EXCESSIVE_ALLOC" in PERFORMANCE_PATTERNS
        assert "LARGE_RESULT_SET" in PERFORMANCE_PATTERNS
        assert "DEEP_RECURSION" in PERFORMANCE_PATTERNS
        assert "INEFFICIENT_DS" in PERFORMANCE_PATTERNS

        # New 6 patterns (Phase 5)
        assert "N_PLUS_ONE" in PERFORMANCE_PATTERNS
        assert "MISSING_INDEX" in PERFORMANCE_PATTERNS
        assert "SYNC_IO_LOOP" in PERFORMANCE_PATTERNS
        assert "STRING_CONCAT_LOOP" in PERFORMANCE_PATTERNS
        assert "UNBOUNDED_QUERY" in PERFORMANCE_PATTERNS
        assert "LOCK_CONTENTION" in PERFORMANCE_PATTERNS

        print(f"[PASS] All 12 patterns present: {list(PERFORMANCE_PATTERNS.keys())}")

    def test_n_plus_one_pattern(self):
        """Test N+1 Query pattern"""
        print("\n[TEST 2] Testing N+1 Query pattern...")

        pattern = PERFORMANCE_PATTERNS["N_PLUS_ONE"]

        assert pattern.id == "N_PLUS_ONE_001"
        assert pattern.name == "N+1 Query Problem"
        assert pattern.category == BottleneckCategory.DATABASE
        assert pattern.severity == BottleneckSeverity.CRITICAL
        assert "N+1" in pattern.description or "N+1" in pattern.name
        assert pattern.cpgql_query is not None
        assert len(pattern.symptoms) > 0

        print(f"[PASS] N+1 pattern: {pattern.name}, severity={pattern.severity.value}")

    def test_missing_index_pattern(self):
        """Test Missing Database Index pattern"""
        print("\n[TEST 3] Testing Missing Index pattern...")

        pattern = PERFORMANCE_PATTERNS["MISSING_INDEX"]

        assert pattern.id == "MISSING_INDEX_001"
        assert pattern.category == BottleneckCategory.DATABASE
        assert pattern.severity == BottleneckSeverity.HIGH
        assert "index" in pattern.name.lower()

        print(f"[PASS] Missing Index pattern: {pattern.name}")

    def test_sync_io_pattern(self):
        """Test Synchronous I/O in Loops pattern"""
        print("\n[TEST 4] Testing Sync I/O pattern...")

        pattern = PERFORMANCE_PATTERNS["SYNC_IO_LOOP"]

        assert pattern.id == "SYNC_IO_LOOP_001"
        assert pattern.category == BottleneckCategory.IO
        assert pattern.severity == BottleneckSeverity.CRITICAL
        assert "synchronous" in pattern.name.lower() or "sync" in pattern.name.lower()

        print(f"[PASS] Sync I/O pattern: {pattern.name}")

    def test_string_concat_pattern(self):
        """Test String Concatenation in Loops pattern"""
        print("\n[TEST 5] Testing String Concat pattern...")

        pattern = PERFORMANCE_PATTERNS["STRING_CONCAT_LOOP"]

        assert pattern.id == "STRING_CONCAT_LOOP_001"
        assert pattern.category == BottleneckCategory.MEMORY
        assert pattern.severity == BottleneckSeverity.HIGH
        assert "string" in pattern.name.lower()

        print(f"[PASS] String Concat pattern: {pattern.name}")

    def test_unbounded_query_pattern(self):
        """Test Unbounded Database Query pattern"""
        print("\n[TEST 6] Testing Unbounded Query pattern...")

        pattern = PERFORMANCE_PATTERNS["UNBOUNDED_QUERY"]

        assert pattern.id == "UNBOUNDED_QUERY_001"
        assert pattern.category == BottleneckCategory.DATABASE
        assert pattern.severity == BottleneckSeverity.HIGH
        assert "unbounded" in pattern.name.lower()

        print(f"[PASS] Unbounded Query pattern: {pattern.name}")

    def test_lock_contention_pattern(self):
        """Test Lock Contention pattern"""
        print("\n[TEST 7] Testing Lock Contention pattern...")

        pattern = PERFORMANCE_PATTERNS["LOCK_CONTENTION"]

        assert pattern.id == "LOCK_CONTENTION_001"
        assert pattern.category == BottleneckCategory.CONCURRENCY
        assert pattern.severity == BottleneckSeverity.CRITICAL
        assert "lock" in pattern.name.lower() or "contention" in pattern.name.lower()

        print(f"[PASS] Lock Contention pattern: {pattern.name}")

    def test_pattern_severity_distribution(self):
        """Test that patterns have appropriate severity distribution"""
        print("\n[TEST 8] Testing pattern severity distribution...")

        by_severity = {}
        for pattern in PERFORMANCE_PATTERNS.values():
            severity = pattern.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        assert by_severity.get('critical', 0) > 0, "Should have critical patterns"
        assert by_severity.get('high', 0) > 0, "Should have high severity patterns"

        print(f"[PASS] Severity distribution: {by_severity}")


# ============================================================================
# TEST PERFORMANCE PROFILER
# ============================================================================

class TestPerformanceProfiler:
    """Test Performance Profiler agent"""

    def test_profile_all_bottlenecks(self):
        """Test profiling all bottleneck patterns"""
        print("\n[TEST 9] Testing profile_all_bottlenecks...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {'id': 1, 'method_name': 'slow_method', 'filename': 'test.py', 'line_number': 10}
        ])

        profiler = PerformanceProfiler(mock_cpg)
        findings = profiler.profile_all_bottlenecks(limit_per_pattern=5)

        assert isinstance(findings, list)
        # Should find some results across 12 patterns
        assert len(findings) > 0

        print(f"[PASS] Found {len(findings)} bottlenecks across 12 patterns")

    def test_profile_specific_pattern(self):
        """Test profiling a specific pattern"""
        print("\n[TEST 10] Testing profile_pattern for N+1 Query...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'fetch_orders',
                'filename': 'orders.py',
                'line_number': 25,
                'db_call_count': 5
            }
        ])

        profiler = PerformanceProfiler(mock_cpg)
        pattern = PERFORMANCE_PATTERNS["N_PLUS_ONE"]
        findings = profiler.profile_pattern(pattern, limit=10)

        assert len(findings) == 1
        assert findings[0].pattern_id == "N_PLUS_ONE_001"
        assert findings[0].method_name == "fetch_orders"
        assert findings[0].severity == "critical"

        print(f"[PASS] Detected N+1 pattern: {findings[0].method_name}")

    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation"""
        print("\n[TEST 11] Testing calculate_performance_metrics...")

        profiler = PerformanceProfiler(create_mock_cpg())

        findings = [
            create_test_finding("N_PLUS_ONE_001", "critical", "method1"),
            create_test_finding("MISSING_INDEX_001", "high", "method2"),
            create_test_finding("STRING_CONCAT_LOOP_001", "high", "method3"),
            create_test_finding("DEEP_RECURSION_001", "medium", "method4"),
        ]

        metrics = profiler.calculate_performance_metrics(findings)

        assert metrics['total_bottlenecks'] == 4
        assert metrics['critical_count'] == 1
        assert metrics['high_count'] == 2
        assert 'by_severity' in metrics
        assert 'by_category' in metrics

        print(f"[PASS] Metrics: {metrics['total_bottlenecks']} bottlenecks, "
              f"{metrics['critical_count']} critical")

    # ========================================================================
    # PHASE 5 ENHANCEMENT TESTS: cProfile Integration
    # ========================================================================

    def test_profile_function_with_cprofile(self):
        """Test real function profiling with cProfile"""
        print("\n[TEST 12] Testing profile_function_with_cprofile...")

        profiler = PerformanceProfiler(create_mock_cpg())

        def test_function(n):
            """Test function that does some work"""
            total = 0
            for i in range(n):
                total += i * i
            return total

        result, profiling_result = profiler.profile_function_with_cprofile(test_function, 1000)

        assert result == sum(i * i for i in range(1000))
        assert isinstance(profiling_result, ProfilingResult)
        assert profiling_result.function_name == "test_function"
        assert profiling_result.total_time >= 0  # May be 0.0 for very fast functions
        assert profiling_result.bottleneck_score >= 0
        assert profiling_result.bottleneck_score <= 1.0

        print(f"[PASS] cProfile: {profiling_result.function_name}, "
              f"time={profiling_result.total_time:.6f}s")

    def test_profile_memory_usage(self):
        """Test memory profiling with tracemalloc"""
        print("\n[TEST 13] Testing profile_memory_usage...")

        profiler = PerformanceProfiler(create_mock_cpg())

        def memory_intensive_function():
            """Function that allocates memory"""
            data = []
            for i in range(1000):
                data.append([0] * 100)  # Allocate lists
            return len(data)

        result, memory_result = profiler.profile_memory_usage(memory_intensive_function)

        assert result == 1000
        assert isinstance(memory_result, MemoryProfilingResult)
        assert memory_result.function_name == "memory_intensive_function"
        assert memory_result.memory_usage_mb >= 0  # Should have used some memory
        assert memory_result.allocations > 0
        assert memory_result.allocation_rate >= 0

        print(f"[PASS] Memory profile: {memory_result.memory_usage_mb:.4f}MB, "
              f"{memory_result.allocations} allocations")

    def test_create_performance_baseline(self):
        """Test creating performance baseline"""
        print("\n[TEST 14] Testing create_performance_baseline...")

        profiler = PerformanceProfiler(create_mock_cpg())

        baseline = profiler.create_performance_baseline(
            method_name="process_data",
            execution_time_ms=150.5,
            memory_usage_mb=25.3,
            cpu_usage_percent=45.2
        )

        assert isinstance(baseline, PerformanceBaseline)
        assert baseline.method_name == "process_data"
        assert baseline.execution_time_ms == 150.5
        assert baseline.memory_usage_mb == 25.3
        assert baseline.cpu_usage_percent == 45.2
        assert baseline.timestamp is not None

        print(f"[PASS] Created baseline for {baseline.method_name}: "
              f"{baseline.execution_time_ms}ms")

    def test_compare_with_baseline_regression(self):
        """Test regression detection with baseline comparison"""
        print("\n[TEST 15] Testing compare_with_baseline (regression)...")

        profiler = PerformanceProfiler(create_mock_cpg())

        # Create baseline
        baseline = profiler.create_performance_baseline(
            method_name="fetch_users",
            execution_time_ms=100.0,
            memory_usage_mb=10.0
        )

        # Compare with slower performance (regression)
        trend = profiler.compare_with_baseline(
            baseline=baseline,
            current_execution_time_ms=150.0,  # 50% slower
            current_memory_mb=12.0,
            regression_threshold_percent=10.0
        )

        assert isinstance(trend, PerformanceTrend)
        assert trend.method_name == "fetch_users"
        assert trend.time_delta_percent == 50.0  # 50% slower
        assert trend.trend_direction == "degrading"
        assert trend.regression_detected is True
        assert trend.severity in ["critical", "high", "medium"]

        print(f"[PASS] Regression detected: {trend.time_delta_percent:+.1f}%, "
              f"severity={trend.severity}")

    def test_compare_with_baseline_improvement(self):
        """Test improvement detection with baseline comparison"""
        print("\n[TEST 16] Testing compare_with_baseline (improvement)...")

        profiler = PerformanceProfiler(create_mock_cpg())

        baseline = profiler.create_performance_baseline(
            method_name="optimize_query",
            execution_time_ms=200.0
        )

        # Compare with faster performance (improvement)
        trend = profiler.compare_with_baseline(
            baseline=baseline,
            current_execution_time_ms=120.0,  # 40% faster
            regression_threshold_percent=10.0
        )

        assert trend.time_delta_percent == -40.0  # 40% improvement
        assert trend.trend_direction == "improving"
        assert trend.regression_detected is False

        print(f"[PASS] Improvement detected: {trend.time_delta_percent:+.1f}%, "
              f"trend={trend.trend_direction}")

    def test_compare_with_baseline_stable(self):
        """Test stable performance detection"""
        print("\n[TEST 17] Testing compare_with_baseline (stable)...")

        profiler = PerformanceProfiler(create_mock_cpg())

        baseline = profiler.create_performance_baseline(
            method_name="stable_method",
            execution_time_ms=100.0
        )

        # Small change within threshold
        trend = profiler.compare_with_baseline(
            baseline=baseline,
            current_execution_time_ms=105.0,  # 5% slower (within 10% threshold)
            regression_threshold_percent=10.0
        )

        assert trend.time_delta_percent == 5.0
        assert trend.trend_direction == "stable"
        assert trend.regression_detected is False

        print(f"[PASS] Stable performance: {trend.time_delta_percent:+.1f}%, "
              f"trend={trend.trend_direction}")


# ============================================================================
# TEST RESOURCE ANALYZER
# ============================================================================

class TestResourceAnalyzer:
    """Test Resource Analyzer agent"""

    def test_analyze_method_resources(self):
        """Test analyzing method resource usage"""
        print("\n[TEST 18] Testing analyze_method_resources...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'name': 'process_batch',
                'filename': 'batch.py',
                'cyclomatic_complexity': 15,
                'call_count': 8
            }
        ])

        analyzer = ResourceAnalyzer(mock_cpg)
        analysis = analyzer.analyze_method_resources("process_batch")

        assert isinstance(analysis, ResourceUsage)
        assert analysis.method_name == "process_batch"
        assert analysis.complexity_score == 15
        assert analysis.resource_intensity >= 0
        assert analysis.resource_intensity <= 1.0

        print(f"[PASS] Resource analysis: {analysis.method_name}, "
              f"complexity={analysis.complexity_score}")


# ============================================================================
# TEST OPTIMIZATION ADVISOR
# ============================================================================

class TestOptimizationAdvisor:
    """Test Optimization Advisor agent"""

    def test_create_optimization_plan(self):
        """Test creating optimization plan"""
        print("\n[TEST 19] Testing create_optimization_plan...")

        advisor = OptimizationAdvisor()

        findings = [
            create_test_finding("N_PLUS_ONE_001", "critical", "fetch_data"),
            create_test_finding("STRING_CONCAT_LOOP_001", "high", "build_report"),
        ]

        recommendations = advisor.create_optimization_plan(findings, resource_analyses=[])

        assert isinstance(recommendations, list)
        assert len(recommendations) == 2

        for rec in recommendations:
            assert isinstance(rec, OptimizationRecommendation)
            assert rec.priority >= 1
            assert rec.priority <= 10
            assert rec.risk_level in ['low', 'medium', 'high']
            assert len(rec.optimization_steps) > 0

        print(f"[PASS] Created {len(recommendations)} recommendations")

    def test_priority_calculation(self):
        """Test optimization priority calculation"""
        print("\n[TEST 20] Testing priority calculation...")

        advisor = OptimizationAdvisor()

        # Critical severity should have higher priority
        critical_finding = create_test_finding("N_PLUS_ONE_001", "critical", "method1")
        low_finding = create_test_finding("DEEP_RECURSION_001", "low", "method2")

        critical_recs = advisor.create_optimization_plan([critical_finding], resource_analyses=[])
        low_recs = advisor.create_optimization_plan([low_finding], resource_analyses=[])

        # Critical should have higher priority (higher number = higher priority in this implementation)
        assert critical_recs[0].priority > low_recs[0].priority

        print(f"[PASS] Priority: critical={critical_recs[0].priority}, "
              f"low={low_recs[0].priority}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestScenario6Integration:
    """Integration tests for complete Scenario 6 workflow"""

    def test_full_performance_analysis_workflow(self):
        """Test complete performance analysis workflow"""
        print("\n[TEST 21] Testing full performance analysis workflow...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': i,
                'method_name': f'method{i}',
                'filename': f'file{i}.py',
                'line_number': i * 10,
                'cyclomatic_complexity': 15,
                'call_count': 5
            }
            for i in range(3)
        ])

        # Step 1: Profile bottlenecks
        profiler = PerformanceProfiler(mock_cpg)
        findings = profiler.profile_all_bottlenecks(limit_per_pattern=3)

        assert len(findings) > 0
        print(f"  Step 1: Found {len(findings)} bottlenecks")

        # Step 2: Calculate metrics
        metrics = profiler.calculate_performance_metrics(findings)

        assert metrics['total_bottlenecks'] > 0
        print(f"  Step 2: Metrics calculated: {metrics['total_bottlenecks']} total")

        # Step 3: Create recommendations
        advisor = OptimizationAdvisor()
        recommendations = advisor.create_optimization_plan(
            findings[:5],
            resource_analyses=[]
        )

        assert len(recommendations) > 0
        print(f"  Step 3: Created {len(recommendations)} recommendations")

        print(f"[PASS] Complete workflow: {len(findings)} bottlenecks -> "
              f"{len(recommendations)} recommendations")

    def test_profiling_integration(self):
        """Test profiling integration with real functions"""
        print("\n[TEST 22] Testing profiling integration...")

        profiler = PerformanceProfiler(create_mock_cpg())

        def compute_fibonacci(n):
            """Simple fibonacci for testing"""
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(n - 1):
                a, b = b, a + b
            return b

        # Profile with cProfile
        result1, cpu_profile = profiler.profile_function_with_cprofile(compute_fibonacci, 100)

        # Profile with memory tracking
        result2, mem_profile = profiler.profile_memory_usage(compute_fibonacci, 100)

        assert result1 == result2  # Same result
        assert cpu_profile.total_time >= 0  # May be 0.0 for very fast functions
        assert mem_profile.allocations >= 0

        print(f"[PASS] Profiling integration: CPU={cpu_profile.total_time:.6f}s, "
              f"Memory={mem_profile.memory_usage_mb:.6f}MB")

    def test_baseline_and_regression_workflow(self):
        """Test baseline creation and regression detection workflow"""
        print("\n[TEST 23] Testing baseline and regression workflow...")

        profiler = PerformanceProfiler(create_mock_cpg())

        # Create baseline from initial run
        baseline = profiler.create_performance_baseline(
            method_name="api_endpoint",
            execution_time_ms=250.0,
            memory_usage_mb=15.0
        )

        # Simulate performance degradation over time
        scenarios = [
            ("stable", 255.0, False),    # 2% slower - stable
            ("degrading", 300.0, True),  # 20% slower - regression
            ("critical", 450.0, True),   # 80% slower - critical regression
        ]

        for scenario_name, exec_time, should_regress in scenarios:
            trend = profiler.compare_with_baseline(
                baseline=baseline,
                current_execution_time_ms=exec_time,
                regression_threshold_percent=10.0
            )

            assert trend.regression_detected == should_regress
            print(f"  Scenario '{scenario_name}': {trend.time_delta_percent:+.1f}%, "
                  f"regression={trend.regression_detected}")

        print(f"[PASS] Baseline workflow: tested {len(scenarios)} scenarios")

    def test_empty_results_handling(self):
        """Test handling of empty results"""
        print("\n[TEST 24] Testing empty results handling...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[])

        profiler = PerformanceProfiler(mock_cpg)
        findings = profiler.profile_all_bottlenecks()

        assert isinstance(findings, list)
        assert len(findings) == 0

        metrics = profiler.calculate_performance_metrics(findings)
        assert metrics['total_bottlenecks'] == 0

        print("[PASS] Empty results handled correctly")

    def test_pattern_coverage(self):
        """Test that all 12 patterns can be detected"""
        print("\n[TEST 25] Testing all 12 patterns are detectable...")

        mock_cpg = create_mock_cpg()
        profiler = PerformanceProfiler(mock_cpg)

        detected_patterns = set()

        for pattern_name, pattern in PERFORMANCE_PATTERNS.items():
            # Mock data for this pattern
            mock_cpg.execute_query = Mock(return_value=[
                {
                    'id': 1,
                    'method_name': f'test_{pattern_name}',
                    'filename': 'test.py',
                    'line_number': 10
                }
            ])

            findings = profiler.profile_pattern(pattern, limit=5)

            if len(findings) > 0:
                detected_patterns.add(pattern_name)

        # All 12 patterns should be detectable
        assert len(detected_patterns) == 12

        print(f"[PASS] All 12 patterns detectable: {sorted(detected_patterns)}")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SCENARIO 6 ENHANCED TEST SUITE")
    print("Testing 12 performance patterns + profiling features")
    print("=" * 70)

    pytest.main([__file__, "-v", "-s"])
