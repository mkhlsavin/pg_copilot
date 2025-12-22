"""
Performance Profiler Agent

Detects performance bottlenecks using pattern library.
Enhanced with cProfile integration and SCC-based cycle detection.
"""
import logging
import cProfile
import pstats
import io
import tracemalloc
import time
from typing import List, Any, Optional, Tuple, Callable
from datetime import datetime

from .models import (
    BottleneckFinding,
    ProfilingResult,
    MemoryProfilingResult,
    PerformanceBaseline,
    PerformanceTrend,
)
from ..performance_patterns import (
    PerformancePattern,
    PERFORMANCE_PATTERNS,
    BottleneckSeverity,
    BottleneckCategory,
    get_patterns_by_category,
)
from ...services.cpg_query_service import CPGQueryService
from ...analysis.call_graph_analyzer import CallGraphAnalyzer

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """
    Detects performance bottlenecks using pattern library

    Responsibilities:
    - Execute CPGQL queries from performance patterns
    - Identify bottlenecks
    - Calculate performance metrics
    - Rank findings by severity and impact

    Phase 3.1 Enhancement:
    - Precise cycle detection using Tarjan's SCC algorithm
    """

    def __init__(self, cpg_service: Optional[CPGQueryService] = None):
        self.cpg = cpg_service
        self._own_cpg = cpg_service is None
        self.call_graph_analyzer = None
        if cpg_service:
            self.call_graph_analyzer = CallGraphAnalyzer(cpg_service)

    def __enter__(self):
        if self._own_cpg:
            self.cpg = CPGQueryService()
            self.cpg.__enter__()
            self.call_graph_analyzer = CallGraphAnalyzer(self.cpg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_cpg and self.cpg:
            self.cpg.__exit__(exc_type, exc_val, exc_tb)

    def profile_all_bottlenecks(self, limit_per_pattern: int = 30) -> List[BottleneckFinding]:
        """
        Detect all performance bottlenecks using all patterns.

        Args:
            limit_per_pattern: Max findings per pattern

        Returns:
            List of bottleneck findings sorted by severity
        """
        logger.info("Starting comprehensive performance profiling")
        all_findings = []

        for pattern_name, pattern in PERFORMANCE_PATTERNS.items():
            try:
                findings = self.profile_pattern(pattern, limit_per_pattern)
                all_findings.extend(findings)
                logger.info(f"Pattern {pattern_name}: found {len(findings)} bottlenecks")
            except Exception as e:
                logger.error(f"Error profiling pattern {pattern_name}: {e}")

        # Sort by severity (critical first)
        severity_order = {
            BottleneckSeverity.CRITICAL.value: 0,
            BottleneckSeverity.HIGH.value: 1,
            BottleneckSeverity.MEDIUM.value: 2,
            BottleneckSeverity.LOW.value: 3,
            BottleneckSeverity.INFO.value: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        logger.info(f"Total bottlenecks found: {len(all_findings)}")
        return all_findings

    def profile_pattern(self, pattern: PerformancePattern, limit: int = 30) -> List[BottleneckFinding]:
        """
        Detect a specific bottleneck pattern.

        Args:
            pattern: Performance pattern to detect
            limit: Max findings to return

        Returns:
            List of bottleneck findings
        """
        try:
            results = self.cpg.execute_query(pattern.cpgql_query)

            findings = []
            for idx, row in enumerate(results[:limit]):
                finding = BottleneckFinding(
                    finding_id=f"{pattern.id}_{idx:03d}",
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    category=pattern.category.value,
                    severity=pattern.severity.value,
                    method_id=row.get('id', 0),
                    method_name=row.get('method_name', row.get('filename', 'unknown')),
                    filename=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    code_snippet='',
                    description=pattern.description,
                    symptoms=pattern.symptoms,
                    optimization_technique=pattern.optimization_technique,
                    potential_speedup=pattern.potential_speedup,
                    metadata=row
                )
                findings.append(finding)

            return findings

        except Exception as e:
            logger.error(f"Error executing pattern {pattern.id}: {e}")
            return []

    def profile_by_category(
        self,
        category: BottleneckCategory,
        limit: int = 50
    ) -> List[BottleneckFinding]:
        """Profile bottlenecks in a specific category."""
        patterns = get_patterns_by_category(category)
        findings = []

        for pattern in patterns:
            pattern_findings = self.profile_pattern(pattern, limit)
            findings.extend(pattern_findings)

        return findings

    def calculate_performance_metrics(self, findings: List[BottleneckFinding]) -> dict:
        """
        Calculate performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        if not findings:
            return {
                'total_bottlenecks': 0,
                'by_severity': {},
                'by_category': {},
                'critical_count': 0
            }

        by_severity = {}
        for severity in BottleneckSeverity:
            count = sum(1 for f in findings if f.severity == severity.value)
            if count > 0:
                by_severity[severity.value] = count

        by_category = {}
        for category in BottleneckCategory:
            count = sum(1 for f in findings if f.category == category.value)
            if count > 0:
                by_category[category.value] = count

        return {
            'total_bottlenecks': len(findings),
            'by_severity': by_severity,
            'by_category': by_category,
            'critical_count': by_severity.get('critical', 0),
            'high_count': by_severity.get('high', 0)
        }

    # ========================================================================
    # PHASE 5 ENHANCEMENT: REAL PROFILING INTEGRATION
    # ========================================================================

    def profile_function_with_cprofile(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, ProfilingResult]:
        """
        Profile a function using cProfile (Phase 5 Enhancement).

        Args:
            func: Function to profile
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Tuple of (function_result, ProfilingResult)
        """
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        profiler.disable()

        # Analyze profiling results
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')

        func_stats = {}
        for func_key, (cc, nc, tt, ct, callers) in stats.stats.items():
            func_name = f"{func_key[0]}:{func_key[1]}:{func_key[2]}"
            func_stats[func_name] = {
                'calls': cc,
                'total_time': tt,
                'cumulative_time': ct,
                'time_per_call': tt / cc if cc > 0 else 0
            }

        func_name = getattr(func, '__name__', str(func))
        profiling_result = ProfilingResult(
            profile_id=f"PROFILE_{func_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            function_name=func_name,
            total_calls=1,
            total_time=end_time - start_time,
            cumulative_time=end_time - start_time,
            time_per_call=end_time - start_time,
            callers=[],
            bottleneck_score=min((end_time - start_time) / 10.0, 1.0),
            metadata={'func_stats': func_stats, 'profiler_output': stream.getvalue()}
        )

        logger.info(f"Profiled {func_name}: {end_time - start_time:.4f}s")
        return result, profiling_result

    def profile_memory_usage(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, MemoryProfilingResult]:
        """
        Profile memory usage of a function (Phase 5 Enhancement).

        Args:
            func: Function to profile
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (function_result, MemoryProfilingResult)
        """
        tracemalloc.start()
        start_time = time.time()

        current, peak = tracemalloc.get_traced_memory()
        initial_memory = current

        result = func(*args, **kwargs)

        current, peak = tracemalloc.get_traced_memory()
        final_memory = current

        end_time = time.time()
        execution_time = end_time - start_time

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        total_allocations = sum(stat.count for stat in top_stats)

        tracemalloc.stop()

        func_name = getattr(func, '__name__', str(func))
        memory_result = MemoryProfilingResult(
            profile_id=f"MEMORY_{func_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            function_name=func_name,
            memory_usage_mb=(final_memory - initial_memory) / (1024 * 1024),
            memory_peak_mb=peak / (1024 * 1024),
            allocations=total_allocations,
            deallocations=0,
            net_allocations=total_allocations,
            allocation_rate=total_allocations / execution_time if execution_time > 0 else 0,
            metadata={
                'initial_memory_mb': initial_memory / (1024 * 1024),
                'final_memory_mb': final_memory / (1024 * 1024),
                'top_allocations': [(str(stat), stat.size, stat.count) for stat in top_stats[:10]]
            }
        )

        logger.info(f"Memory profile {func_name}: {memory_result.memory_usage_mb:.2f}MB, "
                   f"{total_allocations} allocations")
        return result, memory_result

    def create_performance_baseline(
        self,
        method_name: str,
        execution_time_ms: float,
        memory_usage_mb: float = 0.0,
        cpu_usage_percent: float = 0.0
    ) -> PerformanceBaseline:
        """
        Create a performance baseline for future comparison (Phase 5 Enhancement).
        """
        baseline = PerformanceBaseline(
            baseline_id=f"BASELINE_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            method_name=method_name,
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            metadata={}
        )
        logger.info(f"Created baseline for {method_name}: {execution_time_ms:.2f}ms")
        return baseline

    def compare_with_baseline(
        self,
        baseline: PerformanceBaseline,
        current_execution_time_ms: float,
        current_memory_mb: float = 0.0,
        current_cpu_percent: float = 0.0,
        regression_threshold_percent: float = 10.0
    ) -> PerformanceTrend:
        """
        Compare current performance with baseline (Phase 5 Enhancement).
        """
        current_baseline = PerformanceBaseline(
            baseline_id=f"CURRENT_{baseline.method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            method_name=baseline.method_name,
            execution_time_ms=current_execution_time_ms,
            memory_usage_mb=current_memory_mb,
            cpu_usage_percent=current_cpu_percent,
            metadata={}
        )

        time_delta = ((current_execution_time_ms - baseline.execution_time_ms) /
                     baseline.execution_time_ms * 100 if baseline.execution_time_ms > 0 else 0)

        memory_delta = ((current_memory_mb - baseline.memory_usage_mb) /
                       baseline.memory_usage_mb * 100 if baseline.memory_usage_mb > 0 else 0)

        if time_delta > regression_threshold_percent:
            trend_direction = "degrading"
            regression_detected = True
        elif time_delta < -regression_threshold_percent:
            trend_direction = "improving"
            regression_detected = False
        else:
            trend_direction = "stable"
            regression_detected = False

        if abs(time_delta) > 50:
            severity = "critical"
        elif abs(time_delta) > 25:
            severity = "high"
        elif abs(time_delta) > 10:
            severity = "medium"
        else:
            severity = "low"

        trend = PerformanceTrend(
            trend_id=f"TREND_{baseline.method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            method_name=baseline.method_name,
            baseline=baseline,
            current=current_baseline,
            time_delta_percent=time_delta,
            memory_delta_percent=memory_delta,
            trend_direction=trend_direction,
            regression_detected=regression_detected,
            severity=severity
        )

        if regression_detected:
            logger.warning(f"Performance regression detected for {baseline.method_name}: "
                          f"{time_delta:+.1f}% slower")
        else:
            logger.info(f"Performance trend for {baseline.method_name}: {trend_direction} "
                       f"({time_delta:+.1f}%)")

        return trend

    # ========================================================================
    # PHASE 3.1 ENHANCEMENT: SCC-BASED CYCLE DETECTION
    # ========================================================================

    def detect_cycles_scc(self) -> List[BottleneckFinding]:
        """
        Detect recursive calls and cycles using Tarjan's SCC algorithm.

        Uses strongly connected components (SCC) for precise cycle detection.
        """
        if not self.call_graph_analyzer:
            logger.warning("CallGraphAnalyzer not initialized, cannot detect cycles via SCC")
            return []

        findings = []

        try:
            logger.info("Computing strongly connected components for cycle detection")

            sccs = self.call_graph_analyzer.compute_strongly_connected_components()

            if not sccs:
                logger.info("No cycles detected (no SCCs found)")
                return []

            cycles = [scc for scc in sccs if len(scc) > 1]

            logger.info(f"Found {len(cycles)} cycles via SCC (Tarjan's algorithm)")

            for idx, cycle_methods in enumerate(cycles):
                cycle_size = len(cycle_methods)

                if cycle_size > 10:
                    severity = BottleneckSeverity.CRITICAL.value
                    category = "Large mutual recursion - high risk"
                elif cycle_size > 5:
                    severity = BottleneckSeverity.HIGH.value
                    category = "Moderate mutual recursion"
                else:
                    severity = BottleneckSeverity.MEDIUM.value
                    category = "Small mutual recursion"

                sample_methods = list(cycle_methods)[:5]
                method_list = ", ".join(sample_methods)
                if cycle_size > 5:
                    method_list += f" (and {cycle_size - 5} more)"

                finding = BottleneckFinding(
                    finding_id=f"cycle_scc_{idx:03d}",
                    pattern_id="mutual_recursion_scc",
                    pattern_name="Mutual Recursion (SCC Detection)",
                    category=BottleneckCategory.ALGORITHMIC.value,
                    severity=severity,
                    method_id=0,
                    method_name=sample_methods[0] if sample_methods else "unknown",
                    filename="",
                    line_number=0,
                    code_snippet="",
                    description=f"{category} involving {cycle_size} methods: {method_list}",
                    symptoms=[
                        f"Strongly connected component with {cycle_size} methods",
                        "Methods call each other directly or indirectly",
                        "May cause stack overflow on deep recursion",
                        "Difficult to test and maintain"
                    ],
                    optimization_technique=(
                        "1. Break cycle by introducing interfaces/abstractions\n"
                        "2. Use iterative approach instead of recursion\n"
                        "3. Add memoization to avoid redundant calls\n"
                        "4. Consider breaking into separate modules"
                    ),
                    potential_speedup="10-50x (if recursion depth is high)",
                    metadata={
                        'detection_algorithm': 'tarjan_scc',
                        'cycle_size': cycle_size,
                        'all_methods': list(cycle_methods),
                        'scc_index': idx
                    }
                )
                findings.append(finding)

            logger.info(f"Created {len(findings)} bottleneck findings from SCC cycle detection")

        except Exception as e:
            logger.error(f"SCC cycle detection failed: {e}", exc_info=True)

        return findings

    def identify_bottleneck_methods(self) -> List[BottleneckFinding]:
        """
        Identify performance bottlenecks using betweenness centrality.

        High betweenness centrality indicates methods that many execution paths flow through.
        """
        if not self.call_graph_analyzer:
            logger.warning("CallGraphAnalyzer not initialized, cannot detect bottlenecks via betweenness")
            return []

        findings = []

        try:
            logger.info("Computing betweenness centrality for bottleneck identification")

            betweenness_results = self.call_graph_analyzer.compute_betweenness_centrality(
                sample_size=1000,
                top_n=30
            )

            if not betweenness_results:
                logger.info("No betweenness results (empty graph or computation failed)")
                return []

            logger.info(f"Found {len(betweenness_results)} methods with betweenness scores")

            for idx, result in enumerate(betweenness_results[:20]):
                percentile = result.get('percentile', 0)

                if percentile > 95:
                    severity = BottleneckSeverity.CRITICAL.value
                    priority = "critical"
                    speedup = "50-100x potential (many paths)"
                elif percentile > 90:
                    severity = BottleneckSeverity.HIGH.value
                    priority = "high"
                    speedup = "20-50x potential"
                else:
                    severity = BottleneckSeverity.MEDIUM.value
                    priority = "medium"
                    speedup = "10-20x potential"

                finding = BottleneckFinding(
                    finding_id=f"bottleneck_betweenness_{idx:03d}",
                    pattern_id="high_traffic_method",
                    pattern_name="High-Traffic Method (Betweenness)",
                    category=BottleneckCategory.ALGORITHMIC.value,
                    severity=severity,
                    method_id=0,
                    method_name=result['method_name'],
                    filename="",
                    line_number=0,
                    code_snippet="",
                    description=(
                        f"High-traffic method with betweenness score {result['betweenness_score']:.6f} "
                        f"(top {100 - percentile:.1f}%). Many execution paths flow through this method."
                    ),
                    symptoms=[
                        f"Betweenness centrality: {result['betweenness_score']:.6f}",
                        f"Percentile: {percentile:.1f}% (top {100 - percentile:.1f}%)",
                        "Many execution paths flow through this method",
                        "Optimizing this method will improve many code paths"
                    ],
                    optimization_technique=(
                        "1. Profile this method with real workload data\n"
                        "2. Look for algorithmic improvements (O(n²) → O(n log n))\n"
                        "3. Add caching/memoization for repeated calls\n"
                        "4. Consider parallelization if applicable\n"
                        "5. Optimize hot loops and data structures"
                    ),
                    potential_speedup=speedup,
                    metadata={
                        'detection_algorithm': 'brandes_betweenness',
                        'betweenness_score': result['betweenness_score'],
                        'percentile': percentile,
                        'optimization_priority': priority,
                        'expected_impact': 'High - affects many code paths'
                    }
                )
                findings.append(finding)

            logger.info(f"Created {len(findings)} bottleneck findings from betweenness analysis")

        except Exception as e:
            logger.error(f"Betweenness bottleneck detection failed: {e}", exc_info=True)

        return findings


__all__ = ['PerformanceProfiler']
