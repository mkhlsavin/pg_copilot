"""Simple include edge export from existing CPG data.

Since Joern C/C++ frontend doesn't directly expose preprocessor #include directives,
we'll infer include relationships from:
1. File naming conventions (e.g., executor.c includes executor.h)
2. Cross-file function references (if A.c calls functions defined in B.h/B.c)
"""

import sys
import re
import duckdb
import logging

sys.path.insert(0, 'src')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def infer_includes_from_calls():
    """
    Infer include relationships from cross-file function calls.

    If file A calls a function defined in file B, we infer that A includes B's header.
    """
    logger.info("Inferring include relationships from cross-file calls...")

    conn = duckdb.connect('cpg.duckdb')

    # Create edges_include table if not exists
    conn.execute("""
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

    # Clear existing inferred includes
    conn.execute("DELETE FROM edges_include WHERE src IS NULL")

    # Query: Find cross-file call relationships
    # If A.c calls function F defined in B.c, infer A.c includes B.h
    infer_query = """
        WITH cross_file_calls AS (
            SELECT DISTINCT
                cc.filename AS caller_file,
                m.filename AS callee_file
            FROM call_containment cc
            JOIN nodes_method m ON cc.callee_name = m.name
            WHERE cc.filename != m.filename
              AND cc.filename IS NOT NULL
              AND m.filename IS NOT NULL
              AND cc.filename != ''
              AND m.filename != ''
        )
        SELECT
            caller_file,
            callee_file,
            -- Infer header name from source file
            CASE
                WHEN callee_file LIKE '%.c' THEN REPLACE(callee_file, '.c', '.h')
                ELSE callee_file
            END AS inferred_header
        FROM cross_file_calls
        ORDER BY caller_file, callee_file
        LIMIT 10000
    """

    results = conn.execute(infer_query).fetchall()
    logger.info(f"Found {len(results)} cross-file call relationships")

    # Insert inferred includes
    total = 0
    seen = set()

    for idx, (caller_file, callee_file, inferred_header) in enumerate(results):
        key = (caller_file, inferred_header)
        if key in seen:
            continue
        seen.add(key)

        # Extract just the filename for include_path
        include_path = inferred_header.split('/')[-1] if '/' in inferred_header else inferred_header

        try:
            conn.execute("""
                INSERT INTO edges_include
                (id, src, dst, include_path, is_system, line_number, src_filename, dst_filename)
                VALUES (?, NULL, NULL, ?, FALSE, NULL, ?, ?)
            """, (total + 1, include_path, caller_file, inferred_header))
            total += 1
        except Exception as e:
            if 'PRIMARY KEY' not in str(e) and 'UNIQUE' not in str(e):
                logger.debug(f"Insert error: {e}")

    logger.info(f"Inserted {total} inferred include relationships")

    # Also add common header includes based on PostgreSQL conventions
    add_common_includes(conn, total)

    # Final count
    final_count = conn.execute("SELECT COUNT(*) FROM edges_include").fetchone()[0]
    logger.info(f"Total include edges in database: {final_count}")

    # Show sample
    sample = conn.execute("""
        SELECT src_filename, include_path, dst_filename
        FROM edges_include
        LIMIT 10
    """).fetchall()
    logger.info("Sample include relationships:")
    for src, inc, dst in sample:
        logger.info(f"  {src} -> {inc}")

    conn.close()
    return total


def add_common_includes(conn, start_id):
    """Add common PostgreSQL include patterns."""

    logger.info("Adding common PostgreSQL include patterns...")

    # Get all C source files
    c_files = conn.execute("""
        SELECT DISTINCT filename FROM nodes_method
        WHERE filename LIKE '%.c'
        LIMIT 1000
    """).fetchall()

    # Common PostgreSQL headers that most files include
    common_headers = [
        'postgres.h',
        'fmgr.h',
        'utils/elog.h',
        'utils/palloc.h',
        'miscadmin.h',
    ]

    idx = start_id
    for (c_file,) in c_files:
        for header in common_headers:
            idx += 1
            try:
                conn.execute("""
                    INSERT INTO edges_include
                    (id, include_path, is_system, src_filename, dst_filename)
                    VALUES (?, ?, FALSE, ?, ?)
                    ON CONFLICT DO NOTHING
                """, (idx, header, c_file, header))
            except:
                pass

    logger.info(f"Added common header patterns")


if __name__ == '__main__':
    infer_includes_from_calls()
