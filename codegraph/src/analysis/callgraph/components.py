"""Connected Components Analysis for Call Graphs.

Implements Tarjan's SCC and Union-Find WCC algorithms.
"""
import logging
from typing import List, Dict, Set

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class ComponentAnalyzer(BaseAnalyzer):
    """Compute connected components in call graphs.

    Methods:
    - compute_strongly_connected_components: Tarjan's SCC for cycle detection
    - compute_weakly_connected_components: Union-Find for isolated code detection
    """

    def compute_strongly_connected_components(self) -> List[List[str]]:
        """
        Compute Strongly Connected Components (SCC) using Tarjan's algorithm.

        An SCC is a maximal set of methods where every method can reach every other.
        SCCs with >1 method indicate mutual recursion.

        Returns:
            List of SCCs, each is a list of method names, sorted by size descending

        Algorithm: Tarjan's SCC (O(V + E))
        """
        try:
            call_edges_query = """
                SELECT DISTINCT
                    m_caller.name AS caller_name,
                    m_callee.name AS callee_name
                FROM edges_call ec
                JOIN nodes_call nc ON ec.src = nc.id
                JOIN nodes_method m_caller ON nc.method_full_name = m_caller.full_name
                JOIN nodes_method m_callee ON ec.dst = m_callee.id;
            """

            call_edges = self._execute(call_edges_query)

            if not call_edges:
                logger.warning("No call edges found for SCC computation")
                return []

            # Build adjacency list
            adjacency: Dict[str, List[str]] = {}
            all_methods: Set[str] = set()

            for edge in call_edges:
                caller = edge.get('caller_name')
                callee = edge.get('callee_name')

                if not caller or not callee:
                    continue

                all_methods.add(caller)
                all_methods.add(callee)

                if caller not in adjacency:
                    adjacency[caller] = []
                adjacency[caller].append(callee)

            # Ensure all methods have an entry
            for method in all_methods:
                if method not in adjacency:
                    adjacency[method] = []

            logger.info(f"Computing SCC for {len(all_methods)} methods")

            # Tarjan's SCC algorithm
            index_counter = [0]
            stack: List[str] = []
            lowlinks: Dict[str, int] = {}
            index: Dict[str, int] = {}
            on_stack: Dict[str, bool] = {}
            sccs: List[List[str]] = []

            def strongconnect(method: str) -> None:
                index[method] = index_counter[0]
                lowlinks[method] = index_counter[0]
                index_counter[0] += 1
                stack.append(method)
                on_stack[method] = True

                for successor in adjacency.get(method, []):
                    if successor not in index:
                        strongconnect(successor)
                        lowlinks[method] = min(lowlinks[method], lowlinks[successor])
                    elif on_stack.get(successor, False):
                        lowlinks[method] = min(lowlinks[method], index[successor])

                if lowlinks[method] == index[method]:
                    scc: List[str] = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        scc.append(w)
                        if w == method:
                            break
                    sccs.append(scc)

            for method in all_methods:
                if method not in index:
                    strongconnect(method)

            sccs.sort(key=len, reverse=True)

            recursive_sccs = [scc for scc in sccs if len(scc) > 1]
            logger.info(
                f"Found {len(sccs)} SCCs total, "
                f"{len(recursive_sccs)} with recursion (size > 1)"
            )

            if recursive_sccs:
                largest = recursive_sccs[0]
                logger.info(
                    f"Largest recursive SCC has {len(largest)} methods: "
                    f"{', '.join(largest[:5])}{'...' if len(largest) > 5 else ''}"
                )

            return sccs

        except Exception as e:
            logger.error(f"Error computing SCC: {e}", exc_info=True)
            return []

    def compute_weakly_connected_components(self) -> List[List[str]]:
        """
        Compute Weakly Connected Components (WCC) using Union-Find.

        A WCC is a maximal set of methods where there exists an undirected path
        between any two methods. Useful for detecting isolated code modules.

        Returns:
            List of WCCs, each is a list of method names, sorted by size descending

        Algorithm: Union-Find (O(E * α(V)))
        """
        try:
            call_edges_query = """
                SELECT DISTINCT
                    m_caller.name AS caller_name,
                    m_callee.name AS callee_name
                FROM edges_call ec
                JOIN nodes_call nc ON ec.src = nc.id
                JOIN nodes_method m_caller ON nc.method_full_name = m_caller.full_name
                JOIN nodes_method m_callee ON ec.dst = m_callee.id;
            """

            call_edges = self._execute(call_edges_query)

            if not call_edges:
                logger.warning("No call edges found for WCC computation")
                return []

            # Build undirected adjacency list
            adjacency: Dict[str, List[str]] = {}
            all_methods: Set[str] = set()

            for edge in call_edges:
                caller = edge.get('caller_name')
                callee = edge.get('callee_name')

                if not caller or not callee:
                    continue

                all_methods.add(caller)
                all_methods.add(callee)

                if caller not in adjacency:
                    adjacency[caller] = []
                if callee not in adjacency:
                    adjacency[callee] = []

                # Add both directions (undirected)
                adjacency[caller].append(callee)
                adjacency[callee].append(caller)

            logger.info(f"Computing WCC for {len(all_methods)} methods")

            # Union-Find data structure
            parent = {method: method for method in all_methods}
            rank = {method: 0 for method in all_methods}

            def find(method: str) -> str:
                """Find root with path compression."""
                if parent[method] != method:
                    parent[method] = find(parent[method])
                return parent[method]

            def union(method1: str, method2: str) -> None:
                """Union by rank."""
                root1 = find(method1)
                root2 = find(method2)

                if root1 != root2:
                    if rank[root1] < rank[root2]:
                        parent[root1] = root2
                    elif rank[root1] > rank[root2]:
                        parent[root2] = root1
                    else:
                        parent[root2] = root1
                        rank[root1] += 1

            # Union all connected methods
            for method in all_methods:
                for neighbor in adjacency.get(method, []):
                    union(method, neighbor)

            # Group methods by component
            components: Dict[str, List[str]] = {}
            for method in all_methods:
                root = find(method)
                if root not in components:
                    components[root] = []
                components[root].append(method)

            wccs = list(components.values())
            wccs.sort(key=len, reverse=True)

            logger.info(
                f"Found {len(wccs)} weakly connected components. "
                f"Largest has {len(wccs[0])} methods, smallest has {len(wccs[-1])} method(s)"
            )

            if len(wccs) > 1:
                isolated = [wcc for wcc in wccs[1:] if len(wcc) < 10]
                logger.info(f"Found {len(isolated)} small isolated components (potential dead code)")

            return wccs

        except Exception as e:
            logger.error(f"Error computing WCC: {e}", exc_info=True)
            return []
