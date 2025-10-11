#!/usr/bin/env python3
"""Test opening workspace in Joern server using proper import syntax."""

import sys
import json
sys.path.insert(0, 'C:/Users/user/pg_copilot/rag_cpgql')

from cpgqls_client import import_code_query

def test_import_workspace():
    """Test importing workspace using Joern's import functions."""

    print("=" * 80)
    print("Testing Workspace Import via cpgqls_client")
    print("=" * 80)

    # Method 1: Use import_code_query helper from cpgqls_client
    print("\n1. Using import_code_query helper...")
    try:
        result = import_code_query(
            "localhost:8080",
            "C:/Users/user/joern/workspace/pg17_full.cpg",
            "pg17_full"
        )
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_import_workspace()
