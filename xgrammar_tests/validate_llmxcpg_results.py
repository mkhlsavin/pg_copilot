#!/usr/bin/env python3
"""
Validate LLMxCPG-Q extended test results.
"""

import json
import re
from pathlib import Path

def clean_query(query):
    """Clean up generated query."""
    # Remove spaces around dots
    cleaned = re.sub(r'\s*\.\s*', '.', query)
    # Remove spaces around parentheses
    cleaned = re.sub(r'\s*\(\s*', '(', cleaned)
    cleaned = re.sub(r'\s*\)\s*', ')', cleaned)
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Remove quotes around keywords
    cleaned = re.sub(r'"(method|call|controlledBy|code|name|parameter|signature|caller|argument|typeFullName|location|file|lineNumber|start|controlStructure|returns|isStatic|isPublic|fullName)"', r'\1', cleaned)
    # Fix trailing issues
    cleaned = re.sub(r'\s*"\s*$', '', cleaned)
    cleaned = re.sub(r'\(\s*"[a-z]?\s*$', '', cleaned)
    cleaned = re.sub(r'\s+l\s+c$', '.l', cleaned)
    cleaned = re.sub(r'\s+l\s*"?$', '.l', cleaned)
    cleaned = re.sub(r'\s+c$', '', cleaned)
    # Remove incomplete trailing chains
    if not cleaned.endswith(('.l', '.toList', '.head')):
        # Try to add .l if query looks mostly complete
        if cleaned.count('.') >= 2:
            cleaned += '.l'
    return cleaned.strip()

def validate_query(query, example):
    """Validate CPGQL query syntax."""
    issues = []

    # Must start with cpg
    if not query.startswith('cpg'):
        issues.append("Must start with 'cpg'")

    # Should have dots for chaining
    if '.' not in query:
        issues.append("Missing property chain dots")

    # Should end with execution directive
    if not (query.endswith('.l') or query.endswith('.toList') or query.endswith('.head')):
        issues.append("Missing execution directive")

    # Check for incomplete strings
    if '("' in query and not '")' in query:
        issues.append("Incomplete string literal")

    # Check for stray quotes
    if query.count('"') % 2 != 0:
        issues.append("Unmatched quotes")

    is_valid = len(issues) == 0
    return is_valid, issues

def analyze_results():
    """Analyze LLMxCPG-Q results."""
    input_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/llmxcpg_extended_results.json")
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/llmxcpg_validated_results.json")

    print("="*70)
    print("LLMxCPG-Q Extended Test - Validation Results")
    print("="*70)
    print()

    with open(input_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    validated = []
    stats = {
        "total": len(queries),
        "valid_raw": 0,
        "valid_cleaned": 0,
        "simple_queries": 0,
        "complex_queries": 0,
        "avg_length": 0,
        "max_length": 0
    }

    for item in queries:
        original = item['query']
        cleaned = clean_query(original)
        example = item['example']

        is_valid_raw, issues_raw = validate_query(original, example)
        is_valid_cleaned, issues_cleaned = validate_query(cleaned, example)

        # Count dots to measure complexity
        complexity = cleaned.count('.')
        if complexity <= 3:
            stats["simple_queries"] += 1
        else:
            stats["complex_queries"] += 1

        stats["avg_length"] += len(cleaned)
        stats["max_length"] = max(stats["max_length"], len(cleaned))

        if is_valid_raw:
            stats["valid_raw"] += 1
        if is_valid_cleaned:
            stats["valid_cleaned"] += 1

        validated.append({
            "id": item['id'],
            "prompt": item['prompt'],
            "example": example,
            "original_query": original,
            "cleaned_query": cleaned,
            "is_valid_raw": is_valid_raw,
            "is_valid_cleaned": is_valid_cleaned,
            "issues_raw": issues_raw,
            "issues_cleaned": issues_cleaned,
            "complexity": complexity,
            "length": len(cleaned)
        })

        print(f"Query {item['id']}: {item['prompt']}")
        print(f"  Example:   {example}")
        print(f"  Original:  {original[:80]}{'...' if len(original) > 80 else ''}")
        print(f"  Cleaned:   {cleaned[:80]}{'...' if len(cleaned) > 80 else ''}")
        print(f"  Valid (raw/cleaned): {is_valid_raw}/{is_valid_cleaned}")
        if issues_cleaned:
            print(f"  Issues: {', '.join(issues_cleaned)}")
        print(f"  Complexity: {complexity} dots, {len(cleaned)} chars")
        print()

    # Calculate average
    stats["avg_length"] = stats["avg_length"] // stats["total"]

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "statistics": stats,
            "queries": validated
        }, f, indent=2, ensure_ascii=False)

    # Print summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total queries:        {stats['total']}")
    print(f"Valid (raw):          {stats['valid_raw']}/{stats['total']} ({stats['valid_raw']*100//stats['total']}%)")
    print(f"Valid (cleaned):      {stats['valid_cleaned']}/{stats['total']} ({stats['valid_cleaned']*100//stats['total']}%)")
    print(f"Simple queries (≤3):  {stats['simple_queries']}")
    print(f"Complex queries (>3): {stats['complex_queries']}")
    print(f"Average length:       {stats['avg_length']} chars")
    print(f"Max length:           {stats['max_length']} chars")
    print()
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    analyze_results()
