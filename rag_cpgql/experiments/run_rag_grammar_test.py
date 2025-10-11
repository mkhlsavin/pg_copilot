"""Test RAG pipeline with grammar-constrained generation."""
import sys
import logging
from pathlib import Path
import json
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator
from retrieval.vector_store import VectorStore
from execution.joern_client import JoernClient
from rag_pipeline_grammar import RAGCPGQLPipelineGrammar

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_grammar_rag_pipeline():
    """Test full RAG pipeline with grammar constraints."""

    print("\n" + "="*80)
    print("RAG-CPGQL Pipeline with Grammar Constraints - Test")
    print("="*80 + "\n")

    # Test questions (code-specific)
    test_questions = [
        {
            'question': 'Find all methods that use strcpy',
            'answer': 'Methods that use strcpy can introduce buffer overflow vulnerabilities',
            'expected_query': 'cpg.method.callOut.name("strcpy").l'
        },
        {
            'question': 'Find all buffer copy operations',
            'answer': 'Buffer copy operations include memcpy, strcpy, strncpy',
            'expected_query': 'cpg.call.name(".*cpy").l'
        },
        {
            'question': 'List all methods in the codebase',
            'answer': 'The codebase contains many methods across different files',
            'expected_query': 'cpg.method.name.l'
        },
    ]

    try:
        # 1. Initialize LLM with LLMxCPG-Q
        print("1. Initializing LLMxCPG-Q model...")
        llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
        print("   ✅ Model loaded\n")

        # 2. Initialize mock vector store (for testing without database)
        print("2. Initializing vector store (mock)...")
        vector_store = create_mock_vector_store()
        print("   ✅ Vector store ready\n")

        # 3. Initialize Joern client (mock for testing)
        print("3. Initializing Joern client (mock)...")
        joern_client = create_mock_joern_client()
        print("   ✅ Joern client ready\n")

        # 4. Create enhanced RAG pipeline
        print("4. Creating grammar-enhanced RAG pipeline...")
        pipeline = RAGCPGQLPipelineGrammar(
            llm=llm,
            vector_store=vector_store,
            joern_client=joern_client,
            top_k_qa=3,
            top_k_cpgql=5,
            use_grammar=True,
            use_enrichment=True
        )
        print()

        # 5. Test query generation (without full pipeline)
        print("5. Testing query generation:\n")
        print("-" * 80)

        results = []
        for i, item in enumerate(test_questions, 1):
            question = item['question']
            expected = item.get('expected_query', 'N/A')

            print(f"\nTest {i}/{len(test_questions)}:")
            print(f"  Question:  {question}")

            try:
                # Generate query
                query, is_valid, error = pipeline.generate_cpgql_query(question)

                print(f"  Generated: {query}")
                print(f"  Expected:  {expected}")
                print(f"  Valid:     {'✅ YES' if is_valid else f'❌ NO - {error}'}")

                # Analyze quality
                matches_expected = (query.replace(' ', '') == expected.replace(' ', ''))
                quality = 'PERFECT' if matches_expected else 'DIFFERENT'

                print(f"  Quality:   {quality}")

                results.append({
                    'question': question,
                    'query': query,
                    'expected': expected,
                    'valid': is_valid,
                    'matches': matches_expected
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    'question': question,
                    'query': None,
                    'valid': False,
                    'matches': False
                })

        # Summary
        print("\n" + "="*80)
        print("Summary")
        print("="*80 + "\n")

        valid_count = sum(1 for r in results if r['valid'])
        match_count = sum(1 for r in results if r['matches'])

        print(f"Valid queries:    {valid_count}/{len(results)} ({valid_count/len(results)*100:.1f}%)")
        print(f"Perfect matches:  {match_count}/{len(results)} ({match_count/len(results)*100:.1f}%)")
        print(f"Grammar enabled:  YES")
        print(f"Enrichment hints: YES")
        print(f"Model:            LLMxCPG-Q")

        # Save results
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "rag_grammar_test.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': '2025-10-10',
                'pipeline': 'RAG with Grammar',
                'grammar_enabled': True,
                'enrichment_enabled': True,
                'model': 'LLMxCPG-Q',
                'total_questions': len(results),
                'valid_queries': valid_count,
                'perfect_matches': match_count,
                'results': results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {output_file}")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")

        if valid_count == len(results):
            print("✅ SUCCESS: All queries valid")
            return 0
        else:
            print("⚠️  WARNING: Some queries invalid")
            return 1

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


def create_mock_vector_store():
    """Create mock vector store for testing."""

    class MockVectorStore:
        def search_similar_qa(self, question, k=3):
            """Return mock similar Q&A pairs."""
            return [
                {
                    'question': 'How to find unsafe string operations?',
                    'answer': 'Use cpg.call.name("strcpy").l to find strcpy calls',
                    'similarity': 0.85
                },
                {
                    'question': 'Find buffer copy functions',
                    'answer': 'Buffer operations: strcpy, memcpy, strncpy',
                    'similarity': 0.78
                },
                {
                    'question': 'List all methods',
                    'answer': 'Use cpg.method.name.l to list methods',
                    'similarity': 0.65
                }
            ]

        def search_similar_cpgql(self, question, k=5):
            """Return mock CPGQL examples."""
            return [
                {
                    'description': 'Find strcpy calls',
                    'query': 'cpg.call.name("strcpy").l',
                    'similarity': 0.90
                },
                {
                    'description': 'Find memcpy calls',
                    'query': 'cpg.call.name("memcpy").l',
                    'similarity': 0.85
                },
                {
                    'description': 'Find all methods',
                    'query': 'cpg.method.name.l',
                    'similarity': 0.75
                },
                {
                    'description': 'Find buffer operations',
                    'query': 'cpg.call.name(".*cpy").l',
                    'similarity': 0.80
                },
                {
                    'description': 'Find method parameters',
                    'query': 'cpg.method.parameter.name.l',
                    'similarity': 0.60
                }
            ]

    return MockVectorStore()


def create_mock_joern_client():
    """Create mock Joern client for testing."""

    class MockJoernClient:
        def execute_query(self, query):
            """Return mock execution result."""
            return {
                'success': True,
                'results': {
                    'stdout': f'Query executed: {query}',
                    'response': ['result1', 'result2', 'result3']
                }
            }

    return MockJoernClient()


if __name__ == "__main__":
    exit_code = test_grammar_rag_pipeline()
    sys.exit(exit_code)
