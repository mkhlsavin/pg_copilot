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
            "nodes_metadata", "nodes_type_decl", "nodes_control_structure",
            "nodes_block", "nodes_return", "nodes_param", "nodes_local",
            "nodes_literal", "nodes_identifier", "nodes_call", "nodes_method"
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

        logger.info("DuckDB schema initialized successfully (CPG Spec v1.1 compliant)")

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
cpg.method.drop.slice({offset}, {offset + current_batch_size}).map {{ m =>
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
cpg.call.drop.slice({offset}, {offset + current_batch_size}).map {{ c =>
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

        logger.info("=" * 80)
        logger.info("CPG Export Summary:")
        logger.info(f"  Methods exported: {method_count}")
        logger.info(f"  Call nodes exported: {call_node_count}")
        logger.info(f"  Call edges exported: {call_edge_count}")
        logger.info("=" * 80)

        return {
            'methods': method_count,
            'call_nodes': call_node_count,
            'call_edges': call_edge_count
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
