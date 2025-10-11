#!/usr/bin/env python3
"""
Validate generated CPGQL queries by cleaning them and checking syntax.
"""

import json
import re
from pathlib import Path

def clean_query(query):
    """Clean up generated query by removing extra spaces."""
    # Remove spaces around dots
    cleaned = re.sub(r'\s*\.\s*', '.', query)
    # Remove spaces around parentheses
    cleaned = re.sub(r'\s*\(\s*', '(', cleaned)
    cleaned = re.sub(r'\s*\)\s*', ')', cleaned)
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Remove quotes around keywords if present
    cleaned = re.sub(r'"(method|call|controlledBy|code|name)"', r'\1', cleaned)
    # Remove trailing quotes and incomplete parts
    cleaned = re.sub(r'\s*"\s*$', '', cleaned)
    # Remove incomplete string literals
    cleaned = re.sub(r'\(\s*"[a-z]\s*$', '', cleaned)
    cleaned = re.sub(r'\s+l\s+c$', '.l', cleaned)
    cleaned = re.sub(r'\s+l\s*"?$', '.l', cleaned)
    return cleaned.strip()

def validate_query(query):
    """Basic validation of CPGQL query syntax."""
    # Must start with cpg
    if not query.startswith('cpg'):
        return False, "Must start with 'cpg'"

    # Should have dots for chaining
    if '.' not in query:
        return False, "Missing property chain dots"

    # Should end with execution directive (.l, .toList, etc.)
    if not (query.endswith('.l') or query.endswith('.toList') or query.endswith('.head')):
        return False, "Missing execution directive (.l, .toList, etc.)"

    return True, "Valid"

def main():
    input_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/grammar_generated_queries_v2.json")
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/validated_queries_v2.json")

    print("="*70)
    print("CPGQL Query Validation and Cleanup")
    print("="*70)
    print()

    # Load generated queries
    with open(input_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    validated = []

    for item in queries:
        original = item['query']
        cleaned = clean_query(original)
        is_valid, message = validate_query(cleaned)

        validated.append({
            "id": item['id'],
            "prompt": item['prompt'],
            "original_query": original,
            "cleaned_query": cleaned,
            "is_valid": is_valid,
            "validation_message": message
        })

        print(f"Query {item['id']}: {item['prompt']}")
        print(f"  Original:  {original}")
        print(f"  Cleaned:   {cleaned}")
        print(f"  Valid:     {is_valid} - {message}")
        print()

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)

    valid_count = sum(1 for v in validated if v['is_valid'])
    print(f"Results: {valid_count}/{len(validated)} queries are valid")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    main()
