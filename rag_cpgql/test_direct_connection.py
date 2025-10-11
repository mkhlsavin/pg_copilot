"""Direct test of cpgqls-client to debug import and open issues."""
import sys
from cpgqls_client import CPGQLSClient

def test_commands():
    """Test different command sequences."""
    client = CPGQLSClient("localhost:8080")

    print("1. Testing basic import...")
    result = client.execute('import io.joern.console._')
    print(f"Import result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")
    print(f"Stderr: {result.get('stderr', '')[:500]}")

    print("\n2. Testing alternative import...")
    result = client.execute('import $ivy.`io.joern::console:2.0.0`')
    print(f"Import result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

    print("\n3. Testing importCode...")
    result = client.execute('importCode("C:/Users/user/joern/import/postgres-REL_17_6")')
    print(f"ImportCode result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

    print("\n4. Testing cpg after importCode...")
    result = client.execute('cpg.method.name.l.take(3)')
    print(f"Query result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

if __name__ == "__main__":
    test_commands()
