"""
Test CFG Pattern Extractor

Tests the CFG extractor with a small sample to validate:
1. Control structure extraction works
2. Error handling pattern extraction works
3. Lock pattern extraction works
4. Transaction boundary extraction works
5. Complexity metric extraction works
"""

import sys
import json
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.execution.joern_client import JoernClient
from src.extraction.cfg_extractor import CFGPatternExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_extraction_sample(client: JoernClient):
    """Test CFG extraction with small sample."""
    logger.info("="*80)
    logger.info("CFG EXTRACTOR TEST - SMALL SAMPLE")
    logger.info("="*80)

    extractor = CFGPatternExtractor(client)

    results = {}

    # Test 1: Control structures (sample: 10 methods)
    logger.info("\n=== Test 1: Control Structures ===")
    control_patterns = extractor.extract_control_structures(batch_size=10, total_limit=10)
    results['control_structures'] = len(control_patterns)
    if control_patterns:
        logger.info(f"✅ SUCCESS: Extracted {len(control_patterns)} control structures")
        logger.info(f"   Sample: {control_patterns[0].method_name} - {control_patterns[0].description}")
    else:
        logger.warning("⚠️  No control structures extracted")

    # Test 2: Error handling (sample: 10 methods)
    logger.info("\n=== Test 2: Error Handling ===")
    error_patterns = extractor.extract_error_handling(batch_size=10, total_limit=10)
    results['error_handling'] = len(error_patterns)
    if error_patterns:
        logger.info(f"✅ SUCCESS: Extracted {len(error_patterns)} error handling patterns")
        logger.info(f"   Sample: {error_patterns[0].method_name} - {error_patterns[0].description}")
    else:
        logger.warning("⚠️  No error handling patterns extracted")

    # Test 3: Lock patterns (sample: 10 calls)
    logger.info("\n=== Test 3: Lock Patterns ===")
    lock_patterns = extractor.extract_lock_patterns(batch_size=10, total_limit=10)
    results['lock_patterns'] = len(lock_patterns)
    if lock_patterns:
        logger.info(f"✅ SUCCESS: Extracted {len(lock_patterns)} lock patterns")
        logger.info(f"   Sample: {lock_patterns[0].method_name} - {lock_patterns[0].description}")
    else:
        logger.warning("⚠️  No lock patterns extracted")

    # Test 4: Transaction boundaries (sample: 10 calls)
    logger.info("\n=== Test 4: Transaction Boundaries ===")
    txn_patterns = extractor.extract_transaction_boundaries(batch_size=10, total_limit=10)
    results['transaction_boundaries'] = len(txn_patterns)
    if txn_patterns:
        logger.info(f"✅ SUCCESS: Extracted {len(txn_patterns)} transaction patterns")
        logger.info(f"   Sample: {txn_patterns[0].method_name} - {txn_patterns[0].description}")
    else:
        logger.warning("⚠️  No transaction patterns extracted")

    # Test 5: Complexity metrics (sample: 10 methods)
    logger.info("\n=== Test 5: Complexity Metrics ===")
    complexity_metrics = extractor.extract_complexity_metrics(batch_size=10, total_limit=10)
    results['complexity_metrics'] = len(complexity_metrics)
    if complexity_metrics:
        logger.info(f"✅ SUCCESS: Extracted {len(complexity_metrics)} complexity metrics")
        logger.info(f"   Sample: {complexity_metrics[0].method_name} - {complexity_metrics[0].description}")
    else:
        logger.warning("⚠️  No complexity metrics extracted")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    total_patterns = sum(results.values())
    successful_tests = sum(1 for count in results.values() if count > 0)

    for pattern_type, count in results.items():
        status = "✅" if count > 0 else "❌"
        logger.info(f"{status} {pattern_type}: {count} patterns")

    logger.info(f"\nTotal patterns extracted: {total_patterns}")
    logger.info(f"Successful tests: {successful_tests}/5")
    logger.info("="*80)

    # Save sample results
    output_file = "cfg_extractor_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total_patterns': total_patterns,
                'successful_tests': successful_tests,
                'test_results': results
            },
            'samples': {
                'control_structure': control_patterns[0].__dict__ if control_patterns else None,
                'error_handling': error_patterns[0].__dict__ if error_patterns else None,
                'lock_pattern': lock_patterns[0].__dict__ if lock_patterns else None,
                'transaction': txn_patterns[0].__dict__ if txn_patterns else None,
                'complexity': complexity_metrics[0].__dict__ if complexity_metrics else None
            }
        }, f, indent=2, default=str)

    logger.info(f"\nTest results saved to: {output_file}")

    return results


def main():
    """Run CFG extractor tests."""
    logger.info("Initializing Joern client...")
    client = JoernClient("localhost:8080")

    try:
        # Connect to Joern
        logger.info("Connecting to Joern server...")
        client.connect()
        logger.info("✅ Connected to Joern\n")

        # Run tests
        results = test_extraction_sample(client)

        # Check if tests passed
        if sum(results.values()) > 0:
            logger.info("\n✅ CFG extractor is working! Ready for full extraction.")
            return 0
        else:
            logger.error("\n❌ CFG extractor failed to extract patterns. Review queries.")
            return 1

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
