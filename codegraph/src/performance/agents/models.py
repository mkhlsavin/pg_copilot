"""
Performance Analysis Data Structures

Contains all dataclasses used by performance agents.
"""
from typing import Dict, List, Any
from dataclasses import dataclass, field


# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================

@dataclass
class BottleneckFinding:
    """Represents a detected performance bottleneck"""
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    symptoms: List[str]
    optimization_technique: str
    potential_speedup: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """Resource usage analysis for a method"""
    analysis_id: str
    method_name: str
    filename: str
    complexity_score: int  # Cyclomatic complexity
    call_count: int  # Number of calls this method makes
    estimated_memory_impact: str  # "low", "medium", "high"
    estimated_cpu_impact: str  # "low", "medium", "high"
    io_operations: int  # Number of I/O operations
    resource_intensity: float  # 0.0 to 1.0


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation for a bottleneck"""
    recommendation_id: str
    finding_id: str
    pattern_id: str
    optimization_steps: List[str]
    code_example: str
    estimated_speedup: str
    implementation_effort: str  # "low", "medium", "high"
    priority: int  # 1-10, higher = more important
    risk_level: str  # "low", "medium", "high"


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report"""
    report_id: str
    timestamp: str
    total_bottlenecks: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    findings: List[BottleneckFinding]
    resource_analyses: List[ResourceUsage]
    recommendations: List[OptimizationRecommendation]
    total_potential_speedup: str
    summary: str
    action_items: List[str]


# ============================================================================
# PHASE 5 ENHANCED DATA STRUCTURES
# ============================================================================

@dataclass
class ProfilingResult:
    """Results from cProfile profiling (Phase 5 Enhancement)"""
    profile_id: str
    function_name: str
    total_calls: int
    total_time: float  # seconds
    cumulative_time: float  # seconds
    time_per_call: float  # seconds
    callers: List[str]  # List of calling functions
    bottleneck_score: float  # 0.0-1.0, higher = worse bottleneck
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryProfilingResult:
    """Results from memory profiling (Phase 5 Enhancement)"""
    profile_id: str
    function_name: str
    memory_usage_mb: float  # Memory used in MB
    memory_peak_mb: float  # Peak memory in MB
    allocations: int  # Number of allocations
    deallocations: int  # Number of deallocations
    net_allocations: int  # allocations - deallocations
    allocation_rate: float  # allocations per second
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison (Phase 5 Enhancement)"""
    baseline_id: str
    timestamp: str
    method_name: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTrend:
    """Performance trend analysis (Phase 5 Enhancement)"""
    trend_id: str
    method_name: str
    baseline: PerformanceBaseline
    current: PerformanceBaseline
    time_delta_percent: float  # % change in execution time
    memory_delta_percent: float  # % change in memory usage
    trend_direction: str  # "improving", "degrading", "stable"
    regression_detected: bool
    severity: str  # "critical", "high", "medium", "low"


__all__ = [
    'BottleneckFinding',
    'ResourceUsage',
    'OptimizationRecommendation',
    'PerformanceReport',
    'ProfilingResult',
    'MemoryProfilingResult',
    'PerformanceBaseline',
    'PerformanceTrend',
]
