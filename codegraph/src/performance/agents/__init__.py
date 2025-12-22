"""Performance Agents Package.

Provides specialized agents for performance analysis:
- PerformanceProfiler: Detect bottlenecks using pattern library and cProfile
- ResourceAnalyzer: Analyze resource usage patterns
- OptimizationAdvisor: Provide optimization recommendations

Also provides data structures for performance analysis results.
"""

from .models import (
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    PerformanceReport,
    ProfilingResult,
    MemoryProfilingResult,
    PerformanceBaseline,
    PerformanceTrend,
)
from .profiler import PerformanceProfiler
from .resource_analyzer import ResourceAnalyzer
from .optimizer import OptimizationAdvisor
from ...services.cpg_query_service import CPGQueryService


def run_complete_performance_analysis(
    limit_per_pattern: int = 20,
    resource_limit: int = 20
) -> PerformanceReport:
    """
    Run complete performance analysis using all agents

    Convenience function that orchestrates all three agents:
    1. PerformanceProfiler - detects bottlenecks
    2. ResourceAnalyzer - analyzes resource usage
    3. OptimizationAdvisor - creates optimization plan

    Args:
        limit_per_pattern: Maximum bottlenecks per pattern
        resource_limit: Maximum methods to analyze for resources

    Returns:
        Comprehensive PerformanceReport
    """
    with CPGQueryService() as cpg:
        # Agent 1: Profile bottlenecks
        profiler = PerformanceProfiler(cpg)
        findings = profiler.profile_all_bottlenecks(limit_per_pattern)

        # Agent 2: Analyze resources
        analyzer = ResourceAnalyzer(cpg)
        resource_analyses = analyzer.analyze_bulk_resources(findings, resource_limit)

        # Agent 3: Create optimization plan
        advisor = OptimizationAdvisor()
        recommendations = advisor.create_optimization_plan(findings, resource_analyses)
        report = advisor.generate_report(findings, resource_analyses, recommendations)

    return report


__all__ = [
    # Data models
    'BottleneckFinding',
    'ResourceUsage',
    'OptimizationRecommendation',
    'PerformanceReport',
    'ProfilingResult',
    'MemoryProfilingResult',
    'PerformanceBaseline',
    'PerformanceTrend',
    # Agents
    'PerformanceProfiler',
    'ResourceAnalyzer',
    'OptimizationAdvisor',
    # Utility
    'run_complete_performance_analysis',
]
