"""Tests for CPG edge exporters."""
import pytest
from unittest.mock import MagicMock
import duckdb


class TestEdgeExporterBase:
    """Tests for EdgeExporter base class."""

    @pytest.fixture
    def mock_joern_client(self):
        """Create a mock JoernClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def db_conn(self, tmp_path):
        """Create a DuckDB connection."""
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        # Create edge table for testing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_ast (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)
        return conn

    def test_edge_exporter_default_count_query(self):
        """Test default count_query property."""
        from src.cpg_export.edges import AstEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = AstEdgeExporter(mock_client, mock_conn)

        assert exporter.count_query == "cpg.all.size"

    def test_edge_exporter_custom_count_query(self):
        """Test custom count_query property."""
        from src.cpg_export.edges import RefEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = RefEdgeExporter(mock_client, mock_conn)

        assert exporter.count_query == "cpg.identifier.size"

    def test_parse_edge_default(self):
        """Test default parse_edge method."""
        from src.cpg_export.edges import AstEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = AstEdgeExporter(mock_client, mock_conn)

        edge = exporter.parse_edge(['123', '456'])
        assert edge == (123, 456)


class TestCoreEdgeExporters:
    """Tests for core edge exporters."""

    def test_ast_edge_exporter_properties(self):
        """Test AstEdgeExporter properties."""
        from src.cpg_export.edges import AstEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = AstEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_ast'
        assert 'astChildren' in exporter.edge_query_template
        assert 'edges_ast' in exporter.insert_sql

    def test_cfg_edge_exporter_properties(self):
        """Test CfgEdgeExporter properties."""
        from src.cpg_export.edges import CfgEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = CfgEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_cfg'
        assert 'cfgNext' in exporter.edge_query_template

    def test_call_edge_exporter_properties(self):
        """Test CallEdgeExporter properties."""
        from src.cpg_export.edges import CallEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = CallEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_call'
        assert exporter.count_query == 'cpg.call.size'
        assert 'callee' in exporter.edge_query_template

    def test_ref_edge_exporter_properties(self):
        """Test RefEdgeExporter properties."""
        from src.cpg_export.edges import RefEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = RefEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_ref'
        assert exporter.count_query == 'cpg.identifier.size'


class TestAnalysisEdgeExporters:
    """Tests for analysis edge exporters."""

    def test_reaching_def_exporter_properties(self):
        """Test ReachingDefEdgeExporter properties."""
        from src.cpg_export.edges import ReachingDefEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = ReachingDefEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_reaching_def'
        assert 'reachingDefOut' in exporter.edge_query_template

    def test_reaching_def_parse_edge(self):
        """Test ReachingDefEdgeExporter.parse_edge with variable."""
        from src.cpg_export.edges import ReachingDefEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = ReachingDefEdgeExporter(mock_client, mock_conn)

        # With variable
        edge = exporter.parse_edge(['123', '456', 'var_name'])
        assert edge == (123, 456, 'var_name')

        # Without variable
        edge = exporter.parse_edge(['123', '456', ''])
        assert edge == (123, 456, None)

    def test_cdg_edge_exporter_properties(self):
        """Test CdgEdgeExporter properties."""
        from src.cpg_export.edges import CdgEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = CdgEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_cdg'
        assert 'cdgOut' in exporter.edge_query_template

    def test_dominate_edge_exporter_properties(self):
        """Test DominateEdgeExporter properties."""
        from src.cpg_export.edges import DominateEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = DominateEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_dominate'
        assert 'dominates' in exporter.edge_query_template

    def test_eval_type_exporter_properties(self):
        """Test EvalTypeEdgeExporter properties."""
        from src.cpg_export.edges import EvalTypeEdgeExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = EvalTypeEdgeExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'edges_eval_type'
        assert 'evalTypeOut' in exporter.edge_query_template


class TestEdgeExportersList:
    """Tests for edge exporter lists."""

    def test_core_edge_exporters_list(self):
        """Test CORE_EDGE_EXPORTERS list."""
        from src.cpg_export.edges import CORE_EDGE_EXPORTERS

        assert len(CORE_EDGE_EXPORTERS) == 8
        names = [e.__name__ for e in CORE_EDGE_EXPORTERS]
        assert 'AstEdgeExporter' in names
        assert 'CfgEdgeExporter' in names
        assert 'CallEdgeExporter' in names

    def test_analysis_edge_exporters_list(self):
        """Test ANALYSIS_EDGE_EXPORTERS list."""
        from src.cpg_export.edges import ANALYSIS_EDGE_EXPORTERS

        assert len(ANALYSIS_EDGE_EXPORTERS) == 12
        names = [e.__name__ for e in ANALYSIS_EDGE_EXPORTERS]
        assert 'ReachingDefEdgeExporter' in names
        assert 'CdgEdgeExporter' in names
        assert 'EvalTypeEdgeExporter' in names

    def test_all_edge_exporters_list(self):
        """Test ALL_EDGE_EXPORTERS list."""
        from src.cpg_export.edges import ALL_EDGE_EXPORTERS

        # Should include core + analysis
        assert len(ALL_EDGE_EXPORTERS) == 20

    def test_get_all_exporters(self):
        """Test get_all_exporters function."""
        from src.cpg_export.edges import get_all_exporters

        mock_client = MagicMock()
        mock_conn = MagicMock()

        exporters = get_all_exporters(mock_client, mock_conn, batch_size=5000)

        assert len(exporters) == 20
        # Check that they're instantiated with correct params
        assert exporters[0].batch_size == 5000
