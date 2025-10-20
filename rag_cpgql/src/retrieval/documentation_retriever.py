"""
Documentation Retriever - Fetches relevant code documentation for query enrichment.

This module provides semantic search over extracted code documentation (comments)
to enrich the CPGQL query generation process with developer explanations.
"""

import sys
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.retrieval.doc_vector_store import DocumentationVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentationRetriever:
    """Retrieve relevant documentation to enrich query context."""

    def __init__(self,
                 persist_directory: str = "chromadb_storage",
                 collection_name: str = "code_documentation",
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize documentation retriever.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of documentation collection
            model_name: Sentence transformer model for embeddings
        """
        self.vector_store = DocumentationVectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
            model_name=model_name
        )

        logger.info(f"DocumentationRetriever initialized with {self.vector_store.collection.count()} documents")

    def retrieve_relevant_documentation(self,
                                       question: str,
                                       analysis: Dict[str, Any],
                                       top_k: int = 5) -> Dict[str, Any]:
        """Retrieve documentation relevant to the question.

        Args:
            question: User's natural language question
            analysis: Analysis dict from AnalyzerAgent
            top_k: Number of documentation entries to retrieve

        Returns:
            Dict with:
            - documentation: List of relevant doc entries
            - summary: Formatted summary for prompt inclusion
            - stats: Retrieval statistics
        """
        logger.info(f"Retrieving documentation for question: '{question[:50]}...'")

        # Search for relevant documentation
        results = self.vector_store.search_documentation(
            query=question,
            top_k=top_k,
            doc_type='method'  # Focus on method documentation
        )

        # Format for enrichment
        documentation_entries = []
        for i, result in enumerate(results, 1):
            entry = {
                'rank': i,
                'method_name': result['metadata'].get('method_name', 'Unknown'),
                'file_path': result['metadata'].get('file_path', 'Unknown'),
                'line_number': result['metadata'].get('line_number', 0),
                'comment': result['comment'],
                'distance': result['distance'],
                'relevance_score': self._calculate_relevance(result['distance'])
            }
            documentation_entries.append(entry)

        # Create formatted summary for prompt
        summary = self._format_for_prompt(documentation_entries)

        stats = {
            'total_retrieved': len(documentation_entries),
            'avg_relevance': sum(e['relevance_score'] for e in documentation_entries) / len(documentation_entries) if documentation_entries else 0,
            'top_relevance': documentation_entries[0]['relevance_score'] if documentation_entries else 0
        }

        logger.info(f"Retrieved {len(documentation_entries)} docs, "
                   f"avg_relevance={stats['avg_relevance']:.3f}, "
                   f"top_relevance={stats['top_relevance']:.3f}")

        return {
            'documentation': documentation_entries,
            'summary': summary,
            'stats': stats
        }

    def _calculate_relevance(self, distance: float) -> float:
        """Convert distance to relevance score (0-1, higher is better).

        Args:
            distance: Distance from query (lower is better)

        Returns:
            Relevance score (0-1)
        """
        # Convert L2 distance to relevance using exponential decay
        # Typical distances range from 0-2, with <1.0 being very relevant
        import math
        return math.exp(-distance)

    def _format_for_prompt(self, documentation_entries: List[Dict[str, Any]]) -> str:
        """Format documentation for inclusion in LLM prompt.

        Args:
            documentation_entries: List of documentation entries

        Returns:
            Formatted string for prompt
        """
        if not documentation_entries:
            return "No relevant documentation found."

        lines = ["=== Relevant Code Documentation ===\n"]

        for entry in documentation_entries:
            # Only include highly relevant entries (relevance > 0.3)
            if entry['relevance_score'] < 0.3:
                continue

            lines.append(f"Function: {entry['method_name']}")
            lines.append(f"File: {entry['file_path']}:{entry['line_number']}")
            lines.append(f"Relevance: {entry['relevance_score']:.2f}")
            lines.append("Documentation:")
            # Indent the comment
            comment_lines = entry['comment'].split('\n')
            for line in comment_lines:
                lines.append(f"  {line}")
            lines.append("")  # Empty line between entries

        if len(lines) == 1:  # Only header, no relevant docs
            return "No highly relevant documentation found."

        return '\n'.join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics.

        Returns:
            Dict with retriever stats
        """
        return self.vector_store.get_stats()

    def search_by_method_name(self,
                              method_name: str,
                              top_k: int = 3) -> List[Dict[str, Any]]:
        """Search documentation by method name.

        Args:
            method_name: Method name to search for
            top_k: Number of results

        Returns:
            List of documentation entries
        """
        results = self.vector_store.search_documentation(
            query=f"Function: {method_name}",
            top_k=top_k,
            doc_type='method'
        )

        return [
            {
                'method_name': r['metadata'].get('method_name'),
                'file_path': r['metadata'].get('file_path'),
                'comment': r['comment'],
                'distance': r['distance']
            }
            for r in results
        ]

    def search_by_file(self,
                       file_pattern: str,
                       top_k: int = 5) -> List[Dict[str, Any]]:
        """Search documentation from files matching pattern.

        Args:
            file_pattern: File path pattern (e.g., "backend/access/heap")
            top_k: Number of results

        Returns:
            List of documentation entries
        """
        results = self.vector_store.search_documentation(
            query=f"File: {file_pattern}",
            top_k=top_k,
            doc_type='method'
        )

        return [
            {
                'method_name': r['metadata'].get('method_name'),
                'file_path': r['metadata'].get('file_path'),
                'comment': r['comment'],
                'distance': r['distance']
            }
            for r in results
        ]


def main():
    """Test documentation retrieval."""
    import argparse

    parser = argparse.ArgumentParser(description='Test documentation retrieval')
    parser.add_argument('--query', default='How does PostgreSQL implement MVCC?',
                       help='Test query')
    parser.add_argument('--top-k', type=int, default=5,
                       help='Number of results')
    args = parser.parse_args()

    # Initialize retriever
    logger.info("Initializing DocumentationRetriever...")
    retriever = DocumentationRetriever()

    # Get stats
    stats = retriever.get_stats()
    print(f"\nRetriever Stats:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Collection: {stats['collection_name']}")

    # Test retrieval
    print(f"\nTesting retrieval for: '{args.query}'")
    print("="*60)

    result = retriever.retrieve_relevant_documentation(
        question=args.query,
        analysis={'domain': 'mvcc', 'keywords': ['MVCC', 'transaction']},
        top_k=args.top_k
    )

    print(f"\nRetrieved {result['stats']['total_retrieved']} documents")
    print(f"Average relevance: {result['stats']['avg_relevance']:.3f}")
    print(f"Top relevance: {result['stats']['top_relevance']:.3f}")

    print("\n" + result['summary'])

    # Show raw documentation
    print("\n=== Raw Documentation Entries ===")
    for entry in result['documentation']:
        print(f"\n{entry['rank']}. {entry['method_name']} (relevance: {entry['relevance_score']:.3f})")
        print(f"   {entry['file_path']}:{entry['line_number']}")
        print(f"   Distance: {entry['distance']:.4f}")
        print(f"   Comment: {entry['comment'][:150]}...")


if __name__ == '__main__':
    main()
