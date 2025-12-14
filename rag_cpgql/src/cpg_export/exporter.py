"""Main CPG Exporter orchestrating all components.

This module provides the main JoernToDuckDBExporter class that coordinates
schema initialization, node export, edge export, property graph creation,
and validation.
"""
import logging
import duckdb
from typing import Dict, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.execution.joern_client import JoernClient
from src.cpg_export.schema import initialize_schema
from src.cpg_export.progress import ProgressTracker
from src.cpg_export.validation import ExportValidator, validate_export
from src.cpg_export import nodes
from src.cpg_export import edges

logger = logging.getLogger(__name__)


class JoernToDuckDBExporter:
    """Export Joern CPG to DuckDB with CPG Spec v1.1 schema.

    This is the main entry point for CPG export. It coordinates:
    1. Schema initialization
    2. Node export (all CPG node types)
    3. Edge export (all CPG edge types)
    4. Property graph creation
    5. Export validation

    Example usage:
        exporter = JoernToDuckDBExporter(
            server_endpoint="localhost:8080",
            workspace="myproject.cpg",
            db_path="cpg.duckdb"
        )
        exporter.export_full_cpg()
    """

    def __init__(
        self,
        server_endpoint: str = "localhost:8080",
        workspace: str = "pg17_full.cpg",
        db_path: str = "cpg.duckdb",
        batch_size: int = 10000
    ):
        """
        Initialize Joern to DuckDB exporter.

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
        self.progress_tracker = None

    def connect_db(self):
        """Connect to DuckDB and load duckpgq extension."""
        logger.info(f"Connecting to DuckDB: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)

        # Load duckpgq extension for property graph queries
        try:
            self.conn.execute("INSTALL duckpgq;")
            self.conn.execute("LOAD duckpgq;")
            logger.info("DuckPGQ extension loaded successfully")
        except Exception as e:
            logger.warning(f"DuckPGQ extension error (may already be installed): {e}")

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(self.conn)

    def close_db(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def export_full_cpg(
        self,
        limit: Optional[int] = None,
        resume: bool = True,
        force_recreate: bool = False,
        skip_validation: bool = False
    ) -> Dict:
        """Export full CPG from Joern to DuckDB with validation.

        Args:
            limit: Optional limit on number of nodes/edges per type
            resume: Whether to resume from last checkpoint (default True)
            force_recreate: If True, drop all tables and start fresh
            skip_validation: If True, skip validation at the end

        Returns:
            Dict with export statistics and validation results
        """
        logger.info("=" * 60)
        logger.info("Starting CPG Export (CPG Spec v1.1 Compliant)")
        logger.info("=" * 60)

        if not self.conn:
            self.connect_db()

        # Step 1: Initialize schema
        logger.info("\n[STEP 1/5] Initializing schema...")
        initialize_schema(self.conn, force_recreate)

        # Step 2: Export nodes
        logger.info("\n[STEP 2/5] Exporting nodes...")
        node_stats = self._export_all_nodes(limit, resume)

        # Step 3: Export edges
        logger.info("\n[STEP 3/5] Exporting edges...")
        edge_stats = self._export_all_edges(limit, resume)

        # Step 4: Create property graph
        logger.info("\n[STEP 4/5] Creating property graph...")
        self._create_property_graph()

        # Step 5: Validate export
        validation_results = None
        if not skip_validation:
            logger.info("\n[STEP 5/5] Validating export...")
            validation_results = validate_export(self.joern_client, self.conn)
        else:
            logger.info("\n[STEP 5/5] Skipping validation (skip_validation=True)")

        logger.info("\n" + "=" * 60)
        logger.info("CPG Export Complete!")
        logger.info("=" * 60)

        return {
            'node_stats': node_stats,
            'edge_stats': edge_stats,
            'validation': validation_results
        }

    def _export_all_nodes(self, limit: Optional[int], resume: bool) -> Dict[str, int]:
        """Export all node types.

        Args:
            limit: Optional limit per node type
            resume: Whether to resume from checkpoint

        Returns:
            Dict mapping entity_type to count exported
        """
        stats = {}
        node_exporters = nodes.get_all_exporters(
            self.joern_client, self.conn, self.batch_size
        )

        for exporter in node_exporters:
            entity_type = exporter.entity_type

            # Check if already completed
            if resume and self.progress_tracker.is_completed(entity_type):
                count = self.progress_tracker.get_existing_count(entity_type)
                logger.info(f"[SKIP] {entity_type} already completed ({count} records)")
                stats[entity_type] = count
                continue

            # Get resume offset if applicable
            start_offset = 0
            if resume:
                start_offset = self.progress_tracker.get_resume_offset(entity_type)

            try:
                count = exporter.export(limit=limit, start_offset=start_offset)
                stats[entity_type] = count
                self.progress_tracker.mark_completed(entity_type, count)
            except Exception as e:
                logger.error(f"Error exporting {entity_type}: {e}")
                self.progress_tracker.mark_failed(entity_type, str(e))
                stats[entity_type] = 0

        return stats

    def _export_all_edges(self, limit: Optional[int], resume: bool) -> Dict[str, int]:
        """Export all edge types.

        Args:
            limit: Optional limit per edge type
            resume: Whether to resume from checkpoint

        Returns:
            Dict mapping entity_type to count exported
        """
        stats = {}
        edge_exporters = edges.get_all_exporters(
            self.joern_client, self.conn, self.batch_size
        )

        for exporter in edge_exporters:
            entity_type = exporter.entity_type

            # Check if already completed
            if resume and self.progress_tracker.is_completed(entity_type):
                count = self.progress_tracker.get_existing_count(entity_type)
                logger.info(f"[SKIP] {entity_type} already completed ({count} records)")
                stats[entity_type] = count
                continue

            # Get resume offset if applicable
            start_offset = 0
            if resume:
                start_offset = self.progress_tracker.get_resume_offset(entity_type)

            try:
                count = exporter.export(limit=limit, start_offset=start_offset)
                stats[entity_type] = count
                self.progress_tracker.mark_completed(entity_type, count)
            except Exception as e:
                logger.error(f"Error exporting {entity_type}: {e}")
                self.progress_tracker.mark_failed(entity_type, str(e))
                stats[entity_type] = 0

        return stats

    def _create_property_graph(self):
        """Create DuckDB Property Graph for CPG with full schema support."""
        logger.info("Creating Property Graph...")

        # Drop existing property graph if it exists
        try:
            self.conn.execute("DROP PROPERTY GRAPH IF EXISTS cpg")
        except Exception as e:
            logger.warning(f"Could not drop existing property graph: {e}")

        # Create materialized cpg_nodes table
        logger.info("Creating materialized cpg_nodes table...")
        try:
            self.conn.execute("DROP TABLE IF EXISTS cpg_nodes")
        except:
            pass

        self.conn.execute("""
            CREATE TABLE cpg_nodes AS
            -- Core nodes
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
            -- Structure nodes
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

        node_count = self.conn.execute('SELECT COUNT(*) FROM cpg_nodes').fetchone()[0]
        logger.info(f"Created cpg_nodes with {node_count} nodes")

        # Create property graph
        logger.info("Creating CPG property graph...")
        self.conn.execute("""
            CREATE PROPERTY GRAPH cpg
            VERTEX TABLES (
                -- Core nodes
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
                -- Structure nodes
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
                -- Core edges (polymorphic)
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
                -- Typed edges
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
                edges_source_file
                    SOURCE KEY (src) REFERENCES nodes_comment (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL SOURCE_FILE,
                -- Analysis edges
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
                edges_inherits_from
                    SOURCE KEY (src) REFERENCES nodes_type_decl (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type (id)
                    LABEL INHERITS_FROM,
                edges_alias_of
                    SOURCE KEY (src) REFERENCES nodes_type (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type_decl (id)
                    LABEL ALIAS_OF,
                edges_binds_to
                    SOURCE KEY (src) REFERENCES nodes_type_argument (id)
                    DESTINATION KEY (dst) REFERENCES nodes_type_parameter (id)
                    LABEL BINDS_TO,
                edges_parameter_link
                    SOURCE KEY (src) REFERENCES nodes_param (id)
                    DESTINATION KEY (dst) REFERENCES nodes_method_parameter_out (id)
                    LABEL PARAMETER_LINK,
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

        logger.info("[OK] Property Graph created successfully!")

    def export_nodes_only(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Export only nodes (no edges or property graph).

        Args:
            limit: Optional limit per node type

        Returns:
            Dict mapping entity_type to count exported
        """
        if not self.conn:
            self.connect_db()

        initialize_schema(self.conn, force_recreate=False)
        return self._export_all_nodes(limit, resume=True)

    def export_edges_only(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Export only edges (assumes nodes exist).

        Args:
            limit: Optional limit per edge type

        Returns:
            Dict mapping entity_type to count exported
        """
        if not self.conn:
            self.connect_db()

        return self._export_all_edges(limit, resume=True)

    def validate(self) -> Dict:
        """Run validation and return results.

        Returns:
            Dict of validation results
        """
        if not self.conn:
            self.connect_db()

        return validate_export(self.joern_client, self.conn)

    def print_status(self):
        """Print current export status."""
        if not self.conn:
            self.connect_db()

        if not self.progress_tracker:
            self.progress_tracker = ProgressTracker(self.conn)

        self.progress_tracker.print_status()


def main():
    """CLI entry point for CPG export."""
    import argparse

    parser = argparse.ArgumentParser(description='Export Joern CPG to DuckDB')
    parser.add_argument('--endpoint', default='localhost:8080', help='Joern server endpoint')
    parser.add_argument('--workspace', default='pg17_full.cpg', help='Joern workspace name')
    parser.add_argument('--db', default='cpg.duckdb', help='DuckDB database path')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size')
    parser.add_argument('--limit', type=int, help='Limit per entity type')
    parser.add_argument('--force', action='store_true', help='Force recreate tables')
    parser.add_argument('--no-resume', action='store_true', help='Disable resume')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation')
    parser.add_argument('--status', action='store_true', help='Show export status only')
    parser.add_argument('--validate-only', action='store_true', help='Run validation only')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    exporter = JoernToDuckDBExporter(
        server_endpoint=args.endpoint,
        workspace=args.workspace,
        db_path=args.db,
        batch_size=args.batch_size
    )

    try:
        if args.status:
            exporter.print_status()
        elif args.validate_only:
            exporter.validate()
        else:
            exporter.export_full_cpg(
                limit=args.limit,
                resume=not args.no_resume,
                force_recreate=args.force,
                skip_validation=args.skip_validation
            )
    finally:
        exporter.close_db()


if __name__ == '__main__':
    main()
