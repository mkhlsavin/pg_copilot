"""Export Data Flow edges from Joern CPG to DuckDB

This script exports:
1. IDENTIFIER nodes (variable references)
2. LOCAL nodes (local variable definitions)
3. PARAM nodes (function parameters)
4. REACHING_DEF edges (def-use chains - key for data flow analysis)
5. Method-level data flow summary table for efficient querying

Usage:
    python export_dataflow_edges.py [--batch-size 5000] [--limit 1000]
"""

import sys
import os
import duckdb
import logging
import re
import asyncio
from pathlib import Path

try:
    from cpgqls_client import CPGQLSClient
except ImportError:
    CPGQLSClient = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


class JoernDataFlowExporter:
    """Export data flow information from Joern to DuckDB"""

    def __init__(self, db_path: str = "cpg.duckdb", server_endpoint: str = "localhost:8080",
                 workspace: str = "pg17_full.cpg"):
        if CPGQLSClient is None:
            raise ImportError("cpgqls-client not installed. Run: pip install cpgqls-client")

        self.db_path = db_path
        self.server_endpoint = server_endpoint
        self.workspace = workspace
        self.conn = None
        self.client = None
        self.batch_size = 5000

    def connect_db(self):
        """Connect to DuckDB"""
        logger.info(f"Connecting to DuckDB: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)

    def connect_joern(self) -> bool:
        """Connect to Joern server and bootstrap the session"""
        try:
            logger.info(f"Connecting to Joern server at {self.server_endpoint}")

            # Ensure event loop exists
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            self.client = CPGQLSClient(self.server_endpoint)

            # Bootstrap session
            if not self._bootstrap_session():
                logger.error("Failed to bootstrap Joern session")
                return False

            # Test connection
            test = self.execute_joern_query("cpg.method.name.l.size")
            if test["success"]:
                logger.info(f"Connected to Joern server (CPG has {test['result']} methods)")
                return True

            logger.error(f"Connection test failed: {test.get('error')}")
            return False

        except Exception as exc:
            logger.error(f"Failed to connect to Joern: {exc}")
            return False

    def _bootstrap_session(self) -> bool:
        """Bootstrap the Joern interactive session"""
        if not self.client:
            return False

        try:
            # Import required packages
            for command in (
                'import _root_.io.joern.joerncli.console.Joern',
                'import _root_.io.shiftleft.semanticcpg.language._',
            ):
                response = self.client.execute(command)
                if not response.get("success", False):
                    logger.error(f"Bootstrap command failed: {command}")
                    return False

            # Ensure CPG is bound
            if not self._ensure_cpg_bound():
                # Try to open workspace
                response = self.client.execute(f'Joern.open("{self.workspace}")')
                if not response.get("success", False):
                    logger.error(f"Failed to open workspace: {self.workspace}")
                    return False
                if not self._ensure_cpg_bound():
                    return False

            return True
        except Exception as exc:
            logger.error(f"Joern session bootstrap failed: {exc}")
            return False

    def _ensure_cpg_bound(self) -> bool:
        """Ensure CPG is bound in session"""
        response = self.client.execute("val cpg = Joern.cpg")
        if response is None:
            return False
        stdout = response.get("stdout", "") or ""
        if "No CPG loaded" in stdout:
            return False
        return True

    def close_db(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()

    def close_joern(self):
        """Close Joern connection"""
        if self.client:
            self.client = None
            logger.info("Disconnected from Joern server")

    def execute_joern_query(self, query: str) -> dict:
        """Execute a CPGQL query via cpgqls_client"""
        if not self.client:
            return {"success": False, "result": None, "error": "Not connected to Joern"}

        try:
            response = self.client.execute(query)

            stdout = response.get("stdout", "") or ""
            stderr = response.get("stderr", "") or ""
            raw_error = response.get("error")

            # Check for errors
            lowered = (stdout + "\n" + stderr).lower()
            error_markers = [
                "io.joern.console.error",
                "not found",
                "no cpg loaded",
                "exception",
                "-- error",
            ]

            if raw_error or not response.get("success", False) or any(marker in lowered for marker in error_markers):
                error_message = raw_error or stderr or stdout.strip() or "Unknown error"
                return {"success": False, "result": None, "error": error_message}

            return {"success": True, "result": stdout, "error": None}

        except Exception as e:
            return {"success": False, "result": None, "error": str(e)}

    def _ensure_tables(self):
        """Ensure required tables exist"""
        logger.info("Ensuring data flow tables exist...")

        # Create nodes_identifier if not exists
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

        # Create nodes_local if not exists
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

        # Create nodes_param if not exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes_param (
                id BIGINT PRIMARY KEY,
                name VARCHAR,
                type_full_name VARCHAR,
                code TEXT,
                line_number INTEGER,
                column_number INTEGER,
                order_index INTEGER,
                index_num INTEGER,
                is_variadic BOOLEAN,
                evaluation_strategy VARCHAR
            )
        """)

        # Create edges_reaching_def if not exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges_reaching_def (
                src BIGINT,
                dst BIGINT,
                variable VARCHAR,
                PRIMARY KEY (src, dst, variable)
            )
        """)

        # Create method-level data flow summary table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dataflow_summary (
                method_name VARCHAR,
                method_full_name VARCHAR,
                variable_name VARCHAR,
                definition_node_id BIGINT,
                definition_line INTEGER,
                use_node_id BIGINT,
                use_line INTEGER,
                flow_type VARCHAR,
                filename VARCHAR,
                PRIMARY KEY (method_full_name, variable_name, definition_node_id, use_node_id)
            )
        """)

        # Create indexes
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_identifier_name ON nodes_identifier(name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_local_name ON nodes_local(name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_param_name ON nodes_param(name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reaching_def_variable ON edges_reaching_def(variable)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dataflow_method ON dataflow_summary(method_name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dataflow_variable ON dataflow_summary(variable_name)")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def export_identifiers(self, limit: int = None):
        """Export IDENTIFIER nodes from Joern"""
        logger.info("Exporting IDENTIFIER nodes...")

        # Get count
        count_query = "cpg.identifier.size"
        result = self.execute_joern_query(count_query)
        if not result.get('success'):
            logger.error(f"Failed to get identifier count: {result.get('error')}")
            return 0

        count_match = re.search(r'=\s*(\d+)', result.get('result', '0'))
        total = int(count_match.group(1)) if count_match else 0
        if limit:
            total = min(total, limit)
        logger.info(f"Total identifiers to export: {total}")

        offset = 0
        total_exported = 0

        while offset < total:
            batch_size = min(self.batch_size, total - offset)

            query = f"""
cpg.identifier.drop({offset}).take({batch_size}).map {{ i =>
  List(
    i.id,
    i.name,
    i.typeFullName,
    i.code,
    i.lineNumber.getOrElse(-1),
    i.columnNumber.getOrElse(-1),
    i.order,
    i.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            result = self.execute_joern_query(query)
            if not result.get('success'):
                logger.error(f"Failed to fetch identifiers: {result.get('error')}")
                break

            data = result.get('result', '').strip()
            if not data:
                break

            rows = []
            for line in data.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 8:
                    try:
                        rows.append((
                            int(parts[0]),
                            parts[1],
                            parts[2],
                            parts[3],
                            int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                            int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                            int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                            int(parts[7]) if parts[7].lstrip('-').isdigit() else None
                        ))
                    except Exception as e:
                        continue

            if rows:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO nodes_identifier VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    rows
                )
                total_exported += len(rows)
                logger.info(f"Exported {total_exported}/{total} identifiers")

            offset += batch_size

        logger.info(f"Identifier export complete: {total_exported}")
        return total_exported

    def export_locals(self, limit: int = None):
        """Export LOCAL nodes from Joern"""
        logger.info("Exporting LOCAL nodes...")

        # Get count
        count_query = "cpg.local.size"
        result = self.execute_joern_query(count_query)
        if not result.get('success'):
            logger.error(f"Failed to get local count: {result.get('error')}")
            return 0

        count_match = re.search(r'=\s*(\d+)', result.get('result', '0'))
        total = int(count_match.group(1)) if count_match else 0
        if limit:
            total = min(total, limit)
        logger.info(f"Total locals to export: {total}")

        offset = 0
        total_exported = 0

        while offset < total:
            batch_size = min(self.batch_size, total - offset)

            query = f"""
cpg.local.drop({offset}).take({batch_size}).map {{ l =>
  List(
    l.id,
    l.name,
    l.typeFullName,
    l.code,
    l.lineNumber.getOrElse(-1),
    l.columnNumber.getOrElse(-1),
    l.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            result = self.execute_joern_query(query)
            if not result.get('success'):
                logger.error(f"Failed to fetch locals: {result.get('error')}")
                break

            data = result.get('result', '').strip()
            if not data:
                break

            rows = []
            for line in data.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    try:
                        rows.append((
                            int(parts[0]),
                            parts[1],
                            parts[2],
                            parts[3],
                            int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                            int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                            int(parts[6]) if parts[6].lstrip('-').isdigit() else None
                        ))
                    except Exception as e:
                        continue

            if rows:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO nodes_local VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows
                )
                total_exported += len(rows)
                logger.info(f"Exported {total_exported}/{total} locals")

            offset += batch_size

        logger.info(f"Local export complete: {total_exported}")
        return total_exported

    def export_params(self, limit: int = None):
        """Export PARAM nodes from Joern"""
        logger.info("Exporting PARAM nodes...")

        # Get count
        count_query = "cpg.parameter.size"
        result = self.execute_joern_query(count_query)
        if not result.get('success'):
            logger.error(f"Failed to get param count: {result.get('error')}")
            return 0

        count_match = re.search(r'=\s*(\d+)', result.get('result', '0'))
        total = int(count_match.group(1)) if count_match else 0
        if limit:
            total = min(total, limit)
        logger.info(f"Total params to export: {total}")

        offset = 0
        total_exported = 0

        while offset < total:
            batch_size = min(self.batch_size, total - offset)

            query = f"""
cpg.parameter.drop({offset}).take({batch_size}).map {{ p =>
  List(
    p.id,
    p.name,
    p.typeFullName,
    p.code,
    p.lineNumber.getOrElse(-1),
    p.columnNumber.getOrElse(-1),
    p.order,
    p.index,
    p.isVariadic.toString,
    p.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

            result = self.execute_joern_query(query)
            if not result.get('success'):
                logger.error(f"Failed to fetch params: {result.get('error')}")
                break

            data = result.get('result', '').strip()
            if not data:
                break

            rows = []
            for line in data.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 10:
                    try:
                        rows.append((
                            int(parts[0]),
                            parts[1],
                            parts[2],
                            parts[3],
                            int(parts[4]) if parts[4].lstrip('-').isdigit() else None,
                            int(parts[5]) if parts[5].lstrip('-').isdigit() else None,
                            int(parts[6]) if parts[6].lstrip('-').isdigit() else None,
                            int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                            parts[8].lower() == 'true',
                            parts[9]
                        ))
                    except Exception as e:
                        continue

            if rows:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO nodes_param VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    rows
                )
                total_exported += len(rows)
                logger.info(f"Exported {total_exported}/{total} params")

            offset += batch_size

        logger.info(f"Param export complete: {total_exported}")
        return total_exported

    def export_reaching_def_edges(self, limit: int = None):
        """Export REACHING_DEF edges from Joern (def-use chains)"""
        logger.info("Exporting REACHING_DEF edges (def-use chains)...")

        # Get methods and export their reaching definitions
        count_query = "cpg.method.internal.size"
        result = self.execute_joern_query(count_query)
        if not result.get('success'):
            logger.error(f"Failed to get method count: {result.get('error')}")
            return 0

        count_match = re.search(r'=\s*(\d+)', result.get('result', '0'))
        total_methods = int(count_match.group(1)) if count_match else 0
        if limit:
            total_methods = min(total_methods, limit)
        logger.info(f"Exporting reaching definitions for {total_methods} methods...")

        offset = 0
        total_exported = 0
        batch_size = 100  # Process methods in smaller batches

        while offset < total_methods:
            current_batch = min(batch_size, total_methods - offset)

            # Query reaching definitions for batch of methods
            query = f"""
cpg.method.internal.drop({offset}).take({current_batch}).flatMap {{ m =>
  m.ast.isIdentifier.flatMap {{ i =>
    i.reachingDefIn.map {{ defNode =>
      s"${{defNode.id}}\\t${{i.id}}\\t${{i.name}}"
    }}
  }}
}}.l.distinct.mkString("\\n")
"""

            result = self.execute_joern_query(query)
            if not result.get('success'):
                logger.warning(f"Failed to fetch reaching defs for batch at {offset}: {result.get('error')}")
                offset += current_batch
                continue

            data = result.get('result', '').strip()
            if data:
                rows = []
                for line in data.split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        try:
                            rows.append((int(parts[0]), int(parts[1]), parts[2]))
                        except:
                            continue

                if rows:
                    # Use INSERT OR IGNORE to handle duplicates
                    self.conn.executemany(
                        "INSERT OR IGNORE INTO edges_reaching_def VALUES (?, ?, ?)",
                        rows
                    )
                    total_exported += len(rows)

            logger.info(f"Progress: {offset + current_batch}/{total_methods} methods, {total_exported} edges")
            offset += current_batch

        logger.info(f"Reaching def export complete: {total_exported} edges")
        return total_exported

    def build_dataflow_summary(self):
        """Build a method-level data flow summary table for efficient queries"""
        logger.info("Building data flow summary table...")

        # Clear existing summary
        self.conn.execute("DELETE FROM dataflow_summary")

        # Build summary from reaching_def edges joined with method info
        query = """
        INSERT INTO dataflow_summary (method_name, method_full_name, variable_name,
                                       definition_node_id, definition_line, use_node_id, use_line,
                                       flow_type, filename)
        SELECT DISTINCT
            m.name as method_name,
            m.full_name as method_full_name,
            rd.variable as variable_name,
            rd.src as definition_node_id,
            COALESCE(l.line_number, p.line_number, -1) as definition_line,
            rd.dst as use_node_id,
            COALESCE(i.line_number, -1) as use_line,
            CASE
                WHEN l.id IS NOT NULL THEN 'LOCAL_TO_USE'
                WHEN p.id IS NOT NULL THEN 'PARAM_TO_USE'
                ELSE 'UNKNOWN'
            END as flow_type,
            m.filename
        FROM edges_reaching_def rd
        JOIN nodes_identifier i ON i.id = rd.dst
        LEFT JOIN nodes_local l ON l.id = rd.src
        LEFT JOIN nodes_param p ON p.id = rd.src
        LEFT JOIN nodes_method m ON (
            m.line_number <= COALESCE(i.line_number, 0)
            AND m.line_number_end >= COALESCE(i.line_number, 0)
            AND m.filename = (SELECT filename FROM nodes_call WHERE id = rd.src LIMIT 1)
        )
        WHERE m.name IS NOT NULL
        LIMIT 1000000
        """

        try:
            self.conn.execute(query)
            count = self.conn.execute("SELECT COUNT(*) FROM dataflow_summary").fetchone()[0]
            logger.info(f"Built data flow summary with {count} entries")
            return count
        except Exception as e:
            logger.warning(f"Could not build full summary: {e}")
            # Fallback: simpler summary
            return 0

    def export_all(self, limit: int = None):
        """Export all data flow information"""
        self._ensure_tables()

        stats = {}

        # Export nodes
        stats['identifiers'] = self.export_identifiers(limit)
        stats['locals'] = self.export_locals(limit)
        stats['params'] = self.export_params(limit)

        # Export edges
        stats['reaching_def_edges'] = self.export_reaching_def_edges(limit)

        # Build summary
        stats['summary_entries'] = self.build_dataflow_summary()

        # Print summary
        logger.info("=" * 60)
        logger.info("DATA FLOW EXPORT SUMMARY")
        logger.info("=" * 60)
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)

        return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export data flow edges from Joern")
    parser.add_argument('--db', type=str, default='cpg.duckdb', help='DuckDB database path')
    parser.add_argument('--server', type=str, default='localhost:8080', help='Joern server endpoint (host:port)')
    parser.add_argument('--workspace', type=str, default='pg17_full.cpg', help='Joern workspace name')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size for exports')
    parser.add_argument('--limit', type=int, default=None, help='Limit exports (for testing)')

    args = parser.parse_args()

    exporter = JoernDataFlowExporter(
        db_path=args.db,
        server_endpoint=args.server,
        workspace=args.workspace
    )
    exporter.batch_size = args.batch_size

    try:
        # Connect to DuckDB
        exporter.connect_db()

        # Connect to Joern
        if not exporter.connect_joern():
            logger.error("Failed to connect to Joern server. Is it running?")
            sys.exit(1)

        # Export data flow information
        stats = exporter.export_all(limit=args.limit)
        logger.info("Export completed successfully!")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        exporter.close_joern()
        exporter.close_db()


if __name__ == "__main__":
    main()
