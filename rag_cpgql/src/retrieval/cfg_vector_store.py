"""
CFG Pattern Vector Store

Manages ChromaDB vector store for CFG patterns extracted from Joern CPG.
Stores execution flow patterns for semantic search.

Based on: PHASE2_CFG_PATTERN_DESIGN.md
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class CFGVectorStore:
    """Vector store for CFG patterns using ChromaDB."""

    def __init__(self, persist_directory: str = "chromadb_storage"):
        """Initialize ChromaDB vector store for CFG patterns."""
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.logger = logging.getLogger(__name__)

    def initialize(self, collection_name: str = "cfg_patterns"):
        """Initialize ChromaDB client and collection."""
        try:
            # Create ChromaDB client with persistent storage
            self.client = chromadb.Client(Settings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "CFG execution flow patterns from PostgreSQL"}
            )

            self.logger.info(f"ChromaDB initialized: {collection_name} collection ({self.collection.count()} documents)")

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def _prepare_pattern_text(self, pattern: Dict) -> str:
        """
        Prepare natural language text for embedding.

        This is the key to good semantic search - we embed descriptive text
        that explains what the pattern does, not raw code.
        """
        pattern_type = pattern.get('pattern_type', 'unknown')
        method_name = pattern.get('method_name', 'unknown')
        description = pattern.get('description', '')

        # Base text with pattern type and method
        text_parts = [
            f"Execution pattern in {method_name}",
            f"Type: {pattern_type}",
        ]

        # Add pattern-specific details
        if pattern_type == "control_structure":
            control_type = pattern.get('control_type', '')
            condition = pattern.get('condition', '')
            text_parts.append(f"{control_type} statement")
            text_parts.append(f"Condition: {condition[:100]}")  # Truncate long conditions

        elif pattern_type == "error_handling":
            check_type = pattern.get('check_type', '')
            condition = pattern.get('condition', '')
            text_parts.append(f"Error check: {check_type}")
            text_parts.append(f"Validates: {condition[:100]}")

        elif pattern_type == "lock_pattern":
            lock_func = pattern.get('lock_function', '')
            args = pattern.get('lock_args', '')
            text_parts.append(f"Lock operation: {lock_func}")
            text_parts.append(f"Arguments: {args[:80]}")

        elif pattern_type == "transaction":
            txn_call = pattern.get('transaction_call', '')
            text_parts.append(f"Transaction operation: {txn_call}")

        elif pattern_type == "complexity":
            cfg_nodes = pattern.get('cfg_nodes', 0)
            control_count = pattern.get('control_structures', 0)
            text_parts.append(f"Complexity: {cfg_nodes} CFG nodes, {control_count} branches")

        # Add description (most important for semantic search)
        if description:
            text_parts.append(f"Description: {description}")

        return "\n".join(text_parts)

    def _prepare_pattern_metadata(self, pattern: Dict, pattern_id: str) -> Dict:
        """Prepare metadata for pattern storage."""
        return {
            "pattern_id": pattern_id,
            "pattern_type": pattern.get('pattern_type', 'unknown'),
            "method_name": pattern.get('method_name', ''),
            "file_path": pattern.get('file_path', ''),
            "line_number": str(pattern.get('line_number', -1))
        }

    def index_patterns(self, patterns_file: str):
        """Index CFG patterns from JSON file into vector store."""
        self.logger.info(f"Loading CFG patterns from {patterns_file}")

        with open(patterns_file, 'r') as f:
            all_patterns = json.load(f)

        # Flatten all pattern types into single list
        patterns_to_index = []
        pattern_counter = 0

        for pattern_type, patterns in all_patterns.items():
            self.logger.info(f"  Processing {len(patterns)} {pattern_type} patterns...")

            for pattern in patterns:
                pattern_id = f"cfg_{pattern_type}_{pattern_counter}"
                text = self._prepare_pattern_text(pattern)
                metadata = self._prepare_pattern_metadata(pattern, pattern_id)

                patterns_to_index.append({
                    'id': pattern_id,
                    'text': text,
                    'metadata': metadata
                })

                pattern_counter += 1

        self.logger.info(f"Indexing {len(patterns_to_index)} total patterns...")

        # Batch index patterns
        batch_size = 100
        for i in range(0, len(patterns_to_index), batch_size):
            batch = patterns_to_index[i:i+batch_size]

            ids = [p['id'] for p in batch]
            documents = [p['text'] for p in batch]
            metadatas = [p['metadata'] for p in batch]

            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            if (i // batch_size + 1) % 10 == 0:
                self.logger.info(f"  Indexed {i + len(batch)}/{len(patterns_to_index)} patterns")

        self.logger.info(f"✅ Indexed {len(patterns_to_index)} CFG patterns")
        self.logger.info(f"   Total documents in collection: {self.collection.count()}")

    def search_patterns(self, query: str, n_results: int = 5,
                       pattern_type_filter: Optional[str] = None) -> Dict:
        """
        Search for relevant CFG patterns.

        Args:
            query: Natural language query
            n_results: Number of results to return
            pattern_type_filter: Optional filter by pattern type

        Returns:
            Dict with patterns and metadata
        """
        if not self.collection:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")

        # Build query filter
        where_filter = None
        if pattern_type_filter:
            where_filter = {"pattern_type": pattern_type_filter}

        # Search
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        # Format results
        patterns = []
        for i in range(len(results['ids'][0])):
            pattern = {
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            }
            patterns.append(pattern)

        return {
            'patterns': patterns,
            'query': query,
            'count': len(patterns)
        }

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        if not self.collection:
            return {'error': 'Not initialized'}

        total_docs = self.collection.count()

        # Get counts by pattern type (sample-based approximation)
        sample_results = self.collection.get(limit=1000)
        pattern_types = {}
        for metadata in sample_results.get('metadatas', []):
            ptype = metadata.get('pattern_type', 'unknown')
            pattern_types[ptype] = pattern_types.get(ptype, 0) + 1

        return {
            'total_documents': total_docs,
            'pattern_type_distribution': pattern_types,
            'collection_name': self.collection.name
        }


def main():
    """CLI interface for CFG vector store."""
    import argparse

    parser = argparse.ArgumentParser(description="CFG Pattern Vector Store")
    parser.add_argument('--action', choices=['index', 'search', 'stats'], required=True,
                       help='Action to perform')
    parser.add_argument('--patterns-file', default='data/cfg_patterns.json',
                       help='CFG patterns JSON file')
    parser.add_argument('--query', help='Search query (for search action)')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--pattern-type', help='Filter by pattern type')

    args = parser.parse_args()

    # Initialize vector store
    store = CFGVectorStore()
    store.initialize()

    if args.action == 'index':
        store.index_patterns(args.patterns_file)

    elif args.action == 'search':
        if not args.query:
            print("Error: --query required for search")
            return 1

        results = store.search_patterns(
            query=args.query,
            n_results=args.top_k,
            pattern_type_filter=args.pattern_type
        )

        print(f"\nSearch results for: {args.query}")
        print(f"Found {results['count']} patterns\n")

        for i, pattern in enumerate(results['patterns'], 1):
            print(f"{i}. {pattern['metadata']['pattern_type']} in {pattern['metadata']['method_name']}")
            print(f"   File: {pattern['metadata']['file_path']}:{pattern['metadata']['line_number']}")
            if pattern['distance']:
                print(f"   Distance: {pattern['distance']:.4f}")
            print(f"   {pattern['text'][:200]}...")
            print()

    elif args.action == 'stats':
        stats = store.get_stats()
        print("\nCFG Vector Store Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Collection: {stats['collection_name']}")
        print("\nPattern type distribution (sample):")
        for ptype, count in stats['pattern_type_distribution'].items():
            print(f"  {ptype}: {count}")

    return 0


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
