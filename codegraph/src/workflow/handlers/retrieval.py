"""Retrieval Handler for CPG query and retrieval operations.

Handles:
- SQL query execution against DuckDB CPG
- Result formatting and filtering
- Query caching
- Error handling with fallback strategies
"""
import logging
import time
from typing import Any, Dict, List, Optional, Union

from .base import BaseHandler, HandlerResult

logger = logging.getLogger(__name__)


class RetrievalHandler(BaseHandler):
    """
    Handler for CPG query and retrieval operations.

    Executes SQL queries against the DuckDB CPG database,
    formats results, and handles errors with fallback strategies.
    """

    def __init__(
        self,
        cpg_client=None,
        cache_enabled: bool = True,
        max_results: int = 100,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize retrieval handler.

        Args:
            cpg_client: DuckDBCPGClient instance for queries
            cache_enabled: Whether to cache query results
            max_results: Maximum results to return per query
            config: Additional configuration
        """
        super().__init__(config)
        self._cpg_client = cpg_client
        self.cache_enabled = cache_enabled
        self.max_results = max_results
        self._cache: Dict[str, Any] = {}

    def set_cpg_client(self, client):
        """Set or update the CPG client."""
        self._cpg_client = client
        self.log_info("CPG client updated")

    def handle(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        format_as: str = "dict",
        use_cache: bool = True
    ) -> HandlerResult:
        """
        Execute a CPG query and return formatted results.

        Args:
            query: SQL query string
            params: Optional query parameters
            format_as: Result format ("dict", "list", "raw")
            use_cache: Whether to use cached results

        Returns:
            HandlerResult with query results
        """
        start_time = time.time()

        try:
            # Check cache
            cache_key = self._make_cache_key(query, params)
            if use_cache and self.cache_enabled and cache_key in self._cache:
                self.log_debug(f"Cache hit for query: {query[:50]}...")
                cached_result = self._cache[cache_key]
                duration_ms = (time.time() - start_time) * 1000
                self._track_call(duration_ms, True)
                return HandlerResult(
                    success=True,
                    data=cached_result,
                    duration_ms=duration_ms,
                    metadata={"cached": True}
                )

            # Execute query
            if not self._cpg_client:
                raise RuntimeError("CPG client not initialized")

            self.log_debug(f"Executing query: {query[:100]}...")
            raw_results = self._cpg_client.execute_sql_dict(query)

            # Apply limit
            if len(raw_results) > self.max_results:
                self.log_warning(
                    f"Results truncated: {len(raw_results)} -> {self.max_results}"
                )
                raw_results = raw_results[:self.max_results]

            # Format results
            formatted = self._format_results(raw_results, format_as)

            # Cache results
            if use_cache and self.cache_enabled:
                self._cache[cache_key] = formatted

            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, True)

            self.log_info(f"Query returned {len(raw_results)} results in {duration_ms:.1f}ms")

            return HandlerResult(
                success=True,
                data=formatted,
                duration_ms=duration_ms,
                metadata={
                    "row_count": len(raw_results),
                    "cached": False,
                    "truncated": len(raw_results) >= self.max_results
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, False)
            self.log_error(f"Query failed: {e}")

            return HandlerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    def execute_batch(
        self,
        queries: List[str],
        stop_on_error: bool = False
    ) -> List[HandlerResult]:
        """
        Execute multiple queries in batch.

        Args:
            queries: List of SQL queries
            stop_on_error: Stop on first error if True

        Returns:
            List of HandlerResult for each query
        """
        results = []

        for i, query in enumerate(queries):
            self.log_debug(f"Batch query {i+1}/{len(queries)}")
            result = self.handle(query)
            results.append(result)

            if not result.success and stop_on_error:
                self.log_warning(f"Batch stopped at query {i+1} due to error")
                break

        success_count = sum(1 for r in results if r.success)
        self.log_info(f"Batch complete: {success_count}/{len(queries)} successful")

        return results

    def find_methods(
        self,
        name_pattern: str,
        exact: bool = False,
        limit: int = 50
    ) -> HandlerResult:
        """
        Find methods by name pattern.

        Args:
            name_pattern: Method name or LIKE pattern
            exact: If True, exact match; if False, LIKE pattern
            limit: Maximum results

        Returns:
            HandlerResult with matching methods
        """
        if exact:
            query = f"""
                SELECT id, name, full_name, filename, line_number, signature
                FROM nodes_method
                WHERE name = '{name_pattern}'
                LIMIT {limit}
            """
        else:
            query = f"""
                SELECT id, name, full_name, filename, line_number, signature
                FROM nodes_method
                WHERE name ILIKE '%{name_pattern}%'
                LIMIT {limit}
            """

        return self.handle(query)

    def find_calls_to(
        self,
        method_name: str,
        limit: int = 100
    ) -> HandlerResult:
        """
        Find all calls to a method.

        Args:
            method_name: Target method name
            limit: Maximum results

        Returns:
            HandlerResult with call sites
        """
        query = f"""
            SELECT
                c.id as call_id,
                c.name as called_method,
                c.code as call_code,
                c.filename,
                c.line_number,
                m.name as caller_method
            FROM nodes_call c
            LEFT JOIN nodes_method m ON c.containing_method_id = m.id
            WHERE c.name ILIKE '%{method_name}%'
            LIMIT {limit}
        """

        return self.handle(query)

    def get_method_with_context(
        self,
        method_id: int
    ) -> HandlerResult:
        """
        Get method with full context (calls, callees, comments).

        Args:
            method_id: Method node ID

        Returns:
            HandlerResult with method context
        """
        # Get method info
        method_query = f"""
            SELECT * FROM nodes_method WHERE id = {method_id}
        """
        method_result = self.handle(method_query)

        if not method_result.success or not method_result.data:
            return method_result

        method = method_result.data[0] if method_result.data else None

        # Get calls within method
        calls_query = f"""
            SELECT name, code, line_number
            FROM nodes_call
            WHERE containing_method_id = {method_id}
            ORDER BY line_number
        """
        calls_result = self.handle(calls_query, use_cache=False)

        # Get comments
        comments_query = f"""
            SELECT code, line_number
            FROM nodes_comment
            WHERE containing_method_id = {method_id}
            ORDER BY line_number
        """
        comments_result = self.handle(comments_query, use_cache=False)

        context = {
            "method": method,
            "calls": calls_result.data if calls_result.success else [],
            "comments": comments_result.data if comments_result.success else []
        }

        return HandlerResult(
            success=True,
            data=context,
            metadata={"method_id": method_id}
        )

    def clear_cache(self):
        """Clear query cache."""
        self._cache.clear()
        self.log_info("Cache cleared")

    def _make_cache_key(
        self,
        query: str,
        params: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key from query and params."""
        import hashlib
        key_str = query + str(sorted(params.items()) if params else "")
        return hashlib.md5(key_str.encode()).hexdigest()

    def _format_results(
        self,
        results: List[Dict[str, Any]],
        format_as: str
    ) -> Union[List[Dict], List[List], List]:
        """
        Format query results.

        Args:
            results: Raw query results
            format_as: Target format

        Returns:
            Formatted results
        """
        if format_as == "dict":
            return results
        elif format_as == "list":
            if not results:
                return []
            keys = list(results[0].keys())
            return [[row.get(k) for k in keys] for row in results]
        elif format_as == "raw":
            return results
        else:
            self.log_warning(f"Unknown format '{format_as}', using dict")
            return results
