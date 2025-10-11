#!/usr/bin/env python3
"""Test workspace API commands."""

import sys
sys.path.insert(0, 'C:/Users/user/pg_copilot/rag_cpgql')

from cpgqls_client import CPGQLSClient

def test_workspace_api():
    """Test workspace management commands."""

    client = CPGQLSClient("localhost:8080")

    print("=" * 80)
    print("Testing Workspace API Commands")
    print("=" * 80)

    # Test 1: Check workspace command
    print("\n1. Testing 'workspace' command...")
    result = client.execute("workspace")
    print(f"   Success: {result.get('success')}")
    print(f"   Output: {result.get('stdout', 'No output')[:500]}")

    # Test 2: Set active project
    print("\n2. Testing 'workspace.setActiveProject'...")
    result = client.execute('workspace.setActiveProject("pg17_full.cpg")')
    print(f"   Success: {result.get('success')}")
    print(f"   Output: {result.get('stdout', 'No output')[:500]}")

    # Test 3: Check project command
    print("\n3. Testing 'project' command...")
    result = client.execute("project")
    print(f"   Success: {result.get('success')}")
    print(f"   Output: {result.get('stdout', 'No output')[:500]}")

    # Test 4: Try cpg query after setting project
    print("\n4. Testing 'cpg.file.size' after setting project...")
    result = client.execute("cpg.file.size")
    print(f"   Success: {result.get('success')}")
    print(f"   Output: {result.get('stdout', 'No output')[:500]}")

    # Test 5: Try workspace.getPath
    print("\n5. Testing 'workspace.getPath'...")
    result = client.execute("workspace.getPath")
    print(f"   Success: {result.get('success')}")
    print(f"   Output: {result.get('stdout', 'No output')[:500]}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_workspace_api()
