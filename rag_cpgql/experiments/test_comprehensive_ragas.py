"""Comprehensive RAGAS Evaluation Suite.

This script runs a comprehensive evaluation using real RAGAS metrics on the test dataset
to measure and improve the RAG-CPGQL pipeline performance.

Usage:
    conda activate llama.cpp
    python experiments/test_comprehensive_ragas.py --samples 100
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List
import json
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.langgraph_workflow import run_workflow
from src.evaluation.ragas_evaluator import RAGASEvaluator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_questions(num_samples: int = 100) -> List[str]:
    """
    Load test questions from the test split.

    Args:
        num_samples: Number of questions to load

    Returns:
        List of question strings
    """
    test_file = project_root / "data" / "test_split_merged.jsonl"

    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return []

    questions = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            try:
                data = json.loads(line)
                questions.append(data['question'])
            except Exception as e:
                logger.warning(f"Failed to parse line {i}: {e}")
                continue

    logger.info(f"Loaded {len(questions)} test questions")
    return questions


def run_pipeline_on_questions(
    questions: List[str],
    verbose: bool = False
) -> List[Dict]:
    """
    Run the RAG-CPGQL pipeline on test questions.

    Args:
        questions: List of questions
        verbose: Enable verbose output

    Returns:
        List of result dicts
    """
    results = []

    total = len(questions)
    print(f"\nRunning pipeline on {total} questions...")
    print("="*80)

    for i, question in enumerate(questions, 1):
        try:
            start_time = time.time()

            # Run workflow using the correct API
            result = run_workflow(
                question=question,
                verbose=verbose,
                streaming=False
            )

            elapsed = time.time() - start_time

            # Extract relevant data for RAGAS
            test_result = {
                'question': question,
                'query': result.get('generated_query', ''),
                'valid': result.get('query_valid', False),
                'analysis': result.get('analysis', {}),
                'retrieval_stats': {
                    'qa_retrieved': len(result.get('similar_qa', [])),
                    'cpgql_retrieved': len(result.get('cpgql_examples', [])),
                    'avg_qa_similarity': _avg_similarity(result.get('similar_qa', [])),
                    'avg_cpgql_similarity': _avg_similarity(result.get('cpgql_examples', [])),
                },
                'enrichment_coverage': result.get('enrichment_hints', {}).get('coverage_score', 0.0),
                'enrichment_hints': result.get('enrichment_hints', {}),
                'times': {
                    'total': elapsed,
                    'generation': result.get('generation_time', 0),
                    'retrieval': result.get('retrieval_time', 0),
                },
                'execution_result': result.get('execution_result'),
                'answer': result.get('answer', ''),
                # For RAGAS evaluation
                'contexts': _extract_contexts(result),
                'ground_truth': result.get('ground_truth', 'Valid CPGQL query'),
            }

            results.append(test_result)

            # Progress indicator
            if i % 10 == 0 or i == total:
                valid_so_far = sum(1 for r in results if r['valid'])
                avg_coverage = sum(r['enrichment_coverage'] for r in results) / len(results)
                print(f"  [{i}/{total}] Valid: {valid_so_far}/{i} ({valid_so_far/i:.1%}), "
                      f"Avg Coverage: {avg_coverage:.3f}, Time: {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Failed to process question {i}: {e}")
            results.append({
                'question': question,
                'query': '',
                'valid': False,
                'error': str(e),
                'enrichment_coverage': 0.0,
                'contexts': [],
                'ground_truth': '',
                'answer': '',
            })

    print("="*80)
    print(f"\nCompleted {len(results)} questions\n")

    return results


def _avg_similarity(items: List[Dict]) -> float:
    """Calculate average similarity score from retrieval results."""
    if not items:
        return 0.0

    similarities = [item.get('similarity', 0.0) for item in items if isinstance(item, dict)]
    return sum(similarities) / len(similarities) if similarities else 0.0


def _extract_contexts(result: Dict) -> List[str]:
    """
    Extract context strings for RAGAS evaluation.

    Combines:
    - Similar Q&A pairs
    - CPGQL examples
    - Enrichment hints
    """
    contexts = []

    # Add Q&A context
    for qa in result.get('similar_qa', [])[:3]:
        if isinstance(qa, dict):
            q = qa.get('question', '')
            a = qa.get('answer', '')
            if q and a:
                contexts.append(f"Q: {q}\nA: {a}")

    # Add CPGQL examples
    for ex in result.get('cpgql_examples', [])[:3]:
        if isinstance(ex, dict):
            query = ex.get('query', '')
            desc = ex.get('description', '')
            if query:
                contexts.append(f"CPGQL: {query}\nDesc: {desc}" if desc else f"CPGQL: {query}")

    # Add enrichment context
    hints = result.get('enrichment_hints', {})
    if hints.get('subsystems'):
        contexts.append(f"Subsystems: {', '.join(hints['subsystems'])}")
    if hints.get('function_purposes'):
        contexts.append(f"Purposes: {', '.join(hints['function_purposes'])}")
    if hints.get('domain_concepts'):
        contexts.append(f"Concepts: {', '.join(hints['domain_concepts'])}")

    # If no contexts, add a placeholder
    if not contexts:
        contexts = ["No retrieval context available"]

    return contexts


def analyze_results(results: List[Dict]) -> Dict:
    """
    Analyze results and provide detailed insights.

    Args:
        results: List of test results

    Returns:
        Analysis dict with insights
    """
    analysis = {
        'total': len(results),
        'valid': sum(1 for r in results if r.get('valid', False)),
        'by_coverage': {
            'high (>=0.75)': [],
            'medium (0.4-0.75)': [],
            'low (<0.4)': []
        },
        'by_domain': {},
        'enrichment_impact': {},
        'issues': [],
    }

    # Categorize by coverage
    for r in results:
        coverage = r.get('enrichment_coverage', 0.0)
        if coverage >= 0.75:
            analysis['by_coverage']['high (>=0.75)'].append(r)
        elif coverage >= 0.4:
            analysis['by_coverage']['medium (0.4-0.75)'].append(r)
        else:
            analysis['by_coverage']['low (<0.4)'].append(r)

    # Analyze by domain
    for r in results:
        domain = r.get('analysis', {}).get('domain', 'unknown')
        if domain not in analysis['by_domain']:
            analysis['by_domain'][domain] = {'total': 0, 'valid': 0}
        analysis['by_domain'][domain]['total'] += 1
        if r.get('valid', False):
            analysis['by_domain'][domain]['valid'] += 1

    # Analyze enrichment impact
    high_cov_valid = sum(1 for r in analysis['by_coverage']['high (>=0.75)'] if r.get('valid', False))
    low_cov_valid = sum(1 for r in analysis['by_coverage']['low (<0.4)'] if r.get('valid', False))

    high_total = len(analysis['by_coverage']['high (>=0.75)'])
    low_total = len(analysis['by_coverage']['low (<0.4)'])

    analysis['enrichment_impact'] = {
        'high_coverage_validity': high_cov_valid / high_total if high_total > 0 else 0,
        'low_coverage_validity': low_cov_valid / low_total if low_total > 0 else 0,
        'improvement': (high_cov_valid / high_total - low_cov_valid / low_total) if (high_total > 0 and low_total > 0) else 0
    }

    # Identify issues
    if analysis['valid'] / analysis['total'] < 0.95:
        analysis['issues'].append(f"Validity rate below 95%: {analysis['valid']/analysis['total']:.1%}")

    low_count = len(analysis['by_coverage']['low (<0.4)'])
    if low_count > analysis['total'] * 0.2:
        analysis['issues'].append(f"{low_count} samples have low coverage (>{analysis['total']*0.2:.0f} expected)")

    return analysis


def print_analysis_report(analysis: Dict):
    """Print detailed analysis report."""
    print("\n" + "="*80)
    print("DETAILED ANALYSIS REPORT")
    print("="*80 + "\n")

    print(f"Total Samples: {analysis['total']}")
    print(f"Valid Queries: {analysis['valid']} ({analysis['valid']/analysis['total']:.1%})")
    print()

    print("Coverage Distribution:")
    for level, samples in analysis['by_coverage'].items():
        count = len(samples)
        valid_count = sum(1 for s in samples if s.get('valid', False))
        print(f"  {level:20s}: {count:3d} samples ({valid_count:3d} valid, {valid_count/count:.1%})" if count > 0 else f"  {level:20s}: {count:3d} samples")
    print()

    print("Domain Performance:")
    for domain, stats in sorted(analysis['by_domain'].items(), key=lambda x: x[1]['valid']/max(x[1]['total'],1), reverse=True):
        validity = stats['valid'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {domain:20s}: {validity:.1%} ({stats['valid']}/{stats['total']})")
    print()

    print("Enrichment Impact:")
    ei = analysis['enrichment_impact']
    print(f"  High coverage validity:  {ei['high_coverage_validity']:.1%}")
    print(f"  Low coverage validity:   {ei['low_coverage_validity']:.1%}")
    print(f"  Impact (delta):          {ei['improvement']:+.1%}")
    print()

    if analysis['issues']:
        print("Issues Identified:")
        for issue in analysis['issues']:
            print(f"  - {issue}")
        print()

    print("="*80 + "\n")


def save_results(results: List[Dict], analysis: Dict, metrics: Dict, output_dir: Path):
    """Save results and metrics to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save detailed results
    results_file = output_dir / f"comprehensive_ragas_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total_samples': len(results),
            'results': results,
            'analysis': analysis,
            'ragas_metrics': metrics,
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved detailed results to {results_file}")

    # Save summary report
    summary_file = output_dir / f"ragas_summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"RAGAS Evaluation Summary - {timestamp}\n")
        f.write("="*80 + "\n\n")

        f.write(f"Total Samples: {len(results)}\n")
        f.write(f"Valid Queries: {analysis['valid']} ({analysis['valid']/analysis['total']:.1%})\n\n")

        f.write("RAGAS Metrics:\n")
        for category, values in metrics.items():
            if isinstance(values, dict):
                f.write(f"\n{category.replace('_', ' ').title()}:\n")
                for key, val in values.items():
                    if isinstance(val, (int, float)):
                        f.write(f"  {key}: {val:.3f}\n" if isinstance(val, float) else f"  {key}: {val}\n")

        f.write("\n" + "="*80 + "\n")

    logger.info(f"Saved summary to {summary_file}")

    return results_file, summary_file


def main():
    """Run comprehensive RAGAS evaluation."""
    parser = argparse.ArgumentParser(description="Comprehensive RAGAS Evaluation")
    parser.add_argument('--samples', type=int, default=100, help='Number of test samples (default: 100)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--output-dir', type=Path, default=project_root / 'results', help='Output directory')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("COMPREHENSIVE RAGAS EVALUATION SUITE")
    print("="*80 + "\n")

    print(f"Configuration:")
    print(f"  Samples: {args.samples}")
    print(f"  Output: {args.output_dir}")
    print()

    # Create output directory
    args.output_dir.mkdir(exist_ok=True, parents=True)

    # Step 1: Load test questions
    print("Step 1: Loading test questions...")
    questions = load_test_questions(args.samples)

    if not questions:
        print("ERROR: No test questions loaded")
        return 1

    print(f"✓ Loaded {len(questions)} questions\n")

    # Step 2: Run pipeline
    print("Step 2: Running RAG-CPGQL pipeline...")
    results = run_pipeline_on_questions(questions, verbose=args.verbose)

    if not results:
        print("ERROR: No results generated")
        return 1

    print(f"✓ Generated {len(results)} results\n")

    # Step 3: Run RAGAS evaluation
    print("Step 3: Running RAGAS evaluation...")
    evaluator = RAGASEvaluator(use_local_llm=True)
    metrics = evaluator.evaluate_rag_pipeline(results)

    print("✓ RAGAS evaluation completed\n")

    # Step 4: Analyze results
    print("Step 4: Analyzing results...")
    analysis = analyze_results(results)

    print("✓ Analysis completed\n")

    # Step 5: Print reports
    evaluator.print_evaluation_report(metrics)
    print_analysis_report(analysis)

    # Step 6: Save results
    print("Step 5: Saving results...")
    results_file, summary_file = save_results(results, analysis, metrics, args.output_dir)

    print(f"✓ Results saved to {args.output_dir}\n")

    # Step 7: Print recommendations
    print("="*80)
    print("IMPROVEMENT RECOMMENDATIONS")
    print("="*80 + "\n")

    # Analyze metrics and provide recommendations
    rq = metrics['retrieval_quality']
    cc = metrics['context_coverage']
    gq = metrics['generation_quality']

    recommendations = []

    if cc['avg_enrichment_coverage'] < 0.6:
        recommendations.append(
            f"1. LOW ENRICHMENT COVERAGE ({cc['avg_enrichment_coverage']:.2f} < 0.60):\n"
            f"   - Review Phase 4 fallback strategies effectiveness\n"
            f"   - Add more keyword-to-tag patterns\n"
            f"   - Expand domain coverage in enrichment mappings"
        )

    if rq['avg_cpgql_similarity'] < 0.3:
        recommendations.append(
            f"2. LOW CPGQL SIMILARITY ({rq['avg_cpgql_similarity']:.2f} < 0.30):\n"
            f"   - Improve CPGQL example embeddings\n"
            f"   - Add more diverse CPGQL examples to dataset\n"
            f"   - Review retrieval ranking algorithm"
        )

    if gq['validity_rate'] < 0.95:
        recommendations.append(
            f"3. VALIDITY BELOW TARGET ({gq['validity_rate']:.1%} < 95%):\n"
            f"   - Review validation rules\n"
            f"   - Improve prompt engineering\n"
            f"   - Add more refinement iterations"
        )

    if gq['uses_enrichment_tags_rate'] < 0.5:
        recommendations.append(
            f"4. LOW TAG USAGE ({gq['uses_enrichment_tags_rate']:.1%} < 50%):\n"
            f"   - Strengthen tag-based prompt examples\n"
            f"   - Increase tag confidence scoring\n"
            f"   - Review prompt template effectiveness"
        )

    if analysis['enrichment_impact']['improvement'] < 0.1:
        recommendations.append(
            f"5. LOW ENRICHMENT IMPACT ({analysis['enrichment_impact']['improvement']:+.1%} < +10%):\n"
            f"   - Validate enrichment integration in prompts\n"
            f"   - Review tag effectiveness tracking\n"
            f"   - Consider enrichment-aware query patterns"
        )

    if recommendations:
        for rec in recommendations:
            print(rec)
            print()
    else:
        print("✓ All metrics within acceptable ranges!")
        print("  - Enrichment coverage: {:.2f} (target: >0.60)".format(cc['avg_enrichment_coverage']))
        print("  - Validity rate: {:.1%} (target: >95%)".format(gq['validity_rate']))
        print("  - Tag usage: {:.1%} (target: >50%)".format(gq['uses_enrichment_tags_rate']))
        print("  - Enrichment impact: {:+.1%} (target: >+10%)".format(analysis['enrichment_impact']['improvement']))
        print()

    print("="*80 + "\n")

    print(f"Evaluation complete! Results saved to:")
    print(f"  - {results_file}")
    print(f"  - {summary_file}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
