"""Test grammar-constrained CPGQL generation integration."""
import sys
import logging
from pathlib import Path
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_grammar_integration():
    """Test grammar-constrained generation with LLMxCPG-Q."""

    print("\n" + "="*80)
    print("Grammar-Constrained CPGQL Generation - Integration Test")
    print("="*80 + "\n")

    # Test questions
    test_questions = [
        "Find all methods in the code",
        "Find calls to strcpy function",
        "Find all method parameters",
        "Find methods that call memcpy",
        "Find buffer operations with memcpy"
    ]

    try:
        # Initialize LLM with LLMxCPG-Q model
        print("1. Loading LLMxCPG-Q model...")
        llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
        print("   ✅ Model loaded\n")

        # Initialize CPGQL generator with grammar
        print("2. Loading CPGQL grammar...")
        generator = CPGQLGenerator(llm, use_grammar=True)

        if generator.use_grammar:
            print("   ✅ Grammar loaded and enabled\n")
        else:
            print("   ⚠️  Grammar loading failed, using fallback\n")

        # Test query generation
        print("3. Testing query generation:\n")
        print("-" * 80)

        results = []
        for i, question in enumerate(test_questions, 1):
            print(f"\nTest {i}/5: {question}")
            print("-" * 80)

            try:
                # Generate query
                query = generator.generate_query(question, max_tokens=300, temperature=0.6)

                # Validate query
                is_valid, error = generator.validate_query(query)

                # Display result
                print(f"Generated: {query}")
                print(f"Valid:     {'✅ YES' if is_valid else f'❌ NO - {error}'}")

                results.append({
                    'question': question,
                    'query': query,
                    'valid': is_valid,
                    'error': error
                })

            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append({
                    'question': question,
                    'query': None,
                    'valid': False,
                    'error': str(e)
                })

        print("\n" + "="*80)
        print("Summary")
        print("="*80 + "\n")

        valid_count = sum(1 for r in results if r['valid'])
        total_count = len(results)
        success_rate = (valid_count / total_count * 100) if total_count > 0 else 0

        print(f"Valid queries:   {valid_count}/{total_count}")
        print(f"Success rate:    {success_rate:.1f}%")
        print(f"Grammar enabled: {'YES' if generator.use_grammar else 'NO'}")
        print(f"Model:           LLMxCPG-Q (fine-tuned for CPGQL)")

        # Expected results
        print("\n" + "-"*80)
        print("Expected vs Actual:")
        print("-"*80)

        expected = [
            "cpg.method.name.l",
            "cpg.call.name(\"strcpy\").l",
            "cpg.method.parameter.name.l",
            "cpg.method.name(\"memcpy\").caller.name.l",
            "cpg.call.name(\"memcpy\").argument.code.l"
        ]

        for i, (exp, res) in enumerate(zip(expected, results), 1):
            print(f"\n{i}. {res['question']}")
            print(f"   Expected: {exp}")
            print(f"   Actual:   {res['query'] or 'FAILED'}")

            if res['query'] and res['query'].replace(' ', '') == exp.replace(' ', ''):
                print(f"   Status:   ✅ MATCH")
            else:
                print(f"   Status:   ⚠️  DIFFERENT (but may be valid)")

        print("\n" + "="*80)
        print("Integration Test Complete!")
        print("="*80 + "\n")

        if success_rate >= 80:
            print("✅ SUCCESS: Integration working as expected")
            return 0
        else:
            print("⚠️  WARNING: Success rate below 80%")
            return 1

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = test_grammar_integration()
    sys.exit(exit_code)
