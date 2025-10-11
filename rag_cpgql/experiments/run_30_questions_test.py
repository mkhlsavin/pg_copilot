"""Test RAG pipeline with grammar-constrained generation on 30 questions from test dataset."""
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
from retrieval.vector_store import VectorStore
from execution.joern_client import JoernClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_test_questions(test_file, num_questions=30):
    """Load first N questions from test dataset."""
    questions = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_questions:
                break
            data = json.loads(line)
            questions.append({
                'id': i + 1,
                'question': data['question'],
                'reference_answer': data.get('answer', ''),
                'difficulty': data.get('difficulty', 'unknown'),
                'topics': data.get('topics', [])
            })
    return questions


def test_30_questions():
    """Test RAG pipeline on 30 questions from test dataset."""

    print("\n" + "="*80)
    print("RAG-CPGQL Pipeline: 30 Questions Test")
    print("="*80 + "\n")

    # Load test questions
    test_file = Path(__file__).parent.parent / "data" / "test_split.jsonl"
    print(f"Loading test questions from: {test_file}")

    questions = load_test_questions(test_file, num_questions=30)
    print(f"Loaded {len(questions)} questions\n")

    try:
        # 1. Initialize LLM with LLMxCPG-Q
        print("1. Initializing LLMxCPG-Q model...")
        start_time = time.time()
        llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
        load_time = time.time() - start_time
        print(f"   Model loaded in {load_time:.2f}s\n")

        # 2. Initialize CPGQL generator with grammar
        print("2. Initializing CPGQL generator with grammar...")
        generator = CPGQLGenerator(llm, use_grammar=True)
        print("   Generator ready\n")

        # 3. Mock components for now (will integrate real ones later)
        print("3. Using mock components for retrieval and execution...")
        print("   (Real vector store and Joern server will be integrated later)\n")

        # 4. Test query generation
        print("4. Testing query generation:\n")
        print("-" * 80)

        results = []
        valid_count = 0
        total_gen_time = 0

        for i, item in enumerate(questions, 1):
            question = item['question']

            print(f"\n[{i}/{len(questions)}] Question: {question[:80]}...")

            try:
                # Generate query
                start = time.time()
                query, is_valid, error = generator.generate_query(question)
                gen_time = time.time() - start
                total_gen_time += gen_time

                print(f"    Generated: {query}")
                print(f"    Valid:     {'YES' if is_valid else f'NO - {error}'}")
                print(f"    Time:      {gen_time:.2f}s")

                if is_valid:
                    valid_count += 1

                results.append({
                    'id': item['id'],
                    'question': question,
                    'query': query,
                    'valid': is_valid,
                    'error': error if not is_valid else None,
                    'generation_time': gen_time,
                    'difficulty': item['difficulty'],
                    'topics': item['topics']
                })

            except Exception as e:
                print(f"    ERROR: {e}")
                results.append({
                    'id': item['id'],
                    'question': question,
                    'query': None,
                    'valid': False,
                    'error': str(e),
                    'generation_time': 0,
                    'difficulty': item['difficulty'],
                    'topics': item['topics']
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
        print(f"Grammar enabled:     YES")
        print(f"Model:               LLMxCPG-Q")

        # Analyze by difficulty
        if any(r.get('difficulty') for r in results):
            print("\n" + "-"*80)
            print("Analysis by Difficulty:")
            print("-"*80)

            difficulties = {}
            for r in results:
                diff = r.get('difficulty', 'unknown')
                if diff not in difficulties:
                    difficulties[diff] = {'total': 0, 'valid': 0}
                difficulties[diff]['total'] += 1
                if r['valid']:
                    difficulties[diff]['valid'] += 1

            for diff, stats in sorted(difficulties.items()):
                rate = (stats['valid'] / stats['total'] * 100) if stats['total'] > 0 else 0
                print(f"  {diff.capitalize():12} {stats['valid']}/{stats['total']} ({rate:.1f}%)")

        # Save results
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "test_30_questions_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'test_name': '30 Questions Test',
                'pipeline': 'RAG with Grammar',
                'grammar_enabled': True,
                'model': 'LLMxCPG-Q',
                'model_load_time': load_time,
                'total_questions': len(results),
                'valid_queries': valid_count,
                'validity_rate': validity_rate,
                'avg_generation_time': avg_gen_time,
                'total_generation_time': total_gen_time,
                'results': results,
                'summary_by_difficulty': difficulties if any(r.get('difficulty') for r in results) else {}
            }, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")

        if validity_rate >= 90:
            print("SUCCESS: Validity rate >= 90%")
            return 0
        elif validity_rate >= 80:
            print("PARTIAL SUCCESS: Validity rate >= 80%")
            return 0
        else:
            print("WARNING: Validity rate < 80%")
            return 1

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = test_30_questions()
    sys.exit(exit_code)
