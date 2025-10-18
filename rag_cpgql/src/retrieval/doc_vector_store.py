"""
Build ChromaDB vector store for code documentation and comments.

This module creates a specialized collection for semantic search over:
- Method documentation and comments
- File-level documentation
- Inline comments with context

The collection enables retrieval of relevant documentation to enrich
query generation with developer explanations of "how" functionality works.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentationVectorStore:
    """Manage ChromaDB collection for code documentation."""

    def __init__(self,
                 persist_directory: str = "chromadb_storage",
                 collection_name: str = "code_documentation",
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize documentation vector store.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of documentation collection
            model_name: Sentence transformer model for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "PostgreSQL CPG code documentation and comments"}
            )
            logger.info(f"Created new collection: {collection_name}")

    def build_from_extraction(self, extraction_file: str) -> Dict[str, int]:
        """Build vector store from extracted documentation JSON.

        Args:
            extraction_file: Path to cpg_documentation.json

        Returns:
            Stats dict with counts of indexed items
        """
        logger.info(f"Loading documentation from {extraction_file}...")

        with open(extraction_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stats = {
            'method_docs_indexed': 0,
            'file_docs_indexed': 0,
            'inline_comments_indexed': 0,
            'total_indexed': 0
        }

        # Index method documentation
        logger.info("Indexing method documentation...")
        method_docs = self._prepare_method_docs(data.get('methods', []))
        if method_docs:
            self._add_documents(method_docs)
            stats['method_docs_indexed'] = len(method_docs)

        # Index file documentation
        logger.info("Indexing file documentation...")
        file_docs = self._prepare_file_docs(data.get('files', []))
        if file_docs:
            self._add_documents(file_docs)
            stats['file_docs_indexed'] = len(file_docs)

        # Index inline comments
        logger.info("Indexing inline comments...")
        inline_docs = self._prepare_inline_docs(data.get('inline_comments', []))
        if inline_docs:
            self._add_documents(inline_docs)
            stats['inline_comments_indexed'] = len(inline_docs)

        stats['total_indexed'] = sum([
            stats['method_docs_indexed'],
            stats['file_docs_indexed'],
            stats['inline_comments_indexed']
        ])

        logger.info(f"Indexing complete: {stats}")
        return stats

    def _prepare_method_docs(self, methods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare method documentation for indexing.

        Args:
            methods: List of method documentation dicts

        Returns:
            List of prepared document dicts
        """
        prepared = []

        for idx, method in enumerate(methods):
            # Create searchable text combining all relevant info
            search_text = f"""
            Function: {method['method_name']}
            File: {method['file_path']}
            Documentation: {method['comment']}
            Signature: {method['signature']}
            Implementation snippet: {method.get('code_snippet', '')}
            """.strip()

            # Create metadata for filtering and context
            metadata = {
                'doc_type': 'method',
                'method_name': method['method_name'],
                'file_path': method['file_path'],
                'line_number': method.get('line_number', 0),
                'has_implementation': bool(method.get('code_snippet'))
            }

            prepared.append({
                'id': f"method_{idx}_{method['method_name']}",
                'text': search_text,
                'metadata': metadata,
                'comment': method['comment']  # Store original comment for retrieval
            })

        return prepared

    def _prepare_file_docs(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare file documentation for indexing.

        Args:
            files: List of file documentation dicts

        Returns:
            List of prepared document dicts
        """
        prepared = []

        for idx, file_doc in enumerate(files):
            # Create searchable text
            search_text = f"""
            File: {file_doc['file_path']}
            Description: {file_doc.get('description', '')}
            Header documentation: {file_doc['header_comment']}
            """.strip()

            metadata = {
                'doc_type': 'file',
                'file_path': file_doc['file_path']
            }

            prepared.append({
                'id': f"file_{idx}_{Path(file_doc['file_path']).stem}",
                'text': search_text,
                'metadata': metadata,
                'comment': file_doc['header_comment']
            })

        return prepared

    def _prepare_inline_docs(self, inline_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare inline comments for indexing.

        Args:
            inline_comments: List of inline comment dicts

        Returns:
            List of prepared document dicts
        """
        prepared = []

        for idx, comment in enumerate(inline_comments):
            # Create searchable text with context
            search_text = f"""
            File: {comment['file_path']}
            Function: {comment.get('parent_method', 'unknown')}
            Comment: {comment['comment']}
            Code context: {comment.get('context_code', '')}
            """.strip()

            metadata = {
                'doc_type': 'inline',
                'file_path': comment['file_path'],
                'parent_method': comment.get('parent_method', 'unknown'),
                'line_number': comment.get('line_number', 0)
            }

            prepared.append({
                'id': f"inline_{idx}_{comment['file_path']}_{comment.get('line_number', 0)}",
                'text': search_text,
                'metadata': metadata,
                'comment': comment['comment']
            })

        return prepared

    def _add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """Add documents to ChromaDB collection in batches.

        Args:
            documents: List of prepared document dicts
            batch_size: Number of documents per batch
        """
        total = len(documents)

        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]

            # Extract components
            ids = [doc['id'] for doc in batch]
            texts = [doc['text'] for doc in batch]
            metadatas = [doc['metadata'] for doc in batch]

            # Add original comment to metadata for easy retrieval
            for j, doc in enumerate(batch):
                metadatas[j]['original_comment'] = doc['comment']

            # Generate embeddings
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()

            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )

            if (i + batch_size) % 500 == 0 or (i + batch_size) >= total:
                logger.info(f"Indexed {min(i + batch_size, total)}/{total} documents")

    def search_documentation(self,
                           query: str,
                           top_k: int = 5,
                           doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for relevant documentation.

        Args:
            query: Natural language query
            top_k: Number of results to return
            doc_type: Optional filter by doc_type (method, file, inline)

        Returns:
            List of dicts with keys: comment, metadata, distance
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0].tolist()

        # Build filter
        where_filter = None
        if doc_type:
            where_filter = {"doc_type": doc_type}

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        # Format results
        formatted = []
        if results['metadatas'] and results['metadatas'][0]:
            for i, metadata in enumerate(results['metadatas'][0]):
                formatted.append({
                    'comment': metadata.get('original_comment', ''),
                    'metadata': {
                        'doc_type': metadata.get('doc_type'),
                        'file_path': metadata.get('file_path'),
                        'method_name': metadata.get('method_name'),
                        'line_number': metadata.get('line_number', 0)
                    },
                    'distance': results['distances'][0][i]
                })

        return formatted

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dict with collection stats
        """
        count = self.collection.count()

        return {
            'total_documents': count,
            'collection_name': self.collection_name,
            'persist_directory': self.persist_directory
        }


def main():
    """Main entry point for building documentation vector store."""
    import argparse

    parser = argparse.ArgumentParser(description='Build documentation vector store')
    parser.add_argument('--input', default='data/cpg_documentation.json',
                       help='Input documentation JSON file')
    parser.add_argument('--persist-dir', default='chromadb_storage',
                       help='ChromaDB persistence directory')
    parser.add_argument('--collection', default='code_documentation',
                       help='Collection name')

    args = parser.parse_args()

    # Check input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        logger.info("Run comment_extractor.py first to extract documentation")
        sys.exit(1)

    # Build vector store
    logger.info("Initializing documentation vector store...")
    store = DocumentationVectorStore(
        persist_directory=args.persist_dir,
        collection_name=args.collection
    )

    # Index documentation
    stats = store.build_from_extraction(args.input)

    # Get final stats
    collection_stats = store.get_stats()

    # Print summary
    print("\n" + "="*60)
    print("Documentation Vector Store Summary")
    print("="*60)
    print(f"Collection: {collection_stats['collection_name']}")
    print(f"Persist directory: {collection_stats['persist_directory']}")
    print(f"\nIndexing Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value:,}")
    print(f"\nTotal documents in collection: {collection_stats['total_documents']:,}")
    print("="*60)

    # Test search
    print("\nTesting search functionality...")
    test_query = "How does PostgreSQL handle MVCC transaction visibility?"
    results = store.search_documentation(test_query, top_k=3)

    print(f"\nTop 3 results for: '{test_query}'")
    print("-"*60)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['metadata']['doc_type'].upper()}: {result['metadata'].get('method_name', result['metadata'].get('file_path'))}")
        print(f"   Distance: {result['distance']:.4f}")
        print(f"   Comment preview: {result['comment'][:200]}...")


if __name__ == '__main__':
    main()
