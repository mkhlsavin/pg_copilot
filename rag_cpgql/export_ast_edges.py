#!/usr/bin/env python3
"""
Export missing AST edges from Joern CPG server to DuckDB.

This script exports:
1. Call site to containing method mapping (edges_ast)
2. Updates nodes_call with proper filenames and method_id

Usage:
    python export_ast_edges.py --host localhost --port 8080
"""

import argparse
import json
import sys
import duckdb
from pathlib import Path
from typing import Any, Dict, List, Optional
from cpgqls_client import CPGQLSClient


def execute_query(client: CPGQLSClient, query: str) -> Optional[str]:
    """Execute a CPGQL query and return stdout."""
    try:
        response = client.execute(query)
        stdout = (response.get("stdout") or "").strip()
        if response.get("error"):
            print(f"Query error: {response['error']}", file=sys.stderr)
            return None
        return stdout
    except Exception as e:
        print(f"Query execution failed: {e}", file=sys.stderr)
        return None


def parse_json_list(stdout: str) -> List[Any]:
    """Parse JSON list from Joern output."""
    if not stdout or stdout == "List()":
        return []
    try:
        # Joern outputs Scala-style, try to parse as JSON
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Try to extract JSON from Scala format
        # Format might be: List((id1, id2, name), ...)
        print(f"Warning: Could not parse JSON, raw output length: {len(stdout)}")
        return []


def export_call_to_method_mapping(client: CPGQLSClient, batch_size: int = 10000) -> List[Dict]:
    """Export call site to containing method mapping."""
    print("\n=== Exporting call site to method mapping ===")

    # First, get total count
    count_query = "cpg.call.size"
    count_result = execute_query(client, count_query)
    total_calls = int(count_result) if count_result and count_result.isdigit() else 0
    print(f"Total call sites: {total_calls}")

    if total_calls == 0:
        return []

    all_mappings = []

    # Export in batches
    for offset in range(0, total_calls, batch_size):
        print(f"  Processing batch {offset//batch_size + 1} ({offset}-{min(offset+batch_size, total_calls)})...")

        # Query: get call id, containing method id, method name, filename
        query = f"""
            cpg.call.drop({offset}).take({batch_size}).map {{ c =>
                val methodId = c.method.id
                val methodName = c.method.name
                val fileName = c.file.name.headOption.getOrElse("")
                val lineNum = c.lineNumber.getOrElse(-1)
                (c.id, methodId, methodName, fileName, lineNum)
            }}.toJson
        """

        result = execute_query(client, query)
        if result:
            try:
                batch_data = json.loads(result)
                for item in batch_data:
                    if isinstance(item, list) and len(item) >= 5:
                        all_mappings.append({
                            'call_id': item[0],
                            'method_id': item[1],
                            'method_name': item[2],
                            'filename': item[3],
                            'line_number': item[4]
                        })
                print(f"    Got {len(batch_data)} mappings")
            except json.JSONDecodeError as e:
                print(f"    Failed to parse batch: {e}")

    print(f"Total mappings exported: {len(all_mappings)}")
    return all_mappings


def export_ast_edges(client: CPGQLSClient, batch_size: int = 50000) -> List[Dict]:
    """Export AST edges (parent-child relationships)."""
    print("\n=== Exporting AST edges ===")

    # Get AST edges count
    count_query = "cpg.all.outE(\"AST\").size"
    count_result = execute_query(client, count_query)
    total_edges = int(count_result) if count_result and count_result.isdigit() else 0
    print(f"Total AST edges in CPG: {total_edges}")

    if total_edges == 0:
        # Try alternative query
        print("Trying alternative AST edge query...")
        count_query = "cpg.method.ast.size"
        count_result = execute_query(client, count_query)
        print(f"Method AST nodes: {count_result}")
        return []

    all_edges = []

    # Export in batches
    for offset in range(0, total_edges, batch_size):
        print(f"  Processing batch {offset//batch_size + 1}...")

        query = f"""
            cpg.all.outE("AST").drop({offset}).take({batch_size}).map {{ e =>
                (e.outNode.id, e.inNode.id)
            }}.toJson
        """

        result = execute_query(client, query)
        if result:
            try:
                batch_data = json.loads(result)
                for item in batch_data:
                    if isinstance(item, list) and len(item) >= 2:
                        all_edges.append({
                            'src': item[0],
                            'dst': item[1]
                        })
            except json.JSONDecodeError as e:
                print(f"    Failed to parse batch: {e}")

    print(f"Total AST edges exported: {len(all_edges)}")
    return all_edges


def update_duckdb(db_path: str, call_mappings: List[Dict], ast_edges: List[Dict]):
    """Update DuckDB with exported data."""
    print(f"\n=== Updating DuckDB: {db_path} ===")

    con = duckdb.connect(db_path)

    # 1. Update nodes_call with filename and add method_id column
    if call_mappings:
        print(f"Updating nodes_call with {len(call_mappings)} mappings...")

        # Check if method_id column exists
        columns = con.execute("DESCRIBE nodes_call").fetchall()
        column_names = [c[0] for c in columns]

        if 'containing_method_id' not in column_names:
            print("  Adding containing_method_id column...")
            con.execute("ALTER TABLE nodes_call ADD COLUMN containing_method_id BIGINT")

        if 'containing_method_name' not in column_names:
            print("  Adding containing_method_name column...")
            con.execute("ALTER TABLE nodes_call ADD COLUMN containing_method_name VARCHAR")

        # Create temp table and update
        con.execute("""
            CREATE TEMP TABLE call_updates (
                call_id BIGINT,
                method_id BIGINT,
                method_name VARCHAR,
                filename VARCHAR,
                line_number INTEGER
            )
        """)

        # Insert in batches
        batch_size = 10000
        for i in range(0, len(call_mappings), batch_size):
            batch = call_mappings[i:i+batch_size]
            values = [(m['call_id'], m['method_id'], m['method_name'],
                      m['filename'], m['line_number']) for m in batch]
            con.executemany(
                "INSERT INTO call_updates VALUES (?, ?, ?, ?, ?)",
                values
            )

        # Update nodes_call
        print("  Updating nodes_call table...")
        con.execute("""
            UPDATE nodes_call
            SET filename = u.filename,
                containing_method_id = u.method_id,
                containing_method_name = u.method_name,
                line_number = COALESCE(nodes_call.line_number, u.line_number)
            FROM call_updates u
            WHERE nodes_call.id = u.call_id
        """)

        updated = con.execute("SELECT COUNT(*) FROM nodes_call WHERE containing_method_id IS NOT NULL").fetchone()[0]
        print(f"  Updated {updated} rows in nodes_call")

        con.execute("DROP TABLE call_updates")

    # 2. Populate edges_ast if we have data
    if ast_edges:
        print(f"Populating edges_ast with {len(ast_edges)} edges...")

        # Clear existing (if any)
        con.execute("DELETE FROM edges_ast")

        # Insert in batches
        batch_size = 50000
        for i in range(0, len(ast_edges), batch_size):
            batch = ast_edges[i:i+batch_size]
            values = [(e['src'], e['dst']) for e in batch]
            con.executemany("INSERT INTO edges_ast VALUES (?, ?)", values)

        count = con.execute("SELECT COUNT(*) FROM edges_ast").fetchone()[0]
        print(f"  edges_ast now has {count} edges")

    # 3. Create caller-callee view for easy querying
    print("Creating helper view for call graph queries...")
    con.execute("""
        CREATE OR REPLACE VIEW call_graph AS
        SELECT
            caller.name as caller_name,
            caller.id as caller_id,
            callee.name as callee_name,
            callee.id as callee_id,
            c.code as call_code,
            c.line_number,
            c.filename
        FROM edges_call e
        JOIN nodes_call c ON e.src = c.id
        JOIN nodes_method callee ON e.dst = callee.id
        LEFT JOIN nodes_method caller ON c.containing_method_id = caller.id
    """)

    # Verify
    print("\n=== Verification ===")
    result = con.execute("""
        SELECT caller_name, callee_name, call_code
        FROM call_graph
        WHERE callee_name = 'heap_insert'
        LIMIT 5
    """).fetchall()

    print(f"Sample callers of heap_insert:")
    for r in result:
        print(f"  {r[0]} -> heap_insert: {r[2][:50] if r[2] else 'N/A'}...")

    con.close()
    print("\nDuckDB update complete!")


def main():
    parser = argparse.ArgumentParser(description="Export AST edges from Joern to DuckDB")
    parser.add_argument("--host", default="localhost", help="Joern server host")
    parser.add_argument("--port", type=int, default=8080, help="Joern server port")
    parser.add_argument("--db", default="cpg.duckdb", help="DuckDB database path")
    parser.add_argument("--batch-size", type=int, default=10000, help="Batch size for exports")
    parser.add_argument("--skip-ast", action="store_true", help="Skip AST edge export")
    args = parser.parse_args()

    endpoint = f"{args.host}:{args.port}"
    print(f"Connecting to Joern server at {endpoint}...")

    try:
        client = CPGQLSClient(endpoint)
    except Exception as e:
        print(f"Failed to connect: {e}", file=sys.stderr)
        sys.exit(1)

    # Test connection
    result = execute_query(client, "cpg.method.size")
    print(f"Connected! CPG has {result} methods")

    # Export call-to-method mapping (most important)
    call_mappings = export_call_to_method_mapping(client, args.batch_size)

    # Export AST edges (optional, may be large)
    ast_edges = []
    if not args.skip_ast:
        ast_edges = export_ast_edges(client, args.batch_size * 5)

    # Update DuckDB
    if call_mappings or ast_edges:
        update_duckdb(args.db, call_mappings, ast_edges)
    else:
        print("No data to export!")


if __name__ == "__main__":
    main()
