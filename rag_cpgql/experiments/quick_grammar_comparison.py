"""Quick comparison of grammar vs no-grammar query generation."""
import sys
import logging
from pathlib import Path
import json
import io
from datetime import datetime
import time

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

print("\n" + "="*80)
print("Quick Grammar Comparison Test (3 queries only)")
print("="*80 + "\n")

# Only 3 test questions for quick comparison
test_questions = [
    "Find all functions related to vacuum operations",
    "Find buffer pool management functions",
    "Find all hash table implementations"
]

try:
    # Initialize LLM once
    print("Loading LLMxCPG-Q model...")
    llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
    print("Model loaded!\n")

    # Test WITH grammar
    print("="*80)
    print("TEST 1: WITH GRAMMAR")
    print("="*80 + "\n")

    gen_with = CPGQLGenerator(llm, use_grammar=True)
    results_with = []

    for i, q in enumerate(test_questions, 1):
        print(f"[{i}/3] {q}")
        start = time.time()
        query = gen_with.generate_query(q, max_tokens=150)
        elapsed = time.time() - start
        is_valid, error = gen_with.validate_query(query)
        print(f"    Query: {query}")
        print(f"    Valid: {is_valid}, Time: {elapsed:.2f}s\n")
        results_with.append({
            'question': q,
            'query': query,
            'valid': is_valid,
            'time': elapsed
        })

    # Test WITHOUT grammar
    print("="*80)
    print("TEST 2: WITHOUT GRAMMAR")
    print("="*80 + "\n")

    gen_without = CPGQLGenerator(llm, use_grammar=False)
    results_without = []

    for i, q in enumerate(test_questions, 1):
        print(f"[{i}/3] {q}")
        start = time.time()
        query = gen_without.generate_query(q, max_tokens=150)
        elapsed = time.time() - start
        is_valid, error = gen_without.validate_query(query)
        print(f"    Query: {query}")
        print(f"    Valid: {is_valid}, Time: {elapsed:.2f}s\n")
        results_without.append({
            'question': q,
            'query': query,
            'valid': is_valid,
            'time': elapsed
        })

    # Summary
    print("="*80)
    print("COMPARISON SUMMARY")
    print("="*80 + "\n")

    valid_with = sum(1 for r in results_with if r['valid'])
    valid_without = sum(1 for r in results_without if r['valid'])

    avg_time_with = sum(r['time'] for r in results_with) / len(results_with)
    avg_time_without = sum(r['time'] for r in results_without) / len(results_without)

    print(f"WITH GRAMMAR:")
    print(f"  Valid: {valid_with}/3")
    print(f"  Avg time: {avg_time_with:.2f}s")
    print(f"  Example: {results_with[0]['query']}\n")

    print(f"WITHOUT GRAMMAR:")
    print(f"  Valid: {valid_without}/3")
    print(f"  Avg time: {avg_time_without:.2f}s")
    print(f"  Example: {results_without[0]['query']}\n")

    # Save comparison
    output_file = Path(__file__).parent.parent / "results" / "grammar_comparison.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'with_grammar': results_with,
            'without_grammar': results_without,
            'summary': {
                'valid_with': valid_with,
                'valid_without': valid_without,
                'avg_time_with': avg_time_with,
                'avg_time_without': avg_time_without
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_file}")
    print("\n" + "="*80 + "\n")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
