"""
Unit Tests for Hybrid Retriever

Tests the hybrid retrieval engine without requiring full database setup.

Author: Phase 1 Implementation
Date: November 25, 2025
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.retrieval.hybrid_retriever import (
    HybridRetriever,
    HybridRetrievalConfig,
    RetrievalResult,
    hybrid_search_methods,
    semantic_search,
    structural_search
)


class TestRetrievalResult:
    """Test RetrievalResult dataclass"""

    def test_retrieval_result_creation(self):
        """Test creating a retrieval result"""
        result = RetrievalResult(
            id="test_1",
            content="Test content",
            score=0.85,
            source="vector",
            metadata={"key": "value"},
            node_id=123
        )

        assert result.id == "test_1"
        assert result.content == "Test content"
        assert result.score == 0.85
        assert result.source == "vector"
        assert result.metadata["key"] == "value"
        assert result.node_id == 123

    def test_retrieval_result_equality(self):
        """Test result equality based on ID"""
        result1 = RetrievalResult("id1", "content1", 0.9, "vector")
        result2 = RetrievalResult("id1", "different", 0.5, "graph")
        result3 = RetrievalResult("id2", "content1", 0.9, "vector")

        assert result1 == result2  # Same ID
        assert result1 != result3  # Different ID

    def test_retrieval_result_hash(self):
        """Test result hashing for set operations"""
        result1 = RetrievalResult("id1", "content", 0.9, "vector")
        result2 = RetrievalResult("id1", "content", 0.9, "vector")

        results_set = {result1, result2}
        assert len(results_set) == 1  # Deduplication works


class TestHybridRetrievalConfig:
    """Test configuration object"""

    def test_default_config(self):
        """Test default configuration"""
        config = HybridRetrievalConfig()

        assert config.vector_weight == 0.6
        assert config.graph_weight == 0.4
        assert config.vector_top_k == 20
        assert config.graph_top_k == 20
        assert config.final_top_k == 10

    def test_custom_config(self):
        """Test custom configuration"""
        config = HybridRetrievalConfig(
            vector_weight=0.7,
            graph_weight=0.3,
            final_top_k=5
        )

        assert config.vector_weight == 0.7
        assert config.graph_weight == 0.3
        assert config.final_top_k == 5

    def test_config_validation(self):
        """Test that weights must sum to 1.0"""
        with pytest.raises(ValueError):
            HybridRetrievalConfig(vector_weight=0.7, graph_weight=0.5)


class TestHybridRetriever:
    """Test hybrid retriever main class"""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        vector_store = Mock()
        vector_store.qa_collection = Mock()
        vector_store.cpgql_collection = Mock()
        vector_store.encoder = Mock()
        return vector_store

    @pytest.fixture
    def mock_cpg_service(self):
        """Mock CPG service"""
        cpg_service = Mock()
        return cpg_service

    @pytest.fixture
    def retriever(self, mock_vector_store, mock_cpg_service):
        """Create hybrid retriever with mocks"""
        return HybridRetriever(mock_vector_store, mock_cpg_service)

    def test_initialization(self, retriever):
        """Test retriever initialization"""
        assert retriever.vector_store is not None
        assert retriever.cpg_service is not None
        assert retriever.config is not None
        assert retriever.config.vector_weight == 0.6

    def test_adapt_config_semantic(self, retriever):
        """Test config adaptation for semantic queries"""
        adapted = retriever._adapt_config("semantic")

        assert adapted.vector_weight == 0.75
        assert adapted.graph_weight == 0.25

    def test_adapt_config_structural(self, retriever):
        """Test config adaptation for structural queries"""
        adapted = retriever._adapt_config("structural")

        assert adapted.vector_weight == 0.25
        assert adapted.graph_weight == 0.75

    def test_adapt_config_security(self, retriever):
        """Test config adaptation for security queries"""
        adapted = retriever._adapt_config("security")

        assert adapted.vector_weight == 0.5
        assert adapted.graph_weight == 0.5

    def test_adapt_config_none(self, retriever):
        """Test config adaptation with no type"""
        adapted = retriever._adapt_config(None)

        assert adapted.vector_weight == 0.6  # Default
        assert adapted.graph_weight == 0.4

    def test_merge_results_rrf_vector_only(self, retriever):
        """Test RRF merging with vector results only"""
        vector_results = [
            RetrievalResult("v1", "content1", 0.9, "vector"),
            RetrievalResult("v2", "content2", 0.8, "vector"),
        ]
        graph_results = []

        config = HybridRetrievalConfig()
        merged = retriever._merge_results_rrf(vector_results, graph_results, config)

        assert len(merged) == 2
        assert merged[0].id == "v1"  # Higher rank
        assert merged[0].source == "vector"

    def test_merge_results_rrf_graph_only(self, retriever):
        """Test RRF merging with graph results only"""
        vector_results = []
        graph_results = [
            RetrievalResult("g1", "content1", 0.9, "graph"),
            RetrievalResult("g2", "content2", 0.8, "graph"),
        ]

        config = HybridRetrievalConfig()
        merged = retriever._merge_results_rrf(vector_results, graph_results, config)

        assert len(merged) == 2
        assert merged[0].id == "g1"  # Higher rank
        assert merged[0].source == "graph"

    def test_merge_results_rrf_both(self, retriever):
        """Test RRF merging with both vector and graph results"""
        vector_results = [
            RetrievalResult("v1", "content1", 0.9, "vector"),
            RetrievalResult("shared", "shared_content", 0.8, "vector"),
        ]
        graph_results = [
            RetrievalResult("shared", "shared_content", 0.85, "graph"),
            RetrievalResult("g1", "content2", 0.7, "graph"),
        ]

        config = HybridRetrievalConfig()
        merged = retriever._merge_results_rrf(vector_results, graph_results, config)

        # Should have 3 unique results
        assert len(merged) == 3

        # "shared" should have highest RRF score (found in both)
        assert merged[0].id == "shared"
        assert merged[0].source == "hybrid"

    def test_merge_results_rrf_scoring(self, retriever):
        """Test that RRF scoring is correct"""
        vector_results = [
            RetrievalResult("v1", "content1", 1.0, "vector"),
        ]
        graph_results = [
            RetrievalResult("v1", "content1", 1.0, "graph"),
        ]

        config = HybridRetrievalConfig(vector_weight=0.6, graph_weight=0.4)
        merged = retriever._merge_results_rrf(vector_results, graph_results, config)

        k = 60
        expected_score = (0.6 / (k + 1)) + (0.4 / (k + 1))  # Both rank 1

        assert len(merged) == 1
        assert merged[0].score == pytest.approx(expected_score, rel=1e-5)


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        return Mock()

    @pytest.fixture
    def mock_cpg_service(self):
        """Mock CPG service"""
        return Mock()

    @pytest.mark.asyncio
    async def test_hybrid_search_methods(self, mock_vector_store, mock_cpg_service):
        """Test hybrid_search_methods function"""
        with patch.object(HybridRetriever, 'retrieve') as mock_retrieve:
            mock_retrieve.return_value = [
                RetrievalResult("r1", "content", 0.9, "hybrid")
            ]

            results = await hybrid_search_methods(
                "test query",
                mock_vector_store,
                mock_cpg_service,
                top_k=5
            )

            assert len(results) == 1
            assert results[0].id == "r1"
            mock_retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search(self, mock_vector_store, mock_cpg_service):
        """Test semantic_search function"""
        with patch.object(HybridRetriever, 'retrieve') as mock_retrieve:
            mock_retrieve.return_value = [
                RetrievalResult("r1", "content", 0.9, "vector")
            ]

            results = await semantic_search(
                "test query",
                mock_vector_store,
                mock_cpg_service
            )

            assert len(results) == 1
            # Check that query_type was passed correctly
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get('query_type') == "semantic"

    @pytest.mark.asyncio
    async def test_structural_search(self, mock_vector_store, mock_cpg_service):
        """Test structural_search function"""
        with patch.object(HybridRetriever, 'retrieve') as mock_retrieve:
            mock_retrieve.return_value = [
                RetrievalResult("r1", "content", 0.9, "graph")
            ]

            results = await structural_search(
                "test query",
                mock_vector_store,
                mock_cpg_service
            )

            assert len(results) == 1
            # Check that query_type was passed correctly
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get('query_type') == "structural"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
