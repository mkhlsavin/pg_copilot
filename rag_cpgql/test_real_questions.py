"""Test grammar-constrained generation on real PostgreSQL security questions."""
import sys
import logging
from pathlib import Path
import io
import json

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG to see raw queries
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_test_questions(count=10):
    """Load real questions from test dataset."""
    test_file = Path(__file__).parent / "data" / "test_split_merged.jsonl"

    if not test_file.exists():
        logger.warning(f"Test file not found: {test_file}")
        return get_sample_questions()

    questions = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            try:
                data = json.loads(line)
                questions.append({
                    'question': data.get('question', ''),
                    'answer': data.get('answer', ''),
                    'source': 'dataset'
                })
            except:
                continue

    if not questions:
        return get_sample_questions()

    return questions


def get_sample_questions():
    """Get sample PostgreSQL security questions."""
    return [
        {
            'question': 'How does PostgreSQL handle SQL injection prevention?',
            'expected_query': 'cpg.method.name(".*exec.*").parameter.l',
            'source': 'manual'
        },
        {
            'question': 'Find all buffer copy operations',
            'expected_query': 'cpg.call.name(".*cpy").l',
            'source': 'manual'
        },
        {
            'question': 'What functions handle user authentication?',
            'expected_query': 'cpg.method.name(".*auth.*").l',
            'source': 'manual'
        },
        {
            'question': 'Find memory allocation calls',
            'expected_query': 'cpg.call.name(".*alloc").l',
            'source': 'manual'
        },
        {
            'question': 'List all functions that use strcpy',
            'expected_query': 'cpg.call.name("strcpy").l',
            'source': 'manual'
        },
        {
            'question': 'Find pointer parameters in functions',
            'expected_query': 'cpg.parameter.name(".*ptr").l',
            'source': 'manual'
        },
        {
            'question': 'What methods handle password validation?',
            'expected_query': 'cpg.method.name(".*password.*").l',
            'source': 'manual'
        },
        {
            'question': 'Find all file I/O operations',
            'expected_query': 'cpg.call.name(".*read.*|.*write.*").l',
            'source': 'manual'
        },
        {
            'question': 'List functions that call malloc',
            'expected_query': 'cpg.method.callOut.name("malloc").l',
            'source': 'manual'
        },
        {
            'question': 'Find SQL query execution functions',
            'expected_query': 'cpg.method.name(".*query.*|.*exec.*").l',
            'source': 'manual'
        },
    ]


def test_real_questions():
    """Test on real PostgreSQL questions."""

    print("\n" + "="*80)
    print("Grammar-Constrained CPGQL - Real Questions Test")
    print("="*80 + "\n")

    # Load test questions
    questions = load_test_questions(count=10)
    print(f"Loaded {len(questions)} test questions\n")

    try:
        # Initialize LLM with LLMxCPG-Q model
        print("1. Loading LLMxCPG-Q model...")
        llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
        print("   ✅ Model loaded\n")

        # Initialize CPGQL generator with grammar
        print("2. Loading CPGQL grammar...")
        generator = CPGQLGenerator(llm, use_grammar=True)

        if generator.use_grammar:
            print("   ✅ Grammar loaded\n")
        else:
            print("   ⚠️  Grammar failed, using fallback\n")

        # Test query generation
        print("3. Testing on real questions:\n")
        print("="*80 + "\n")

        results = []
        for i, item in enumerate(questions, 1):
            question = item['question']
            expected = item.get('expected_query', 'N/A')

            print(f"Question {i}/{len(questions)}:")
            print(f"  Q: {question}")

            try:
                # Generate query with higher max_tokens for complete strings
                query = generator.generate_query(
                    question,
                    max_tokens=400,  # Increased for complete generation
                    temperature=0.5  # Lower for more deterministic
                )

                # Validate
                is_valid, error = generator.validate_query(query)

                print(f"  Generated: {query}")
                print(f"  Expected:  {expected}")
                print(f"  Valid:     {'✅ YES' if is_valid else f'❌ NO - {error}'}")

                # Analyze query quality
                quality = analyze_query_quality(query, question)
                print(f"  Quality:   {quality['score']}/100 - {quality['reason']}")

                results.append({
                    'question': question,
                    'query': query,
                    'expected': expected,
                    'valid': is_valid,
                    'quality': quality['score']
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    'question': question,
                    'query': None,
                    'valid': False,
                    'quality': 0
                })

            print()

        # Summary
        print("="*80)
        print("Summary")
        print("="*80 + "\n")

        valid_count = sum(1 for r in results if r['valid'])
        avg_quality = sum(r['quality'] for r in results) / len(results)

        print(f"Valid queries:   {valid_count}/{len(results)} ({valid_count/len(results)*100:.1f}%)")
        print(f"Avg quality:     {avg_quality:.1f}/100")
        print(f"Grammar enabled: {'YES' if generator.use_grammar else 'NO'}")

        # Quality distribution
        high_quality = sum(1 for r in results if r['quality'] >= 80)
        medium_quality = sum(1 for r in results if 50 <= r['quality'] < 80)
        low_quality = sum(1 for r in results if r['quality'] < 50)

        print(f"\nQuality Distribution:")
        print(f"  High (80-100):   {high_quality} queries")
        print(f"  Medium (50-79):  {medium_quality} queries")
        print(f"  Low (0-49):      {low_quality} queries")

        # Save results
        output_file = Path(__file__).parent / "results" / "real_questions_test.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': '2025-10-10',
                'model': 'LLMxCPG-Q',
                'grammar_enabled': generator.use_grammar,
                'total_questions': len(results),
                'valid_queries': valid_count,
                'avg_quality': avg_quality,
                'results': results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {output_file}")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")

        if valid_count / len(results) >= 0.9:
            print("✅ EXCELLENT: 90%+ valid queries")
            return 0
        elif valid_count / len(results) >= 0.7:
            print("✅ GOOD: 70%+ valid queries")
            return 0
        else:
            print("⚠️  NEEDS IMPROVEMENT: <70% valid queries")
            return 1

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


def analyze_query_quality(query: str, question: str) -> dict:
    """
    Analyze query quality based on relevance to question.

    Returns:
        {'score': int, 'reason': str}
    """
    score = 50  # Base score for valid syntax
    reasons = []

    # Check if query is specific (not just cpg.method.l or cpg.call.l)
    if query in ['cpg.method.l', 'cpg.call.l', 'cpg.parameter.l']:
        score = 40
        reasons.append("Too generic")
        return {'score': score, 'reason': ', '.join(reasons)}

    # Check for specific patterns based on question keywords
    question_lower = question.lower()

    # Security-related
    if any(kw in question_lower for kw in ['sql', 'injection', 'query', 'exec']):
        if 'exec' in query or 'query' in query:
            score += 20
            reasons.append("Relevant to SQL/exec")

    # Memory operations
    if any(kw in question_lower for kw in ['buffer', 'copy', 'strcpy', 'memcpy']):
        if 'cpy' in query or 'strcpy' in query or 'memcpy' in query:
            score += 20
            reasons.append("Relevant to buffer ops")

    # Authentication
    if any(kw in question_lower for kw in ['auth', 'password', 'login']):
        if 'auth' in query or 'password' in query:
            score += 20
            reasons.append("Relevant to auth")

    # Memory allocation
    if any(kw in question_lower for kw in ['malloc', 'alloc', 'memory']):
        if 'alloc' in query or 'malloc' in query:
            score += 20
            reasons.append("Relevant to allocation")

    # File I/O
    if any(kw in question_lower for kw in ['file', 'read', 'write', 'i/o']):
        if 'read' in query or 'write' in query:
            score += 20
            reasons.append("Relevant to I/O")

    # Check for regex patterns (more sophisticated)
    if '.*' in query or '.+' in query:
        score += 10
        reasons.append("Uses regex")

    # Check for chaining (method calls)
    if '.caller' in query or '.callOut' in query or '.argument' in query:
        score += 10
        reasons.append("Has method chaining")

    # Cap at 100
    score = min(score, 100)

    if not reasons:
        reasons.append("Basic valid query")

    return {'score': score, 'reason': ', '.join(reasons)}


if __name__ == "__main__":
    exit_code = test_real_questions()
    sys.exit(exit_code)
