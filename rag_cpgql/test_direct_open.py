"""Test direct open() command as user confirmed works."""
from cpgqls_client import CPGQLSClient
import json

def test_direct_open():
    """Test direct open command."""
    client = CPGQLSClient("localhost:8080")

    print("1. Try open with project name from project.json...")
    result = client.execute('open("pg17_full.cpg")')
    print(f"Result: success={result.get('success')}")
    print(f"UUID: {result.get('uuid')}")
    stdout = result.get('stdout', '')
    print(f"Stdout ({len(stdout)} chars):")
    print(stdout[:2000])

    # Check if there's an error
    if '[E' in stdout or 'error' in stdout.lower():
        print("\n[ERROR] Open command failed")
        return False

    print("\n2. Test query after open...")
    result = client.execute('cpg.method.name.l.take(3)')
    print(f"Result: success={result.get('success')}")
    stdout = result.get('stdout', '')
    print(f"Stdout: {stdout[:1000]}")

    if 'List(' in stdout or 'res' in stdout:
        print("\n[SUCCESS] CPG loaded and queryable!")
        return True
    else:
        print("\n[FAILED] CPG not loaded")
        return False

if __name__ == "__main__":
    success = test_direct_open()
    exit(0 if success else 1)
