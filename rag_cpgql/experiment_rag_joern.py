"""RAG+Joern Experiment: Test retrieval and query execution without LLM.

This experiment validates:
1. Vector similarity search for relevant QA pairs
2. CPGQL query execution from dataset examples
3. Enrichment tag extraction from results
4. Query success rate and result quality
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import logging
from typing import List, Dict
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_experiment(num_samples: int = 5):
    """Run RAG+Joern experiment on sample questions.

    Args:
        num_samples: Number of test samples to process
    """
    from utils.config import load_config
    from utils.data_loader import load_qa_pairs
    from retrieval.vector_store import VectorStore
    from execution.joern_client import JoernClient

    logger.info("=" * 80)
    logger.info(f"RAG+JOERN EXPERIMENT - {num_samples} samples")
    logger.info("=" * 80)

    # Load config and data
    config = load_config()

    logger.info("\n[1/5] Loading datasets...")
    train_data = load_qa_pairs(config.train_split)
    test_data = load_qa_pairs(config.test_split)
    logger.info(f"  Train: {len(train_data)} pairs")
    logger.info(f"  Test: {len(test_data)} pairs")

    # Initialize vector store
    logger.info("\n[2/5] Initializing vector store...")
    vector_store = VectorStore(model_name=config.embedding_model)
    logger.info(f"  Indexing {len(train_data)} training examples...")
    start_time = time.time()
    vector_store.create_qa_index(train_data)
    index_time = time.time() - start_time
    logger.info(f"  Indexed in {index_time:.1f}s")

    # Connect to Joern
    logger.info("\n[3/5] Connecting to Joern...")
    joern = JoernClient(cpg_project_name="pg17_full.cpg", port=config.joern_port)
    if not joern.connect():
        logger.error("Failed to connect to Joern")
        return

    logger.info(f"  Connected to CPG with {52303} methods")

    # Run experiments on test samples
    logger.info(f"\n[4/5] Running experiments on {num_samples} test questions...")
    test_samples = test_data[:num_samples]

    results = []
    for i, test_qa in enumerate(test_samples, 1):
        logger.info(f"\n--- Sample {i}/{num_samples} ---")
        logger.info(f"Question: {test_qa['question'][:100]}...")
        logger.info(f"Difficulty: {test_qa.get('difficulty', 'N/A')}")
        logger.info(f"Source: {test_qa.get('source_dataset', 'N/A')}")

        # Step 1: Retrieve similar QA pairs
        similar_qa = vector_store.search_similar_qa(test_qa['question'], k=3)
        logger.info(f"\nRetrieved {len(similar_qa)} similar QA pairs:")
        for j, sim in enumerate(similar_qa, 1):
            logger.info(f"  {j}. Similarity: {sim['similarity']:.3f}")
            logger.info(f"     Q: {sim['question'][:80]}...")

        # Step 2: Extract CPGQL queries from similar examples
        cpgql_queries = []
        for sim in similar_qa:
            # Try to extract CPGQL from answer
            answer = sim.get('answer', '')
            if 'cpg.' in answer.lower():
                # Simple extraction: find lines with 'cpg.'
                for line in answer.split('\n'):
                    if 'cpg.' in line and not line.strip().startswith('#'):
                        query = line.strip()
                        if query and len(query) < 200:
                            cpgql_queries.append(query)
                            break

        if cpgql_queries:
            logger.info(f"\nExtracted {len(cpgql_queries)} CPGQL queries from examples")

            # Step 3: Execute first query
            query = cpgql_queries[0]
            logger.info(f"\nExecuting query: {query[:100]}...")

            try:
                result = joern.execute_query(query)

                if result.get('success'):
                    stdout = result['results'].get('stdout', '')

                    # Check for errors in output
                    if '[E' in stdout or 'error' in stdout.lower():
                        logger.warning("  Query executed but returned error")
                        success = False
                        enrichments_found = []
                    else:
                        logger.info("  ✓ Query executed successfully")
                        success = True

                        # Extract enrichment tags from output
                        enrichments_found = []
                        enrichment_keywords = [
                            'cyclomatic-complexity', 'lines-of-code', 'code-smell',
                            'security-risk', 'refactor-priority', 'test-coverage',
                            'perf-hotspot', 'allocation-heavy', 'loop-depth'
                        ]
                        for keyword in enrichment_keywords:
                            if keyword in stdout:
                                enrichments_found.append(keyword)

                        if enrichments_found:
                            logger.info(f"  Enrichments found: {', '.join(enrichments_found)}")

                        # Show result preview
                        result_preview = stdout[:300].replace('\r\n', ' ').replace('\n', ' ')
                        logger.info(f"  Result preview: {result_preview}...")
                else:
                    logger.error(f"  ✗ Query failed: {result.get('error', 'Unknown error')}")
                    success = False
                    enrichments_found = []

                results.append({
                    'question': test_qa['question'],
                    'difficulty': test_qa.get('difficulty'),
                    'source': test_qa.get('source_dataset'),
                    'retrieved_count': len(similar_qa),
                    'cpgql_extracted': len(cpgql_queries) > 0,
                    'query_executed': query if cpgql_queries else None,
                    'execution_success': success,
                    'enrichments_found': enrichments_found
                })

            except Exception as e:
                logger.error(f"  ✗ Exception during execution: {e}")
                results.append({
                    'question': test_qa['question'],
                    'difficulty': test_qa.get('difficulty'),
                    'source': test_qa.get('source_dataset'),
                    'retrieved_count': len(similar_qa),
                    'cpgql_extracted': False,
                    'query_executed': None,
                    'execution_success': False,
                    'enrichments_found': [],
                    'error': str(e)
                })
        else:
            logger.warning("  No CPGQL queries found in retrieved examples")
            results.append({
                'question': test_qa['question'],
                'difficulty': test_qa.get('difficulty'),
                'source': test_qa.get('source_dataset'),
                'retrieved_count': len(similar_qa),
                'cpgql_extracted': False,
                'query_executed': None,
                'execution_success': False,
                'enrichments_found': []
            })

    # Analyze results
    logger.info("\n[5/5] Analyzing results...")
    logger.info("=" * 80)

    total = len(results)
    retrieved_all = sum(1 for r in results if r['retrieved_count'] > 0)
    cpgql_found = sum(1 for r in results if r['cpgql_extracted'])
    executed = sum(1 for r in results if r['query_executed'] is not None)
    successful = sum(1 for r in results if r['execution_success'])
    with_enrichments = sum(1 for r in results if r['enrichments_found'])

    logger.info(f"\nRESULTS SUMMARY ({num_samples} samples):")
    logger.info(f"  Retrieval successful: {retrieved_all}/{total} ({100*retrieved_all/total:.1f}%)")
    logger.info(f"  CPGQL extracted: {cpgql_found}/{total} ({100*cpgql_found/total:.1f}%)")
    logger.info(f"  Queries executed: {executed}/{total} ({100*executed/total:.1f}%)")
    logger.info(f"  Execution success: {successful}/{total} ({100*successful/total:.1f}%)")
    logger.info(f"  With enrichments: {with_enrichments}/{total} ({100*with_enrichments/total:.1f}%)")

    # Enrichment statistics
    all_enrichments = []
    for r in results:
        all_enrichments.extend(r['enrichments_found'])

    if all_enrichments:
        from collections import Counter
        enrichment_counts = Counter(all_enrichments)
        logger.info(f"\nEnrichment tag distribution:")
        for tag, count in enrichment_counts.most_common():
            logger.info(f"  {tag}: {count}")

    # Source breakdown
    logger.info(f"\nBy source dataset:")
    by_source = {}
    for r in results:
        source = r['source']
        if source not in by_source:
            by_source[source] = {'total': 0, 'success': 0}
        by_source[source]['total'] += 1
        if r['execution_success']:
            by_source[source]['success'] += 1

    for source, stats in by_source.items():
        success_rate = 100 * stats['success'] / stats['total'] if stats['total'] > 0 else 0
        logger.info(f"  {source}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

    # Save results
    output_file = f"experiment_results_{num_samples}samples.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'experiment': 'RAG+Joern',
            'num_samples': num_samples,
            'summary': {
                'retrieval_success_rate': retrieved_all / total,
                'cpgql_extraction_rate': cpgql_found / total,
                'execution_rate': executed / total,
                'success_rate': successful / total,
                'enrichment_rate': with_enrichments / total
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\nResults saved to: {output_file}")

    # Cleanup
    logger.info("\nCleaning up...")
    joern.close()

    logger.info("\n" + "=" * 80)
    logger.info("EXPERIMENT COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run RAG+Joern experiment')
    parser.add_argument('--samples', type=int, default=5,
                        help='Number of test samples to process (default: 5)')
    args = parser.parse_args()

    run_experiment(num_samples=args.samples)
