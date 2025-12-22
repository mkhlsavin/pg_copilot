"""Call Graph Analyzer - Main Facade.

Composes all call graph analysis modules into a unified interface.
"""
import logging
from typing import Dict, List, Any, Optional

from .base import BaseAnalyzer
from .pathfinding import PathFinder
from .centrality import CentralityAnalyzer
from .components import ComponentAnalyzer
from .impact import ImpactAnalyzer
from .complexity import ComplexityAnalyzer
from .models import CallPath, CallCycle, ImpactAnalysis

logger = logging.getLogger(__name__)


class CallGraphAnalyzer(BaseAnalyzer):
    """
    Advanced call graph analysis using SQL/PGQ queries and proper graph algorithms.

    Core Methods (Original):
    - find_shortest_path: Find shortest call chain between two methods
    - find_all_callers: Find all methods calling a given method
    - find_all_callees: Find all methods called by a given method
    - detect_cycles: Find recursive calls using Tarjan's SCC
    - analyze_impact: Determine which methods are affected by changes
    - get_call_statistics: Overall call graph statistics

    Advanced Methods (Phase 1.2):
    - compute_pagerank: Method importance ranking
    - compute_strongly_connected_components: Precise cycle detection
    - compute_weakly_connected_components: Isolated code detection
    - compute_betweenness_centrality: Bridge method identification
    - compute_cyclomatic_complexity: Code complexity via CFG

    Key Algorithms:
    1. PageRank (O(V+E) per iteration): Method importance
    2. Tarjan's SCC (O(V+E)): Precise cycle detection
    3. Union-Find WCC (O(E*α(V))): Component detection
    4. Brandes' Betweenness (O(V*E)): Bridge methods
    5. CFG-based Complexity (O(V+E)): M = E - N + 2
    """

    def __init__(self, cpg_service):
        """
        Initialize analyzer with CPG service.

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        super().__init__(cpg_service)

        # Initialize component analyzers
        self._pathfinder = PathFinder(cpg_service)
        self._centrality = CentralityAnalyzer(cpg_service)
        self._components = ComponentAnalyzer(cpg_service)
        self._complexity = ComplexityAnalyzer(cpg_service)
        self._impact = ImpactAnalyzer(cpg_service, self._pathfinder, self._components)

        logger.info("CallGraphAnalyzer initialized")

    # ==================== PathFinder Methods ====================

    def find_shortest_path(
        self,
        source_method: str,
        target_method: str,
        max_depth: int = 10
    ) -> Optional[CallPath]:
        """
        Find shortest call path from source to target method.

        Args:
            source_method: Starting method name
            target_method: Target method name
            max_depth: Maximum path length to consider

        Returns:
            CallPath if path exists, None otherwise
        """
        return self._pathfinder.find_shortest_path(source_method, target_method, max_depth)

    def find_all_callers(
        self,
        method_name: str,
        max_depth: int = 5,
        direct_only: bool = False
    ) -> List[str]:
        """
        Find all methods that call the given method.

        Args:
            method_name: Method to analyze
            max_depth: Maximum call depth for transitive callers
            direct_only: If True, return only direct callers

        Returns:
            List of caller method names
        """
        return self._pathfinder.find_all_callers(method_name, max_depth, direct_only)

    def find_all_callees(
        self,
        method_name: str,
        max_depth: int = 5,
        direct_only: bool = False
    ) -> List[str]:
        """
        Find all methods called by the given method.

        Args:
            method_name: Method to analyze
            max_depth: Maximum call depth for transitive callees
            direct_only: If True, return only direct callees

        Returns:
            List of callee method names
        """
        return self._pathfinder.find_all_callees(method_name, max_depth, direct_only)

    # ==================== Impact Methods ====================

    def detect_cycles(self, max_cycle_length: int = 10) -> List[CallCycle]:
        """
        Detect cycles (recursion) in the call graph using SCC.

        Args:
            max_cycle_length: Maximum cycle length to report

        Returns:
            List of detected cycles
        """
        return self._impact.detect_cycles(max_cycle_length)

    def analyze_impact(
        self,
        method_name: str,
        max_depth: int = 3
    ) -> ImpactAnalysis:
        """
        Analyze impact of changes to a method.

        Args:
            method_name: Method to analyze
            max_depth: Maximum depth for transitive analysis

        Returns:
            ImpactAnalysis with complete impact information
        """
        return self._impact.analyze_impact(method_name, max_depth)

    def get_call_statistics(self) -> Dict[str, Any]:
        """
        Get overall call graph statistics.

        Returns:
            Dictionary with total_methods, total_calls, average_fan_out, etc.
        """
        return self._impact.get_call_statistics()

    # ==================== Centrality Methods ====================

    def compute_pagerank(
        self,
        damping_factor: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 0.0001,
        top_n: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Compute PageRank scores for methods.

        Args:
            damping_factor: Probability of following a link (typically 0.85)
            max_iterations: Maximum iterations
            tolerance: Convergence threshold
            top_n: Return top N methods

        Returns:
            List of {method_name, pagerank_score, in_degree, out_degree}
        """
        return self._centrality.compute_pagerank(
            damping_factor, max_iterations, tolerance, top_n
        )

    def compute_betweenness_centrality(
        self,
        sample_size: Optional[int] = None,
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Compute betweenness centrality for methods.

        Args:
            sample_size: Number of sources to sample (None = auto)
            top_n: Return top N methods

        Returns:
            List of {method_name, betweenness_score, paths_through}
        """
        return self._centrality.compute_betweenness_centrality(sample_size, top_n)

    # ==================== Component Methods ====================

    def compute_strongly_connected_components(self) -> List[List[str]]:
        """
        Compute Strongly Connected Components using Tarjan's algorithm.

        Returns:
            List of SCCs, each is a list of method names
        """
        return self._components.compute_strongly_connected_components()

    def compute_weakly_connected_components(self) -> List[List[str]]:
        """
        Compute Weakly Connected Components using Union-Find.

        Returns:
            List of WCCs, each is a list of method names
        """
        return self._components.compute_weakly_connected_components()

    # ==================== Complexity Methods ====================

    def compute_cyclomatic_complexity(
        self,
        method_name: Optional[str] = None,
        top_n: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Compute cyclomatic complexity for methods using CFG.

        Args:
            method_name: Specific method to analyze (None = all)
            top_n: Return top N most complex methods

        Returns:
            List of {method_name, complexity, decision_points, risk_level}
        """
        return self._complexity.compute_cyclomatic_complexity(method_name, top_n)
