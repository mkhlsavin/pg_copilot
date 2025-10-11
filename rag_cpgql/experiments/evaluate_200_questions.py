"""Evaluate 200-question test results using RAGAS metrics."""
import sys
import logging
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def evaluate_200_questions():
    """Run RAGAS evaluation on 200-question test results."""

    print("\n" + "="*80)
    print("RAG-CPGQL RAGAS Evaluation - 200 Questions")
    print("="*80 + "\n")

    try:
        # Load 200-question test results
        results_file = Path(__file__).parent.parent / "results" / "test_200_questions_results.json"

        if not results_file.exists():
            print(f"Error: Results file not found: {results_file}")
            print("Please run test_200_questions.py first")
            return 1

        print(f"Loading test results from: {results_file}")
        with open(results_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        test_results = test_data['results']
        print(f"Loaded {len(test_results)} test results\n")

        # Initialize RAGAS evaluator
        print("Initializing RAGAS evaluator...")
        evaluator = RAGASEvaluator(use_local_llm=True)

        # Run evaluation
        print("Running evaluation...\n")
        output_file = Path(__file__).parent.parent / "results" / "ragas_evaluation_200q.json"
        metrics = evaluator.evaluate_rag_pipeline(test_results, output_file)

        # Print report
        evaluator.print_evaluation_report(metrics)

        print(f"\nDetailed results saved to: {output_file}")

        # Additional insights
        print("\n" + "="*80)
        print("Key Insights")
        print("="*80 + "\n")

        rq = metrics['retrieval_quality']
        gq = metrics['generation_quality']
        cc = metrics['context_coverage']

        print("Strengths:")
        if gq['validity_rate'] >= 0.9:
            print(f"  [+] Excellent query generation ({gq['validity_rate']:.1%} valid)")
        if rq['avg_qa_similarity'] >= 0.75:
            print(f"  [+] High-quality Q&A retrieval ({rq['avg_qa_similarity']:.3f} similarity)")
        if gq['uses_enrichment_tags_rate'] >= 0.4:
            print(f"  [+] Good enrichment tag utilization ({gq['uses_enrichment_tags_rate']:.1%})")

        print("\nAreas for Improvement:")
        if rq['avg_cpgql_similarity'] < 0.3:
            print(f"  [-] CPGQL example retrieval could be improved ({rq['avg_cpgql_similarity']:.3f} similarity)")
        if cc['samples_with_low_coverage'] > 0:
            print(f"  [-] {cc['samples_with_low_coverage']} samples have low enrichment coverage")
        if gq['uses_enrichment_tags_rate'] < 0.5:
            print(f"  [-] Only {gq['uses_enrichment_tags_rate']:.1%} queries use enrichment tags")

        print("\nRecommendations:")
        if rq['avg_cpgql_similarity'] < 0.3:
            print("  1. Improve CPGQL example embedding quality")
            print("  2. Add more diverse CPGQL examples to dataset")
        if cc['avg_enrichment_coverage'] < 0.5:
            print("  3. Expand enrichment tag mappings for more domains")
        if metrics['efficiency']['avg_generation_time'] > 5:
            print("  4. Optimize generation for better latency")

        # Statistical significance
        print("\n" + "="*80)
        print("Statistical Summary")
        print("="*80 + "\n")

        # Load statistical analysis from original results
        if 'statistical_analysis' in test_data:
            stats = test_data['statistical_analysis']
            print(f"Sample Size:           {stats['sample_size']}")
            print(f"Validity Rate:         {stats['validity_rate']:.1%}")
            print(f"Standard Error:        {stats['standard_error']:.4f}")
            print(f"95% Confidence:        [{stats['confidence_interval_95'][0]:.3f}, {stats['confidence_interval_95'][1]:.3f}]")
            print()
            print("Interpretation:")
            print(f"  With 95% confidence, the true validity rate is between")
            print(f"  {stats['confidence_interval_95'][0]:.1%} and {stats['confidence_interval_95'][1]:.1%}")

        print("\n" + "="*80 + "\n")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = evaluate_200_questions()
    sys.exit(exit_code)
