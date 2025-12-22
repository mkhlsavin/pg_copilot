"""Call Graph Analyzer - Backward Compatibility Facade.

This module re-exports from src.analysis.callgraph for backward compatibility.
New code should import directly from src.analysis.callgraph.

Example:
    # Old import (still works)
    from src.analysis.call_graph_analyzer import CallGraphAnalyzer

    # New import (preferred)
    from src.analysis.callgraph import CallGraphAnalyzer
"""

from src.analysis.callgraph import (
    CallGraphAnalyzer,
    PathFinder,
    CentralityAnalyzer,
    ComponentAnalyzer,
    ImpactAnalyzer,
    ComplexityAnalyzer,
    CallPath,
    CallCycle,
    ImpactAnalysis,
)

__all__ = [
    "CallGraphAnalyzer",
    "PathFinder",
    "CentralityAnalyzer",
    "ComponentAnalyzer",
    "ImpactAnalyzer",
    "ComplexityAnalyzer",
    "CallPath",
    "CallCycle",
    "ImpactAnalysis",
]
