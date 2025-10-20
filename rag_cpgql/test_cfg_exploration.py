"""
Test Joern CFG (Control Flow Graph) Capabilities

This script explores Joern's CFG API to understand:
1. How to access control flow information
2. Available CFG traversals (.cfgFirst, .cfgNext, etc.)
3. CFG pattern extraction (lock patterns, error handling, etc.)
4. Performance characteristics of CFG queries

Phase 2 Goal: Extract execution flow patterns to explain "how" code works
"""

import sys
import json
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.execution.joern_client import JoernClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_cfg_basic_access(client: JoernClient):
    """Test basic CFG access for a simple function."""
    logger.info("\n=== Test 1: Basic CFG Access ===")

    # Test if we can access CFG for a method
    query = """
    cpg.method.name("brinbeginscan").take(1)
      .map { m =>
        val entry = m.cfgFirst.code.headOption.getOrElse("NO_ENTRY")
        val numNodes = m.cfgNode.size
        s"Method: ${m.name}, Entry: ${entry}, CFG Nodes: ${numNodes}"
      }.l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_traversal(client: JoernClient):
    """Test CFG traversal to get execution flow."""
    logger.info("\n=== Test 2: CFG Traversal ===")

    # Get first 10 CFG nodes for a method
    query = """
    cpg.method.name("brinbeginscan").take(1)
      .cfgFirst
      .repeat(_.cfgNext)(_.emit.times(10))
      .map(node => s"${node.order}: ${node.code.take(50)}")
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Found CFG nodes")
        logger.info(f"Result preview: {str(result['result'])[:500]}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_call_extraction(client: JoernClient):
    """Extract function calls in CFG order."""
    logger.info("\n=== Test 3: CFG Call Extraction ===")

    # Get function calls in execution order
    query = """
    cpg.method.name("heap_fetch").take(1)
      .cfgFirst
      .repeat(_.cfgNext)(_.emit.times(20))
      .where(_.isCall)
      .map(call => s"${call.order}: ${call.name}")
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Extracted CFG calls")
        logger.info(f"Calls: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_control_structures(client: JoernClient):
    """Test extraction of control structures (if, while, etc.)."""
    logger.info("\n=== Test 4: Control Structure Extraction ===")

    # Find if statements and their conditions
    query = """
    cpg.method.name("HeapTupleSatisfiesMVCC").take(1)
      .controlStructure
      .map { cs =>
        val csType = cs.controlStructureType
        val condition = cs.condition.code.headOption.getOrElse("NO_COND")
        s"Type: ${csType}, Condition: ${condition}"
      }
      .take(5)
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Extracted control structures")
        logger.info(f"Structures: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_error_handling_pattern(client: JoernClient):
    """Test detection of error handling patterns."""
    logger.info("\n=== Test 5: Error Handling Pattern Detection ===")

    # Find error checks (NULL checks, elog calls, etc.)
    query = """
    cpg.method.name(".*brin.*").take(3)
      .controlStructure.controlStructureType("IF")
      .where(_.condition.code(".*== NULL.*"))
      .map { ifStmt =>
        val method = ifStmt.method.name.head
        val condition = ifStmt.condition.code.head
        val thenBranch = ifStmt.cfgNext.code.take(50).headOption.getOrElse("NO_THEN")
        s"Method: ${method}, Check: ${condition}, Then: ${thenBranch}"
      }
      .take(5)
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Found error handling patterns")
        logger.info(f"Patterns: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_lock_pattern(client: JoernClient):
    """Test detection of lock acquisition patterns."""
    logger.info("\n=== Test 6: Lock Pattern Detection ===")

    # Find lock acquisition and release
    query = """
    cpg.call.name("LockBuffer").take(3)
      .map { lockCall =>
        val method = lockCall.method.name.head
        val lockArg = lockCall.argument.code.l.mkString(", ")

        // Try to find corresponding unlock
        val unlockCalls = lockCall.method.call.name("UnlockBuffer").size

        s"Method: ${method}, Lock: ${lockArg}, Unlocks: ${unlockCalls}"
      }
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Found lock patterns")
        logger.info(f"Locks: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_branching_paths(client: JoernClient):
    """Test extraction of branching paths."""
    logger.info("\n=== Test 7: Branching Path Analysis ===")

    # Analyze branching in a method
    query = """
    cpg.method.name("heap_vacuum_rel").take(1)
      .map { m =>
        val totalNodes = m.cfgNode.size
        val calls = m.call.size
        val controlStructures = m.controlStructure.size
        val returns = m.methodReturn.size

        s"CFG Nodes: ${totalNodes}, Calls: ${calls}, Control: ${controlStructures}, Returns: ${returns}"
      }
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Analyzed branching")
        logger.info(f"Analysis: {result['result']}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def test_cfg_execution_sequence(client: JoernClient):
    """Test extracting execution sequence with call details."""
    logger.info("\n=== Test 8: Execution Sequence Extraction ===")

    # Get detailed execution sequence
    query = """
    cpg.method.name("brin_doinsert").take(1)
      .cfgFirst
      .repeat(_.cfgNext)(_.emit.times(15))
      .map { node =>
        val nodeType = node.label
        val code = node.code.take(40)
        val order = node.order
        s"${order}|${nodeType}|${code}"
      }
      .l
    """

    logger.info(f"Query: {query}")
    result = client.execute_query(query)

    if result['success']:
        logger.info(f"✅ SUCCESS: Extracted execution sequence")
        lines = str(result['result']).split(',')
        for i, line in enumerate(lines[:10], 1):
            logger.info(f"  {i}. {line.strip()}")
    else:
        logger.error(f"❌ FAILED: {result.get('error')}")

    return result


def main():
    """Run all CFG exploration tests."""
    logger.info("="*80)
    logger.info("JOERN CFG CAPABILITIES EXPLORATION")
    logger.info("="*80)
    logger.info("Phase 2: Control Flow Graph Integration")
    logger.info("Goal: Extract execution flow patterns to improve answer quality")
    logger.info("="*80)

    # Initialize Joern client
    client = JoernClient("localhost:8080")

    try:
        # Connect to Joern
        logger.info("\nConnecting to Joern server...")
        client.connect()
        logger.info("✅ Connected to Joern")

        # Run tests
        results = {}

        results['basic_access'] = test_cfg_basic_access(client)
        results['traversal'] = test_cfg_traversal(client)
        results['call_extraction'] = test_cfg_call_extraction(client)
        results['control_structures'] = test_cfg_control_structures(client)
        results['error_handling'] = test_cfg_error_handling_pattern(client)
        results['lock_patterns'] = test_cfg_lock_pattern(client)
        results['branching'] = test_cfg_branching_paths(client)
        results['execution_sequence'] = test_cfg_execution_sequence(client)

        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)

        successful_tests = sum(1 for r in results.values() if r.get('success', False))
        total_tests = len(results)

        logger.info(f"Successful tests: {successful_tests}/{total_tests}")
        logger.info(f"Success rate: {successful_tests/total_tests*100:.1f}%")

        # Save results
        output_file = "cfg_exploration_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'successful': successful_tests,
                    'success_rate': successful_tests/total_tests
                },
                'results': results
            }, f, indent=2)

        logger.info(f"\nResults saved to: {output_file}")
        logger.info("="*80)

        # Recommendations
        logger.info("\nRECOMMENDATIONS FOR PHASE 2:")
        if successful_tests >= total_tests * 0.75:
            logger.info("✅ CFG API is functional - proceed with implementation")
            logger.info("   Next steps:")
            logger.info("   1. Design CFG extraction schema")
            logger.info("   2. Implement CFG pattern extractors")
            logger.info("   3. Create execution-pattern enrichment tags")
        else:
            logger.info("⚠️  CFG API has limitations - investigate failures")
            logger.info("   Review failed queries and adjust approach")

    except Exception as e:
        logger.error(f"❌ Exploration failed: {e}", exc_info=True)

    finally:
        logger.info("\nCFG exploration complete")


if __name__ == '__main__':
    main()
