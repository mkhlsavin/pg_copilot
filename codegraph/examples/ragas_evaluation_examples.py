"""
RAGAS Evaluation Examples

Examples demonstrating how to use RAGAS evaluation with different LLM providers.

Author: Configurable LLM Architecture - Week 2
Date: November 25, 2025

Usage:
    # Example 1: Default config (from config.yaml)
    python examples/ragas_evaluation_examples.py --example default

    # Example 2: Local LLM
    python examples/ragas_evaluation_examples.py --example local

    # Example 3: GigaChat
    python examples/ragas_evaluation_examples.py --example gigachat

    # Example 4: Custom config
    python examples/ragas_evaluation_examples.py --example custom
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_1_default_config():
    """
    Example 1: Use RAGAS with default configuration from config.yaml

    This uses whatever LLM provider is configured in config.yaml (llm.provider).
    """
    print("\n" + "="*80)
    print("Example 1: RAGAS with Default Config")
    print("="*80 + "\n")

    from src.evaluation.ragas_config import create_ragas_evaluator

    # Create evaluator from config.yaml
    evaluator = create_ragas_evaluator()

    # Prepare mock test results
    test_results = _get_mock_test_results()

    # Run evaluation
    print("Running RAGAS evaluation...")
    scores = evaluator.evaluate_rag_pipeline(
        test_results,
        output_file=Path("results/ragas_default_example.json")
    )

    # Print results
    print("\nRASAS Metrics:")
    if scores.get('ragas_metrics'):
        for metric, value in scores['ragas_metrics'].items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("  RAGAS metrics not available (using custom metrics)")

    print("\nCustom Metrics:")
    print(f"  Validity Rate: {scores['custom_metrics']['generation_quality']['validity_rate']:.2%}")
    print(f"  Avg QA Similarity: {scores['custom_metrics']['retrieval_quality']['avg_qa_similarity']:.4f}")

    print("\n✓ Example 1 completed successfully!")


def example_2_local_llm():
    """
    Example 2: Use RAGAS with local LLM (llama-cpp-python)

    Explicitly uses LocalLLMProvider for RAGAS evaluation.
    """
    print("\n" + "="*80)
    print("Example 2: RAGAS with Local LLM")
    print("="*80 + "\n")

    from src.evaluation.ragas_config import get_ragas_evaluator_with_local_llm

    # Create evaluator with local LLM
    evaluator = get_ragas_evaluator_with_local_llm()

    # Prepare mock test results
    test_results = _get_mock_test_results()

    # Run evaluation
    print("Running RAGAS evaluation with local LLM...")
    scores = evaluator.evaluate_rag_pipeline(
        test_results,
        output_file=Path("results/ragas_local_example.json")
    )

    # Print results
    print("\nRASAS Metrics:")
    if scores.get('ragas_metrics'):
        for metric, value in scores['ragas_metrics'].items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("  RAGAS metrics not available")

    print("\n✓ Example 2 completed successfully!")


def example_3_gigachat():
    """
    Example 3: Use RAGAS with GigaChat API

    Uses GigaChatProvider for RAGAS evaluation. Requires GIGACHAT_CREDENTIALS env var.
    """
    print("\n" + "="*80)
    print("Example 3: RAGAS with GigaChat API")
    print("="*80 + "\n")

    import os

    # Check if credentials are available
    if not os.getenv('GIGACHAT_CREDENTIALS'):
        print("⚠ GIGACHAT_CREDENTIALS not set. Skipping GigaChat example.")
        print("Set credentials with: export GIGACHAT_CREDENTIALS='your_credentials_here'")
        return

    from src.evaluation.ragas_config import get_ragas_evaluator_with_gigachat

    # Create evaluator with GigaChat
    evaluator = get_ragas_evaluator_with_gigachat(model="GigaChat-Pro")

    # Prepare mock test results
    test_results = _get_mock_test_results()

    # Run evaluation
    print("Running RAGAS evaluation with GigaChat-Pro...")
    scores = evaluator.evaluate_rag_pipeline(
        test_results,
        output_file=Path("results/ragas_gigachat_example.json")
    )

    # Print results
    print("\nRASAS Metrics:")
    if scores.get('ragas_metrics'):
        for metric, value in scores['ragas_metrics'].items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("  RAGAS metrics not available")
        if scores.get('ragas_error'):
            print(f"  Error: {scores['ragas_error']}")

    print("\n✓ Example 3 completed successfully!")


def example_4_custom_config():
    """
    Example 4: Use RAGAS with custom configuration

    Demonstrates how to create custom RAGAS config with specific settings.
    """
    print("\n" + "="*80)
    print("Example 4: RAGAS with Custom Config")
    print("="*80 + "\n")

    from src.llm import create_llm_provider, LLMConfig
    from src.evaluation import RAGASEvaluator

    # Create custom LLM config
    custom_config = {
        'llm': {
            'provider': 'local',
            'local': {
                'use_llmxcpg': True,
                'temperature': 0.5,  # Lower temperature for more focused evaluation
                'max_tokens': 256
            }
        }
    }

    # Create provider
    provider = create_llm_provider(custom_config)

    # Create evaluator
    evaluator = RAGASEvaluator(llm_provider=provider)

    # Prepare mock test results
    test_results = _get_mock_test_results()

    # Run evaluation with custom settings
    print("Running RAGAS evaluation with custom config (temp=0.5)...")
    scores = evaluator.evaluate_rag_pipeline(
        test_results,
        output_file=Path("results/ragas_custom_example.json"),
        use_ragas=True  # Explicitly enable RAGAS metrics
    )

    # Print results
    print("\nRASAS Metrics:")
    if scores.get('ragas_metrics'):
        for metric, value in scores['ragas_metrics'].items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("  RAGAS metrics not available")

    print("\nCustom Metrics (for comparison):")
    print(f"  Validity Rate: {scores['custom_metrics']['generation_quality']['validity_rate']:.2%}")

    print("\n✓ Example 4 completed successfully!")


def example_5_preset_configs():
    """
    Example 5: Use predefined RAGAS configurations

    Demonstrates using preset configs like 'local_fast', 'gigachat_full', etc.
    """
    print("\n" + "="*80)
    print("Example 5: RAGAS with Preset Configs")
    print("="*80 + "\n")

    from src.evaluation.ragas_config import get_preset_config, RAGAS_CONFIGS
    from src.evaluation import RAGASEvaluator

    # Show available presets
    print("Available presets:")
    for preset_name in RAGAS_CONFIGS.keys():
        print(f"  - {preset_name}")
    print()

    # Use 'local_fast' preset
    print("Using 'local_fast' preset...")
    config = get_preset_config('local_fast')
    provider = config.create_llm_provider()
    evaluator = RAGASEvaluator(llm_provider=provider)

    # Prepare mock test results
    test_results = _get_mock_test_results()

    # Run evaluation
    print(f"Running RAGAS with metrics: {config.metrics}")
    scores = evaluator.evaluate_rag_pipeline(
        test_results,
        output_file=Path("results/ragas_preset_example.json")
    )

    print("\nRASAS Metrics:")
    if scores.get('ragas_metrics'):
        for metric, value in scores['ragas_metrics'].items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("  RAGAS metrics not available")

    print("\n✓ Example 5 completed successfully!")


def _get_mock_test_results() -> List[Dict]:
    """
    Create mock test results for demonstration.

    In real usage, these would come from your actual RAG pipeline evaluation.
    """
    return [
        {
            'question': 'How does PostgreSQL implement MVCC?',
            'query': 'cpg.method.name("GetTransactionSnapshot").l',
            'valid': True,
            'retrieval_stats': {
                'qa_retrieved': 3,
                'cpgql_retrieved': 5,
                'avg_qa_similarity': 0.85,
                'avg_cpgql_similarity': 0.78
            },
            'enrichment_coverage': 0.65,
            'times': {
                'generation': 1.5,
                'retrieval': 0.3
            },
            'analysis': {
                'domain': 'concurrency'
            }
        },
        {
            'question': 'Find all heap tuple operations',
            'query': 'cpg.method.name(".*heap.*tuple.*").l',
            'valid': True,
            'retrieval_stats': {
                'qa_retrieved': 3,
                'cpgql_retrieved': 5,
                'avg_qa_similarity': 0.72,
                'avg_cpgql_similarity': 0.81
            },
            'enrichment_coverage': 0.82,
            'times': {
                'generation': 1.2,
                'retrieval': 0.4
            },
            'analysis': {
                'domain': 'storage'
            }
        },
        {
            'question': 'Show buffer manager functions',
            'query': 'cpg.method.name(".*Buffer.*").tag.name("category:storage").l',
            'valid': True,
            'retrieval_stats': {
                'qa_retrieved': 3,
                'cpgql_retrieved': 5,
                'avg_qa_similarity': 0.88,
                'avg_cpgql_similarity': 0.85
            },
            'enrichment_coverage': 0.91,
            'times': {
                'generation': 1.3,
                'retrieval': 0.35
            },
            'analysis': {
                'domain': 'storage'
            }
        }
    ]


def main():
    """Run examples based on command line argument."""
    import argparse

    parser = argparse.ArgumentParser(description="RAGAS Evaluation Examples")
    parser.add_argument(
        '--example',
        choices=['default', 'local', 'gigachat', 'custom', 'preset', 'all'],
        default='all',
        help='Which example to run'
    )

    args = parser.parse_args()

    # Create results directory
    Path("results").mkdir(exist_ok=True)

    try:
        if args.example == 'default' or args.example == 'all':
            example_1_default_config()

        if args.example == 'local' or args.example == 'all':
            example_2_local_llm()

        if args.example == 'gigachat' or args.example == 'all':
            example_3_gigachat()

        if args.example == 'custom' or args.example == 'all':
            example_4_custom_config()

        if args.example == 'preset' or args.example == 'all':
            example_5_preset_configs()

        print("\n" + "="*80)
        print("All examples completed! Check results/ directory for output files.")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
