"""Export Joern CPG to DuckDB (CPG Spec v1.1 Compliant)

This module exports Code Property Graphs from Joern to DuckDB using batched queries
and the official CPG spec v1.1 schema.

Supports:
- All major node types (METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, etc.)
- All major edge types (AST, CFG, CALL, REF, REACHING_DEF, etc.)
- Batched export for large codebases (50K+ methods)
- Full CPG spec v1.1 compliance
"""

import os
import sys
import duckdb
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.execution.joern_client import JoernClient
from src.execution.scala_parser import parse_scala_output

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JoernToDuckDB:
    """Export Joern CPG to DuckDB with CPG Spec v1.1 schema"""

    def __init__(
        self,
        server_endpoint: str = "localhost:8080",
        workspace: str = "pg17_full.cpg",
        db_path: str = "cpg.duckdb",
        batch_size: int = 10000
    ):
        """
        Initialize Joern to DuckDB exporter

        Args:
            server_endpoint: Joern server endpoint (host:port)
            workspace: Name of the workspace/CPG to open
            db_path: Path to DuckDB database file
            batch_size: Number of rows to insert in each batch
        """
        self.joern_client = JoernClient(server_endpoint, workspace)
        self.db_path = db_path
        self.batch_size = batch_size
        self.conn = None

    def connect_db(self):
        """Connect to DuckDB and load duckpgq extension"""
        logger.info(f"Connecting to DuckDB: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)

        # Load duckpgq extension for property graph queries
        try:
            self.conn.execute("INSTALL duckpgq;")
            self.conn.execute("LOAD duckpgq;")
            logger.info("DuckPGQ extension loaded successfully")
        except Exception as e:
            logger.warning(f"DuckPGQ extension error (may already be installed): {e}")

    def close_db(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    # =========================================================================
    # Progress Tracking Methods
    # =========================================================================

    def _create_progress_table(self):
        """Create export_progress table if not exists"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS export_progress (
                entity_type VARCHAR PRIMARY KEY,
                total_count BIGINT,
                exported_count BIGINT,
                last_offset BIGINT,
                status VARCHAR,
                last_updated TIMESTAMP,
                error_message VARCHAR
            )
        """)
        logger.info("Export progress table ready")

    def _get_export_status(self, entity_type: str) -> tuple:
        """Get export status and last offset for entity type

        Returns:
            tuple: (status, last_offset) or ('pending', 0) if not found
        """
        result = self.conn.execute("""
            SELECT status, last_offset FROM export_progress
            WHERE entity_type = ?
        """, [entity_type]).fetchone()
        return (result[0], result[1]) if result else ('pending', 0)

    def _update_export_progress(self, entity_type: str, total: int, exported: int,
                                 offset: int, status: str, error: str = None):
        """Update export progress for entity type"""
        self.conn.execute("""
            INSERT OR REPLACE INTO export_progress
            (entity_type, total_count, exported_count, last_offset, status, last_updated, error_message)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, [entity_type, total, exported, offset, status, error])

    def _mark_completed(self, entity_type: str, total: int = 0):
        """Mark entity export as completed"""
        self._update_export_progress(entity_type, total, total, total, 'completed')
        logger.info(f"[OK] {entity_type} export completed ({total} records)")

    def _mark_failed(self, entity_type: str, error: str, offset: int = 0):
        """Mark entity export as failed"""
        self._update_export_progress(entity_type, 0, 0, offset, 'failed', error)
        logger.error(f"[FAIL] {entity_type} export failed at offset {offset}: {error}")

    def _is_completed(self, entity_type: str) -> bool:
        """Check if entity export is already completed"""
        status, _ = self._get_export_status(entity_type)
        return status == 'completed'

    def _get_existing_count(self, table_name: str) -> int:
        """Get count of existing records in table"""
        try:
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except:
            return 0

    # =========================================================================
    # Schema Initialization
    # =========================================================================

    def _initialize_schema(self, force_recreate: bool = False):
        """Initialize DuckDB schema for CPG storage (CPG Spec v1.1)

        Args:
            force_recreate: If True, drop existing tables. If False, preserve existing data.
        """
        logger.info("Initializing CPG schema (CPG Spec v1.1)...")

        if force_recreate:
            # Drop existing tables if force_recreate is True
            logger.info("Force recreate: dropping existing tables...")
            tables_to_drop = [
                # P0-P3 Edges (new)
                "edges_binds", "edges_tagged_by", "edges_parameter_link", "edges_binds_to",
                "edges_alias_of", "edges_inherits_from", "edges_eval_type", "edges_contains", "edges_cdg",
                # Existing edges
                "edges_post_dominate", "edges_dominate", "edges_condition",
                "edges_receiver", "edges_argument", "edges_reaching_def",
                "edges_ref", "edges_call", "edges_cfg", "edges_ast",
                "edges_source_file", "edges_include",
                # P0-P3 Nodes (new)
                "nodes_annotation_parameter_assign", "nodes_annotation_parameter",
                "nodes_annotation_literal", "nodes_annotation", "nodes_binding",
                "nodes_unknown", "nodes_type_ref", "nodes_modifier", "nodes_method_ref",
                "nodes_jump_target", "nodes_jump_label", "nodes_type_parameter",
                "nodes_type_argument", "nodes_field_identifier", "nodes_method_return",
                "nodes_method_parameter_out", "nodes_type", "nodes_member",
                "nodes_namespace_block", "nodes_namespace", "nodes_file",
                # Existing nodes
                "nodes_metadata", "nodes_type_decl", "nodes_control_structure",
                "nodes_block", "nodes_return", "nodes_param", "nodes_local",
                "nodes_literal", "nodes_identifier", "nodes_call", "nodes_method",
                "nodes_comment", "export_progress", "cpg_nodes"
            ]
            for table in tables_to_drop:
                self.conn.execute(f"DROP TABLE IF EXISTS {table}")
        else:
            logger.info("Resume mode: preserving existing tables with data")

        # Create nodes_method table (CPG Spec: METHOD node)
        logger.info("Creating node tables (IF NOT EXISTS)...")
        self.conn.execute("""
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

        # Create nodes_call table (CPG Spec: CALL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_call (
                id BIGINT PRIMARY KEY,
                method_full_name VARCHAR,
                name VARCHAR,
                signature VARCHAR,
                type_full_name VARCHAR,
                dispatch_type VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                filename VARCHAR
            )
        """)

        # Create nodes_identifier table (CPG Spec: IDENTIFIER node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_identifier (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER
            )
        """)

        # Create nodes_literal table (CPG Spec: LITERAL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_literal (
                id BIGINT PRIMARY KEY,
                code TEXT,
                type_full_name VARCHAR,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER
            )
        """)

        # Create nodes_local table (CPG Spec: LOCAL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_local (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_param table (CPG Spec: METHOD_PARAMETER_IN/OUT node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_param (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                index INTEGER,
                is_variadic BOOLEAN,
                evaluation_strategy VARCHAR
            )
        """)

        # Create nodes_return table (CPG Spec: RETURN node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_return (
                id BIGINT PRIMARY KEY,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER
            )
        """)

        # Create nodes_block table (CPG Spec: BLOCK node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_block (
                id BIGINT PRIMARY KEY,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER
            )
        """)

        # Create nodes_control_structure table (CPG Spec: CONTROL_STRUCTURE node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_control_structure (
                id BIGINT PRIMARY KEY,
                control_structure_type VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                parser_type_name VARCHAR
            )
        """)

        # Create nodes_type_decl table (CPG Spec: TYPE_DECL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_type_decl (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                full_name VARCHAR,
                is_external BOOLEAN,
                inherits_from_type_full_name VARCHAR[],
                alias_type_full_name VARCHAR,
                filename VARCHAR,
                code TEXT,
                ast_parent_type VARCHAR,
                ast_parent_full_name VARCHAR
            )
        """)

        # Create nodes_metadata table (CPG Spec: META_DATA node - required)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_metadata (
                id BIGINT PRIMARY KEY,
                language VARCHAR,
                version VARCHAR,
                overlays VARCHAR[],
                root VARCHAR
            )
        """)

        # Create nodes_comment table (CPG Spec: COMMENT node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_comment (
                id BIGINT PRIMARY KEY,
                code TEXT,
                filename VARCHAR,
                line_number INTEGER,
                column_number INTEGER,
                "offset" INTEGER,
                "offset_end" INTEGER,
                order_index INTEGER
            )
        """)

        # =====================================================================
        # P0 Nodes - Critical for code structure
        # =====================================================================

        # Create nodes_file table (CPG Spec: FILE node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_file (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                hash VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_namespace table (CPG Spec: NAMESPACE node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_namespace (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_namespace_block table (CPG Spec: NAMESPACE_BLOCK node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_namespace_block (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                full_name VARCHAR,
                filename VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_member table (CPG Spec: MEMBER node - struct/class fields)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_member (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_type table (CPG Spec: TYPE node - type instances)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_type (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                full_name VARCHAR,
                type_decl_full_name VARCHAR
            )
        """)

        # =====================================================================
        # P1 Nodes - Important for analysis
        # =====================================================================

        # Create nodes_method_parameter_out table (CPG Spec: METHOD_PARAMETER_OUT node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_method_parameter_out (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                index INTEGER,
                is_variadic BOOLEAN,
                evaluation_strategy VARCHAR
            )
        """)

        # Create nodes_method_return table (CPG Spec: METHOD_RETURN node - formal return)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_method_return (
                id BIGINT PRIMARY KEY,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                evaluation_strategy VARCHAR
            )
        """)

        # Create nodes_field_identifier table (CPG Spec: FIELD_IDENTIFIER node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_field_identifier (
                id BIGINT PRIMARY KEY,
                canonical_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # Create nodes_type_argument table (CPG Spec: TYPE_ARGUMENT node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_type_argument (
                id BIGINT PRIMARY KEY,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_type_parameter table (CPG Spec: TYPE_PARAMETER node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_type_parameter (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # =====================================================================
        # P2 Nodes - Supplementary
        # =====================================================================

        # Create nodes_jump_label table (CPG Spec: JUMP_LABEL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_jump_label (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                parser_type_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_jump_target table (CPG Spec: JUMP_TARGET node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_jump_target (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                parser_type_name VARCHAR,
                argument_index INTEGER,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_method_ref table (CPG Spec: METHOD_REF node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_method_ref (
                id BIGINT PRIMARY KEY,
                method_full_name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # Create nodes_modifier table (CPG Spec: MODIFIER node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_modifier (
                id BIGINT PRIMARY KEY,
                modifier_type VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_type_ref table (CPG Spec: TYPE_REF node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_type_ref (
                id BIGINT PRIMARY KEY,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # Create nodes_unknown table (CPG Spec: UNKNOWN node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_unknown (
                id BIGINT PRIMARY KEY,
                contained_ref VARCHAR,
                parser_type_name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # =====================================================================
        # P3 Nodes - Low priority
        # =====================================================================

        # Create nodes_binding table (CPG Spec: BINDING node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_binding (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                signature VARCHAR,
                method_full_name VARCHAR
            )
        """)

        # Create nodes_annotation table (CPG Spec: ANNOTATION node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_annotation (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # Create nodes_annotation_literal table (CPG Spec: ANNOTATION_LITERAL node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_annotation_literal (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                argument_index INTEGER,
                argument_name VARCHAR
            )
        """)

        # Create nodes_annotation_parameter table (CPG Spec: ANNOTATION_PARAMETER node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_annotation_parameter (
                id BIGINT PRIMARY KEY,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create nodes_annotation_parameter_assign table (CPG Spec: ANNOTATION_PARAMETER_ASSIGN node)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_annotation_parameter_assign (
                id BIGINT PRIMARY KEY,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER
            )
        """)

        # Create edge tables
        logger.info("Creating edge tables (IF NOT EXISTS)...")

        # Create edges_ast table (CPG Spec: AST edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_ast (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_cfg table (CPG Spec: CFG edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_cfg (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_call table (CPG Spec: CALL edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_call (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_ref table (CPG Spec: REF edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_ref (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_reaching_def table (CPG Spec: REACHING_DEF edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_reaching_def (
                src BIGINT,
                dst BIGINT,
                variable VARCHAR,
                PRIMARY KEY (src, dst, variable)
            )
        """)

        # Create edges_argument table (CPG Spec: ARGUMENT edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_argument (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_receiver table (CPG Spec: RECEIVER edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_receiver (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_condition table (CPG Spec: CONDITION edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_condition (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_dominate table (CPG Spec: DOMINATE edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_dominate (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_post_dominate table (CPG Spec: POST_DOMINATE edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_post_dominate (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_source_file table (Comment to AST parent relationship)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_source_file (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # =====================================================================
        # P0 Edges - Critical for analysis
        # =====================================================================

        # Create edges_cdg table (CPG Spec: CDG edge - Control Dependence Graph)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_cdg (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_contains table (CPG Spec: CONTAINS edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_contains (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_eval_type table (CPG Spec: EVAL_TYPE edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_eval_type (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # =====================================================================
        # P1 Edges - Important for OOP analysis
        # =====================================================================

        # Create edges_inherits_from table (CPG Spec: INHERITS_FROM edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_inherits_from (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_alias_of table (CPG Spec: ALIAS_OF edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_alias_of (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # =====================================================================
        # P2 Edges - Supplementary
        # =====================================================================

        # Create edges_binds_to table (CPG Spec: BINDS_TO edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_binds_to (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_parameter_link table (CPG Spec: PARAMETER_LINK edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_parameter_link (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # =====================================================================
        # P3 Edges - Low priority
        # =====================================================================

        # Create edges_tagged_by table (CPG Spec: TAGGED_BY edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_tagged_by (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_binds table (CPG Spec: BINDS edge)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_binds (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        logger.info("Creating indexes (IF NOT EXISTS)...")

        # Node indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_method_full_name ON nodes_method(full_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_method_name ON nodes_method(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_method_filename ON nodes_method(filename)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_call_method_full_name ON nodes_call(method_full_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_call_name ON nodes_call(name)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_identifier_name ON nodes_identifier(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_local_name ON nodes_local(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_param_name ON nodes_param(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type_decl_full_name ON nodes_type_decl(full_name)")

        # Edge indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ast_src ON edges_ast(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ast_dst ON edges_ast(dst)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cfg_src ON edges_cfg(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cfg_dst ON edges_cfg(dst)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_call_edge_src ON edges_call(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_call_edge_dst ON edges_call(dst)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_src ON edges_ref(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_dst ON edges_ref(dst)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reaching_def_src ON edges_reaching_def(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reaching_def_dst ON edges_reaching_def(dst)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reaching_def_variable ON edges_reaching_def(variable)")

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_argument_src ON edges_argument(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_argument_dst ON edges_argument(dst)")

        # Comment indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_comment_filename ON nodes_comment(filename)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_comment_line ON nodes_comment(line_number)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source_file_src ON edges_source_file(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source_file_dst ON edges_source_file(dst)")

        # P0 Node indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_file_name ON nodes_file(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace_name ON nodes_namespace(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace_block_full_name ON nodes_namespace_block(full_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_member_name ON nodes_member(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type_full_name ON nodes_type(full_name)")

        # P1 Node indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_field_identifier_canonical ON nodes_field_identifier(canonical_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_method_ref_method ON nodes_method_ref(method_full_name)")

        # P2 Node indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_modifier_type ON nodes_modifier(modifier_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type_ref_type ON nodes_type_ref(type_full_name)")

        # P0-P3 Edge indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cdg_src ON edges_cdg(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cdg_dst ON edges_cdg(dst)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contains_src ON edges_contains(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contains_dst ON edges_contains(dst)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_type_src ON edges_eval_type(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_type_dst ON edges_eval_type(dst)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_inherits_from_src ON edges_inherits_from(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_inherits_from_dst ON edges_inherits_from(dst)")

        logger.info("DuckDB schema initialized successfully (CPG Spec v1.1 compliant)")

    def _create_property_graph(self):
        """Create DuckDB Property Graph for CPG with full schema support

        Uses materialized cpg_nodes table to support polymorphic edges.
        """
        logger.info("Creating Property Graph...")

        # Drop existing property graph if it exists
        try:
            self.conn.execute("DROP PROPERTY GRAPH IF EXISTS cpg")
        except Exception as e:
            logger.warning(f"Could not drop existing property graph: {e}")

        # Step 1: Create materialized cpg_nodes table (not view!) for polymorphic edges
        logger.info("Creating materialized cpg_nodes table...")
        try:
            self.conn.execute("DROP TABLE IF EXISTS cpg_nodes")
        except:
            pass

        self.conn.execute("""
            CREATE TABLE cpg_nodes AS
            -- Existing nodes
            SELECT id, 'METHOD' as node_type FROM nodes_method
            UNION ALL SELECT id, 'CALL' FROM nodes_call
            UNION ALL SELECT id, 'IDENTIFIER' FROM nodes_identifier
            UNION ALL SELECT id, 'LITERAL' FROM nodes_literal
            UNION ALL SELECT id, 'LOCAL' FROM nodes_local
            UNION ALL SELECT id, 'PARAM' FROM nodes_param
            UNION ALL SELECT id, 'RETURN' FROM nodes_return
            UNION ALL SELECT id, 'BLOCK' FROM nodes_block
            UNION ALL SELECT id, 'CONTROL_STRUCTURE' FROM nodes_control_structure
            UNION ALL SELECT id, 'TYPE_DECL' FROM nodes_type_decl
            UNION ALL SELECT id, 'METADATA' FROM nodes_metadata
            UNION ALL SELECT id, 'COMMENT' FROM nodes_comment
            -- P0 Nodes
            UNION ALL SELECT id, 'FILE' FROM nodes_file
            UNION ALL SELECT id, 'NAMESPACE' FROM nodes_namespace
            UNION ALL SELECT id, 'NAMESPACE_BLOCK' FROM nodes_namespace_block
            UNION ALL SELECT id, 'MEMBER' FROM nodes_member
            UNION ALL SELECT id, 'TYPE' FROM nodes_type
            -- P1 Nodes
            UNION ALL SELECT id, 'METHOD_PARAMETER_OUT' FROM nodes_method_parameter_out
            UNION ALL SELECT id, 'METHOD_RETURN' FROM nodes_method_return
            UNION ALL SELECT id, 'FIELD_IDENTIFIER' FROM nodes_field_identifier
            UNION ALL SELECT id, 'TYPE_ARGUMENT' FROM nodes_type_argument
            UNION ALL SELECT id, 'TYPE_PARAMETER' FROM nodes_type_parameter
            -- P2 Nodes
            UNION ALL SELECT id, 'JUMP_LABEL' FROM nodes_jump_label
            UNION ALL SELECT id, 'JUMP_TARGET' FROM nodes_jump_target
            UNION ALL SELECT id, 'METHOD_REF' FROM nodes_method_ref
            UNION ALL SELECT id, 'MODIFIER' FROM nodes_modifier
            UNION ALL SELECT id, 'TYPE_REF' FROM nodes_type_ref
            UNION ALL SELECT id, 'UNKNOWN' FROM nodes_unknown
            -- P3 Nodes
            UNION ALL SELECT id, 'BINDING' FROM nodes_binding
            UNION ALL SELECT id, 'ANNOTATION' FROM nodes_annotation
        """)

        # Create primary key and index on cpg_nodes
        self.conn.execute("ALTER TABLE cpg_nodes ADD PRIMARY KEY (id)")
        self.conn.execute("CREATE INDEX idx_cpg_nodes_type ON cpg_nodes(node_type)")

        logger.info(f"Created cpg_nodes with {self.conn.execute('SELECT COUNT(*) FROM cpg_nodes').fetchone()[0]} nodes")

        # Step 2: Create comprehensive property graph with ALL edge types
        logger.info("Creating comprehensive CPG property graph...")
        self.conn.execute("""
            CREATE PROPERTY GRAPH cpg
            VERTEX TABLES (
                -- Existing nodes
                nodes_method LABEL METHOD,
                nodes_call LABEL CALL_NODE,
                nodes_identifier LABEL IDENTIFIER,
                nodes_literal LABEL LITERAL,
                nodes_local LABEL LOCAL,
                nodes_param LABEL PARAM,
                nodes_return LABEL RETURN_NODE,
                nodes_block LABEL BLOCK,
                nodes_control_structure LABEL CONTROL_STRUCTURE,
                nodes_type_decl LABEL TYPE_DECL,
                nodes_metadata LABEL METADATA,
                nodes_comment LABEL COMMENT,
                -- P0 Nodes
                nodes_file LABEL FILE_NODE,
                nodes_namespace LABEL NAMESPACE,
                nodes_namespace_block LABEL NAMESPACE_BLOCK,
                nodes_member LABEL MEMBER,
                nodes_type LABEL TYPE_NODE,
                -- P1 Nodes
                nodes_method_parameter_out LABEL METHOD_PARAMETER_OUT,
                nodes_method_return LABEL METHOD_RETURN,
                nodes_field_identifier LABEL FIELD_IDENTIFIER,
                nodes_type_argument LABEL TYPE_ARGUMENT,
                nodes_type_parameter LABEL TYPE_PARAMETER,
                -- P2 Nodes
                nodes_jump_label LABEL JUMP_LABEL,
                nodes_jump_target LABEL JUMP_TARGET,
                nodes_method_ref LABEL METHOD_REF,
                nodes_modifier LABEL MODIFIER,
                nodes_type_ref LABEL TYPE_REF,
                nodes_unknown LABEL UNKNOWN,
                -- P3 Nodes
                nodes_binding LABEL BINDING_NODE,
                nodes_annotation LABEL ANNOTATION,
                -- Polymorphic node table
                cpg_nodes LABEL CPG_NODE
            )
            EDGE TABLES (
                -- Polymorphic edges (using cpg_nodes)
                edges_ast
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL AST,
                edges_cfg
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL CFG,
                edges_ref
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL REF,
                edges_reaching_def
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL REACHING_DEF,
                edges_argument
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL ARGUMENT,
                edges_dominate
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL DOMINATE,
                edges_post_dominate
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL POST_DOMINATE,

                -- Specific typed edges
                edges_call
                    SOURCE KEY (src) REFERENCES nodes_call (id)
                    DESTINATION KEY (dst) REFERENCES nodes_method (id)
                    LABEL CALLS,
                edges_receiver
                    SOURCE KEY (src) REFERENCES nodes_call (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL RECEIVER,
                edges_condition
                    SOURCE KEY (src) REFERENCES nodes_control_structure (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL CONDITION,

                -- Comment edges
                edges_source_file
                    SOURCE KEY (src) REFERENCES nodes_comment (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL SOURCE_FILE,

                -- P0 Edges - Critical for analysis
                edges_cdg
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL CDG,
                edges_contains
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL CONTAINS,
                edges_eval_type
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type (id)
                    LABEL EVAL_TYPE,

                -- P1 Edges - OOP analysis
                edges_inherits_from
                    SOURCE KEY (src) REFERENCES nodes_type_decl (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type (id)
                    LABEL INHERITS_FROM,
                edges_alias_of
                    SOURCE KEY (src) REFERENCES nodes_type (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type_decl (id)
                    LABEL ALIAS_OF,

                -- P2 Edges
                edges_binds_to
                    SOURCE KEY (src) REFERENCES nodes_type_argument (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type_parameter (id)
                    LABEL BINDS_TO,
                edges_parameter_link
                    SOURCE KEY (src) REFERENCES nodes_param (id)
                    DESTINATION KEY (dst) REFERENCES nodes_method_parameter_out (id)
                    LABEL PARAMETER_LINK,

                -- P3 Edges
                edges_tagged_by
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL TAGGED_BY,
                edges_binds
                    SOURCE KEY (src) REFERENCES nodes_type_decl (id)
                    DESTINATION KEY (dst) REFERENCES nodes_binding (id)
                    LABEL BINDS
            )
        """)

        logger.info("[OK] Property Graph created successfully with ALL edge types!")
        logger.info("[OK] Nodes: METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE, TYPE_DECL, FILE, NAMESPACE, MEMBER, TYPE, etc.")
        logger.info("[OK] Edges: AST, CFG, CALL, REF, REACHING_DEF, CDG, CONTAINS, EVAL_TYPE, INHERITS_FROM, ALIAS_OF, etc.")

    def _export_methods_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export methods from Joern to DuckDB in batches

        Args:
            limit: Optional limit on number of methods to export
            start_offset: Offset to start from (for resume)
        """
        logger.info(f"Exporting methods (batch size: {self.batch_size}, start_offset: {start_offset}, limit: {limit or 'None'})...")

        # Get total count
        count_query = "cpg.method.size"
        count_result = self.joern_client.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.error("Failed to get method count")
            return 0

        # Parse count from result - look for the actual number after "= "
        import re
        count_str = count_result.get('result', '0')
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_methods = int(count_match.group(1)) if count_match else 0

        if limit:
            total_methods = min(total_methods, limit)

        logger.info(f"Total methods to export: {total_methods}")

        # Resume from start_offset
        offset = start_offset
        total_exported = self._get_existing_count('nodes_method') if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_exported})")

        while offset < total_methods:
            current_batch_size = min(self.batch_size, total_methods - offset)

            # Build batched query - escape newlines in code field
            query = f"""
cpg.method.drop({offset}).take({current_batch_size}).map {{ m =>
  List(
    m.id,
    m.name,
    m.fullName,
    m.signature,
    m.filename,
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.lineNumberEnd.getOrElse(-1),
    m.columnNumberEnd.getOrElse(-1),
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.isExternal.toString,
    m.astParentType,
    m.astParentFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            logger.info(f"Fetching methods {offset} to {offset + current_batch_size}...")
            query_result = self.joern_client.execute_query(query)

            if not query_result or not query_result.get('success'):
                logger.error("Failed to fetch methods batch")
                break

            result = query_result.get('result', '')
            if not result or result.strip() == "":
                logger.info("No more methods to export")
                break

            # Parse results and insert into DuckDB
            # Skip Scala REPL header line (val resXX: String = """)
            rows_to_insert = []
            for line in result.strip().split('\n'):
                if not line.strip():
                    continue
                # Skip Scala REPL output header
                if 'val' in line and 'res' in line and '=' in line:
                    continue

                parts = line.split('\t')
                if len(parts) < 13:
                    logger.warning(f"Skipping malformed row: {line[:100]}")
                    continue

                try:
                    row = (
                        int(parts[0]),  # id
                        parts[1],       # name
                        parts[2],       # full_name
                        parts[3],       # signature
                        parts[4],       # filename
                        int(parts[5]) if parts[5].lstrip('-').isdigit() else None,  # line_number
                        int(parts[6]) if parts[6].lstrip('-').isdigit() else None,  # column_number
                        int(parts[7]) if parts[7].lstrip('-').isdigit() else None,  # line_number_end
                        int(parts[8]) if parts[8].lstrip('-').isdigit() else None,  # column_number_end
                        parts[9],       # code
                        parts[10].lower() == 'true',  # is_external
                        parts[11],      # ast_parent_type
                        parts[12],      # ast_parent_full_name
                        None,           # order_index
                        None            # hash
                    )
                    rows_to_insert.append(row)
                except Exception as e:
                    logger.warning(f"Error parsing row: {e} - Row: {line[:100]}")
                    continue

            # Bulk insert (use INSERT OR IGNORE to skip duplicates on resume)
            if rows_to_insert:
                self.conn.executemany("""
                    INSERT OR IGNORE INTO nodes_method VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_to_insert)

                total_exported += len(rows_to_insert)
                logger.info(f"Inserted {len(rows_to_insert)} methods (total: {total_exported}/{total_methods})")

                # Update progress after each batch
                self._update_export_progress('nodes_method', total_methods, total_exported,
                                             offset + current_batch_size, 'in_progress')

            offset += current_batch_size

        logger.info(f"Method export complete. Total exported: {total_exported}")
        return total_exported

    def _export_calls_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CALL nodes and CALL edges from Joern to DuckDB in batches

        Args:
            limit: Optional limit on number of calls to export
            start_offset: Offset to start from (for resume)
        """
        logger.info(f"Exporting CALL nodes and edges (batch size: {self.batch_size}, start_offset: {start_offset})...")

        # Get total count
        count_query = "cpg.call.size"
        count_result = self.joern_client.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.error("Failed to get call count")
            return 0, 0

        # Parse count from result
        import re
        count_str = count_result.get('result', '0')
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_calls = int(count_match.group(1)) if count_match else 0

        if limit:
            total_calls = min(total_calls, limit)

        logger.info(f"Total call nodes to export: {total_calls}")

        # Resume from start_offset
        offset = start_offset
        total_call_nodes = self._get_existing_count('nodes_call') if start_offset > 0 else 0
        total_call_edges = self._get_existing_count('edges_call') if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_call_nodes} nodes, {total_call_edges} edges)")

        while offset < total_calls:
            current_batch_size = min(self.batch_size, total_calls - offset)

            # Build batched query for CALL nodes (includes filename for completeness)
            # Escape newlines in code field to avoid parsing issues
            query = f"""
cpg.call.drop({offset}).take({current_batch_size}).map {{ c =>
  List(
    c.id,
    c.methodFullName,
    c.name,
    c.signature,
    c.typeFullName,
    c.dispatchType,
    c.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.order,
    c.argumentIndex,
    c.file.name.headOption.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            logger.info(f"Fetching call nodes {offset} to {offset + current_batch_size}...")
            query_result = self.joern_client.execute_query(query)

            if not query_result or not query_result.get('success'):
                logger.error("Failed to fetch call nodes batch")
                break

            result = query_result.get('result', '')
            if not result or result.strip() == "":
                logger.info("No more call nodes to export")
                break

            # Parse results and insert CALL nodes
            # Skip Scala REPL header line
            call_rows = []
            call_ids = []

            for line in result.strip().split('\n'):
                if not line.strip():
                    continue
                # Skip Scala REPL output header
                if 'val' in line and 'res' in line and '=' in line:
                    continue

                parts = line.split('\t')
                if len(parts) < 12:  # Now includes filename as 12th field
                    continue

                try:
                    call_id = int(parts[0])
                    row = (
                        call_id,        # id
                        parts[1],       # method_full_name
                        parts[2],       # name
                        parts[3],       # signature
                        parts[4],       # type_full_name
                        parts[5],       # dispatch_type
                        parts[6],       # code
                        int(parts[7]) if parts[7].lstrip('-').isdigit() else None,  # line_number
                        int(parts[8]) if parts[8].lstrip('-').isdigit() else None,  # column_number
                        int(parts[9]) if parts[9].lstrip('-').isdigit() else None,  # order_index
                        int(parts[10]) if parts[10].lstrip('-').isdigit() else None,  # argument_index
                        parts[11] if len(parts) > 11 and parts[11] else None  # filename
                    )
                    call_rows.append(row)
                    call_ids.append(call_id)
                except Exception as e:
                    logger.warning(f"Error parsing call row: {e}")
                    continue

            # Bulk insert CALL nodes (use INSERT OR IGNORE to skip duplicates on resume)
            if call_rows:
                self.conn.executemany("""
                    INSERT OR IGNORE INTO nodes_call VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, call_rows)
                total_call_nodes += len(call_rows)

            # Now fetch CALL edges for these call nodes
            if call_ids:
                call_ids_str = ", ".join(map(str, call_ids))
                edges_query = f"""
val callIds = Set({call_ids_str})
cpg.call.filter(c => callIds.contains(c.id)).map {{ c =>
  c.callee.map(m => s"${{c.id}}\\t${{m.id}}").mkString("\\n")
}}.l.mkString("\\n")
"""

                edges_query_result = self.joern_client.execute_query(edges_query)

                if edges_query_result and edges_query_result.get('success'):
                    edges_result = edges_query_result.get('result', '')
                    if edges_result and edges_result.strip():
                        edge_rows = []
                        for line in edges_result.strip().split('\n'):
                            if not line.strip():
                                continue
                            parts = line.split('\t')
                            if len(parts) == 2:
                                try:
                                    edge_rows.append((int(parts[0]), int(parts[1])))
                                except:
                                    continue

                        if edge_rows:
                            self.conn.executemany("INSERT OR IGNORE INTO edges_call VALUES (?, ?)", edge_rows)
                            total_call_edges += len(edge_rows)
                            logger.info(f"Inserted {len(edge_rows)} call edges")

            logger.info(f"Progress: {total_call_nodes}/{total_calls} call nodes, {total_call_edges} call edges")

            # Update progress after each batch
            self._update_export_progress('nodes_call', total_calls, total_call_nodes,
                                         offset + current_batch_size, 'in_progress')

            offset += current_batch_size

        logger.info(f"Call export complete. Nodes: {total_call_nodes}, Edges: {total_call_edges}")
        return total_call_nodes, total_call_edges

    # =========================================================================
    # Additional Node Export Methods
    # =========================================================================

    def _export_identifiers_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export IDENTIFIER nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_identifier',
            cpg_type='identifier',
            query_template="""
cpg.identifier.drop({offset}).take({batch_size}).map {{ i =>
  List(
    i.id,
    i.name,
    i.typeFullName,
    i.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    i.lineNumber.getOrElse(-1),
    i.columnNumber.getOrElse(-1),
    i.order,
    i.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_identifier VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=8,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_literals_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export LITERAL nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_literal',
            cpg_type='literal',
            query_template="""
cpg.literal.drop({offset}).take({batch_size}).map {{ l =>
  List(
    l.id,
    l.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    l.typeFullName,
    l.lineNumber.getOrElse(-1),
    l.columnNumber.getOrElse(-1),
    l.order,
    l.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_literal VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_locals_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export LOCAL nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_local',
            cpg_type='local',
            query_template="""
cpg.local.drop({offset}).take({batch_size}).map {{ l =>
  List(
    l.id,
    l.name,
    l.typeFullName,
    l.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    l.lineNumber.getOrElse(-1),
    l.columnNumber.getOrElse(-1),
    l.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_local VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_params_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export PARAM nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_param',
            cpg_type='parameter',
            query_template="""
cpg.parameter.drop({offset}).take({batch_size}).map {{ p =>
  List(
    p.id,
    p.name,
    p.typeFullName,
    p.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    p.lineNumber.getOrElse(-1),
    p.columnNumber.getOrElse(-1),
    p.order,
    p.index,
    p.isVariadic.toString,
    p.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_param VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=10,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                parts[8].lower() == 'true',
                parts[9] if len(parts) > 9 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_returns_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export RETURN nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_return',
            cpg_type='ret',
            query_template="""
cpg.ret.drop({offset}).take({batch_size}).map {{ r =>
  List(
    r.id,
    r.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    r.lineNumber.getOrElse(-1),
    r.columnNumber.getOrElse(-1),
    r.order,
    r.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_return VALUES (?, ?, ?, ?, ?, ?)",
            field_count=6,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                int(parts[2]) if parts[2].lstrip('-').isdigit() else None,
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_blocks_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export BLOCK nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_block',
            cpg_type='block',
            query_template="""
cpg.block.drop({offset}).take({batch_size}).map {{ b =>
  List(
    b.id,
    b.typeFullName,
    b.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    b.lineNumber.getOrElse(-1),
    b.columnNumber.getOrElse(-1),
    b.order,
    b.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_block VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_control_structures_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CONTROL_STRUCTURE nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_control_structure',
            cpg_type='controlStructure',
            query_template="""
cpg.controlStructure.drop({offset}).take({batch_size}).map {{ c =>
  List(
    c.id,
    c.controlStructureType,
    c.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.order,
    c.parserTypeName
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_control_structure VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                parts[6] if len(parts) > 6 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_type_decls_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TYPE_DECL nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_type_decl',
            cpg_type='typeDecl',
            query_template="""
cpg.typeDecl.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.fullName,
    t.isExternal.toString,
    "",
    t.aliasTypeFullName.getOrElse(""),
    t.filename,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.astParentType,
    t.astParentFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_type_decl VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=10,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3].lower() == 'true',
                None,  # inherits_from_type_full_name (complex array, skip for now)
                parts[5] if parts[5] else None,
                parts[6],
                parts[7],
                parts[8],
                parts[9] if len(parts) > 9 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P0 Node Export Methods - Critical for code structure
    # =========================================================================

    def _export_files_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export FILE nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_file',
            cpg_type='file',
            query_template="""
cpg.file.drop({offset}).take({batch_size}).map {{ f =>
  List(
    f.id,
    f.name,
    f.hash,
    "",
    f.lineNumber.getOrElse(-1),
    f.columnNumber.getOrElse(-1),
    f.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_file VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2] if parts[2] else None,
                parts[3] if parts[3] else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_namespaces_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export NAMESPACE nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_namespace',
            cpg_type='namespace',
            query_template="""
cpg.namespace.drop({offset}).take({batch_size}).map {{ n =>
  List(
    n.id,
    n.name,
    n.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    n.lineNumber.getOrElse(-1),
    n.columnNumber.getOrElse(-1),
    n.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_namespace VALUES (?, ?, ?, ?, ?, ?)",
            field_count=6,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_namespace_blocks_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export NAMESPACE_BLOCK nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_namespace_block',
            cpg_type='namespaceBlock',
            query_template="""
cpg.namespaceBlock.drop({offset}).take({batch_size}).map {{ n =>
  List(
    n.id,
    n.name,
    n.fullName,
    n.filename,
    n.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    n.lineNumber.getOrElse(-1),
    n.columnNumber.getOrElse(-1),
    n.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_namespace_block VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=8,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                parts[4],
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_members_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export MEMBER nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_member',
            cpg_type='member',
            query_template="""
cpg.member.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.name,
    m.typeFullName,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_member VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_types_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TYPE nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_type',
            cpg_type='typ',
            query_template="""
cpg.typ.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.fullName,
    t.typeDeclFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_type VALUES (?, ?, ?, ?)",
            field_count=4,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3] if len(parts) > 3 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P1 Node Export Methods - Important for analysis
    # =========================================================================

    def _export_method_parameter_out_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export METHOD_PARAMETER_OUT nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_method_parameter_out',
            cpg_type='methodParameterOut',
            query_template="""
cpg.methodParameterOut.drop({offset}).take({batch_size}).map {{ p =>
  List(
    p.id,
    p.name,
    p.typeFullName,
    p.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    p.lineNumber.getOrElse(-1),
    p.columnNumber.getOrElse(-1),
    p.order,
    p.index,
    p.isVariadic.toString,
    p.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_method_parameter_out VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=10,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                parts[8].lower() == 'true',
                parts[9] if len(parts) > 9 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_method_return_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export METHOD_RETURN nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_method_return',
            cpg_type='methodReturn',
            query_template="""
cpg.methodReturn.drop({offset}).take({batch_size}).map {{ r =>
  List(
    r.id,
    r.typeFullName,
    r.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    r.lineNumber.getOrElse(-1),
    r.columnNumber.getOrElse(-1),
    r.order,
    r.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_method_return VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                parts[6] if len(parts) > 6 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_field_identifiers_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export FIELD_IDENTIFIER nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_field_identifier',
            cpg_type='fieldAccess',
            query_template="""
cpg.fieldAccess.drop({offset}).take({batch_size}).map {{ f =>
  List(
    f.id,
    f.canonicalName,
    f.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    f.lineNumber.getOrElse(-1),
    f.columnNumber.getOrElse(-1),
    f.order,
    f.argumentIndex,
    f.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_field_identifier VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=8,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                parts[7] if len(parts) > 7 and parts[7] else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_type_arguments_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TYPE_ARGUMENT nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_type_argument',
            cpg_type='typeArgument',
            query_template="""
cpg.typeArgument.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_type_argument VALUES (?, ?, ?, ?, ?)",
            field_count=5,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                int(parts[2]) if parts[2].lstrip('-').isdigit() else None,
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_type_parameters_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TYPE_PARAMETER nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_type_parameter',
            cpg_type='typeParameter',
            query_template="""
cpg.typeParameter.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_type_parameter VALUES (?, ?, ?, ?, ?, ?)",
            field_count=6,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P2 Node Export Methods - Supplementary
    # =========================================================================

    def _export_jump_labels_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export JUMP_LABEL nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_jump_label',
            cpg_type='jumpLabel',
            query_template="""
cpg.jumpLabel.drop({offset}).take({batch_size}).map {{ j =>
  List(
    j.id,
    j.name,
    j.parserTypeName,
    j.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    j.lineNumber.getOrElse(-1),
    j.columnNumber.getOrElse(-1),
    j.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_jump_label VALUES (?, ?, ?, ?, ?, ?, ?)",
            field_count=7,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_jump_targets_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export JUMP_TARGET nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_jump_target',
            cpg_type='jumpTarget',
            query_template="""
cpg.jumpTarget.drop({offset}).take({batch_size}).map {{ j =>
  List(
    j.id,
    j.name,
    j.parserTypeName,
    j.argumentIndex,
    j.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    j.lineNumber.getOrElse(-1),
    j.columnNumber.getOrElse(-1),
    j.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_jump_target VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=8,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                parts[4],
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_method_refs_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export METHOD_REF nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_method_ref',
            cpg_type='methodRef',
            query_template="""
cpg.methodRef.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.methodFullName,
    m.typeFullName,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order,
    m.argumentIndex,
    m.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_method_ref VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=9,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                parts[8] if len(parts) > 8 and parts[8] else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_modifiers_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export MODIFIER nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_modifier',
            cpg_type='modifier',
            query_template="""
cpg.modifier.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.modifierType,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_modifier VALUES (?, ?, ?, ?, ?, ?)",
            field_count=6,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_type_refs_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TYPE_REF nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_type_ref',
            cpg_type='typeRef',
            query_template="""
cpg.typeRef.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.typeFullName,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order,
    t.argumentIndex,
    t.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_type_ref VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=8,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                int(parts[3]) if parts[3].lstrip('-').isdigit() else None,
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                parts[7] if len(parts) > 7 and parts[7] else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_unknowns_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export UNKNOWN nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_unknown',
            cpg_type='unknown',
            query_template="""
cpg.unknown.drop({offset}).take({batch_size}).map {{ u =>
  List(
    u.id,
    u.containedRef,
    u.parserTypeName,
    u.typeFullName,
    u.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    u.lineNumber.getOrElse(-1),
    u.columnNumber.getOrElse(-1),
    u.order,
    u.argumentIndex,
    u.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_unknown VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=10,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1] if parts[1] else None,
                parts[2] if parts[2] else None,
                parts[3] if parts[3] else None,
                parts[4],
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                int(parts[8]) if parts[8].lstrip('-').isdigit() else None,
                parts[9] if len(parts) > 9 and parts[9] else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P3 Node Export Methods - Low priority
    # =========================================================================

    def _export_bindings_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export BINDING nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_binding',
            cpg_type='binding',
            query_template="""
cpg.binding.drop({offset}).take({batch_size}).map {{ b =>
  List(
    b.id,
    b.name,
    b.signature,
    b.methodFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_binding VALUES (?, ?, ?, ?)",
            field_count=4,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3] if len(parts) > 3 else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_annotations_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export ANNOTATION nodes from Joern to DuckDB in batches"""
        return self._export_simple_nodes(
            entity_type='nodes_annotation',
            cpg_type='annotation',
            query_template="""
cpg.annotation.drop({offset}).take({batch_size}).map {{ a =>
  List(
    a.id,
    a.name,
    a.fullName,
    a.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    a.lineNumber.getOrElse(-1),
    a.columnNumber.getOrElse(-1),
    a.order,
    a.argumentIndex,
    a.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO nodes_annotation VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            field_count=9,
            parse_fn=lambda parts: (
                int(parts[0]),
                parts[1],
                parts[2],
                parts[3],
                int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                parts[8] if len(parts) > 8 and parts[8] else None,
            ),
            limit=limit,
            start_offset=start_offset
        )

    def _export_simple_nodes(self, entity_type: str, cpg_type: str, query_template: str,
                              insert_sql: str, field_count: int, parse_fn,
                              limit: Optional[int] = None, start_offset: int = 0):
        """Generic method to export simple node types in batches

        Args:
            entity_type: Table name (e.g., 'nodes_identifier')
            cpg_type: CPG type name (e.g., 'identifier')
            query_template: Scala query template with {offset} and {batch_size} placeholders
            insert_sql: SQL INSERT statement
            field_count: Expected number of fields in parsed row
            parse_fn: Function to parse row parts into tuple
            limit: Optional limit on number of nodes to export
            start_offset: Offset to start from (for resume)
        """
        import re
        logger.info(f"Exporting {entity_type} (batch size: {self.batch_size}, start_offset: {start_offset})...")

        # Get total count
        count_query = f"cpg.{cpg_type}.size"
        count_result = self.joern_client.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.warning(f"Failed to get {cpg_type} count - may not exist in this CPG")
            return 0

        count_str = count_result.get('result', '0')
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_count = int(count_match.group(1)) if count_match else 0

        if total_count == 0:
            logger.info(f"No {cpg_type} nodes found in CPG")
            return 0

        if limit:
            total_count = min(total_count, limit)

        logger.info(f"Total {cpg_type} to export: {total_count}")

        offset = start_offset
        total_exported = self._get_existing_count(entity_type) if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_exported})")

        while offset < total_count:
            current_batch_size = min(self.batch_size, total_count - offset)
            query = query_template.format(offset=offset, batch_size=current_batch_size)

            logger.info(f"Fetching {cpg_type} {offset} to {offset + current_batch_size}...")
            query_result = self.joern_client.execute_query(query)

            if not query_result or not query_result.get('success'):
                logger.error(f"Failed to fetch {cpg_type} batch")
                break

            result = query_result.get('result', '')
            if not result or result.strip() == "":
                logger.info(f"No more {cpg_type} to export")
                break

            rows_to_insert = []
            for line in result.strip().split('\n'):
                if not line.strip():
                    continue
                if 'val' in line and 'res' in line and '=' in line:
                    continue

                parts = line.split('\t')
                if len(parts) < field_count:
                    continue

                try:
                    row = parse_fn(parts)
                    rows_to_insert.append(row)
                except Exception as e:
                    logger.warning(f"Error parsing {cpg_type} row: {e}")
                    continue

            if rows_to_insert:
                self.conn.executemany(insert_sql, rows_to_insert)
                total_exported += len(rows_to_insert)
                logger.info(f"Inserted {len(rows_to_insert)} {cpg_type} (total: {total_exported}/{total_count})")

                self._update_export_progress(entity_type, total_count, total_exported,
                                             offset + current_batch_size, 'in_progress')

            offset += current_batch_size

        logger.info(f"{entity_type} export complete. Total exported: {total_exported}")
        return total_exported

    # =========================================================================
    # Edge Export Methods
    # =========================================================================

    def _export_ast_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export AST edges from Joern to DuckDB in batches

        AST edges are the most numerous - we export them by iterating through all nodes.
        """
        return self._export_edges_via_nodes(
            entity_type='edges_ast',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.astChildren.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_ast VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_cfg_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CFG edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_cfg',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.cfgNext.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_cfg VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_ref_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export REF edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_ref',
            edge_query_template="""
cpg.identifier.drop({offset}).take({batch_size}).flatMap {{ i =>
  i.refOut.map(r => s"${{i.id}}\\t${{r.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_ref VALUES (?, ?)",
            count_query="cpg.identifier.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_argument_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export ARGUMENT edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_argument',
            edge_query_template="""
cpg.call.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.argument.map(a => s"${{c.id}}\\t${{a.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_argument VALUES (?, ?)",
            count_query="cpg.call.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_receiver_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export RECEIVER edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_receiver',
            edge_query_template="""
cpg.call.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.receiver.map(r => s"${{c.id}}\\t${{r.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_receiver VALUES (?, ?)",
            count_query="cpg.call.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_condition_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CONDITION edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_condition',
            edge_query_template="""
cpg.controlStructure.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.condition.map(cond => s"${{c.id}}\\t${{cond.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_condition VALUES (?, ?)",
            count_query="cpg.controlStructure.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_dominate_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export DOMINATE edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_dominate',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.dominates.map(d => s"${{n.id}}\\t${{d.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_dominate VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_post_dominate_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export POST_DOMINATE edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_post_dominate',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.postDominates.map(d => s"${{n.id}}\\t${{d.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_post_dominate VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_edges_via_nodes(self, entity_type: str, edge_query_template: str,
                                 insert_sql: str, count_query: str = "cpg.all.size",
                                 limit: Optional[int] = None, start_offset: int = 0):
        """Generic method to export edges by iterating through nodes

        Args:
            entity_type: Table name (e.g., 'edges_ast')
            edge_query_template: Scala query template with {offset} and {batch_size} placeholders
            insert_sql: SQL INSERT statement
            count_query: Query to get total node count
            limit: Optional limit
            start_offset: Offset to start from (for resume)
        """
        import re
        logger.info(f"Exporting {entity_type} (batch size: {self.batch_size}, start_offset: {start_offset})...")

        # Get total count
        count_result = self.joern_client.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.warning(f"Failed to get node count for {entity_type}")
            return 0

        count_str = count_result.get('result', '0')
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_nodes = int(count_match.group(1)) if count_match else 0

        if total_nodes == 0:
            logger.info(f"No nodes found for {entity_type}")
            return 0

        if limit:
            total_nodes = min(total_nodes, limit)

        logger.info(f"Iterating through {total_nodes} nodes for {entity_type}")

        offset = start_offset
        total_exported = self._get_existing_count(entity_type) if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_exported})")

        while offset < total_nodes:
            current_batch_size = min(self.batch_size, total_nodes - offset)
            query = edge_query_template.format(offset=offset, batch_size=current_batch_size)

            logger.info(f"Fetching {entity_type} for nodes {offset} to {offset + current_batch_size}...")
            query_result = self.joern_client.execute_query(query)

            if not query_result or not query_result.get('success'):
                logger.error(f"Failed to fetch {entity_type} batch")
                break

            result = query_result.get('result', '')

            edges_to_insert = []
            if result and result.strip():
                for line in result.strip().split('\n'):
                    if not line.strip():
                        continue
                    if 'val' in line and 'res' in line and '=' in line:
                        continue

                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            edges_to_insert.append((int(parts[0]), int(parts[1])))
                        except:
                            continue

            if edges_to_insert:
                self.conn.executemany(insert_sql, edges_to_insert)
                total_exported += len(edges_to_insert)
                logger.info(f"Inserted {len(edges_to_insert)} {entity_type} (total: {total_exported})")

            # Update progress after each batch
            self._update_export_progress(entity_type, total_nodes, total_exported,
                                         offset + current_batch_size, 'in_progress')

            offset += current_batch_size

        logger.info(f"{entity_type} export complete. Total exported: {total_exported}")
        return total_exported

    def _export_comments_batched(self, limit: Optional[int] = None):
        """Export COMMENT nodes from Joern CPG to DuckDB in batches"""
        logger.info(f"Exporting COMMENT nodes (batch size: {self.batch_size})...")

        # Get total count
        count_query = "cpg.comment.size"
        count_result = self.joern_client.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.warning("Failed to get comment count - comments may not be available in this CPG")
            return 0

        # Parse count from result
        import re
        count_str = count_result.get('result', '0')
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_comments = int(count_match.group(1)) if count_match else 0

        if total_comments == 0:
            logger.info("No comments found in CPG")
            return 0

        if limit:
            total_comments = min(total_comments, limit)

        logger.info(f"Total comments to export: {total_comments}")

        offset = 0
        total_exported = 0

        while offset < total_comments:
            current_batch_size = min(self.batch_size, total_comments - offset)

            # Build batched query for COMMENT nodes
            query = f"""
cpg.comment.drop({offset}).take({current_batch_size}).map {{ c =>
  List(
    c.id,
    c.code,
    c.filename.getOrElse("unknown"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.offset.getOrElse(-1),
    c.offsetEnd.getOrElse(-1),
    c.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            logger.info(f"Fetching comments {offset} to {offset + current_batch_size}...")
            query_result = self.joern_client.execute_query(query)

            if not query_result or not query_result.get('success'):
                logger.error("Failed to fetch comments batch")
                break

            result = query_result.get('result', '')
            if not result or result.strip() == "":
                logger.info("No more comments to export")
                break

            # Parse results and insert COMMENT nodes
            comment_rows = []

            for line in result.strip().split('\n'):
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) < 8:
                    continue

                try:
                    row = (
                        int(parts[0]),   # id
                        parts[1],        # code (comment text)
                        parts[2],        # filename
                        int(parts[3]) if parts[3].lstrip('-').isdigit() else None,  # line_number
                        int(parts[4]) if parts[4].lstrip('-').isdigit() else None,  # column_number
                        int(parts[5]) if parts[5].lstrip('-').isdigit() else None,  # offset
                        int(parts[6]) if parts[6].lstrip('-').isdigit() else None,  # offset_end
                        int(parts[7]) if parts[7].lstrip('-').isdigit() else None   # order_index
                    )
                    comment_rows.append(row)
                except Exception as e:
                    logger.warning(f"Error parsing comment row: {e}")
                    continue

            # Bulk insert COMMENT nodes
            if comment_rows:
                self.conn.executemany("""
                    INSERT INTO nodes_comment VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, comment_rows)
                total_exported += len(comment_rows)
                logger.info(f"Inserted {len(comment_rows)} comments (total: {total_exported}/{total_comments})")

            offset += current_batch_size

        logger.info(f"Comment export complete. Total exported: {total_exported}")
        return total_exported

    def _export_comment_edges_batched(self, limit: Optional[int] = None):
        """Export edges connecting COMMENT nodes to their AST parent (METHOD or FILE)"""
        logger.info("Exporting comment-to-code edges...")

        # Get total comment count
        count_result = self.conn.execute("SELECT COUNT(*) FROM nodes_comment").fetchone()
        total_comments = count_result[0] if count_result else 0

        if total_comments == 0:
            logger.info("No comments to link - skipping edge export")
            return 0

        if limit:
            total_comments = min(total_comments, limit)

        logger.info(f"Creating edges for {total_comments} comments...")

        offset = 0
        total_edges = 0
        batch_size = min(self.batch_size, 5000)  # Smaller batches for edge queries

        while offset < total_comments:
            current_batch_size = min(batch_size, total_comments - offset)

            # Get comment IDs for this batch
            comment_ids = self.conn.execute(f"""
                SELECT id FROM nodes_comment
                ORDER BY id
                LIMIT {current_batch_size} OFFSET {offset}
            """).fetchall()

            if not comment_ids:
                break

            comment_ids_str = ", ".join(str(c[0]) for c in comment_ids)

            # Query Joern for AST parent relationships
            query = f"""
val commentIds = Set({comment_ids_str}L)
cpg.comment.filter(c => commentIds.contains(c.id)).map {{ c =>
  val parentId = c.astParent.id
  s"${{c.id}}\\t${{parentId}}"
}}.l.mkString("\\n")
"""

            query_result = self.joern_client.execute_query(query)

            if query_result and query_result.get('success'):
                result = query_result.get('result', '')
                if result and result.strip():
                    edge_rows = []
                    for line in result.strip().split('\n'):
                        if not line.strip():
                            continue
                        parts = line.split('\t')
                        if len(parts) == 2:
                            try:
                                src_id = int(parts[0])
                                dst_id = int(parts[1])
                                edge_rows.append((src_id, dst_id))
                            except:
                                continue

                    if edge_rows:
                        self.conn.executemany("""
                            INSERT OR IGNORE INTO edges_source_file VALUES (?, ?)
                        """, edge_rows)
                        total_edges += len(edge_rows)
                        logger.info(f"Inserted {len(edge_rows)} comment edges (total: {total_edges})")

            offset += current_batch_size

        logger.info(f"Comment edge export complete. Total edges: {total_edges}")
        return total_edges

    # =========================================================================
    # P0 Edge Export Methods - Critical for analysis
    # =========================================================================

    def _export_cdg_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CDG (Control Dependence Graph) edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_cdg',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.cdgNext.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_cdg VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_contains_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export CONTAINS edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_contains',
            edge_query_template="""
cpg.file.drop({offset}).take({batch_size}).flatMap {{ f =>
  f.method.map(m => s"${{f.id}}\\t${{m.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_contains VALUES (?, ?)",
            count_query="cpg.file.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_eval_type_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export EVAL_TYPE edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_eval_type',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.evalType.map(t => s"${{n.id}}\\t${{t.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_eval_type VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P1 Edge Export Methods - Important for OOP analysis
    # =========================================================================

    def _export_inherits_from_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export INHERITS_FROM edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_inherits_from',
            edge_query_template="""
cpg.typeDecl.drop({offset}).take({batch_size}).flatMap {{ t =>
  t.inheritsFromTypeFullName.flatMap {{ inheritName =>
    cpg.typ.fullNameExact(inheritName).headOption.map(parent => s"${{t.id}}\\t${{parent.id}}")
  }}
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_inherits_from VALUES (?, ?)",
            count_query="cpg.typeDecl.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_alias_of_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export ALIAS_OF edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_alias_of',
            edge_query_template="""
cpg.typ.drop({offset}).take({batch_size}).flatMap {{ t =>
  cpg.typeDecl.fullNameExact(t.typeDeclFullName).headOption.map(td => s"${{t.id}}\\t${{td.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_alias_of VALUES (?, ?)",
            count_query="cpg.typ.size",
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P2 Edge Export Methods - Supplementary
    # =========================================================================

    def _export_binds_to_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export BINDS_TO edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_binds_to',
            edge_query_template="""
cpg.typeArgument.drop({offset}).take({batch_size}).flatMap {{ ta =>
  ta.bindsTo.map(tp => s"${{ta.id}}\\t${{tp.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_binds_to VALUES (?, ?)",
            count_query="cpg.typeArgument.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_parameter_link_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export PARAMETER_LINK edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_parameter_link',
            edge_query_template="""
cpg.parameter.drop({offset}).take({batch_size}).flatMap {{ p =>
  p.asOutput.map(out => s"${{p.id}}\\t${{out.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_parameter_link VALUES (?, ?)",
            count_query="cpg.parameter.size",
            limit=limit,
            start_offset=start_offset
        )

    # =========================================================================
    # P3 Edge Export Methods - Low priority
    # =========================================================================

    def _export_tagged_by_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export TAGGED_BY edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_tagged_by',
            edge_query_template="""
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.tag.map(t => s"${{n.id}}\\t${{t.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_tagged_by VALUES (?, ?)",
            limit=limit,
            start_offset=start_offset
        )

    def _export_binds_edges_batched(self, limit: Optional[int] = None, start_offset: int = 0):
        """Export BINDS edges from Joern to DuckDB in batches"""
        return self._export_edges_via_nodes(
            entity_type='edges_binds',
            edge_query_template="""
cpg.typeDecl.drop({offset}).take({batch_size}).flatMap {{ t =>
  t.bindsOut.map(b => s"${{t.id}}\\t${{b.id}}")
}}.l.mkString("\\n")
""",
            insert_sql="INSERT OR IGNORE INTO edges_binds VALUES (?, ?)",
            count_query="cpg.typeDecl.size",
            limit=limit,
            start_offset=start_offset
        )

    def _export_includes(self, limit: Optional[int] = None) -> int:
        """
        Export #include directives as edges_include for file-level dependencies
        (Sprint 3 - Scenario 11 Enhancement)

        This extracts include relationships from the CPG to support module dependency queries.

        Args:
            limit: Optional limit on number of includes to export

        Returns:
            Number of include edges exported
        """
        logger.info("Exporting #include directives...")

        # Create edges_include table if not exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_include (
                id BIGINT PRIMARY KEY,
                src BIGINT,
                dst BIGINT,
                include_path VARCHAR NOT NULL,
                resolved_path VARCHAR,
                is_system BOOLEAN DEFAULT FALSE,
                line_number INTEGER,
                src_filename VARCHAR,
                dst_filename VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_include_src ON edges_include(src)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_include_dst ON edges_include(dst)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_include_path ON edges_include(include_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_include_src_filename ON edges_include(src_filename)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_include_dst_filename ON edges_include(dst_filename)")

        # Query Joern for #include directives
        # In C/C++ code, #include is typically represented as a special AST node
        include_query = """
            cpg.file.l.flatMap { file =>
              // Find include calls in file AST
              file.ast.isCall.name(".*include.*").l.map { inc =>
                Map(
                  "src_file_id" -> file.id,
                  "src_filename" -> file.name,
                  "include_path" -> (if (inc.argument.size > 0) inc.argument.head.code else inc.code),
                  "is_system" -> inc.code.startsWith("<"),
                  "line_number" -> inc.lineNumber.getOrElse(-1)
                )
              }
            }.take(""" + str(limit or 10000) + """)
        """

        try:
            # Execute query
            result = self.joern_client.query(include_query)
            includes = parse_scala_output(result) if result else []

            if not includes:
                logger.warning("No #include directives found in CPG. Attempting fallback extraction...")
                # Fallback: extract from file nodes directly (preprocessor directives)
                fallback_query = """
                    cpg.preproc.l.filter(_.code.contains("#include")).map { p =>
                      Map(
                        "src_filename" -> p.file.name.getOrElse("unknown"),
                        "include_path" -> p.code.replace("#include", "").trim,
                        "is_system" -> p.code.contains("<"),
                        "line_number" -> p.lineNumber.getOrElse(-1)
                      )
                    }.take(""" + str(limit or 10000) + """)
                """
                result = self.joern_client.query(fallback_query)
                includes = parse_scala_output(result) if result else []

            if not includes:
                logger.warning("No includes found via Joern. Includes extraction may require special Joern configuration.")
                return 0

            # Insert into DuckDB
            total = 0
            for idx, inc in enumerate(includes):
                try:
                    include_path = inc.get('include_path', '').strip('"<>')
                    is_system = inc.get('is_system', False)
                    src_filename = inc.get('src_filename', 'unknown')

                    # Try to resolve destination filename
                    dst_filename = include_path.split('/')[-1] if '/' in include_path else include_path

                    self.conn.execute("""
                        INSERT INTO edges_include
                        (id, src, dst, include_path, is_system, line_number, src_filename, dst_filename)
                        VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                        ON CONFLICT DO NOTHING
                    """, (
                        idx + 1,
                        inc.get('src_file_id', 0),
                        include_path,
                        is_system if isinstance(is_system, bool) else str(is_system).lower() == 'true',
                        inc.get('line_number', -1),
                        src_filename,
                        dst_filename
                    ))
                    total += 1
                except Exception as e:
                    logger.debug(f"Error inserting include: {e}")
                    continue

            logger.info(f"Exported {total} #include directives")
            return total

        except Exception as e:
            logger.error(f"Include extraction failed: {e}")
            logger.info("Continuing without include edges...")
            return 0

    def export_full_cpg(self, limit: Optional[int] = None, resume: bool = True,
                         force_recreate: bool = False):
        """
        Export full CPG from Joern to DuckDB with checkpoint/resume support

        Args:
            limit: Optional limit on number of nodes to export per type
            resume: If True, resume from last successful batch (default: True)
            force_recreate: If True, drop all tables and start fresh (default: False)
        """
        logger.info("=" * 80)
        logger.info("Starting full CPG export...")
        logger.info(f"  Resume mode: {resume}")
        logger.info(f"  Force recreate: {force_recreate}")
        logger.info("=" * 80)

        # Create progress table first
        self._create_progress_table()

        # Initialize schema (preserves data if resume=True and force_recreate=False)
        self._initialize_schema(force_recreate=force_recreate)

        # Define export order: nodes first, then edges
        # Organized by priority (P0 = critical, P1 = important, P2 = supplementary, P3 = low priority)
        node_exports = [
            # Existing nodes
            ('nodes_method', self._export_methods_batched),
            ('nodes_call', lambda l, o: self._export_calls_batched(l, o)[0]),  # Returns tuple
            ('nodes_identifier', self._export_identifiers_batched),
            ('nodes_literal', self._export_literals_batched),
            ('nodes_local', self._export_locals_batched),
            ('nodes_param', self._export_params_batched),
            ('nodes_return', self._export_returns_batched),
            ('nodes_block', self._export_blocks_batched),
            ('nodes_control_structure', self._export_control_structures_batched),
            ('nodes_type_decl', self._export_type_decls_batched),
            ('nodes_comment', self._export_comments_batched),
            # P0 Nodes - Critical for code structure
            ('nodes_file', self._export_files_batched),
            ('nodes_namespace', self._export_namespaces_batched),
            ('nodes_namespace_block', self._export_namespace_blocks_batched),
            ('nodes_member', self._export_members_batched),
            ('nodes_type', self._export_types_batched),
            # P1 Nodes - Important for analysis
            ('nodes_method_parameter_out', self._export_method_parameter_out_batched),
            ('nodes_method_return', self._export_method_return_batched),
            ('nodes_field_identifier', self._export_field_identifiers_batched),
            ('nodes_type_argument', self._export_type_arguments_batched),
            ('nodes_type_parameter', self._export_type_parameters_batched),
            # P2 Nodes - Supplementary
            ('nodes_jump_label', self._export_jump_labels_batched),
            ('nodes_jump_target', self._export_jump_targets_batched),
            ('nodes_method_ref', self._export_method_refs_batched),
            ('nodes_modifier', self._export_modifiers_batched),
            ('nodes_type_ref', self._export_type_refs_batched),
            ('nodes_unknown', self._export_unknowns_batched),
            # P3 Nodes - Low priority
            ('nodes_binding', self._export_bindings_batched),
            ('nodes_annotation', self._export_annotations_batched),
        ]

        edge_exports = [
            # Existing edges
            ('edges_ast', self._export_ast_edges_batched),
            ('edges_cfg', self._export_cfg_edges_batched),
            ('edges_ref', self._export_ref_edges_batched),
            ('edges_argument', self._export_argument_edges_batched),
            ('edges_receiver', self._export_receiver_edges_batched),
            ('edges_condition', self._export_condition_edges_batched),
            ('edges_dominate', self._export_dominate_edges_batched),
            ('edges_post_dominate', self._export_post_dominate_edges_batched),
            # P0 Edges - Critical for analysis
            ('edges_cdg', self._export_cdg_edges_batched),
            ('edges_contains', self._export_contains_edges_batched),
            ('edges_eval_type', self._export_eval_type_edges_batched),
            # P1 Edges - Important for OOP analysis
            ('edges_inherits_from', self._export_inherits_from_edges_batched),
            ('edges_alias_of', self._export_alias_of_edges_batched),
            # P2 Edges - Supplementary
            ('edges_binds_to', self._export_binds_to_edges_batched),
            ('edges_parameter_link', self._export_parameter_link_edges_batched),
            # P3 Edges - Low priority
            ('edges_tagged_by', self._export_tagged_by_edges_batched),
            ('edges_binds', self._export_binds_edges_batched),
        ]

        stats = {}

        # Export nodes
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 1: Exporting Nodes")
        logger.info("=" * 40)

        for entity_type, export_fn in node_exports:
            status, offset = self._get_export_status(entity_type)

            if status == 'completed' and resume:
                count = self._get_existing_count(entity_type)
                logger.info(f"[SKIP] {entity_type} - already completed ({count} records)")
                stats[entity_type] = count
                continue

            logger.info(f"\n[EXPORT] {entity_type}...")
            try:
                start_offset = offset if resume and status == 'in_progress' else 0
                count = export_fn(limit=limit, start_offset=start_offset)
                self._mark_completed(entity_type, count)
                stats[entity_type] = count
            except Exception as e:
                self._mark_failed(entity_type, str(e), offset)
                logger.error(f"[ERROR] {entity_type} failed: {e}")
                stats[entity_type] = 0
                # Continue with next entity instead of stopping

        # Export edges
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 2: Exporting Edges")
        logger.info("=" * 40)

        for entity_type, export_fn in edge_exports:
            status, offset = self._get_export_status(entity_type)

            if status == 'completed' and resume:
                count = self._get_existing_count(entity_type)
                logger.info(f"[SKIP] {entity_type} - already completed ({count} records)")
                stats[entity_type] = count
                continue

            logger.info(f"\n[EXPORT] {entity_type}...")
            try:
                start_offset = offset if resume and status == 'in_progress' else 0
                count = export_fn(limit=limit, start_offset=start_offset)
                self._mark_completed(entity_type, count)
                stats[entity_type] = count
            except Exception as e:
                self._mark_failed(entity_type, str(e), offset)
                logger.error(f"[ERROR] {entity_type} failed: {e}")
                stats[entity_type] = 0

        # Export includes (separate handling)
        logger.info("\n[EXPORT] edges_include...")
        try:
            include_count = self._export_includes(limit=limit)
            stats['edges_include'] = include_count
        except Exception as e:
            logger.error(f"[ERROR] edges_include failed: {e}")
            stats['edges_include'] = 0

        # Create property graph
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 3: Creating Property Graph")
        logger.info("=" * 40)

        try:
            self._create_property_graph()
        except Exception as e:
            logger.error(f"Property graph creation failed: {e}")

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("CPG Export Summary:")
        logger.info("=" * 80)

        total_nodes = 0
        total_edges = 0
        for key, count in stats.items():
            if key.startswith('nodes_'):
                total_nodes += count
            elif key.startswith('edges_'):
                total_edges += count
            logger.info(f"  {key}: {count:,}")

        logger.info("-" * 40)
        logger.info(f"  Total nodes: {total_nodes:,}")
        logger.info(f"  Total edges: {total_edges:,}")
        logger.info("=" * 80)

        return stats


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export Joern CPG to DuckDB with checkpoint/resume support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First run - export all data
  python joern_to_duckdb_v2.py --db cpg.duckdb

  # Resume interrupted export
  python joern_to_duckdb_v2.py --db cpg.duckdb --resume

  # Force complete re-export
  python joern_to_duckdb_v2.py --db cpg.duckdb --force-recreate

  # Export with smaller batch size (for debugging)
  python joern_to_duckdb_v2.py --db cpg.duckdb --batch-size 1000
"""
    )
    parser.add_argument('--endpoint', type=str, default='localhost:8080',
                        help='Joern server endpoint (host:port)')
    parser.add_argument('--workspace', type=str, default='pg17_full.cpg',
                        help='Name of the workspace/CPG to open')
    parser.add_argument('--db', type=str, default='cpg.duckdb',
                        help='Path to DuckDB database file')
    parser.add_argument('--batch-size', type=int, default=10000,
                        help='Batch size for exports (default: 10000)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of nodes per type (for testing)')

    # Resume/recreate options
    parser.add_argument('--resume', action='store_true', default=True,
                        help='Resume from last checkpoint (default: True)')
    parser.add_argument('--no-resume', dest='resume', action='store_false',
                        help='Start from beginning without resume')
    parser.add_argument('--force-recreate', action='store_true', default=False,
                        help='Drop all tables and start fresh')

    args = parser.parse_args()

    # Validate args
    if args.force_recreate and args.resume:
        logger.warning("--force-recreate overrides --resume, all data will be dropped")
        args.resume = False

    # Create exporter
    exporter = JoernToDuckDB(
        server_endpoint=args.endpoint,
        workspace=args.workspace,
        db_path=args.db,
        batch_size=args.batch_size
    )

    try:
        # Connect to Joern server
        if not exporter.joern_client.connect():
            logger.error("Failed to connect to Joern server")
            sys.exit(1)

        # Connect to database
        exporter.connect_db()

        # Export full CPG with resume support
        stats = exporter.export_full_cpg(
            limit=args.limit,
            resume=args.resume,
            force_recreate=args.force_recreate
        )

        logger.info("\nExport completed successfully!")
        logger.info(f"Database file: {args.db}")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        exporter.close_db()


if __name__ == "__main__":
    main()
