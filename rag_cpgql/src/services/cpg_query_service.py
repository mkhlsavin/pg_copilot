"""
Unified CPG Query Service for DuckDB.

Provides high-level API for common CPG queries used across scenarios.
All queries leverage the enriched tag data (15.68M tags, 98 categories).
"""

import duckdb
import networkx as nx
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path


class CPGQueryService:
    """
    Unified service for querying CPG data from DuckDB.

    Architecture:
    - Wraps DuckDB connection to cpg.duckdb
    - Provides scenario-specific query methods
    - Returns structured data (dicts, lists, graphs)
    - Handles connection pooling and error recovery
    """

    def __init__(self, db_path: str = "cpg.duckdb"):
        """
        Initialize CPG query service.

        Args:
            db_path: Path to DuckDB CPG database
        """
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish connection to DuckDB"""
        try:
            self.conn = duckdb.connect(self.db_path, read_only=True)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.db_path}: {e}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== CORE QUERY EXECUTION ====================

    def execute_query(
        self,
        query: str,
        parameters: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dicts.

        This is the primary query execution method used by all agents.
        Provides a consistent interface for both parameterized and non-parameterized queries.

        Args:
            query: SQL query to execute
            parameters: Optional tuple of query parameters

        Returns:
            List of result rows as dictionaries

        Raises:
            Exception: If query execution fails
        """
        try:
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)

            # Fetch all results
            rows = result.fetchall()

            # Convert to list of dicts using column names
            if not rows:
                return []

            column_names = [desc[0] for desc in result.description]

            return [
                dict(zip(column_names, row))
                for row in rows
            ]

        except Exception as e:
            raise Exception(f"Query execution failed: {e}\nQuery: {query[:200]}...")

    def execute_custom_sql(
        self,
        query: str,
        parameters: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Alias for execute_query() for backward compatibility.

        Args:
            query: SQL query to execute
            parameters: Optional tuple of query parameters

        Returns:
            List of result rows as dictionaries
        """
        return self.execute_query(query, parameters)

    # ==================== SUBSYSTEM QUERIES ====================

    def get_subsystems(self) -> List[Dict[str, Any]]:
        """
        Get all subsystems in the codebase.

        Returns:
            List of subsystems with name, path, method count
        """
        query = """
        SELECT
            t.value as subsystem_name,
            COUNT(DISTINCT m.id) as method_count,
            COUNT(DISTINCT m.filename) as file_count
        FROM nodes_tag t
        JOIN edges_tagged_by e ON t.id = e.dst
        JOIN nodes_method m ON e.src = m.id
        WHERE t.name = 'subsystem-name'
        GROUP BY t.value
        ORDER BY method_count DESC
        """

        results = self.conn.execute(query).fetchall()

        return [
            {
                "name": row[0],
                "method_count": row[1],
                "file_count": row[2]
            }
            for row in results
        ]

    def get_methods_by_subsystem(
        self,
        subsystem: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get methods belonging to a specific subsystem.

        Args:
            subsystem: Subsystem name (e.g., 'executor', 'planner')
            limit: Maximum number of methods to return

        Returns:
            List of methods with id, name, filename, signature
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.signature,
            m.line_number
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'subsystem-name'
          AND t.value = ?
        ORDER BY m.filename, m.line_number
        LIMIT ?
        """

        results = self.conn.execute(query, [subsystem, limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "signature": row[3],
                "line_number": row[4]
            }
            for row in results
        ]

    # ==================== CALL GRAPH QUERIES ====================

    def get_call_graph(
        self,
        method_id: int,
        depth: int = 2,
        direction: str = "both"
    ) -> nx.DiGraph:
        """
        Get call graph centered on a method.

        Args:
            method_id: Starting method ID
            depth: How many call levels to traverse
            direction: "callers", "callees", or "both"

        Returns:
            NetworkX directed graph with method nodes and call edges
        """
        G = nx.DiGraph()

        # Get initial method
        method = self._get_method_by_id(method_id)
        if not method:
            return G

        G.add_node(method_id, **method)

        # BFS traversal for callees
        if direction in ["callees", "both"]:
            self._traverse_callees(G, method_id, depth)

        # BFS traversal for callers
        if direction in ["callers", "both"]:
            self._traverse_callers(G, method_id, depth)

        return G

    def _get_method_by_id(self, method_id: int) -> Optional[Dict[str, Any]]:
        """Get method metadata by ID"""
        query = "SELECT id, name, filename, signature FROM nodes_method WHERE id = ?"
        result = self.conn.execute(query, [method_id]).fetchone()

        if result:
            return {
                "id": result[0],
                "name": result[1],
                "filename": result[2],
                "signature": result[3]
            }
        return None

    def _traverse_callees(self, G: nx.DiGraph, start_id: int, max_depth: int):
        """Traverse call graph in callee direction (who this calls)"""
        visited = set()
        queue = [(start_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited:
                continue

            visited.add(current_id)

            # Get callees
            query = """
            SELECT dst, receiver_method_name
            FROM edges_call
            WHERE src = ?
            """

            callees = self.conn.execute(query, [current_id]).fetchall()

            for callee_id, call_name in callees:
                # Add callee node
                if callee_id not in G:
                    callee = self._get_method_by_id(callee_id)
                    if callee:
                        G.add_node(callee_id, **callee)

                # Add edge
                G.add_edge(current_id, callee_id, call_name=call_name)

                # Continue traversal
                queue.append((callee_id, depth + 1))

    def _traverse_callers(self, G: nx.DiGraph, start_id: int, max_depth: int):
        """Traverse call graph in caller direction (who calls this)"""
        visited = set()
        queue = [(start_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited:
                continue

            visited.add(current_id)

            # Get callers
            query = """
            SELECT src, receiver_method_name
            FROM edges_call
            WHERE dst = ?
            """

            callers = self.conn.execute(query, [current_id]).fetchall()

            for caller_id, call_name in callers:
                # Add caller node
                if caller_id not in G:
                    caller = self._get_method_by_id(caller_id)
                    if caller:
                        G.add_node(caller_id, **caller)

                # Add edge
                G.add_edge(caller_id, current_id, call_name=call_name)

                # Continue traversal
                queue.append((caller_id, depth + 1))

    # ==================== SECURITY QUERIES ====================

    def get_security_hotspots(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find methods tagged with security risks.

        Returns:
            Methods with security-risk tags
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.line_number,
            t.value as risk_level
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'security-risk'
        ORDER BY
            CASE t.value
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            m.filename
        LIMIT ?
        """

        results = self.conn.execute(query, [limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "line_number": row[3],
                "risk_level": row[4]
            }
            for row in results
        ]

    def get_taint_sources(self) -> List[Dict[str, Any]]:
        """
        Find methods that handle untrusted input (taint sources).

        Returns:
            Methods with taint-source tags
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.signature
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'taint-source'
        ORDER BY m.filename, m.line_number
        """

        results = self.conn.execute(query).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "signature": row[3]
            }
            for row in results
        ]

    # ==================== PERFORMANCE QUERIES ====================

    def get_performance_hotspots(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find methods tagged as performance hotspots.

        Returns:
            Methods with perf-hotspot tags
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.line_number,
            m.signature
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'perf-hotspot'
        ORDER BY m.filename
        LIMIT ?
        """

        results = self.conn.execute(query, [limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "line_number": row[3],
                "signature": row[4]
            }
            for row in results
        ]

    def get_allocation_heavy_methods(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find methods with heavy memory allocation.

        Returns:
            Methods with allocation-heavy tags
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.line_number
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'allocation-heavy'
        ORDER BY m.filename
        LIMIT ?
        """

        results = self.conn.execute(query, [limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "line_number": row[3]
            }
            for row in results
        ]

    # ==================== TEST COVERAGE QUERIES ====================

    def get_methods_without_tests(
        self,
        subsystem: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find methods that lack test coverage.

        Args:
            subsystem: Optional filter by subsystem
            limit: Maximum results

        Returns:
            Methods without test-coverage tags
        """
        base_query = """
        SELECT
            m.id,
            m.name,
            m.filename,
            m.signature
        FROM nodes_method m
        WHERE NOT EXISTS (
            SELECT 1 FROM edges_tagged_by e
            JOIN nodes_tag t ON e.dst = t.id
            WHERE e.src = m.id AND t.name = 'test-coverage'
        )
        """

        if subsystem:
            base_query += """
            AND EXISTS (
                SELECT 1 FROM edges_tagged_by e2
                JOIN nodes_tag t2 ON e2.dst = t2.id
                WHERE e2.src = m.id
                  AND t2.name = 'subsystem-name'
                  AND t2.value = ?
            )
            """
            results = self.conn.execute(base_query + " LIMIT ?", [subsystem, limit]).fetchall()
        else:
            results = self.conn.execute(base_query + " LIMIT ?", [limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "signature": row[3]
            }
            for row in results
        ]

    # ==================== CODE QUALITY QUERIES ====================

    def get_complex_methods(
        self,
        min_complexity: int = 10,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find methods with high cyclomatic complexity.

        Args:
            min_complexity: Minimum complexity threshold
            limit: Maximum results

        Returns:
            Methods with cyclomatic-complexity >= threshold
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            m.line_number,
            CAST(t.value AS INTEGER) as complexity
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'cyclomatic-complexity'
          AND CAST(t.value AS INTEGER) >= ?
        ORDER BY complexity DESC
        LIMIT ?
        """

        results = self.conn.execute(query, [min_complexity, limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "line_number": row[3],
                "complexity": row[4]
            }
            for row in results
        ]

    # ==================== SEMANTIC QUERIES ====================

    def search_by_function_purpose(
        self,
        purpose_keyword: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search methods by semantic purpose description.

        Args:
            purpose_keyword: Keyword to search in function-purpose tags
            limit: Maximum results

        Returns:
            Methods with matching purpose descriptions
        """
        query = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.filename,
            t.value as purpose
        FROM nodes_method m
        JOIN edges_tagged_by e ON m.id = e.src
        JOIN nodes_tag t ON e.dst = t.id
        WHERE t.name = 'function-purpose'
          AND t.value LIKE ?
        ORDER BY m.filename
        LIMIT ?
        """

        search_pattern = f"%{purpose_keyword}%"
        results = self.conn.execute(query, [search_pattern, limit]).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "filename": row[2],
                "purpose": row[3]
            }
            for row in results
        ]

    # ==================== STATISTICS QUERIES ====================

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall CPG database statistics.

        Returns:
            Dict with node counts, edge counts, tag categories
        """
        stats = {}

        # Method count
        stats["method_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM nodes_method"
        ).fetchone()[0]

        # Tag count
        stats["tag_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM nodes_tag"
        ).fetchone()[0]

        # Tag categories
        stats["tag_categories"] = self.conn.execute(
            "SELECT COUNT(DISTINCT name) FROM nodes_tag"
        ).fetchone()[0]

        # Tagged relationships
        stats["tagged_edges"] = self.conn.execute(
            "SELECT COUNT(*) FROM edges_tagged_by"
        ).fetchone()[0]

        # Call edges
        stats["call_edges"] = self.conn.execute(
            "SELECT COUNT(*) FROM edges_call"
        ).fetchone()[0]

        return stats

    # ==================== COMMENT QUERIES ====================

    def get_method_comments(
        self,
        method_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get comments associated with a method.

        Args:
            method_name: Name of the method
            limit: Maximum number of comments to return

        Returns:
            List of comments with code, line_number, filename
        """
        query = """
        SELECT c.id, c.code, c.filename, c.line_number, c.column_number
        FROM nodes_comment c
        JOIN edges_source_file e ON c.id = e.src
        JOIN nodes_method m ON e.dst = m.id
        WHERE m.name = ?
        ORDER BY c.line_number
        LIMIT ?
        """

        results = self.conn.execute(query, [method_name, limit]).fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "filename": row[2],
                "line_number": row[3],
                "column_number": row[4]
            }
            for row in results
        ]

    def get_file_comments(
        self,
        filename: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all comments in a file.

        Args:
            filename: Filename or partial path to match
            limit: Maximum number of comments to return

        Returns:
            List of comments ordered by line number
        """
        query = """
        SELECT id, code, filename, line_number, column_number
        FROM nodes_comment
        WHERE filename LIKE ?
        ORDER BY line_number
        LIMIT ?
        """

        results = self.conn.execute(query, [f"%{filename}%", limit]).fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "filename": row[2],
                "line_number": row[3],
                "column_number": row[4]
            }
            for row in results
        ]

    def search_comments(
        self,
        pattern: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Full-text search in comments.

        Args:
            pattern: Text pattern to search for
            limit: Maximum number of results

        Returns:
            List of matching comments
        """
        query = """
        SELECT id, code, filename, line_number
        FROM nodes_comment
        WHERE code ILIKE ?
        LIMIT ?
        """

        results = self.conn.execute(query, [f"%{pattern}%", limit]).fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "filename": row[2],
                "line_number": row[3]
            }
            for row in results
        ]

    def get_todo_comments(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find TODO/FIXME/HACK comments in the codebase.

        Args:
            limit: Maximum number of results

        Returns:
            List of TODO-style comments with priority indicators
        """
        query = """
        SELECT id, code, filename, line_number,
            CASE
                WHEN code ILIKE '%FIXME%' THEN 'FIXME'
                WHEN code ILIKE '%TODO%' THEN 'TODO'
                WHEN code ILIKE '%HACK%' THEN 'HACK'
                WHEN code ILIKE '%XXX%' THEN 'XXX'
                ELSE 'NOTE'
            END as comment_type
        FROM nodes_comment
        WHERE code ILIKE '%TODO%'
           OR code ILIKE '%FIXME%'
           OR code ILIKE '%HACK%'
           OR code ILIKE '%XXX%'
        ORDER BY
            CASE
                WHEN code ILIKE '%FIXME%' THEN 1
                WHEN code ILIKE '%HACK%' THEN 2
                WHEN code ILIKE '%TODO%' THEN 3
                ELSE 4
            END,
            filename, line_number
        LIMIT ?
        """

        results = self.conn.execute(query, [limit]).fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "filename": row[2],
                "line_number": row[3],
                "comment_type": row[4]
            }
            for row in results
        ]

    def get_comment_statistics(self) -> Dict[str, Any]:
        """
        Get comment statistics for the codebase.

        Returns:
            Dict with comment counts and distribution
        """
        stats = {}

        # Total comment count
        try:
            stats["total_comments"] = self.conn.execute(
                "SELECT COUNT(*) FROM nodes_comment"
            ).fetchone()[0]
        except Exception:
            stats["total_comments"] = 0

        # Comments per file (top 10)
        try:
            results = self.conn.execute("""
                SELECT filename, COUNT(*) as cnt
                FROM nodes_comment
                GROUP BY filename
                ORDER BY cnt DESC
                LIMIT 10
            """).fetchall()
            stats["top_commented_files"] = [
                {"filename": r[0], "count": r[1]} for r in results
            ]
        except Exception:
            stats["top_commented_files"] = []

        # TODO/FIXME counts
        try:
            stats["todo_count"] = self.conn.execute(
                "SELECT COUNT(*) FROM nodes_comment WHERE code ILIKE '%TODO%'"
            ).fetchone()[0]
            stats["fixme_count"] = self.conn.execute(
                "SELECT COUNT(*) FROM nodes_comment WHERE code ILIKE '%FIXME%'"
            ).fetchone()[0]
        except Exception:
            stats["todo_count"] = 0
            stats["fixme_count"] = 0

        return stats
