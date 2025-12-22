"""Impact Analysis for Call Graphs.

Cycle detection, impact analysis, and call graph statistics.
"""
import logging
from typing import List, Dict, Any

from .base import BaseAnalyzer
from .models import CallCycle, ImpactAnalysis

logger = logging.getLogger(__name__)


class ImpactAnalyzer(BaseAnalyzer):
    """Analyze impact of method changes and detect cycles.

    Methods:
    - detect_cycles: Find recursive calls using SCC
    - analyze_impact: Determine affected methods
    - get_call_statistics: Overall call graph statistics
    """

    def __init__(self, cpg_service, pathfinder=None, component_analyzer=None):
        """
        Initialize impact analyzer.

        Args:
            cpg_service: CPG query service
            pathfinder: Optional PathFinder for transitive analysis
            component_analyzer: Optional ComponentAnalyzer for SCC
        """
        super().__init__(cpg_service)
        self._pathfinder = pathfinder
        self._component_analyzer = component_analyzer

    def detect_cycles(self, max_cycle_length: int = 10) -> List[CallCycle]:
        """
        Detect cycles (recursion) in the call graph using SCC.

        Finds:
        - Self-recursive methods
        - Mutual recursion (A->B->A)
        - Longer cycles

        Args:
            max_cycle_length: Maximum cycle length to report

        Returns:
            List of detected cycles
        """
        try:
            if self._component_analyzer is None:
                logger.warning("ComponentAnalyzer not available, returning empty cycles")
                return []

            sccs = self._component_analyzer.compute_strongly_connected_components()
            cycles = []

            # Find self-recursive methods
            self_recursive_query = """
                SELECT DISTINCT m.name AS method_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.containing_method_id = m.id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method target ON ec.dst = target.id
                WHERE target.name = m.name;
            """

            self_recursive = self._execute(self_recursive_query)
            self_recursive_methods = {row.get('method_name') for row in self_recursive if row.get('method_name')}

            for idx, scc in enumerate(sccs):
                if len(scc) > max_cycle_length:
                    continue

                if len(scc) == 1:
                    method = scc[0]
                    if method in self_recursive_methods:
                        cycles.append(CallCycle(
                            cycle_id=f"CYCLE_SELF_{idx:03d}",
                            methods=[method],
                            cycle_length=1,
                            is_self_recursive=True
                        ))
                else:
                    cycles.append(CallCycle(
                        cycle_id=f"CYCLE_SCC_{idx:03d}",
                        methods=scc,
                        cycle_length=len(scc),
                        is_self_recursive=False
                    ))

            cycles.sort(key=lambda c: c.cycle_length, reverse=True)

            logger.info(
                f"Detected {len(cycles)} cycles: "
                f"{len([c for c in cycles if c.is_self_recursive])} self-recursive, "
                f"{len([c for c in cycles if not c.is_self_recursive])} mutual/complex"
            )

            return cycles

        except Exception as e:
            logger.error(f"Error detecting cycles: {e}", exc_info=True)
            return []

    def analyze_impact(
        self,
        method_name: str,
        max_depth: int = 3
    ) -> ImpactAnalysis:
        """
        Analyze impact of changes to a method.

        Determines:
        - Who calls this method (upstream impact)
        - What this method calls (downstream dependencies)
        - Overall impact score

        Args:
            method_name: Method to analyze
            max_depth: Maximum depth for transitive analysis

        Returns:
            ImpactAnalysis with complete impact information
        """
        if self._pathfinder is None:
            logger.warning("PathFinder not available for impact analysis")
            return ImpactAnalysis(
                method_name=method_name,
                direct_callers=[],
                transitive_callers=[],
                direct_callees=[],
                transitive_callees=[],
                impact_score=0.0
            )

        direct_callers = self._pathfinder.find_all_callers(method_name, direct_only=True)
        transitive_callers = self._pathfinder.find_all_callers(method_name, max_depth=max_depth)

        direct_callees = self._pathfinder.find_all_callees(method_name, direct_only=True)
        transitive_callees = self._pathfinder.find_all_callees(method_name, max_depth=max_depth)

        total_affected = len(set(transitive_callers + transitive_callees))

        total_methods_query = "SELECT COUNT(*) as total FROM nodes_method;"
        total_result = self._execute(total_methods_query)
        total_methods = total_result[0].get('total', 1000) if total_result else 1000

        impact_score = min(1.0, total_affected / (total_methods * 0.1))

        analysis = ImpactAnalysis(
            method_name=method_name,
            direct_callers=direct_callers,
            transitive_callers=[c for c in transitive_callers if c not in direct_callers],
            direct_callees=direct_callees,
            transitive_callees=[c for c in transitive_callees if c not in direct_callees],
            impact_score=impact_score
        )

        logger.info(
            f"Impact analysis for {method_name}: "
            f"{len(direct_callers)} direct callers, "
            f"{len(transitive_callers)} total callers, "
            f"impact score: {impact_score:.2f}"
        )

        return analysis

    def get_call_statistics(self) -> Dict[str, Any]:
        """
        Get overall call graph statistics.

        Returns:
            Dictionary with metrics:
            - total_methods
            - total_calls
            - average_fan_out
            - average_fan_in
        """
        stats_query = """
            SELECT
                (SELECT COUNT(*) FROM nodes_method) AS total_methods,
                (SELECT COUNT(*) FROM edges_call) AS total_calls,
                (SELECT AVG(call_count) FROM (
                    SELECT COUNT(ec.dst) AS call_count
                    FROM nodes_method m
                    LEFT JOIN nodes_call nc ON nc.containing_method_id = m.id
                    LEFT JOIN edges_call ec ON ec.src = nc.id
                    GROUP BY m.id
                )) AS avg_fan_out,
                (SELECT AVG(called_count) FROM (
                    SELECT COUNT(ec.src) AS called_count
                    FROM nodes_method m
                    LEFT JOIN edges_call ec ON ec.dst = m.id
                    GROUP BY m.id
                )) AS avg_fan_in;
        """

        try:
            results = self._execute(stats_query)
            if results:
                stats = results[0]
                return {
                    'total_methods': stats.get('total_methods', 0),
                    'total_calls': stats.get('total_calls', 0),
                    'average_fan_out': float(stats.get('avg_fan_out', 0) or 0),
                    'average_fan_in': float(stats.get('avg_fan_in', 0) or 0),
                    'max_call_depth': 'unknown'
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting call statistics: {e}")
            return {}
