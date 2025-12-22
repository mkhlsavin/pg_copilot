"""Path Finding in Call Graphs.

Implements shortest path and transitive closure algorithms.
"""
import logging
from typing import List, Optional, Dict, Any

from .base import BaseAnalyzer
from .models import CallPath

logger = logging.getLogger(__name__)


class PathFinder(BaseAnalyzer):
    """Find paths between methods in the call graph.

    Methods:
    - find_shortest_path: Find shortest call chain between methods
    - find_all_callers: Find all methods calling a given method
    - find_all_callees: Find all methods called by a given method
    """

    def find_shortest_path(
        self,
        source_method: str,
        target_method: str,
        max_depth: int = 10
    ) -> Optional[CallPath]:
        """
        Find shortest call path from source to target method.

        Uses SQL/PGQ: ANY SHORTEST (source)-[:CALL]->+(target)

        Args:
            source_method: Starting method name
            target_method: Target method name
            max_depth: Maximum path length to consider

        Returns:
            CallPath if path exists, None otherwise

        Example:
            path = finder.find_shortest_path('main', 'malloc')
            # Returns: main -> foo -> bar -> malloc (length=3)
        """
        query = """
            WITH RECURSIVE call_path AS (
                -- Base case: direct calls from source method
                SELECT
                    ec.dst AS to_method,
                    1 AS depth,
                    CAST(ec.dst AS VARCHAR) AS path
                FROM nodes_method src
                JOIN nodes_call nc ON nc.containing_method_id = src.id
                JOIN edges_call ec ON ec.src = nc.id
                WHERE src.name = ?

                UNION ALL

                -- Recursive case: extend path
                SELECT
                    ec.dst,
                    cp.depth + 1,
                    cp.path || ',' || CAST(ec.dst AS VARCHAR)
                FROM call_path cp
                JOIN nodes_call nc ON nc.containing_method_id = cp.to_method
                JOIN edges_call ec ON ec.src = nc.id
                WHERE cp.depth < ?
            )
            SELECT
                ? AS source_name,
                tgt.name AS target_name,
                cp.depth AS path_length,
                cp.path
            FROM call_path cp
            JOIN nodes_method tgt ON tgt.id = cp.to_method
            WHERE tgt.name = ?
            ORDER BY cp.depth
            LIMIT 1;
        """

        try:
            results = self._execute(query, (source_method, max_depth, source_method, target_method))

            if not results:
                logger.info(f"No path found from {source_method} to {target_method}")
                return None

            result = results[0]

            # Parse intermediate methods from path
            path_ids = result.get('path', '').split(',')
            intermediate = []
            if len(path_ids) > 2:
                intermediate_query = """
                    SELECT name FROM nodes_method
                    WHERE id IN ({})
                """.format(','.join(['?'] * (len(path_ids) - 2)))
                inter_results = self._execute(
                    intermediate_query,
                    tuple(path_ids[1:-1])
                )
                intermediate = [r.get('name', '') for r in inter_results]

            return CallPath(
                source_method=result.get('source_name', source_method),
                target_method=result.get('target_name', target_method),
                path_length=result.get('depth', 0),
                intermediate_methods=intermediate,
                path_type="transitive" if result.get('depth', 0) > 1 else "direct"
            )

        except Exception as e:
            logger.error(f"Error finding shortest path: {e}")
            return None

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
        if direct_only:
            query = """
                SELECT DISTINCT m.name AS caller_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.containing_method_id = m.id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method target ON ec.dst = target.id
                WHERE target.name = ?
                ORDER BY caller_name;
            """
            params = (method_name,)
        else:
            query = """
                WITH RECURSIVE callers AS (
                    -- Base: direct callers
                    SELECT DISTINCT
                        m.id AS caller_id,
                        m.name AS caller_name,
                        1 AS depth
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    WHERE target.name = ?

                    UNION

                    -- Recursive: callers of callers
                    SELECT DISTINCT
                        m.id,
                        m.name,
                        c.depth + 1
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN callers c ON ec.dst = c.caller_id
                    WHERE c.depth < ?
                )
                SELECT DISTINCT caller_name
                FROM callers
                ORDER BY caller_name;
            """
            params = (method_name, max_depth)

        try:
            results = self._execute(query, params)
            callers = [r.get('caller_name', '') for r in results if r.get('caller_name')]

            # Fallback to call_containment table
            if not callers:
                fallback_query = """
                    SELECT DISTINCT containing_method_name AS caller_name
                    FROM call_containment
                    WHERE callee_name = ?
                      AND containing_method_name IS NOT NULL
                      AND containing_method_name != ''
                      AND NOT containing_method_name LIKE '<%'
                    ORDER BY caller_name
                    LIMIT 100
                """
                try:
                    fallback_results = self._execute(fallback_query, (method_name,))
                    callers = [r.get('caller_name', '') for r in fallback_results if r.get('caller_name')]
                    if callers:
                        logger.info(f"Found {len(callers)} callers from call_containment fallback")
                except Exception as fallback_error:
                    logger.debug(f"call_containment fallback failed: {fallback_error}")

            logger.info(f"Found {len(callers)} callers for {method_name}")
            return callers
        except Exception as e:
            logger.error(f"Error finding callers: {e}")
            return []

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
        if direct_only:
            query = """
                SELECT DISTINCT target.name AS callee_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.containing_method_id = m.id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method target ON ec.dst = target.id
                WHERE m.name = ?
                ORDER BY callee_name;
            """
            params = (method_name,)
        else:
            query = """
                WITH RECURSIVE callees AS (
                    -- Base: direct callees
                    SELECT DISTINCT
                        target.id AS callee_id,
                        target.name AS callee_name,
                        1 AS depth
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    WHERE m.name = ?

                    UNION

                    -- Recursive: callees of callees
                    SELECT DISTINCT
                        target.id,
                        target.name,
                        c.depth + 1
                    FROM nodes_call nc
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    JOIN callees c ON nc.containing_method_id = c.callee_id
                    WHERE c.depth < ?
                )
                SELECT DISTINCT callee_name
                FROM callees
                ORDER BY callee_name;
            """
            params = (method_name, max_depth)

        try:
            results = self._execute(query, params)
            callees = [
                r.get('callee_name', '')
                for r in results
                if r.get('callee_name')
                and not r.get('callee_name', '').startswith('<')
                and r.get('callee_name') not in ('true', 'false', 'NULL', 'null', '')
            ]

            # Fallback to call_containment table
            if not callees:
                fallback_query = """
                    SELECT DISTINCT callee_name
                    FROM call_containment
                    WHERE containing_method_name = ?
                      AND callee_name IS NOT NULL
                      AND callee_name != ''
                      AND NOT callee_name LIKE '<%'
                    ORDER BY callee_name
                    LIMIT 100
                """
                try:
                    fallback_results = self._execute(fallback_query, (method_name,))
                    callees = [r.get('callee_name', '') for r in fallback_results if r.get('callee_name')]
                    if callees:
                        logger.info(f"Found {len(callees)} callees from call_containment fallback")
                except Exception as fallback_error:
                    logger.debug(f"call_containment fallback failed: {fallback_error}")

            logger.info(f"Found {len(callees)} callees for {method_name}")
            return callees
        except Exception as e:
            logger.error(f"Error finding callees: {e}")
            return []
