"""
Simple test for dual-path workflow focusing on pattern-matched queries (no LLM).

Tests only queries that use rule-based pattern matching to avoid LLM issues.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow.dual_query_workflow import run_dual_path_query

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(levelname)s - %(message)s'
)


def test_pattern_matched_queries():
    """Test pattern-matched queries that don't require LLM."""

    print("\n" + "="*80)
    print("SIMPLE WORKFLOW TEST - Pattern-Matched Queries Only")
    print("="*80)

    # Test queries that should match patterns (no LLM needed)
    test_cases = [
        ("Find method 'main'", "find_method"),
        ("Find method 'processData'", "find_method"),
        ("Find methods in example.c", "methods_in_file"),
        ("Which methods make the most calls?", "top_callers"),
        ("What are the most called methods?", "top_callees"),
    ]

    passed = 0
    failed = 0

    for question, expected_template in test_cases:
        print(f"\nTEST: {question}")
        print(f"Expected template: {expected_template}")

        try:
            result = run_dual_path_query(
                question=question,
                duckdb_path="sample_cpg_v2.duckdb",
                use_sql=True,
                use_cpgql=False
            )

            if result.get("sql_template") == expected_template:
                print(f"[OK] Template matched: {expected_template}")

                if result.get("sql_success"):
                    count = result.get("result_count_sql", 0)
                    print(f"[OK] SQL execution successful: {count} results")
                    passed += 1
                else:
                    print(f"[ERROR] SQL execution failed")
                    failed += 1
            else:
                actual = result.get("sql_template", "none")
                print(f"[ERROR] Template mismatch: expected {expected_template}, got {actual}")
                failed += 1

        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = test_pattern_matched_queries()
    sys.exit(0 if success else 1)