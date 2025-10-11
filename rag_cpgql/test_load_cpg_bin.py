"""Test loading cpg.bin file directly."""
from cpgqls_client import CPGQLSClient

def test_load_bin():
    """Test loading cpg.bin."""
    client = CPGQLSClient("localhost:8080")

    print("1. Load cpg.bin file...")
    result = client.execute('val cpg = io.shiftleft.codepropertygraph.cpgloading.CpgLoader.load("C:/Users/user/joern/workspace/pg17_full.cpg/cpg.bin")')
    stdout = result.get('stdout', '')
    print(f"Result: success={result.get('success')}")
    print(f"Stdout: {stdout[:2000]}")

    if 'error' in stdout.lower() or 'exception' in stdout.lower():
        print("\n[ERROR] Load failed")
        return False

    print("\n2. Query CPG after loading...")
    result = client.execute('cpg.method.name.l.take(3)')
    stdout = result.get('stdout', '')
    print(f"Stdout: {stdout[:1000]}")

    if 'List(' in stdout:
        print("\n[SUCCESS] CPG loaded!")
        return True
    else:
        print("\n[FAILED] CPG not queryable")
        return False

if __name__ == "__main__":
    success = test_load_bin()
    exit(0 if success else 1)
