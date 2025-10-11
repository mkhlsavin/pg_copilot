#!/usr/bin/env python3
"""Check actual file paths in CPG."""

import sys
sys.path.insert(0, 'src')

from execution.joern_client import JoernClient

client = JoernClient('localhost', 8080)

print("="*80)
print("[CPG PATH ANALYSIS]")
print("="*80)

# Get total count
result = client.execute_query('cpg.file.name.l.size')
if result.get('success'):
    total = result['result'][0]
    print(f"\nTotal files: {total}")

# Get first file as example
result = client.execute_query('cpg.file.name.l.headOption')
if result.get('success') and result.get('result'):
    path = result['result'][0]
    print(f"\nExample file path:")
    print(f"{path}")

    # Normalize
    normalized = path.replace(chr(92), '/')  # chr(92) is backslash
    print(f"\nNormalized:")
    print(f"{normalized}")

    # Check patterns
    print(f"\nContains:")
    patterns = ['postgres', 'mingw', 'workspace', 'src/backend', 'REL_17']
    for p in patterns:
        found = p in normalized
        print(f"  {p:20s}: {'YES' if found else 'NO'}")

# Count PostgreSQL vs MinGW files
print("\n" + "="*80)
print("[FILE COUNTS]")
print("="*80)

query1 = """cpg.file.filter { f =>
    val path = f.name.replace('\\\\', '/')
    path.contains("postgres")
}.name.l.size"""

result = client.execute_query(query1)
if result.get('success'):
    pg_count = result['result'][0]
    print(f"Files with 'postgres': {pg_count}")

query2 = """cpg.file.filter { f =>
    val path = f.name.replace('\\\\', '/')
    path.contains("mingw")
}.name.l.size"""

result = client.execute_query(query2)
if result.get('success'):
    mingw_count = result['result'][0]
    print(f"Files with 'mingw':    {mingw_count}")

# Show examples
print("\n" + "="*80)
print("[EXAMPLE POSTGRES FILES]")
print("="*80)

query3 = """cpg.file.filter { f =>
    val path = f.name.replace('\\\\', '/')
    path.contains("postgres")
}.name.l.take(3)"""

result = client.execute_query(query3)
if result.get('success'):
    for i, path in enumerate(result['result'], 1):
        # Show last 70 chars
        display = path if len(path) <= 70 else "..." + path[-67:]
        print(f"{i}. {display}")

print("\n" + "="*80)
print("[EXAMPLE MINGW FILES]")
print("="*80)

query4 = """cpg.file.filter { f =>
    val path = f.name.replace('\\\\', '/')
    path.contains("mingw")
}.name.l.take(3)"""

result = client.execute_query(query4)
if result.get('success'):
    for i, path in enumerate(result['result'], 1):
        display = path if len(path) <= 70 else "..." + path[-67:]
        print(f"{i}. {display}")

print("\n" + "="*80)
