"""
QA Generator Module

Generates question-answer pairs using LLM.
"""
import json
import logging
import re
import time
from typing import Dict, List

from tqdm import tqdm

import config
from llm_interface import LLMInterface
from utils import load_json, save_jsonl, append_jsonl, get_timestamp, truncate_text


logger = logging.getLogger(__name__)


class QAGenerator:
    """Generates QA pairs from discussions and source context."""

    def __init__(self, llm_interface: LLMInterface):
        """
        Initialize QA generator.

        Args:
            llm_interface: Initialized LLM interface
        """
        self.llm = llm_interface
        self.qa_pairs = []

    def build_topic_context(
        self,
        cluster: Dict,
        source_mapping: Dict,
        threads_data: Dict
    ) -> str:
        """
        Build context for QA generation.

        Args:
            cluster: Topic cluster
            source_mapping: Source file mapping
            threads_data: All threads

        Returns:
            Context string
        """
        parts = []

        # Topic header
        parts.append(f"TOPIC: {cluster.get('label', '')}")
        parts.append(f"KEYWORDS: {', '.join(cluster.get('keywords', []))}")
        parts.append("")

        # Discussion threads
        parts.append(f"DISCUSSION THREADS ({cluster.get('thread_count', 0)} threads):")
        parts.append("")

        for i, thread_ref in enumerate(cluster.get('threads', [])[:config.MAX_THREADS_PER_CLUSTER], 1):
            thread_id = thread_ref.get('thread_id', '')
            thread = threads_data.get(thread_id, {})

            parts.append(f"Thread {i}: {thread.get('subject', '')}")
            parts.append(f"Messages: {thread.get('message_count', 0)}")
            parts.append("")

            # Add content (truncated)
            content = thread.get('aggregated_content', '')
            content = truncate_text(content, 1500, "... [truncated]")
            parts.append(content)
            parts.append("")
            parts.append("---")
            parts.append("")

        # Source files
        if source_mapping and 'source_files' in source_mapping:
            parts.append(f"RELEVANT SOURCE FILES:")
            parts.append("")

            for file_info in source_mapping['source_files'][:config.MAX_SOURCE_FILES_PER_CLUSTER]:
                parts.append(f"File: {file_info.get('file_path', '')}")
                parts.append(f"Component: {file_info.get('component', '')}")
                parts.append("")

        context = '\n'.join(parts)

        # Ensure context isn't too long
        if len(context) > config.MAX_CONTEXT_LENGTH:
            context = truncate_text(context, config.MAX_CONTEXT_LENGTH, "\n... [context truncated]")

        return context

    def build_qa_prompt(self, context: str, n_pairs: int = config.QA_PAIRS_PER_CLUSTER) -> str:
        """
        Build prompt for QA generation.

        Args:
            context: Topic context
            n_pairs: Number of QA pairs to generate

        Returns:
            Full prompt
        """
        prompt = f"""You are a PostgreSQL internals expert. Based on the discussion threads and source code context below, generate {n_pairs} high-quality question-answer pairs about PostgreSQL 17 internals.

Requirements:
- Questions should be technical and specific
- Answers should be comprehensive and reference source code when relevant
- Cover different aspects of the topic
- Include difficulty level (beginner/intermediate/advanced)
- Include topic tags

{context}

Generate exactly {n_pairs} question-answer pairs in JSON format:

[
  {{
    "question": "How does PostgreSQL's partition pruning work during query planning?",
    "answer": "PostgreSQL's partition pruning...",
    "difficulty": "advanced",
    "topics": ["query_planner", "partitioning"]
  }}
]

Output ONLY the JSON array, no additional text."""

        return prompt

    def parse_qa_response(self, response: str) -> List[Dict]:
        """
        Parse QA pairs from LLM response.

        Args:
            response: LLM response text

        Returns:
            List of QA pair dictionaries
        """
        # Remove <think> reasoning tokens if present
        response = response.strip()
        if '<think>' in response:
            # Extract everything after </think>
            match = re.search(r'</think>\s*(.*)', response, re.DOTALL)
            if match:
                response = match.group(1).strip()

        # Remove markdown code blocks
        if response.startswith('```'):
            match = re.search(r'```(?:json)?\n(.*?)\n```', response, re.DOTALL)
            if match:
                response = match.group(1)
            else:
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

        # Try to parse JSON
        try:
            qa_pairs = json.loads(response)

            if not isinstance(qa_pairs, list):
                logger.warning("Response is not a list")
                return []

            # Validate structure
            valid_pairs = []
            for qa in qa_pairs:
                if 'question' in qa and 'answer' in qa:
                    valid_pairs.append(qa)
                else:
                    logger.warning(f"Invalid QA pair structure: {qa}")

            return valid_pairs

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Response: {response[:500]}...")
            return []

    def generate_for_cluster(
        self,
        cluster: Dict,
        source_mapping: Dict,
        threads_data: Dict
    ) -> List[Dict]:
        """
        Generate QA pairs for one cluster.

        Args:
            cluster: Topic cluster
            source_mapping: Source mapping
            threads_data: All threads

        Returns:
            List of QA pairs
        """
        logger.info(f"Generating QA for cluster: {cluster.get('label', '')}")

        # Build context
        context = self.build_topic_context(cluster, source_mapping, threads_data)

        # Build prompt
        prompt = self.build_qa_prompt(context)

        # Generate with retries
        qa_pairs = []
        for attempt in range(config.MAX_RETRIES):
            try:
                logger.debug(f"Generation attempt {attempt + 1}/{config.MAX_RETRIES}")

                response = self.llm.generate(
                    prompt=prompt,
                    max_tokens=config.GENERATION_MAX_TOKENS,
                    temperature=config.GENERATION_TEMPERATURE
                )

                qa_pairs = self.parse_qa_response(response)

                if qa_pairs:
                    logger.info(f"Generated {len(qa_pairs)} QA pairs")
                    break
                else:
                    logger.warning(f"Failed to parse response on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Generation error on attempt {attempt + 1}: {e}")

            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2)

        # Add metadata
        for qa in qa_pairs:
            qa['cluster_id'] = cluster.get('cluster_id')
            qa['cluster_label'] = cluster.get('label', '')
            qa['source_files'] = [f['file_path'] for f in source_mapping.get('source_files', [])[:5]]
            qa['thread_ids'] = [t['thread_id'] for t in cluster.get('threads', [])[:5]]
            qa['generated_at'] = get_timestamp()

        return qa_pairs

    def generate_all(
        self,
        clustered_topics: Dict,
        source_mappings: Dict,
        processed_threads: Dict,
        max_clusters: int = None
    ) -> List[Dict]:
        """
        Generate QA pairs for all clusters.

        Args:
            clustered_topics: Clustered topics
            source_mappings: Source mappings
            processed_threads: Processed threads
            max_clusters: Limit clusters (for testing)

        Returns:
            All QA pairs
        """
        logger.info("Starting QA generation for all clusters")

        # Convert threads list to dict
        threads_dict = {t['thread_id']: t for t in processed_threads.get('threads', [])}

        # Get clusters
        clusters = clustered_topics.get('clusters', [])
        if max_clusters:
            clusters = clusters[:max_clusters]
            logger.info(f"Limiting to {max_clusters} clusters")

        # Create source mapping dict
        source_map_dict = {m['cluster_id']: m for m in source_mappings.get('topic_mappings', [])}

        all_qa_pairs = []

        for cluster in tqdm(clusters, desc="Generating QA pairs"):
            cluster_id = cluster.get('cluster_id')
            source_mapping = source_map_dict.get(cluster_id, {})

            qa_pairs = self.generate_for_cluster(cluster, source_mapping, threads_dict)

            all_qa_pairs.extend(qa_pairs)

            # Save checkpoint
            for qa in qa_pairs:
                append_jsonl(qa, config.QA_CHECKPOINT_FILE)

        self.qa_pairs = all_qa_pairs
        logger.info(f"Generated total {len(all_qa_pairs)} QA pairs")

        return all_qa_pairs

    def save_to_jsonl(self, output_path: str = config.QA_PAIRS_FILE):
        """Save QA pairs to JSONL."""
        save_jsonl(self.qa_pairs, output_path)
        logger.info(f"Saved {len(self.qa_pairs)} QA pairs to {output_path}")


def main():
    """Main function for standalone execution."""
    import sys
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting QA generation")

    # Load data
    logger.info("Loading data files...")
    clustered_topics = load_json(config.CLUSTERED_TOPICS_FILE)
    source_mappings = load_json(config.SOURCE_MAPPING_FILE)
    processed_threads = load_json(config.PROCESSED_THREADS_FILE)

    # Initialize LLM
    logger.info("Loading LLM...")
    llm = LLMInterface()
    llm.load_model()

    # Generate QA pairs
    generator = QAGenerator(llm)

    # Limit clusters for testing if argument provided
    max_clusters = int(sys.argv[1]) if len(sys.argv) > 1 else None

    qa_pairs = generator.generate_all(
        clustered_topics,
        source_mappings,
        processed_threads,
        max_clusters=max_clusters
    )

    # Save results
    generator.save_to_jsonl()

    # Unload model
    llm.unload_model()

    logger.info("QA generation complete")


if __name__ == '__main__':
    main()
