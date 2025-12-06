"""
Impact Analyzers for Patch Review

Analyzers for computing the impact of patch changes:
- Call graph impact (blast radius, ripple effect, breaking changes)
- Data flow impact (taint paths, sanitization bypass)
- Control flow impact (complexity changes, new loops)
- Dependency impact (new imports, circular deps, layer violations)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional

from ..models import (
    BlastRadius,
    BreakingChange,
    RippleEffect,
    TaintPathFinding,
    SanitizationBypass,
    Finding,
)


@dataclass
class CallGraphAnalysisResult:
    """Result of call graph impact analysis."""
    blast_radius: Dict[str, BlastRadius] = field(default_factory=dict)
    breaking_changes: List[BreakingChange] = field(default_factory=list)
    ripple_effects: Dict[str, RippleEffect] = field(default_factory=dict)
    affected_centrality: Dict[str, float] = field(default_factory=dict)
    findings: List[Finding] = field(default_factory=list)


@dataclass
class DataFlowAnalysisResult:
    """Result of data flow impact analysis."""
    new_taint_paths: List[TaintPathFinding] = field(default_factory=list)
    sanitization_bypasses: List[SanitizationBypass] = field(default_factory=list)
    sensitive_data_findings: List[Finding] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)


@dataclass
class ControlFlowAnalysisResult:
    """Result of control flow impact analysis."""
    complexity_changes: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    new_loops: List[Any] = field(default_factory=list)
    error_handling_changes: List[Any] = field(default_factory=list)
    branch_coverage_impacts: List[Any] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)


@dataclass
class DependencyAnalysisResult:
    """Result of dependency impact analysis."""
    dependency_changes: List[Any] = field(default_factory=list)
    circular_dependencies: List[Any] = field(default_factory=list)
    layer_violations: List[Any] = field(default_factory=list)
    coupling_before: Dict[str, Any] = field(default_factory=dict)
    coupling_after: Dict[str, Any] = field(default_factory=dict)
    findings: List[Finding] = field(default_factory=list)
    new_dependencies_count: int = 0
    removed_dependencies_count: int = 0
    affected_modules: Set[str] = field(default_factory=set)


# Import analyzer classes with lazy loading to avoid circular imports
def _get_call_graph_analyzer():
    from .call_graph_analyzer import PatchCallGraphAnalyzer
    return PatchCallGraphAnalyzer

def _get_dataflow_analyzer():
    from .dataflow_analyzer import PatchDataFlowAnalyzer
    return PatchDataFlowAnalyzer

def _get_control_flow_analyzer():
    from .control_flow_analyzer import PatchControlFlowAnalyzer
    return PatchControlFlowAnalyzer

def _get_dependency_analyzer():
    from .dependency_analyzer import PatchDependencyAnalyzer
    return PatchDependencyAnalyzer


class PatchCallGraphAnalyzer:
    """Wrapper for lazy-loaded call graph analyzer."""
    def __new__(cls, *args, **kwargs):
        return _get_call_graph_analyzer()(*args, **kwargs)


class PatchDataFlowAnalyzer:
    """Wrapper for lazy-loaded dataflow analyzer."""
    def __new__(cls, *args, **kwargs):
        return _get_dataflow_analyzer()(*args, **kwargs)


class PatchControlFlowAnalyzer:
    """Wrapper for lazy-loaded control flow analyzer."""
    def __new__(cls, *args, **kwargs):
        return _get_control_flow_analyzer()(*args, **kwargs)


class PatchDependencyAnalyzer:
    """Wrapper for lazy-loaded dependency analyzer."""
    def __new__(cls, *args, **kwargs):
        return _get_dependency_analyzer()(*args, **kwargs)


__all__ = [
    'PatchCallGraphAnalyzer',
    'CallGraphAnalysisResult',
    'PatchDataFlowAnalyzer',
    'DataFlowAnalysisResult',
    'PatchControlFlowAnalyzer',
    'ControlFlowAnalysisResult',
    'PatchDependencyAnalyzer',
    'DependencyAnalysisResult',
]
