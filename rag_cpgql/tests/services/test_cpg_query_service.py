"""
Tests for CPG Query Service.

Tests for CPGQueryService including query execution, subsystem queries,
call graph analysis, security queries, and statistics.
"""

import pytest
from unittest.mock import MagicMock, patch
import networkx as nx


class MockCursor:
    """Mock DuckDB cursor for testing."""

    def __init__(self, rows=None, description=None):
        self._rows = rows or []
        self.description = description or []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class MockConnection:
    """Mock DuckDB connection for testing."""

    def __init__(self):
        self.queries = []
        self._results = {}
        self._closed = False

    def execute(self, query, params=None):
        self.queries.append((query, params))
        # Return mock cursor with default empty results
        return MockCursor(rows=[], description=[])

    def close(self):
        self._closed = True


class TestCPGQueryServiceInit:
    """Tests for CPGQueryService initialization."""

    def test_init_connects_to_db(self):
        """Test initialization connects to database."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MockConnection()
            mock_duckdb.connect.return_value = mock_conn

            service = CPGQueryService(db_path="test.duckdb")

            mock_duckdb.connect.assert_called_once_with("test.duckdb", read_only=True)
            assert service.conn is mock_conn

    def test_init_connection_failure(self):
        """Test initialization with connection failure."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_duckdb.connect.side_effect = Exception("Connection failed")

            with pytest.raises(ConnectionError) as exc_info:
                CPGQueryService(db_path="bad.duckdb")

            assert "Failed to connect" in str(exc_info.value)

    def test_close_connection(self):
        """Test closing database connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MockConnection()
            mock_duckdb.connect.return_value = mock_conn

            service = CPGQueryService()
            service.close()

            assert mock_conn._closed is True
            assert service.conn is None

    def test_context_manager(self):
        """Test context manager protocol."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MockConnection()
            mock_duckdb.connect.return_value = mock_conn

            with CPGQueryService() as service:
                assert service.conn is mock_conn

            assert mock_conn._closed is True

    def test_set_database(self):
        """Test switching to different database."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn1 = MockConnection()
            mock_conn2 = MockConnection()
            mock_duckdb.connect.side_effect = [mock_conn1, mock_conn2]

            service = CPGQueryService(db_path="db1.duckdb")
            service.set_database("db2.duckdb")

            assert mock_conn1._closed is True
            assert service.db_path == "db2.duckdb"


class TestExecuteQuery:
    """Tests for query execution methods."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_execute_query_returns_dicts(self, service):
        """Test execute_query returns list of dicts."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "test_method", "test.c"),
            (2, "another_method", "another.c"),
        ]
        mock_result.description = [("id",), ("name",), ("filename",)]
        service.conn.execute.return_value = mock_result

        results = service.execute_query("SELECT id, name, filename FROM methods")

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["name"] == "test_method"
        assert results[1]["filename"] == "another.c"

    def test_execute_query_empty_results(self, service):
        """Test execute_query with empty results."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        service.conn.execute.return_value = mock_result

        results = service.execute_query("SELECT * FROM empty_table")

        assert results == []

    def test_execute_query_with_parameters(self, service):
        """Test execute_query with parameters."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "method")]
        mock_result.description = [("id",), ("name",)]
        service.conn.execute.return_value = mock_result

        results = service.execute_query(
            "SELECT * FROM methods WHERE id = ?",
            parameters=(123,)
        )

        service.conn.execute.assert_called_with(
            "SELECT * FROM methods WHERE id = ?",
            (123,)
        )
        assert len(results) == 1

    def test_execute_query_failure(self, service):
        """Test execute_query handles errors."""
        service.conn.execute.side_effect = Exception("Query error")

        with pytest.raises(Exception) as exc_info:
            service.execute_query("INVALID SQL")

        assert "Query execution failed" in str(exc_info.value)

    def test_execute_custom_sql_alias(self, service):
        """Test execute_custom_sql is alias for execute_query."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,)]
        mock_result.description = [("count",)]
        service.conn.execute.return_value = mock_result

        results = service.execute_custom_sql("SELECT COUNT(*) FROM methods")

        assert len(results) == 1


class TestSubsystemQueries:
    """Tests for subsystem-related queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_subsystems(self, service):
        """Test getting subsystems."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("executor", 500, 50),
            ("planner", 300, 30),
            ("parser", 200, 20),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_subsystems()

        assert len(results) == 3
        assert results[0]["name"] == "executor"
        assert results[0]["method_count"] == 500
        assert results[0]["file_count"] == 50

    def test_get_methods_by_subsystem(self, service):
        """Test getting methods by subsystem."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "ExecInitNode", "executor.c", "void ExecInitNode(...)", 100),
            (2, "ExecProcNode", "executor.c", "TupleTableSlot* ExecProcNode(...)", 200),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_methods_by_subsystem("executor", limit=10)

        assert len(results) == 2
        assert results[0]["name"] == "ExecInitNode"
        assert results[0]["filename"] == "executor.c"
        service.conn.execute.assert_called_once()


class TestCallGraphQueries:
    """Tests for call graph analysis."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_call_graph_empty(self, service):
        """Test get_call_graph for nonexistent method."""
        service.conn.execute.return_value.fetchone.return_value = None

        graph = service.get_call_graph(method_id=999)

        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes()) == 0

    def test_get_call_graph_basic(self, service):
        """Test get_call_graph returns graph."""
        # Mock method lookup
        def execute_side_effect(query, params=None):
            result = MagicMock()
            if "FROM nodes_method WHERE id" in query:
                result.fetchone.return_value = (1, "main", "main.c", "int main()")
            elif "FROM edges_call" in query:
                result.fetchall.return_value = []
            else:
                result.fetchall.return_value = []
            return result

        service.conn.execute.side_effect = execute_side_effect

        graph = service.get_call_graph(method_id=1, depth=1)

        assert isinstance(graph, nx.DiGraph)
        assert 1 in graph.nodes()

    def test_get_method_by_id(self, service):
        """Test _get_method_by_id helper."""
        service.conn.execute.return_value.fetchone.return_value = (
            1, "test_method", "test.c", "void test_method()"
        )

        result = service._get_method_by_id(1)

        assert result["id"] == 1
        assert result["name"] == "test_method"
        assert result["filename"] == "test.c"

    def test_get_method_by_id_not_found(self, service):
        """Test _get_method_by_id for nonexistent method."""
        service.conn.execute.return_value.fetchone.return_value = None

        result = service._get_method_by_id(999)

        assert result is None


class TestSecurityQueries:
    """Tests for security-related queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_security_hotspots(self, service):
        """Test getting security hotspots."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "parse_input", "parser.c", 100, "high"),
            (2, "exec_query", "executor.c", 200, "medium"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_security_hotspots(limit=10)

        assert len(results) == 2
        assert results[0]["name"] == "parse_input"
        assert results[0]["risk_level"] == "high"

    def test_get_taint_sources(self, service):
        """Test getting taint sources."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "read_input", "input.c", "char* read_input()"),
            (2, "get_request", "network.c", "Request* get_request()"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_taint_sources()

        assert len(results) == 2
        assert results[0]["name"] == "read_input"


class TestPerformanceQueries:
    """Tests for performance-related queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_performance_hotspots(self, service):
        """Test getting performance hotspots."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "heavy_loop", "process.c", 100, "void heavy_loop()"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_performance_hotspots(limit=10)

        assert len(results) == 1
        assert results[0]["name"] == "heavy_loop"

    def test_get_allocation_heavy_methods(self, service):
        """Test getting allocation-heavy methods."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "alloc_buffer", "memory.c", 50),
            (2, "create_objects", "objects.c", 100),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_allocation_heavy_methods(limit=10)

        assert len(results) == 2
        assert results[0]["name"] == "alloc_buffer"


class TestTestCoverageQueries:
    """Tests for test coverage queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_methods_without_tests(self, service):
        """Test getting methods without test coverage."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "untested_func", "module.c", "void untested_func()"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_methods_without_tests(limit=10)

        assert len(results) == 1
        assert results[0]["name"] == "untested_func"

    def test_get_methods_without_tests_by_subsystem(self, service):
        """Test getting untested methods by subsystem."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "exec_untested", "executor.c", "void exec_untested()"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_methods_without_tests(
            subsystem="executor",
            limit=10
        )

        assert len(results) == 1
        # Should include subsystem parameter in query
        call_args = service.conn.execute.call_args
        assert "executor" in call_args[0][1]


class TestCodeQualityQueries:
    """Tests for code quality queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_complex_methods(self, service):
        """Test getting complex methods."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "complex_func", "complex.c", 50, 25),
            (2, "another_complex", "another.c", 100, 15),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_complex_methods(min_complexity=10, limit=10)

        assert len(results) == 2
        assert results[0]["complexity"] == 25

    def test_search_by_function_purpose(self, service):
        """Test searching by function purpose."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "init_memory", "memory.c", "initializes memory pool"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.search_by_function_purpose("memory", limit=10)

        assert len(results) == 1
        assert results[0]["purpose"] == "initializes memory pool"


class TestStatisticsQueries:
    """Tests for database statistics."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_database_stats(self, service):
        """Test getting database statistics."""
        # Mock multiple execute calls
        service.conn.execute.return_value.fetchone.side_effect = [
            (5000,),  # method_count
            (100000,),  # tag_count
            (98,),  # tag_categories
            (50000,),  # tagged_edges
            (25000,),  # call_edges
        ]

        stats = service.get_database_stats()

        assert stats["method_count"] == 5000
        assert stats["tag_count"] == 100000
        assert stats["tag_categories"] == 98
        assert stats["tagged_edges"] == 50000
        assert stats["call_edges"] == 25000


class TestCommentQueries:
    """Tests for comment-related queries."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_get_method_comments(self, service):
        """Test getting comments for a method."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "/* Init function */", "test.c", 10, 0),
            (2, "// Helper comment", "test.c", 15, 4),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_method_comments("test_func", limit=10)

        assert len(results) == 2
        assert "Init function" in results[0]["code"]

    def test_get_file_comments(self, service):
        """Test getting comments in a file."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "/* File header */", "file.c", 1, 0),
            (2, "// Function doc", "file.c", 10, 0),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_file_comments("file.c", limit=10)

        assert len(results) == 2

    def test_search_comments(self, service):
        """Test searching comments."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "/* memory allocation */", "alloc.c", 50),
        ]
        service.conn.execute.return_value = mock_result

        results = service.search_comments("memory", limit=10)

        assert len(results) == 1

    def test_get_todo_comments(self, service):
        """Test getting TODO comments."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "// TODO: Fix this", "todo.c", 10, "TODO"),
            (2, "// FIXME: Critical bug", "fix.c", 20, "FIXME"),
        ]
        service.conn.execute.return_value = mock_result

        results = service.get_todo_comments(limit=10)

        assert len(results) == 2
        assert results[0]["comment_type"] == "TODO"
        assert results[1]["comment_type"] == "FIXME"

    def test_get_comment_statistics(self, service):
        """Test getting comment statistics."""
        def mock_execute(query):
            result = MagicMock()
            if "COUNT(*)" in query and "FROM nodes_comment" in query:
                if "TODO" in query:
                    result.fetchone.return_value = (50,)
                elif "FIXME" in query:
                    result.fetchone.return_value = (10,)
                else:
                    result.fetchone.return_value = (1000,)
            elif "GROUP BY filename" in query:
                result.fetchall.return_value = [
                    ("file1.c", 100),
                    ("file2.c", 80),
                ]
            else:
                result.fetchone.return_value = (0,)
            return result

        service.conn.execute.side_effect = mock_execute

        stats = service.get_comment_statistics()

        assert stats["total_comments"] == 1000
        assert len(stats["top_commented_files"]) == 2

    def test_get_comment_statistics_error_handling(self, service):
        """Test comment statistics handles errors gracefully."""
        service.conn.execute.side_effect = Exception("Query failed")

        stats = service.get_comment_statistics()

        # Should return zeros on error
        assert stats["total_comments"] == 0
        assert stats["top_commented_files"] == []


class TestCallGraphTraversal:
    """Tests for call graph traversal methods."""

    @pytest.fixture
    def service(self):
        """Create CPGQueryService with mock connection."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            service = CPGQueryService()
            return service

    def test_traverse_callees(self, service):
        """Test _traverse_callees method."""
        G = nx.DiGraph()
        G.add_node(1, name="start", filename="start.c")

        # Mock callee lookup
        def execute_side_effect(query, params=None):
            result = MagicMock()
            if "FROM edges_call" in query and params and params[0] == 1:
                result.fetchall.return_value = [(2, "callee_func")]
            elif "FROM nodes_method WHERE id" in query:
                result.fetchone.return_value = (2, "callee", "callee.c", "void callee()")
            else:
                result.fetchall.return_value = []
            return result

        service.conn.execute.side_effect = execute_side_effect

        service._traverse_callees(G, start_id=1, max_depth=1)

        assert 2 in G.nodes()
        assert G.has_edge(1, 2)

    def test_traverse_callers(self, service):
        """Test _traverse_callers method."""
        G = nx.DiGraph()
        G.add_node(1, name="target", filename="target.c")

        # Mock caller lookup
        def execute_side_effect(query, params=None):
            result = MagicMock()
            if "FROM edges_call" in query and params and params[0] == 1:
                result.fetchall.return_value = [(0, "caller_func")]
            elif "FROM nodes_method WHERE id" in query:
                result.fetchone.return_value = (0, "caller", "caller.c", "void caller()")
            else:
                result.fetchall.return_value = []
            return result

        service.conn.execute.side_effect = execute_side_effect

        service._traverse_callers(G, start_id=1, max_depth=1)

        assert 0 in G.nodes()
        assert G.has_edge(0, 1)


class TestIntegration:
    """Integration tests for CPGQueryService."""

    def test_service_lifecycle(self):
        """Test complete service lifecycle."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn

            # Create service
            service = CPGQueryService(db_path="test.duckdb")
            assert service.conn is not None

            # Switch database
            mock_conn2 = MagicMock()
            mock_duckdb.connect.return_value = mock_conn2
            service.set_database("other.duckdb")
            assert service.db_path == "other.duckdb"

            # Close
            service.close()
            assert service.conn is None

    def test_multiple_queries(self):
        """Test executing multiple queries."""
        from src.services.cpg_query_service import CPGQueryService

        with patch("src.services.cpg_query_service.duckdb") as mock_duckdb:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_result.description = []
            mock_conn.execute.return_value = mock_result
            mock_duckdb.connect.return_value = mock_conn

            with CPGQueryService() as service:
                service.execute_query("SELECT 1")
                service.execute_query("SELECT 2")
                service.execute_query("SELECT 3")

            assert mock_conn.execute.call_count == 3
