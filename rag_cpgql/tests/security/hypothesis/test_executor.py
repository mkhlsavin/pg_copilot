"""
Tests for DuckDB Query Executor.

Tests for:
- QueryResult dataclass
- QueryExecutor initialization
- QueryExecutor connection management
- execute_query method
- execute_hypothesis_query method
- validate_hypothesis method
- validate_batch method
- get_table_stats method
- check_database_health method
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from src.security.hypothesis.executor import QueryResult, QueryExecutor
from src.security.hypothesis.models import SecurityHypothesis, Evidence, ValidationStatus


# =============================================================================
# QueryResult Tests
# =============================================================================

class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_query_result_creation(self):
        """Test QueryResult can be created with all fields."""
        result = QueryResult(
            query="SELECT * FROM test",
            success=True,
            row_count=5,
            results=[{"id": 1}, {"id": 2}],
            execution_time_ms=10.5,
        )
        assert result.query == "SELECT * FROM test"
        assert result.success is True
        assert result.row_count == 5
        assert len(result.results) == 2
        assert result.execution_time_ms == 10.5
        assert result.error is None

    def test_query_result_with_error(self):
        """Test QueryResult with error field."""
        result = QueryResult(
            query="INVALID SQL",
            success=False,
            row_count=0,
            results=[],
            execution_time_ms=1.0,
            error="Syntax error",
        )
        assert result.success is False
        assert result.error == "Syntax error"

    def test_query_result_empty_results(self):
        """Test QueryResult with empty results."""
        result = QueryResult(
            query="SELECT * FROM empty",
            success=True,
            row_count=0,
            results=[],
            execution_time_ms=5.0,
        )
        assert result.row_count == 0
        assert result.results == []


# =============================================================================
# QueryExecutor Initialization Tests
# =============================================================================

class TestQueryExecutorInit:
    """Tests for QueryExecutor initialization."""

    def test_init_sets_db_path(self):
        """Test executor stores db_path."""
        executor = QueryExecutor("/path/to/db.duckdb")
        assert executor.db_path == "/path/to/db.duckdb"

    def test_init_sets_read_only_default(self):
        """Test executor defaults to read_only mode."""
        executor = QueryExecutor("/path/to/db.duckdb")
        assert executor.read_only is True

    def test_init_sets_read_only_false(self):
        """Test executor can disable read_only mode."""
        executor = QueryExecutor("/path/to/db.duckdb", read_only=False)
        assert executor.read_only is False

    def test_init_sets_timeout(self):
        """Test executor sets custom timeout."""
        executor = QueryExecutor("/path/to/db.duckdb", timeout_seconds=60.0)
        assert executor.timeout_seconds == 60.0

    def test_init_connection_is_none(self):
        """Test executor starts with no connection."""
        executor = QueryExecutor("/path/to/db.duckdb")
        assert executor._conn is None


# =============================================================================
# QueryExecutor Connection Management Tests
# =============================================================================

class TestQueryExecutorConnection:
    """Tests for QueryExecutor connection management."""

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_connect_creates_connection(self):
        """Test connect creates a DuckDB connection."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        executor = QueryExecutor("/path/to/db.duckdb")
        executor.connect()

        mock_duckdb.connect.assert_called_once_with(
            "/path/to/db.duckdb",
            read_only=True,
        )
        assert executor._conn is mock_conn

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_connect_raises_on_error(self):
        """Test connect raises exception on failure."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_duckdb.connect.side_effect = Exception("Connection failed")

        executor = QueryExecutor("/path/to/db.duckdb")
        with pytest.raises(Exception, match="Connection failed"):
            executor.connect()

    def test_close_closes_connection(self):
        """Test close closes the connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn

        executor.close()

        mock_conn.close.assert_called_once()
        assert executor._conn is None

    def test_close_does_nothing_when_not_connected(self):
        """Test close does nothing when no connection."""
        executor = QueryExecutor("/path/to/db.duckdb")
        executor.close()  # Should not raise
        assert executor._conn is None

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_context_manager_enter(self):
        """Test context manager connects on enter."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        executor = QueryExecutor("/path/to/db.duckdb")
        result = executor.__enter__()

        assert result is executor
        assert executor._conn is mock_conn

    def test_context_manager_exit(self):
        """Test context manager closes on exit."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn

        result = executor.__exit__(None, None, None)

        assert result is False
        mock_conn.close.assert_called_once()


# =============================================================================
# execute_query Tests
# =============================================================================

class TestExecuteQuery:
    """Tests for execute_query method."""

    @pytest.fixture
    def executor_with_conn(self):
        """Create executor with mocked connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn
        return executor, mock_conn

    def test_execute_query_success(self, executor_with_conn):
        """Test successful query execution."""
        executor, mock_conn = executor_with_conn

        # Mock DataFrame result
        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 3
        mock_df.to_dict.return_value = [
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b"},
            {"id": 3, "name": "c"},
        ]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.execute_query("SELECT * FROM test")

        assert result.success is True
        assert result.row_count == 3
        assert len(result.results) == 3
        assert result.error is None

    def test_execute_query_stores_query(self, executor_with_conn):
        """Test executed query is stored in result."""
        executor, mock_conn = executor_with_conn

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.execute_query("SELECT * FROM nodes")

        assert result.query == "SELECT * FROM nodes"

    def test_execute_query_measures_time(self, executor_with_conn):
        """Test execution time is measured."""
        executor, mock_conn = executor_with_conn

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.execute_query("SELECT 1")

        assert result.execution_time_ms >= 0

    def test_execute_query_handles_error(self, executor_with_conn):
        """Test query error is handled."""
        executor, mock_conn = executor_with_conn
        mock_conn.execute.side_effect = Exception("SQL syntax error")

        result = executor.execute_query("INVALID SQL")

        assert result.success is False
        assert result.row_count == 0
        assert result.results == []
        assert "SQL syntax error" in result.error

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_execute_query_connects_if_needed(self):
        """Test execute_query connects if not connected."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        executor = QueryExecutor("/path/to/db.duckdb")
        result = executor.execute_query("SELECT 1")

        mock_duckdb.connect.assert_called_once()
        assert result.success is True


# =============================================================================
# execute_hypothesis_query Tests
# =============================================================================

class TestExecuteHypothesisQuery:
    """Tests for execute_hypothesis_query method."""

    @pytest.fixture
    def executor_with_conn(self):
        """Create executor with mocked connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn
        return executor, mock_conn

    def test_execute_hypothesis_query_success(self, executor_with_conn, sample_hypothesis):
        """Test executing query from hypothesis."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulnerabilities"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 2
        mock_df.to_dict.return_value = [{"id": 1}, {"id": 2}]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.execute_hypothesis_query(sample_hypothesis)

        assert result.success is True
        assert result.row_count == 2

    def test_execute_hypothesis_query_no_query(self, executor_with_conn, sample_hypothesis):
        """Test returns error when hypothesis has no query."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = None

        result = executor.execute_hypothesis_query(sample_hypothesis)

        assert result.success is False
        assert "No SQL query" in result.error

    def test_execute_hypothesis_query_empty_query(self, executor_with_conn, sample_hypothesis):
        """Test returns error when hypothesis has empty query."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = ""

        result = executor.execute_hypothesis_query(sample_hypothesis)

        assert result.success is False


# =============================================================================
# validate_hypothesis Tests
# =============================================================================

class TestValidateHypothesis:
    """Tests for validate_hypothesis method."""

    @pytest.fixture
    def executor_with_conn(self):
        """Create executor with mocked connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn
        return executor, mock_conn

    def test_validate_hypothesis_confirms_on_results(self, executor_with_conn, sample_hypothesis):
        """Test hypothesis is confirmed when results found."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulns"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 3
        mock_df.to_dict.return_value = [
            {"filename": "test.c", "line_number": 10, "code": "strcpy(buf, input)"},
            {"filename": "test.c", "line_number": 20, "code": "memcpy(dst, src, len)"},
            {"filename": "test.c", "line_number": 30, "code": "gets(buf)"},
        ]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_hypothesis(sample_hypothesis)

        assert result.validation_status == ValidationStatus.CONFIRMED
        assert len(result.evidence) >= 1

    def test_validate_hypothesis_rejects_on_no_results(self, executor_with_conn, sample_hypothesis):
        """Test hypothesis is rejected when no results."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulns WHERE 1=0"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_hypothesis(sample_hypothesis)

        assert result.validation_status == ValidationStatus.REJECTED

    def test_validate_hypothesis_inconclusive_on_error(self, executor_with_conn, sample_hypothesis):
        """Test hypothesis is inconclusive on query error."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "INVALID SQL"
        mock_conn.execute.side_effect = Exception("Syntax error")

        result = executor.validate_hypothesis(sample_hypothesis)

        assert result.validation_status == ValidationStatus.INCONCLUSIVE
        assert "Query error" in result.notes

    def test_validate_hypothesis_adds_evidence(self, executor_with_conn, sample_hypothesis):
        """Test hypothesis gets evidence added."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulns"
        sample_hypothesis.evidence = []

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 1
        mock_df.to_dict.return_value = [
            {"filename": "vuln.c", "line_number": 42, "code": "strcpy(a, b)"}
        ]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_hypothesis(sample_hypothesis)

        assert len(result.evidence) >= 1
        evidence = result.evidence[-1]
        assert evidence.result_count == 1
        assert evidence.filename == "vuln.c"
        assert evidence.line_number == 42

    def test_validate_hypothesis_sets_validated_at(self, executor_with_conn, sample_hypothesis):
        """Test hypothesis validated_at is set."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT 1"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        before = datetime.utcnow()
        result = executor.validate_hypothesis(sample_hypothesis)
        after = datetime.utcnow()

        assert result.validated_at is not None
        assert before <= result.validated_at <= after

    def test_validate_hypothesis_respects_min_results(self, executor_with_conn, sample_hypothesis):
        """Test min_results_for_confirmation threshold."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulns"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 2
        mock_df.to_dict.return_value = [{"id": 1}, {"id": 2}]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        # With threshold of 3, 2 results should be INCONCLUSIVE
        result = executor.validate_hypothesis(sample_hypothesis, min_results_for_confirmation=3)

        assert result.validation_status == ValidationStatus.INCONCLUSIVE

    def test_validate_hypothesis_evidence_confidence(self, executor_with_conn, sample_hypothesis):
        """Test evidence confidence calculation."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT * FROM vulns"
        sample_hypothesis.evidence = []

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 5
        mock_df.to_dict.return_value = [{"id": i} for i in range(5)]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_hypothesis(sample_hypothesis)

        # Confidence = min(0.9, 0.5 + (5 * 0.1)) = min(0.9, 1.0) = 0.9
        assert result.evidence[-1].confidence == 0.9


# =============================================================================
# validate_batch Tests
# =============================================================================

class TestValidateBatch:
    """Tests for validate_batch method."""

    @pytest.fixture
    def executor_with_conn(self):
        """Create executor with mocked connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn
        return executor, mock_conn

    def test_validate_batch_returns_list(self, executor_with_conn, sample_hypothesis):
        """Test validate_batch returns list."""
        executor, mock_conn = executor_with_conn
        sample_hypothesis.sql_query = "SELECT 1"

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_batch([sample_hypothesis])

        assert isinstance(result, list)
        assert len(result) == 1

    def test_validate_batch_multiple_hypotheses(self, executor_with_conn):
        """Test validate_batch handles multiple hypotheses."""
        executor, mock_conn = executor_with_conn

        hyps = []
        for i in range(3):
            h = SecurityHypothesis(
                id=f"hyp-{i}",
                hypothesis_text=f"Test {i}",
                cwe_ids=["CWE-120"],
                capec_ids=[],
                language="C",
                category="buffer_overflow",
                source_patterns=[],
                sink_patterns=[],
                sanitizer_patterns=[],
                sql_query="SELECT 1",
            )
            hyps.append(h)

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 0
        mock_df.to_dict.return_value = []
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        result = executor.validate_batch(hyps)

        assert len(result) == 3
        for h in result:
            assert h.validation_status == ValidationStatus.REJECTED


# =============================================================================
# get_table_stats Tests
# =============================================================================

class TestGetTableStats:
    """Tests for get_table_stats method."""

    @pytest.fixture
    def executor_with_conn(self):
        """Create executor with mocked connection."""
        mock_conn = MagicMock()
        executor = QueryExecutor("/path/to/db.duckdb")
        executor._conn = mock_conn
        return executor, mock_conn

    def test_get_table_stats_returns_dict(self, executor_with_conn):
        """Test get_table_stats returns dictionary."""
        executor, mock_conn = executor_with_conn

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 1
        mock_df.to_dict.return_value = [{"cnt": 100}]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        stats = executor.get_table_stats()

        assert isinstance(stats, dict)
        assert "nodes_method" in stats
        assert "edges_cfg" in stats

    def test_get_table_stats_handles_errors(self, executor_with_conn):
        """Test get_table_stats handles table errors."""
        executor, mock_conn = executor_with_conn
        mock_conn.execute.side_effect = Exception("Table not found")

        stats = executor.get_table_stats()

        # Should return 0 for tables that error
        for table, count in stats.items():
            assert count == 0


# =============================================================================
# check_database_health Tests
# =============================================================================

class TestCheckDatabaseHealth:
    """Tests for check_database_health method."""

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_check_database_health_returns_dict(self):
        """Test check_database_health returns health dict."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 1
        mock_df.to_dict.return_value = [{"cnt": 50}]
        mock_conn.execute.return_value.fetchdf.return_value = mock_df

        executor = QueryExecutor("/path/to/db.duckdb")
        health = executor.check_database_health()

        assert isinstance(health, dict)
        assert "connected" in health
        assert "database_path" in health
        assert "tables" in health

    @patch.dict('sys.modules', {'duckdb': MagicMock()})
    def test_check_database_health_on_error(self):
        """Test check_database_health handles connection error."""
        import sys
        mock_duckdb = sys.modules['duckdb']
        mock_duckdb.connect.side_effect = Exception("Cannot connect")

        executor = QueryExecutor("/nonexistent/db.duckdb")
        health = executor.check_database_health()

        assert health["connected"] is False
        assert "Cannot connect" in health["error"]
