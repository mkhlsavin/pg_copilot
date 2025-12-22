"""Centrality Metrics for Call Graphs.

PageRank and betweenness centrality algorithms.
"""
import logging
import random
from collections import deque, defaultdict
from typing import List, Dict, Any, Optional

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class CentralityAnalyzer(BaseAnalyzer):
    """Compute centrality metrics for call graphs.

    Methods:
    - compute_pagerank: Method importance ranking
    - compute_betweenness_centrality: Bridge method identification
    """

    def compute_pagerank(
        self,
        damping_factor: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 0.0001,
        top_n: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Compute PageRank scores for methods.

        High PageRank = frequently called by important methods.

        Args:
            damping_factor: Probability of following a link (typically 0.85)
            max_iterations: Maximum iterations
            tolerance: Convergence threshold
            top_n: Return top N methods

        Returns:
            List of {method_name, pagerank_score, in_degree, out_degree}
        """
        try:
            call_edges_query = """
                SELECT DISTINCT
                    m_caller.id AS caller_id,
                    m_caller.name AS caller_name,
                    m_callee.id AS callee_id,
                    m_callee.name AS callee_name
                FROM edges_call ec
                JOIN nodes_call nc ON ec.src = nc.id
                JOIN nodes_method m_caller ON nc.method_full_name = m_caller.full_name
                JOIN nodes_method m_callee ON ec.dst = m_callee.id;
            """

            call_edges = self._execute(call_edges_query)

            if not call_edges:
                logger.warning("No call edges found for PageRank")
                return []

            # Build in-memory graph
            adjacency = {}
            all_methods = set()
            out_degree = {}

            for edge in call_edges:
                caller = edge.get('caller_name')
                callee = edge.get('callee_name')

                if not caller or not callee:
                    continue

                all_methods.add(caller)
                all_methods.add(callee)

                if callee not in adjacency:
                    adjacency[callee] = []
                adjacency[callee].append(caller)

                out_degree[caller] = out_degree.get(caller, 0) + 1

            N = len(all_methods)
            if N == 0:
                return []

            logger.info(f"Computing PageRank for {N} methods with {len(call_edges)} edges")

            # Initialize PageRank
            pagerank = {method: 1.0 / N for method in all_methods}
            new_pagerank = pagerank.copy()

            # Iterative computation
            for iteration in range(max_iterations):
                max_diff = 0.0

                for method in all_methods:
                    rank = (1 - damping_factor) / N

                    if method in adjacency:
                        for caller in adjacency[method]:
                            caller_out = out_degree.get(caller, 1)
                            rank += damping_factor * (pagerank[caller] / caller_out)

                    new_pagerank[method] = rank
                    max_diff = max(max_diff, abs(new_pagerank[method] - pagerank[method]))

                if max_diff < tolerance:
                    logger.info(f"PageRank converged after {iteration + 1} iterations")
                    break

                pagerank = new_pagerank.copy()

            # Compute degrees
            in_degree = {}
            for method in all_methods:
                in_degree[method] = len(adjacency.get(method, []))

            # Prepare results
            results = []
            for method in all_methods:
                results.append({
                    'method_name': method,
                    'pagerank_score': pagerank[method],
                    'in_degree': in_degree.get(method, 0),
                    'out_degree': out_degree.get(method, 0)
                })

            results.sort(key=lambda x: x['pagerank_score'], reverse=True)

            if results:
                logger.info(
                    f"PageRank complete: Top method '{results[0]['method_name']}' "
                    f"with score {results[0]['pagerank_score']:.6f}"
                )

            return results[:top_n]

        except Exception as e:
            logger.error(f"Error computing PageRank: {e}", exc_info=True)
            return []

    def compute_betweenness_centrality(
        self,
        sample_size: Optional[int] = None,
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Compute betweenness centrality for methods.

        High betweenness = critical connector/gateway method.

        Args:
            sample_size: Number of sources to sample (None = auto)
            top_n: Return top N methods

        Returns:
            List of {method_name, betweenness_score, paths_through}
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
                logger.warning("No call edges found for betweenness centrality")
                return []

            # Build adjacency list
            adjacency = {}
            all_methods = set()

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

            N = len(all_methods)

            # Decide sampling
            if sample_size is None:
                if N > 1000:
                    sample_size = min(500, N // 2)
                    logger.warning(f"Large graph ({N} methods). Using {sample_size} samples.")
                else:
                    sample_size = N

            source_methods = random.sample(list(all_methods), min(sample_size, N))

            logger.info(
                f"Computing betweenness for {N} methods using {len(source_methods)} samples"
            )

            # Initialize
            betweenness = {method: 0.0 for method in all_methods}

            # BFS from each source
            for source in source_methods:
                queue = deque([source])
                distances = {source: 0}
                predecessors = defaultdict(list)
                sigma = defaultdict(int)
                sigma[source] = 1

                # Forward BFS
                while queue:
                    current = queue.popleft()

                    for neighbor in adjacency.get(current, []):
                        if neighbor not in distances:
                            distances[neighbor] = distances[current] + 1
                            queue.append(neighbor)

                        if distances[neighbor] == distances[current] + 1:
                            sigma[neighbor] += sigma[current]
                            predecessors[neighbor].append(current)

                # Backward accumulation
                delta = defaultdict(float)
                sorted_nodes = sorted(distances.keys(), key=lambda v: distances[v], reverse=True)

                for w in sorted_nodes:
                    for v in predecessors[w]:
                        delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])

                    if w != source:
                        betweenness[w] += delta[w]

            # Normalize
            normalization = len(source_methods) * (len(source_methods) - 1)
            if normalization > 0:
                for method in betweenness:
                    betweenness[method] /= normalization

            # Prepare results
            results = []
            for method, score in betweenness.items():
                results.append({
                    'method_name': method,
                    'betweenness_score': score,
                    'paths_through': int(score * normalization) if normalization > 0 else 0
                })

            results.sort(key=lambda x: x['betweenness_score'], reverse=True)

            if results:
                logger.info(
                    f"Betweenness complete: Top method '{results[0]['method_name']}' "
                    f"with score {results[0]['betweenness_score']:.6f}"
                )

            return results[:top_n]

        except Exception as e:
            logger.error(f"Error computing betweenness: {e}", exc_info=True)
            return []
