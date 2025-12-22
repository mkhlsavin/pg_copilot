# ============================================================================
# BACKWARD COMPATIBILITY FACADE
# ============================================================================
# This file is kept for backward compatibility.
# All functionality has been moved to src/performance/agents/ package.
#
# New code should import directly from the package:
#   from src.performance.agents import PerformanceProfiler, ResourceAnalyzer
# ============================================================================
"""
Performance Analysis Agents for Enhanced Performance Workflow

Backward compatibility facade - imports from agents package.
"""
from src.performance.agents import (
    # Data models
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    PerformanceReport,
    ProfilingResult,
    MemoryProfilingResult,
    PerformanceBaseline,
    PerformanceTrend,
    # Agents
    PerformanceProfiler,
    ResourceAnalyzer,
    OptimizationAdvisor,
    # Utility
    run_complete_performance_analysis,
)

__all__ = [
    'BottleneckFinding',
    'ResourceUsage',
    'OptimizationRecommendation',
    'PerformanceReport',
    'ProfilingResult',
    'MemoryProfilingResult',
    'PerformanceBaseline',
    'PerformanceTrend',
    'PerformanceProfiler',
    'ResourceAnalyzer',
    'OptimizationAdvisor',
    'run_complete_performance_analysis',
]
