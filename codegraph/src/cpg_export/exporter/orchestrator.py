"""CPG Export Orchestrator.

Main class for exporting Joern CPG to DuckDB.
"""
import logging
from typing import Optional
from pathlib import Path
import duckdb

from .progress import ProgressTracker
from .batch_processor import BatchProcessor
from src.execution.joern_client import JoernClient
from src.cpg_export.schema import initialize_schema

logger = logging.getLogger(__name__)


class JoernToDuckDB:
    """
    Export Joern CPG to DuckDB with CPG Spec v1.1 schema.

    Orchestrates the full export process including:
    - Schema initialization
    - Progress tracking for resumable exports
    - Batched node and edge export
    - Property graph creation
    """

    def __init__(
        self,
        server_endpoint: Optional[str] = None,
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
        self.progress: Optional[ProgressTracker] = None
        self.batch_processor: Optional[BatchProcessor] = None

    def connect_db(self):
        """Connect to DuckDB and initialize components."""
        logger.info(f"Connecting to DuckDB: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)

        # Load duckpgq extension
        try:
            self.conn.execute("INSTALL duckpgq;")
            self.conn.execute("LOAD duckpgq;")
            logger.info("DuckPGQ extension loaded successfully")
        except Exception as e:
            logger.warning(f"DuckPGQ extension error: {e}")

        # Initialize components
        self.progress = ProgressTracker(self.conn)
        self.batch_processor = BatchProcessor(
            self.conn,
            self.joern_client,
            self.progress,
            self.batch_size
        )

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
        skip_edges: bool = False,
        skip_dataflow: bool = False
    ) -> dict:
        """
        Export full CPG from Joern to DuckDB.

        Args:
            limit: Optional limit on rows per entity type
            resume: If True, resume from last checkpoint
            force_recreate: If True, drop and recreate all tables
            skip_edges: If True, skip edge export
            skip_dataflow: If True, skip REACHING_DEF edges

        Returns:
            Dict with export statistics
        """
        logger.info("="*80)
        logger.info("FULL CPG EXPORT TO DUCKDB")
        logger.info("="*80)

        # Connect if not already connected
        if not self.conn:
            self.connect_db()

        # Initialize schema
        if force_recreate:
            logger.warning("Force recreate enabled - dropping all tables!")
        initialize_schema(self.conn, force_recreate=force_recreate)
        self.progress.initialize()

        stats = {}

        # Export core nodes
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: CORE NODES")
        logger.info("="*60)

        stats['methods'] = self._export_methods(limit)
        stats['calls'] = self._export_calls(limit)

        # Export additional nodes
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: ADDITIONAL NODES")
        logger.info("="*60)

        stats['identifiers'] = self._export_identifiers(limit)
        stats['literals'] = self._export_literals(limit)
        stats['locals'] = self._export_locals(limit)
        stats['params'] = self._export_params(limit)
        stats['returns'] = self._export_returns(limit)
        stats['blocks'] = self._export_blocks(limit)
        stats['control_structures'] = self._export_control_structures(limit)
        stats['type_decls'] = self._export_type_decls(limit)

        # Export comments
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: COMMENTS")
        logger.info("="*60)

        stats['comments'] = self._export_comments(limit)

        if not skip_edges:
            # Export edges
            logger.info("\n" + "="*60)
            logger.info("PHASE 4: EDGES")
            logger.info("="*60)

            stats['ast_edges'] = self._export_ast_edges(limit)
            stats['cfg_edges'] = self._export_cfg_edges(limit)
            stats['call_edges'] = self.batch_processor.export_call_edges(limit)
            stats['ref_edges'] = self._export_ref_edges(limit)

            if not skip_dataflow:
                stats['reaching_def_edges'] = self.batch_processor.export_reaching_def_edges(limit)
            else:
                logger.info("Skipping REACHING_DEF edges as requested")
                stats['reaching_def_edges'] = 0

        logger.info("\n" + "="*80)
        logger.info("EXPORT COMPLETE")
        logger.info("="*80)

        # Log summary
        total_nodes = sum(
            v for k, v in stats.items()
            if not k.endswith('_edges')
        )
        total_edges = sum(
            v for k, v in stats.items()
            if k.endswith('_edges')
        )

        logger.info(f"Total nodes exported: {total_nodes:,}")
        logger.info(f"Total edges exported: {total_edges:,}")

        return stats

    # === Node Export Methods ===

    def _export_methods(self, limit: Optional[int] = None) -> int:
        """Export METHOD nodes."""
        query_template = """
            cpg.method.drop({offset}).take({batch_size}).map {{ m =>
                (m.id, m.name, m.fullName, m.filename, m.lineNumber.getOrElse(-1),
                 m.lineNumberEnd.getOrElse(-1), m.signature, m.code)
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_method (id, name, full_name, filename, line_number, line_number_end, signature, code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2]) if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None,
                int(row[5]) if row[5] and int(row[5]) > 0 else None,
                str(row[6]) if row[6] else '',
                str(row[7])[:10000] if row[7] else ''
            )

        return self.batch_processor.export_nodes(
            entity_type='methods',
            cpg_type='Method',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=8,
            row_parser=parse_row,
            limit=limit
        )

    def _export_calls(self, limit: Optional[int] = None) -> int:
        """Export CALL nodes."""
        query_template = """
            cpg.call.drop({offset}).take({batch_size}).map {{ c =>
                val containingMethod = c.method.headOption
                (c.id, c.name, c.code, c.filename, c.lineNumber.getOrElse(-1),
                 c.methodFullName, containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_call (id, name, code, filename, line_number, method_full_name, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2])[:5000] if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None,
                str(row[5]) if row[5] else '',
                int(row[6]) if row[6] and int(row[6]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='calls',
            cpg_type='Call',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=7,
            row_parser=parse_row,
            limit=limit
        )

    def _export_identifiers(self, limit: Optional[int] = None) -> int:
        """Export IDENTIFIER nodes."""
        query_template = """
            cpg.identifier.drop({offset}).take({batch_size}).map {{ i =>
                val containingMethod = i.method.headOption
                (i.id, i.name, i.code, i.filename, i.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_identifier (id, name, code, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2])[:2000] if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None,
                int(row[5]) if row[5] and int(row[5]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='identifiers',
            cpg_type='Identifier',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=6,
            row_parser=parse_row,
            limit=limit
        )

    def _export_literals(self, limit: Optional[int] = None) -> int:
        """Export LITERAL nodes."""
        query_template = """
            cpg.literal.drop({offset}).take({batch_size}).map {{ l =>
                val containingMethod = l.method.headOption
                (l.id, l.code, l.typeFullName, l.filename, l.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_literal (id, code, type_full_name, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1])[:2000] if row[1] else '',
                str(row[2]) if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None,
                int(row[5]) if row[5] and int(row[5]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='literals',
            cpg_type='Literal',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=6,
            row_parser=parse_row,
            limit=limit
        )

    def _export_locals(self, limit: Optional[int] = None) -> int:
        """Export LOCAL nodes."""
        query_template = """
            cpg.local.drop({offset}).take({batch_size}).map {{ l =>
                val containingMethod = l.method.headOption
                (l.id, l.name, l.code, l.typeFullName, l.filename, l.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_local (id, name, code, type_full_name, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2])[:2000] if row[2] else '',
                str(row[3]) if row[3] else '',
                str(row[4]) if row[4] else '',
                int(row[5]) if row[5] and int(row[5]) > 0 else None,
                int(row[6]) if row[6] and int(row[6]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='locals',
            cpg_type='Local',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=7,
            row_parser=parse_row,
            limit=limit
        )

    def _export_params(self, limit: Optional[int] = None) -> int:
        """Export PARAM nodes."""
        query_template = """
            cpg.parameter.drop({offset}).take({batch_size}).map {{ p =>
                val containingMethod = p.method.headOption
                (p.id, p.name, p.code, p.typeFullName, p.index, p.filename, p.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_param (id, name, code, type_full_name, index, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2])[:2000] if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] else 0,
                str(row[5]) if row[5] else '',
                int(row[6]) if row[6] and int(row[6]) > 0 else None,
                int(row[7]) if row[7] and int(row[7]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='params',
            cpg_type='MethodParameterIn',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=8,
            row_parser=parse_row,
            limit=limit
        )

    def _export_returns(self, limit: Optional[int] = None) -> int:
        """Export RETURN nodes."""
        query_template = """
            cpg.ret.drop({offset}).take({batch_size}).map {{ r =>
                val containingMethod = r.method.headOption
                (r.id, r.code, r.filename, r.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_return (id, code, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1])[:2000] if row[1] else '',
                str(row[2]) if row[2] else '',
                int(row[3]) if row[3] and int(row[3]) > 0 else None,
                int(row[4]) if row[4] and int(row[4]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='returns',
            cpg_type='Return',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=5,
            row_parser=parse_row,
            limit=limit
        )

    def _export_blocks(self, limit: Optional[int] = None) -> int:
        """Export BLOCK nodes."""
        query_template = """
            cpg.block.drop({offset}).take({batch_size}).map {{ b =>
                val containingMethod = b.method.headOption
                (b.id, b.typeFullName, b.filename, b.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_block (id, type_full_name, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2]) if row[2] else '',
                int(row[3]) if row[3] and int(row[3]) > 0 else None,
                int(row[4]) if row[4] and int(row[4]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='blocks',
            cpg_type='Block',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=5,
            row_parser=parse_row,
            limit=limit
        )

    def _export_control_structures(self, limit: Optional[int] = None) -> int:
        """Export CONTROL_STRUCTURE nodes."""
        query_template = """
            cpg.controlStructure.drop({offset}).take({batch_size}).map {{ cs =>
                val containingMethod = cs.method.headOption
                (cs.id, cs.controlStructureType, cs.code, cs.filename, cs.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_control_structure (id, control_structure_type, code, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2])[:2000] if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None,
                int(row[5]) if row[5] and int(row[5]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='control_structures',
            cpg_type='ControlStructure',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=6,
            row_parser=parse_row,
            limit=limit
        )

    def _export_type_decls(self, limit: Optional[int] = None) -> int:
        """Export TYPE_DECL nodes."""
        query_template = """
            cpg.typeDecl.drop({offset}).take({batch_size}).map {{ t =>
                (t.id, t.name, t.fullName, t.filename, t.lineNumber.getOrElse(-1))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_type_decl (id, name, full_name, filename, line_number)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1]) if row[1] else '',
                str(row[2]) if row[2] else '',
                str(row[3]) if row[3] else '',
                int(row[4]) if row[4] and int(row[4]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='type_decls',
            cpg_type='TypeDecl',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=5,
            row_parser=parse_row,
            limit=limit
        )

    def _export_comments(self, limit: Optional[int] = None) -> int:
        """Export COMMENT nodes."""
        query_template = """
            cpg.comment.drop({offset}).take({batch_size}).map {{ c =>
                val containingMethod = c.astParent.collectFirst {{ case m: io.shiftleft.codepropertygraph.generated.nodes.Method => m }}
                (c.id, c.code, c.filename, c.lineNumber.getOrElse(-1),
                 containingMethod.map(_.id).getOrElse(-1L))
            }}.l
        """

        insert_sql = """
            INSERT INTO nodes_comment (id, code, filename, line_number, containing_method_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """

        def parse_row(row):
            return (
                int(row[0]) if row[0] else None,
                str(row[1])[:10000] if row[1] else '',
                str(row[2]) if row[2] else '',
                int(row[3]) if row[3] and int(row[3]) > 0 else None,
                int(row[4]) if row[4] and int(row[4]) > 0 else None
            )

        return self.batch_processor.export_nodes(
            entity_type='comments',
            cpg_type='Comment',
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=5,
            row_parser=parse_row,
            limit=limit
        )

    # === Edge Export Methods ===

    def _export_ast_edges(self, limit: Optional[int] = None) -> int:
        """Export AST edges."""
        query_template = """
            cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
                n._astOut.map(child => (n.id, child.id))
            }}.l
        """

        return self.batch_processor.export_edges(
            entity_type='ast_edges',
            edge_query_template=query_template,
            insert_sql="INSERT INTO edges_ast (src, dst) VALUES (?, ?) ON CONFLICT DO NOTHING",
            limit=limit
        )

    def _export_cfg_edges(self, limit: Optional[int] = None) -> int:
        """Export CFG edges."""
        query_template = """
            cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
                n._cfgOut.map(succ => (n.id, succ.id))
            }}.l
        """

        return self.batch_processor.export_edges(
            entity_type='cfg_edges',
            edge_query_template=query_template,
            insert_sql="INSERT INTO edges_cfg (src, dst) VALUES (?, ?) ON CONFLICT DO NOTHING",
            limit=limit
        )

    def _export_ref_edges(self, limit: Optional[int] = None) -> int:
        """Export REF edges."""
        query_template = """
            cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
                n._refOut.map(ref => (n.id, ref.id))
            }}.l
        """

        return self.batch_processor.export_edges(
            entity_type='ref_edges',
            edge_query_template=query_template,
            insert_sql="INSERT INTO edges_ref (src, dst) VALUES (?, ?) ON CONFLICT DO NOTHING",
            limit=limit
        )

    def __enter__(self):
        self.connect_db()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()
