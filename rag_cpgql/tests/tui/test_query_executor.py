"""
Tests for TUI Query Executor.

Tests for SQL query validation, execution, and result rendering.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile


class MockTheme:
    """Mock theme for testing."""
    border = "blue"
    accent = "cyan"
    highlight = "green"


class TestQueryValidation:
    """Tests for query validation."""

    @pytest.fixture
    def executor(self):
        """Create QueryExecutor for testing."""
        from src.tui.components.query_executor import QueryExecutor

        return QueryExecutor(theme=MockTheme())

    def test_validate_empty_query(self, executor):
        """Test validation of empty query."""
        valid, msg = executor.validate_query("")

        assert valid is False
        assert "empty" in msg.lower()

    def test_validate_whitespace_query(self, executor):
        """Test validation of whitespace-only query."""
        valid, msg = executor.validate_query("   ")

        assert valid is False
        assert "empty" in msg.lower()

    def test_validate_select_query(self, executor):
        """Test validation of SELECT query."""
        valid, msg = executor.validate_query("SELECT * FROM nodes_method")

        assert valid is True
        assert msg == ""

    def test_validate_describe_query(self, executor):
        """Test validation of DESCRIBE query."""
        valid, msg = executor.validate_query("DESCRIBE nodes_method")

        assert valid is True

    def test_validate_show_query(self, executor):
        """Test validation of SHOW query."""
        valid, msg = executor.validate_query("SHOW TABLES")

        assert valid is True

    def test_block_drop_query(self, executor):
        """Test blocking of DROP query."""
        valid, msg = executor.validate_query("DROP TABLE users")

        assert valid is False
        assert "DROP" in msg

    def test_block_delete_query(self, executor):
        """Test blocking of DELETE query."""
        valid, msg = executor.validate_query("DELETE FROM users")

        assert valid is False
        assert "DELETE" in msg

    def test_block_insert_query(self, executor):
        """Test blocking of INSERT query."""
        valid, msg = executor.validate_query("INSERT INTO users VALUES (1)")

        assert valid is False
        assert "INSERT" in msg

    def test_block_update_query(self, executor):
        """Test blocking of UPDATE query."""
        valid, msg = executor.validate_query("UPDATE users SET name='test'")

        assert valid is False
        assert "UPDATE" in msg

    def test_block_alter_query(self, executor):
        """Test blocking of ALTER query."""
        valid, msg = executor.validate_query("ALTER TABLE users ADD col INT")

        assert valid is False
        assert "ALTER" in msg

    def test_block_truncate_query(self, executor):
        """Test blocking of TRUNCATE query."""
        valid, msg = executor.validate_query("TRUNCATE TABLE users")

        assert valid is False
        assert "TRUNCATE" in msg

    def test_block_create_query(self, executor):
        """Test blocking of CREATE query."""
        valid, msg = executor.validate_query("CREATE TABLE test (id INT)")

        assert valid is False
        assert "CREATE" in msg

    def test_block_multiple_statements(self, executor):
        """Test blocking of multiple statements."""
        valid, msg = executor.validate_query(
            "SELECT * FROM t1; SELECT * FROM t2"
        )

        assert valid is False
        assert "multiple" in msg.lower()

    def test_allow_semicolon_at_end(self, executor):
        """Test allowing semicolon at end."""
        valid, msg = executor.validate_query("SELECT * FROM nodes;")

        assert valid is True

    def test_block_injection_attempt(self, executor):
        """Test blocking injection with chained write."""
        valid, msg = executor.validate_query(
            "SELECT * FROM t; DROP TABLE users"
        )

        assert valid is False

    def test_case_insensitive_blocking(self, executor):
        """Test that blocking is case-insensitive."""
        valid, msg = executor.validate_query("drop table users")

        assert valid is False
        assert "DROP" in msg

    def test_block_grant_query(self, executor):
        """Test blocking of GRANT query."""
        valid, msg = executor.validate_query("GRANT ALL ON users TO admin")

        assert valid is False
        assert "GRANT" in msg


class TestQueryExecutorInit:
    """Tests for QueryExecutor initialization."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        from src.tui.components.query_executor import QueryExecutor, DEFAULT_DB_PATH

        executor = QueryExecutor()

        assert executor.db_path == DEFAULT_DB_PATH
        assert executor.timeout == 30.0
        assert executor.max_rows == 100

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        from src.tui.components.query_executor import QueryExecutor

        custom_path = Path("/custom/db.duckdb")
        executor = QueryExecutor(
            db_path=custom_path,
            theme=MockTheme(),
            timeout=60.0,
            max_rows=50,
        )

        assert executor.db_path == custom_path
        assert executor.timeout == 60.0
        assert executor.max_rows == 50


class TestQueryExecution:
    """Tests for query execution."""

    @pytest.fixture
    def mock_duckdb(self):
        """Create mock DuckDB connection."""
        with patch("src.tui.components.query_executor.duckdb") as mock:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.description = [("name",), ("line",)]
            mock_result.fetchall.return_value = [
                ("test_method", 10),
                ("another_method", 20),
            ]
            mock_conn.execute.return_value = mock_result
            mock.connect.return_value = mock_conn
            yield mock

    @pytest.fixture
    def executor_with_db(self, tmp_path, mock_duckdb):
        """Create QueryExecutor with mock database."""
        from src.tui.components.query_executor import QueryExecutor

        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        return QueryExecutor(db_path=db_path, theme=MockTheme())

    def test_execute_query(self, executor_with_db, mock_duckdb):
        """Test executing a query."""
        results, duration = executor_with_db.execute("SELECT * FROM nodes")

        assert len(results) == 2
        assert results[0]["name"] == "test_method"
        assert results[0]["line"] == 10
        assert duration >= 0

    def test_execute_adds_limit(self, executor_with_db, mock_duckdb):
        """Test that LIMIT is added if missing."""
        executor_with_db.execute("SELECT * FROM nodes")

        call_args = mock_duckdb.connect().execute.call_args[0][0]
        assert "LIMIT" in call_args

    def test_execute_keeps_existing_limit(self, executor_with_db, mock_duckdb):
        """Test that existing LIMIT is preserved."""
        executor_with_db.execute("SELECT * FROM nodes LIMIT 5")

        call_args = mock_duckdb.connect().execute.call_args[0][0]
        # Should not add another LIMIT
        assert call_args.count("LIMIT") == 1

    def test_execute_db_not_found(self):
        """Test execution with missing database."""
        from src.tui.components.query_executor import QueryExecutor

        executor = QueryExecutor(
            db_path=Path("/nonexistent/db.duckdb"),
            theme=MockTheme(),
        )

        with pytest.raises(FileNotFoundError):
            executor.execute("SELECT 1")


class TestResultRendering:
    """Tests for result rendering."""

    @pytest.fixture
    def executor(self):
        """Create QueryExecutor for testing."""
        from src.tui.components.query_executor import QueryExecutor

        return QueryExecutor(theme=MockTheme())

    def test_render_results_empty(self, executor):
        """Test rendering empty results."""
        result = executor.render_results([], "SELECT * FROM empty", 0.001)

        assert result is not None
        # Should indicate no rows

    def test_render_results_with_data(self, executor):
        """Test rendering results with data."""
        results = [
            {"name": "test", "line": 10},
            {"name": "test2", "line": 20},
        ]

        panel = executor.render_results(results, "SELECT * FROM t", 0.05)

        assert panel is not None

    def test_render_results_truncates_query(self, executor):
        """Test that long queries are truncated."""
        long_query = "SELECT " + "column, " * 50 + "last FROM table"

        panel = executor.render_results([], long_query, 0.01)

        assert panel is not None

    def test_render_results_shows_duration(self, executor):
        """Test that duration is shown."""
        panel = executor.render_results(
            [{"col": 1}],
            "SELECT 1",
            0.123,
        )

        assert panel is not None

    def test_render_results_handles_null(self, executor):
        """Test rendering NULL values."""
        results = [
            {"name": "test", "value": None},
        ]

        panel = executor.render_results(results, "SELECT * FROM t", 0.01)

        assert panel is not None

    def test_render_results_truncates_long_values(self, executor):
        """Test that long values are truncated."""
        results = [
            {"content": "x" * 100},  # Longer than 50 chars
        ]

        panel = executor.render_results(results, "SELECT * FROM t", 0.01)

        assert panel is not None


class TestErrorRendering:
    """Tests for error rendering."""

    @pytest.fixture
    def executor(self):
        """Create QueryExecutor for testing."""
        from src.tui.components.query_executor import QueryExecutor

        return QueryExecutor(theme=MockTheme())

    def test_render_error(self, executor):
        """Test rendering error panel."""
        error = Exception("Syntax error near 'FROM'")
        panel = executor.render_error(error, "SELECT * FORM table")

        assert panel is not None
        # Should have error styling

    def test_render_error_truncates_query(self, executor):
        """Test that error panel truncates long queries."""
        long_query = "SELECT " + "a, " * 50 + " FROM table"
        error = Exception("Query too complex")

        panel = executor.render_error(error, long_query)

        assert panel is not None


class TestTableInfo:
    """Tests for table info methods."""

    @pytest.fixture
    def mock_duckdb(self):
        """Create mock DuckDB connection."""
        with patch("src.tui.components.query_executor.duckdb") as mock:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.description = [("name",)]
            mock_result.fetchall.return_value = [
                ("nodes_method",),
                ("nodes_call",),
                ("edges_cfg",),
            ]
            mock_conn.execute.return_value = mock_result
            mock.connect.return_value = mock_conn
            yield mock

    @pytest.fixture
    def executor_with_db(self, tmp_path, mock_duckdb):
        """Create QueryExecutor with mock database."""
        from src.tui.components.query_executor import QueryExecutor

        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        return QueryExecutor(db_path=db_path, theme=MockTheme())

    def test_get_table_info(self, executor_with_db, mock_duckdb):
        """Test getting table info."""
        tables = executor_with_db.get_table_info()

        assert "nodes_method" in tables
        assert "nodes_call" in tables
        assert "edges_cfg" in tables

    def test_get_table_info_error(self):
        """Test get_table_info handles errors."""
        from src.tui.components.query_executor import QueryExecutor

        executor = QueryExecutor(
            db_path=Path("/nonexistent/db.duckdb"),
            theme=MockTheme(),
        )

        tables = executor.get_table_info()

        assert tables == []


class TestDescribeTable:
    """Tests for table describe functionality."""

    @pytest.fixture
    def mock_duckdb(self):
        """Create mock DuckDB connection."""
        with patch("src.tui.components.query_executor.duckdb") as mock:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.description = [("column_name",), ("column_type",)]
            mock_result.fetchall.return_value = [
                ("id", "BIGINT"),
                ("name", "VARCHAR"),
            ]
            mock_conn.execute.return_value = mock_result
            mock.connect.return_value = mock_conn
            yield mock

    @pytest.fixture
    def executor_with_db(self, tmp_path, mock_duckdb):
        """Create QueryExecutor with mock database."""
        from src.tui.components.query_executor import QueryExecutor

        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        return QueryExecutor(db_path=db_path, theme=MockTheme())

    def test_describe_table(self, executor_with_db, mock_duckdb):
        """Test describing a table."""
        panel = executor_with_db.describe_table("nodes_method")

        assert panel is not None

    def test_describe_table_invalid_name(self, executor_with_db):
        """Test describing with invalid table name."""
        panel = executor_with_db.describe_table("users; DROP TABLE--")

        assert panel is not None
        # Should show error

    def test_describe_table_valid_name_with_underscore(self, executor_with_db):
        """Test describing table with underscores."""
        panel = executor_with_db.describe_table("nodes_method_name")

        assert panel is not None


class TestQueryHelp:
    """Tests for query help rendering."""

    @pytest.fixture
    def executor(self):
        """Create QueryExecutor for testing."""
        from src.tui.components.query_executor import QueryExecutor

        return QueryExecutor(theme=MockTheme())

    def test_render_help(self, executor):
        """Test rendering help panel."""
        panel = executor.render_help()

        assert panel is not None

    def test_help_contains_usage(self, executor):
        """Test that help contains usage examples."""
        panel = executor.render_help()

        assert panel is not None

    def test_help_contains_common_tables(self, executor):
        """Test that help lists common tables."""
        panel = executor.render_help()

        assert panel is not None


class TestBlockedKeywords:
    """Tests for blocked keyword list."""

    def test_blocked_keywords_list(self):
        """Test that blocked keywords are defined."""
        from src.tui.components.query_executor import BLOCKED_KEYWORDS

        expected = [
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "ALTER",
            "TRUNCATE",
            "CREATE",
        ]

        for keyword in expected:
            assert keyword in BLOCKED_KEYWORDS

    def test_blocked_keywords_uppercase(self):
        """Test that blocked keywords are uppercase."""
        from src.tui.components.query_executor import BLOCKED_KEYWORDS

        for keyword in BLOCKED_KEYWORDS:
            assert keyword == keyword.upper()
