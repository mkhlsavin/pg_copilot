"""Call Chain Analyzer (Phase 7C)"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class CallChainAnalyzer:
    """
    Analyzes CPGQL execution results to build call chains and control flow graphs.

    Takes results from multiple CPGQL queries and constructs:
    1. Call graph (directed graph of method calls)
    2. Call chains (paths from entry point to key functions)
    3. Key functions (methods relevant to the question)
    """

    def __init__(self):
        """Initialize Call Chain Analyzer."""
        pass

    def analyze(
        self,
        entry_point_result: Optional[Dict],
        keyword_methods_result: List[Dict],
        call_graph_result: List[Dict],
        question_keywords: List[str]
    ) -> Dict:
        """
        Analyze CPGQL results to build call chain.

        Args:
            entry_point_result: Result from entry point query (single method)
            keyword_methods_result: Results from keyword methods query (list of methods)
            call_graph_result: Results from call graph query (list of methods with calls)
            question_keywords: Keywords from original question

        Returns:
            Dictionary with:
            - entry_point: Entry method name
            - call_graph: Adjacency list representation
            - call_chains: List of paths from entry to key functions
            - key_functions: List of relevant methods
            - metadata: Analysis metadata
        """
        logger.info("Analyzing call chain from CPGQL results")

        # Parse results into structured format
        all_methods = self._parse_results(
            entry_point_result,
            keyword_methods_result,
            call_graph_result
        )

        if not all_methods:
            logger.warning("No methods found in CPGQL results")
            return self._empty_result()

        # Build call graph (adjacency list)
        call_graph = self._build_call_graph(all_methods)

        # Identify entry point
        entry_point = self._identify_entry_point(entry_point_result, all_methods)

        # Identify key functions based on keywords
        key_functions = self._extract_key_functions(all_methods, question_keywords)

        # Build call chains from entry to key functions
        call_chains = []
        if entry_point:
            call_chains = self._build_call_chains(
                entry_point,
                key_functions,
                call_graph,
                max_depth=5
            )

        result = {
            'entry_point': entry_point,
            'call_graph': call_graph,
            'call_chains': call_chains,
            'key_functions': key_functions,
            'all_methods': all_methods,
            'metadata': {
                'total_methods': len(all_methods),
                'total_edges': sum(len(v) for v in call_graph.values()),
                'key_function_count': len(key_functions),
                'chain_count': len(call_chains)
            }
        }

        logger.info(f"Call chain analysis complete: entry={entry_point}, "
                   f"methods={len(all_methods)}, key_functions={len(key_functions)}, "
                   f"chains={len(call_chains)}")

        return result

    def _parse_results(
        self,
        entry_point_result: Optional[Dict],
        keyword_methods_result: List[Dict],
        call_graph_result: List[Dict]
    ) -> List[Dict]:
        """
        Parse CPGQL results into unified method list.

        Returns:
            List of method dictionaries with: method, file, line, calls_to, called_by
        """
        methods = []

        # Parse entry point (single result)
        if entry_point_result:
            method_info = self._parse_method_result(entry_point_result)
            if method_info:
                methods.append(method_info)

        # Parse keyword methods (list)
        for result in keyword_methods_result:
            method_info = self._parse_method_result(result)
            if method_info:
                methods.append(method_info)

        # Parse call graph methods (list)
        for result in call_graph_result:
            method_info = self._parse_method_result(result)
            if method_info:
                methods.append(method_info)

        # Deduplicate by method name
        unique_methods = {}
        for method in methods:
            name = method['method']
            if name not in unique_methods:
                unique_methods[name] = method
            else:
                # Merge call information
                existing = unique_methods[name]
                existing['calls_to'] = list(set(existing['calls_to'] + method['calls_to']))
                existing['called_by'] = list(set(existing['called_by'] + method['called_by']))

        return list(unique_methods.values())

    def _parse_method_result(self, result: Dict) -> Optional[Dict]:
        """
        Parse a single CPGQL result into method info.

        Result format (from CPGQL Map):
        {
            "method": "MethodName",
            "file": "path/to/file.c",
            "line": 123,
            "calls_to": ["Method1", "Method2", ...],
            "called_by": ["Method3", "Method4", ...]
        }
        """
        if not result or not isinstance(result, dict):
            return None

        method_name = result.get('method')
        if not method_name:
            return None

        # Extract calls_to (list or string)
        calls_to = result.get('calls_to', [])
        if isinstance(calls_to, str):
            # Handle string format: "Method1, Method2, Method3"
            calls_to = [c.strip() for c in calls_to.split(',') if c.strip()]
        elif not isinstance(calls_to, list):
            calls_to = []

        # Extract called_by (list or string)
        called_by = result.get('called_by', [])
        if isinstance(called_by, str):
            called_by = [c.strip() for c in called_by.split(',') if c.strip()]
        elif not isinstance(called_by, list):
            called_by = []

        return {
            'method': method_name,
            'file': result.get('file', ''),
            'line': result.get('line', 0),
            'calls_to': calls_to,
            'called_by': called_by
        }

    def _build_call_graph(self, methods: List[Dict]) -> Dict[str, List[str]]:
        """
        Build adjacency list representation of call graph.

        Args:
            methods: List of method info dicts

        Returns:
            Dict mapping method name -> list of methods it calls
        """
        graph = defaultdict(list)

        for method in methods:
            method_name = method['method']
            calls_to = method['calls_to']

            # Add edges: method -> callees
            if calls_to:
                graph[method_name].extend(calls_to)

            # Ensure method exists in graph even if no outgoing edges
            if method_name not in graph:
                graph[method_name] = []

        return dict(graph)

    def _identify_entry_point(
        self,
        entry_point_result: Optional[Dict],
        all_methods: List[Dict]
    ) -> Optional[str]:
        """
        Identify the entry point method.

        Priority:
        1. Entry point query result (explicit)
        2. Method with most callouts (hub)
        3. First method in list (fallback)
        """
        # Priority 1: Explicit entry point
        if entry_point_result and 'method' in entry_point_result:
            return entry_point_result['method']

        # Priority 2: Method with most callouts (likely entry point)
        if all_methods:
            methods_by_callout_count = sorted(
                all_methods,
                key=lambda m: len(m['calls_to']),
                reverse=True
            )
            if methods_by_callout_count:
                return methods_by_callout_count[0]['method']

        # Priority 3: Fallback
        if all_methods:
            return all_methods[0]['method']

        return None

    def _extract_key_functions(
        self,
        methods: List[Dict],
        keywords: List[str]
    ) -> List[Dict]:
        """
        Extract key functions relevant to the question.

        Scoring:
        - Exact keyword match in name: +3 points
        - Partial keyword match: +1 point
        - Has callouts: +1 point
        - Has callers: +1 point

        Returns top 10 by score.
        """
        scored_methods = []

        for method in methods:
            method_name = method['method'].lower()
            score = 0

            # Check keyword matches
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in method_name:
                    if keyword_lower == method_name:
                        score += 3  # Exact match
                    else:
                        score += 1  # Partial match

            # Bonus for having call relationships (more connected = more important)
            if method['calls_to']:
                score += 1
            if method['called_by']:
                score += 1

            if score > 0:
                scored_methods.append({
                    'method': method['method'],
                    'file': method['file'],
                    'line': method['line'],
                    'score': score
                })

        # Sort by score and return top 10
        scored_methods.sort(key=lambda m: m['score'], reverse=True)
        return scored_methods[:10]

    def _build_call_chains(
        self,
        entry_point: str,
        key_functions: List[Dict],
        call_graph: Dict[str, List[str]],
        max_depth: int = 5
    ) -> List[Dict]:
        """
        Build call chains from entry point to key functions.

        Uses BFS to find paths, limited to max_depth.

        Returns:
            List of chains, each with: path (list of methods), target (key function)
        """
        if not entry_point or not key_functions:
            return []

        key_function_names = {kf['method'] for kf in key_functions}
        chains = []

        # BFS from entry point
        for target in key_function_names:
            path = self._find_path_bfs(entry_point, target, call_graph, max_depth)
            if path:
                chains.append({
                    'path': path,
                    'target': target,
                    'length': len(path)
                })

        # Sort by path length (shorter = more direct)
        chains.sort(key=lambda c: c['length'])

        return chains

    def _find_path_bfs(
        self,
        start: str,
        target: str,
        graph: Dict[str, List[str]],
        max_depth: int
    ) -> Optional[List[str]]:
        """
        Find shortest path from start to target using BFS.

        Args:
            start: Starting method
            target: Target method
            graph: Adjacency list
            max_depth: Maximum depth to search

        Returns:
            Path as list of method names, or None if not found
        """
        if start == target:
            return [start]

        if start not in graph:
            return None

        # BFS queue: (current_method, path_to_current, depth)
        queue = deque([(start, [start], 0)])
        visited = {start}

        while queue:
            current, path, depth = queue.popleft()

            # Max depth reached
            if depth >= max_depth:
                continue

            # Get neighbors
            neighbors = graph.get(current, [])

            for neighbor in neighbors:
                if neighbor == target:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], depth + 1))

        return None

    def _empty_result(self) -> Dict:
        """Return empty result when no methods found."""
        return {
            'entry_point': None,
            'call_graph': {},
            'call_chains': [],
            'key_functions': [],
            'all_methods': [],
            'metadata': {
                'total_methods': 0,
                'total_edges': 0,
                'key_function_count': 0,
                'chain_count': 0
            }
        }

    def format_call_chain_summary(self, analysis_result: Dict) -> str:
        """
        Format call chain analysis as human-readable summary.

        Args:
            analysis_result: Result from analyze()

        Returns:
            Formatted string summary
        """
        lines = []

        entry = analysis_result.get('entry_point')
        key_functions = analysis_result.get('key_functions', [])
        call_chains = analysis_result.get('call_chains', [])

        lines.append("=== CALL CHAIN ANALYSIS ===")
        lines.append("")

        if entry:
            lines.append(f"Entry Point: {entry}")
        else:
            lines.append("Entry Point: Not found")

        lines.append("")
        lines.append(f"Key Functions ({len(key_functions)}):")
        for i, kf in enumerate(key_functions[:5], 1):
            lines.append(f"  {i}. {kf['method']} (score: {kf.get('score', 0)})")

        lines.append("")
        lines.append(f"Call Chains ({len(call_chains)}):")
        for i, chain in enumerate(call_chains[:3], 1):
            path_str = " -> ".join(chain['path'])
            lines.append(f"  {i}. {path_str} (length: {chain['length']})")

        return "\n".join(lines)
