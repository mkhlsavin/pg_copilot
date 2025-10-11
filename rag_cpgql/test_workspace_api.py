"""Test using workspace commands that user verified in REPL."""
from cpgqls_client import CPGQLSClient

def test_workspace():
    """Test workspace API commands."""
    client = CPGQLSClient("localhost:8080")

    print("1. List workspace projects...")
    result = client.execute('workspace.projects')
    print(f"Result: success={result.get('success')}")
    stdout = result.get('stdout', '')
    print(f"Stdout ({len(stdout)} chars): {stdout[:1000]}")

    print("\n2. Get active project...")
    result = client.execute('workspace.getActiveProject')
    print(f"Result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

    print("\n3. Set active project to 'pg17_full.cpg'...")
    result = client.execute('workspace.setActiveProject("pg17_full.cpg")')
    print(f"Result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

    print("\n4. Open the project...")
    result = client.execute('open')
    print(f"Result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:1000]}")

    print("\n5. Query cpg after opening...")
    result = client.execute('cpg.method.name.l.take(3)')
    print(f"Result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:1000]}")

if __name__ == "__main__":
    test_workspace()
