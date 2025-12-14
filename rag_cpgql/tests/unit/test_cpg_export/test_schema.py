"""Tests for CPG schema module."""
import pytest
import duckdb
from pathlib import Path


class TestSchemaDefinitions:
    """Tests for schema definitions."""

    def test_node_tables_defined(self):
        """Test that all required node tables are defined."""
        from src.cpg_export.schema import NODE_TABLES

        # Core nodes
        assert 'nodes_method' in NODE_TABLES
        assert 'nodes_call' in NODE_TABLES
        assert 'nodes_identifier' in NODE_TABLES
        assert 'nodes_literal' in NODE_TABLES
        assert 'nodes_local' in NODE_TABLES
        assert 'nodes_param' in NODE_TABLES
        assert 'nodes_return' in NODE_TABLES
        assert 'nodes_block' in NODE_TABLES
        assert 'nodes_control_structure' in NODE_TABLES

        # Structure nodes
        assert 'nodes_file' in NODE_TABLES
        assert 'nodes_namespace' in NODE_TABLES
        assert 'nodes_type' in NODE_TABLES
        assert 'nodes_type_decl' in NODE_TABLES

    def test_edge_tables_defined(self):
        """Test that all required edge tables are defined."""
        from src.cpg_export.schema import EDGE_TABLES

        # Core edges
        assert 'edges_ast' in EDGE_TABLES
        assert 'edges_cfg' in EDGE_TABLES
        assert 'edges_call' in EDGE_TABLES
        assert 'edges_ref' in EDGE_TABLES

        # Analysis edges
        assert 'edges_cdg' in EDGE_TABLES
        assert 'edges_reaching_def' in EDGE_TABLES
        assert 'edges_dominate' in EDGE_TABLES

    def test_indexes_defined(self):
        """Test that indexes are defined."""
        from src.cpg_export.schema import INDEXES

        assert len(INDEXES) > 0
        # Check for some important indexes
        index_strs = ' '.join(INDEXES)
        assert 'idx_method_full_name' in index_strs
        assert 'idx_call_method_full_name' in index_strs
        assert 'idx_ast_src' in index_strs

    def test_all_tables_list(self):
        """Test that ALL_TABLES contains all tables."""
        from src.cpg_export.schema import ALL_TABLES, ALL_NODE_TABLES, ALL_EDGE_TABLES

        assert len(ALL_TABLES) == len(ALL_NODE_TABLES) + len(ALL_EDGE_TABLES)
        assert 'nodes_method' in ALL_TABLES
        assert 'edges_ast' in ALL_TABLES


class TestSchemaInitialization:
    """Tests for schema initialization."""

    def test_initialize_schema_creates_tables(self, tmp_path):
        """Test that initialize_schema creates all tables."""
        from src.cpg_export.schema import initialize_schema, ALL_NODE_TABLES, ALL_EDGE_TABLES

        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        initialize_schema(conn)

        # Verify node tables exist
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

        for table_name in ALL_NODE_TABLES:
            assert table_name in tables, f"Node table {table_name} not created"

        for table_name in ALL_EDGE_TABLES:
            assert table_name in tables, f"Edge table {table_name} not created"

        conn.close()

    def test_initialize_schema_force_recreate(self, tmp_path):
        """Test that force_recreate drops and recreates tables."""
        from src.cpg_export.schema import initialize_schema

        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create schema first time
        initialize_schema(conn)

        # Insert a test row
        conn.execute("INSERT INTO nodes_method (id, name) VALUES (1, 'test')")
        count = conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0]
        assert count == 1

        # Force recreate
        initialize_schema(conn, force_recreate=True)

        # Verify table is empty after recreate
        count = conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0]
        assert count == 0

        conn.close()

    def test_initialize_schema_resume_mode(self, tmp_path):
        """Test that resume mode preserves existing data."""
        from src.cpg_export.schema import initialize_schema

        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create schema first time
        initialize_schema(conn)

        # Insert a test row
        conn.execute("INSERT INTO nodes_method (id, name) VALUES (1, 'test')")

        # Resume mode (default)
        initialize_schema(conn, force_recreate=False)

        # Verify data is preserved
        count = conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0]
        assert count == 1

        conn.close()

    def test_get_all_tables_to_drop(self):
        """Test get_all_tables_to_drop returns correct order."""
        from src.cpg_export.schema import get_all_tables_to_drop

        tables = get_all_tables_to_drop()

        # Edges should come before nodes for proper FK handling
        ast_idx = tables.index('edges_ast')
        method_idx = tables.index('nodes_method')
        assert ast_idx < method_idx, "Edges should be dropped before nodes"

        # Progress table should be included
        assert 'export_progress' in tables
