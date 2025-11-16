"""Test SQL Query Generator for DuckDB CPG"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.generation.sql_query_generator import SQLQueryGenerator


def test_sql_query_generator():
    """Test the SQL query generator with various question patterns"""

    print("=" * 80)
    print("Testing SQL Query Generator for DuckDB CPG")
    print("=" * 80)

    generator = SQLQueryGenerator()

    # Test questions covering different patterns
    test_cases = [
        {
            "question": "What does 'main' call?",
            "expected_template": "find_callees",
            "description": "Find callees pattern"
        },
        {
            "question": "Who calls 'malloc'?",
            "expected_template": "find_callers",
            "description": "Find callers pattern"
        },
        {
            "question": "Show me the call chain from 'processData' with depth 3",
            "expected_template": "call_chain",
            "description": "Call chain pattern"
        },
        {
            "question": "Which methods make the most calls?",
            "expected_template": "top_callers",
            "description": "Top callers pattern"
        },
        {
            "question": "What are the most frequently called methods?",
            "expected_template": "top_callees",
            "description": "Top callees pattern"
        },
        {
            "question": "Find methods in server.c",
            "expected_template": "methods_in_file",
            "description": "Methods in file pattern"
        },
        {
            "question": "Show data flow for 'userInput' variable",
            "expected_template": "data_flow",
            "description": "Data flow pattern"
        },
        {
            "question": "Find method 'executeQuery'",
            "expected_template": "find_method",
            "description": "Find method pattern"
        }
    ]

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Question: {test_case['question']}")
        print("-" * 80)

        try:
            result = generator.generate_query(test_case['question'])

            # Check if correct template was used
            if result['template'] == test_case['expected_template']:
                print(f"   [OK] Template: {result['template']}")
                print(f"   [OK] Params: {result['params']}")
                passed += 1
            else:
                print(f"   [FAIL] Expected: {test_case['expected_template']}, Got: {result['template']}")
                failed += 1

            # Show generated SQL (truncated)
            sql_preview = result['query'][:200].replace('\n', ' ').strip()
            print(f"   SQL: {sql_preview}...")

        except Exception as e:
            print(f"   [ERROR] {e}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    # Test template listing
    print("\nAvailable Templates:")
    for template_name in generator.list_templates():
        print(f"  - {template_name}")

    # Test examples
    print(f"\nFew-shot Examples: {len(generator.get_examples())} examples loaded")

    return failed == 0


if __name__ == "__main__":
    success = test_sql_query_generator()
    sys.exit(0 if success else 1)
