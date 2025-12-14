#!/usr/bin/env python3
"""Debug CPG database structure."""

import duckdb

conn = duckdb.connect('cpg.duckdb', read_only=True)

# Check analyze.c calls with forward slash
print('=== nodes_call with analyze in path ===')
result = conn.execute("""
    SELECT nc.filename, COUNT(*)
    FROM nodes_call nc
    WHERE nc.filename LIKE '%analyze%'
    GROUP BY nc.filename
""").fetchall()
if not result:
    print('  (empty)')
for r in result:
    print(f'  {r[0]}: {r[1]}')

# Count files in each table
print()
print('=== Unique files in each table ===')
result = conn.execute("""
    SELECT COUNT(DISTINCT filename) FROM nodes_method
""").fetchone()
print(f'  nodes_method distinct files: {result[0]}')

result = conn.execute("""
    SELECT COUNT(DISTINCT filename) FROM nodes_call
""").fetchone()
print(f'  nodes_call distinct files: {result[0]}')

# Check what backend directories have calls
print()
print('=== Backend directories with calls ===')
result = conn.execute("""
    SELECT
        CASE
            WHEN filename LIKE 'backend/access/%' THEN 'backend/access'
            WHEN filename LIKE 'backend/catalog/%' THEN 'backend/catalog'
            WHEN filename LIKE 'backend/commands/%' THEN 'backend/commands'
            WHEN filename LIKE 'backend/executor/%' THEN 'backend/executor'
            WHEN filename LIKE 'backend/optimizer/%' THEN 'backend/optimizer'
            WHEN filename LIKE 'backend/parser/%' THEN 'backend/parser'
            WHEN filename LIKE 'backend/utils/%' THEN 'backend/utils'
            ELSE 'other'
        END as dir,
        COUNT(*) as cnt
    FROM nodes_call
    GROUP BY dir
    ORDER BY cnt DESC
""").fetchall()
for r in result:
    print(f'  {r[0]}: {r[1]:,}')

# Check nodes_call for commands directory
print()
print('=== nodes_call in backend/commands ===')
result = conn.execute("""
    SELECT filename, COUNT(*)
    FROM nodes_call
    WHERE filename LIKE 'backend/commands%'
    GROUP BY filename
    ORDER BY COUNT(*) DESC
    LIMIT 10
""").fetchall()
if not result:
    print('  (empty - no calls from commands directory)')
for r in result:
    print(f'  {r[0]}: {r[1]}')

# Check what's in nodes_method for commands
print()
print('=== nodes_method in backend/commands ===')
result = conn.execute(r"""
    SELECT filename, COUNT(*)
    FROM nodes_method
    WHERE filename LIKE '%commands%'
    GROUP BY filename
    ORDER BY COUNT(*) DESC
    LIMIT 10
""").fetchall()
for r in result:
    print(f'  {r[0]}: {r[1]}')

conn.close()
