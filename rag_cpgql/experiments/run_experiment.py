"""Run RAG-CPGQL experiments with fine-tuned and base models."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import logging
import json
from datetime import datetime

from utils.config import load_config
from utils.data_loader import load_qa_pairs, load_cpgql_examples, save_json
from retrieval.vector_store import VectorStore
from generation.llm_interface import LLMInterface
from execution.joern_client import JoernClient
from rag_pipeline import RAGCPGQLPipeline
from evaluation.metrics import Evaluator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_experiment(
    model_name: str,
    model_path: str,
    test_data: list,
    vector_store: VectorStore,
    joern_client: JoernClient,
    config,
    limit: int = None
) -> dict:
    """
    Run experiment with a specific model.

    Args:
        model_name: Model identifier
        model_path: Path to model file
        test_data: Test Q&A pairs
        vector_store: Initialized vector store
        joern_client: Initialized Joern client
        config: Configuration object
        limit: Limit number of test examples (for quick testing)

    Returns:
        Dictionary with results
    """
    logger.info("=" * 80)
    logger.info(f"Running experiment with model: {model_name}")
    logger.info("=" * 80)

    # Limit test data if specified
    if limit:
        test_data = test_data[:limit]
        logger.info(f"Limited to {limit} test examples")

    # Initialize LLM
    logger.info(f"Loading model from: {model_path}")
    llm = LLMInterface(
        model_path=model_path,
        n_ctx=config.get('llm', 'n_ctx', default=8192),
        n_gpu_layers=config.get('llm', 'n_gpu_layers', default=-1),
        n_batch=config.get('llm', 'n_batch', default=512),
        n_threads=config.get('llm', 'n_threads', default=8)
    )

    # Initialize pipeline
    pipeline = RAGCPGQLPipeline(
        llm=llm,
        vector_store=vector_store,
        joern_client=joern_client,
        top_k_qa=config.top_k_qa,
        top_k_cpgql=config.top_k_cpgql
    )

    # Run batch
    logger.info(f"Processing {len(test_data)} test examples...")
    results = pipeline.run_batch(test_data)

    # Compute aggregate metrics
    evaluator = Evaluator()
    aggregate_metrics = evaluator.evaluate_batch(results)

    logger.info("\n" + "=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Model: {model_name}")
    logger.info(f"Total Questions: {aggregate_metrics['total_questions']}")
    logger.info(f"Query Validity Rate: {aggregate_metrics['query_validity_rate']:.2%}")
    logger.info(f"Execution Success Rate: {aggregate_metrics['execution_success_rate']:.2%}")
    logger.info(f"Avg Semantic Similarity: {aggregate_metrics['avg_semantic_similarity']:.3f}")
    logger.info(f"Avg Overall F1: {aggregate_metrics['avg_overall_f1']:.3f}")
    logger.info("=" * 80)

    return {
        'model_name': model_name,
        'model_path': model_path,
        'timestamp': datetime.now().isoformat(),
        'test_size': len(test_data),
        'aggregate_metrics': aggregate_metrics,
        'detailed_results': results
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run RAG-CPGQL experiments")
    parser.add_argument('--model', choices=['finetuned', 'base', 'both'], default='both',
                        help='Which model to test')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of test examples')
    parser.add_argument('--no-joern', action='store_true',
                        help='Skip Joern server startup (assumes already running)')
    args = parser.parse_args()

    # Load config
    config = load_config()

    logger.info("=" * 80)
    logger.info("RAG-CPGQL EXPERIMENTS")
    logger.info("=" * 80)

    # Load data
    logger.info("Loading test data...")
    test_data = load_qa_pairs(config.test_split)
    logger.info(f"Loaded {len(test_data)} test examples")

    logger.info("Loading training data for indexing...")
    train_data = load_qa_pairs(config.train_split)
    logger.info(f"Loaded {len(train_data)} training examples")

    logger.info("Loading CPGQL examples...")
    cpgql_examples = load_cpgql_examples(config.cpgql_examples)
    logger.info(f"Loaded {len(cpgql_examples)} CPGQL examples")

    # Initialize vector store
    logger.info("Initializing vector store...")
    vector_store = VectorStore(model_name=config.embedding_model)

    logger.info("Indexing training Q&A pairs...")
    vector_store.create_qa_index(train_data)

    logger.info("Indexing CPGQL examples...")
    vector_store.create_cpgql_index(cpgql_examples)

    stats = vector_store.get_stats()
    logger.info(f"Vector store stats: {stats}")

    # Initialize Joern client
    if not args.no_joern:
        logger.info("Starting Joern server...")
        joern = JoernClient(
            joern_cli_path=config.joern_cli_path,
            cpg_path=config.cpg_path,
            port=config.joern_port
        )
        if not joern.start_server(wait_time=20):
            logger.error("Failed to start Joern server")
            return
    else:
        logger.info("Using existing Joern server...")
        joern = JoernClient(
            joern_cli_path=config.joern_cli_path,
            cpg_path=config.cpg_path,
            port=config.joern_port
        )
        joern.process = None  # Indicate we didn't start it

    # Run experiments
    try:
        if args.model in ['finetuned', 'both']:
            logger.info("\n" + "=" * 80)
            logger.info("EXPERIMENT 1: Fine-tuned Model")
            logger.info("=" * 80 + "\n")

            finetuned_results = run_experiment(
                model_name='LLMxCPG-Q-32B',
                model_path=config.finetuned_model_path,
                test_data=test_data,
                vector_store=vector_store,
                joern_client=joern,
                config=config,
                limit=args.limit
            )

            # Save results
            output_file = 'results/rag_finetuned_results.json'
            save_json(finetuned_results, output_file)
            logger.info(f"Saved fine-tuned results to: {output_file}")

        if args.model in ['base', 'both']:
            logger.info("\n" + "=" * 80)
            logger.info("EXPERIMENT 2: Base Model")
            logger.info("=" * 80 + "\n")

            base_results = run_experiment(
                model_name='Qwen3-Coder-30B',
                model_path=config.base_model_path,
                test_data=test_data,
                vector_store=vector_store,
                joern_client=joern,
                config=config,
                limit=args.limit
            )

            # Save results
            output_file = 'results/rag_base_results.json'
            save_json(base_results, output_file)
            logger.info(f"Saved base results to: {output_file}")

    finally:
        # Stop Joern if we started it
        if not args.no_joern and joern.process:
            joern.stop_server()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXPERIMENTS COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
