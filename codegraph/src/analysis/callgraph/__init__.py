"""Call Graph Analysis Package.

Advanced call graph analysis using SQL/PGQ queries and graph algorithms.

Main components:
- CallGraphAnalyzer: Main analyzer class (facade)
- PathFinder: Shortest path and transitive closure
- CentralityAnalyzer: PageRank and betweenness centrality
- ComponentAnalyzer: SCC and WCC detection
- ImpactAnalyzer: Cycle detection and impact analysis
- ComplexityAnalyzer: Cyclomatic complexity

Example usage:
    from src.analysis.callgraph import CallGraphAnalyzer

    analyzer = CallGraphAnalyzer(cpg_service)
    path = analyzer.find_shortest_path('main', 'malloc')
    callers = analyzer.find_all_callers('vulnerable_function')
    pagerank = analyzer.compute_pagerank()
"""

from .analyzer import CallGraphAnalyzer
from .pathfinding import PathFinder
from .centrality import CentralityAnalyzer
from .components import ComponentAnalyzer
from .impact import ImpactAnalyzer
from .complexity import ComplexityAnalyzer
from .models import CallPath, CallCycle, ImpactAnalysis

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
