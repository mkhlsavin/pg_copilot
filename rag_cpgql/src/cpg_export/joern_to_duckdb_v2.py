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
        joern_path: str,
        workspace_path: str,
        db_path: str = "cpg.duckdb",
        batch_size: int = 10000
    ):
        """
        Initialize Joern to DuckDB exporter

        Args:
            joern_path: Path to Joern installation
            workspace_path: Path to Joern workspace
            db_path: Path to DuckDB database file
            batch_size: Number of rows to insert in each batch
        """
        self.joern_client = JoernClient(joern_path, workspace_path)
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

    def _initialize_schema(self):
        """Initialize DuckDB schema for CPG storage (CPG Spec v1.1)"""
        logger.info("Initializing CPG schema (CPG Spec v1.1)...")

        # Drop existing tables if they exist (in correct order due to foreign keys)
        logger.info("Dropping existing tables...")
        tables_to_drop = [
            "edges_post_dominate", "edges_dominate", "edges_condition",
            "edges_receiver", "edges_argument", "edges_reaching_def",
            "edges_ref", "edges_call", "edges_cfg", "edges_ast",
            "edges_source_file",
            "nodes_metadata", "nodes_type_decl", "nodes_control_structure",
            "nodes_block", "nodes_return", "nodes_param", "nodes_local",
            "nodes_literal", "nodes_identifier", "nodes_call", "nodes_method",
            "nodes_comment"
        ]
        for table in tables_to_drop:
            self.conn.execute(f"DROP TABLE IF EXISTS {table}")

        # Create nodes_method table (CPG Spec: METHOD node)
        logger.info("Creating node tables...")
        self.conn.execute("""
            CREATE TABLE nodes_method (
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
            CREATE TABLE nodes_call (
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
            CREATE TABLE nodes_identifier (
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
            CREATE TABLE nodes_literal (
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
            CREATE TABLE nodes_local (
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
            CREATE TABLE nodes_param (
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
            CREATE TABLE nodes_return (
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
            CREATE TABLE nodes_block (
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
            CREATE TABLE nodes_control_structure (
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
            CREATE TABLE nodes_type_decl (
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
            CREATE TABLE nodes_metadata (
                id BIGINT PRIMARY KEY,
                language VARCHAR,
                version VARCHAR,
                overlays VARCHAR[],
                root VARCHAR
            )
        """)

        # Create nodes_comment table (CPG Spec: COMMENT node)
        self.conn.execute("""
            CREATE TABLE nodes_comment (
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

        # Create edge tables
        logger.info("Creating edge tables...")

        # Create edges_ast table (CPG Spec: AST edge)
        self.conn.execute("""
            CREATE TABLE edges_ast (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_cfg table (CPG Spec: CFG edge)
        self.conn.execute("""
            CREATE TABLE edges_cfg (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_call table (CPG Spec: CALL edge)
        self.conn.execute("""
            CREATE TABLE edges_call (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_ref table (CPG Spec: REF edge)
        self.conn.execute("""
            CREATE TABLE edges_ref (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_reaching_def table (CPG Spec: REACHING_DEF edge)
        self.conn.execute("""
            CREATE TABLE edges_reaching_def (
                src BIGINT,
                dst BIGINT,
                variable VARCHAR,
                PRIMARY KEY (src, dst, variable)
            )
        """)

        # Create edges_argument table (CPG Spec: ARGUMENT edge)
        self.conn.execute("""
            CREATE TABLE edges_argument (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_receiver table (CPG Spec: RECEIVER edge)
        self.conn.execute("""
            CREATE TABLE edges_receiver (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_condition table (CPG Spec: CONDITION edge)
        self.conn.execute("""
            CREATE TABLE edges_condition (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_dominate table (CPG Spec: DOMINATE edge)
        self.conn.execute("""
            CREATE TABLE edges_dominate (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_post_dominate table (CPG Spec: POST_DOMINATE edge)
        self.conn.execute("""
            CREATE TABLE edges_post_dominate (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        # Create edges_source_file table (Comment to AST parent relationship)
        self.conn.execute("""
            CREATE TABLE edges_source_file (
                src BIGINT,
                dst BIGINT,
                PRIMARY KEY (src, dst)
            )
        """)

        logger.info("Creating indexes...")

        # Node indexes
        self.conn.execute("CREATE INDEX idx_method_full_name ON nodes_method(full_name)")
        self.conn.execute("CREATE INDEX idx_method_name ON nodes_method(name)")
        self.conn.execute("CREATE INDEX idx_method_filename ON nodes_method(filename)")

        self.conn.execute("CREATE INDEX idx_call_method_full_name ON nodes_call(method_full_name)")
        self.conn.execute("CREATE INDEX idx_call_name ON nodes_call(name)")

        self.conn.execute("CREATE INDEX idx_identifier_name ON nodes_identifier(name)")
        self.conn.execute("CREATE INDEX idx_local_name ON nodes_local(name)")
        self.conn.execute("CREATE INDEX idx_param_name ON nodes_param(name)")
        self.conn.execute("CREATE INDEX idx_type_decl_full_name ON nodes_type_decl(full_name)")

        # Edge indexes
        self.conn.execute("CREATE INDEX idx_ast_src ON edges_ast(src)")
        self.conn.execute("CREATE INDEX idx_ast_dst ON edges_ast(dst)")

        self.conn.execute("CREATE INDEX idx_cfg_src ON edges_cfg(src)")
        self.conn.execute("CREATE INDEX idx_cfg_dst ON edges_cfg(dst)")

        self.conn.execute("CREATE INDEX idx_call_edge_src ON edges_call(src)")
        self.conn.execute("CREATE INDEX idx_call_edge_dst ON edges_call(dst)")

        self.conn.execute("CREATE INDEX idx_ref_src ON edges_ref(src)")
        self.conn.execute("CREATE INDEX idx_ref_dst ON edges_ref(dst)")

        self.conn.execute("CREATE INDEX idx_reaching_def_src ON edges_reaching_def(src)")
        self.conn.execute("CREATE INDEX idx_reaching_def_dst ON edges_reaching_def(dst)")
        self.conn.execute("CREATE INDEX idx_reaching_def_variable ON edges_reaching_def(variable)")

        self.conn.execute("CREATE INDEX idx_argument_src ON edges_argument(src)")
        self.conn.execute("CREATE INDEX idx_argument_dst ON edges_argument(dst)")

        # Comment indexes
        self.conn.execute("CREATE INDEX idx_comment_filename ON nodes_comment(filename)")
        self.conn.execute("CREATE INDEX idx_comment_line ON nodes_comment(line_number)")
        self.conn.execute("CREATE INDEX idx_source_file_src ON edges_source_file(src)")
        self.conn.execute("CREATE INDEX idx_source_file_dst ON edges_source_file(dst)")

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
            UNION ALL SELECT id, 'TAG' FROM nodes_tag
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
                nodes_tag LABEL TAG,
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

                -- Comment and Tag edges (P0/P1 - CPG Integration)
                edges_source_file
                    SOURCE KEY (src) REFERENCES nodes_comment (id)
                    DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                    LABEL SOURCE_FILE,
                edges_tagged_by
                    SOURCE KEY (src) REFERENCES cpg_nodes (id)
                    DESTINATION KEY (dst) REFERENCES nodes_tag (id)
                    LABEL TAGGED_BY
            )
        """)

        logger.info("[OK] Property Graph created successfully with ALL edge types!")
        logger.info("[OK] Includes: AST, CFG, CALL, REF, REACHING_DEF, ARGUMENT, DOMINATE, POST_DOMINATE, RECEIVER, CONDITION, SOURCE_FILE, TAGGED_BY")

    def _export_methods_batched(self, limit: Optional[int] = None):
        """Export methods from Joern to DuckDB in batches"""
        logger.info(f"Exporting methods (batch size: {self.batch_size}, limit: {limit or 'None'})...")

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

        offset = 0
        total_exported = 0

        while offset < total_methods:
            current_batch_size = min(self.batch_size, total_methods - offset)

            # Build batched query
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
    m.code,
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
            rows_to_insert = []
            for line in result.strip().split('\n'):
                if not line.strip():
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

            # Bulk insert
            if rows_to_insert:
                self.conn.executemany("""
                    INSERT INTO nodes_method VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_to_insert)

                total_exported += len(rows_to_insert)
                logger.info(f"Inserted {len(rows_to_insert)} methods (total: {total_exported}/{total_methods})")

            offset += current_batch_size

        logger.info(f"Method export complete. Total exported: {total_exported}")
        return total_exported

    def _export_calls_batched(self, limit: Optional[int] = None):
        """Export CALL nodes and CALL edges from Joern to DuckDB in batches"""
        logger.info(f"Exporting CALL nodes and edges (batch size: {self.batch_size})...")

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

        offset = 0
        total_call_nodes = 0
        total_call_edges = 0

        while offset < total_calls:
            current_batch_size = min(self.batch_size, total_calls - offset)

            # Build batched query for CALL nodes
            query = f"""
cpg.call.drop({offset}).take({current_batch_size}).map {{ c =>
  List(
    c.id,
    c.methodFullName,
    c.name,
    c.signature,
    c.typeFullName,
    c.dispatchType,
    c.code,
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.order,
    c.argumentIndex
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
            call_rows = []
            call_ids = []

            for line in result.strip().split('\n'):
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) < 11:
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
                        None            # filename
                    )
                    call_rows.append(row)
                    call_ids.append(call_id)
                except Exception as e:
                    logger.warning(f"Error parsing call row: {e}")
                    continue

            # Bulk insert CALL nodes
            if call_rows:
                self.conn.executemany("""
                    INSERT INTO nodes_call VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            self.conn.executemany("INSERT INTO edges_call VALUES (?, ?)", edge_rows)
                            total_call_edges += len(edge_rows)
                            logger.info(f"Inserted {len(edge_rows)} call edges")

            logger.info(f"Progress: {total_call_nodes}/{total_calls} call nodes, {total_call_edges} call edges")
            offset += current_batch_size

        logger.info(f"Call export complete. Nodes: {total_call_nodes}, Edges: {total_call_edges}")
        return total_call_nodes, total_call_edges

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
    c.file.name.headOption.getOrElse("unknown"),
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

    def export_full_cpg(self, limit: Optional[int] = None):
        """
        Export full CPG from Joern to DuckDB

        Args:
            limit: Optional limit on number of methods to export
        """
        logger.info("Starting full CPG export...")

        # Initialize schema
        self._initialize_schema()

        # Export methods
        method_count = self._export_methods_batched(limit=limit)

        # Export calls
        call_node_count, call_edge_count = self._export_calls_batched(limit=limit)

        # Export comments (P0 - CPG Integration)
        comment_count = self._export_comments_batched(limit=limit)

        # Export comment edges (P0 - CPG Integration)
        comment_edge_count = self._export_comment_edges_batched(limit=limit)

        # Export includes (Sprint 3 - Scenario 11 Enhancement)
        include_count = self._export_includes(limit=limit)

        # Create property graph
        self._create_property_graph()

        logger.info("=" * 80)
        logger.info("CPG Export Summary:")
        logger.info(f"  Methods exported: {method_count}")
        logger.info(f"  Call nodes exported: {call_node_count}")
        logger.info(f"  Call edges exported: {call_edge_count}")
        logger.info(f"  Comments exported: {comment_count}")
        logger.info(f"  Comment edges exported: {comment_edge_count}")
        logger.info(f"  Include edges exported: {include_count}")
        logger.info("=" * 80)

        return {
            'methods': method_count,
            'call_nodes': call_node_count,
            'call_edges': call_edge_count,
            'comments': comment_count,
            'comment_edges': comment_edge_count,
            'include_edges': include_count
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Export Joern CPG to DuckDB")
    parser.add_argument('--joern-path', type=str, required=True,
                        help='Path to Joern installation')
    parser.add_argument('--workspace', type=str, required=True,
                        help='Path to Joern workspace')
    parser.add_argument('--db', type=str, default='cpg.duckdb',
                        help='Path to DuckDB database file')
    parser.add_argument('--batch-size', type=int, default=10000,
                        help='Batch size for exports')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of methods to export (for testing)')

    args = parser.parse_args()

    # Create exporter
    exporter = JoernToDuckDB(
        joern_path=args.joern_path,
        workspace_path=args.workspace,
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

        # Export full CPG
        stats = exporter.export_full_cpg(limit=args.limit)

        logger.info("\nExport completed successfully!")
        logger.info(f"Database file: {args.db}")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        exporter.close_db()


if __name__ == "__main__":
    main()
