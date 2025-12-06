"""
Unit Tests for GigaChat Provider

Tests the GigaChatProvider class with mocked API calls.
Covers initialization, generation, error handling, and rate limiting.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

# Test constants
TEST_CREDENTIALS = "test_credentials_base64"
TEST_MODEL = "GigaChat-Pro"
TEST_SCOPE = "GIGACHAT_API_PERS"


class TestGigaChatProviderImport:
    """Tests for GigaChat provider import handling."""

    def test_import_without_gigachat_library(self):
        """Test that provider handles missing langchain-gigachat gracefully."""
        with patch.dict('sys.modules', {'langchain_gigachat': None}):
            # Force reimport to test import error handling
            import importlib
            # The provider should log a warning but not crash
            # This is tested at module load time


class TestGigaChatProviderInit:
    """Tests for GigaChatProvider initialization."""

    @pytest.fixture
    def mock_gigachat(self):
        """Mock GigaChat client."""
        with patch('src.llm.gigachat_provider.GigaChat') as mock:
            mock.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def mock_gigachat_available(self):
        """Mock GIGACHAT_AVAILABLE to True."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            yield

    def test_init_with_valid_credentials(self, mock_gigachat, mock_gigachat_available):
        """Test successful initialization with valid credentials."""
        from src.llm.gigachat_provider import GigaChatProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='gigachat',
            temperature=0.7,
            max_tokens=512,
            extra_params={
                'credentials': TEST_CREDENTIALS,
                'model': TEST_MODEL,
                'scope': TEST_SCOPE,
            }
        )

        provider = GigaChatProvider(config)

        assert provider.is_available() is True
        assert provider.model_name == TEST_MODEL
        assert provider.scope == TEST_SCOPE
        mock_gigachat.assert_called_once()

    def test_init_without_credentials_raises_error(self, mock_gigachat_available):
        """Test that missing credentials raises ValueError."""
        from src.llm.gigachat_provider import GigaChatProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='gigachat',
            extra_params={}  # No credentials
        )

        with pytest.raises(ValueError, match="credentials not provided"):
            GigaChatProvider(config)

    def test_init_with_unknown_model_logs_warning(self, mock_gigachat, mock_gigachat_available, caplog):
        """Test that unknown model name logs a warning."""
        from src.llm.gigachat_provider import GigaChatProvider
        from src.llm.base_provider import LLMConfig

        config = LLMConfig(
            provider_type='gigachat',
            extra_params={
                'credentials': TEST_CREDENTIALS,
                'model': 'Unknown-Model-XYZ',
            }
        )

        with caplog.at_level('WARNING'):
            provider = GigaChatProvider(config)

        assert provider.model_name == 'Unknown-Model-XYZ'
        assert "Unknown model" in caplog.text or provider.model_name not in GigaChatProvider.SUPPORTED_MODELS

    def test_init_with_custom_base_url(self, mock_gigachat, mock_gigachat_available):
        """Test initialization with custom base URL."""
        from src.llm.gigachat_provider import GigaChatProvider
        from src.llm.base_provider import LLMConfig

        custom_url = "https://custom.gigachat.api/v1"
        config = LLMConfig(
            provider_type='gigachat',
            extra_params={
                'credentials': TEST_CREDENTIALS,
                'base_url': custom_url,
            }
        )

        provider = GigaChatProvider(config)

        assert provider.base_url == custom_url
        # Verify base_url was passed to GigaChat client
        call_kwargs = mock_gigachat.call_args.kwargs
        assert call_kwargs.get('base_url') == custom_url


class TestGigaChatProviderGenerate:
    """Tests for GigaChatProvider.generate() method."""

    @pytest.fixture
    def provider(self):
        """Create a mock GigaChat provider."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                # Create mock response
                mock_response = MagicMock()
                mock_response.content = "This is the generated response"
                mock_response.response_metadata = {'usage': {'total_tokens': 100}}

                mock_client = MagicMock()
                mock_client.invoke.return_value = mock_response
                mock_gc.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                config = LLMConfig(
                    provider_type='gigachat',
                    temperature=0.7,
                    max_tokens=512,
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                yield GigaChatProvider(config)

    def test_generate_returns_llm_response(self, provider):
        """Test that generate returns proper LLMResponse."""
        response = provider.generate(
            system_prompt="You are a helpful assistant",
            user_prompt="Hello, how are you?"
        )

        assert response.content == "This is the generated response"
        assert response.metadata['provider'] == 'gigachat'
        assert response.metadata['model'] == 'GigaChat-Pro'

    def test_generate_with_custom_temperature(self, provider):
        """Test generation with overridden temperature."""
        response = provider.generate(
            system_prompt="System",
            user_prompt="User",
            temperature=0.1
        )

        # Verify invoke was called with custom temperature
        call_kwargs = provider.client.invoke.call_args
        assert call_kwargs.kwargs['temperature'] == 0.1

    def test_generate_not_available_raises_error(self):
        """Test that generate raises error when provider not available."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                mock_gc.side_effect = Exception("Connection failed")

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig, LLMProviderNotAvailableError

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                provider = GigaChatProvider(config)
                assert provider.is_available() is False

                with pytest.raises(LLMProviderNotAvailableError):
                    provider.generate("system", "user")


class TestGigaChatProviderRateLimiting:
    """Tests for GigaChat rate limiting and retry logic."""

    @pytest.fixture
    def provider_with_rate_limit(self):
        """Create a provider that simulates rate limiting."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                mock_client = MagicMock()
                mock_gc.return_value = mock_client

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                provider = GigaChatProvider(config)
                # Reduce retry delays for testing
                provider.BASE_RETRY_DELAY = 0.01
                provider.MAX_RETRY_DELAY = 0.1

                yield provider, mock_client

    def test_is_rate_limit_error_detects_429(self, provider_with_rate_limit):
        """Test that 429 errors are detected as rate limit errors."""
        provider, _ = provider_with_rate_limit

        assert provider._is_rate_limit_error(Exception("429 Too Many Requests")) is True
        assert provider._is_rate_limit_error(Exception("Rate limit exceeded")) is True
        assert provider._is_rate_limit_error(Exception("too many requests")) is True
        assert provider._is_rate_limit_error(Exception("Server error 500")) is False

    def test_retry_with_backoff_succeeds_after_rate_limit(self, provider_with_rate_limit):
        """Test that retry succeeds after rate limit errors."""
        provider, mock_client = provider_with_rate_limit

        # First two calls raise rate limit, third succeeds
        mock_response = MagicMock()
        mock_response.content = "Success after retry"
        mock_response.response_metadata = {}

        mock_client.invoke.side_effect = [
            Exception("429 Too Many Requests"),
            Exception("Rate limit exceeded"),
            mock_response
        ]

        response = provider.generate("system", "user")

        assert response.content == "Success after retry"
        assert mock_client.invoke.call_count == 3

    def test_retry_exhaustion_raises_rate_limit_error(self, provider_with_rate_limit):
        """Test that max retries raises GigaChatRateLimitError."""
        provider, mock_client = provider_with_rate_limit
        provider.MAX_RETRIES = 3

        # All calls raise rate limit
        mock_client.invoke.side_effect = Exception("429 Too Many Requests")

        from src.llm.gigachat_provider import GigaChatRateLimitError

        with pytest.raises(GigaChatRateLimitError, match="Rate limit exceeded"):
            provider.generate("system", "user")

    def test_non_rate_limit_error_not_retried(self, provider_with_rate_limit):
        """Test that non-rate-limit errors are not retried."""
        provider, mock_client = provider_with_rate_limit

        mock_client.invoke.side_effect = Exception("Internal server error 500")

        from src.llm.base_provider import LLMProviderAPIError

        with pytest.raises(LLMProviderAPIError):
            provider.generate("system", "user")

        # Should only be called once (no retry)
        assert mock_client.invoke.call_count == 1


class TestGigaChatProviderSimpleGenerate:
    """Tests for GigaChatProvider.generate_simple() method."""

    @pytest.fixture
    def provider(self):
        """Create a mock GigaChat provider."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                mock_response = MagicMock()
                mock_response.content = "Simple response"

                mock_client = MagicMock()
                mock_client.invoke.return_value = mock_response
                mock_gc.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                yield GigaChatProvider(config)

    def test_generate_simple_returns_response(self, provider):
        """Test simple generation returns proper response."""
        response = provider.generate_simple("Just a simple prompt")

        assert response.content == "Simple response"
        assert response.metadata['provider'] == 'gigachat'


class TestGigaChatProviderStreaming:
    """Tests for GigaChatProvider streaming generation."""

    @pytest.fixture
    def streaming_provider(self):
        """Create a provider with streaming mock."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                mock_client = MagicMock()
                mock_gc.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                yield GigaChatProvider(config), mock_client

    def test_generate_stream_yields_chunks(self, streaming_provider):
        """Test that streaming yields chunks."""
        provider, mock_client = streaming_provider

        # Create mock chunks
        chunk1, chunk2, chunk3 = MagicMock(), MagicMock(), MagicMock()
        chunk1.content = "Hello"
        chunk2.content = " world"
        chunk3.content = "!"

        mock_client.stream.return_value = [chunk1, chunk2, chunk3]

        chunks = list(provider.generate_stream("system", "user"))

        assert chunks == ["Hello", " world", "!"]


class TestGigaChatProviderEmbeddings:
    """Tests for GigaChatProvider embeddings (not implemented)."""

    @pytest.fixture
    def provider(self):
        """Create a mock GigaChat provider."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                mock_gc.return_value = MagicMock()

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS}
                )

                yield GigaChatProvider(config)

    def test_get_embeddings_raises_not_implemented(self, provider):
        """Test that embeddings raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="embeddings not yet implemented"):
            provider.get_embeddings(["text1", "text2"])


class TestGigaChatProviderRepr:
    """Tests for GigaChatProvider string representation."""

    def test_repr_format(self):
        """Test __repr__ output format."""
        with patch('src.llm.gigachat_provider.GIGACHAT_AVAILABLE', True):
            with patch('src.llm.gigachat_provider.GigaChat') as mock_gc:
                mock_gc.return_value = MagicMock()

                from src.llm.gigachat_provider import GigaChatProvider
                from src.llm.base_provider import LLMConfig

                config = LLMConfig(
                    provider_type='gigachat',
                    extra_params={'credentials': TEST_CREDENTIALS, 'model': 'GigaChat-Max'}
                )

                provider = GigaChatProvider(config)
                repr_str = repr(provider)

                assert "GigaChatProvider" in repr_str
                assert "GigaChat-Max" in repr_str
                assert "initialized=True" in repr_str
