"""
Call Graph Analyzer - Type Definitions

Contains dataclasses for call graph analysis results.
Extracted from call_graph_analyzer.py for reusability.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CallPath:
    """Represents a path in the call graph"""
    source_method: str
    target_method: str
    path_length: int
    intermediate_methods: List[str] = field(default_factory=list)
    path_type: str = "direct"  # direct, transitive, recursive


@dataclass
class CallCycle:
    """Represents a cycle (recursion) in the call graph"""
    cycle_id: str
    methods: List[str]
    cycle_length: int
    is_self_recursive: bool


@dataclass
class ImpactAnalysis:
    """Results of impact analysis for a method"""
    method_name: str
    direct_callers: List[str]  # Methods that call this directly
    transitive_callers: List[str]  # All methods that eventually call this
    direct_callees: List[str]  # Methods called directly by this
    transitive_callees: List[str]  # All methods eventually called by this
    impact_score: float  # 0.0-1.0, based on number of affected methods


__all__ = ['CallPath', 'CallCycle', 'ImpactAnalysis']
