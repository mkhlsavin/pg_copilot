"""End-to-End test: RAG-CPGQL with real Joern PostgreSQL CPG execution.

This test validates the complete pipeline:
1. Question Analysis (Analyzer Agent)
2. Context Retrieval (Retriever Agent)
3. Enrichment Hints (Enrichment Agent)
4. CPGQL Generation (Generator Agent)
5. Query Execution on real PostgreSQL CPG (Joern)
6. Result Validation
"""
import sys
from pathlib import Path
import json
import logging
from typing import Dict, List
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.generator_agent import GeneratorAgent
from src.execution.joern_client import JoernClient
from src.utils.data_loader import load_qa_pairs
from src.utils.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_e2e_with_joern(
    test_questions: List[str] = None,
    num_samples: int = 10,
    require_joern: bool = True
):
    """
    Run end-to-end test with real Joern execution.

    Args:
        test_questions: Optional list of custom questions
        num_samples: Number of questions from test set (if no custom questions)
        require_joern: If False, run without Joern (generation only)
    """
    print("\n" + "="*80)
    print("RAG-CPGQL END-TO-END TEST WITH JOERN")
    print("="*80 + "\n")

    # Load configuration
    config = load_config()

    # Initialize agents
    print("[1/7] Initializing agents...")
    analyzer = AnalyzerAgent()
    retriever = RetrieverAgent()
    enrichment = EnrichmentAgent()
    generator = GeneratorAgent(use_llmxcpg=True)
    print("  [OK] All agents initialized\n")

    # Initialize Joern client
    joern_client = None
    if require_joern:
        print("[2/7] Connecting to Joern...")
        try:
            joern_client = JoernClient(server_endpoint="localhost:8080")
            if not joern_client.connect():
                print("  [WARNING] Could not connect to Joern server")
                print("  Make sure Joern is running:")
                print("    cd ../joern")
                print("    ./joern --server --server-host localhost --server-port 8080")
                print("\n  Continuing without Joern (generation-only mode)")
                joern_client = None
            else:
                print("  [OK] Connected to Joern server")
                stats = joern_client.get_cpg_stats()
                print(f"  CPG Stats: {stats.get('methods', 0)} methods, "
                      f"{stats.get('files', 0)} files\n")
        except Exception as e:
            print(f"  [WARNING] Joern connection error: {e}")
            print("  Continuing without Joern (generation-only mode)\n")
            joern_client = None
    else:
        print("[2/7] Skipping Joern connection (generation-only mode)\n")

    # Prepare test questions
    print("[3/7] Preparing test questions...")
    if test_questions is None:
        # Load from test split
        test_split = load_qa_pairs(config.test_split)
        test_questions = [qa['question'] for qa in test_split[:num_samples]]
        print(f"  Loaded {len(test_questions)} questions from test split\n")
    else:
        print(f"  Using {len(test_questions)} custom questions\n")

    # Run pipeline on each question
    print(f"[4/7] Running pipeline on {len(test_questions)} questions...\n")

    results = []
    start_time = time.time()

    for i, question in enumerate(test_questions, 1):
        print(f"{'='*80}")
        print(f"Question {i}/{len(test_questions)}")
        print(f"{'='*80}")
        print(f"Q: {question}\n")

        result = {
            'question': question,
            'question_num': i,
            'times': {}
        }

        try:
            # Step 1: Analyze question
            t0 = time.time()
            analysis = analyzer.analyze(question)
            result['times']['analysis'] = time.time() - t0
            result['analysis'] = analysis
            print(f"Analysis: domain={analysis.get('domain')}, "
                  f"complexity={analysis.get('complexity')}")

            # Step 2: Retrieve context
            t0 = time.time()
            retrieval_result = retriever.retrieve(question, analysis)
            result['times']['retrieval'] = time.time() - t0
            result['retrieval_stats'] = {
                'qa_retrieved': len(retrieval_result['qa_pairs']),
                'cpgql_retrieved': len(retrieval_result['cpgql_examples']),
                'avg_qa_similarity': retrieval_result['metadata']['avg_qa_similarity'],
                'avg_cpgql_similarity': retrieval_result['metadata']['avg_cpgql_similarity']
            }
            print(f"Retrieved: {result['retrieval_stats']['qa_retrieved']} Q&A pairs, "
                  f"{result['retrieval_stats']['cpgql_retrieved']} CPGQL examples")

            # Step 3: Get enrichment hints
            t0 = time.time()
            enrichment_hints = enrichment.get_enrichment_hints(
                question,
                analysis,
                retrieval_result['qa_pairs']
            )
            result['times']['enrichment'] = time.time() - t0
            result['enrichment_hints'] = enrichment_hints
            result['enrichment_coverage'] = len(enrichment_hints) / 12.0  # 12 total enrichment layers
            print(f"Enrichment: {len(enrichment_hints)} hints "
                  f"({result['enrichment_coverage']:.1%} coverage)")

            # Step 4: Generate CPGQL query
            t0 = time.time()
            query = generator.generate(
                question,
                analysis,
                retrieval_result,
                enrichment_hints
            )
            result['times']['generation'] = time.time() - t0
            result['query'] = query

            # Basic validation
            result['valid'] = generator.validate_query(query)
            print(f"\nGenerated query ({result['times']['generation']:.2f}s):")
            print(f"  {query}")
            print(f"  Valid: {result['valid']}")

            # Step 5: Execute on Joern (if available)
            if joern_client and result['valid']:
                print(f"\nExecuting on Joern CPG...")
                t0 = time.time()
                exec_result = joern_client.execute_query(query)
                result['times']['execution'] = time.time() - t0
                result['execution'] = {
                    'success': exec_result['success'],
                    'execution_time': exec_result['execution_time'],
                    'error': exec_result.get('error')
                }

                if exec_result['success']:
                    result_data = exec_result.get('result', '')
                    result['execution']['result_length'] = len(str(result_data))
                    result['execution']['result_preview'] = str(result_data)[:200]
                    print(f"  [OK] Execution successful ({exec_result['execution_time']:.2f}s)")
                    print(f"  Result length: {result['execution']['result_length']} chars")
                    if result['execution']['result_length'] > 0:
                        print(f"  Preview: {result['execution']['result_preview']}...")
                else:
                    print(f"  [FAILED] Execution error: {exec_result.get('error')}")
            else:
                result['execution'] = None
                if not result['valid']:
                    print(f"  [SKIPPED] Query invalid, not executing")
                else:
                    print(f"  [SKIPPED] Joern not available")

            # Total time
            total_time = sum(result['times'].values())
            result['times']['total'] = total_time
            print(f"\nTotal pipeline time: {total_time:.2f}s")

        except Exception as e:
            logger.error(f"Error processing question {i}: {e}", exc_info=True)
            result['error'] = str(e)
            result['valid'] = False

        results.append(result)
        print()

    total_time = time.time() - start_time

    # Summary statistics
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80 + "\n")

    total = len(results)
    valid_queries = sum(1 for r in results if r.get('valid', False))
    executed = sum(1 for r in results if r.get('execution') and r['execution']['success'])
    errors = sum(1 for r in results if 'error' in r)

    print(f"Total questions:       {total}")
    print(f"Valid queries:         {valid_queries}/{total} ({100*valid_queries/total:.1%})")
    if joern_client:
        print(f"Successful execution:  {executed}/{valid_queries} ({100*executed/valid_queries:.1%} of valid)")
    print(f"Errors:                {errors}/{total}")
    print(f"\nTotal time:            {total_time:.2f}s")
    print(f"Avg time per question: {total_time/total:.2f}s")

    # Timing breakdown
    avg_times = {}
    for key in ['analysis', 'retrieval', 'enrichment', 'generation', 'execution']:
        times = [r['times'].get(key, 0) for r in results if r['times'].get(key)]
        if times:
            avg_times[key] = sum(times) / len(times)

    print(f"\nAverage timing breakdown:")
    for key, avg_time in avg_times.items():
        print(f"  {key:15} {avg_time:.3f}s")

    # Domain breakdown
    domain_stats = {}
    for r in results:
        domain = r.get('analysis', {}).get('domain', 'unknown')
        if domain not in domain_stats:
            domain_stats[domain] = {'total': 0, 'valid': 0, 'executed': 0}
        domain_stats[domain]['total'] += 1
        if r.get('valid'):
            domain_stats[domain]['valid'] += 1
        if r.get('execution') and r['execution'].get('success'):
            domain_stats[domain]['executed'] += 1

    print(f"\nPerformance by domain:")
    for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['valid'], reverse=True):
        validity_rate = 100 * stats['valid'] / stats['total'] if stats['total'] > 0 else 0
        if joern_client and stats['valid'] > 0:
            exec_rate = 100 * stats['executed'] / stats['valid']
            print(f"  {domain:20} {stats['valid']}/{stats['total']} valid ({validity_rate:.1f}%), "
                  f"{stats['executed']}/{stats['valid']} executed ({exec_rate:.1f}%)")
        else:
            print(f"  {domain:20} {stats['valid']}/{stats['total']} valid ({validity_rate:.1f}%)")

    # Save results
    output_file = project_root / "results" / "e2e_test_with_joern_results.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_name': 'End-to-End Test with Joern',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config': {
                'num_questions': total,
                'joern_enabled': joern_client is not None,
                'model': 'LLMxCPG-Q' if generator.use_llmxcpg else 'Qwen3-Coder'
            },
            'summary': {
                'total_questions': total,
                'valid_queries': valid_queries,
                'validity_rate': valid_queries / total if total > 0 else 0,
                'executed_successfully': executed,
                'execution_success_rate': executed / valid_queries if valid_queries > 0 else 0,
                'errors': errors,
                'total_time': total_time,
                'avg_time_per_question': total_time / total if total > 0 else 0
            },
            'timing': avg_times,
            'domain_stats': domain_stats,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {output_file}")

    # Cleanup
    if joern_client:
        joern_client.close()
        print("\nJoern connection closed")

    print("\n" + "="*80)
    print("END-TO-END TEST COMPLETED")
    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='End-to-end RAG-CPGQL test with Joern')
    parser.add_argument('--samples', type=int, default=10,
                        help='Number of test samples (default: 10)')
    parser.add_argument('--no-joern', action='store_true',
                        help='Run without Joern (generation only)')
    parser.add_argument('--questions', nargs='+',
                        help='Custom questions to test')

    args = parser.parse_args()

    test_e2e_with_joern(
        test_questions=args.questions,
        num_samples=args.samples,
        require_joern=not args.no_joern
    )
