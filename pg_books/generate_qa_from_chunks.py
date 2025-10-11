"""
Direct QA Generation from Chunks

This script generates QA pairs directly from each chunk without clustering,
treating each chunk as its own topic. This bypasses the clustering limitation
where similar embeddings collapse into very few clusters.

Strategy:
- Load chunks and determine QA pairs per chunk based on token count:
  * Long chunks (>400 tokens): 2 QA pairs
  * Medium chunks (150-400 tokens): 1 QA pair
  * Short chunks (<150 tokens): skip or enhance with source code context
- Checkpoint system for resume capability
"""

import json
import jsonlines
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional
from tqdm import tqdm

import config
from utils import setup_logging, load_json
from llm_interface import LLMInterface
from qa_generator import QAGenerator

logger = logging.getLogger(__name__)

# Token count thresholds
LONG_CHUNK_THRESHOLD = 400
MEDIUM_CHUNK_THRESHOLD = 150
MIN_CHUNK_THRESHOLD = 50


def determine_qa_pairs(chunk: Dict) -> int:
    """
    Determine number of QA pairs to generate based on chunk token count.

    Args:
        chunk: Chunk dictionary with token_count field

    Returns:
        Number of QA pairs to generate (0, 1, or 2)
    """
    token_count = chunk.get('token_count', 0)

    if token_count >= LONG_CHUNK_THRESHOLD:
        return 2
    elif token_count >= MEDIUM_CHUNK_THRESHOLD:
        return 1
    elif token_count >= MIN_CHUNK_THRESHOLD:
        return 1  # Still generate for shorter chunks if they have some substance
    else:
        return 0  # Skip very short chunks


def load_checkpoint(checkpoint_file: str) -> set:
    """
    Load processed chunk IDs from checkpoint file.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        Set of processed chunk indices
    """
    processed = set()

    if not os.path.exists(checkpoint_file):
        return processed

    try:
        with jsonlines.open(checkpoint_file, 'r') as reader:
            for qa in reader:
                # Extract chunk index from cluster_id or thread_id
                cluster_id = qa.get('cluster_id')
                if cluster_id is not None:
                    processed.add(cluster_id)

        logger.info(f"Loaded checkpoint: {len(processed)} chunks already processed")
    except Exception as e:
        logger.warning(f"Error loading checkpoint: {e}")

    return processed


def create_pseudo_clusters_from_chunks(chunks: List[Dict], skip_indices: set = None) -> Dict:
    """
    Create pseudo-clusters where each chunk is treated as its own cluster.

    Args:
        chunks: List of text chunks
        skip_indices: Set of chunk indices to skip (already processed)

    Returns:
        Clustered topics dictionary compatible with QAGenerator
    """
    if skip_indices is None:
        skip_indices = set()

    clusters = []

    for i, chunk in enumerate(chunks):
        # Skip already processed chunks
        if i in skip_indices:
            continue

        # Determine QA pairs count
        qa_pairs = determine_qa_pairs(chunk)

        # Skip if no QA pairs should be generated
        if qa_pairs == 0:
            logger.debug(f"Skipping chunk {i}: too short ({chunk.get('token_count', 0)} tokens)")
            continue

        # Create meaningful label from chunk metadata
        source_type = chunk.get('source_type', 'unknown')

        if source_type in ('README', 'C_COMMENT'):
            file_path = chunk.get('relative_path', chunk.get('file_path', 'Unknown'))
            line_start = chunk.get('line_start', '')
            label = f"{file_path}:{line_start}" if line_start else file_path
        else:
            chapter = chunk.get('chapter', 'Unknown')
            section = chunk.get('section', '')
            if section:
                label = f"{chapter} - {section}"
            else:
                label = chapter

        # Each chunk becomes its own cluster with specific QA pairs count
        cluster = {
            'cluster_id': i,
            'label': label,
            'keywords': [],
            'thread_count': 1,
            'qa_pairs_count': qa_pairs,  # Add QA pairs count to cluster
            'threads': [
                {
                    'thread_id': f"chunk_{i}",
                    'thread_index': i,
                    **chunk
                }
            ]
        }
        clusters.append(cluster)

    logger.info(f"Created {len(clusters)} pseudo-clusters from chunks (skipped {len(skip_indices)} processed)")

    return {'clusters': clusters}


def create_dummy_source_mapping(n_clusters: int) -> Dict:
    """
    Create dummy source mapping for each pseudo-cluster.

    Since source mapping is optional for QA generation, we create
    minimal placeholders.
    """
    mappings = []

    for i in range(n_clusters):
        mapping = {
            'cluster_id': i,
            'source_files': [],
            'confidence': 0.0
        }
        mappings.append(mapping)

    return {'mappings': mappings}


def main():
    """Generate QA pairs directly from chunks."""

    import argparse
    parser = argparse.ArgumentParser(description="Generate QA pairs directly from chunks")
    parser.add_argument('--test', action='store_true', help='Test mode with first 5 chunks')
    parser.add_argument('--max-chunks', type=int, default=None, help='Maximum chunks to process')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_file=config.LOG_FILE, log_level=config.LOG_LEVEL)

    logger.info("=" * 60)
    logger.info("Direct Chunk-to-QA Generation (Dynamic)")
    logger.info("=" * 60)
    logger.info(f"Long chunks (>={LONG_CHUNK_THRESHOLD} tokens): 2 QA pairs")
    logger.info(f"Medium chunks ({MEDIUM_CHUNK_THRESHOLD}-{LONG_CHUNK_THRESHOLD} tokens): 1 QA pair")
    logger.info(f"Short chunks (<{MEDIUM_CHUNK_THRESHOLD} tokens): 1 QA pair (if >{MIN_CHUNK_THRESHOLD})")
    logger.info(f"Very short chunks (<{MIN_CHUNK_THRESHOLD} tokens): skip")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        # Load chunks
        logger.info("Loading chunked content...")

        if args.test:
            chunks = load_json('data/chunked_content_test.json')
            logger.info(f"TEST MODE: Loaded {len(chunks)} test chunks")
        else:
            chunks = load_json(config.CHUNKED_CONTENT_FILE)
            logger.info(f"Loaded {len(chunks)} chunks")

        # Limit chunks if requested
        if args.max_chunks is not None:
            chunks = chunks[:args.max_chunks]
            logger.info(f"Limited to {len(chunks)} chunks")

        # Load checkpoint if resuming
        processed_indices = set()
        if args.resume:
            logger.info("Resume mode enabled, loading checkpoint...")
            processed_indices = load_checkpoint(config.QA_CHECKPOINT_FILE)

        # Analyze token distribution
        token_counts = [c.get('token_count', 0) for c in chunks]
        long_chunks = sum(1 for t in token_counts if t >= LONG_CHUNK_THRESHOLD)
        medium_chunks = sum(1 for t in token_counts if MEDIUM_CHUNK_THRESHOLD <= t < LONG_CHUNK_THRESHOLD)
        short_chunks = sum(1 for t in token_counts if MIN_CHUNK_THRESHOLD <= t < MEDIUM_CHUNK_THRESHOLD)
        skip_chunks = sum(1 for t in token_counts if t < MIN_CHUNK_THRESHOLD)

        logger.info(f"Chunk distribution:")
        logger.info(f"  Long (2 QA): {long_chunks}")
        logger.info(f"  Medium (1 QA): {medium_chunks}")
        logger.info(f"  Short (1 QA): {short_chunks}")
        logger.info(f"  Skip: {skip_chunks}")

        estimated_qa = long_chunks * 2 + medium_chunks + short_chunks
        logger.info(f"Estimated total QA pairs: {estimated_qa}")

        # Create pseudo-clusters (each chunk = cluster)
        logger.info("Creating pseudo-clusters from chunks...")
        pseudo_clusters = create_pseudo_clusters_from_chunks(chunks, processed_indices)

        if not pseudo_clusters['clusters']:
            logger.info("No new chunks to process. All chunks already processed!")
            return

        # Create dummy source mapping
        logger.info("Creating source mappings...")
        source_mapping = create_dummy_source_mapping(len(chunks))

        # Initialize LLM
        logger.info("Loading LLM model...")
        llm = LLMInterface()
        llm.load_model()
        logger.info("LLM model loaded successfully")

        # Initialize QA Generator
        generator = QAGenerator(llm)

        # Prepare processed threads (wrap chunks)
        for i, chunk in enumerate(chunks):
            chunk['thread_id'] = f"chunk_{i}"

        processed_threads = {'threads': chunks}

        # Generate QA pairs
        logger.info("=" * 60)
        logger.info(f"Generating QA pairs from {len(pseudo_clusters['clusters'])} chunks...")
        logger.info("=" * 60)

        qa_pairs = generator.generate_all(
            clustered_topics=pseudo_clusters,
            source_mappings=source_mapping,
            processed_threads=processed_threads,
            max_clusters=None  # Process all chunks
        )

        # Consolidate checkpoint file to final output
        logger.info("Consolidating all QA pairs...")
        all_qa_pairs = []

        # Load all from checkpoint
        if os.path.exists(config.QA_CHECKPOINT_FILE):
            with jsonlines.open(config.QA_CHECKPOINT_FILE, 'r') as reader:
                for qa in reader:
                    all_qa_pairs.append(qa)

        # Save consolidated file
        logger.info(f"Saving {len(all_qa_pairs)} QA pairs to final output...")
        with jsonlines.open(config.QA_PAIRS_FILE, 'w') as writer:
            for qa in all_qa_pairs:
                writer.write(qa)

        elapsed = time.time() - start_time

        logger.info("=" * 60)
        logger.info(f"QA Generation Complete!")
        logger.info(f"Generated {len(qa_pairs)} new QA pairs in this run")
        logger.info(f"Total QA pairs: {len(all_qa_pairs)}")
        logger.info(f"Time elapsed: {elapsed / 60:.1f} minutes")
        logger.info(f"Checkpoint: {config.QA_CHECKPOINT_FILE}")
        logger.info(f"Final output: {config.QA_PAIRS_FILE}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"QA generation failed: {e}", exc_info=True)
        logger.info(f"Progress saved to checkpoint: {config.QA_CHECKPOINT_FILE}")
        logger.info("Run with --resume to continue from checkpoint")
        sys.exit(1)


if __name__ == "__main__":
    main()
