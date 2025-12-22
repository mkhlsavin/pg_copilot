"""
Vector Search Module

Provides vector-based (ChromaDB) search functionality.
"""

import logging
import asyncio
from typing import List, Dict

from .models import RetrievalResult

logger = logging.getLogger(__name__)


async def vector_search_async(
    vector_store,
    query: str,
    top_k: int,
    **kwargs
) -> List[RetrievalResult]:
    """
    Vector search in ChromaDB (async wrapper).

    Args:
        vector_store: VectorStore instance with ChromaDB
        query: Search query
        top_k: Number of results to return
        **kwargs: Additional parameters (collection_name, etc.)

    Returns:
        List of RetrievalResult objects from vector search
    """
    try:
        # Run in thread pool (ChromaDB is blocking)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            vector_search_sync,
            vector_store,
            query,
            top_k,
            kwargs
        )
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def vector_search_sync(
    vector_store,
    query: str,
    top_k: int,
    kwargs: Dict
) -> List[RetrievalResult]:
    """Synchronous vector search implementation."""
    collection_name = kwargs.get('collection_name', 'qa_pairs')

    # Get collection
    if collection_name == 'qa_pairs' and vector_store.qa_collection:
        collection = vector_store.qa_collection
    elif collection_name == 'cpgql_examples' and vector_store.cpgql_collection:
        collection = vector_store.cpgql_collection
    else:
        logger.warning(f"Collection {collection_name} not found")
        return []

    # Generate query embedding
    query_embedding = vector_store.encoder.encode([query])[0]

    # Search
    search_results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k
    )

    # Convert to RetrievalResult
    results = []
    if search_results and search_results['ids']:
        for i, doc_id in enumerate(search_results['ids'][0]):
            distance = search_results['distances'][0][i] if 'distances' in search_results else 0
            # Convert distance to similarity score (cosine: 1 - distance)
            score = 1.0 - (distance / 2.0)  # Normalize [0, 2] → [0, 1]

            results.append(RetrievalResult(
                id=doc_id,
                content=search_results['documents'][0][i],
                score=score,
                source="vector",
                metadata=search_results['metadatas'][0][i] if 'metadatas' in search_results else {}
            ))

    return results


__all__ = ['vector_search_async', 'vector_search_sync']
