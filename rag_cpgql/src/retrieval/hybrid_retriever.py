"""
Hybrid Retriever - Phase 1 Implementation

Combines graph-based (DuckDB/CPG) and vector-based (ChromaDB) retrieval
in parallel with intelligent result merging.

Based on: "Hybrid Code Property Graph.md" research
Author: Phase 1 Implementation
Date: November 25, 2025
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN PLUGIN INTEGRATION
# ============================================================================

def _get_subsystems_from_domain_plugin() -> Optional[Dict[str, Dict]]:
    """
    Try to get subsystems from the active domain plugin.

    Returns:
        Dictionary of subsystems or None if plugin not available
    """
    try:
        from src.domains import DomainRegistry

        domain = DomainRegistry.get_active_or_none()
        if domain is None:
            logger.debug("No active domain plugin")
            return None

        # Load YAML config once for efficiency
        yaml_data = domain._load_yaml_config("subsystems.yaml")
        yaml_subsystems = yaml_data.get('subsystems', {}) if yaml_data else {}

        # Convert domain plugin subsystems to legacy format
        subsystems = {}
        for name, info in domain.subsystems.items():
            # Get keywords from YAML (preferred) or fall back to empty list
            yaml_entry = yaml_subsystems.get(name, {})
            keywords = yaml_entry.get('keywords', [])

            subsystems[name] = {
                'patterns': info.patterns,
                'description': info.description,
                'keywords': keywords,
                'key_functions': info.key_functions,
            }

        logger.debug(f"Loaded {len(subsystems)} subsystems from {domain.name} plugin")
        return subsystems if subsystems else None
    except Exception as e:
        logger.debug(f"Could not load subsystems from domain plugin: {e}")
        return None


def get_subsystems() -> Dict[str, Dict]:
    """
    Get subsystems from the active domain plugin.

    Returns:
        Dictionary of subsystem definitions
    """
    subsystems = _get_subsystems_from_domain_plugin()
    if subsystems:
        return subsystems

    # If no plugin available, return empty dict and log warning
    logger.warning("No domain plugin active - subsystem mapping disabled")
    return {}


@dataclass
class RetrievalResult:
    """Unified retrieval result from any source"""
    id: str
    content: str
    score: float
    source: str  # "vector", "graph", or "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)
    node_id: Optional[int] = None  # CPG node ID (for deduplication)

    def __hash__(self):
        """Enable set operations for deduplication"""
        return hash(self.id)

    def __eq__(self, other):
        """Equality based on ID"""
        if not isinstance(other, RetrievalResult):
            return False
        return self.id == other.id


@dataclass
class HybridRetrievalConfig:
    """Configuration for hybrid retrieval"""
    vector_weight: float = 0.6  # Weight for vector search results
    graph_weight: float = 0.4   # Weight for graph search results
    vector_top_k: int = 20      # Top-K from vector search
    graph_top_k: int = 20       # Top-K from graph search
    final_top_k: int = 10       # Final results after merging
    min_score_threshold: float = 0.1  # Minimum score to consider
    enable_reranking: bool = False  # LLM-based re-ranking (expensive)

    def __post_init__(self):
        """Validate configuration"""
        total_weight = self.vector_weight + self.graph_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")


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
            self._vector_search(query, config.vector_top_k, **kwargs)
        )
        graph_task = asyncio.create_task(
            self._graph_search(query, config.graph_top_k, **kwargs)
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
        merged_results = self._merge_results_rrf(
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
        vector_results = await self._vector_search(query, config.final_top_k, **kwargs)
        return vector_results[:config.final_top_k]

    async def _graph_search_only(
        self,
        query: str,
        config: HybridRetrievalConfig,
        **kwargs
    ) -> List[RetrievalResult]:
        """Graph search only (fallback mode)."""
        graph_results = await self._graph_search(query, config.final_top_k, **kwargs)
        return graph_results[:config.final_top_k]

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Vector search in ChromaDB.

        Args:
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
                self._vector_search_sync,
                query,
                top_k,
                kwargs
            )
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    def _vector_search_sync(
        self,
        query: str,
        top_k: int,
        kwargs: Dict
    ) -> List[RetrievalResult]:
        """Synchronous vector search implementation."""
        collection_name = kwargs.get('collection_name', 'qa_pairs')

        # Get collection
        if collection_name == 'qa_pairs' and self.vector_store.qa_collection:
            collection = self.vector_store.qa_collection
        elif collection_name == 'cpgql_examples' and self.vector_store.cpgql_collection:
            collection = self.vector_store.cpgql_collection
        else:
            logger.warning(f"Collection {collection_name} not found")
            return []

        # Generate query embedding
        query_embedding = self.vector_store.encoder.encode([query])[0]

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

    async def _graph_search(
        self,
        query: str,
        top_k: int,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Graph search in DuckDB CPG.

        Args:
            query: Search query (keywords or patterns)
            top_k: Number of results to return
            **kwargs: Additional parameters (domain, method_pattern, etc.)

        Returns:
            List of RetrievalResult objects from graph search
        """
        try:
            # Run in thread pool (DuckDB might block)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._graph_search_sync,
                query,
                top_k,
                kwargs
            )
            return results

        except Exception as e:
            logger.error(f"Graph search failed: {e}", exc_info=True)
            return []

    def _graph_search_sync(
        self,
        query: str,
        top_k: int,
        kwargs: Dict
    ) -> List[RetrievalResult]:
        """Synchronous graph search implementation."""
        # Extract search parameters
        keywords = kwargs.get('keywords', [])
        domain = kwargs.get('domain', None)

        # Build keyword list from query
        if not keywords:
            # Simple keyword extraction (can be improved with NLP)
            keywords = [w.lower() for w in query.split() if len(w) > 3]

        if not keywords:
            logger.warning("No keywords extracted from query for graph search")
            return []

        # Build SQL query for method search
        keyword_conditions = ' OR '.join([
            f"LOWER(m.name) LIKE '%{kw}%'" for kw in keywords[:5]
        ])

        sql_query = f"""
            SELECT
                m.id,
                m.name,
                m.fullName,
                m.signature,
                m.filename,
                m.lineNumber,
                COUNT(DISTINCT c.id) AS caller_count
            FROM nodes_method m
            LEFT JOIN edges_call ec ON ec.dst = m.id
            LEFT JOIN nodes_call c ON c.id = ec.src
            WHERE {keyword_conditions}
            GROUP BY m.id, m.name, m.fullName, m.signature, m.filename, m.lineNumber
            ORDER BY caller_count DESC, m.name
            LIMIT ?
        """

        try:
            # Execute query
            results_raw = self.cpg_service.execute_query(sql_query, (top_k,))

            # Convert to RetrievalResult
            results = []
            for i, row in enumerate(results_raw):
                # Score based on rank (higher rank = higher score)
                score = 1.0 - (i / max(len(results_raw), 1))

                # Build content string
                content = f"{row.get('name', 'unknown')} - {row.get('filename', 'unknown')}:{row.get('lineNumber', 0)}"
                if row.get('signature'):
                    content += f"\nSignature: {row['signature']}"

                results.append(RetrievalResult(
                    id=f"method_{row.get('id', i)}",
                    content=content,
                    score=score,
                    source="graph",
                    node_id=row.get('id'),
                    metadata={
                        'name': row.get('name'),
                        'fullName': row.get('fullName'),
                        'filename': row.get('filename'),
                        'lineNumber': row.get('lineNumber'),
                        'caller_count': row.get('caller_count', 0)
                    }
                ))

            return results

        except Exception as e:
            logger.error(f"Graph query execution failed: {e}", exc_info=True)
            return []

    def _merge_results_rrf(
        self,
        vector_results: List[RetrievalResult],
        graph_results: List[RetrievalResult],
        config: HybridRetrievalConfig
    ) -> List[RetrievalResult]:
        """
        Merge results using Reciprocal Rank Fusion (RRF) with weighted scoring.

        RRF Formula: score(d) = Σ 1/(k + rank(d))
        where k is a constant (typically 60)

        Args:
            vector_results: Results from vector search
            graph_results: Results from graph search
            config: Configuration with weights

        Returns:
            Merged and sorted results
        """
        k = 60  # RRF constant

        # Build lookup tables for RRF scores
        rrf_scores = {}

        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            result_id = result.id
            rrf_score = config.vector_weight / (k + rank)

            if result_id not in rrf_scores:
                rrf_scores[result_id] = {
                    'rrf_score': 0.0,
                    'result': result,
                    'sources': []
                }

            rrf_scores[result_id]['rrf_score'] += rrf_score
            rrf_scores[result_id]['sources'].append('vector')

        # Process graph results
        for rank, result in enumerate(graph_results, start=1):
            result_id = result.id
            rrf_score = config.graph_weight / (k + rank)

            if result_id not in rrf_scores:
                rrf_scores[result_id] = {
                    'rrf_score': 0.0,
                    'result': result,
                    'sources': []
                }

            rrf_scores[result_id]['rrf_score'] += rrf_score
            rrf_scores[result_id]['sources'].append('graph')

        # Create merged results
        merged_results = []
        for result_id, data in rrf_scores.items():
            result = data['result']
            rrf_score = data['rrf_score']
            sources = data['sources']

            # Determine source label
            if len(sources) == 2:
                source = "hybrid"  # Found in both
            else:
                source = sources[0]

            # Create new result with RRF score
            merged_result = RetrievalResult(
                id=result.id,
                content=result.content,
                score=rrf_score,
                source=source,
                metadata=result.metadata,
                node_id=result.node_id
            )

            merged_results.append(merged_result)

        # Sort by RRF score
        merged_results.sort(key=lambda r: r.score, reverse=True)

        logger.debug(
            f"RRF merging: {len(vector_results)} vector + {len(graph_results)} graph "
            f"→ {len(merged_results)} merged results"
        )

        return merged_results


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


# ============================================================================
# SPECIALIZED RETRIEVERS FOR CODE QUALITY ANALYSIS
# ============================================================================

class SpecializedRetriever:
    """
    Specialized retriever for code quality scenarios (dead code, complexity, duplicates).

    These scenarios require specific graph queries that target particular patterns
    rather than semantic or keyword-based search.
    """

    def __init__(self, cpg_service):
        """
        Initialize specialized retriever.

        Args:
            cpg_service: CPGQueryService instance for DuckDB queries
        """
        self.cpg = cpg_service
        logger.info("Specialized Retriever initialized for code quality analysis")

    def retrieve_dead_code(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potentially dead (uncalled) functions.

        Uses call graph analysis to find methods that are never called.

        Returns:
            List of RetrievalResult with dead code candidates
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                'dead_code' AS category
            FROM nodes_method m
            LEFT JOIN call_containment c ON c.callee_name = m.name
            WHERE c.callee_name IS NULL
            AND m.name NOT LIKE 'test_%'
            AND m.name NOT LIKE 'main'
            AND m.name NOT LIKE '%_init'
            AND m.name NOT LIKE '%_fini'
            AND m.name NOT LIKE '__attribute__%'
            AND (m.line_number_end - m.line_number) > 5
            AND m.line_number_end > 0
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "dead_code")
        except Exception as e:
            logger.error(f"Dead code retrieval failed: {e}")
            return []

    def retrieve_high_complexity(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find methods with high complexity (based on line count as proxy).

        Since cyclomatic complexity isn't stored, uses line count as heuristic.

        Returns:
            List of RetrievalResult with high-complexity methods
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                CASE
                    WHEN (m.line_number_end - m.line_number) > 200 THEN 'CRITICAL'
                    WHEN (m.line_number_end - m.line_number) > 100 THEN 'HIGH'
                    ELSE 'MEDIUM'
                END AS severity,
                'high_complexity' AS category
            FROM nodes_method m
            WHERE (m.line_number_end - m.line_number) > 50
            AND m.line_number_end > 0
            AND m.name NOT LIKE 'test_%'
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "complexity")
        except Exception as e:
            logger.error(f"Complexity retrieval failed: {e}")
            return []

    def retrieve_long_methods(self, threshold: int = 50, limit: int = 50) -> List[RetrievalResult]:
        """
        Find methods exceeding line count threshold.

        Args:
            threshold: Minimum line count to include
            limit: Maximum results to return

        Returns:
            List of RetrievalResult with long methods
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                'long_method' AS category
            FROM nodes_method m
            WHERE (m.line_number_end - m.line_number) > ?
            AND m.line_number_end > 0
            AND m.name NOT LIKE 'test_%'
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (threshold, limit))
            return self._convert_to_results(results, "long_method")
        except Exception as e:
            logger.error(f"Long method retrieval failed: {e}")
            return []

    def retrieve_duplicates(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potential code duplicates based on similar method names.

        Note: True clone detection requires more sophisticated analysis.
        This is a heuristic approach based on naming patterns.

        Returns:
            List of RetrievalResult with duplicate candidates
        """
        query = """
            SELECT DISTINCT
                m1.id AS id,
                m1.name AS name,
                m1.full_name,
                m1.filename,
                m1.line_number,
                m2.name AS similar_to,
                m2.filename AS similar_file,
                'duplicate' AS category
            FROM nodes_method m1
            JOIN nodes_method m2 ON (
                m1.name LIKE m2.name || '%' OR m2.name LIKE m1.name || '%'
            )
            WHERE m1.id < m2.id
            AND m1.filename != m2.filename
            AND (m1.line_number_end - m1.line_number) > 10
            AND m1.line_number_end > 0
            AND m1.name NOT LIKE 'test_%'
            AND LENGTH(m1.name) > 5
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "duplicate")
        except Exception as e:
            logger.error(f"Duplicate retrieval failed: {e}")
            return []

    def retrieve_entry_points(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find entry points and attack surface (methods called but calling nothing).

        Returns:
            List of RetrievalResult with entry point candidates
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                COUNT(DISTINCT c.call_id) AS caller_count,
                'entry_point' AS category
            FROM nodes_method m
            JOIN call_containment c ON c.callee_name = m.name
            LEFT JOIN call_containment c2 ON c2.containing_method_name = m.name
            WHERE c2.call_id IS NULL
            AND m.name NOT LIKE 'test_%'
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number, m.line_number_end
            HAVING COUNT(DISTINCT c.call_id) > 3
            ORDER BY caller_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "entry_point")
        except Exception as e:
            logger.error(f"Entry point retrieval failed: {e}")
            return []

    def retrieve_god_classes(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potential god classes (files with many methods).

        Returns:
            List of RetrievalResult with god class candidates
        """
        query = """
            SELECT DISTINCT
                m.filename AS id,
                m.filename AS name,
                m.filename AS full_name,
                m.filename AS filename,
                MIN(m.line_number) AS line_number,
                COUNT(DISTINCT m.id) AS method_count,
                SUM(m.line_number_end - m.line_number) AS total_lines,
                'god_class' AS category
            FROM nodes_method m
            WHERE m.name NOT LIKE 'test_%'
            AND m.line_number_end > 0
            GROUP BY m.filename
            HAVING COUNT(DISTINCT m.id) > 30
               OR SUM(m.line_number_end - m.line_number) > 1000
            ORDER BY total_lines DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "god_class")
        except Exception as e:
            logger.error(f"God class retrieval failed: {e}")
            return []

    def _convert_to_results(
        self,
        raw_results: List[Dict],
        category: str
    ) -> List[RetrievalResult]:
        """Convert raw query results to RetrievalResult objects."""
        results = []
        for i, row in enumerate(raw_results):
            # Score based on position (first = best)
            score = 1.0 - (i / max(len(raw_results), 1))

            # Build content string
            name = row.get('name', 'unknown')
            filename = row.get('filename', 'unknown')
            line = row.get('line_number', 0)
            content = f"{name} - {filename}:{line}"

            if row.get('line_count'):
                content += f" ({row['line_count']} lines)"
            if row.get('similar_to'):
                content += f" [similar to {row['similar_to']}]"
            if row.get('method_count'):
                content += f" [{row['method_count']} methods]"

            results.append(RetrievalResult(
                id=f"{category}_{row.get('id', i)}",
                content=content,
                score=score,
                source="graph",
                node_id=row.get('id'),
                metadata={
                    'category': category,
                    'name': name,
                    'full_name': row.get('full_name'),
                    'filename': filename,
                    'line_number': line,
                    **{k: v for k, v in row.items() if k not in ['id', 'name', 'full_name', 'filename', 'line_number']}
                }
            ))

        return results


def create_specialized_retriever(cpg_service) -> SpecializedRetriever:
    """Factory function to create a SpecializedRetriever."""
    return SpecializedRetriever(cpg_service)


# ============================================================================
# SUBSYSTEM MAPPER FOR ARCHITECTURE QUERIES
# ============================================================================


class SubsystemMapper:
    """
    Maps queries to PostgreSQL subsystems for architecture analysis.

    Helps with scenarios 11 (Dependencies) and 13 (Subsystem Explanation)
    by identifying which subsystem(s) a query relates to.
    """

    def __init__(self, cpg_service):
        self.cpg = cpg_service

    def identify_subsystem(self, query_text: str) -> List[Dict]:
        """
        Identify which subsystem(s) a query relates to.

        Args:
            query_text: User's query text

        Returns:
            List of matching subsystems with confidence scores
        """
        query_lower = query_text.lower()
        matches = []

        subsystems = get_subsystems()
        for subsystem, info in subsystems.items():
            score = 0
            matched_keywords = []

            # Check keywords
            for kw in info.get('keywords', []):
                if kw.lower() in query_lower:
                    score += 10
                    matched_keywords.append(kw)

            # Check patterns
            for pattern in info['patterns']:
                if pattern.lower() in query_lower:
                    score += 20
                    matched_keywords.append(pattern)

            if score > 0:
                matches.append({
                    'subsystem': subsystem,
                    'score': score,
                    'description': info['description'],
                    'matched_keywords': matched_keywords
                })

        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches

    def retrieve_subsystem_methods(
        self,
        subsystem: str,
        limit: int = 50
    ) -> List[RetrievalResult]:
        """
        Retrieve methods belonging to a specific subsystem.

        Args:
            subsystem: Subsystem name (e.g., 'executor', 'parser')
            limit: Maximum results

        Returns:
            List of RetrievalResult with methods from that subsystem
        """
        subsystems = get_subsystems()
        if subsystem not in subsystems:
            logger.warning(f"Unknown subsystem: {subsystem}")
            return []

        info = subsystems[subsystem]

        # Build pattern matching conditions
        pattern_conditions = []
        for pattern in info['patterns']:
            pattern_conditions.append(f"m.filename LIKE '%{pattern}%'")

        if not pattern_conditions:
            return []

        pattern_where = ' OR '.join(pattern_conditions)

        query = f"""
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                '{subsystem}' AS subsystem
            FROM nodes_method m
            WHERE ({pattern_where})
            AND m.name NOT LIKE 'test_%'
            AND m.line_number_end > 0
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))

            retrieval_results = []
            for i, row in enumerate(results):
                score = 1.0 - (i / max(len(results), 1))

                content = f"{row.get('name', 'unknown')} - {row.get('filename', 'unknown')}:{row.get('line_number', 0)}"
                if row.get('line_count'):
                    content += f" ({row['line_count']} lines)"

                retrieval_results.append(RetrievalResult(
                    id=f"subsystem_{subsystem}_{row.get('id', i)}",
                    content=content,
                    score=score,
                    source="graph",
                    node_id=row.get('id'),
                    metadata={
                        'subsystem': subsystem,
                        'name': row.get('name'),
                        'full_name': row.get('full_name'),
                        'filename': row.get('filename'),
                        'line_number': row.get('line_number'),
                        'line_count': row.get('line_count')
                    }
                ))

            return retrieval_results

        except Exception as e:
            logger.error(f"Subsystem retrieval failed for {subsystem}: {e}")
            return []

    def retrieve_subsystem_dependencies(
        self,
        subsystem: str,
        limit: int = 50
    ) -> List[RetrievalResult]:
        """
        Find dependencies between a subsystem and other subsystems.

        Args:
            subsystem: Subsystem name
            limit: Maximum results

        Returns:
            List of RetrievalResult showing cross-subsystem dependencies
        """
        subsystems = get_subsystems()
        if subsystem not in subsystems:
            return []

        info = subsystems[subsystem]

        # Build pattern for this subsystem
        patterns = info['patterns']
        if not patterns:
            return []

        pattern_conditions = ' OR '.join([f"c.filename LIKE '%{p}%'" for p in patterns])

        query = f"""
            SELECT
                c.filename AS caller_file,
                c.containing_method_name AS caller_method,
                m.filename AS callee_file,
                c.callee_name AS callee_method,
                '{subsystem}' AS from_subsystem
            FROM call_containment c
            JOIN nodes_method m ON c.callee_name = m.name
            WHERE ({pattern_conditions})
            AND NOT ({' OR '.join([f"m.filename LIKE '%{p}%'" for p in patterns])})
            AND m.filename IS NOT NULL
            AND c.filename != m.filename
            GROUP BY c.filename, c.containing_method_name, m.filename, c.callee_name
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))

            retrieval_results = []
            for i, row in enumerate(results):
                score = 1.0 - (i / max(len(results), 1))

                content = f"{row.get('caller_method', 'unknown')} ({row.get('caller_file', '')}) -> {row.get('callee_method', 'unknown')} ({row.get('callee_file', '')})"

                retrieval_results.append(RetrievalResult(
                    id=f"dep_{subsystem}_{i}",
                    content=content,
                    score=score,
                    source="graph",
                    metadata={
                        'from_subsystem': subsystem,
                        'caller_file': row.get('caller_file'),
                        'caller_method': row.get('caller_method'),
                        'callee_file': row.get('callee_file'),
                        'callee_method': row.get('callee_method')
                    }
                ))

            return retrieval_results

        except Exception as e:
            logger.error(f"Subsystem dependency retrieval failed: {e}")
            return []


def create_subsystem_mapper(cpg_service) -> SubsystemMapper:
    """Factory function to create a SubsystemMapper."""
    return SubsystemMapper(cpg_service)
