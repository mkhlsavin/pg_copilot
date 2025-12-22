"""
Unit Tests for ResultRanker Cross-Source Ranking Extension

Tests the Phase 1 cross-source ranking enhancements:
- Source confidence scoring
- Integration with HybridRetriever results
- Cross-source relevance computation
- LLM re-ranking placeholder

Author: Phase 1 Implementation
Date: November 25, 2025
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.ranking.result_ranker import (
    ResultRanker,
    RelevanceScore
)
from src.retrieval.hybrid_retriever import RetrievalResult


class TestRelevanceScoreExtension:
    """Test extended RelevanceScore with cross-source fields"""

    def test_relevance_score_has_new_fields(self):
        """Test that RelevanceScore has source_confidence and retrieval_score fields"""
        score = RelevanceScore(
            total=0.85,
            keyword_match=0.7,
            tag_coverage=0.6,
            name_match=0.8,
            length_bonus=0.9,
            semantic_similarity=0.75,
            source_confidence=0.95,
            retrieval_score=0.88
        )

        assert score.total == 0.85
        assert score.source_confidence == 0.95
        assert score.retrieval_score == 0.88

        print(f"\n  OK RelevanceScore extended with cross-source fields")

    def test_relevance_score_breakdown_includes_new_fields(self):
        """Test that get_breakdown() includes new fields"""
        score = RelevanceScore(
            total=0.85,
            source_confidence=0.95,
            retrieval_score=0.88
        )

        breakdown = score.get_breakdown()

        assert 'source_confidence' in breakdown
        assert 'retrieval_score' in breakdown
        assert breakdown['source_confidence'] == 0.95
        assert breakdown['retrieval_score'] == 0.88

        print(f"\n  OK Breakdown includes source_confidence and retrieval_score")


class TestSourceConfidence:
    """Test source confidence scoring"""

    @pytest.fixture
    def ranker(self):
        """Create ResultRanker instance"""
        return ResultRanker(enable_semantic=False)

    def test_hybrid_source_highest_confidence(self, ranker):
        """Test that hybrid source has highest confidence"""
        confidence = ranker._compute_source_confidence(
            source="hybrid",
            question="What does this function do?",
            context={}
        )

        assert confidence == 0.95  # Hybrid has highest confidence

        print(f"\n  OK Hybrid source confidence: {confidence}")

    def test_vector_confidence_semantic_query(self, ranker):
        """Test that vector source has high confidence for semantic queries"""
        semantic_question = "What is the purpose of this function?"

        confidence = ranker._compute_source_confidence(
            source="vector",
            question=semantic_question,
            context={}
        )

        assert confidence == 0.85  # High for semantic queries

        print(f"\n  OK Vector confidence for semantic query: {confidence}")

    def test_vector_confidence_structural_query(self, ranker):
        """Test that vector source has lower confidence for structural queries"""
        structural_question = "Find call dependencies between functions"

        confidence = ranker._compute_source_confidence(
            source="vector",
            question=structural_question,
            context={}
        )

        assert confidence == 0.65  # Lower for structural queries

        print(f"\n  OK Vector confidence for structural query: {confidence}")

    def test_graph_confidence_structural_query(self, ranker):
        """Test that graph source has high confidence for structural queries"""
        structural_question = "Show me the call path from main to exit"

        confidence = ranker._compute_source_confidence(
            source="graph",
            question=structural_question,
            context={}
        )

        assert confidence == 0.85  # High for structural queries

        print(f"\n  OK Graph confidence for structural query: {confidence}")

    def test_graph_confidence_semantic_query(self, ranker):
        """Test that graph source has lower confidence for semantic queries"""
        semantic_question = "Explain how this code works"

        confidence = ranker._compute_source_confidence(
            source="graph",
            question=semantic_question,
            context={}
        )

        assert confidence == 0.65  # Lower for semantic queries

        print(f"\n  OK Graph confidence for semantic query: {confidence}")

    def test_unknown_source_neutral_confidence(self, ranker):
        """Test that unknown source gets neutral confidence"""
        confidence = ranker._compute_source_confidence(
            source="unknown_source",
            question="Test question",
            context={}
        )

        assert confidence == 0.5  # Neutral for unknown

        print(f"\n  OK Unknown source confidence: {confidence}")


class TestCrossSourceRanking:
    """Test cross-source ranking with RetrievalResult objects"""

    @pytest.fixture
    def ranker(self):
        """Create ResultRanker instance"""
        return ResultRanker(enable_semantic=False)

    @pytest.fixture
    def sample_results(self):
        """Create sample RetrievalResult objects"""
        return [
            RetrievalResult(
                id="vector_1",
                content="getUserData function retrieves user information from database",
                score=0.85,
                source="vector",
                metadata={"type": "method"},
                node_id=123
            ),
            RetrievalResult(
                id="graph_1",
                content="getUserData called by validateUser, returns user object",
                score=0.75,
                source="graph",
                metadata={"type": "call"},
                node_id=124
            ),
            RetrievalResult(
                id="hybrid_1",
                content="getUserData: core authentication function",
                score=0.90,
                source="hybrid",
                metadata={"type": "method"},
                node_id=125
            ),
        ]

    def test_rank_hybrid_results_accepts_retrieval_results(self, ranker, sample_results):
        """Test that rank_hybrid_results accepts RetrievalResult objects"""
        ranked = ranker.rank_hybrid_results(
            results=sample_results,
            question="What does getUserData do?",
            context={},
            top_k=3
        )

        assert len(ranked) == 3
        assert all('result' in r for r in ranked)
        assert all('score' in r for r in ranked)
        assert all('source' in r for r in ranked)

        print(f"\n  OK rank_hybrid_results accepts RetrievalResult objects")
        print(f"  OK Returned {len(ranked)} ranked results")

    def test_rank_hybrid_results_returns_sorted_by_score(self, ranker, sample_results):
        """Test that results are sorted by score descending"""
        ranked = ranker.rank_hybrid_results(
            results=sample_results,
            question="What does getUserData do?",
            context={},
            top_k=3
        )

        # Check descending order
        scores = [r['score'] for r in ranked]
        assert scores == sorted(scores, reverse=True)

        print(f"\n  OK Results sorted by score descending")
        print(f"  OK Scores: {[f'{s:.3f}' for s in scores]}")

    def test_rank_hybrid_results_includes_source_info(self, ranker, sample_results):
        """Test that ranked results include source information"""
        ranked = ranker.rank_hybrid_results(
            results=sample_results,
            question="What does getUserData do?",
            context={},
            top_k=3
        )

        for result in ranked:
            assert 'source' in result
            assert result['source'] in ['vector', 'graph', 'hybrid']
            assert 'node_id' in result
            assert 'metadata' in result

        print(f"\n  OK Ranked results include source, node_id, metadata")

    def test_rank_hybrid_results_includes_score_breakdown(self, ranker, sample_results):
        """Test that results include detailed score breakdown"""
        ranked = ranker.rank_hybrid_results(
            results=sample_results,
            question="What does getUserData do?",
            context={},
            top_k=3
        )

        for result in ranked:
            assert 'score_breakdown' in result
            breakdown = result['score_breakdown']

            # Check all components
            assert 'total' in breakdown
            assert 'keyword_match' in breakdown
            assert 'source_confidence' in breakdown
            assert 'retrieval_score' in breakdown

        print(f"\n  OK Score breakdown includes all components")

    def test_rank_hybrid_results_top_k_limit(self, ranker, sample_results):
        """Test that top_k parameter limits results"""
        # Add more results
        extended_results = sample_results + [
            RetrievalResult(f"r{i}", f"content {i}", 0.5, "vector")
            for i in range(10)
        ]

        ranked = ranker.rank_hybrid_results(
            results=extended_results,
            question="Test query",
            context={},
            top_k=5
        )

        assert len(ranked) == 5

        print(f"\n  OK top_k=5 returns 5 results from {len(extended_results)} total")

    def test_rank_hybrid_results_empty_list(self, ranker):
        """Test handling of empty results list"""
        ranked = ranker.rank_hybrid_results(
            results=[],
            question="Test query",
            context={},
            top_k=10
        )

        assert ranked == []

        print(f"\n  OK Empty results list handled correctly")


class TestCrossSourceRelevanceComputation:
    """Test cross-source relevance computation logic"""

    @pytest.fixture
    def ranker(self):
        """Create ResultRanker instance"""
        return ResultRanker(enable_semantic=False)

    def test_compute_cross_source_relevance_uses_retrieval_score(self, ranker):
        """Test that cross-source relevance incorporates retrieval score"""
        result = RetrievalResult(
            id="test_1",
            content="Test function content",
            score=0.90,  # High retrieval score
            source="hybrid",
            node_id=100
        )

        relevance = ranker._compute_cross_source_relevance(
            result=result,
            question="What does this function do?",
            context={}
        )

        # Retrieval score should contribute to total
        assert relevance.retrieval_score == 0.90
        assert relevance.total > 0

        print(f"\n  OK Retrieval score incorporated: {relevance.retrieval_score}")
        print(f"  OK Total relevance: {relevance.total:.3f}")

    def test_compute_cross_source_relevance_uses_source_confidence(self, ranker):
        """Test that cross-source relevance incorporates source confidence"""
        hybrid_result = RetrievalResult(
            id="test_1",
            content="Test content",
            score=0.80,
            source="hybrid",  # Should get 0.95 confidence
            node_id=100
        )

        relevance = ranker._compute_cross_source_relevance(
            result=hybrid_result,
            question="Test query",
            context={}
        )

        assert relevance.source_confidence == 0.95  # Hybrid confidence

        print(f"\n  OK Source confidence: {relevance.source_confidence}")

    def test_cross_source_relevance_combines_all_signals(self, ranker):
        """Test that all signals are combined in total score"""
        result = RetrievalResult(
            id="test_1",
            content="getUserData function retrieves user information",
            score=0.85,
            source="vector",
            node_id=100
        )

        relevance = ranker._compute_cross_source_relevance(
            result=result,
            question="What does getUserData function do?",
            context={}
        )

        # Check all components are computed
        assert relevance.retrieval_score > 0
        assert relevance.source_confidence > 0
        assert relevance.keyword_match > 0  # "getUserData" matches
        assert relevance.total > 0

        # Total should be combination
        assert 0 < relevance.total <= 1.0

        print(f"\n  OK All signals combined:")
        print(f"    - Retrieval: {relevance.retrieval_score:.3f}")
        print(f"    - Source: {relevance.source_confidence:.3f}")
        print(f"    - Keywords: {relevance.keyword_match:.3f}")
        print(f"    - Total: {relevance.total:.3f}")


class TestLLMReranking:
    """Test LLM re-ranking placeholder"""

    @pytest.fixture
    def ranker(self):
        """Create ResultRanker with LLM re-ranking enabled"""
        return ResultRanker(enable_semantic=False, enable_llm_rerank=True)

    def test_llm_rerank_enabled_flag(self, ranker):
        """Test that LLM re-ranking can be enabled"""
        assert ranker.enable_llm_rerank is True

        print(f"\n  OK LLM re-ranking enabled: {ranker.enable_llm_rerank}")

    def test_llm_rerank_returns_results(self, ranker):
        """Test that _llm_rerank returns results (placeholder)"""
        sample_ranked = [
            {"result": RetrievalResult("r1", "content1", 0.9, "hybrid"), "score": 0.9},
            {"result": RetrievalResult("r2", "content2", 0.8, "vector"), "score": 0.8},
        ]

        reranked = ranker._llm_rerank(
            ranked_results=sample_ranked,
            question="Test query",
            context={}
        )

        # Should return results (currently same as input - placeholder)
        assert len(reranked) == 2
        assert reranked == sample_ranked  # Placeholder returns original

        print(f"\n  OK LLM re-rank placeholder returns results")


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_rank_results_still_works(self):
        """Test that original rank_results() method still works"""
        ranker = ResultRanker(enable_semantic=False)

        results = [
            "getUserData function implementation",
            "validateUser calls getUserData",
            "User authentication module"
        ]

        ranked = ranker.rank_results(
            results=results,
            question="What does getUserData do?",
            context={},
            top_k=3
        )

        assert len(ranked) == 3
        assert all('result' in r for r in ranked)
        assert all('score' in r for r in ranked)

        print(f"\n  OK Original rank_results() method still works")

    def test_relevance_score_defaults(self):
        """Test that RelevanceScore has sensible defaults for new fields"""
        score = RelevanceScore(total=0.85)

        assert score.source_confidence == 0.0  # Default
        assert score.retrieval_score == 0.0    # Default

        print(f"\n  OK RelevanceScore defaults: source_confidence={score.source_confidence}, retrieval_score={score.retrieval_score}")


class TestRankerWeights:
    """Test that cross-source weights are configured correctly"""

    def test_cross_source_weights_exist(self):
        """Test that new weights are initialized"""
        ranker = ResultRanker()

        assert hasattr(ranker, 'source_confidence_weight')
        assert hasattr(ranker, 'retrieval_score_weight')

        assert ranker.source_confidence_weight == 0.15
        assert ranker.retrieval_score_weight == 0.20

        print(f"\n  OK Cross-source weights initialized:")
        print(f"    - source_confidence_weight: {ranker.source_confidence_weight}")
        print(f"    - retrieval_score_weight: {ranker.retrieval_score_weight}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
