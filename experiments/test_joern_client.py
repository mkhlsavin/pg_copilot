"""Test Joern client connection and query execution."""
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_joern_connection():
    """Test connection to Joern server."""
    print("=" * 80)
    print("JOERN CLIENT CONNECTION TEST")
    print("=" * 80)

    # Initialize client
    print("\n1. Initializing JoernClient...")
    client = JoernClient(server_endpoint="localhost:8080")

    # Load PostgreSQL CPG
    print("\n2. Loading PostgreSQL CPG...")
    cpg_path = "C:/Users/user/joern/workspace/postgres-REL_17_6.cpg"
    load_result = client.execute_query(f'importCpg("{cpg_path}")')

    if load_result['success']:
        print(f"[OK] CPG loaded successfully")
    else:
        print(f"[WARNING] Could not load CPG: {load_result['error']}")
        print("  (Continuing anyway - testing connection...)")

    # Connect
    print("\n3. Testing connection with simple query...")
    connected = client.connect()

    if not connected:
        print("[FAIL] Failed to connect to Joern server")
        print("\nTo start Joern server:")
        print("  cd C:/Users/user/joern")
        print("  ./joern.bat --server --server-host localhost --server-port 8080")
        return False

    print("[OK] Connected successfully")

    # Get CPG statistics
    print("\n4. Getting CPG statistics...")
    stats = client.get_cpg_stats()

    print("\nCPG Statistics:")
    print("-" * 40)
    for key, value in stats.items():
        print(f"  {key:15s}: {value:,}")

    # Test sample queries
    print("\n5. Testing sample queries...")
    print("-" * 80)

    test_queries = [
        ("Count methods", "cpg.method.name.l.size"),
        ("Get method names (first 5)", "cpg.method.name.l.take(5)"),
        ("Count files", "cpg.file.name.l.size"),
        ("Get file names (first 3)", "cpg.file.name.l.take(3)"),
        ("Find functions with 'lock' in name", 'cpg.method.name(".*lock.*").name.l'),
    ]

    for description, query in test_queries:
        print(f"\n{description}:")
        print(f"  Query: {query}")

        result = client.execute_query(query)

        if result['success']:
            result_str = result['result']
            # Truncate long results
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            print(f"  Result: {result_str}")
            print(f"  Time: {result['execution_time']:.3f}s")
        else:
            print(f"  [FAIL] Error: {result['error']}")

    # Close connection
    print("\n5. Closing connection...")
    client.close()
    print("[OK] Connection closed")

    return True


def test_context_manager():
    """Test context manager usage."""
    print("\n" + "=" * 80)
    print("CONTEXT MANAGER TEST")
    print("=" * 80)

    print("\nUsing JoernClient as context manager...")

    try:
        with JoernClient() as client:
            result = client.execute_query("cpg.method.name.l.size")
            if result['success']:
                print(f"[OK] Query executed: {result['result']} methods found")
                return True
            else:
                print(f"[FAIL] Query failed: {result['error']}")
                return False
    except Exception as e:
        print(f"[FAIL] Context manager failed: {e}")
        return False


if __name__ == "__main__":
    success1 = test_joern_connection()

    if success1:
        success2 = test_context_manager()

        if success1 and success2:
            print("\n" + "=" * 80)
            print("[OK] ALL TESTS PASSED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("[WARNING]  SOME TESTS FAILED")
            print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("[FAIL] CONNECTION FAILED - Cannot run further tests")
        print("=" * 80)
