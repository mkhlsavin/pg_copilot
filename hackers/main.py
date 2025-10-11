"""
Main Orchestration Script for PostgreSQL Hackers QA Dataset Generator

This script runs the complete pipeline from scraping to final dataset.
"""
import argparse
import logging
import sys
import time
from datetime import datetime

import config
from utils import setup_logging, ensure_dir, format_duration

# Import pipeline modules
from scraper import MailingListScraper
from thread_parser import ThreadParser
from topic_clustering import TopicClusterer
from pg_source_context import SourceContextMapper
from llm_interface import LLMInterface
from qa_generator import QAGenerator
from dataset_builder import DatasetBuilder


logger = logging.getLogger(__name__)


def run_scraper(args):
    """Run mailing list scraper."""
    logger.info("=" * 60)
    logger.info("STEP 1: Scraping Mailing List")
    logger.info("=" * 60)

    start_time = time.time()

    scraper = MailingListScraper()

    # Load checkpoint if exists
    if not args.no_checkpoint:
        checkpoint_emails = scraper.load_checkpoint()
        if checkpoint_emails:
            logger.info(f"Resuming from checkpoint: {len(checkpoint_emails)} emails")
            scraper.emails = checkpoint_emails

    # Scrape
    scraper.scrape_all(max_archives=args.max_archives)

    # Save
    scraper.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Scraping complete in {format_duration(elapsed)}")

    return scraper.emails


def run_thread_parser(args):
    """Run thread parser."""
    logger.info("=" * 60)
    logger.info("STEP 2: Parsing Threads")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load raw emails
    raw_emails = load_json(config.RAW_THREADS_FILE)

    # Parse
    parser = ThreadParser(raw_emails)
    threads = parser.parse_threads()

    # Statistics
    stats = parser.get_statistics()
    logger.info(f"Thread Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Save
    parser.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Thread parsing complete in {format_duration(elapsed)}")

    return threads


def run_topic_clustering(args):
    """Run topic clustering."""
    logger.info("=" * 60)
    logger.info("STEP 3: Clustering Topics")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load threads
    data = load_json(config.PROCESSED_THREADS_FILE)
    threads = data.get('threads', [])

    # Cluster
    clusterer = TopicClusterer(threads)
    clusters = clusterer.cluster_threads()

    logger.info(f"Created {len(clusters.get('clusters', []))} topic clusters")

    # Save
    clusterer.save_to_json()

    elapsed = time.time() - start_time
    logger.info(f"Topic clustering complete in {format_duration(elapsed)}")

    return clusters


def run_source_mapping(args):
    """Run source context mapping."""
    logger.info("=" * 60)
    logger.info("STEP 4: Mapping to Source Code")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load clusters
    clustered_topics = load_json(config.CLUSTERED_TOPICS_FILE)

    # Map
    mapper = SourceContextMapper()
    mappings = mapper.map_topics_to_source(clustered_topics)

    # Save
    mapper.save_to_json(mappings)

    elapsed = time.time() - start_time
    logger.info(f"Source mapping complete in {format_duration(elapsed)}")

    return mappings


def run_qa_generation(args):
    """Run QA generation."""
    logger.info("=" * 60)
    logger.info("STEP 5: Generating QA Pairs")
    logger.info("=" * 60)

    start_time = time.time()

    from utils import load_json

    # Load data
    clustered_topics = load_json(config.CLUSTERED_TOPICS_FILE)
    source_mappings = load_json(config.SOURCE_MAPPING_FILE)
    processed_threads = load_json(config.PROCESSED_THREADS_FILE)

    # Initialize LLM
    logger.info("Loading LLM model...")
    llm = LLMInterface()
    llm.load_model()

    # Generate
    generator = QAGenerator(llm)
    qa_pairs = generator.generate_all(
        clustered_topics,
        source_mappings,
        processed_threads,
        max_clusters=args.max_clusters
    )

    # Save
    generator.save_to_jsonl()

    # Unload model
    llm.unload_model()

    elapsed = time.time() - start_time
    logger.info(f"QA generation complete in {format_duration(elapsed)}")
    logger.info(f"Generated {len(qa_pairs)} QA pairs")

    return qa_pairs


def run_dataset_builder(args):
    """Run dataset builder."""
    logger.info("=" * 60)
    logger.info("STEP 6: Building Final Dataset")
    logger.info("=" * 60)

    start_time = time.time()

    # Build
    builder = DatasetBuilder()
    builder.load_qa_pairs()

    # Validate
    validation_report = builder.validate_qa_pairs()

    # Deduplicate
    if not args.no_dedup:
        builder.deduplicate()

    # Add metadata
    builder.add_metadata()

    # Statistics
    stats = builder.generate_statistics()

    logger.info("Final Dataset Statistics:")
    logger.info(f"  Total QA pairs: {stats['total_qa_pairs']}")
    logger.info(f"  Unique source files: {stats['unique_source_files']}")
    logger.info(f"  Avg answer length: {stats['answer_length']['mean']:.0f} chars")

    # Export
    builder.export_dataset()

    # Report
    builder.create_report(stats, validation_report)

    elapsed = time.time() - start_time
    logger.info(f"Dataset building complete in {format_duration(elapsed)}")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Hackers Mailing List QA Dataset Generator"
    )

    # Pipeline control
    parser.add_argument('--all', action='store_true', help='Run entire pipeline')
    parser.add_argument('--scrape', action='store_true', help='Run scraper only')
    parser.add_argument('--parse', action='store_true', help='Run thread parser only')
    parser.add_argument('--cluster', action='store_true', help='Run topic clustering only')
    parser.add_argument('--map-source', action='store_true', help='Run source mapping only')
    parser.add_argument('--generate-qa', action='store_true', help='Run QA generation only')
    parser.add_argument('--build-dataset', action='store_true', help='Run dataset builder only')

    # Options
    parser.add_argument('--max-archives', type=int, help='Limit archives to scrape')
    parser.add_argument('--max-clusters', type=int, help='Limit clusters for QA generation')
    parser.add_argument('--no-checkpoint', action='store_true', help='Ignore checkpoints')
    parser.add_argument('--no-dedup', action='store_true', help='Skip deduplication')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    args = parser.parse_args()

    # Setup logging
    setup_logging(config.LOG_FILE, args.log_level)

    logger.info("=" * 60)
    logger.info("PostgreSQL Hackers QA Dataset Generator")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verify paths
    if not config.verify_paths():
        logger.error("Configuration errors found. Please fix and retry.")
        sys.exit(1)

    # Ensure directories exist
    ensure_dir(config.DATA_DIR)
    ensure_dir(config.OUTPUT_DIR)

    pipeline_start = time.time()

    try:
        # Determine what to run
        run_all = args.all or not any([
            args.scrape, args.parse, args.cluster,
            args.map_source, args.generate_qa, args.build_dataset
        ])

        # Run pipeline stages
        if run_all or args.scrape:
            run_scraper(args)

        if run_all or args.parse:
            run_thread_parser(args)

        if run_all or args.cluster:
            run_topic_clustering(args)

        if run_all or args.map_source:
            run_source_mapping(args)

        if run_all or args.generate_qa:
            run_qa_generation(args)

        if run_all or args.build_dataset:
            run_dataset_builder(args)

        # Final summary
        total_elapsed = time.time() - pipeline_start

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total time: {format_duration(total_elapsed)}")
        logger.info(f"Output directory: {config.OUTPUT_DIR}")
        logger.info("")
        logger.info("Generated files:")
        logger.info(f"  - {config.FINAL_DATASET_FILE}")
        logger.info(f"  - {config.DATASET_REPORT_FILE}")

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
