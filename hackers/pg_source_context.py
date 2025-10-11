"""
PostgreSQL Source Context Module

Maps discussion topics to relevant PostgreSQL source code files.
"""
import logging
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from tqdm import tqdm

import config
from utils import (
    load_json,
    save_json,
    extract_component_from_path,
    extract_keywords_from_path,
    get_timestamp
)


logger = logging.getLogger(__name__)


class SourceContextMapper:
    """Maps topics to PostgreSQL source code."""

    def __init__(self, pg_source_path: str = config.PG_SOURCE_PATH):
        """
        Initialize mapper.

        Args:
            pg_source_path: Path to PostgreSQL source code
        """
        self.pg_source_path = pg_source_path
        self.file_index = {}

    def build_file_index(self) -> Dict[str, Dict]:
        """
        Index all source files in PostgreSQL codebase.

        Returns:
            File index dictionary
        """
        logger.info(f"Indexing PostgreSQL source: {self.pg_source_path}")

        # Check for cached index
        if os.path.exists(config.FILE_INDEX_CACHE_FILE):
            try:
                self.file_index = load_json(config.FILE_INDEX_CACHE_FILE)
                logger.info(f"Loaded cached file index: {len(self.file_index)} files")
                return self.file_index
            except Exception as e:
                logger.warning(f"Failed to load cached index: {e}")

        file_index = {}

        # Walk source tree
        for root, dirs, files in os.walk(self.pg_source_path):
            # Skip build artifacts and .git
            if 'build' in root or '.git' in root or 'tmp' in root:
                continue

            for filename in files:
                if not filename.endswith(('.c', '.h')):
                    continue

                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, self.pg_source_path)
                relative_path = relative_path.replace('\\', '/')

                file_info = {
                    'full_path': full_path,
                    'relative_path': relative_path,
                    'component': extract_component_from_path(relative_path),
                    'language': 'c' if filename.endswith('.c') else 'h',
                    'size_bytes': os.path.getsize(full_path),
                    'keywords': extract_keywords_from_path(relative_path)
                }

                file_index[relative_path] = file_info

        logger.info(f"Indexed {len(file_index)} source files")

        # Cache index
        save_json(file_index, config.FILE_INDEX_CACHE_FILE)

        self.file_index = file_index
        return file_index

    def map_keywords_to_files(self, keywords: List[str]) -> List[Tuple[str, float]]:
        """
        Map keywords to relevant files with scores.

        Args:
            keywords: Topic keywords

        Returns:
            List of (file_path, score) tuples
        """
        file_scores = defaultdict(float)

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Check component mapping
            if keyword_lower in config.KEYWORD_TO_COMPONENT:
                for component_path in config.KEYWORD_TO_COMPONENT[keyword_lower]:
                    for file_path, file_info in self.file_index.items():
                        if component_path in file_path:
                            file_scores[file_path] += 1.0

            # Check file keywords
            for file_path, file_info in self.file_index.items():
                file_keywords = ' '.join(file_info['keywords']).lower()
                if keyword_lower in file_keywords:
                    file_scores[file_path] += 0.5

                # Check filename match
                if keyword_lower in os.path.basename(file_path).lower():
                    file_scores[file_path] += 0.8

        # Sort by score
        ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)

        # Filter by minimum score
        ranked_files = [(f, s) for f, s in ranked_files if s >= config.MIN_RELEVANCE_SCORE]

        return ranked_files[:config.MAX_FILES_PER_TOPIC]

    def map_topics_to_source(self, clustered_topics: Dict) -> Dict:
        """
        Map each topic cluster to relevant source files.

        Args:
            clustered_topics: Clustered topics from topic_clustering

        Returns:
            Topic-source mapping dictionary
        """
        logger.info("Mapping topics to source files...")

        # Build file index if not already built
        if not self.file_index:
            self.build_file_index()

        topic_mappings = []

        for cluster in tqdm(clustered_topics.get('clusters', []), desc="Mapping topics"):
            keywords = cluster.get('keywords', [])

            # Map keywords to files
            ranked_files = self.map_keywords_to_files(keywords)

            # Build source file info
            source_files = []
            for file_path, score in ranked_files:
                file_info = self.file_index.get(file_path, {})

                source_files.append({
                    'file_path': file_path,
                    'full_path': file_info.get('full_path', ''),
                    'relevance_score': round(score, 2),
                    'component': file_info.get('component', 'unknown')
                })

            # Get top components
            components = [f['component'] for f in source_files]
            top_components = [c for c, _ in sorted(
                [(c, components.count(c)) for c in set(components)],
                key=lambda x: x[1],
                reverse=True
            )[:5]]

            mapping = {
                'cluster_id': cluster.get('cluster_id'),
                'label': cluster.get('label'),
                'keywords': keywords,
                'thread_count': cluster.get('thread_count', 0),
                'source_files': source_files,
                'top_components': top_components
            }

            topic_mappings.append(mapping)

        logger.info(f"Mapped {len(topic_mappings)} topics to source files")

        return {'topic_mappings': topic_mappings}

    def save_to_json(self, data: Dict, output_path: str = config.SOURCE_MAPPING_FILE):
        """Save source mappings to JSON."""
        output = {
            **data,
            'metadata': {
                'total_topics': len(data.get('topic_mappings', [])),
                'pg_source_path': self.pg_source_path,
                'indexed_files': len(self.file_index),
                'mapped_at': get_timestamp()
            }
        }

        save_json(output, output_path)
        logger.info(f"Saved source mappings to {output_path}")


def main():
    """Main function for standalone execution."""
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting source context mapping")

    # Load clustered topics
    clustered_topics = load_json(config.CLUSTERED_TOPICS_FILE)
    logger.info(f"Loaded {len(clustered_topics.get('clusters', []))} clusters")

    # Map to source
    mapper = SourceContextMapper()
    mappings = mapper.map_topics_to_source(clustered_topics)

    # Save results
    mapper.save_to_json(mappings)

    logger.info("Source context mapping complete")


if __name__ == '__main__':
    main()
