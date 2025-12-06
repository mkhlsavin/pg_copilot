#!/usr/bin/env python3
"""
Import call containment data from CSV into DuckDB.

This script imports the call_containment.csv exported from Joern
and updates the DuckDB CPG database with containing method information.

Usage:
    python import_call_containment.py --csv path/to/call_containment.csv --db cpg.duckdb
"""

import argparse
import csv
import duckdb
from pathlib import Path


def import_csv_to_duckdb(csv_path: str, db_path: str):
    """Import call containment CSV into DuckDB."""
    print(f"Importing {csv_path} into {db_path}")

    # Check if CSV exists
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found: {csv_path}")
        return False

    con = duckdb.connect(db_path)

    # 1. Check if columns exist, add if needed
    print("Checking nodes_call table structure...")
    columns = con.execute("DESCRIBE nodes_call").fetchall()
    column_names = [c[0] for c in columns]

    if 'containing_method_id' not in column_names:
        print("  Adding containing_method_id column...")
        con.execute("ALTER TABLE nodes_call ADD COLUMN containing_method_id BIGINT")

    if 'containing_method_name' not in column_names:
        print("  Adding containing_method_name column...")
        con.execute("ALTER TABLE nodes_call ADD COLUMN containing_method_name VARCHAR")

    # 2. Create temp table and load CSV
    print("Loading CSV data...")
    con.execute("""
        CREATE TEMP TABLE call_containment_import (
            call_id BIGINT,
            containing_method_id BIGINT,
            containing_method_name VARCHAR,
            callee_name VARCHAR,
            filename VARCHAR,
            line_number INTEGER,
            code VARCHAR
        )
    """)

    # Import CSV using DuckDB's built-in CSV reader
    try:
        con.execute(f"""
            INSERT INTO call_containment_import
            SELECT * FROM read_csv('{csv_path}',
                header=true,
                columns={{
                    'call_id': 'BIGINT',
                    'containing_method_id': 'BIGINT',
                    'containing_method_name': 'VARCHAR',
                    'callee_name': 'VARCHAR',
                    'filename': 'VARCHAR',
                    'line_number': 'INTEGER',
                    'code': 'VARCHAR'
                }},
                ignore_errors=true
            )
        """)
    except Exception as e:
        print(f"  DuckDB CSV import failed, trying manual import: {e}")
        # Manual import
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            batch = []
            for i, row in enumerate(reader):
                try:
                    batch.append((
                        int(row.get('call_id', 0)),
                        int(row.get('containing_method_id', 0)),
                        row.get('containing_method_name', ''),
                        row.get('callee_name', ''),
                        row.get('filename', ''),
                        int(row.get('line_number', -1)),
                        row.get('code', '')[:500]
                    ))
                    if len(batch) >= 10000:
                        con.executemany(
                            "INSERT INTO call_containment_import VALUES (?, ?, ?, ?, ?, ?, ?)",
                            batch
                        )
                        batch = []
                        print(f"    Imported {i+1} rows...")
                except Exception as row_error:
                    continue  # Skip bad rows
            if batch:
                con.executemany(
                    "INSERT INTO call_containment_import VALUES (?, ?, ?, ?, ?, ?, ?)",
                    batch
                )

    imported = con.execute("SELECT COUNT(*) FROM call_containment_import").fetchone()[0]
    print(f"  Imported {imported} rows from CSV")

    # 3. Update nodes_call with containment info
    print("Updating nodes_call table...")
    con.execute("""
        UPDATE nodes_call
        SET filename = COALESCE(c.filename, nodes_call.filename),
            containing_method_id = c.containing_method_id,
            containing_method_name = c.containing_method_name,
            line_number = COALESCE(c.line_number, nodes_call.line_number)
        FROM call_containment_import c
        WHERE nodes_call.id = c.call_id
    """)

    updated = con.execute(
        "SELECT COUNT(*) FROM nodes_call WHERE containing_method_id IS NOT NULL"
    ).fetchone()[0]
    print(f"  Updated {updated} rows in nodes_call")

    # 4. Create/update call_graph view
    print("Creating call_graph view...")
    con.execute("""
        CREATE OR REPLACE VIEW call_graph AS
        SELECT
            caller.name as caller_name,
            caller.id as caller_id,
            caller.filename as caller_file,
            callee.name as callee_name,
            callee.id as callee_id,
            callee.filename as callee_file,
            c.code as call_code,
            c.line_number as call_line,
            c.filename as call_file
        FROM edges_call e
        JOIN nodes_call c ON e.src = c.id
        JOIN nodes_method callee ON e.dst = callee.id
        LEFT JOIN nodes_method caller ON c.containing_method_id = caller.id
    """)

    # 5. Verify with sample query
    print("\n=== Verification ===")
    result = con.execute("""
        SELECT caller_name, callee_name, call_code
        FROM call_graph
        WHERE callee_name = 'heap_insert' AND caller_name IS NOT NULL
        LIMIT 5
    """).fetchall()

    if result:
        print("Callers of heap_insert:")
        for r in result:
            print(f"  {r[0]} -> heap_insert: {r[2][:50] if r[2] else 'N/A'}...")
    else:
        print("No callers found for heap_insert yet")

    # Show some stats
    print("\n=== Statistics ===")
    total_calls = con.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
    with_containment = con.execute(
        "SELECT COUNT(*) FROM nodes_call WHERE containing_method_id IS NOT NULL"
    ).fetchone()[0]
    print(f"Total call sites: {total_calls}")
    print(f"With containment info: {with_containment} ({100*with_containment/total_calls:.1f}%)")

    # Test call_graph
    graph_rows = con.execute("SELECT COUNT(*) FROM call_graph WHERE caller_name IS NOT NULL").fetchone()[0]
    print(f"Call graph edges with caller: {graph_rows}")

    con.execute("DROP TABLE call_containment_import")
    con.close()

    print("\nImport complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Import call containment CSV into DuckDB")
    parser.add_argument("--csv", default="C:/Users/user/joern/call_containment.csv",
                       help="Path to call_containment.csv")
    parser.add_argument("--db", default="cpg.duckdb",
                       help="Path to DuckDB database")
    args = parser.parse_args()

    import_csv_to_duckdb(args.csv, args.db)


if __name__ == "__main__":
    main()
