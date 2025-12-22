"""
Unit Tests for Local LLM Provider

Tests the LocalLLMProvider class with mocked llama-cpp-python.
Covers initialization, generation, streaming, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os


class TestLocalLLMProviderInit:
    """Tests for LocalLLMProvider initialization."""

    @pytest.fixture
    def mock_llama(self):
        """Mock Llama class from llama-cpp-python."""
        with patch('src.llm.local_provider.Llama') as mock:
            mock_model = MagicMock()
            mock.return_value = mock_model
            yield mock, mock_model

    @pytest.fixture
    def temp_model_file(self):
        """Create a temporary file to simulate model file."""
        with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
            f.write(b'dummy model content')
            yield f.name
        os.unlink(f.name)

    def test_init_with_valid_model_path(self, mock_llama, temp_model_file):
        """Test successful initialization with valid model path."""
        mock_llama_class, mock_model = mock_llama

        from src.llm.local_provider import LocalLLMProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='local',
            temperature=0.7,
            max_tokens=512,
            extra_params={
                'model_path': temp_model_file,
                'n_ctx': 4096,
                'n_gpu_layers': 32,
            }
        )

        provider = LocalLLMProvider(config)

        assert provider.is_available() is True
        assert provider.model_path == temp_model_file
        assert provider.n_ctx == 4096
        assert provider.n_gpu_layers == 32
        mock_llama_class.assert_called_once()

    def test_init_with_nonexistent_model_path(self):
        """Test that nonexistent model path results in unavailable provider."""
        from src.llm.local_provider import LocalLLMProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='local',
            extra_params={
                'model_path': '/nonexistent/path/model.gguf',
            }
        )

        provider = LocalLLMProvider(config)

        assert provider.is_available() is False
        assert provider.model is None

    def test_init_with_env_var_model_path(self, mock_llama, temp_model_file):
        """Test initialization using environment variable for model path."""
        mock_llama_class, mock_model = mock_llama

        with patch.dict(os.environ, {'QWEN3_MODEL_PATH': temp_model_file}):
            # Re-import to pick up new env var
            import importlib
            import src.llm.local_provider as local_provider
            importlib.reload(local_provider)

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            config = LLMConfig(
                provider_type='local',
                extra_params={}
            )

            provider = LocalLLMProvider(config)

            assert provider.model_path == temp_model_file

    def test_init_without_any_model_path(self):
        """Test that missing model path results in unavailable provider."""
        with patch.dict(os.environ, {'QWEN3_MODEL_PATH': ''}, clear=True):
            # Re-import to pick up cleared env var
            import importlib
            import src.llm.local_provider as local_provider
            importlib.reload(local_provider)

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            config = LLMConfig(
                provider_type='local',
                extra_params={}
            )

            provider = LocalLLMProvider(config)

            assert provider.is_available() is False

    def test_init_with_model_load_error(self, temp_model_file):
        """Test handling of model loading errors."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_llama.side_effect = RuntimeError("Failed to load model")

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            config = LLMConfig(
                provider_type='local',
                extra_params={'model_path': temp_model_file}
            )

            provider = LocalLLMProvider(config)

            assert provider.is_available() is False
            assert provider.model is None

    def test_init_default_parameters(self, mock_llama, temp_model_file):
        """Test default parameter values."""
        mock_llama_class, _ = mock_llama

        from src.llm.local_provider import LocalLLMProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='local',
            extra_params={'model_path': temp_model_file}
        )

        provider = LocalLLMProvider(config)

        assert provider.n_ctx == 8192  # default
        assert provider.n_gpu_layers == -1  # default (all layers)
        assert provider.n_batch == 512  # default
        assert provider.n_threads == 8  # default
        assert provider.verbose is False  # default


class TestLocalLLMProviderGenerate:
    """Tests for LocalLLMProvider.generate() method."""

    @pytest.fixture
    def provider(self):
        """Create a mock local LLM provider."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_model = MagicMock()
            mock_model.return_value = {
                'choices': [{'text': 'Generated response', 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 50, 'completion_tokens': 20}
            }
            mock_llama.return_value = mock_model

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            config = LLMConfig(
                provider_type='local',
                temperature=0.7,
                max_tokens=512,
                extra_params={'model_path': temp_path}
            )

            provider = LocalLLMProvider(config)
            yield provider

            os.unlink(temp_path)

    def test_generate_returns_llm_response(self, provider):
        """Test that generate returns proper LLMResponse."""
        response = provider.generate(
            system_prompt="You are a helpful assistant",
            user_prompt="Hello, world!"
        )

        assert response.content == "Generated response"
        assert 'model_path' in response.metadata
        assert response.metadata['finish_reason'] == 'stop'

    def test_generate_builds_chatml_prompt(self, provider):
        """Test that ChatML format is used."""
        provider.generate(
            system_prompt="System instructions",
            user_prompt="User question"
        )

        # Verify the model was called with ChatML formatted prompt
        call_args = provider.model.call_args
        prompt = call_args[0][0]

        assert "<|im_start|>system" in prompt
        assert "System instructions" in prompt
        assert "<|im_start|>user" in prompt
        assert "User question" in prompt
        assert "<|im_start|>assistant" in prompt

    def test_generate_with_custom_parameters(self, provider):
        """Test generation with custom parameters."""
        provider.generate(
            system_prompt="System",
            user_prompt="User",
            temperature=0.2,
            max_tokens=100
        )

        call_kwargs = provider.model.call_args.kwargs

        assert call_kwargs['temperature'] == 0.2
        assert call_kwargs['max_tokens'] == 100

    def test_generate_with_grammar(self, provider):
        """Test generation with grammar constraint."""
        mock_grammar = MagicMock()

        provider.generate(
            system_prompt="System",
            user_prompt="User",
            grammar=mock_grammar
        )

        call_kwargs = provider.model.call_args.kwargs

        assert call_kwargs['grammar'] == mock_grammar

    def test_generate_not_available_raises_error(self):
        """Test that generate raises error when model not available."""
        from src.llm.local_provider import LocalLLMProvider
        from src.llm.base_provider import LLMConfig, LLMProviderNotAvailableError

        config = LLMConfig(
            provider_type='local',
            extra_params={'model_path': '/nonexistent/model.gguf'}
        )

        provider = LocalLLMProvider(config)

        with pytest.raises(LLMProviderNotAvailableError):
            provider.generate("system", "user")


class TestLocalLLMProviderSimpleGenerate:
    """Tests for LocalLLMProvider.generate_simple() method."""

    @pytest.fixture
    def provider(self):
        """Create a mock local LLM provider."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_model = MagicMock()
            mock_model.return_value = {
                'choices': [{'text': 'Simple response', 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 20, 'completion_tokens': 10}
            }
            mock_llama.return_value = mock_model

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            config = LLMConfig(
                provider_type='local',
                extra_params={'model_path': temp_path}
            )

            provider = LocalLLMProvider(config)
            yield provider

            os.unlink(temp_path)

    def test_generate_simple_returns_response(self, provider):
        """Test simple generation returns proper response."""
        response = provider.generate_simple("Just a direct prompt")

        assert response.content == "Simple response"

    def test_generate_simple_no_chatml_format(self, provider):
        """Test that simple generation doesn't use ChatML."""
        provider.generate_simple("Direct prompt without formatting")

        call_args = provider.model.call_args
        prompt = call_args[0][0]

        # Should NOT have ChatML markers
        assert "<|im_start|>" not in prompt
        assert prompt == "Direct prompt without formatting"


class TestLocalLLMProviderStreaming:
    """Tests for LocalLLMProvider streaming generation."""

    @pytest.fixture
    def streaming_provider(self):
        """Create a provider with streaming mock."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_model = MagicMock()
            mock_llama.return_value = mock_model

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            config = LLMConfig(
                provider_type='local',
                extra_params={'model_path': temp_path}
            )

            provider = LocalLLMProvider(config)
            yield provider, mock_model

            os.unlink(temp_path)

    def test_generate_stream_yields_chunks(self, streaming_provider):
        """Test that streaming yields chunks."""
        provider, mock_model = streaming_provider

        # Create mock streaming response
        chunks = [
            {'choices': [{'text': 'Hello'}]},
            {'choices': [{'text': ' '}]},
            {'choices': [{'text': 'world'}]},
            {'choices': [{'text': '!'}]},
        ]

        mock_model.return_value = iter(chunks)

        result = list(provider.generate_stream("system", "user"))

        assert result == ['Hello', ' ', 'world', '!']

    def test_generate_stream_filters_empty_chunks(self, streaming_provider):
        """Test that empty chunks are filtered out."""
        provider, mock_model = streaming_provider

        chunks = [
            {'choices': [{'text': 'Hello'}]},
            {'choices': [{'text': ''}]},  # Empty
            {'choices': [{'text': 'world'}]},
        ]

        mock_model.return_value = iter(chunks)

        result = list(provider.generate_stream("system", "user"))

        assert result == ['Hello', 'world']


class TestLocalLLMProviderAvailability:
    """Tests for LocalLLMProvider.is_available() method."""

    def test_is_available_true_when_initialized(self):
        """Test is_available returns True when properly initialized."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_llama.return_value = MagicMock()

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            try:
                config = LLMConfig(
                    provider_type='local',
                    extra_params={'model_path': temp_path}
                )

                provider = LocalLLMProvider(config)

                assert provider.is_available() is True
            finally:
                os.unlink(temp_path)

    def test_is_available_false_when_model_none(self):
        """Test is_available returns False when model is None."""
        from src.llm.local_provider import LocalLLMProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='local',
            extra_params={'model_path': '/nonexistent/model.gguf'}
        )

        provider = LocalLLMProvider(config)

        assert provider.is_available() is False


class TestLocalLLMProviderRepr:
    """Tests for LocalLLMProvider string representation."""

    def test_repr_format(self):
        """Test __repr__ output format."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_llama.return_value = MagicMock()

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            try:
                config = LLMConfig(
                    provider_type='local',
                    extra_params={
                        'model_path': temp_path,
                        'n_ctx': 4096,
                        'n_gpu_layers': 16
                    }
                )

                provider = LocalLLMProvider(config)
                repr_str = repr(provider)

                assert "LocalLLMProvider" in repr_str
                assert "initialized=True" in repr_str
                assert "n_ctx=4096" in repr_str
                assert "n_gpu_layers=16" in repr_str
            finally:
                os.unlink(temp_path)


class TestLocalLLMProviderCleanup:
    """Tests for LocalLLMProvider cleanup."""

    def test_del_cleans_up_model(self):
        """Test that __del__ properly cleans up the model."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_model = MagicMock()
            mock_llama.return_value = mock_model

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            try:
                config = LLMConfig(
                    provider_type='local',
                    extra_params={'model_path': temp_path}
                )

                provider = LocalLLMProvider(config)
                assert provider.model is not None

                # Trigger cleanup
                del provider

                # Model should be deleted (can't directly verify, but no exception = success)
            finally:
                os.unlink(temp_path)


class TestLocalLLMProviderConfigMerge:
    """Tests for configuration merging."""

    @pytest.fixture
    def provider(self):
        """Create a mock local LLM provider."""
        with patch('src.llm.local_provider.Llama') as mock_llama:
            mock_model = MagicMock()
            mock_model.return_value = {
                'choices': [{'text': 'Response', 'finish_reason': 'stop'}],
                'usage': {}
            }
            mock_llama.return_value = mock_model

            from src.llm.local_provider import LocalLLMProvider
            from src.llm.base_provider import LLMConfig

            with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
                f.write(b'dummy')
                temp_path = f.name

            config = LLMConfig(
                provider_type='local',
                temperature=0.5,
                max_tokens=256,
                top_p=0.95,
                extra_params={'model_path': temp_path}
            )

            provider = LocalLLMProvider(config)
            yield provider

            os.unlink(temp_path)

    def test_config_values_used_by_default(self, provider):
        """Test that config values are used when not overridden."""
        provider.generate("system", "user")

        call_kwargs = provider.model.call_args.kwargs

        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['max_tokens'] == 256

    def test_kwargs_override_config(self, provider):
        """Test that kwargs override config values."""
        provider.generate(
            "system", "user",
            temperature=0.9,
            max_tokens=1024
        )

        call_kwargs = provider.model.call_args.kwargs

        assert call_kwargs['temperature'] == 0.9
        assert call_kwargs['max_tokens'] == 1024
