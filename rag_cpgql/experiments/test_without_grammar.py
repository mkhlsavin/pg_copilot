"""Test query generation without grammar constraints."""
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_without_grammar():
    """Test query generation without grammar constraints to check quality."""

    print("\n" + "="*80)
    print("CPGQL Generation Test: Grammar DISABLED")
    print("="*80 + "\n")

    # Test questions - varied difficulty and concepts
    test_questions = [
        "How does PostgreSQL handle memory management in shared buffers?",
        "Find all functions related to vacuum operations",
        "What are the main components of the WAL (Write-Ahead Log) system?",
        "Find buffer pool management functions",
        "How does PostgreSQL implement MVCC for transaction isolation?",
        "Find all hash table implementations in the codebase",
        "What functions handle query planning and optimization?",
        "Find all functions that use spinlocks for synchronization",
        "How does PostgreSQL handle parallel query execution?",
        "Find all functions related to B-tree index operations"
    ]

    try:
        # 1. Initialize LLM with LLMxCPG-Q
        print("1. Initializing LLMxCPG-Q model...")
        start_time = time.time()
        llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
        load_time = time.time() - start_time
        print(f"   Model loaded in {load_time:.2f}s\n")

        # 2. Initialize CPGQL generator WITHOUT grammar
        print("2. Initializing CPGQL generator WITHOUT grammar...")
        generator = CPGQLGenerator(llm, use_grammar=False)
        print(f"   Grammar status: {'ENABLED' if generator.use_grammar else 'DISABLED'}")
        print(f"   Generator ready\n")

        # 3. Test query generation
        print("3. Testing query generation:\n")
        print("-" * 80)

        results = []
        total_gen_time = 0
        valid_count = 0

        for i, question in enumerate(test_questions, 1):
            print(f"\n[{i}/{len(test_questions)}] Question: {question}")

            try:
                # Generate query
                start = time.time()
                query = generator.generate_query(question)
                gen_time = time.time() - start
                total_gen_time += gen_time

                # Validate
                is_valid, error = generator.validate_query(query)

                print(f"    Generated: {query}")
                print(f"    Valid:     {'YES' if is_valid else f'NO - {error}'}")
                print(f"    Time:      {gen_time:.2f}s")

                if is_valid:
                    valid_count += 1

                results.append({
                    'id': i,
                    'question': question,
                    'query': query,
                    'valid': is_valid,
                    'error': error if not is_valid else None,
                    'generation_time': gen_time
                })

            except Exception as e:
                print(f"    ERROR: {e}")
                results.append({
                    'id': i,
                    'question': question,
                    'query': None,
                    'valid': False,
                    'error': str(e),
                    'generation_time': 0
                })

        # Summary
        print("\n" + "="*80)
        print("Test Summary")
        print("="*80 + "\n")

        avg_gen_time = total_gen_time / len(results) if results else 0
        validity_rate = (valid_count / len(results) * 100) if results else 0

        print(f"Total questions:     {len(results)}")
        print(f"Valid queries:       {valid_count}/{len(results)} ({validity_rate:.1f}%)")
        print(f"Invalid queries:     {len(results) - valid_count}/{len(results)}")
        print(f"Avg generation time: {avg_gen_time:.2f}s")
        print(f"Total time:          {total_gen_time:.2f}s")
        print(f"Grammar enabled:     NO")
        print(f"Model:               LLMxCPG-Q")

        # Analyze query complexity
        print("\n" + "-"*80)
        print("Query Analysis:")
        print("-"*80)

        for r in results:
            if r['valid'] and r['query']:
                query = r['query']
                # Count traversal steps
                steps = query.count('.')
                # Check for filters/predicates
                has_filters = 'where' in query.lower() or 'filter' in query.lower()
                has_regex = '.*' in query or '\\.' in query
                has_tags = '.tag' in query

                print(f"\nQ: {r['question'][:60]}...")
                print(f"   Query: {query}")
                print(f"   Steps: {steps}, Filters: {has_filters}, Regex: {has_regex}, Tags: {has_tags}")

        # Save results
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "test_without_grammar_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'test_name': 'Query Generation Without Grammar Test',
                'grammar_enabled': False,
                'model': 'LLMxCPG-Q',
                'model_load_time': load_time,
                'total_questions': len(results),
                'valid_queries': valid_count,
                'validity_rate': validity_rate,
                'avg_generation_time': avg_gen_time,
                'total_generation_time': total_gen_time,
                'results': results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n\nResults saved to: {output_file}")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")

        # Return code based on validity rate
        if validity_rate >= 70:
            print("SUCCESS: Validity rate >= 70% (acceptable without grammar)")
            return 0
        else:
            print("WARNING: Validity rate < 70% - grammar may be needed")
            return 1

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = test_without_grammar()
    sys.exit(exit_code)
