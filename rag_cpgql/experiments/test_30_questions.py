"""Test Core Agents on 30 diverse questions."""
import sys
import logging
from pathlib import Path
import json
import time
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.analyzer_agent import AnalyzerAgent
from agents.retriever_agent import RetrieverAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.generator_agent import GeneratorAgent
from retrieval.vector_store_real import VectorStoreReal
from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_test_questions(data_dir: Path, num_questions: int = 30):
    """Load diverse test questions from dataset."""

    # Load train split merged
    train_file = data_dir / "train_split_merged.jsonl"

    questions = []
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if 'question' in data:
                questions.append(data['question'])

    # Sample diverse questions
    random.seed(42)  # Reproducible
    if len(questions) > num_questions:
        sampled = random.sample(questions, num_questions)
    else:
        sampled = questions[:num_questions]

    logger.info(f"Loaded {len(sampled)} test questions from {len(questions)} total")
    return sampled


def analyze_query_patterns(results: list):
    """Analyze patterns in generated queries."""

    patterns = {
        'has_tag_filter': 0,
        'has_name_filter': 0,
        'has_file_filter': 0,
        'has_where_clause': 0,
        'uses_method': 0,
        'uses_call': 0,
        'uses_file': 0,
        'has_artifacts': 0,  # Trailing ] or escaped quotes
        'avg_query_length': 0
    }

    for r in results:
        query = r['query']

        if '.tag.' in query:
            patterns['has_tag_filter'] += 1
        if '.name(' in query:
            patterns['has_name_filter'] += 1
        if '.file' in query:
            patterns['has_file_filter'] += 1
        if '.where(' in query:
            patterns['has_where_clause'] += 1
        if 'cpg.method' in query:
            patterns['uses_method'] += 1
        if 'cpg.call' in query:
            patterns['uses_call'] += 1
        if 'cpg.file' in query:
            patterns['uses_file'] += 1

        # Check for artifacts
        if query.endswith('"]') or query.endswith(']') or '\\"' in query:
            patterns['has_artifacts'] += 1

        patterns['avg_query_length'] += len(query)

    if results:
        patterns['avg_query_length'] /= len(results)

    return patterns


def test_30_questions():
    """Test the 4 core agents on 30 questions."""

    print("\n" + "="*80)
    print("Core Agents Test - 30 Questions")
    print("="*80 + "\n")

    try:
        # 1. Load test questions
        print("1. Loading test questions...")
        data_dir = Path(__file__).parent.parent / "data"
        test_questions = load_test_questions(data_dir, num_questions=30)
        print(f"   Loaded {len(test_questions)} questions\n")

        # 2. Initialize components
        print("2. Initializing components...")
        start_time = time.time()

        # Vector store
        vector_store = VectorStoreReal()
        vector_store.initialize_collections()

        stats = vector_store.get_stats()
        print(f"   Vector store: {stats['qa_pairs_count']:,} Q&A, "
              f"{stats['cpgql_examples_count']:,} CPGQL")

        # LLM (for generator) - USE BASE MODEL
        print("   Loading Qwen3-Coder-30B (base model)...")
        llm = LLMInterface(use_llmxcpg=False, n_ctx=4096, verbose=False)

        # CPGQL Generator (WITHOUT grammar)
        cpgql_gen = CPGQLGenerator(llm, use_grammar=False)

        # Initialize agents
        analyzer = AnalyzerAgent()
        retriever = RetrieverAgent(vector_store, analyzer)
        enrichment = EnrichmentAgent()
        generator = GeneratorAgent(cpgql_gen, use_grammar=False)

        init_time = time.time() - start_time
        print(f"   Initialized in {init_time:.2f}s\n")

        # 3. Test each question through the pipeline
        print("3. Testing agent pipeline:\n")
        print("-" * 80)

        results = []
        total_start = time.time()

        for i, question in enumerate(test_questions, 1):
            print(f"\n[{i}/{len(test_questions)}] {question[:70]}...")

            try:
                # Step 1: Analyze
                start = time.time()
                analysis = analyzer.analyze(question)
                analysis_time = time.time() - start

                # Step 2: Retrieve
                start = time.time()
                context = retriever.retrieve(
                    question=question,
                    analysis=analysis,
                    top_k_qa=3,
                    top_k_cpgql=5
                )
                retrieval_time = time.time() - start

                # Step 3: Enrichment
                start = time.time()
                enrichment_hints = enrichment.get_enrichment_hints(question, analysis)
                context['enrichment_hints'] = enrichment_hints
                enrichment_time = time.time() - start

                # Step 4: Generate
                start = time.time()
                query, is_valid, error = generator.generate(question, context)
                gen_time = time.time() - start

                # Show result
                status = "[+]" if is_valid else "[-]"
                print(f"   {status} Query: {query[:80]}...")
                print(f"   Time: {gen_time:.2f}s | Domain: {analysis['domain']} | Coverage: {enrichment_hints['coverage_score']:.2f}")

                if not is_valid:
                    print(f"   Error: {error}")

                results.append({
                    'question': question,
                    'analysis': analysis,
                    'retrieval_stats': context['retrieval_stats'],
                    'enrichment_coverage': enrichment_hints['coverage_score'],
                    'query': query,
                    'valid': is_valid,
                    'error': error,
                    'times': {
                        'analysis': analysis_time,
                        'retrieval': retrieval_time,
                        'enrichment': enrichment_time,
                        'generation': gen_time
                    }
                })

            except Exception as e:
                logger.error(f"Failed on question {i}: {e}")
                results.append({
                    'question': question,
                    'query': 'cpg.method.name.l',
                    'valid': False,
                    'error': str(e)
                })

        total_time = time.time() - total_start

        # 4. Analyze results
        print("\n" + "="*80)
        print("Test Results")
        print("="*80 + "\n")

        valid_count = sum(1 for r in results if r['valid'])
        avg_gen_time = sum(r.get('times', {}).get('generation', 0) for r in results) / len(results) if results else 0
        avg_coverage = sum(r.get('enrichment_coverage', 0) for r in results) / len(results) if results else 0

        print(f"Questions tested:      {len(results)}")
        print(f"Valid queries:         {valid_count}/{len(results)} ({valid_count/len(results)*100:.1f}%)")
        print(f"Avg generation time:   {avg_gen_time:.2f}s")
        print(f"Avg enrich coverage:   {avg_coverage:.2f}")
        print(f"Total test time:       {total_time:.2f}s")

        # Analyze by domain
        print("\nAnalysis by Domain:")
        domains = {}
        for r in results:
            domain = r.get('analysis', {}).get('domain', 'unknown')
            if domain not in domains:
                domains[domain] = {'total': 0, 'valid': 0}
            domains[domain]['total'] += 1
            if r['valid']:
                domains[domain]['valid'] += 1

        for domain, stats in sorted(domains.items(), key=lambda x: x[1]['total'], reverse=True):
            rate = (stats['valid'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {domain:20} {stats['valid']:2}/{stats['total']:2} ({rate:5.1f}%)")

        # Analyze query patterns
        print("\nQuery Pattern Analysis:")
        patterns = analyze_query_patterns(results)

        print(f"  Uses enrichment tags:  {patterns['has_tag_filter']}/{len(results)} ({patterns['has_tag_filter']/len(results)*100:.1f}%)")
        print(f"  Uses name filters:     {patterns['has_name_filter']}/{len(results)} ({patterns['has_name_filter']/len(results)*100:.1f}%)")
        print(f"  Uses where clauses:    {patterns['has_where_clause']}/{len(results)} ({patterns['has_where_clause']/len(results)*100:.1f}%)")
        print(f"  Uses cpg.method:       {patterns['uses_method']}/{len(results)} ({patterns['uses_method']/len(results)*100:.1f}%)")
        print(f"  Uses cpg.call:         {patterns['uses_call']}/{len(results)} ({patterns['uses_call']/len(results)*100:.1f}%)")
        print(f"  Has artifacts:         {patterns['has_artifacts']}/{len(results)} ({patterns['has_artifacts']/len(results)*100:.1f}%)")
        print(f"  Avg query length:      {patterns['avg_query_length']:.1f} chars")

        # Show examples of valid queries with tags
        print("\nExample Valid Queries with Enrichment Tags:")
        tag_queries = [r for r in results if r['valid'] and '.tag.' in r['query']]
        for i, r in enumerate(tag_queries[:5], 1):
            print(f"\n  {i}. Q: {r['question'][:60]}...")
            print(f"     Query: {r['query']}")
            print(f"     Domain: {r.get('analysis', {}).get('domain', 'unknown')}")

        # Show problematic queries
        print("\nExample Queries with Artifacts:")
        artifact_queries = [r for r in results if r['query'].endswith('"]') or r['query'].endswith(']') or '\\"' in r['query']]
        for i, r in enumerate(artifact_queries[:3], 1):
            print(f"\n  {i}. Q: {r['question'][:60]}...")
            print(f"     Query: {r['query']}")
            print(f"     Issue: {r.get('error', 'Has trailing artifacts')}")

        # Save results
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "test_30_questions_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_name': 'Core Agents Test - 30 Questions',
                'total_questions': len(results),
                'valid_queries': valid_count,
                'validity_rate': (valid_count / len(results) * 100) if results else 0,
                'avg_generation_time': avg_gen_time,
                'avg_enrichment_coverage': avg_coverage,
                'total_test_time': total_time,
                'query_patterns': patterns,
                'results': results
            }, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")

        return 0

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = test_30_questions()
    sys.exit(exit_code)
