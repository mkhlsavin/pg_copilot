"""Result Ranker - Rank query results by relevance to question.

This module implements Phase 2 of the Query Funnel approach:
semantic ranking of results to prioritize the most relevant matches.

Phase 1 Extension: Cross-source ranking for hybrid retrieval.
Supports ranking results from multiple sources (vector, graph, hybrid)
with source confidence scoring and optional LLM re-ranking.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Import RetrievalResult for hybrid ranking (optional for backward compatibility)
try:
    from src.retrieval.hybrid_retriever import RetrievalResult
except ImportError:
    logger.warning("hybrid_retriever not available - cross-source ranking disabled")
    RetrievalResult = None

# Lazy import for sentence transformers (optional dependency)
_sentence_transformer_model = None

def _get_embedding_model():
    """Lazily load sentence transformer model."""
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer model for semantic similarity...")
            _sentence_transformer_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
        except ImportError:
            logger.warning("sentence-transformers not installed. Semantic similarity scoring disabled.")
            _sentence_transformer_model = False
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            _sentence_transformer_model = False
    return _sentence_transformer_model if _sentence_transformer_model is not False else None


@dataclass
class RelevanceScore:
    """Relevance score breakdown for a result."""
    total: float
    keyword_match: float = 0.0
    tag_coverage: float = 0.0
    name_match: float = 0.0
    length_bonus: float = 0.0
    semantic_similarity: float = 0.0
    # Phase 1 extensions for cross-source ranking
    source_confidence: float = 0.0  # Confidence in retrieval source
    retrieval_score: float = 0.0     # Original RRF/similarity score from retrieval

    def get_breakdown(self) -> Dict[str, float]:
        """Get score breakdown as dictionary."""
        return {
            'total': self.total,
            'keyword_match': self.keyword_match,
            'tag_coverage': self.tag_coverage,
            'name_match': self.name_match,
            'length_bonus': self.length_bonus,
            'semantic_similarity': self.semantic_similarity,
            'source_confidence': self.source_confidence,
            'retrieval_score': self.retrieval_score
        }


# ===== PHASE 5 IMPROVEMENT: Query-Type Weighted Ranking =====
# Different query types benefit from different ranking signal weights

QUERY_TYPE_WEIGHTS = {
    'definition': {
        'name_match': 0.50,      # Exact name match is critical
        'keyword_match': 0.25,   # Keyword context
        'semantic': 0.15,        # Semantic similarity
        'tag_coverage': 0.05,    # Tags less important
        'length_bonus': 0.05,    # Length less important
    },
    'security': {
        'pattern_match': 0.40,   # Pattern detection is key
        'keyword_match': 0.25,   # Security keywords
        'semantic': 0.20,        # Semantic context
        'tag_coverage': 0.10,    # Security tags
        'length_bonus': 0.05,    # Complexity
    },
    'dead_code': {
        'confidence': 0.45,      # Detection confidence
        'keyword_match': 0.25,   # Dead code keywords
        'semantic': 0.15,        # Semantic context
        'tag_coverage': 0.10,    # Tags
        'length_bonus': 0.05,    # Complexity
    },
    'duplicate': {
        'similarity': 0.50,      # Clone similarity is critical
        'pattern_match': 0.25,   # Shared patterns
        'semantic': 0.15,        # Semantic similarity
        'keyword_match': 0.05,   # Keywords less important
        'length_bonus': 0.05,    # Length less important
    },
    'call_graph': {
        'name_match': 0.40,      # Function name matching
        'keyword_match': 0.25,   # Relationship keywords
        'semantic': 0.20,        # Semantic context
        'tag_coverage': 0.10,    # Tags
        'length_bonus': 0.05,    # Complexity
    },
    'dataflow': {
        'semantic': 0.35,        # Semantic understanding important
        'keyword_match': 0.30,   # Variable/flow keywords
        'name_match': 0.20,      # Function names
        'tag_coverage': 0.10,    # Tags
        'length_bonus': 0.05,    # Complexity
    },
    'general': {
        'keyword_match': 0.30,   # Balanced approach
        'semantic': 0.25,        # Semantic similarity
        'name_match': 0.20,      # Name matching
        'tag_coverage': 0.15,    # Tag coverage
        'length_bonus': 0.10,    # Complexity
    },
}


def detect_query_type_for_ranking(query: str) -> str:
    """
    Detect query type for ranking weight selection.

    Args:
        query: User query string

    Returns:
        Query type string (definition, security, dead_code, duplicate, call_graph, dataflow, general)
    """
    query_lower = query.lower()

    # Definition queries
    if any(kw in query_lower for kw in ['where is', 'defined', 'definition', 'signature', 'find function', 'locate']):
        return 'definition'

    # Security queries
    if any(kw in query_lower for kw in ['vulnerab', 'security', 'injection', 'overflow', 'memory leak', 'exploit']):
        return 'security'

    # Dead code queries
    if any(kw in query_lower for kw in ['dead code', 'unused', 'unreachable', 'deprecated', 'never called']):
        return 'dead_code'

    # Duplicate queries
    if any(kw in query_lower for kw in ['duplicate', 'clone', 'similar', 'copy-paste', 'repeated']):
        return 'duplicate'

    # Call graph queries
    if any(kw in query_lower for kw in ['who calls', 'callers', 'callees', 'what calls', 'call graph']):
        return 'call_graph'

    # Dataflow queries
    if any(kw in query_lower for kw in ['dataflow', 'data flow', 'trace', 'flows', 'taint', 'variable']):
        return 'dataflow'

    return 'general'


class ResultRanker:
    """
    Rank query results by semantic relevance to question.

    Uses multiple relevance signals:
    1. Keyword overlap (question vs result text)
    2. Tag coverage (enrichment tags present)
    3. Name match (method/function name similarity)
    4. Length/complexity bonus (non-trivial results)
    5. Semantic similarity (embedding-based similarity)

    Phase 5 Enhancement: Query-type weighted ranking for improved precision.
    """

    def __init__(self, enable_semantic: bool = True, enable_llm_rerank: bool = False):
        """Initialize Result Ranker.

        Args:
            enable_semantic: Whether to enable semantic similarity scoring (requires sentence-transformers)
            enable_llm_rerank: Whether to enable LLM-based re-ranking for top-k results
        """
        self.enable_semantic = enable_semantic
        self.enable_llm_rerank = enable_llm_rerank
        self._embedding_model = None
        self._llm_client = None  # Lazy-loaded if LLM re-ranking enabled

        # Signal weights (must sum to 1.0) - default weights
        if enable_semantic:
            # With semantic similarity enabled (5 signals)
            self.keyword_weight = 0.25      # Lexical similarity
            self.tag_weight = 0.20          # Tag coverage
            self.name_weight = 0.15         # Name matching
            self.length_weight = 0.10       # Code complexity
            self.semantic_weight = 0.30     # Semantic similarity (highest weight)
        else:
            # Without semantic similarity (4 signals - original weights)
            self.keyword_weight = 0.4       # Lexical similarity
            self.tag_weight = 0.3           # Tag coverage
            self.name_weight = 0.2          # Name matching
            self.length_weight = 0.1        # Code complexity
            self.semantic_weight = 0.0      # Disabled

        # Cross-source ranking weights (for hybrid retrieval)
        self.source_confidence_weight = 0.15  # Confidence in source reliability
        self.retrieval_score_weight = 0.20    # Original retrieval score (RRF/similarity)

    def set_weights_for_query_type(self, query: str):
        """
        Dynamically set weights based on query type.

        Phase 5 Enhancement: Query-type weighted ranking.

        Args:
            query: User query string
        """
        query_type = detect_query_type_for_ranking(query)
        weights = QUERY_TYPE_WEIGHTS.get(query_type, QUERY_TYPE_WEIGHTS['general'])

        # Map query-type weights to ranker weights
        self.keyword_weight = weights.get('keyword_match', 0.25)
        self.name_weight = weights.get('name_match', 0.20)
        self.tag_weight = weights.get('tag_coverage', 0.15)
        self.length_weight = weights.get('length_bonus', 0.10)

        # Semantic weight uses the 'semantic' key or combines pattern/confidence/similarity
        if self.enable_semantic:
            self.semantic_weight = weights.get('semantic', 0.20)
        else:
            # Redistribute semantic weight to other signals
            self.keyword_weight += weights.get('semantic', 0.20) / 2
            self.name_weight += weights.get('semantic', 0.20) / 2
            self.semantic_weight = 0.0

        logger.debug(f"Set weights for query type '{query_type}': keyword={self.keyword_weight:.2f}, "
                    f"name={self.name_weight:.2f}, tag={self.tag_weight:.2f}, "
                    f"length={self.length_weight:.2f}, semantic={self.semantic_weight:.2f}")

    def rank_results(
        self,
        results: List[str],
        question: str,
        context: Dict[str, Any],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rank results by multiple relevance signals.

        Args:
            results: List of result strings from executor
            question: Original user question
            context: Context dict with enrichment_hints, analysis, etc.
            top_k: Number of top results to return

        Returns:
            List of dicts with:
            - result: Original result string
            - score: Total relevance score
            - score_breakdown: Dict with individual signal scores
        """
        if not results:
            logger.warning("No results to rank")
            return []

        logger.info(f"Ranking {len(results)} results (top_k={top_k})")

        scored_results = []

        for result in results:
            score = self._compute_relevance_score(result, question, context)
            scored_results.append({
                "result": result,
                "score": score.total,
                "score_breakdown": score.get_breakdown()
            })

        # Sort by score descending
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        top_results = scored_results[:top_k]

        logger.info(f"Returning top {len(top_results)} ranked results")
        logger.debug(f"Top score: {top_results[0]['score']:.3f}, Bottom score: {top_results[-1]['score']:.3f}")

        return top_results

    def rank_hybrid_results(
        self,
        results: List['RetrievalResult'],
        question: str,
        context: Dict[str, Any],
        top_k: int = 10,
        enable_llm_rerank: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank hybrid retrieval results from multiple sources.

        Phase 1 Extension: Cross-source ranking for vector + graph + hybrid results.

        Integrates:
        - Original retrieval scores (RRF/similarity from HybridRetriever)
        - Source confidence (reliability of vector/graph/hybrid sources)
        - All existing relevance signals (keyword, tags, names, etc.)
        - Optional LLM re-ranking for top-k results

        Args:
            results: List of RetrievalResult objects from HybridRetriever
            question: Original user question
            context: Context dict with enrichment_hints, analysis, etc.
            top_k: Number of top results to return
            enable_llm_rerank: Override instance setting for LLM re-ranking

        Returns:
            List of dicts with:
            - result: RetrievalResult object
            - score: Total relevance score
            - score_breakdown: Dict with individual signal scores
            - source: Source type ("vector", "graph", "hybrid")
        """
        if not results:
            logger.warning("No hybrid results to rank")
            return []

        if RetrievalResult is None:
            logger.error("RetrievalResult not available - cannot rank hybrid results")
            return []

        logger.info(f"Ranking {len(results)} hybrid results from multiple sources (top_k={top_k})")

        # Count sources
        sources = {}
        for r in results:
            sources[r.source] = sources.get(r.source, 0) + 1
        logger.info(f"Source distribution: {sources}")

        scored_results = []

        for result in results:
            # Compute cross-source relevance score
            score = self._compute_cross_source_relevance(result, question, context)
            scored_results.append({
                "result": result,
                "score": score.total,
                "score_breakdown": score.get_breakdown(),
                "source": result.source,
                "node_id": result.node_id,
                "metadata": result.metadata
            })

        # Sort by score descending
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        top_results = scored_results[:top_k]

        # Optional LLM re-ranking for top results
        if enable_llm_rerank is None:
            enable_llm_rerank = self.enable_llm_rerank

        if enable_llm_rerank and len(top_results) > 1:
            logger.info(f"Applying LLM re-ranking to top {len(top_results)} results")
            top_results = self._llm_rerank(top_results, question, context)

        logger.info(f"Returning top {len(top_results)} ranked hybrid results")
        if top_results:
            logger.debug(f"Top score: {top_results[0]['score']:.3f}, Bottom score: {top_results[-1]['score']:.3f}")
            logger.debug(f"Top source: {top_results[0]['source']}, Bottom source: {top_results[-1]['source']}")

        return top_results

    def _compute_relevance_score(
        self,
        result: str,
        question: str,
        context: Dict[str, Any]
    ) -> RelevanceScore:
        """
        Multi-signal relevance scoring.

        Signals:
        1. Keyword match (25%/40%) - Lexical overlap between question and result
        2. Tag coverage (20%/30%) - How many enrichment tags are relevant
        3. Name match (15%/20%) - Method/function name similarity
        4. Length bonus (10%) - Prefer non-trivial code
        5. Semantic similarity (30%/0%) - Embedding-based similarity (if enabled)

        Args:
            result: Result string (method name or code snippet)
            question: Original question
            context: Context with enrichment hints

        Returns:
            RelevanceScore object with breakdown
        """
        # 1. Keyword match score (0.0-1.0)
        keyword_score = self._keyword_similarity(result, question)

        # 2. Tag coverage score (0.0-1.0)
        tag_score = self._tag_coverage(result, context)

        # 3. Name match score (0.0-1.0)
        name_score = self._name_match(result, question)

        # 4. Length/complexity bonus (0.0-1.0)
        length_score = self._complexity_score(result)

        # 5. Semantic similarity score (0.0-1.0) - only if enabled
        semantic_score = 0.0
        if self.enable_semantic:
            semantic_score = self._semantic_similarity(result, question)

        # Weighted total
        total = (
            self.keyword_weight * keyword_score +
            self.tag_weight * tag_score +
            self.name_weight * name_score +
            self.length_weight * length_score +
            self.semantic_weight * semantic_score
        )

        return RelevanceScore(
            total=total,
            keyword_match=keyword_score,
            tag_coverage=tag_score,
            name_match=name_score,
            length_bonus=length_score,
            semantic_similarity=semantic_score
        )

    def _compute_cross_source_relevance(
        self,
        result: 'RetrievalResult',
        question: str,
        context: Dict[str, Any]
    ) -> RelevanceScore:
        """
        Compute cross-source relevance score for hybrid retrieval results.

        Phase 1 Extension: Combines traditional relevance signals with:
        - Original retrieval score (RRF/similarity from HybridRetriever)
        - Source confidence (reliability of vector/graph/hybrid sources)

        Weighting strategy:
        - Retrieval score: 20% - Trust the hybrid retriever's initial ranking
        - Source confidence: 15% - Factor in source reliability
        - Content signals: 65% - Traditional relevance scoring

        Args:
            result: RetrievalResult object with content, score, source
            question: Original question
            context: Context with enrichment hints

        Returns:
            RelevanceScore with cross-source components
        """
        # 1. Get original retrieval score (already normalized 0-1)
        retrieval_score = result.score

        # 2. Compute source confidence
        source_confidence = self._compute_source_confidence(result.source, question, context)

        # 3. Compute content-based relevance on result content
        # Use scaled weights for content signals (65% total)
        content_weight_scale = 0.65

        # Get base content scores
        keyword_score = self._keyword_similarity(result.content, question)
        tag_score = self._tag_coverage(result.content, context)
        name_score = self._name_match(result.content, question)
        length_score = self._complexity_score(result.content)

        semantic_score = 0.0
        if self.enable_semantic:
            semantic_score = self._semantic_similarity(result.content, question)

        # Content-based total (normalized within 65%)
        content_total = (
            self.keyword_weight * keyword_score +
            self.tag_weight * tag_score +
            self.name_weight * name_score +
            self.length_weight * length_score +
            self.semantic_weight * semantic_score
        ) * content_weight_scale

        # 4. Combine all scores
        total = (
            self.retrieval_score_weight * retrieval_score +      # 20%
            self.source_confidence_weight * source_confidence +  # 15%
            content_total                                         # 65%
        )

        return RelevanceScore(
            total=total,
            keyword_match=keyword_score,
            tag_coverage=tag_score,
            name_match=name_score,
            length_bonus=length_score,
            semantic_similarity=semantic_score,
            source_confidence=source_confidence,
            retrieval_score=retrieval_score
        )

    def _keyword_similarity(self, result: str, question: str) -> float:
        """
        Compute lexical similarity between result and question.

        Uses Jaccard similarity on word sets (case-insensitive).

        Args:
            result: Result string
            question: Question string

        Returns:
            Jaccard similarity score (0.0-1.0)
        """
        # Extract alphanumeric tokens
        result_tokens = set(re.findall(r'\w+', result.lower()))
        question_tokens = set(re.findall(r'\w+', question.lower()))

        if not result_tokens or not question_tokens:
            return 0.0

        intersection = result_tokens & question_tokens
        union = result_tokens | question_tokens

        similarity = len(intersection) / len(union) if union else 0.0

        return similarity

    def _tag_coverage(self, result: str, context: Dict[str, Any]) -> float:
        """
        Compute tag coverage score.

        Checks how many enrichment tag values appear in the result.

        Args:
            result: Result string
            context: Context with enrichment_hints

        Returns:
            Coverage ratio (0.0-1.0)
        """
        hints = context.get('enrichment_hints', {})
        tags = hints.get('tags', [])

        if not tags:
            return 0.5  # Neutral score if no tags

        result_lower = result.lower()

        # Count how many tag values appear in result
        matches = 0
        for tag in tags[:5]:  # Check top 5 tags
            tag_value = tag.get('tag_value', '')
            if tag_value:
                # Convert tag_value to searchable form (replace hyphens with spaces/underscores)
                search_terms = tag_value.replace('-', ' ').replace('_', ' ').split()
                for term in search_terms:
                    if term.lower() in result_lower:
                        matches += 1
                        break  # Count each tag once

        coverage = matches / min(len(tags), 5)  # Normalize by top 5 tags

        return coverage

    def _name_match(self, result: str, question: str) -> float:
        """
        Compute method/function name match score.

        Extracts potential method names from question and checks if they appear in result.

        Args:
            result: Result string
            question: Question string

        Returns:
            Name match score (0.0-1.0)
        """
        # Extract potential function/method names from question
        # Look for patterns like: get_user, SendData, timestamp2time_t
        name_patterns = re.findall(r'\b[a-z_][a-z0-9_]*\b|\b[A-Z][a-zA-Z0-9]*\b', question)

        if not name_patterns:
            return 0.5  # Neutral if no names found

        result_lower = result.lower()

        # Check for exact or partial matches
        exact_matches = 0
        partial_matches = 0

        for name in name_patterns:
            name_lower = name.lower()
            if len(name) < 3:  # Skip very short tokens
                continue

            if name_lower in result_lower:
                exact_matches += 1
            elif any(part in result_lower for part in name_lower.split('_')):
                partial_matches += 0.5

        total_score = (exact_matches + partial_matches) / max(len([n for n in name_patterns if len(n) >= 3]), 1)

        # Cap at 1.0
        return min(total_score, 1.0)

    def _complexity_score(self, result: str) -> float:
        """
        Compute code complexity bonus.

        Prefers non-trivial results (longer, more informative).

        Args:
            result: Result string

        Returns:
            Complexity score (0.0-1.0)
        """
        # Score based on length (normalized)
        length = len(result)

        # Scoring tiers:
        # - Very short (<10 chars): 0.2
        # - Short (10-30 chars): 0.4
        # - Medium (30-100 chars): 0.7
        # - Long (100+ chars): 1.0

        if length < 10:
            return 0.2
        elif length < 30:
            return 0.4
        elif length < 100:
            return 0.7
        else:
            return 1.0

    def _semantic_similarity(self, result: str, question: str) -> float:
        """
        Compute semantic similarity using sentence embeddings.

        Uses sentence-transformers to compute cosine similarity between
        question and result embeddings.

        Args:
            result: Result string
            question: Question string

        Returns:
            Cosine similarity score (0.0-1.0)
        """
        # Lazy load embedding model
        if self._embedding_model is None:
            self._embedding_model = _get_embedding_model()

        # If model loading failed, return neutral score
        if self._embedding_model is None:
            return 0.5

        try:
            # Encode question and result
            question_emb = self._embedding_model.encode(question, convert_to_tensor=False)
            result_emb = self._embedding_model.encode(result, convert_to_tensor=False)

            # Compute cosine similarity
            cosine_sim = np.dot(question_emb, result_emb) / (
                np.linalg.norm(question_emb) * np.linalg.norm(result_emb)
            )

            # Normalize to 0.0-1.0 range (cosine similarity is already -1 to 1)
            # Shift and scale from [-1, 1] to [0, 1]
            normalized_sim = (cosine_sim + 1.0) / 2.0

            return float(normalized_sim)

        except Exception as e:
            logger.warning(f"Failed to compute semantic similarity: {e}")
            return 0.5  # Neutral score on error

    def _compute_source_confidence(
        self,
        source: str,
        question: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Compute confidence score for retrieval source.

        Phase 1 Extension: Different sources have different reliability for different query types.

        Source reliability heuristics:
        - "hybrid": Highest confidence (0.95) - Consensus from multiple sources
        - "vector": High for semantic queries (0.85), medium otherwise (0.7)
        - "graph": High for structural queries (0.85), medium otherwise (0.7)

        Query type detection (simple heuristics):
        - Structural: Contains keywords like "calls", "depends", "flow", "path"
        - Semantic: Contains keywords like "what", "why", "how", "explain"

        Args:
            source: Source type ("vector", "graph", "hybrid")
            question: Original question
            context: Context dict (for future enhancements)

        Returns:
            Confidence score (0.0-1.0)
        """
        question_lower = question.lower()

        # Detect query type
        structural_keywords = ['calls', 'call', 'depends', 'dependency', 'flow', 'path',
                               'uses', 'invokes', 'reaches', 'structure']
        semantic_keywords = ['what', 'why', 'how', 'explain', 'describe', 'meaning',
                            'purpose', 'understand', 'does']

        is_structural = any(kw in question_lower for kw in structural_keywords)
        is_semantic = any(kw in question_lower for kw in semantic_keywords)

        # Confidence scoring
        if source == "hybrid":
            # Hybrid results have highest confidence (consensus)
            return 0.95

        elif source == "vector":
            # Vector search excels at semantic queries
            if is_semantic:
                return 0.85
            elif is_structural:
                return 0.65  # Lower confidence for structural queries
            else:
                return 0.75  # Neutral queries

        elif source == "graph":
            # Graph search excels at structural queries
            if is_structural:
                return 0.85
            elif is_semantic:
                return 0.65  # Lower confidence for semantic queries
            else:
                return 0.75  # Neutral queries

        else:
            # Unknown source
            logger.warning(f"Unknown source type: {source}")
            return 0.5

    def _llm_rerank(
        self,
        ranked_results: List[Dict[str, Any]],
        question: str,
        context: Dict[str, Any],
        max_tokens: int = 200
    ) -> List[Dict[str, Any]]:
        """
        LLM-based re-ranking for top-k results.

        Phase 2 Enhancement: Use LLM to re-rank top results by relevance scoring.

        Strategy:
        1. Take top-k results from initial ranking
        2. Format as numbered list with content snippets
        3. Ask LLM to score relevance (0-10) for each result
        4. Parse LLM response and reorder by LLM scores
        5. Combine LLM scores with existing scores (weighted)
        6. Fallback to original ranking on error

        Args:
            ranked_results: List of ranked result dicts
            question: Original question
            context: Context dict
            max_tokens: Maximum tokens for LLM response

        Returns:
            Re-ranked results (or original on error)
        """
        if not self.enable_llm_rerank:
            return ranked_results

        if len(ranked_results) <= 1:
            return ranked_results

        try:
            # Lazy load LLM client
            if self._llm_client is None:
                try:
                    from src.llm.llm_interface_compat import LLMInterface
                    self._llm_client = LLMInterface()
                    if not self._llm_client.is_available():
                        logger.warning("LLM not available for re-ranking")
                        return ranked_results
                except Exception as e:
                    logger.warning(f"Could not initialize LLM for re-ranking: {e}")
                    return ranked_results

            # Format results for LLM (limit to top 10)
            results_to_rerank = ranked_results[:10]
            prompt = self._build_rerank_prompt(question, results_to_rerank)

            # Call LLM
            logger.info(f"LLM re-ranking {len(results_to_rerank)} results...")
            response = self._llm_client.generate_simple(prompt, max_tokens=max_tokens)

            if not response:
                logger.warning("LLM returned empty response for re-ranking")
                return ranked_results

            # Parse LLM scores
            llm_scores = self._parse_rerank_response(response, len(results_to_rerank))

            if not llm_scores:
                logger.warning("Could not parse LLM re-ranking response")
                return ranked_results

            # Combine LLM scores with existing scores (70% original, 30% LLM)
            original_weight = 0.7
            llm_weight = 0.3

            for i, result in enumerate(results_to_rerank):
                if i < len(llm_scores):
                    llm_score_normalized = llm_scores[i] / 10.0  # Normalize 0-10 to 0-1
                    combined_score = (
                        original_weight * result['score'] +
                        llm_weight * llm_score_normalized
                    )
                    result['llm_score'] = llm_scores[i]
                    result['original_score'] = result['score']
                    result['score'] = combined_score

            # Re-sort by combined score
            results_to_rerank.sort(key=lambda x: x['score'], reverse=True)

            # Combine re-ranked top with remaining results
            remaining = ranked_results[10:]
            final_results = results_to_rerank + remaining

            logger.info(f"LLM re-ranking complete. Top result score: {final_results[0]['score']:.3f}")

            return final_results

        except Exception as e:
            logger.error(f"LLM re-ranking failed: {e}")
            return ranked_results  # Fallback to original ranking

    def _build_rerank_prompt(
        self,
        question: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for LLM re-ranking.

        Args:
            question: User question
            results: List of results to rank

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a code search relevance evaluator. Rate each code snippet's relevance to the question on a scale of 0-10.

Question: {question}

Code snippets to rate:
"""

        for i, result in enumerate(results):
            # Extract content - handle both string results and RetrievalResult objects
            if isinstance(result.get('result'), str):
                content = result['result']
            elif hasattr(result.get('result'), 'content'):
                content = result['result'].content
            else:
                content = str(result.get('result', ''))

            # Truncate content for prompt
            content_snippet = content[:300] + "..." if len(content) > 300 else content
            prompt += f"\n{i+1}. {content_snippet}\n"

        prompt += """
Output ONLY a JSON array of scores, one for each snippet. Example: [8, 6, 9, 4, 7, 5, 3, 8, 6, 4]
Do not include any other text, just the JSON array."""

        return prompt

    def _parse_rerank_response(
        self,
        response: str,
        expected_count: int
    ) -> Optional[List[float]]:
        """
        Parse LLM re-ranking response.

        Args:
            response: LLM response text
            expected_count: Expected number of scores

        Returns:
            List of scores or None on parse error
        """
        import json

        try:
            # Clean response - extract JSON array
            response = response.strip()

            # Try to find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']')

            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                scores = json.loads(json_str)

                if isinstance(scores, list):
                    # Validate and normalize scores
                    validated_scores = []
                    for score in scores[:expected_count]:
                        try:
                            s = float(score)
                            # Clamp to 0-10
                            s = max(0.0, min(10.0, s))
                            validated_scores.append(s)
                        except (ValueError, TypeError):
                            validated_scores.append(5.0)  # Neutral score on error

                    # Pad with neutral scores if needed
                    while len(validated_scores) < expected_count:
                        validated_scores.append(5.0)

                    return validated_scores

            # Try parsing as comma-separated numbers
            numbers = re.findall(r'(\d+(?:\.\d+)?)', response)
            if len(numbers) >= expected_count:
                return [float(n) for n in numbers[:expected_count]]

            return None

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse re-ranking response: {e}")
            return None

    def set_weights(
        self,
        keyword: float = None,
        tag: float = None,
        name: float = None,
        length: float = None,
        semantic: float = None
    ):
        """
        Update signal weights (must sum to 1.0).

        Args:
            keyword: Keyword matching weight
            tag: Tag coverage weight
            name: Name matching weight
            length: Length/complexity weight
            semantic: Semantic similarity weight
        """
        if keyword is not None:
            self.keyword_weight = keyword
        if tag is not None:
            self.tag_weight = tag
        if name is not None:
            self.name_weight = name
        if length is not None:
            self.length_weight = length
        if semantic is not None:
            self.semantic_weight = semantic

        # Validate sum
        total = self.keyword_weight + self.tag_weight + self.name_weight + self.length_weight + self.semantic_weight
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0 (sum={total:.3f}), normalizing...")
            norm_factor = 1.0 / total
            self.keyword_weight *= norm_factor
            self.tag_weight *= norm_factor
            self.name_weight *= norm_factor
            self.length_weight *= norm_factor
            self.semantic_weight *= norm_factor

        logger.info(f"Updated weights: keyword={self.keyword_weight:.2f}, "
                   f"tag={self.tag_weight:.2f}, name={self.name_weight:.2f}, "
                   f"length={self.length_weight:.2f}, semantic={self.semantic_weight:.2f}")


# ===== PHASE 5 IMPROVEMENT: Result Deduplication =====

def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    Remove duplicate results based on method name and filename.

    Phase 5 Enhancement: Deduplication for cleaner result sets.

    Args:
        results: List of result dicts with 'method_name'/'name' and 'filename' keys

    Returns:
        Deduplicated list preserving order (first occurrence kept)
    """
    seen = set()
    unique = []

    for r in results:
        # Get method name (try multiple keys)
        method_name = r.get('method_name') or r.get('name') or r.get('function_name', '')
        filename = r.get('filename', '')

        # Create deduplication key
        key = (method_name, filename)

        if key not in seen and method_name:  # Skip empty names
            seen.add(key)
            unique.append(r)

    return unique


def rank_by_query_type(
    results: List[Dict],
    query: str,
    enable_semantic: bool = False
) -> List[Dict]:
    """
    Convenience function to rank results with query-type specific weights.

    Phase 5 Enhancement: One-liner for query-type weighted ranking.

    Args:
        results: List of result dicts
        query: User query string
        enable_semantic: Whether to enable semantic similarity

    Returns:
        Ranked and deduplicated results
    """
    ranker = ResultRanker(enable_semantic=enable_semantic)
    ranker.set_weights_for_query_type(query)

    # Convert results to format expected by rank_results
    result_strings = [
        r.get('name', '') + ' ' + r.get('filename', '') + ' ' + str(r.get('code', ''))
        for r in results
    ]

    context = {'enrichment_hints': {}}
    ranked = ranker.rank_results(result_strings, query, context, top_k=len(results))

    # Map back to original results with scores
    for i, r in enumerate(ranked):
        if i < len(results):
            results[i]['ranking_score'] = r['score']

    # Sort by score and deduplicate
    results.sort(key=lambda x: x.get('ranking_score', 0), reverse=True)
    return deduplicate_results(results)
