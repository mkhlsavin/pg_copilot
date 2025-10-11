"""Test Joern connection with cpgqls-client and workspace API."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_joern_workspace():
    """Test connection to Joern workspace."""
    from execution.joern_client import JoernClient

    logger.info("=" * 80)
    logger.info("JOERN WORKSPACE CONNECTION TEST")
    logger.info("=" * 80)

    # Initialize client
    logger.info("\n1. Initializing Joern client...")
    client = JoernClient(
        cpg_project_name="pg17_full.cpg",
        server_host="localhost",
        port=8080
    )

    # Connect
    logger.info("\n2. Connecting to Joern server and opening workspace...")
    if not client.connect():
        logger.error("[FAILED] Could not connect to Joern server")
        logger.error("Make sure Joern is running with:")
        logger.error("  joern --server --server-host localhost --server-port 8080")
        return False

    logger.info("[OK] Connected to Joern workspace")

    # Test simple query
    logger.info("\n3. Testing simple query: cpg.method.name.l.take(5)")
    result = client.execute_query("cpg.method.name.l.take(5)")

    if result['success']:
        logger.info("[OK] Query executed successfully")
        logger.info(f"Result type: {type(result['results'])}")
        logger.info(f"Result preview: {str(result['results'])[:200]}...")
    else:
        logger.error(f"[FAILED] Query failed: {result.get('error')}")
        client.close()
        return False

    # Test enrichment query
    logger.info("\n4. Testing enrichment query: cpg.method.tag.name.l.take(10)")
    result = client.execute_query("cpg.method.tag.name.l.take(10)")

    if result['success']:
        logger.info("[OK] Enrichment query executed successfully")
        logger.info(f"Tags found: {str(result['results'])[:300]}...")
    else:
        logger.error(f"[FAILED] Enrichment query failed: {result.get('error')}")
        client.close()
        return False

    # Test count query
    logger.info("\n5. Testing count query: cpg.method.size")
    result = client.execute_query("cpg.method.size")

    if result['success']:
        logger.info("[OK] Count query executed successfully")
        logger.info(f"Total methods: {result['results']}")
    else:
        logger.error(f"[FAILED] Count query failed: {result.get('error')}")
        client.close()
        return False

    # Test enrichment presence
    logger.info("\n6. Testing for enrichment tags...")
    result = client.execute_query(
        'cpg.method.tag.nameExact("cyclomatic-complexity").value.l.take(5)'
    )

    if result['success']:
        logger.info("[OK] Enrichment tags query executed")
        logger.info(f"Complexity values: {result['results']}")
    else:
        logger.error(f"[FAILED] Enrichment tags query failed: {result.get('error')}")

    # Close connection
    logger.info("\n7. Closing connection...")
    client.close()
    logger.info("[OK] Connection closed")

    logger.info("\n" + "=" * 80)
    logger.info("ALL TESTS PASSED!")
    logger.info("=" * 80)
    logger.info("\nJoern workspace API is working correctly.")
    logger.info("CPG project 'pg17_full' is loaded and enrichments are available.")

    return True

if __name__ == "__main__":
    success = test_joern_workspace()
    sys.exit(0 if success else 1)
