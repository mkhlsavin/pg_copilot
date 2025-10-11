"""Test CPG loading and query execution on PostgreSQL CPG."""
import sys
from pathlib import Path
import io

# Fix Unicode encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_cpgql.src.execution.joern_client import JoernClient
import logging

logging.basicConfig(level=logging.WARNING)  # Reduce log clutter

def main():
    print("=" * 80)
    print("TESTING CPGQL QUERIES ON POSTGRESQL CPG")
    print("=" * 80)

    client = JoernClient(server_endpoint="localhost:8080")

    # Initialize connection by creating CPGQLSClient
    print("\n1. Initializing connection...")
    from cpgqls_client import CPGQLSClient
    client.client = CPGQLSClient("localhost:8080")
    print("[OK] Connection initialized")

    # Try to open the workspace (Joern uses workspace names, not full paths)
    print("\n2. Loading PostgreSQL CPG workspace...")
    result = client.execute_query('open("pg17_full")')

    if result['success']:
        print(f"[OK] Workspace opened")
        print(f"     Output: {result['result'][:200] if result['result'] else 'No output'}...")
    else:
        print(f"[WARNING] Could not open workspace: {result['error'][:200]}")
        print("\n  Trying alternative: importCpg with full path...")

        # Try with full path
        result2 = client.execute_query('importCpg("C:/Users/user/joern/workspace/pg17_full.cpg")')
        if result2['success']:
            print(f"[OK] CPG imported via full path")
        else:
            print(f"[FAIL] Could not import CPG: {result2['error'][:300]}")
            print("\nNote: You may need to manually load the CPG in Joern REPL first.")
            return

    # Test basic queries
    print("\n2. Testing CPGQL queries...")
    print("-" * 80)

    test_queries = [
        ("Count all methods", "cpg.method.size"),
        ("Count method names", "cpg.method.name.l.size"),
        ("Get first 3 method names", "cpg.method.name.l.take(3)"),
        ("Count files", "cpg.file.size"),
        ("Find lock-related functions", 'cpg.method.name(".*[Ll]ock.*").name.l.size'),
        ("Find malloc calls", 'cpg.call.name(".*malloc").size'),
    ]

    results = []
    for description, query in test_queries:
        print(f"\n{description}:")
        print(f"  Query: {query}")

        result = client.execute_query(query)

        if result['success']:
            output = result['result'].strip()
            # Clean up ANSI color codes
            if '[31m' not in output and '[0m' not in output and 'Error' not in output:
                print(f"  [OK] Result: {output}")
                print(f"       Time: {result['execution_time']:.3f}s")
                results.append((description, True, output))
            else:
                # Still an error despite success flag
                error_msg = output.split('\n')[0] if '\n' in output else output[:100]
                print(f"  [FAIL] Error: {error_msg}")
                results.append((description, False, None))
        else:
            error_msg = result['error'][:200] if result['error'] else "Unknown error"
            print(f"  [FAIL] Error: {error_msg}")
            results.append((description, False, None))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\nQueries executed: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")

    if successful > 0:
        print("\n[SUCCESS] Client is working! CPG queries can be executed.")
    else:
        print("\n[FAIL] No queries succeeded - CPG may not be loaded properly.")

    client.close()

if __name__ == "__main__":
    main()
