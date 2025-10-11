"""
Dataset Builder Module

Aggregates, validates, and formats QA pairs into final dataset.
"""
import logging
import uuid
from collections import Counter
from datetime import datetime
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import config
from utils import load_jsonl, save_jsonl, save_json, get_timestamp


logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Builds final QA dataset with validation and deduplication."""

    def __init__(self, qa_pairs_file: str = config.QA_PAIRS_FILE):
        """
        Initialize dataset builder.

        Args:
            qa_pairs_file: Path to QA pairs JSONL
        """
        self.qa_pairs_file = qa_pairs_file
        self.qa_pairs = []

    def load_qa_pairs(self):
        """Load QA pairs from JSONL."""
        logger.info(f"Loading QA pairs from {self.qa_pairs_file}")
        self.qa_pairs = load_jsonl(self.qa_pairs_file)
        logger.info(f"Loaded {len(self.qa_pairs)} QA pairs")

    def validate_qa_pairs(self) -> Dict:
        """
        Validate QA pairs.

        Returns:
            Validation report
        """
        logger.info("Validating QA pairs...")

        report = {
            'total': len(self.qa_pairs),
            'valid': 0,
            'errors': [],
            'warnings': []
        }

        required_fields = ['question', 'answer']

        for i, qa in enumerate(self.qa_pairs):
            errors = []
            warnings = []

            # Check required fields
            for field in required_fields:
                if field not in qa or not qa[field]:
                    errors.append(f"Missing/empty field: {field}")

            # Validate question
            if 'question' in qa:
                if not qa['question'].strip().endswith('?'):
                    warnings.append("Question doesn't end with '?'")

            # Validate answer
            if 'answer' in qa:
                if len(qa['answer']) < config.MIN_ANSWER_LENGTH:
                    warnings.append(f"Short answer ({len(qa['answer'])} chars)")

            if errors:
                report['errors'].append({'index': i, 'errors': errors})
            else:
                report['valid'] += 1

            if warnings and not errors:
                report['warnings'].append({'index': i, 'warnings': warnings})

        logger.info(f"Validation: {report['valid']}/{report['total']} valid")
        if report['errors']:
            logger.warning(f"Found {len(report['errors'])} QA pairs with errors")

        return report

    def deduplicate(self, threshold: float = config.DEDUP_SIMILARITY_THRESHOLD):
        """
        Remove duplicate questions.

        Args:
            threshold: Similarity threshold (0-1)
        """
        if not self.qa_pairs:
            return

        logger.info(f"Deduplicating questions (threshold={threshold})...")

        questions = [qa['question'] for qa in self.qa_pairs]

        # Generate embeddings
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(questions, show_progress_bar=True)

        # Calculate similarities
        similarities = cosine_similarity(embeddings)

        # Find duplicates
        keep_indices = set(range(len(self.qa_pairs)))

        for i in range(len(self.qa_pairs)):
            if i not in keep_indices:
                continue

            for j in range(i + 1, len(self.qa_pairs)):
                if j not in keep_indices:
                    continue

                if similarities[i, j] >= threshold:
                    # Keep the one with longer answer
                    if len(self.qa_pairs[i]['answer']) >= len(self.qa_pairs[j]['answer']):
                        keep_indices.discard(j)
                    else:
                        keep_indices.discard(i)
                        break

        # Filter
        original_count = len(self.qa_pairs)
        self.qa_pairs = [self.qa_pairs[i] for i in sorted(keep_indices)]

        logger.info(f"Deduplicated: {original_count} → {len(self.qa_pairs)} QA pairs")

    def add_metadata(self):
        """Add unique IDs and metadata."""
        logger.info("Adding metadata to QA pairs...")

        for i, qa in enumerate(self.qa_pairs):
            # Unique ID
            qa['qa_id'] = f"pg17_{i:04d}_{uuid.uuid4().hex[:8]}"

            # Dataset metadata
            qa['dataset_version'] = "1.0"
            qa['postgres_version'] = config.PG_VERSION

            if 'generated_at' not in qa:
                qa['created_at'] = get_timestamp()

        logger.info("Metadata added")

    def generate_statistics(self) -> Dict:
        """
        Generate dataset statistics.

        Returns:
            Statistics dictionary
        """
        logger.info("Generating statistics...")

        stats = {
            'total_qa_pairs': len(self.qa_pairs)
        }

        # Difficulty distribution
        difficulty_counts = Counter(qa.get('difficulty', 'unknown') for qa in self.qa_pairs)
        stats['difficulty_distribution'] = dict(difficulty_counts)

        # Topic distribution
        all_topics = [topic for qa in self.qa_pairs for topic in qa.get('topics', [])]
        topic_counts = Counter(all_topics)
        stats['topic_distribution'] = dict(topic_counts.most_common(20))

        # Length statistics
        question_lengths = [len(qa['question']) for qa in self.qa_pairs]
        answer_lengths = [len(qa['answer']) for qa in self.qa_pairs]

        stats['question_length'] = {
            'min': min(question_lengths) if question_lengths else 0,
            'max': max(question_lengths) if question_lengths else 0,
            'mean': sum(question_lengths) / len(question_lengths) if question_lengths else 0,
            'median': sorted(question_lengths)[len(question_lengths) // 2] if question_lengths else 0
        }

        stats['answer_length'] = {
            'min': min(answer_lengths) if answer_lengths else 0,
            'max': max(answer_lengths) if answer_lengths else 0,
            'mean': sum(answer_lengths) / len(answer_lengths) if answer_lengths else 0,
            'median': sorted(answer_lengths)[len(answer_lengths) // 2] if answer_lengths else 0
        }

        # Source file coverage
        all_source_files = [f for qa in self.qa_pairs for f in qa.get('source_files', [])]
        stats['unique_source_files'] = len(set(all_source_files))

        return stats

    def export_dataset(self, output_path: str = config.FINAL_DATASET_FILE):
        """Export final dataset."""
        save_jsonl(self.qa_pairs, output_path)
        logger.info(f"Exported dataset to {output_path}")

    def create_report(self, stats: Dict, validation: Dict, output_path: str = config.DATASET_REPORT_FILE):
        """Create dataset report."""
        report = {
            'metadata': {
                'created_at': get_timestamp(),
                'postgres_version': config.PG_VERSION,
                'dataset_version': "1.0"
            },
            'statistics': stats,
            'validation': validation
        }

        save_json(report, output_path)
        logger.info(f"Created report at {output_path}")


def main():
    """Main function for standalone execution."""
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting dataset builder")

    # Build dataset
    builder = DatasetBuilder()
    builder.load_qa_pairs()

    # Validate
    validation_report = builder.validate_qa_pairs()

    # Deduplicate
    builder.deduplicate()

    # Add metadata
    builder.add_metadata()

    # Generate statistics
    stats = builder.generate_statistics()

    logger.info("Dataset Statistics:")
    logger.info(f"  Total QA pairs: {stats['total_qa_pairs']}")
    logger.info(f"  Unique source files: {stats['unique_source_files']}")
    logger.info(f"  Avg answer length: {stats['answer_length']['mean']:.0f} chars")

    # Export
    builder.export_dataset()

    # Create report
    builder.create_report(stats, validation_report)

    logger.info("Dataset building complete")


if __name__ == '__main__':
    main()
