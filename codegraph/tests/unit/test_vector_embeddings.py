"""
Unit Tests for Vector Embedding Manager

Tests the vector embedding addition to DuckDB CPG schema.

Author: Phase 1 Implementation
Date: November 25, 2025
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import numpy as np

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)


class TestEmbeddingModel:
    """Test embedding model loading"""

    @patch('sentence_transformers.SentenceTransformer')
    def test_get_embedding_model_loads_model(self, mock_st):
        """Test that embedding model is loaded correctly"""
        from src.cpg_export.add_vector_embeddings import get_embedding_model

        # Reset global state
        import src.cpg_export.add_vector_embeddings as emb_module
        emb_module._embedding_model = None

        # Mock model
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        # Load model
        model = get_embedding_model('all-MiniLM-L6-v2')

        assert model is not None
        assert model == mock_model
        mock_st.assert_called_once_with('all-MiniLM-L6-v2')

        print("\n  OK Embedding model loaded successfully")

    @patch('sentence_transformers.SentenceTransformer')
    def test_get_embedding_model_caches_model(self, mock_st):
        """Test that embedding model is cached after first load"""
        from src.cpg_export.add_vector_embeddings import get_embedding_model
        import src.cpg_export.add_vector_embeddings as emb_module

        # Reset global state
        emb_module._embedding_model = None

        # Mock model
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        # Load model twice
        model1 = get_embedding_model()
        model2 = get_embedding_model()

        # Should be same instance
        assert model1 is model2

        # Should only call SentenceTransformer once
        assert mock_st.call_count == 1

        print("\n  OK Embedding model caching works")


class TestVectorEmbeddingManager:
    """Test VectorEmbeddingManager class"""

    @patch('src.cpg_export.add_vector_embeddings.Path')
    @patch('src.cpg_export.add_vector_embeddings.duckdb.connect')
    @patch('src.cpg_export.add_vector_embeddings.get_embedding_model')
    def test_initialization(self, mock_get_model, mock_connect, mock_path):
        """Test manager initialization"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        # Mock path exists
        mock_path.return_value.exists.return_value = True

        # Mock embedding model
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_get_model.return_value = mock_model

        # Mock connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Initialize manager
        manager = VectorEmbeddingManager(db_path="test.duckdb")
        manager.connect()

        assert manager.db_path == "test.duckdb"
        assert manager.embedding_dim == 384

        print("\n  OK Manager initialized correctly")

    def test_make_method_text(self):
        """Test method text creation for embedding"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        manager = VectorEmbeddingManager()

        text = manager._make_method_text(
            name="getUserData",
            signature="int getUserData(int user_id)",
            code="int getUserData(int user_id) { return db_query(user_id); }",
            full_name="app::getUserData"
        )

        assert "getUserData" in text
        assert "int getUserData(int user_id)" in text
        assert "db_query" in text

        print("\n  OK Method text created correctly")

    def test_make_method_text_truncates_long_code(self):
        """Test that long method code is truncated"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        manager = VectorEmbeddingManager()

        long_code = "x" * 1000  # 1000 characters

        text = manager._make_method_text(
            name="longMethod",
            signature="void longMethod()",
            code=long_code,
            full_name="app::longMethod"
        )

        # Should be truncated to 500 chars + name + signature
        assert len(text) < 600  # Name + signature + 500 char code

        print("\n  OK Long code truncated correctly")

    def test_make_call_text(self):
        """Test call text creation for embedding"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        manager = VectorEmbeddingManager()

        text = manager._make_call_text(
            name="getUserData",
            method_full_name="database::query",
            code="db.query(user_id)",
            signature="int(int)"
        )

        assert "getUserData" in text
        assert "calls database::query" in text
        assert "db.query(user_id)" in text

        print("\n  OK Call text created correctly")

    def test_cosine_similarity_calculation(self):
        """Test cosine similarity computation"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        manager = VectorEmbeddingManager()

        # Test identical vectors (similarity = 1.0)
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        similarity = manager._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.001)

        # Test orthogonal vectors (similarity = 0.0)
        vec3 = np.array([1.0, 0.0, 0.0])
        vec4 = np.array([0.0, 1.0, 0.0])
        similarity = manager._cosine_similarity(vec3, vec4)
        assert similarity == pytest.approx(0.0, abs=0.001)

        # Test opposite vectors (similarity = -1.0)
        vec5 = np.array([1.0, 0.0, 0.0])
        vec6 = np.array([-1.0, 0.0, 0.0])
        similarity = manager._cosine_similarity(vec5, vec6)
        assert similarity == pytest.approx(-1.0, abs=0.001)

        print("\n  OK Cosine similarity computed correctly")

    def test_cosine_similarity_zero_vector(self):
        """Test that zero vectors return 0 similarity"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        manager = VectorEmbeddingManager()

        vec_zero = np.array([0.0, 0.0, 0.0])
        vec_normal = np.array([1.0, 2.0, 3.0])

        similarity = manager._cosine_similarity(vec_zero, vec_normal)
        assert similarity == 0.0

        print("\n  OK Zero vector handling correct")


class TestSchemaModification:
    """Test schema modification operations"""

    @patch('src.cpg_export.add_vector_embeddings.Path')
    @patch('src.cpg_export.add_vector_embeddings.duckdb.connect')
    @patch('src.cpg_export.add_vector_embeddings.get_embedding_model')
    def test_column_exists_check(self, mock_get_model, mock_connect, mock_path):
        """Test checking if embedding columns exist"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_get_model.return_value = mock_model

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Mock column check query
        mock_conn.execute.return_value.fetchall.return_value = [('embedding',)]

        manager = VectorEmbeddingManager()
        manager.connect()

        # Check if column exists
        exists = manager._column_exists('nodes_method', 'embedding')

        assert exists is True

        print("\n  OK Column existence check works")


class TestEmbeddingGeneration:
    """Test embedding generation workflow"""

    @patch('src.cpg_export.add_vector_embeddings.Path')
    @patch('src.cpg_export.add_vector_embeddings.duckdb.connect')
    @patch('src.cpg_export.add_vector_embeddings.get_embedding_model')
    def test_generate_method_embeddings_workflow(self, mock_get_model, mock_connect, mock_path):
        """Test method embedding generation workflow"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        # Setup mocks
        mock_path.return_value.exists.return_value = True

        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
        mock_get_model.return_value = mock_model

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Mock method query results
        mock_methods = [
            (1, 'methodA', 'void methodA()', 'void methodA() {}', 'app::methodA'),
            (2, 'methodB', 'int methodB()', 'int methodB() { return 0; }', 'app::methodB'),
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_methods

        manager = VectorEmbeddingManager()
        manager.connect()

        # Generate embeddings
        count = manager.generate_method_embeddings(batch_size=10, limit=2)

        # Should have embedded 2 methods
        assert count == 2

        # Should have called encode once (batch of 2)
        assert mock_model.encode.call_count >= 1

        print("\n  OK Method embedding generation works")


class TestSimilaritySearch:
    """Test similarity search functionality"""

    @patch('src.cpg_export.add_vector_embeddings.Path')
    @patch('src.cpg_export.add_vector_embeddings.duckdb.connect')
    @patch('src.cpg_export.add_vector_embeddings.get_embedding_model')
    def test_search_similar_methods(self, mock_get_model, mock_connect, mock_path):
        """Test method similarity search"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        # Setup mocks
        mock_path.return_value.exists.return_value = True

        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 3  # Small dim for testing
        # Query embedding
        mock_model.encode.return_value = np.array([1.0, 0.0, 0.0])
        mock_get_model.return_value = mock_model

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Mock search results with embeddings
        mock_results = [
            (1, 'methodA', 'app::methodA', 'void methodA()', 'code A', [1.0, 0.0, 0.0]),  # Perfect match
            (2, 'methodB', 'app::methodB', 'void methodB()', 'code B', [0.0, 1.0, 0.0]),  # Orthogonal
            (3, 'methodC', 'app::methodC', 'void methodC()', 'code C', [0.9, 0.1, 0.0]),  # Close match
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_results

        manager = VectorEmbeddingManager()
        manager.connect()

        # Search
        results = manager.search_similar_methods("test query", top_k=2)

        # Should return top 2 results
        assert len(results) == 2

        # First result should be perfect match (methodA)
        assert results[0]['name'] == 'methodA'
        assert results[0]['similarity'] == pytest.approx(1.0, abs=0.001)

        # Second result should be close match (methodC)
        assert results[1]['name'] == 'methodC'
        assert results[1]['similarity'] > 0.9

        print("\n  OK Method similarity search works")


class TestEmbeddingStats:
    """Test embedding statistics"""

    @patch('src.cpg_export.add_vector_embeddings.Path')
    @patch('src.cpg_export.add_vector_embeddings.duckdb.connect')
    @patch('src.cpg_export.add_vector_embeddings.get_embedding_model')
    def test_get_embedding_stats(self, mock_get_model, mock_connect, mock_path):
        """Test embedding statistics retrieval"""
        from src.cpg_export.add_vector_embeddings import VectorEmbeddingManager

        # Setup mocks
        mock_path.return_value.exists.return_value = True

        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_get_model.return_value = mock_model

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Mock stats queries
        def mock_execute(query):
            result = Mock()
            if 'nodes_method' in query:
                result.fetchone.return_value = (100, 80, 20)  # total, embedded, not_embedded
            elif 'nodes_call' in query:
                result.fetchone.return_value = (200, 150, 50)
            return result

        mock_conn.execute.side_effect = mock_execute

        manager = VectorEmbeddingManager()
        manager.connect()

        # Get stats
        stats = manager.get_embedding_stats()

        # Check method stats
        assert stats['methods']['total'] == 100
        assert stats['methods']['embedded'] == 80
        assert stats['methods']['coverage'] == 80.0

        # Check call stats
        assert stats['calls']['total'] == 200
        assert stats['calls']['embedded'] == 150
        assert stats['calls']['coverage'] == 75.0

        # Check model info
        assert stats['model'] == 'all-MiniLM-L6-v2'
        assert stats['embedding_dim'] == 384

        print("\n  OK Embedding statistics correct")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
