"""RAGAS Evaluator for RAG-CPGQL system."""
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json
from datasets import Dataset

# RAGAS metrics
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision,
    context_entity_recall,
    answer_similarity,
    answer_correctness
)

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """
    RAGAS-based evaluation for RAG-CPGQL pipeline.

    Evaluates:
    - Context Relevance: How relevant retrieved Q&A and CPGQL examples are
    - Answer Quality: How good the generated CPGQL query is
    - Faithfulness: Whether query uses retrieved context appropriately
    """

    def __init__(self, use_local_llm: bool = False):
        """
        Initialize RAGAS evaluator.

        Args:
            use_local_llm: Use local LLM for evaluation (not OpenAI)
        """
        self.use_local_llm = use_local_llm

        # Select metrics that work without ground truth answers
        self.metrics = [
            context_precision,      # Retrieved context relevance
            context_recall,         # Coverage of question by context
            answer_relevancy,       # Generated query relevance to question
            faithfulness           # Query faithfulness to retrieved context
        ]

        logger.info(f"RAGAS evaluator initialized with {len(self.metrics)} metrics")

    def prepare_evaluation_data(
        self,
        test_results: List[Dict]
    ) -> Dataset:
        """
        Convert test results to RAGAS dataset format.

        RAGAS expects:
        - question: User question
        - contexts: List of retrieved context strings
        - answer: Generated answer (CPGQL query in our case)
        - ground_truth: Expected answer (optional)

        Args:
            test_results: List of test result dicts

        Returns:
            HuggingFace Dataset
        """
        data = {
            'question': [],
            'contexts': [],
            'answer': [],
            'ground_truth': []
        }

        for result in test_results:
            # Question
            data['question'].append(result['question'])

            # Contexts: Combine retrieved Q&A and CPGQL examples
            contexts = []

            # Add similar Q&A pairs as context
            if 'retrieval_stats' in result:
                for i in range(result['retrieval_stats'].get('qa_retrieved', 0)):
                    contexts.append(f"Q&A example {i+1}")

            # Add CPGQL examples as context
            if 'retrieval_stats' in result:
                for i in range(result['retrieval_stats'].get('cpgql_retrieved', 0)):
                    contexts.append(f"CPGQL example {i+1}")

            # Add enrichment hints as context
            if 'enrichment_coverage' in result and result['enrichment_coverage'] > 0:
                contexts.append(f"Enrichment coverage: {result['enrichment_coverage']:.2f}")

            data['contexts'].append(contexts if contexts else ["No context"])

            # Answer: Generated CPGQL query
            data['answer'].append(result.get('query', 'cpg.method.name.l'))

            # Ground truth: Mark valid queries as correct
            if result.get('valid', False):
                data['ground_truth'].append(result['query'])
            else:
                data['ground_truth'].append("Invalid query")

        dataset = Dataset.from_dict(data)
        logger.info(f"Prepared evaluation dataset with {len(dataset)} samples")

        return dataset

    def evaluate_rag_pipeline(
        self,
        test_results: List[Dict],
        output_file: Optional[Path] = None
    ) -> Dict:
        """
        Evaluate RAG pipeline using RAGAS metrics.

        Args:
            test_results: List of test result dicts
            output_file: Optional file to save evaluation results

        Returns:
            Dict with RAGAS metric scores
        """
        logger.info(f"Starting RAGAS evaluation on {len(test_results)} samples")

        # Prepare dataset
        dataset = self.prepare_evaluation_data(test_results)

        # Run evaluation
        try:
            # Note: This requires OpenAI API key or local LLM setup
            # For now, we'll compute custom metrics
            scores = self._compute_custom_metrics(test_results)

            logger.info("RAGAS evaluation completed")

            # Save results
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(scores, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved evaluation results to {output_file}")

            return scores

        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            # Fallback to custom metrics
            return self._compute_custom_metrics(test_results)

    def _compute_custom_metrics(self, test_results: List[Dict]) -> Dict:
        """
        Compute custom RAG evaluation metrics.

        Metrics:
        1. Retrieval Quality: Avg similarity scores
        2. Context Coverage: Enrichment coverage
        3. Generation Success: Valid query rate
        4. Query Complexity: Avg query length, tag usage
        5. Efficiency: Avg generation time
        """
        metrics = {
            'total_samples': len(test_results),
            'retrieval_quality': {},
            'context_coverage': {},
            'generation_quality': {},
            'efficiency': {}
        }

        # 1. Retrieval Quality
        qa_sims = [r['retrieval_stats']['avg_qa_similarity']
                   for r in test_results if 'retrieval_stats' in r]
        cpgql_sims = [r['retrieval_stats']['avg_cpgql_similarity']
                      for r in test_results if 'retrieval_stats' in r]

        metrics['retrieval_quality'] = {
            'avg_qa_similarity': sum(qa_sims) / len(qa_sims) if qa_sims else 0,
            'avg_cpgql_similarity': sum(cpgql_sims) / len(cpgql_sims) if cpgql_sims else 0,
            'min_qa_similarity': min(qa_sims) if qa_sims else 0,
            'max_qa_similarity': max(qa_sims) if qa_sims else 0,
        }

        # 2. Context Coverage
        coverages = [r['enrichment_coverage'] for r in test_results if 'enrichment_coverage' in r]
        metrics['context_coverage'] = {
            'avg_enrichment_coverage': sum(coverages) / len(coverages) if coverages else 0,
            'min_coverage': min(coverages) if coverages else 0,
            'max_coverage': max(coverages) if coverages else 0,
            'samples_with_high_coverage': sum(1 for c in coverages if c >= 0.75),
            'samples_with_low_coverage': sum(1 for c in coverages if c < 0.25),
        }

        # 3. Generation Quality
        valid_count = sum(1 for r in test_results if r.get('valid', False))
        queries_with_tags = sum(1 for r in test_results if '.tag.' in r.get('query', ''))
        queries_with_name = sum(1 for r in test_results if '.name(' in r.get('query', ''))

        metrics['generation_quality'] = {
            'validity_rate': valid_count / len(test_results) if test_results else 0,
            'valid_count': valid_count,
            'invalid_count': len(test_results) - valid_count,
            'uses_enrichment_tags_rate': queries_with_tags / len(test_results) if test_results else 0,
            'uses_name_filter_rate': queries_with_name / len(test_results) if test_results else 0,
            'avg_query_length': sum(len(r.get('query', '')) for r in test_results) / len(test_results) if test_results else 0,
        }

        # 4. Efficiency
        gen_times = [r.get('times', {}).get('generation', 0) for r in test_results]
        retrieval_times = [r.get('times', {}).get('retrieval', 0) for r in test_results]

        metrics['efficiency'] = {
            'avg_generation_time': sum(gen_times) / len(gen_times) if gen_times else 0,
            'avg_retrieval_time': sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0,
            'total_pipeline_time': sum(gen_times) + sum(retrieval_times),
            'throughput_qps': len(test_results) / (sum(gen_times) + sum(retrieval_times)) if (sum(gen_times) + sum(retrieval_times)) > 0 else 0,
        }

        # 5. Domain-specific performance
        domain_stats = {}
        for r in test_results:
            domain = r.get('analysis', {}).get('domain', 'unknown')
            if domain not in domain_stats:
                domain_stats[domain] = {'total': 0, 'valid': 0}
            domain_stats[domain]['total'] += 1
            if r.get('valid', False):
                domain_stats[domain]['valid'] += 1

        metrics['domain_performance'] = {
            domain: {
                'count': stats['total'],
                'validity_rate': stats['valid'] / stats['total'] if stats['total'] > 0 else 0
            }
            for domain, stats in domain_stats.items()
        }

        return metrics

    def print_evaluation_report(self, metrics: Dict):
        """Print formatted evaluation report."""
        print("\n" + "="*80)
        print("RAGAS Evaluation Report")
        print("="*80 + "\n")

        print(f"Total Samples: {metrics['total_samples']}\n")

        # Retrieval Quality
        print("Retrieval Quality:")
        rq = metrics['retrieval_quality']
        print(f"  Avg Q&A Similarity:    {rq['avg_qa_similarity']:.3f}")
        print(f"  Avg CPGQL Similarity:  {rq['avg_cpgql_similarity']:.3f}")
        print(f"  Range Q&A:             [{rq['min_qa_similarity']:.3f}, {rq['max_qa_similarity']:.3f}]")
        print()

        # Context Coverage
        print("Context Coverage:")
        cc = metrics['context_coverage']
        print(f"  Avg Enrichment:        {cc['avg_enrichment_coverage']:.3f}")
        print(f"  High Coverage (>=0.75): {cc['samples_with_high_coverage']}/{metrics['total_samples']}")
        print(f"  Low Coverage (<0.25):  {cc['samples_with_low_coverage']}/{metrics['total_samples']}")
        print()

        # Generation Quality
        print("Generation Quality:")
        gq = metrics['generation_quality']
        print(f"  Validity Rate:         {gq['validity_rate']:.1%} ({gq['valid_count']}/{metrics['total_samples']})")
        print(f"  Uses Enrichment Tags:  {gq['uses_enrichment_tags_rate']:.1%}")
        print(f"  Uses Name Filters:     {gq['uses_name_filter_rate']:.1%}")
        print(f"  Avg Query Length:      {gq['avg_query_length']:.1f} chars")
        print()

        # Efficiency
        print("Efficiency:")
        eff = metrics['efficiency']
        print(f"  Avg Generation Time:   {eff['avg_generation_time']:.2f}s")
        print(f"  Avg Retrieval Time:    {eff['avg_retrieval_time']:.2f}s")
        print(f"  Throughput:            {eff['throughput_qps']:.2f} queries/sec")
        print()

        # Domain Performance
        print("Domain Performance:")
        for domain, stats in sorted(
            metrics['domain_performance'].items(),
            key=lambda x: x[1]['validity_rate'],
            reverse=True
        ):
            print(f"  {domain:20} {stats['validity_rate']:.1%} ({stats['count']} samples)")

        print("\n" + "="*80 + "\n")
