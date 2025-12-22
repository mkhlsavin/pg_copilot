"""
Unit tests for LLM Re-ranking in ResultRanker

Tests:
- Prompt building
- Response parsing
- LLM re-ranking logic
- Fallback behavior
- Score combination

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ranking.result_ranker import ResultRanker, RelevanceScore


class TestLLMRerankingPromptBuilding:
    """Test prompt building for LLM re-ranking."""

    def test_build_rerank_prompt_basic(self):
        """Test basic prompt building."""
        ranker = ResultRanker(enable_llm_rerank=True)

        results = [
            {'result': 'def exec_simple_query(): pass', 'score': 0.8},
            {'result': 'def parse_query(): pass', 'score': 0.7},
        ]

        prompt = ranker._build_rerank_prompt(
            question="How does query execution work?",
            results=results
        )

        assert "How does query execution work?" in prompt
        assert "exec_simple_query" in prompt
        assert "parse_query" in prompt
        assert "[8, 6, 9, 4, 7, 5, 3, 8, 6, 4]" in prompt  # Example format

    def test_build_rerank_prompt_truncation(self):
        """Test content truncation in prompt."""
        ranker = ResultRanker(enable_llm_rerank=True)

        # Long content
        long_content = "x" * 500

        results = [
            {'result': long_content, 'score': 0.8},
        ]

        prompt = ranker._build_rerank_prompt(
            question="Test?",
            results=results
        )

        # Should truncate to ~300 chars
        assert len(prompt) < len(long_content) + 500


class TestLLMRerankingResponseParsing:
    """Test parsing LLM re-ranking responses."""

    def test_parse_valid_json_array(self):
        """Test parsing valid JSON array response."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "[8, 6, 9, 4, 7]"
        scores = ranker._parse_rerank_response(response, expected_count=5)

        assert scores == [8.0, 6.0, 9.0, 4.0, 7.0]

    def test_parse_json_array_with_decimals(self):
        """Test parsing JSON with decimal scores."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "[8.5, 6.2, 9.0]"
        scores = ranker._parse_rerank_response(response, expected_count=3)

        assert scores[0] == 8.5
        assert scores[1] == 6.2

    def test_parse_json_with_extra_text(self):
        """Test parsing JSON array with surrounding text."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "Here are my scores: [8, 6, 9] based on relevance."
        scores = ranker._parse_rerank_response(response, expected_count=3)

        assert scores == [8.0, 6.0, 9.0]

    def test_parse_clamps_scores(self):
        """Test that scores are clamped to 0-10."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "[-5, 15, 10, 0]"
        scores = ranker._parse_rerank_response(response, expected_count=4)

        assert scores[0] == 0.0  # Clamped from -5
        assert scores[1] == 10.0  # Clamped from 15
        assert scores[2] == 10.0
        assert scores[3] == 0.0

    def test_parse_pads_missing_scores(self):
        """Test padding when fewer scores than expected."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "[8, 6]"
        scores = ranker._parse_rerank_response(response, expected_count=5)

        assert len(scores) == 5
        assert scores[0] == 8.0
        assert scores[1] == 6.0
        assert scores[2] == 5.0  # Padded neutral
        assert scores[3] == 5.0
        assert scores[4] == 5.0

    def test_parse_comma_separated_numbers(self):
        """Test fallback parsing of comma-separated numbers."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "Scores: 8, 6, 9, 4, 7"
        scores = ranker._parse_rerank_response(response, expected_count=5)

        assert scores == [8.0, 6.0, 9.0, 4.0, 7.0]

    def test_parse_invalid_response(self):
        """Test handling invalid response."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = "I cannot provide scores."
        scores = ranker._parse_rerank_response(response, expected_count=5)

        assert scores is None

    def test_parse_empty_response(self):
        """Test handling empty response."""
        ranker = ResultRanker(enable_llm_rerank=True)

        response = ""
        scores = ranker._parse_rerank_response(response, expected_count=5)

        assert scores is None


class TestLLMRerankingLogic:
    """Test LLM re-ranking logic."""

    def test_rerank_disabled(self):
        """Test that re-ranking is skipped when disabled."""
        ranker = ResultRanker(enable_llm_rerank=False)

        results = [
            {'result': 'test1', 'score': 0.8},
            {'result': 'test2', 'score': 0.6},
        ]

        reranked = ranker._llm_rerank(results, "question", {})

        # Should return original results unchanged
        assert reranked == results

    def test_rerank_single_result(self):
        """Test that single result is not re-ranked."""
        ranker = ResultRanker(enable_llm_rerank=True)

        results = [{'result': 'test1', 'score': 0.8}]

        reranked = ranker._llm_rerank(results, "question", {})

        assert reranked == results

    def test_rerank_with_mock_llm(self):
        """Test re-ranking with mocked LLM."""
        ranker = ResultRanker(enable_llm_rerank=True)

        # Create mock LLM client directly on the instance
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.generate_simple.return_value = "[6, 9]"  # Second result gets higher score
        ranker._llm_client = mock_client

        results = [
            {'result': 'first result', 'score': 0.8},
            {'result': 'second result', 'score': 0.6},
        ]

        # Make copies to avoid modifying originals
        results_copy = [dict(r) for r in results]
        reranked = ranker._llm_rerank(results_copy, "test question", {})

        # LLM scored second result higher (9 vs 6)
        # Combined: first = 0.7*0.8 + 0.3*0.6 = 0.74
        # Combined: second = 0.7*0.6 + 0.3*0.9 = 0.69
        # So first should still be first, but scores should be updated
        assert 'llm_score' in reranked[0]

    def test_rerank_fallback_on_error(self):
        """Test fallback to original ranking on error."""
        ranker = ResultRanker(enable_llm_rerank=True)
        ranker._llm_client = Mock()
        ranker._llm_client.is_available.return_value = True
        ranker._llm_client.generate_simple.side_effect = Exception("API error")

        results = [
            {'result': 'test1', 'score': 0.8},
            {'result': 'test2', 'score': 0.6},
        ]

        reranked = ranker._llm_rerank(results.copy(), "question", {})

        # Should return original results
        assert reranked[0]['score'] == 0.8


class TestLLMRerankingIntegration:
    """Test LLM re-ranking integration with rank_hybrid_results."""

    def test_hybrid_results_with_llm_rerank_disabled(self):
        """Test hybrid ranking without LLM re-ranking."""
        ranker = ResultRanker(enable_llm_rerank=False)

        # Skip if RetrievalResult not available
        try:
            from src.retrieval.hybrid_retriever import RetrievalResult
        except ImportError:
            pytest.skip("hybrid_retriever not available")

        # Create mock results - check RetrievalResult signature
        try:
            # Try with 'id' parameter (newer version)
            results = [
                RetrievalResult(
                    id="1",
                    content="def exec_simple_query(): pass",
                    score=0.8,
                    source="vector",
                    node_id="1",
                    metadata={}
                ),
            ]
        except TypeError:
            # Fallback without 'id' parameter (older version)
            results = [
                RetrievalResult(
                    content="def exec_simple_query(): pass",
                    score=0.8,
                    source="vector",
                    node_id="1",
                    metadata={}
                ),
            ]

        ranked = ranker.rank_hybrid_results(
            results=results,
            question="How does execution work?",
            context={},
            top_k=5,
            enable_llm_rerank=False
        )

        assert len(ranked) == 1
        assert 'llm_score' not in ranked[0]


class TestRelevanceScoreDataclass:
    """Test RelevanceScore dataclass."""

    def test_relevance_score_creation(self):
        """Test creating relevance score."""
        score = RelevanceScore(
            total=0.8,
            keyword_match=0.7,
            tag_coverage=0.6,
            name_match=0.9,
            length_bonus=0.5,
            semantic_similarity=0.85,
            source_confidence=0.9,
            retrieval_score=0.75
        )

        assert score.total == 0.8
        assert score.semantic_similarity == 0.85

    def test_relevance_score_breakdown(self):
        """Test getting score breakdown."""
        score = RelevanceScore(
            total=0.8,
            keyword_match=0.7,
            tag_coverage=0.6,
            name_match=0.9,
            length_bonus=0.5,
            semantic_similarity=0.85
        )

        breakdown = score.get_breakdown()

        assert breakdown['total'] == 0.8
        assert breakdown['keyword_match'] == 0.7
        assert breakdown['semantic_similarity'] == 0.85


class TestResultRankerBasic:
    """Test basic ResultRanker functionality."""

    def test_initialization_with_semantic(self):
        """Test initialization with semantic similarity enabled."""
        ranker = ResultRanker(enable_semantic=True)

        assert ranker.enable_semantic is True
        assert ranker.semantic_weight == 0.30

    def test_initialization_without_semantic(self):
        """Test initialization without semantic similarity."""
        ranker = ResultRanker(enable_semantic=False)

        assert ranker.enable_semantic is False
        assert ranker.semantic_weight == 0.0

    def test_initialization_with_llm_rerank(self):
        """Test initialization with LLM re-ranking enabled."""
        ranker = ResultRanker(enable_llm_rerank=True)

        assert ranker.enable_llm_rerank is True

    def test_rank_empty_results(self):
        """Test ranking empty results list."""
        ranker = ResultRanker()

        ranked = ranker.rank_results([], "test question", {})

        assert ranked == []

    def test_set_weights(self):
        """Test setting custom weights."""
        ranker = ResultRanker()

        ranker.set_weights(
            keyword=0.3,
            tag=0.3,
            name=0.2,
            length=0.1,
            semantic=0.1
        )

        assert ranker.keyword_weight == 0.3
        assert ranker.tag_weight == 0.3

    def test_set_weights_normalizes(self):
        """Test that set_weights normalizes weights."""
        ranker = ResultRanker()

        ranker.set_weights(
            keyword=0.5,
            tag=0.5,
            name=0.5,
            length=0.5,
            semantic=0.5
        )

        # Should normalize to sum to 1.0
        total = (ranker.keyword_weight + ranker.tag_weight +
                 ranker.name_weight + ranker.length_weight +
                 ranker.semantic_weight)

        assert abs(total - 1.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
