#!/usr/bin/env python3
"""Test CPG workspace loading via Joern server."""

import sys
sys.path.insert(0, 'C:/Users/user/pg_copilot/rag_cpgql')

from cpgqls_client import CPGQLSClient

def test_cpg_loading():
    """Test loading CPG workspace through Joern server."""

    client = CPGQLSClient("localhost:8080")

    print("=" * 80)
    print("Testing CPG Workspace Loading")
    print("=" * 80)

    # Step 1: Open workspace
    print("\n1. Opening workspace 'pg17_full.cpg'...")
    result = client.execute('open("pg17_full.cpg")')
    print(f"   Response: {result}")

    # Step 2: Test basic CPG query
    print("\n2. Testing basic CPG query: cpg.file.size")
    result = client.execute("cpg.file.size")
    print(f"   Response: {result}")

    # Step 3: Test method count
    print("\n3. Testing method count: cpg.method.size")
    result = client.execute("cpg.method.size")
    print(f"   Response: {result}")

    # Step 4: Test call count
    print("\n4. Testing call count: cpg.call.size")
    result = client.execute("cpg.call.size")
    print(f"   Response: {result}")

    # Step 5: Sample query with tags
    print("\n5. Testing enrichment tags: cpg.tag.name.dedup.sorted.l.take(10)")
    result = client.execute("cpg.tag.name.dedup.sorted.l.take(10)")
    print(f"   Response: {result}")

    # Step 6: Test workspace command
    print("\n6. Testing workspace command")
    result = client.execute("workspace")
    print(f"   Response: {result}")

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    test_cpg_loading()
