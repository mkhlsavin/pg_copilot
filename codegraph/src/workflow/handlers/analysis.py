"""Analysis Handler for code analysis operations.

Handles:
- Call graph analysis (callers, callees, paths)
- Data flow tracing
- Control flow analysis
- Metrics computation (complexity, coupling)
"""
import logging
import time
from typing import Any, Dict, List, Optional, Set

from .base import BaseHandler, HandlerResult

logger = logging.getLogger(__name__)


class AnalysisHandler(BaseHandler):
    """
    Handler for code analysis operations.

    Provides high-level analysis capabilities using
    call graph and dataflow analyzers.
    """

    def __init__(
        self,
        call_graph_analyzer=None,
        dataflow_tracer=None,
        cpg_client=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize analysis handler.

        Args:
            call_graph_analyzer: CallGraphAnalyzer instance
            dataflow_tracer: DataFlowTracer instance
            cpg_client: DuckDBCPGClient for queries
            config: Additional configuration
        """
        super().__init__(config)
        self._call_graph = call_graph_analyzer
        self._dataflow = dataflow_tracer
        self._cpg_client = cpg_client

    def set_analyzers(
        self,
        call_graph_analyzer=None,
        dataflow_tracer=None,
        cpg_client=None
    ):
        """Set or update analyzers."""
        if call_graph_analyzer:
            self._call_graph = call_graph_analyzer
        if dataflow_tracer:
            self._dataflow = dataflow_tracer
        if cpg_client:
            self._cpg_client = cpg_client
        self.log_info("Analyzers updated")

    def handle(
        self,
        analysis_type: str,
        **kwargs
    ) -> HandlerResult:
        """
        Execute analysis based on type.

        Args:
            analysis_type: Type of analysis to perform
            **kwargs: Analysis-specific arguments

        Returns:
            HandlerResult with analysis results
        """
        start_time = time.time()

        try:
            # Dispatch to specific analysis method
            if analysis_type == "callers":
                result = self._find_callers(**kwargs)
            elif analysis_type == "callees":
                result = self._find_callees(**kwargs)
            elif analysis_type == "call_path":
                result = self._find_call_path(**kwargs)
            elif analysis_type == "impact":
                result = self._analyze_impact(**kwargs)
            elif analysis_type == "dataflow":
                result = self._trace_dataflow(**kwargs)
            elif analysis_type == "complexity":
                result = self._compute_complexity(**kwargs)
            elif analysis_type == "dead_code":
                result = self._find_dead_code(**kwargs)
            elif analysis_type == "hotspots":
                result = self._find_hotspots(**kwargs)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")

            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, True)

            return HandlerResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                metadata={"analysis_type": analysis_type}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, False)
            self.log_error(f"Analysis failed ({analysis_type}): {e}")

            return HandlerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                metadata={"analysis_type": analysis_type}
            )

    def find_all_callers(
        self,
        method_name: str,
        max_depth: int = 5
    ) -> HandlerResult:
        """
        Find all transitive callers of a method.

        Args:
            method_name: Target method name
            max_depth: Maximum call chain depth

        Returns:
            HandlerResult with caller information
        """
        return self.handle(
            "callers",
            method_name=method_name,
            max_depth=max_depth
        )

    def find_all_callees(
        self,
        method_name: str,
        max_depth: int = 5
    ) -> HandlerResult:
        """
        Find all transitive callees of a method.

        Args:
            method_name: Source method name
            max_depth: Maximum call chain depth

        Returns:
            HandlerResult with callee information
        """
        return self.handle(
            "callees",
            method_name=method_name,
            max_depth=max_depth
        )

    def analyze_change_impact(
        self,
        method_name: str,
        include_indirect: bool = True
    ) -> HandlerResult:
        """
        Analyze impact of changing a method.

        Args:
            method_name: Method being changed
            include_indirect: Include indirect dependencies

        Returns:
            HandlerResult with impact analysis
        """
        return self.handle(
            "impact",
            method_name=method_name,
            include_indirect=include_indirect
        )

    def trace_variable_flow(
        self,
        variable_name: str,
        method_name: Optional[str] = None
    ) -> HandlerResult:
        """
        Trace data flow of a variable.

        Args:
            variable_name: Variable to trace
            method_name: Optional containing method

        Returns:
            HandlerResult with dataflow paths
        """
        return self.handle(
            "dataflow",
            variable_name=variable_name,
            method_name=method_name
        )

    # === Private Analysis Methods ===

    def _find_callers(
        self,
        method_name: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """Find all transitive callers."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        # Use recursive CTE for transitive callers
        query = f"""
            WITH RECURSIVE caller_chain AS (
                -- Base case: direct callers
                SELECT DISTINCT
                    m.name as caller,
                    c.name as callee,
                    1 as depth
                FROM nodes_call c
                JOIN nodes_method m ON c.containing_method_id = m.id
                WHERE c.name ILIKE '%{method_name}%'

                UNION ALL

                -- Recursive case: callers of callers
                SELECT DISTINCT
                    m.name as caller,
                    cc.caller as callee,
                    cc.depth + 1 as depth
                FROM caller_chain cc
                JOIN nodes_call c ON c.name = cc.caller
                JOIN nodes_method m ON c.containing_method_id = m.id
                WHERE cc.depth < {max_depth}
            )
            SELECT DISTINCT caller, callee, MIN(depth) as min_depth
            FROM caller_chain
            GROUP BY caller, callee
            ORDER BY min_depth, caller
            LIMIT 500
        """

        results = self._cpg_client.execute_sql_dict(query)

        # Build caller tree
        callers_by_depth: Dict[int, List[str]] = {}
        for row in results:
            depth = row.get('min_depth', 1)
            caller = row.get('caller', '')
            if depth not in callers_by_depth:
                callers_by_depth[depth] = []
            if caller not in callers_by_depth[depth]:
                callers_by_depth[depth].append(caller)

        return {
            "target": method_name,
            "total_callers": len(set(r['caller'] for r in results)),
            "callers_by_depth": callers_by_depth,
            "max_depth_reached": max(callers_by_depth.keys()) if callers_by_depth else 0,
            "raw_results": results[:100]  # Limit raw output
        }

    def _find_callees(
        self,
        method_name: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """Find all transitive callees."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        query = f"""
            WITH RECURSIVE callee_chain AS (
                -- Base case: direct callees from target method
                SELECT DISTINCT
                    m.name as caller,
                    c.name as callee,
                    1 as depth
                FROM nodes_method m
                JOIN nodes_call c ON c.containing_method_id = m.id
                WHERE m.name ILIKE '%{method_name}%'

                UNION ALL

                -- Recursive case: callees of callees
                SELECT DISTINCT
                    cc.callee as caller,
                    c.name as callee,
                    cc.depth + 1 as depth
                FROM callee_chain cc
                JOIN nodes_method m ON m.name = cc.callee
                JOIN nodes_call c ON c.containing_method_id = m.id
                WHERE cc.depth < {max_depth}
            )
            SELECT DISTINCT caller, callee, MIN(depth) as min_depth
            FROM callee_chain
            GROUP BY caller, callee
            ORDER BY min_depth, callee
            LIMIT 500
        """

        results = self._cpg_client.execute_sql_dict(query)

        callees_by_depth: Dict[int, List[str]] = {}
        for row in results:
            depth = row.get('min_depth', 1)
            callee = row.get('callee', '')
            if depth not in callees_by_depth:
                callees_by_depth[depth] = []
            if callee not in callees_by_depth[depth]:
                callees_by_depth[depth].append(callee)

        return {
            "source": method_name,
            "total_callees": len(set(r['callee'] for r in results)),
            "callees_by_depth": callees_by_depth,
            "max_depth_reached": max(callees_by_depth.keys()) if callees_by_depth else 0,
            "raw_results": results[:100]
        }

    def _find_call_path(
        self,
        source: str,
        target: str,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """Find call path between two methods."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        # Simplified path finding - find if path exists
        query = f"""
            WITH RECURSIVE call_path AS (
                SELECT DISTINCT
                    m.name as current,
                    c.name as next_call,
                    ARRAY[m.name] as path,
                    1 as depth
                FROM nodes_method m
                JOIN nodes_call c ON c.containing_method_id = m.id
                WHERE m.name ILIKE '%{source}%'

                UNION ALL

                SELECT DISTINCT
                    cp.next_call as current,
                    c.name as next_call,
                    array_append(cp.path, cp.next_call) as path,
                    cp.depth + 1 as depth
                FROM call_path cp
                JOIN nodes_method m ON m.name = cp.next_call
                JOIN nodes_call c ON c.containing_method_id = m.id
                WHERE cp.depth < {max_depth}
                    AND cp.next_call NOT ILIKE '%{target}%'
                    AND NOT array_contains(cp.path, cp.next_call)
            )
            SELECT path, depth
            FROM call_path
            WHERE next_call ILIKE '%{target}%'
            ORDER BY depth
            LIMIT 10
        """

        try:
            results = self._cpg_client.execute_sql_dict(query)
            paths = [r.get('path', []) + [target] for r in results]

            return {
                "source": source,
                "target": target,
                "paths_found": len(paths),
                "shortest_path": paths[0] if paths else None,
                "shortest_length": len(paths[0]) if paths else None,
                "all_paths": paths[:5]  # Top 5 shortest
            }
        except Exception as e:
            self.log_warning(f"Path finding query failed: {e}")
            return {
                "source": source,
                "target": target,
                "paths_found": 0,
                "error": str(e)
            }

    def _analyze_impact(
        self,
        method_name: str,
        include_indirect: bool = True
    ) -> Dict[str, Any]:
        """Analyze impact of changing a method."""
        # Get direct callers
        callers_result = self._find_callers(
            method_name,
            max_depth=3 if include_indirect else 1
        )

        # Get files affected
        affected_files: Set[str] = set()
        if self._cpg_client:
            query = f"""
                SELECT DISTINCT m.filename
                FROM nodes_call c
                JOIN nodes_method m ON c.containing_method_id = m.id
                WHERE c.name ILIKE '%{method_name}%'
            """
            results = self._cpg_client.execute_sql_dict(query)
            affected_files = {r['filename'] for r in results if r.get('filename')}

        return {
            "method": method_name,
            "direct_callers": callers_result.get('callers_by_depth', {}).get(1, []),
            "total_affected_methods": callers_result.get('total_callers', 0),
            "affected_files": list(affected_files),
            "affected_file_count": len(affected_files),
            "impact_level": self._classify_impact(
                callers_result.get('total_callers', 0),
                len(affected_files)
            )
        }

    def _classify_impact(self, caller_count: int, file_count: int) -> str:
        """Classify change impact level."""
        if caller_count == 0:
            return "none"
        elif caller_count <= 3 and file_count <= 1:
            return "low"
        elif caller_count <= 10 and file_count <= 5:
            return "medium"
        else:
            return "high"

    def _trace_dataflow(
        self,
        variable_name: str,
        method_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trace dataflow for a variable."""
        if self._dataflow:
            # Use dataflow tracer if available
            try:
                flow = self._dataflow.trace_variable(
                    variable_name,
                    containing_method=method_name
                )
                return {
                    "variable": variable_name,
                    "method": method_name,
                    "flow": flow
                }
            except Exception as e:
                self.log_warning(f"Dataflow tracer failed: {e}")

        # Fallback: simple reaching definitions query
        if not self._cpg_client:
            raise RuntimeError("No dataflow tracer or CPG client available")

        query = f"""
            SELECT
                src.id as def_id,
                dst.id as use_id,
                rd.variable,
                src.code as def_code,
                dst.code as use_code
            FROM edges_reaching_def rd
            JOIN nodes_identifier src ON rd.src = src.id
            JOIN nodes_identifier dst ON rd.dst = dst.id
            WHERE rd.variable ILIKE '%{variable_name}%'
            LIMIT 100
        """

        results = self._cpg_client.execute_sql_dict(query)

        return {
            "variable": variable_name,
            "method": method_name,
            "definitions": len(set(r['def_id'] for r in results)),
            "uses": len(set(r['use_id'] for r in results)),
            "flows": results[:50]
        }

    def _compute_complexity(
        self,
        method_name: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Compute complexity metrics for methods."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        # Count control structures per method
        where_clause = f"WHERE m.name ILIKE '%{method_name}%'" if method_name else ""

        query = f"""
            SELECT
                m.name,
                m.filename,
                m.line_number,
                m.line_number_end,
                COUNT(DISTINCT cs.id) as control_structures,
                COUNT(DISTINCT c.id) as call_count
            FROM nodes_method m
            LEFT JOIN nodes_control_structure cs
                ON cs.filename = m.filename
                AND cs.line_number >= m.line_number
                AND cs.line_number <= COALESCE(m.line_number_end, m.line_number + 1000)
            LEFT JOIN nodes_call c ON c.containing_method_id = m.id
            {where_clause}
            GROUP BY m.id, m.name, m.filename, m.line_number, m.line_number_end
            ORDER BY control_structures DESC
            LIMIT {limit}
        """

        results = self._cpg_client.execute_sql_dict(query)

        # Add estimated cyclomatic complexity
        for r in results:
            # Simple estimate: 1 + control_structures
            r['estimated_complexity'] = 1 + (r.get('control_structures', 0) or 0)

        return {
            "methods": results,
            "total_analyzed": len(results),
            "avg_complexity": sum(r['estimated_complexity'] for r in results) / max(len(results), 1)
        }

    def _find_dead_code(self, **kwargs) -> Dict[str, Any]:
        """Find potentially dead code (uncalled methods)."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        # Find methods that are never called
        query = """
            SELECT m.name, m.filename, m.line_number
            FROM nodes_method m
            WHERE NOT EXISTS (
                SELECT 1 FROM nodes_call c
                WHERE c.name = m.name
            )
            AND m.name NOT LIKE '%main%'
            AND m.name NOT LIKE '%init%'
            AND m.name NOT LIKE '%test%'
            ORDER BY m.filename, m.line_number
            LIMIT 200
        """

        results = self._cpg_client.execute_sql_dict(query)

        return {
            "potentially_dead": results,
            "count": len(results),
            "note": "Methods with no callers found (excludes main/init/test)"
        }

    def _find_hotspots(self, limit: int = 20, **kwargs) -> Dict[str, Any]:
        """Find code hotspots (most called methods)."""
        if not self._cpg_client:
            raise RuntimeError("CPG client not initialized")

        query = f"""
            SELECT
                c.name as method_name,
                COUNT(*) as call_count,
                COUNT(DISTINCT c.containing_method_id) as unique_callers
            FROM nodes_call c
            GROUP BY c.name
            ORDER BY call_count DESC
            LIMIT {limit}
        """

        results = self._cpg_client.execute_sql_dict(query)

        return {
            "hotspots": results,
            "count": len(results)
        }
