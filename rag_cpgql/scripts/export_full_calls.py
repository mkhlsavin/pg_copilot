#!/usr/bin/env python3
"""
Export ALL nodes_call from Joern CPG to DuckDB.

This script exports call nodes from ALL files in the Joern CPG,
not just the ones that were previously exported (backend/access, backend/catalog).

Usage:
    python scripts/export_full_calls.py --db cpg.duckdb

Prerequisites:
    - Joern server running on localhost:8080
    - CPG loaded in Joern workspace (pg17_full.cpg)
"""

import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import duckdb
    from src.execution.joern_client import JoernClient
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you have duckdb and cpgqls-client installed")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_joern_connection(client: JoernClient) -> bool:
    """Check if Joern server is reachable."""
    logger.info("Checking Joern connection...")
    if client.connect():
        result = client.execute_query("cpg.call.size")
        if result.get('success'):
            count = result.get('result', '0').strip()
            logger.info(f"Joern CPG has {count} total call nodes")
            return True
    return False


def get_call_files_from_joern(client: JoernClient) -> list:
    """Get list of unique files with call nodes from Joern."""
    result = client.execute_query("cpg.call.file.name.distinct.l")
    if result.get('success'):
        files_str = result.get('result', '')
        # Parse Scala list format: List(file1, file2, ...)
        if 'List(' in files_str:
            files_str = files_str.replace('List(', '').replace(')', '')
            files = [f.strip().strip('"') for f in files_str.split(',') if f.strip()]
            return files
    return []


def export_calls_for_directory(client: JoernClient, conn: duckdb.DuckDBPyConnection,
                               directory: str, batch_size: int = 5000) -> int:
    """Export call nodes from a specific directory."""
    # Count calls in this directory
    count_query = f'cpg.call.filter(_.file.name.exists(_.contains("{directory}"))).size'
    result = client.execute_query(count_query)

    if not result.get('success'):
        logger.warning(f"Failed to count calls in {directory}")
        return 0

    total_calls = int(result.get('result', '0').strip())
    if total_calls == 0:
        logger.info(f"No calls in {directory}")
        return 0

    logger.info(f"Exporting {total_calls} calls from {directory}...")

    exported = 0
    offset = 0

    while offset < total_calls:
        current_batch = min(batch_size, total_calls - offset)

        query = f'''
cpg.call.filter(_.file.name.exists(_.contains("{directory}"))).drop({offset}).take({current_batch}).map {{ c =>
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
'''
        result = client.execute_query(query)

        if not result.get('success'):
            logger.error(f"Failed to fetch calls at offset {offset}")
            break

        output = result.get('result', '')
        if not output or not output.strip():
            break

        rows = []
        for line in output.strip().split('\n'):
            if not line.strip() or 'val res' in line:
                continue
            parts = line.split('\t')
            if len(parts) >= 12:
                try:
                    row = (
                        int(parts[0]),
                        parts[1],
                        parts[2],
                        parts[3],
                        parts[4],
                        parts[5],
                        parts[6],
                        int(parts[7]) if parts[7].lstrip('-').isdigit() else None,
                        int(parts[8]) if parts[8].lstrip('-').isdigit() else None,
                        int(parts[9]) if parts[9].lstrip('-').isdigit() else None,
                        int(parts[10]) if parts[10].lstrip('-').isdigit() else None,
                        parts[11] if len(parts) > 11 else None
                    )
                    rows.append(row)
                except Exception as e:
                    logger.debug(f"Parse error: {e}")
                    continue

        if rows:
            conn.executemany("""
                INSERT OR IGNORE INTO nodes_call
                (id, method_full_name, name, signature, type_full_name, dispatch_type,
                 code, line_number, column_number, order_index, argument_index, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            exported += len(rows)

        offset += current_batch
        logger.info(f"  Progress: {exported}/{total_calls} calls from {directory}")

    return exported


def main():
    parser = argparse.ArgumentParser(description="Export all nodes_call from Joern to DuckDB")
    parser.add_argument("--db", type=str, default="cpg.duckdb", help="DuckDB database path")
    parser.add_argument("--joern", type=str, default="localhost:8080", help="Joern server endpoint")
    parser.add_argument("--workspace", type=str, default="pg17_full.cpg", help="Joern workspace name")
    parser.add_argument("--directories", type=str, nargs="+",
                        default=["backend/commands", "bin/pg_dump", "backend/optimizer",
                                 "backend/parser", "backend/utils", "src/bin"],
                        help="Directories to export (default: CVE-critical)")

    args = parser.parse_args()

    # Connect to Joern
    client = JoernClient(args.joern, args.workspace)
    if not check_joern_connection(client):
        logger.error("Cannot connect to Joern server")
        logger.error("Make sure Joern is running: joern-server")
        logger.error(f"And CPG is loaded: open(\"{args.workspace}\")")
        sys.exit(1)

    # Connect to DuckDB
    conn = duckdb.connect(args.db)
    logger.info(f"Connected to DuckDB: {args.db}")

    # Get current count
    before_count = conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
    logger.info(f"Current nodes_call count: {before_count}")

    # Export from each directory
    total_exported = 0
    for directory in args.directories:
        exported = export_calls_for_directory(client, conn, directory)
        total_exported += exported

    # Final count
    after_count = conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
    new_records = after_count - before_count

    logger.info("=" * 60)
    logger.info("EXPORT COMPLETE")
    logger.info(f"  Before: {before_count}")
    logger.info(f"  After:  {after_count}")
    logger.info(f"  New:    {new_records}")
    logger.info("=" * 60)

    # Verify CVE files
    logger.info("\nVerifying CVE target files:")
    for filename in ["analyze.c", "pg_dump.c", "pg_backup_archiver.c", "selfuncs.c"]:
        count = conn.execute(f"""
            SELECT COUNT(*) FROM nodes_call WHERE filename LIKE '%{filename}'
        """).fetchone()[0]
        status = "OK" if count > 0 else "MISSING"
        logger.info(f"  {filename}: {count} calls [{status}]")

    conn.close()


if __name__ == "__main__":
    main()
