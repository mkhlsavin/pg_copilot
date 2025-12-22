"""Base class for data flow analysis modules.

Provides common query execution logic for all tracers.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BaseTracer:
    """Base class with query execution support for data flow tracers."""

    def __init__(self, cpg_service):
        """
        Initialize tracer with CPG service.

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

    def _execute(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute query with proper parameter handling for both interfaces."""
        if self._use_inline_params and params:
            for p in params:
                if isinstance(p, str):
                    query = query.replace('?', f"'{p}'", 1)
                else:
                    query = query.replace('?', str(p), 1)
            return self._execute_base(query)
        elif params:
            return self._execute_base(query, params)
        else:
            return self._execute_base(query)

    def _get_containing_methods(self, node_ids: List[int]) -> Dict[int, Optional[str]]:
        """
        Find the containing method for each node using AST parent traversal.

        Args:
            node_ids: List of node IDs to lookup

        Returns:
            Dict mapping node_id -> method_full_name (or None if not in a method)
        """
        if not node_ids:
            return {}

        node_list = ','.join(str(nid) for nid in node_ids)

        query = f"""
            WITH RECURSIVE ast_ancestors AS (
                SELECT
                    id AS original_id,
                    id AS current_id,
                    0 AS depth
                FROM nodes_identifier
                WHERE id IN ({node_list})

                UNION ALL

                SELECT
                    aa.original_id,
                    ast.src AS current_id,
                    aa.depth + 1
                FROM ast_ancestors aa
                JOIN edges_ast ast ON ast.dst = aa.current_id
                WHERE aa.depth < 20
            )
            SELECT DISTINCT
                aa.original_id AS node_id,
                m.full_name AS method_full_name
            FROM ast_ancestors aa
            JOIN nodes_method m ON m.id = aa.current_id
            WHERE m.full_name IS NOT NULL
        """

        try:
            results = self._execute(query)
            return {row['node_id']: row['method_full_name'] for row in results}
        except Exception as e:
            logger.warning(f"Failed to get containing methods: {e}")
            return {}

    def _detect_inter_procedural(
        self,
        source_id: int,
        sink_id: int,
        method_map: Dict[int, Optional[str]]
    ) -> bool:
        """
        Detect if a flow is inter-procedural (crosses function boundaries).

        Args:
            source_id: Source node ID (definition)
            sink_id: Sink node ID (use)
            method_map: Mapping from node_id to containing method

        Returns:
            True if flow crosses function boundaries
        """
        source_method = method_map.get(source_id)
        sink_method = method_map.get(sink_id)

        if source_method is None or sink_method is None:
            return False

        return source_method != sink_method
