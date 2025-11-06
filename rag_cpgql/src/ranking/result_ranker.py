"""Result Ranker - Rank query results by relevance to question.

This module implements Phase 2 of the Query Funnel approach:
semantic ranking of results to prioritize the most relevant matches.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

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

    def get_breakdown(self) -> Dict[str, float]:
        """Get score breakdown as dictionary."""
        return {
            'total': self.total,
            'keyword_match': self.keyword_match,
            'tag_coverage': self.tag_coverage,
            'name_match': self.name_match,
            'length_bonus': self.length_bonus,
            'semantic_similarity': self.semantic_similarity
        }


class ResultRanker:
    """
    Rank query results by semantic relevance to question.

    Uses multiple relevance signals:
    1. Keyword overlap (question vs result text)
    2. Tag coverage (enrichment tags present)
    3. Name match (method/function name similarity)
    4. Length/complexity bonus (non-trivial results)
    5. Semantic similarity (embedding-based similarity)
    """

    def __init__(self, enable_semantic: bool = True):
        """Initialize Result Ranker.

        Args:
            enable_semantic: Whether to enable semantic similarity scoring (requires sentence-transformers)
        """
        self.enable_semantic = enable_semantic
        self._embedding_model = None

        # Signal weights (must sum to 1.0)
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
