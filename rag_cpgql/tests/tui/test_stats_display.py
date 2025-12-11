"""
Tests for TUI Stats Display.

Tests for StatsDisplay, CPGStats, ChromaDBStats, and SystemStats.
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


class TestCPGStatsDataclass:
    """Tests for CPGStats dataclass."""

    def test_cpg_stats_creation(self):
        """Test creating CPGStats with values."""
        from src.tui.components.stats_display import CPGStats

        stats = CPGStats(
            method_count=1000,
            call_node_count=5000,
            identifier_count=10000,
            literal_count=2000,
            local_count=3000,
            param_count=1500,
            return_count=800,
            block_count=2500,
            control_structure_count=1200,
            type_decl_count=500,
            ast_edge_count=50000,
            cfg_edge_count=20000,
            call_edge_count=8000,
            ref_edge_count=15000,
            reaching_def_edge_count=10000,
            argument_edge_count=5000,
            receiver_edge_count=1000,
            condition_edge_count=2000,
        )

        assert stats.method_count == 1000
        assert stats.call_node_count == 5000
        assert stats.ast_edge_count == 50000

    def test_cpg_stats_defaults(self):
        """Test CPGStats default values."""
        from src.tui.components.stats_display import CPGStats

        stats = CPGStats()

        assert stats.method_count == 0
        assert stats.call_node_count == 0
        assert stats.ast_edge_count == 0
        assert stats.cfg_edge_count == 0


class TestChromaDBStatsDataclass:
    """Tests for ChromaDBStats dataclass."""

    def test_chromadb_stats_creation(self):
        """Test creating ChromaDBStats with values."""
        from src.tui.components.stats_display import ChromaDBStats

        stats = ChromaDBStats(
            code_documentation_count=500,
            qa_pairs_count=1000,
            cpgql_examples_count=200,
        )

        assert stats.code_documentation_count == 500
        assert stats.qa_pairs_count == 1000
        assert stats.cpgql_examples_count == 200

    def test_chromadb_stats_defaults(self):
        """Test ChromaDBStats default values."""
        from src.tui.components.stats_display import ChromaDBStats

        stats = ChromaDBStats()

        assert stats.code_documentation_count == 0
        assert stats.qa_pairs_count == 0
        assert stats.cpgql_examples_count == 0


class TestSystemStatsDataclass:
    """Tests for SystemStats dataclass."""

    def test_system_stats_creation(self):
        """Test creating SystemStats with values."""
        from src.tui.components.stats_display import (
            SystemStats,
            CPGStats,
            ChromaDBStats,
        )

        cpg_stats = CPGStats(method_count=100)
        chromadb_stats = ChromaDBStats(qa_pairs_count=50)

        stats = SystemStats(
            cpg_stats=cpg_stats,
            chromadb_stats=chromadb_stats,
            db_path="/path/to/db.duckdb",
            db_size_mb=125.5,
            chromadb_path="/path/to/chromadb",
            cpg_available=True,
            chromadb_available=True,
        )

        assert stats.cpg_stats.method_count == 100
        assert stats.chromadb_stats.qa_pairs_count == 50
        assert stats.db_size_mb == 125.5
        assert stats.cpg_available is True

    def test_system_stats_defaults(self):
        """Test SystemStats default values."""
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats()

        assert stats.cpg_stats is None
        assert stats.chromadb_stats is None
        assert stats.db_path == ""
        assert stats.db_size_mb == 0.0
        assert stats.cpg_available is False
        assert stats.chromadb_available is False

    def test_system_stats_error_messages_init(self):
        """Test error_messages initialization."""
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats()

        assert stats.error_messages == {}

    def test_system_stats_error_messages_set(self):
        """Test setting error messages."""
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats(error_messages={"cpg": "Database not found"})

        assert stats.error_messages["cpg"] == "Database not found"


class TestStatsDisplayInit:
    """Tests for StatsDisplay initialization."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        from src.tui.components.stats_display import (
            StatsDisplay,
            DEFAULT_DUCKDB_PATH,
            DEFAULT_CHROMADB_PATH,
        )

        display = StatsDisplay()

        assert display.duckdb_path == DEFAULT_DUCKDB_PATH
        assert display.chromadb_path == DEFAULT_CHROMADB_PATH

    def test_init_custom_paths(self, tmp_path):
        """Test initialization with custom paths."""
        from src.tui.components.stats_display import StatsDisplay

        duckdb_path = tmp_path / "custom.duckdb"
        chromadb_path = tmp_path / "custom_chromadb"

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=duckdb_path,
            chromadb_path=chromadb_path,
        )

        assert display.duckdb_path == duckdb_path
        assert display.chromadb_path == chromadb_path

    def test_init_with_theme(self):
        """Test initialization with custom theme."""
        from src.tui.components.stats_display import StatsDisplay

        display = StatsDisplay(theme=MockTheme())

        assert display.theme.border == "blue"


class TestCollectStats:
    """Tests for collect_stats method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay with temp paths."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_collect_stats_returns_system_stats(self, display):
        """Test that collect_stats returns SystemStats."""
        from src.tui.components.stats_display import SystemStats

        stats = display.collect_stats()

        assert isinstance(stats, SystemStats)

    def test_collect_stats_missing_duckdb(self, display):
        """Test collecting stats with missing DuckDB file."""
        stats = display.collect_stats()

        assert stats.cpg_available is False
        assert "cpg" in stats.error_messages

    def test_collect_stats_missing_chromadb(self, display):
        """Test collecting stats with missing ChromaDB."""
        stats = display.collect_stats()

        assert stats.chromadb_available is False
        assert "chromadb" in stats.error_messages

    def test_collect_stats_with_existing_duckdb(self, tmp_path):
        """Test collecting stats with existing DuckDB file."""
        from src.tui.components.stats_display import StatsDisplay

        # Create a dummy DuckDB file
        db_path = tmp_path / "test.duckdb"
        db_path.write_bytes(b"dummy data for size test")

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=db_path,
            chromadb_path=tmp_path / "chromadb",
        )

        with patch(
            "src.cpg_export.duckdb_cpg_client_v2.DuckDBCPGClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_statistics = MagicMock(
                method_count=100,
                call_node_count=500,
                identifier_count=1000,
                literal_count=200,
                local_count=300,
                param_count=150,
                return_count=80,
                block_count=250,
                control_structure_count=120,
                type_decl_count=50,
                ast_edge_count=5000,
                cfg_edge_count=2000,
                call_edge_count=800,
                ref_edge_count=1500,
                reaching_def_edge_count=1000,
                argument_edge_count=500,
                receiver_edge_count=100,
                condition_edge_count=200,
            )
            mock_client.get_statistics.return_value = mock_statistics
            mock_client_class.return_value.__enter__ = MagicMock(
                return_value=mock_client
            )
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            stats = display.collect_stats()

            assert stats.db_size_mb > 0
            # CPG stats may or may not be available depending on mock setup


class TestCollectCPGStats:
    """Tests for _collect_cpg_stats method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay for testing."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_collect_cpg_stats_file_not_found(self, display):
        """Test CPG stats when file doesn't exist."""
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats()
        display._collect_cpg_stats(stats)

        assert stats.cpg_available is False
        assert "cpg" in stats.error_messages

    def test_collect_cpg_stats_import_error(self, tmp_path):
        """Test CPG stats when DuckDBCPGClient import fails."""
        from src.tui.components.stats_display import StatsDisplay, SystemStats

        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=db_path,
            chromadb_path=tmp_path / "chromadb",
        )

        stats = SystemStats()

        with patch(
            "src.cpg_export.duckdb_cpg_client_v2.DuckDBCPGClient",
            side_effect=ImportError("Module not found"),
        ):
            display._collect_cpg_stats(stats)

        assert stats.cpg_available is False


class TestCollectChromaDBStats:
    """Tests for _collect_chromadb_stats method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay for testing."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_collect_chromadb_stats_dir_not_found(self, display):
        """Test ChromaDB stats when directory doesn't exist."""
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats()
        display._collect_chromadb_stats(stats)

        assert stats.chromadb_available is False
        assert "chromadb" in stats.error_messages

    def test_collect_chromadb_stats_with_existing_dir(self, tmp_path):
        """Test ChromaDB stats with existing directory."""
        from src.tui.components.stats_display import StatsDisplay, SystemStats

        chromadb_path = tmp_path / "chromadb"
        chromadb_path.mkdir()

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=chromadb_path,
        )

        stats = SystemStats()

        with patch(
            "src.retrieval.doc_vector_store.DocumentationVectorStore"
        ) as mock_doc_store:
            mock_store = MagicMock()
            mock_store.get_stats.return_value = {"total_documents": 100}
            mock_doc_store.return_value = mock_store

            display._collect_chromadb_stats(stats)

        # Should try to collect stats
        assert stats.chromadb_available is True


class TestRenderStats:
    """Tests for render method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay for testing."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_render_returns_panel(self, display):
        """Test that render returns a Panel."""
        from rich.panel import Panel
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats()
        result = display.render(stats)

        assert isinstance(result, Panel)

    def test_render_with_cpg_stats(self, display):
        """Test rendering with CPG stats available."""
        from src.tui.components.stats_display import SystemStats, CPGStats

        stats = SystemStats(
            cpg_stats=CPGStats(method_count=100, call_node_count=500),
            cpg_available=True,
            db_path="/path/db.duckdb",
            db_size_mb=50.0,
        )

        result = display.render(stats)

        assert result is not None

    def test_render_with_chromadb_stats(self, display):
        """Test rendering with ChromaDB stats available."""
        from src.tui.components.stats_display import (
            SystemStats,
            ChromaDBStats,
        )

        stats = SystemStats(
            chromadb_stats=ChromaDBStats(qa_pairs_count=100),
            chromadb_available=True,
            chromadb_path="/path/chromadb",
        )

        result = display.render(stats)

        assert result is not None


class TestRenderCPGPanel:
    """Tests for _render_cpg_panel method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay for testing."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_render_cpg_panel_unavailable(self, display):
        """Test rendering CPG panel when unavailable."""
        from rich.panel import Panel
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats(
            cpg_available=False,
            error_messages={"cpg": "Database not found"},
        )

        result = display._render_cpg_panel(stats)

        assert isinstance(result, Panel)

    def test_render_cpg_panel_available(self, display):
        """Test rendering CPG panel when available."""
        from rich.panel import Panel
        from src.tui.components.stats_display import SystemStats, CPGStats

        stats = SystemStats(
            cpg_stats=CPGStats(
                method_count=1000,
                call_node_count=5000,
                ast_edge_count=50000,
                cfg_edge_count=20000,
            ),
            cpg_available=True,
            db_path="/path/db.duckdb",
            db_size_mb=100.0,
        )

        result = display._render_cpg_panel(stats)

        assert isinstance(result, Panel)
        assert "CPG" in str(result.title)


class TestRenderChromaDBPanel:
    """Tests for _render_chromadb_panel method."""

    @pytest.fixture
    def display(self, tmp_path):
        """Create StatsDisplay for testing."""
        from src.tui.components.stats_display import StatsDisplay

        return StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "test.duckdb",
            chromadb_path=tmp_path / "chromadb",
        )

    def test_render_chromadb_panel_unavailable(self, display):
        """Test rendering ChromaDB panel when unavailable."""
        from rich.panel import Panel
        from src.tui.components.stats_display import SystemStats

        stats = SystemStats(
            chromadb_available=False,
            error_messages={"chromadb": "Storage not found"},
        )

        result = display._render_chromadb_panel(stats)

        assert isinstance(result, Panel)

    def test_render_chromadb_panel_available(self, display):
        """Test rendering ChromaDB panel when available."""
        from rich.panel import Panel
        from src.tui.components.stats_display import (
            SystemStats,
            ChromaDBStats,
        )

        stats = SystemStats(
            chromadb_stats=ChromaDBStats(
                code_documentation_count=500,
                qa_pairs_count=1000,
                cpgql_examples_count=200,
            ),
            chromadb_available=True,
            chromadb_path="/path/chromadb",
        )

        result = display._render_chromadb_panel(stats)

        assert isinstance(result, Panel)
        assert "ChromaDB" in str(result.title)


class TestDefaultPaths:
    """Tests for default path constants."""

    def test_default_duckdb_path(self):
        """Test default DuckDB path is defined."""
        from src.tui.components.stats_display import DEFAULT_DUCKDB_PATH

        assert DEFAULT_DUCKDB_PATH is not None
        assert "duckdb" in str(DEFAULT_DUCKDB_PATH).lower()

    def test_default_chromadb_path(self):
        """Test default ChromaDB path is defined."""
        from src.tui.components.stats_display import DEFAULT_CHROMADB_PATH

        assert DEFAULT_CHROMADB_PATH is not None
        assert "chroma" in str(DEFAULT_CHROMADB_PATH).lower()


class TestIntegration:
    """Integration tests for StatsDisplay."""

    def test_full_workflow_missing_data(self, tmp_path):
        """Test complete workflow with missing data sources."""
        from src.tui.components.stats_display import StatsDisplay

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=tmp_path / "nonexistent.duckdb",
            chromadb_path=tmp_path / "nonexistent_chromadb",
        )

        stats = display.collect_stats()
        panel = display.render(stats)

        assert panel is not None
        assert stats.cpg_available is False
        assert stats.chromadb_available is False

    def test_full_workflow_partial_data(self, tmp_path):
        """Test workflow with partial data available."""
        from src.tui.components.stats_display import StatsDisplay

        # Create DuckDB file but not ChromaDB
        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        display = StatsDisplay(
            theme=MockTheme(),
            duckdb_path=db_path,
            chromadb_path=tmp_path / "missing_chromadb",
        )

        stats = display.collect_stats()
        panel = display.render(stats)

        assert panel is not None
        # DuckDB exists but may not have valid data
        assert stats.chromadb_available is False
