#!/usr/bin/env python3
"""Direct test of Joern client to diagnose cpg context loss."""

import sys
sys.path.insert(0, 'src')

from execution.joern_client import JoernClient
import time

client = JoernClient('localhost', 8080)

print("="*80)
print("JOERN CLIENT DIRECT TEST")
print("="*80)

# Connect
print("\n[1] Connecting...")
if not client.connect():
    print("FAILED to connect!")
    sys.exit(1)
print("✅ Connected")

# Test 1: Check CPG
print("\n[2] Testing CPG access...")
result1 = client.execute_query('cpg')
print(f"Result 1: {result1}")

# Test 2: Run first query
print("\n[3] Running first query...")
query1 = 'cpg.method.name.l.take(3)'
result2 = client.execute_query(query1)
print(f"Success: {result2.get('success')}")
if result2.get('success'):
    print(f"Results preview: {str(result2.get('results'))[:200]}")
else:
    print(f"Error: {result2.get('error')}")

time.sleep(1)

# Test 3: Check CPG again
print("\n[4] Checking CPG after first query...")
result3 = client.execute_query('cpg')
print(f"Result 3: {result3}")

# Test 4: Run second query
print("\n[5] Running second query...")
query2 = 'cpg.file.name.l.take(3)'
result4 = client.execute_query(query2)
print(f"Success: {result4.get('success')}")
if result4.get('success'):
    print(f"Results preview: {str(result4.get('results'))[:200]}")
else:
    print(f"Error: {result4.get('error')}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

client.close()
