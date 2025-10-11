"""Test console functions with different prefixes."""
from cpgqls_client import CPGQLSClient

def test_console():
    """Test different ways to call console functions."""
    client = CPGQLSClient("localhost:8080")

    tests = [
        ('console', 'console'),
        ('JoernConsole.open', 'JoernConsole.open("pg17_full.cpg")'),
        ('io.joern.console.open', 'io.joern.console.open("pg17_full.cpg")'),
        ('Run.open', 'Run.open("pg17_full.cpg")'),
        ('importCpg', 'importCpg("C:/Users/user/joern/workspace/pg17_full.cpg")'),
        ('loadCpg from path', 'io.shiftleft.codepropertygraph.cpgloading.CpgLoader.load("C:/Users/user/joern/workspace/pg17_full.cpg")'),
    ]

    for name, cmd in tests:
        print(f"\n{name}: {cmd}")
        result = client.execute(cmd)
        stdout = result.get('stdout', '')
        if 'Not found' in stdout or '[E' in stdout:
            print(f"  [FAILED] {stdout[:200]}")
        else:
            print(f"  [OK] {stdout[:300]}")

if __name__ == "__main__":
    test_console()
