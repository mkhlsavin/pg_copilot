"""
Main Orchestration Script for PostgreSQL Books QA Dataset Generator

This script runs the complete pipeline from PDF extraction to final dataset.
"""
import argparse
import logging
import sys
import time
from datetime import datetime

import config
from utils import setup_logging, ensure_dir, format_duration

# Import pipeline modules
from pdf_extractor import PDFExtractor
from content_chunker import ContentChunker
# Reuse from hackers (will need to copy/symlink)
from topic_clustering import TopicClusterer
from pg_source_context import SourceContextMapper
from llm_interface import LLMInterface
from qa_generator import QAGenerator
from dataset_builder import DatasetBuilder


logger = logging.getLogger(__name__)


def run_extraction(args):
    """Extract content from PDF books."""
    logger.info("=" * 60)
    logger.info("STEP 1: Extracting Content from PDFs")
    logger.info("=" * 60)

    start_time = time.time()

    extractor = PDFExtractor()
    content = extractor.extract_all_pdfs(pdf_dir=config.PDF_DIR)

    # Save extracted content
    extractor.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Extraction complete in {format_duration(elapsed)}")
    logger.info(f"Extracted {len(content)} items from {extractor.pdf_count} PDF(s)")

    return content


def run_chunking(args):
    """Chunk extracted content."""
    logger.info("=" * 60)
    logger.info("STEP 2: Chunking Content")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load extracted content
    content = load_json(config.EXTRACTED_CONTENT_FILE)

    # Chunk
    chunker = ContentChunker(content)
    chunks = chunker.chunk_content()

    # Statistics
    stats = chunker.get_statistics()
    logger.info(f"Chunking Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Save
    chunker.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Chunking complete in {format_duration(elapsed)}")

    return chunks


def run_topic_clustering(args):
    """Run topic clustering."""
    logger.info("=" * 60)
    logger.info("STEP 3: Clustering Topics")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load chunks
    data = load_json(config.CHUNKED_CONTENT_FILE)

    # TopicClusterer expects dicts with 'text' field (already have that)
    # It will extract texts internally
    clusterer = TopicClusterer(data)

    # Cluster (n_clusters is set in config or auto-determined)
    if args.n_clusters:
        # Temporarily set config value
        import config as cfg
        cfg.N_CLUSTERS = args.n_clusters
    clusters = clusterer.cluster_threads()

    # Save
    clusterer.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Clustering complete in {format_duration(elapsed)}")
    logger.info(f"Created {len(clusters)} clusters")

    return clusters


def run_source_mapping(args):
    """Map topics to PostgreSQL source code."""
    logger.info("=" * 60)
    logger.info("STEP 4: Mapping to PostgreSQL Source Code")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load clusters
    clusters = load_json(config.CLUSTERED_TOPICS_FILE)

    # Map to source
    mapper = SourceContextMapper()
    mapping = mapper.map_topics_to_source(clusters)

    # Save
    mapper.save_to_json(mapping)

    elapsed = time.time() - start_time
    logger.info(f"Source mapping complete in {format_duration(elapsed)}")

    return mapping


def run_qa_generation(args):
    """Generate QA pairs."""
    logger.info("=" * 60)
    logger.info("STEP 5: Generating QA Pairs")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load data
    chunks = load_json(config.CHUNKED_CONTENT_FILE)
    clusters = load_json(config.CLUSTERED_TOPICS_FILE)
    source_mapping = load_json(config.SOURCE_MAPPING_FILE)

    # Initialize LLM
    logger.info("Loading LLM model...")
    llm = LLMInterface()
    llm.load_model()  # Load the model before generating

    # Generate QA pairs
    generator = QAGenerator(llm)

    # Wrap chunks in expected format (add thread_id to each chunk)
    for i, chunk in enumerate(chunks):
        chunk['thread_id'] = f"chunk_{i}"

    qa_pairs = generator.generate_all(
        clustered_topics=clusters,
        source_mappings=source_mapping,
        processed_threads={'threads': chunks},  # Wrap chunks in dict with 'threads' key
        max_clusters=args.max_clusters
    )

    # Save QA pairs
    from utils import save_json
    import jsonlines

    # Save as JSONL
    with jsonlines.open(config.QA_PAIRS_FILE, 'w') as writer:
        for qa in qa_pairs:
            writer.write(qa)
    logger.info(f"Saved {len(qa_pairs)} QA pairs to {config.QA_PAIRS_FILE}")

    elapsed = time.time() - start_time
    logger.info(f"QA generation complete in {format_duration(elapsed)}")
    logger.info(f"Generated {len(qa_pairs)} QA pairs")

    return qa_pairs


def run_dataset_builder(args):
    """Build final dataset."""
    logger.info("=" * 60)
    logger.info("STEP 6: Building Final Dataset")
    logger.info("=" * 60)

    start_time = time.time()

    import jsonlines

    # Build dataset
    builder = DatasetBuilder(config.QA_PAIRS_FILE)

    # Load QA pairs
    builder.load_qa_pairs()

    # Validate
    validation_results = builder.validate_qa_pairs()
    logger.info(f"Validation Results:")
    logger.info(f"  Total QA pairs: {validation_results.get('total', 0)}")
    logger.info(f"  Valid: {validation_results.get('valid', 0)}")
    logger.info(f"  Invalid: {validation_results.get('invalid', 0)}")

    # Deduplicate
    builder.deduplicate()

    # Add metadata
    builder.add_metadata()

    # Generate statistics
    stats = builder.generate_statistics()

    # Export dataset
    builder.export_dataset()

    # Create report
    builder.create_report(stats, validation_results)

    elapsed = time.time() - start_time
    logger.info(f"Dataset building complete in {format_duration(elapsed)}")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Books QA Dataset Generator"
    )

    # Pipeline stages
    parser.add_argument('--extract', action='store_true',
                        help='Extract content from PDFs')
    parser.add_argument('--chunk', action='store_true',
                        help='Chunk extracted content')
    parser.add_argument('--cluster', action='store_true',
                        help='Cluster topics')
    parser.add_argument('--map-source', action='store_true',
                        help='Map to PostgreSQL source')
    parser.add_argument('--generate-qa', action='store_true',
                        help='Generate QA pairs')
    parser.add_argument('--build-dataset', action='store_true',
                        help='Build final dataset')
    parser.add_argument('--all', action='store_true',
                        help='Run complete pipeline')

    # Parameters
    parser.add_argument('--n-clusters', type=int, default=None,
                        help='Number of topic clusters (default: auto)')
    parser.add_argument('--max-clusters', type=int, default=None,
                        help='Maximum clusters to process (for testing)')
    parser.add_argument('--qa-per-cluster', type=int, default=5,
                        help='QA pairs per cluster (default: 5)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_file=config.LOG_FILE, log_level=config.LOG_LEVEL)

    # Ensure directories exist
    ensure_dir(config.DATA_DIR)
    ensure_dir(config.OUTPUT_DIR)

    # Log configuration
    logger.info("=" * 60)
    logger.info("PostgreSQL Books QA Dataset Generator")
    logger.info("=" * 60)
    logger.info(f"PDF Directory: {config.PDF_DIR}")
    logger.info(f"PostgreSQL Source: {config.PG_SOURCE_PATH}")
    logger.info(f"LLM Model: {config.MODEL_PATH}")
    logger.info("=" * 60)

    pipeline_start = time.time()

    try:
        # Run pipeline stages
        if args.all or args.extract:
            run_extraction(args)

        if args.all or args.chunk:
            run_chunking(args)

        if args.all or args.cluster:
            run_topic_clustering(args)

        if args.all or args.map_source:
            run_source_mapping(args)

        if args.all or args.generate_qa:
            run_qa_generation(args)

        if args.all or args.build_dataset:
            run_dataset_builder(args)

        pipeline_elapsed = time.time() - pipeline_start
        logger.info("=" * 60)
        logger.info(f"Pipeline completed successfully in {format_duration(pipeline_elapsed)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
