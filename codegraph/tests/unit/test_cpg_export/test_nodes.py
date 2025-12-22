"""Tests for CPG node exporters."""
import pytest
from unittest.mock import MagicMock
import duckdb


class TestNodeExporterBase:
    """Tests for NodeExporter base class."""

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
        # Create method table for testing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_method (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                full_name VARCHAR,
                signature VARCHAR,
                filename VARCHAR,
                line_number INTEGER,
                column_number INTEGER,
                line_number_end INTEGER,
                column_number_end INTEGER,
                code TEXT,
                is_external BOOLEAN,
                ast_parent_type VARCHAR,
                ast_parent_full_name VARCHAR,
                order_index INTEGER,
                hash VARCHAR
            )
        """)
        return conn

    def test_parse_int(self):
        """Test parse_int utility function."""
        from src.cpg_export.nodes.base import parse_int

        assert parse_int('123') == 123
        assert parse_int('0') == 0
        assert parse_int('-1') is None  # Negative numbers are treated as None
        assert parse_int('') is None
        assert parse_int('abc') is None

    def test_parse_bool(self):
        """Test parse_bool utility function."""
        from src.cpg_export.nodes.base import parse_bool

        assert parse_bool('true') is True
        assert parse_bool('True') is True
        assert parse_bool('TRUE') is True
        assert parse_bool('false') is False
        assert parse_bool('False') is False
        assert parse_bool('') is False

    def test_escape_code(self):
        """Test escape_code utility function."""
        from src.cpg_export.nodes.base import escape_code

        assert escape_code('line1\nline2') == 'line1\\nline2'
        assert escape_code('tab\there') == 'tab\\there'
        assert escape_code('return\rhere') == 'return\\rhere'


class TestCoreNodeExporters:
    """Tests for core node exporters."""

    def test_method_exporter_properties(self):
        """Test MethodExporter properties."""
        from src.cpg_export.nodes import MethodExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = MethodExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_method'
        assert exporter.cpg_type == 'method'
        assert 'cpg.method' in exporter.query_template
        assert 'nodes_method' in exporter.insert_sql
        assert exporter.field_count == 13

    def test_call_exporter_properties(self):
        """Test CallExporter properties."""
        from src.cpg_export.nodes import CallExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = CallExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_call'
        assert exporter.cpg_type == 'call'
        assert exporter.field_count == 12

    def test_identifier_exporter_properties(self):
        """Test IdentifierExporter properties."""
        from src.cpg_export.nodes import IdentifierExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = IdentifierExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_identifier'
        assert exporter.cpg_type == 'identifier'
        assert exporter.field_count == 8

    def test_method_exporter_parse_row(self):
        """Test MethodExporter.parse_row."""
        from src.cpg_export.nodes import MethodExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = MethodExporter(mock_client, mock_conn)

        parts = [
            '123',      # id
            'test_fn',  # name
            'pkg.test_fn',  # full_name
            'void()',   # signature
            'test.py',  # filename
            '10',       # line_number
            '5',        # column_number
            '20',       # line_number_end
            '10',       # column_number_end
            'code',     # code
            'false',    # is_external
            'FILE',     # ast_parent_type
            'test.py',  # ast_parent_full_name
        ]

        row = exporter.parse_row(parts)

        assert row[0] == 123  # id
        assert row[1] == 'test_fn'  # name
        assert row[5] == 10  # line_number
        assert row[10] is False  # is_external


class TestStructureNodeExporters:
    """Tests for structure node exporters."""

    def test_file_exporter_properties(self):
        """Test FileExporter properties."""
        from src.cpg_export.nodes import FileExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = FileExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_file'
        assert exporter.cpg_type == 'file'

    def test_namespace_exporter_properties(self):
        """Test NamespaceExporter properties."""
        from src.cpg_export.nodes import NamespaceExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = NamespaceExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_namespace'
        assert exporter.cpg_type == 'namespace'

    def test_type_decl_exporter_properties(self):
        """Test TypeDeclExporter properties."""
        from src.cpg_export.nodes import TypeDeclExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = TypeDeclExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_type_decl'
        assert exporter.cpg_type == 'typeDecl'


class TestSupplementaryNodeExporters:
    """Tests for supplementary node exporters."""

    def test_modifier_exporter_properties(self):
        """Test ModifierExporter properties."""
        from src.cpg_export.nodes import ModifierExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = ModifierExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_modifier'
        assert exporter.cpg_type == 'modifier'

    def test_annotation_exporter_properties(self):
        """Test AnnotationExporter properties."""
        from src.cpg_export.nodes import AnnotationExporter

        mock_client = MagicMock()
        mock_conn = MagicMock()
        exporter = AnnotationExporter(mock_client, mock_conn)

        assert exporter.entity_type == 'nodes_annotation'
        assert exporter.cpg_type == 'annotation'


class TestNodeExportersList:
    """Tests for exporter lists."""

    def test_core_exporters_list(self):
        """Test CORE_EXPORTERS list."""
        from src.cpg_export.nodes import CORE_EXPORTERS

        assert len(CORE_EXPORTERS) == 9
        # Check class names
        names = [e.__name__ for e in CORE_EXPORTERS]
        assert 'MethodExporter' in names
        assert 'CallExporter' in names
        assert 'IdentifierExporter' in names

    def test_structure_exporters_list(self):
        """Test STRUCTURE_EXPORTERS list."""
        from src.cpg_export.nodes import STRUCTURE_EXPORTERS

        assert len(STRUCTURE_EXPORTERS) == 7
        names = [e.__name__ for e in STRUCTURE_EXPORTERS]
        assert 'FileExporter' in names
        assert 'TypeDeclExporter' in names

    def test_all_node_exporters_list(self):
        """Test ALL_NODE_EXPORTERS list."""
        from src.cpg_export.nodes import ALL_NODE_EXPORTERS

        # Should include core + structure + supplementary
        assert len(ALL_NODE_EXPORTERS) > 15

    def test_get_all_exporters(self):
        """Test get_all_exporters function."""
        from src.cpg_export.nodes import get_all_exporters

        mock_client = MagicMock()
        mock_conn = MagicMock()

        exporters = get_all_exporters(mock_client, mock_conn, batch_size=5000)

        assert len(exporters) > 15
        # Check that they're instantiated with correct params
        assert exporters[0].batch_size == 5000
