#!/usr/bin/env python3
"""Test available commands in Joern server."""

import sys
sys.path.insert(0, 'C:/Users/user/pg_copilot/rag_cpgql')

from cpgqls_client import CPGQLSClient

def test_commands():
    """Test various commands to see what's available."""

    client = CPGQLSClient("localhost:8080")

    print("=" * 80)
    print("Testing Available Commands")
    print("=" * 80)

    # Try importCpg
    print("\n1. Testing importCpg command...")
    result = client.execute('importCpg("C:/Users/user/joern/workspace/pg17_full.cpg")')
    print(f"   Response: {result.get('stdout', 'No stdout')[:200]}")

    # Try loading workspace differently
    print("\n2. Testing workspace load via path...")
    result = client.execute('loadCpg("pg17_full.cpg")')
    print(f"   Response: {result.get('stdout', 'No stdout')[:200]}")

    # Try using io.shiftleft.codepropertygraph
    print("\n3. Testing direct CPG access...")
    result = client.execute('io.shiftleft.codepropertygraph.Cpg')
    print(f"   Response: {result.get('stdout', 'No stdout')[:200]}")

    # Check if there's a help command
    print("\n4. Testing help command...")
    result = client.execute('help')
    print(f"   Response: {result.get('stdout', 'No stdout')[:200]}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_commands()
