"""
CFG Analyzer - Control Flow Graph Analysis

Provides CFG-based analysis using the edges_cfg table:
- Cyclomatic complexity calculation (M = E - N + 2)
- Execution path enumeration
- CFG structure extraction
- Dominator tree analysis (using edges_dominate/edges_post_dominate)

This module provides proper CFG analysis without fallback heuristics,
replacing the fallback-based approach in control_flow_analyzer.py.

Key Features:
- Uses edges_contains to associate CFG nodes with containing methods
- Proper McCabe cyclomatic complexity calculation
- DFS-based path enumeration with cycle detection
- Support for dominance analysis

Based on: "Graph methods for RAG copilot.md" - Method #5 (partial)
Used in scenarios: 5, 6, 13 (refactoring, performance, mass-refactoring)
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CFGStructure:
    """Represents the CFG structure of a method"""
    method_name: str
    method_full_name: str
    nodes: List[int]
    edges: List[Tuple[int, int]]  # (src, dst) pairs
    entry_nodes: List[int]
    exit_nodes: List[int]
    node_count: int
    edge_count: int


@dataclass
class CFGPath:
    """Represents an execution path through the CFG"""
    path_id: str
    nodes: List[int]
    length: int
    has_loop: bool = False


class CFGAnalyzer:
    """
    CFG-based analysis utilities using edges_cfg table.

    Provides accurate CFG analysis using the actual CFG edges
    exported from Joern, rather than heuristic-based approximations.

    Methods:
        get_method_cfg: Get CFG structure (nodes, edges, entry/exit points)
        compute_cyclomatic_complexity: McCabe complexity via M = E - N + 2
        enumerate_paths: Find execution paths through the CFG
        find_dominators: Compute dominator tree
        find_post_dominators: Compute post-dominator tree
        get_cfg_successors: Get CFG successors of a node
        get_cfg_predecessors: Get CFG predecessors of a node
    """

    def __init__(self, cpg_service):
        """
        Initialize CFG analyzer with CPG service.

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        self.cpg = cpg_service

        # Support both execute_query and execute_sql_dict interfaces
        if hasattr(cpg_service, 'execute_query'):
            self._execute_base = cpg_service.execute_query
            self._use_inline_params = False
        elif hasattr(cpg_service, 'execute_sql_dict'):
            self._execute_base = cpg_service.execute_sql_dict
            self._use_inline_params = True
        else:
            raise ValueError("CPG service must have execute_query or execute_sql_dict method")

        logger.info("CFGAnalyzer initialized")

    def _execute(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SQL query with parameters."""
        try:
            if self._use_inline_params and params:
                # Replace ? placeholders with actual values for inline params
                query_with_params = query
                for param in params:
                    if isinstance(param, str):
                        query_with_params = query_with_params.replace('?', f"'{param}'", 1)
                    else:
                        query_with_params = query_with_params.replace('?', str(param), 1)
                return self._execute_base(query_with_params)
            else:
                return self._execute_base(query, params) if params else self._execute_base(query)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def get_method_cfg(self, method_name: str) -> Optional[CFGStructure]:
        """
        Get the CFG structure for a method.

        Uses edges_contains to find nodes belonging to the method,
        then extracts CFG edges between those nodes.

        Args:
            method_name: Name of the method (simple name, not full name)

        Returns:
            CFGStructure with nodes, edges, and entry/exit points,
            or None if method not found or has no CFG data.
        """
        # First get the method info
        method_query = """
            SELECT id, name, full_name
            FROM nodes_method
            WHERE name = ?
            LIMIT 1
        """
        method_results = self._execute(method_query, (method_name,))
        if not method_results:
            logger.warning(f"Method not found: {method_name}")
            return None

        method_id = method_results[0]['id']
        method_full_name = method_results[0].get('full_name', method_name)

        # Get all nodes contained in this method
        nodes_query = """
            SELECT DISTINCT ec.dst AS node_id
            FROM edges_contains ec
            WHERE ec.src = ?
        """
        node_results = self._execute(nodes_query, (method_id,))
        if not node_results:
            logger.warning(f"No nodes found for method: {method_name}")
            return None

        nodes = [r['node_id'] for r in node_results]
        node_set = set(nodes)

        # Get CFG edges between nodes in this method
        # We need to filter edges where both src and dst are in the method
        edges_query = """
            SELECT cfg.src, cfg.dst
            FROM edges_cfg cfg
            WHERE cfg.src IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
            AND cfg.dst IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
        """
        edge_results = self._execute(edges_query, (method_id, method_id))
        edges = [(r['src'], r['dst']) for r in edge_results]

        # Find entry nodes (nodes with no predecessors in the method)
        dst_nodes = {e[1] for e in edges}
        src_nodes = {e[0] for e in edges}
        entry_nodes = list(node_set - dst_nodes) if edges else nodes[:1]

        # Find exit nodes (nodes with no successors in the method)
        exit_nodes = list(node_set - src_nodes) if edges else nodes[-1:]

        return CFGStructure(
            method_name=method_name,
            method_full_name=method_full_name,
            nodes=nodes,
            edges=edges,
            entry_nodes=entry_nodes,
            exit_nodes=exit_nodes,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    def compute_cyclomatic_complexity(self, method_name: str) -> int:
        """
        Compute McCabe cyclomatic complexity for a method.

        Uses the formula: M = E - N + 2
        Where E = number of edges, N = number of nodes.

        For disconnected graphs, the formula is: M = E - N + 2P
        where P = number of connected components. We assume P=1.

        Args:
            method_name: Name of the method

        Returns:
            Cyclomatic complexity (minimum 1)
        """
        # Use a single optimized query
        query = """
            WITH method_nodes AS (
                SELECT ec.dst AS node_id
                FROM nodes_method m
                JOIN edges_contains ec ON ec.src = m.id
                WHERE m.name = ?
            ),
            cfg_stats AS (
                SELECT
                    (SELECT COUNT(DISTINCT node_id) FROM method_nodes) AS node_count,
                    COUNT(*) AS edge_count
                FROM edges_cfg cfg
                WHERE cfg.src IN (SELECT node_id FROM method_nodes)
                  AND cfg.dst IN (SELECT node_id FROM method_nodes)
            )
            SELECT
                CASE
                    WHEN node_count = 0 THEN 1
                    WHEN edge_count = 0 THEN 1
                    ELSE GREATEST(1, edge_count - node_count + 2)
                END AS complexity
            FROM cfg_stats
        """
        results = self._execute(query, (method_name,))

        if results and 'complexity' in results[0]:
            complexity = results[0]['complexity']
            return max(1, complexity) if complexity else 1

        # Fallback: try to get CFG structure and calculate manually
        cfg = self.get_method_cfg(method_name)
        if cfg and cfg.node_count > 0:
            complexity = cfg.edge_count - cfg.node_count + 2
            return max(1, complexity)

        logger.warning(f"Could not compute complexity for {method_name}, returning 1")
        return 1

    def enumerate_paths(
        self,
        method_name: str,
        max_paths: int = 100,
        max_depth: int = 50
    ) -> List[CFGPath]:
        """
        Enumerate execution paths through the CFG.

        Uses DFS with cycle detection to find paths from entry to exit nodes.

        Args:
            method_name: Name of the method
            max_paths: Maximum number of paths to return
            max_depth: Maximum path depth (to prevent infinite loops)

        Returns:
            List of CFGPath objects representing execution paths
        """
        cfg = self.get_method_cfg(method_name)
        if not cfg or not cfg.nodes:
            return []

        # Build adjacency list from edges
        adjacency: Dict[int, List[int]] = {}
        for src, dst in cfg.edges:
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(dst)

        exit_node_set = set(cfg.exit_nodes)
        paths: List[CFGPath] = []
        path_count = 0

        def dfs(node: int, current_path: List[int], visited: Set[int]) -> None:
            nonlocal path_count
            if path_count >= max_paths:
                return
            if len(current_path) > max_depth:
                return

            current_path.append(node)

            # Check if we reached an exit node
            if node in exit_node_set:
                path_count += 1
                paths.append(CFGPath(
                    path_id=f"path_{path_count}",
                    nodes=list(current_path),
                    length=len(current_path),
                    has_loop=False,
                ))
            elif node in adjacency:
                for successor in adjacency[node]:
                    if successor in visited:
                        # Cycle detected - still record the path
                        path_count += 1
                        paths.append(CFGPath(
                            path_id=f"path_{path_count}",
                            nodes=list(current_path) + [successor],
                            length=len(current_path) + 1,
                            has_loop=True,
                        ))
                    else:
                        dfs(successor, current_path, visited | {node})

            current_path.pop()

        # Start DFS from each entry node
        for entry in cfg.entry_nodes:
            if path_count >= max_paths:
                break
            dfs(entry, [], set())

        return paths

    def find_dominators(self, method_name: str) -> Dict[int, Set[int]]:
        """
        Compute dominator tree using edges_dominate table.

        A node D dominates node N if every path from entry to N
        passes through D.

        Args:
            method_name: Name of the method

        Returns:
            Dict mapping each node to its set of dominators
        """
        cfg = self.get_method_cfg(method_name)
        if not cfg:
            return {}

        method_id = self._get_method_id(method_name)
        if not method_id:
            return {}

        # Query dominator edges
        query = """
            SELECT dom.src AS dominator, dom.dst AS dominated
            FROM edges_dominate dom
            WHERE dom.src IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
            AND dom.dst IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
        """
        results = self._execute(query, (method_id, method_id))

        # Build dominator sets
        dominators: Dict[int, Set[int]] = {n: {n} for n in cfg.nodes}
        for r in results:
            dominated = r['dominated']
            dominator = r['dominator']
            if dominated in dominators:
                dominators[dominated].add(dominator)

        return dominators

    def find_post_dominators(self, method_name: str) -> Dict[int, Set[int]]:
        """
        Compute post-dominator tree using edges_post_dominate table.

        A node D post-dominates node N if every path from N to exit
        passes through D.

        Args:
            method_name: Name of the method

        Returns:
            Dict mapping each node to its set of post-dominators
        """
        cfg = self.get_method_cfg(method_name)
        if not cfg:
            return {}

        method_id = self._get_method_id(method_name)
        if not method_id:
            return {}

        # Query post-dominator edges
        query = """
            SELECT pdom.src AS post_dominator, pdom.dst AS post_dominated
            FROM edges_post_dominate pdom
            WHERE pdom.src IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
            AND pdom.dst IN (
                SELECT ec.dst FROM edges_contains ec WHERE ec.src = ?
            )
        """
        results = self._execute(query, (method_id, method_id))

        # Build post-dominator sets
        post_dominators: Dict[int, Set[int]] = {n: {n} for n in cfg.nodes}
        for r in results:
            post_dominated = r['post_dominated']
            post_dominator = r['post_dominator']
            if post_dominated in post_dominators:
                post_dominators[post_dominated].add(post_dominator)

        return post_dominators

    def get_cfg_successors(self, node_id: int) -> List[int]:
        """Get CFG successors of a node."""
        query = """
            SELECT cfg.dst AS successor
            FROM edges_cfg cfg
            WHERE cfg.src = ?
        """
        results = self._execute(query, (node_id,))
        return [r['successor'] for r in results]

    def get_cfg_predecessors(self, node_id: int) -> List[int]:
        """Get CFG predecessors of a node."""
        query = """
            SELECT cfg.src AS predecessor
            FROM edges_cfg cfg
            WHERE cfg.dst = ?
        """
        results = self._execute(query, (node_id,))
        return [r['predecessor'] for r in results]

    def _get_method_id(self, method_name: str) -> Optional[int]:
        """Get method ID by name."""
        query = "SELECT id FROM nodes_method WHERE name = ? LIMIT 1"
        results = self._execute(query, (method_name,))
        return results[0]['id'] if results else None

    def get_control_flow_paths(
        self,
        source_node: int,
        sink_node: int,
        max_depth: int = 20
    ) -> List[List[int]]:
        """
        Find all CFG paths between two nodes.

        Args:
            source_node: Starting node ID
            sink_node: Target node ID
            max_depth: Maximum path depth

        Returns:
            List of paths (each path is a list of node IDs)
        """
        paths: List[List[int]] = []

        def dfs(current: int, path: List[int], visited: Set[int]) -> None:
            if len(path) > max_depth:
                return
            if current == sink_node:
                paths.append(list(path))
                return

            successors = self.get_cfg_successors(current)
            for succ in successors:
                if succ not in visited:
                    dfs(succ, path + [succ], visited | {succ})

        dfs(source_node, [source_node], {source_node})
        return paths

    def analyze_complexity_distribution(
        self,
        threshold: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze cyclomatic complexity distribution across all methods.

        Args:
            threshold: Complexity threshold for flagging high-complexity methods

        Returns:
            Dict with complexity statistics and high-complexity methods
        """
        # Get all methods with their CFG stats
        query = """
            WITH method_cfg_stats AS (
                SELECT
                    m.name,
                    m.full_name,
                    m.filename,
                    m.line_number,
                    (SELECT COUNT(DISTINCT ec.dst) FROM edges_contains ec WHERE ec.src = m.id) AS node_count,
                    (SELECT COUNT(*)
                     FROM edges_cfg cfg
                     WHERE cfg.src IN (SELECT ec.dst FROM edges_contains ec WHERE ec.src = m.id)
                       AND cfg.dst IN (SELECT ec.dst FROM edges_contains ec WHERE ec.src = m.id)
                    ) AS edge_count
                FROM nodes_method m
                WHERE m.is_external = FALSE OR m.is_external IS NULL
            )
            SELECT
                name,
                full_name,
                filename,
                line_number,
                node_count,
                edge_count,
                CASE
                    WHEN node_count = 0 THEN 1
                    WHEN edge_count = 0 THEN 1
                    ELSE GREATEST(1, edge_count - node_count + 2)
                END AS complexity
            FROM method_cfg_stats
            WHERE node_count > 0
            ORDER BY complexity DESC
            LIMIT 1000
        """
        results = self._execute(query)

        if not results:
            return {
                'total_methods': 0,
                'avg_complexity': 0,
                'max_complexity': 0,
                'high_complexity_methods': [],
            }

        complexities = [r['complexity'] for r in results]
        high_complexity = [r for r in results if r['complexity'] > threshold]

        return {
            'total_methods': len(results),
            'avg_complexity': sum(complexities) / len(complexities) if complexities else 0,
            'max_complexity': max(complexities) if complexities else 0,
            'min_complexity': min(complexities) if complexities else 0,
            'high_complexity_methods': high_complexity[:50],  # Top 50
            'threshold': threshold,
            'methods_above_threshold': len(high_complexity),
        }
