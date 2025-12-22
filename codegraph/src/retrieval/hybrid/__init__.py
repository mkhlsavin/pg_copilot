"""Hybrid Retrieval Package.

Provides hybrid retrieval combining vector (ChromaDB) and graph (DuckDB/CPG) search:
- HybridRetriever: Main hybrid retrieval engine with RRF merging
- SpecializedRetriever: Code quality analysis (dead code, complexity, etc.)
- SubsystemMapper: Architecture and subsystem analysis

Convenience functions:
- hybrid_search_methods: Quick hybrid method search
- semantic_search: Semantic-focused search (vector-heavy)
- structural_search: Structure-focused search (graph-heavy)
"""

from typing import List

from .models import RetrievalResult, HybridRetrievalConfig
from .retriever import HybridRetriever
from .specialized import SpecializedRetriever, create_specialized_retriever
from .subsystem import SubsystemMapper, create_subsystem_mapper
from .domain_plugin import get_subsystems
from .merger import merge_results_rrf
from .vector_search import vector_search_async, vector_search_sync
from .graph_search import graph_search_async, graph_search_sync


# Convenience functions for common use cases

async def hybrid_search_methods(
    query: str,
    vector_store,
    cpg_service,
    top_k: int = 10
) -> List[RetrievalResult]:
    """
    Convenience function for hybrid method search.

    Args:
        query: Natural language query
        vector_store: VectorStore instance
        cpg_service: CPGQueryService instance
        top_k: Number of results to return

    Returns:
        Top-K hybrid search results
    """
    config = HybridRetrievalConfig(
        vector_weight=0.6,
        graph_weight=0.4,
        final_top_k=top_k
    )

    retriever = HybridRetriever(vector_store, cpg_service, config)
    return await retriever.retrieve(query, mode="hybrid")


async def semantic_search(
    query: str,
    vector_store,
    cpg_service,
    top_k: int = 10
) -> List[RetrievalResult]:
    """
    Semantic-focused search (vector-heavy).

    Args:
        query: Natural language query
        vector_store: VectorStore instance
        cpg_service: CPGQueryService instance
        top_k: Number of results to return

    Returns:
        Top-K semantic search results
    """
    config = HybridRetrievalConfig(
        vector_weight=0.8,
        graph_weight=0.2,
        final_top_k=top_k
    )

    retriever = HybridRetriever(vector_store, cpg_service, config)
    return await retriever.retrieve(
        query,
        mode="hybrid",
        query_type="semantic"
    )


async def structural_search(
    query: str,
    vector_store,
    cpg_service,
    top_k: int = 10
) -> List[RetrievalResult]:
    """
    Structure-focused search (graph-heavy).

    Args:
        query: Natural language query
        vector_store: VectorStore instance
        cpg_service: CPGQueryService instance
        top_k: Number of results to return

    Returns:
        Top-K structural search results
    """
    config = HybridRetrievalConfig(
        vector_weight=0.2,
        graph_weight=0.8,
        final_top_k=top_k
    )

    retriever = HybridRetriever(vector_store, cpg_service, config)
    return await retriever.retrieve(
        query,
        mode="hybrid",
        query_type="structural"
    )


__all__ = [
    # Data models
    'RetrievalResult',
    'HybridRetrievalConfig',
    # Main retriever
    'HybridRetriever',
    # Specialized retrievers
    'SpecializedRetriever',
    'create_specialized_retriever',
    'SubsystemMapper',
    'create_subsystem_mapper',
    # Domain plugin
    'get_subsystems',
    # Merging
    'merge_results_rrf',
    # Search functions
    'vector_search_async',
    'vector_search_sync',
    'graph_search_async',
    'graph_search_sync',
    # Convenience functions
    'hybrid_search_methods',
    'semantic_search',
    'structural_search',
]
