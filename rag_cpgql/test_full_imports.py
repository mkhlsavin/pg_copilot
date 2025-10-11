"""Test with all necessary imports for full CPG querying."""
from cpgqls_client import CPGQLSClient

def test_full_setup():
    """Test complete setup with all imports."""
    client = CPGQLSClient("localhost:8080")

    print("1. Load CPG...")
    result = client.execute('val cpg = io.shiftleft.codepropertygraph.cpgloading.CpgLoader.load("C:/Users/user/joern/workspace/pg17_full.cpg/cpg.bin")')
    print(f"CPG: {result.get('stdout', '')[:80]}")

    print("\n2. Import all semantic CPG language...")
    result = client.execute('import io.shiftleft.semanticcpg.language._')
    print(f"Imported: {result.get('success')}")

    print("\n3. Query method names...")
    result = client.execute('cpg.method.name.l.take(5)')
    stdout = result.get('stdout', '')
    print(f"Methods:\n{stdout[:800]}")

    print("\n4. Query enrichment tags...")
    result = client.execute('cpg.method.tag.name.l.take(10)')
    stdout = result.get('stdout', '')
    print(f"Tags:\n{stdout[:800]}")

    print("\n5. Query cyclomatic complexity...")
    result = client.execute('cpg.method.tag.nameExact("cyclomatic-complexity").value.l.take(5)')
    stdout = result.get('stdout', '')
    print(f"Complexity values:\n{stdout[:500]}")

    print("\n6. Test file query...")
    result = client.execute('cpg.file.name.l.take(3)')
    stdout = result.get('stdout', '')
    print(f"Files:\n{stdout[:500]}")

    if 'List(' in stdout and 'res' in stdout:
        print("\n[SUCCESS] Full CPG setup complete!")
        return True
    else:
        print("\n[PARTIAL] Some queries may not work")
        return False

if __name__ == "__main__":
    success = test_full_setup()
    exit(0 if success else 1)
