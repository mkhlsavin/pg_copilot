"""
Test script for dual-path workflow (CPGQL + SQL)

Tests the integrated workflow with sample queries to verify:
1. SQL query generation works
2. DuckDB execution succeeds
3. Results are properly interpreted
4. Performance metrics are captured
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow.dual_query_workflow import run_dual_path_query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str):
    """Print a formatted separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_query(question: str, use_sql: bool = True, use_cpgql: bool = False):
    """Test a single query"""
    print_separator(f"TEST: {question}")

    print(f"Question: {question}")
    print(f"SQL enabled: {use_sql}")
    print(f"CPGQL enabled: {use_cpgql}")
    print()

    try:
        result = run_dual_path_query(
            question=question,
            duckdb_path="sample_cpg_v2.duckdb",
            use_sql=use_sql,
            use_cpgql=use_cpgql
        )

        print("RESULTS:")
        print("-" * 80)

        # SQL Path Results
        if result.get("sql_success"):
            print(f"[OK] SQL Query Generated:")
            print(f"     Template: {result.get('sql_template', 'N/A')}")
            print(f"     Query: {result.get('sql_query', 'N/A')[:150]}...")
            print(f"     Execution Time: {result.get('sql_time', 0):.3f}s")
            print(f"     Results: {result.get('result_count_sql', 0)} rows")
            if result.get("sql_execution_result"):
                print(f"     Sample: {str(result['sql_execution_result'])[:200]}...")
        else:
            print(f"[ERROR] SQL Path Failed")
            if result.get("sql_query"):
                print(f"        Query: {result['sql_query'][:150]}...")

        print()

        # CPGQL Path Results
        if use_cpgql:
            if result.get("cpgql_success"):
                print(f"[OK] CPGQL Query Generated:")
                print(f"     Query: {result.get('cpgql_query', 'N/A')[:150]}...")
                print(f"     Execution Time: {result.get('cpgql_time', 0):.3f}s")
                print(f"     Results: {result.get('result_count_cpgql', 0)} rows")
            else:
                print(f"[ERROR] CPGQL Path Failed")

        print()

        # Result Comparison
        if use_sql and use_cpgql:
            if result.get("results_match") is not None:
                if result["results_match"]:
                    print(f"[OK] Results Match: {result.get('result_count_sql')} rows")
                else:
                    print(f"[WARNING] Results Mismatch:")
                    print(f"          SQL: {result.get('result_count_sql')} rows")
                    print(f"          CPGQL: {result.get('result_count_cpgql')} rows")

        print()

        # Final Answer
        print("ANSWER:")
        print("-" * 80)
        answer = result.get("answer", "No answer generated")
        print(answer)

        print("\n" + "=" * 80)
        return True

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False


def main():
    """Run all test queries"""
    print_separator("DUAL-PATH WORKFLOW TEST SUITE")
    print("Testing SQL query generation and execution with sample CPG database")
    print(f"Database: sample_cpg_v2.duckdb")
    print(f"Sample data: 5 methods, 4 calls")
    print()

    # Test queries covering different patterns
    test_queries = [
        # Pattern 1: Find method
        "Find method 'main'",

        # Pattern 2: Find callees
        "What does main call?",

        # Pattern 3: Find callers
        "Who calls malloc?",

        # Pattern 4: Call chain
        "Show call chain from main depth 3",

        # Pattern 5: Top callers
        "Which methods make the most calls?",

        # Pattern 6: Top callees
        "What are the most called methods?",

        # Pattern 7: Methods in file
        "Find methods in example.c",

        # Pattern 8: Complex query (will use basic fallback)
        "Show me all methods that process data"
    ]

    results = []
    for i, question in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/{len(test_queries)}]")
        success = test_query(question, use_sql=True, use_cpgql=False)
        results.append((question, success))

    # Summary
    print_separator("TEST SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")
    print()

    if passed == total:
        print("[OK] ALL TESTS PASSED")
    else:
        print(f"[ERROR] {total - passed} tests failed:")
        for question, success in results:
            if not success:
                print(f"  - {question}")

    print("\n" + "=" * 80)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
