"""
Tests for RAGAS Integration

Tests for RAGAS evaluation with different LLM providers.

Author: Configurable LLM Architecture - Week 2
Date: November 25, 2025

Usage:
    pytest tests/test_ragas_integration.py -v
    pytest tests/test_ragas_integration.py::test_ragas_with_local_llm -v
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator
from src.evaluation.ragas_config import (
    RAGASConfig,
    create_ragas_evaluator,
    get_ragas_evaluator_with_local_llm,
    get_preset_config
)
from src.llm import BaseLLMProvider, LLMConfig, LLMResponse


# Mock LLM Provider for testing
class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Mock generation."""
        return LLMResponse(
            content="Mock response",
            metadata={'model': 'mock'}
        )

    def generate_simple(self, prompt: str, **kwargs) -> LLMResponse:
        """Mock simple generation."""
        return LLMResponse(
            content="Mock simple response",
            metadata={'model': 'mock'}
        )

    def is_available(self) -> bool:
        """Always available."""
        return True


# Test fixtures

@pytest.fixture
def mock_test_results():
    """Mock test results for evaluation."""
    return [
        {
            'question': 'Test question 1',
            'query': 'cpg.method.name("test").l',
            'valid': True,
            'retrieval_stats': {
                'qa_retrieved': 3,
                'cpgql_retrieved': 5,
                'avg_qa_similarity': 0.85,
                'avg_cpgql_similarity': 0.78
            },
            'enrichment_coverage': 0.65,
            'times': {'generation': 1.5, 'retrieval': 0.3},
            'analysis': {'domain': 'test'}
        },
        {
            'question': 'Test question 2',
            'query': 'cpg.method.name("test2").l',
            'valid': True,
            'retrieval_stats': {
                'qa_retrieved': 3,
                'cpgql_retrieved': 5,
                'avg_qa_similarity': 0.72,
                'avg_cpgql_similarity': 0.81
            },
            'enrichment_coverage': 0.82,
            'times': {'generation': 1.2, 'retrieval': 0.4},
            'analysis': {'domain': 'test'}
        }
    ]


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    config = LLMConfig(
        provider_type='mock',
        temperature=0.7,
        max_tokens=512
    )
    return MockLLMProvider(config)


# Tests for RAGASConfig

def test_ragas_config_creation():
    """Test RAGASConfig creation."""
    config = RAGASConfig(
        use_separate_llm=True,
        provider_type='local',
        metrics=['context_precision', 'answer_relevancy']
    )

    assert config.use_separate_llm == True
    assert config.provider_type == 'local'
    assert len(config.metrics) == 2
    assert 'context_precision' in config.metrics


def test_ragas_config_defaults():
    """Test RAGASConfig default values."""
    config = RAGASConfig()

    assert config.use_separate_llm == False
    assert config.provider_type is None
    assert len(config.metrics) == 4  # Default 4 metrics
    assert config.batch_size == 10
    assert config.max_samples is None


def test_preset_configs():
    """Test predefined RAGAS configurations."""
    # Test 'local_fast' preset
    config = get_preset_config('local_fast')
    assert config.use_separate_llm == False
    assert len(config.metrics) == 2
    assert config.batch_size == 20

    # Test 'gigachat_full' preset
    config = get_preset_config('gigachat_full')
    assert config.use_separate_llm == True
    assert config.provider_type == 'gigachat'
    assert len(config.metrics) == 4


def test_invalid_preset():
    """Test that invalid preset raises ValueError."""
    with pytest.raises(ValueError, match="Unknown preset"):
        get_preset_config('invalid_preset_name')


# Tests for RAGASEvaluator

def test_ragas_evaluator_init_with_provider(mock_llm_provider):
    """Test RAGASEvaluator initialization with provider."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.return_value = MagicMock()

        evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)

        assert evaluator.llm is not None
        assert evaluator.llm_available == True
        assert len(evaluator.metrics) == 4


def test_ragas_evaluator_init_without_provider():
    """Test RAGASEvaluator initialization without provider (from config)."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.return_value = MagicMock()

        evaluator = RAGASEvaluator()

        assert evaluator.llm is not None
        mock_get_llm.assert_called_once_with(None)


def test_ragas_evaluator_llm_not_available():
    """Test RAGASEvaluator when LLM is not available."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.side_effect = Exception("LLM not available")

        evaluator = RAGASEvaluator()

        assert evaluator.llm is None
        assert evaluator.llm_available == False


def test_prepare_evaluation_data(mock_llm_provider, mock_test_results):
    """Test dataset preparation for RAGAS."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.return_value = MagicMock()

        evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)
        dataset = evaluator.prepare_evaluation_data(mock_test_results)

        assert len(dataset) == 2
        assert 'question' in dataset.column_names
        assert 'contexts' in dataset.column_names
        assert 'answer' in dataset.column_names
        assert 'ground_truth' in dataset.column_names


def test_evaluate_rag_pipeline_with_ragas(mock_llm_provider, mock_test_results, tmp_path):
    """Test RAGAS evaluation with LLM (mocked)."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        with patch('src.evaluation.ragas_evaluator.evaluate') as mock_ragas_evaluate:
            # Setup mocks
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm

            mock_result = MagicMock()
            mock_result.to_pandas.return_value.to_dict.return_value = [{
                'context_precision': 0.85,
                'context_recall': 0.78,
                'answer_relevancy': 0.82,
                'faithfulness': 0.88
            }]
            mock_ragas_evaluate.return_value = mock_result

            # Create evaluator and run evaluation
            evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)
            output_file = tmp_path / "test_results.json"

            scores = evaluator.evaluate_rag_pipeline(
                mock_test_results,
                output_file=output_file,
                use_ragas=True
            )

            # Check results
            assert 'ragas_metrics' in scores
            assert 'custom_metrics' in scores
            assert scores['ragas_metrics'] is not None
            assert scores['ragas_metrics']['context_precision'] == 0.85

            # Check that evaluate was called
            mock_ragas_evaluate.assert_called_once()

            # Check output file created
            assert output_file.exists()


def test_evaluate_rag_pipeline_without_ragas(mock_llm_provider, mock_test_results):
    """Test evaluation with custom metrics only (no RAGAS)."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.return_value = MagicMock()

        evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)

        scores = evaluator.evaluate_rag_pipeline(
            mock_test_results,
            use_ragas=False  # Disable RAGAS
        )

        # Should only have custom metrics
        assert 'custom_metrics' in scores
        assert scores['ragas_metrics'] is None
        assert scores['custom_metrics']['total_samples'] == 2


def test_evaluate_rag_pipeline_ragas_failure(mock_llm_provider, mock_test_results):
    """Test that RAGAS failure falls back to custom metrics."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        with patch('src.evaluation.ragas_evaluator.evaluate') as mock_ragas_evaluate:
            mock_get_llm.return_value = MagicMock()
            mock_ragas_evaluate.side_effect = Exception("RAGAS failed")

            evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)

            scores = evaluator.evaluate_rag_pipeline(
                mock_test_results,
                use_ragas=True
            )

            # Should have custom metrics and error info
            assert 'custom_metrics' in scores
            assert scores['ragas_metrics'] is None
            assert 'ragas_error' in scores


def test_custom_metrics_computation(mock_llm_provider, mock_test_results):
    """Test custom metrics computation."""
    with patch('src.evaluation.ragas_evaluator.get_ragas_llm') as mock_get_llm:
        mock_get_llm.return_value = MagicMock()

        evaluator = RAGASEvaluator(llm_provider=mock_llm_provider)
        metrics = evaluator._compute_custom_metrics(mock_test_results)

        assert metrics['total_samples'] == 2
        assert 'retrieval_quality' in metrics
        assert 'context_coverage' in metrics
        assert 'generation_quality' in metrics
        assert 'efficiency' in metrics

        # Check specific values
        assert metrics['generation_quality']['validity_rate'] == 1.0  # Both valid
        assert metrics['retrieval_quality']['avg_qa_similarity'] > 0


# Tests for LangChain Adapter

def test_langchain_adapter_creation(mock_llm_provider):
    """Test LangChain adapter creation."""
    from src.llm.langchain_adapter import create_langchain_adapter

    with patch('src.llm.langchain_adapter.LangChainLLMAdapter') as mock_adapter:
        mock_adapter.return_value = MagicMock()

        adapter = create_langchain_adapter(mock_llm_provider)

        # Should create adapter for non-LangChain providers
        mock_adapter.assert_called_once_with(mock_llm_provider)


def test_langchain_adapter_with_gigachat():
    """Test that GigaChatProvider uses .client directly."""
    from src.llm.langchain_adapter import create_langchain_adapter

    # Mock GigaChatProvider
    mock_provider = MagicMock()
    mock_provider.client = MagicMock()  # GigaChat has .client attribute

    adapter = create_langchain_adapter(mock_provider)

    # Should return .client directly, not create adapter
    assert adapter == mock_provider.client


def test_get_ragas_llm():
    """Test get_ragas_llm helper function."""
    from src.llm.langchain_adapter import get_ragas_llm

    with patch('src.llm.langchain_adapter.create_llm_provider') as mock_create:
        with patch('src.llm.langchain_adapter.create_langchain_adapter') as mock_adapter:
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider
            mock_adapter.return_value = MagicMock()

            llm = get_ragas_llm()

            # Should create provider and adapter
            mock_create.assert_called_once()
            mock_adapter.assert_called_once_with(mock_provider)


# Integration tests (optional, can be skipped if no real LLM available)

@pytest.mark.skip(reason="Requires real LLM model")
def test_ragas_with_real_local_llm(mock_test_results):
    """Integration test with real local LLM (skip if not available)."""
    try:
        evaluator = get_ragas_evaluator_with_local_llm()
        scores = evaluator.evaluate_rag_pipeline(mock_test_results, use_ragas=True)
        assert scores['ragas_metrics'] is not None
    except Exception as e:
        pytest.skip(f"Local LLM not available: {e}")


@pytest.mark.skip(reason="Requires GigaChat credentials")
def test_ragas_with_real_gigachat(mock_test_results):
    """Integration test with real GigaChat API (skip if no credentials)."""
    import os
    if not os.getenv('GIGACHAT_CREDENTIALS'):
        pytest.skip("GIGACHAT_CREDENTIALS not set")

    try:
        from src.evaluation.ragas_config import get_ragas_evaluator_with_gigachat
        evaluator = get_ragas_evaluator_with_gigachat()
        scores = evaluator.evaluate_rag_pipeline(mock_test_results, use_ragas=True)
        assert scores['ragas_metrics'] is not None
    except Exception as e:
        pytest.skip(f"GigaChat not available: {e}")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
