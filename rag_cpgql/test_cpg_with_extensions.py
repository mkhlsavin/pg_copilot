"""Test loading CPG and importing extension methods."""
from cpgqls_client import CPGQLSClient

def test_cpg_full():
    """Test complete CPG loading and querying."""
    client = CPGQLSClient("localhost:8080")

    print("1. Load cpg.bin...")
    result = client.execute('val cpg = io.shiftleft.codepropertygraph.cpgloading.CpgLoader.load("C:/Users/user/joern/workspace/pg17_full.cpg/cpg.bin")')
    print(f"CPG loaded: {result.get('stdout', '')[:100]}")

    print("\n2. Import extension methods...")
    result = client.execute('import io.shiftleft.codepropertygraph.generated.language.toGeneratedNodeStarters')
    print(f"Extensions imported: {result.get('success')}")

    print("\n3. Query method names...")
    result = client.execute('cpg.method.name.l.take(5)')
    stdout = result.get('stdout', '')
    print(f"Methods: {stdout[:500]}")

    print("\n4. Query method count...")
    result = client.execute('cpg.method.size')
    stdout = result.get('stdout', '')
    print(f"Method count: {stdout[:200]}")

    print("\n5. Test enrichment tags...")
    result = client.execute('cpg.method.tag.name.l.take(10)')
    stdout = result.get('stdout', '')
    print(f"Tags: {stdout[:500]}")

    if 'List(' in stdout:
        print("\n[SUCCESS] CPG fully loaded and queryable with enrichments!")
        return True
    else:
        print("\n[PARTIAL] CPG loaded but enrichments may not be available")
        return False

if __name__ == "__main__":
    success = test_cpg_full()
    exit(0 if success else 1)
