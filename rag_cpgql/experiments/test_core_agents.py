"""Test Core Agents integration (Analyzer + Retriever + Enrichment + Generator)."""
import sys
import logging
from pathlib import Path
import json
import time

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


def test_core_agents():
    """Test the 4 core agents working together."""

    print("\n" + "="*80)
    print("Core Agents Integration Test")
    print("="*80 + "\n")

    # Test questions
    test_questions = [
        "How does PostgreSQL handle vacuum operations?",
        "Find all functions related to WAL checkpointing",
        "What data structures are used in MVCC snapshot management?",
    ]

    try:
        # 1. Initialize components
        print("1. Initializing components...")
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

        # 2. Test each question through the pipeline
        print("2. Testing agent pipeline:\n")
        print("-" * 80)

        results = []

        for i, question in enumerate(test_questions, 1):
            print(f"\n[{i}/{len(test_questions)}] Question: {question}\n")

            # Step 1: Analyze
            print("   Step 1: Analyzing...")
            start = time.time()
            analysis = analyzer.analyze(question)
            print(f"      Intent: {analysis['intent']}")
            print(f"      Domain: {analysis['domain']}")
            print(f"      Keywords: {', '.join(analysis['keywords'][:5])}")
            print(f"      Confidence: {analysis['confidence']:.2f}")
            print(f"      Time: {time.time() - start:.2f}s")

            # Step 2: Retrieve
            print("\n   Step 2: Retrieving context...")
            start = time.time()
            context = retriever.retrieve(
                question=question,
                analysis=analysis,
                top_k_qa=3,
                top_k_cpgql=5
            )
            print(f"      Retrieved: {len(context['similar_qa'])} Q&A pairs, "
                  f"{len(context['cpgql_examples'])} CPGQL examples")
            print(f"      Avg similarity: QA={context['retrieval_stats']['avg_qa_similarity']:.3f}, "
                  f"CPGQL={context['retrieval_stats']['avg_cpgql_similarity']:.3f}")
            print(f"      Time: {time.time() - start:.2f}s")

            # Step 3: Enrichment
            print("\n   Step 3: Getting enrichment hints...")
            start = time.time()
            enrichment_hints = enrichment.get_enrichment_hints(question, analysis)
            context['enrichment_hints'] = enrichment_hints

            print(f"      Features: {', '.join(enrichment_hints['features'][:3]) if enrichment_hints['features'] else 'none'}")
            print(f"      Function purposes: {', '.join(enrichment_hints['function_purposes'][:3]) if enrichment_hints['function_purposes'] else 'none'}")
            print(f"      Data structures: {', '.join(enrichment_hints['data_structures'][:3]) if enrichment_hints['data_structures'] else 'none'}")
            print(f"      Tag filters: {len(enrichment_hints['tags'])}")
            print(f"      Coverage: {enrichment_hints['coverage_score']:.2f}")
            print(f"      Time: {time.time() - start:.2f}s")

            # Step 4: Generate
            print("\n   Step 4: Generating CPGQL query...")
            start = time.time()
            query, is_valid, error = generator.generate(question, context)
            gen_time = time.time() - start

            # Highlight the query
            print(f"\n      {'='*60}")
            print(f"      CPGQL Query: {query}")
            print(f"      {'='*60}")
            print(f"      Valid: {'YES [+]' if is_valid else 'NO [-]'}")
            if not is_valid:
                print(f"      Error: {error}")
            print(f"      Time: {gen_time:.2f}s")

            # Explain query
            if is_valid:
                explanation = generator.explain_query(query, context)
                print(f"      Explanation: {explanation}")

            # Show top retrieved Q&A
            print("\n   Top Retrieved Q&A:")
            for j, qa in enumerate(context['similar_qa'][:2], 1):
                print(f"      {j}. (sim={qa['similarity']:.3f}) {qa['question'][:70]}...")

            # Show enrichment tag examples
            if enrichment_hints['tags']:
                print("\n   Example Tag-Based Queries:")
                examples = enrichment.get_example_queries(enrichment_hints, limit=2)
                for j, example in enumerate(examples, 1):
                    print(f"      {j}. {example[:90]}...")

            results.append({
                'question': question,
                'analysis': analysis,
                'retrieval_stats': context['retrieval_stats'],
                'enrichment_coverage': enrichment_hints['coverage_score'],
                'query': query,
                'valid': is_valid,
                'error': error,
                'generation_time': gen_time
            })

        # Summary
        print("\n" + "="*80)
        print("Test Summary")
        print("="*80 + "\n")

        valid_count = sum(1 for r in results if r['valid'])
        avg_gen_time = sum(r['generation_time'] for r in results) / len(results)
        avg_coverage = sum(r['enrichment_coverage'] for r in results) / len(results)

        print(f"Questions tested:      {len(results)}")
        print(f"Valid queries:         {valid_count}/{len(results)}")
        print(f"Avg generation time:   {avg_gen_time:.2f}s")
        print(f"Avg enrich coverage:   {avg_coverage:.2f}")

        # Analyze by domain
        print("\nAnalysis by Domain:")
        domains = {}
        for r in results:
            domain = r['analysis']['domain']
            if domain not in domains:
                domains[domain] = {'total': 0, 'valid': 0}
            domains[domain]['total'] += 1
            if r['valid']:
                domains[domain]['valid'] += 1

        for domain, stats in domains.items():
            rate = (stats['valid'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {domain:15} {stats['valid']}/{stats['total']} ({rate:.1f}%)")

        # Save results
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "core_agents_test_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_name': 'Core Agents Integration Test',
                'total_questions': len(results),
                'valid_queries': valid_count,
                'validity_rate': (valid_count / len(results) * 100) if results else 0,
                'avg_generation_time': avg_gen_time,
                'avg_enrichment_coverage': avg_coverage,
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
    exit_code = test_core_agents()
    sys.exit(exit_code)
