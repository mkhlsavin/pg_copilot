"""Test loading existing CPG from workspace."""
from cpgqls_client import CPGQLSClient

def test_load_cpg():
    """Test loading existing CPG."""
    client = CPGQLSClient("localhost:8080")

    print("1. Testing loadCpg with full path...")
    result = client.execute('loadCpg("C:/Users/user/joern/workspace/pg17_full.cpg")')
    print(f"LoadCpg result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:800]}")

    print("\n2. Testing cpg after loadCpg...")
    result = client.execute('cpg.method.name.l.take(3)')
    print(f"Query result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:500]}")

    print("\n3. Try importing scala library...")
    result = client.execute('import better.files._')
    print(f"Import result: success={result.get('success')}")
    print(f"Stdout: {result.get('stdout', '')[:200]}")

if __name__ == "__main__":
    test_load_cpg()
