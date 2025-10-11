#!/usr/bin/env python3
"""Test HTTP-based feature mapping."""
import sys
sys.path.insert(0, '.')

from feature_mapping.joern_http_client import JoernHTTPClient
from feature_mapping.feature_matrix import fetch_feature_matrix
from feature_mapping.heuristics import expand_tokens

# Initialize HTTP client
client = JoernHTTPClient(server_url="http://localhost:8080")

# Test 1: Simple query
print("=" * 80)
print("TEST 1: Simple CPG query")
print("=" * 80)
try:
    result = client.execute_query("cpg.method.name.l.take(5)")
    print(f"Success: {result.get('success')}")
    print(f"Output preview: {result.get('stdout', '')[:200]}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Find candidates for MERGE feature
print("\n" + "=" * 80)
print("TEST 2: Find candidates for MERGE feature")
print("=" * 80)
try:
    tokens = ["merge"]  # Simple token list
    print(f"Tokens: {tokens}")

    candidates = client.find_candidates(
        feature_name="MERGE",
        tokens=tokens,
        max_per_kind=10
    )

    print(f"\nFound {len(candidates)} candidates:")
    for i, cand in enumerate(candidates[:10], 1):
        print(f"{i}. [{cand.kind}] {cand.name[:60]} (score: {cand.score:.3f})")
        if cand.filename:
            print(f"   File: {cand.filename}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TESTS COMPLETE")
print("=" * 80)
