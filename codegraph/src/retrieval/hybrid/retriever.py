"""
Hybrid Retriever - Main Class

Combines graph-based (DuckDB/CPG) and vector-based (ChromaDB) retrieval
in parallel with intelligent result merging.
"""

import logging
import asyncio
import time
from typing import List, Optional

from .models import RetrievalResult, HybridRetrievalConfig
from .vector_search import vector_search_async
from .graph_search import graph_search_async
from .merger import merge_results_rrf

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval engine combining vector and graph search.

    Features:
    - Parallel async execution (ChromaDB + DuckDB)
    - Reciprocal Rank Fusion (RRF) for result merging
    - Weighted scoring based on query type
    - Deduplication via node IDs
    - Fallback strategies

    Usage:
        retriever = HybridRetriever(vector_store, cpg_service)
        results = await retriever.retrieve(
            query="Find authentication methods",
            mode="hybrid"  # or "vector_only", "graph_only"
        )
    """

    def __init__(
        self,
        vector_store,  # VectorStore instance
        cpg_service,   # CPGQueryService instance
        config: Optional[HybridRetrievalConfig] = None
    ):
        """
        Initialize hybrid retriever.

        Args:
            vector_store: ChromaDB vector store instance
            cpg_service: DuckDB CPG query service instance
            config: Hybrid retrieval configuration
        """
        self.vector_store = vector_store
        self.cpg_service = cpg_service
        self.config = config or HybridRetrievalConfig()

        logger.info(
            f"Hybrid Retriever initialized: "
            f"vector_weight={self.config.vector_weight}, "
            f"graph_weight={self.config.graph_weight}"
        )

    async def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        query_type: Optional[str] = None,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve results using hybrid search.

        Args:
            query: Natural language query
            mode: "hybrid", "vector_only", or "graph_only"
            query_type: Optional query type for adaptive weighting
                       ("semantic", "structural", "security", etc.)
            **kwargs: Additional parameters (domain, keywords, etc.)

        Returns:
            List of RetrievalResult objects, ranked by score
        """
        start_time = time.time()

        # Adaptive weighting based on query type
        config = self._adapt_config(query_type)

        try:
            if mode == "vector_only":
                results = await self._vector_search_only(query, config, **kwargs)
            elif mode == "graph_only":
                results = await self._graph_search_only(query, config, **kwargs)
            elif mode == "hybrid":
                results = await self._hybrid_search(query, config, **kwargs)
            else:
                raise ValueError(f"Unknown mode: {mode}")

            elapsed = time.time() - start_time
            logger.info(
                f"Hybrid retrieval completed in {elapsed:.3f}s: "
                f"{len(results)} results (mode={mode})"
            )

            return results

        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}", exc_info=True)
            # Fallback to vector-only
            logger.warning("Falling back to vector-only retrieval")
            return await self._vector_search_only(query, config, **kwargs)

    def _adapt_config(self, query_type: Optional[str]) -> HybridRetrievalConfig:
        """
        Adapt configuration based on query type.

        Args:
            query_type: Type of query (semantic, structural, security, etc.)

        Returns:
            Adapted configuration
        """
        if query_type is None:
            return self.config

        # Adaptive weighting based on query type
        adapted_config = HybridRetrievalConfig(
            vector_weight=self.config.vector_weight,
            graph_weight=self.config.graph_weight,
            vector_top_k=self.config.vector_top_k,
            graph_top_k=self.config.graph_top_k,
            final_top_k=self.config.final_top_k,
            min_score_threshold=self.config.min_score_threshold,
            enable_reranking=self.config.enable_reranking
        )

        # Semantic queries: favor vector search
        if query_type in ["semantic", "documentation", "explanation"]:
            adapted_config.vector_weight = 0.75
            adapted_config.graph_weight = 0.25

        # Structural queries: favor graph search
        elif query_type in ["structural", "call_graph", "dependency"]:
            adapted_config.vector_weight = 0.25
            adapted_config.graph_weight = 0.75

        # Security queries: balanced
        elif query_type in ["security", "vulnerability", "taint"]:
            adapted_config.vector_weight = 0.5
            adapted_config.graph_weight = 0.5

        logger.debug(f"Adapted config for {query_type}: v={adapted_config.vector_weight}, g={adapted_config.graph_weight}")
        return adapted_config

    async def _hybrid_search(
        self,
        query: str,
        config: HybridRetrievalConfig,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Parallel hybrid search: vector + graph.

        Args:
            query: Search query
            config: Retrieval configuration
            **kwargs: Additional parameters

        Returns:
            Merged and ranked results
        """
        # Execute searches in parallel
        vector_task = asyncio.create_task(
            vector_search_async(self.vector_store, query, config.vector_top_k, **kwargs)
        )
        graph_task = asyncio.create_task(
            graph_search_async(self.cpg_service, query, config.graph_top_k, **kwargs)
        )

        # Wait for both to complete
        vector_results, graph_results = await asyncio.gather(
            vector_task, graph_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(vector_results, Exception):
            logger.error(f"Vector search failed: {vector_results}")
            vector_results = []

        if isinstance(graph_results, Exception):
            logger.error(f"Graph search failed: {graph_results}")
            graph_results = []

        logger.info(
            f"Parallel retrieval: {len(vector_results)} vector + "
            f"{len(graph_results)} graph results"
        )

        # Merge results with RRF
        merged_results = merge_results_rrf(
            vector_results, graph_results, config
        )

        # Apply score threshold
        filtered_results = [
            r for r in merged_results
            if r.score >= config.min_score_threshold
        ]

        # Return top-K
        return filtered_results[:config.final_top_k]

    async def _vector_search_only(
        self,
        query: str,
        config: HybridRetrievalConfig,
        **kwargs
    ) -> List[RetrievalResult]:
        """Vector search only (fallback mode)."""
        vector_results = await vector_search_async(
            self.vector_store, query, config.final_top_k, **kwargs
        )
        return vector_results[:config.final_top_k]

    async def _graph_search_only(
        self,
        query: str,
        config: HybridRetrievalConfig,
        **kwargs
    ) -> List[RetrievalResult]:
        """Graph search only (fallback mode)."""
        graph_results = await graph_search_async(
            self.cpg_service, query, config.final_top_k, **kwargs
        )
        return graph_results[:config.final_top_k]


__all__ = ['HybridRetriever']
