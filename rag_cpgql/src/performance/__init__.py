"""
Performance Analysis Module

Provides performance bottleneck detection, resource analysis, and optimization tools.

Week 7: Enhanced Performance Analysis with Specialized Agents
- PerformanceProfiler: Detect bottlenecks using patterns
- ResourceAnalyzer: Analyze resource usage and impact
- OptimizationAdvisor: Create prioritized optimization plans

Phase 5 Enhancement: Production-Ready Performance Analysis
- Real profiling with cProfile and tracemalloc
- Performance baseline and regression detection
- 12 total performance patterns (6 original + 6 new)
- Memory profiling and trend analysis
"""

from .performance_patterns import (
    PerformancePattern,
    BottleneckSeverity,
    BottleneckCategory,
    PERFORMANCE_PATTERNS,
    get_pattern_by_id,
    get_patterns_by_category,
    get_patterns_by_severity,
    get_critical_patterns,
    get_all_cpgql_queries,
    get_pattern_summary,
    validate_pattern,
    validate_all_patterns,
)

from .performance_agents import (
    PerformanceProfiler,
    ResourceAnalyzer,
    OptimizationAdvisor,
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    PerformanceReport,
    run_complete_performance_analysis,
    # Phase 5 Enhancement: New data structures
    ProfilingResult,
    MemoryProfilingResult,
    PerformanceBaseline,
    PerformanceTrend,
)

__all__ = [
    # Patterns
    "PerformancePattern",
    "BottleneckSeverity",
    "BottleneckCategory",
    "PERFORMANCE_PATTERNS",
    "get_pattern_by_id",
    "get_patterns_by_category",
    "get_patterns_by_severity",
    "get_critical_patterns",
    "get_all_cpgql_queries",
    "get_pattern_summary",
    "validate_pattern",
    "validate_all_patterns",
    # Agents
    "PerformanceProfiler",
    "ResourceAnalyzer",
    "OptimizationAdvisor",
    # Data structures
    "BottleneckFinding",
    "ResourceUsage",
    "OptimizationRecommendation",
    "PerformanceReport",
    # Phase 5 Enhancement: Profiling data structures
    "ProfilingResult",
    "MemoryProfilingResult",
    "PerformanceBaseline",
    "PerformanceTrend",
    # Utilities
    "run_complete_performance_analysis",
]
