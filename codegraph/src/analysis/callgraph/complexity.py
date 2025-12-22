"""Cyclomatic Complexity Analysis for Call Graphs.

CFG-based complexity measurement using M = E - N + 2.
"""
import logging
from typing import List, Dict, Any, Optional

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class ComplexityAnalyzer(BaseAnalyzer):
    """Compute cyclomatic complexity using Control Flow Graph.

    Methods:
    - compute_cyclomatic_complexity: CFG-based complexity (M = E - N + 2)
    """

    def compute_cyclomatic_complexity(
        self,
        method_name: Optional[str] = None,
        top_n: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Compute cyclomatic complexity for methods using CFG.

        Formula: M = E - N + 2
        Where E = CFG edges, N = CFG nodes

        Complexity Levels:
        - 1-10: Simple, low risk
        - 11-20: Moderate complexity
        - 21-50: High complexity, hard to test
        - 50+: Very high, unmaintainable

        Args:
            method_name: Specific method to analyze (None = all)
            top_n: Return top N most complex methods

        Returns:
            List of {method_name, complexity, decision_points, risk_level}
        """
        try:
            if method_name:
                return self._analyze_single_method(method_name)
            else:
                return self._analyze_all_methods(top_n)

        except Exception as e:
            logger.error(f"Error computing cyclomatic complexity: {e}", exc_info=True)
            return []

    def _analyze_single_method(self, method_name: str) -> List[Dict[str, Any]]:
        """Analyze complexity for a single method."""
        nodes_query = """
            SELECT n.id
            FROM cpg_nodes n
            WHERE n.method_full_name LIKE '%' || ? || '%';
        """
        nodes = self._execute(nodes_query, (method_name,))

        if not nodes:
            logger.warning(f"No nodes found for method {method_name}")
            return []

        node_ids = [n.get('id') for n in nodes]
        node_id_placeholders = ','.join(['?'] * len(node_ids))

        cfg_query = f"""
            SELECT
                ? AS method_name,
                COUNT(DISTINCT src) + COUNT(DISTINCT dst) AS node_count,
                COUNT(*) AS edge_count
            FROM edges_cfg
            WHERE src IN ({node_id_placeholders})
               OR dst IN ({node_id_placeholders});
        """

        params = [method_name] + node_ids + node_ids
        results = self._execute(cfg_query, tuple(params))

        return self._process_results(results)

    def _analyze_all_methods(self, top_n: int) -> List[Dict[str, Any]]:
        """Analyze complexity for all methods."""
        cfg_query = """
            WITH method_cfg AS (
                SELECT
                    m.id AS method_id,
                    m.name AS method_name,
                    m.filename,
                    COUNT(DISTINCT CASE WHEN cfg.src IN (
                        SELECT n.id FROM cpg_nodes n WHERE n.method_full_name LIKE '%' || m.name || '%'
                    ) THEN cfg.src END) +
                    COUNT(DISTINCT CASE WHEN cfg.dst IN (
                        SELECT n.id FROM cpg_nodes n WHERE n.method_full_name LIKE '%' || m.name || '%'
                    ) THEN cfg.dst END) AS node_count,
                    COUNT(*) AS edge_count
                FROM nodes_method m
                LEFT JOIN cpg_nodes n ON n.method_full_name LIKE '%' || m.name || '%'
                LEFT JOIN edges_cfg cfg ON cfg.src = n.id OR cfg.dst = n.id
                GROUP BY m.id, m.name, m.filename
                HAVING node_count > 0
            )
            SELECT
                method_name,
                filename,
                node_count,
                edge_count
            FROM method_cfg
            ORDER BY (edge_count - node_count + 2) DESC
            LIMIT ?;
        """

        results = self._execute(cfg_query, (top_n * 2,))
        return self._process_results(results)[:top_n]

    def _process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process query results into complexity metrics."""
        if not results:
            logger.warning("No CFG data found for complexity calculation")
            return []

        complexity_results = []

        for row in results:
            method = row.get('method_name', '')
            if not method:
                continue

            N = row.get('node_count', 0)
            E = row.get('edge_count', 0)

            # Cyclomatic complexity: M = E - N + 2
            if N == 0 or E == 0:
                complexity = 1
            else:
                complexity = E - N + 2

            decision_points = max(0, complexity - 1)

            if complexity <= 10:
                risk_level = "low"
            elif complexity <= 20:
                risk_level = "moderate"
            elif complexity <= 50:
                risk_level = "high"
            else:
                risk_level = "very_high"

            complexity_results.append({
                'method_name': method,
                'filename': row.get('filename', ''),
                'complexity': complexity,
                'decision_points': decision_points,
                'cfg_nodes': N,
                'cfg_edges': E,
                'risk_level': risk_level
            })

        complexity_results.sort(key=lambda x: x['complexity'], reverse=True)

        if complexity_results:
            logger.info(
                f"Cyclomatic complexity complete: "
                f"Top method '{complexity_results[0]['method_name']}' "
                f"has complexity {complexity_results[0]['complexity']} "
                f"({complexity_results[0]['risk_level']} risk)"
            )

        return complexity_results
