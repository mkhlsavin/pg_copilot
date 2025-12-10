"""
Tests for GigaChat LLM Provider.

Tests for GigaChatProvider initialization, generation, streaming, and embeddings.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.llm.base_provider import (
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
    LLMProviderAPIError,
)


class TestGigaChatProviderInit:
    """Tests for GigaChatProvider initialization."""

    def test_init_success(self):
        """Test successful initialization with credentials."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_client = MagicMock()
                mock_gigachat.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    temperature=0.7,
                    max_tokens=512,
                    extra_params={
                        "credentials": "test_credentials",
                        "model": "GigaChat-Pro",
                    },
                )

                provider = GigaChatProvider(config)

                assert provider.is_available() is True
                assert provider.model_name == "GigaChat-Pro"
                mock_gigachat.assert_called_once()

    def test_init_missing_credentials(self):
        """Test initialization fails without credentials."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            from src.llm.gigachat_provider import GigaChatProvider

            config = LLMConfig(
                provider_type="gigachat",
                extra_params={},
            )

            with pytest.raises(ValueError) as exc_info:
                GigaChatProvider(config)

            assert "credentials" in str(exc_info.value).lower()

    def test_init_library_not_available(self):
        """Test initialization fails when langchain-gigachat not installed."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", False):
            from src.llm.gigachat_provider import GigaChatProvider

            config = LLMConfig(
                provider_type="gigachat",
                extra_params={"credentials": "test"},
            )

            with pytest.raises(ImportError):
                GigaChatProvider(config)

    def test_init_default_model(self):
        """Test default model is GigaChat-Pro."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat"):
                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)

                assert provider.model_name == "GigaChat-Pro"

    def test_init_custom_scope(self):
        """Test custom scope configuration."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={
                        "credentials": "test_credentials",
                        "scope": "GIGACHAT_API_CORP",
                    },
                )

                provider = GigaChatProvider(config)

                assert provider.scope == "GIGACHAT_API_CORP"


class TestGigaChatProviderGenerate:
    """Tests for GigaChatProvider.generate()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked GigaChat provider."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_client = MagicMock()
                mock_gigachat.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    temperature=0.7,
                    max_tokens=512,
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)
                yield provider, mock_client

    def test_generate_success(self, mock_provider):
        """Test successful generation."""
        provider, mock_client = mock_provider

        mock_response = MagicMock()
        mock_response.content = "This is the generated response."
        mock_response.response_metadata = {"usage": {"total_tokens": 100}}
        mock_client.invoke.return_value = mock_response

        response = provider.generate(
            system_prompt="You are a code expert",
            user_prompt="Explain malloc",
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "This is the generated response."
        mock_client.invoke.assert_called_once()

    def test_generate_not_available(self):
        """Test generate when provider not available."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_gigachat.side_effect = Exception("Connection failed")

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)

                with pytest.raises(LLMProviderNotAvailableError):
                    provider.generate(
                        system_prompt="test",
                        user_prompt="test",
                    )

    def test_generate_api_error(self, mock_provider):
        """Test API error handling."""
        provider, mock_client = mock_provider
        mock_client.invoke.side_effect = Exception("API Error")

        with pytest.raises(LLMProviderAPIError):
            provider.generate(
                system_prompt="test",
                user_prompt="test",
            )


class TestGigaChatProviderGenerateSimple:
    """Tests for GigaChatProvider.generate_simple()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked GigaChat provider."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_client = MagicMock()
                mock_gigachat.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)
                yield provider, mock_client

    def test_generate_simple_success(self, mock_provider):
        """Test simple generation."""
        provider, mock_client = mock_provider

        mock_response = MagicMock()
        mock_response.content = "Simple response"
        mock_client.invoke.return_value = mock_response

        response = provider.generate_simple("Test prompt")

        assert response.content == "Simple response"


class TestGigaChatProviderStream:
    """Tests for GigaChatProvider.generate_stream()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked GigaChat provider."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_client = MagicMock()
                mock_gigachat.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)
                yield provider, mock_client

    def test_generate_stream_success(self, mock_provider):
        """Test streaming generation."""
        provider, mock_client = mock_provider

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.content = "Hello"
        chunk2 = MagicMock()
        chunk2.content = " World"
        chunk3 = MagicMock()
        chunk3.content = "!"

        mock_client.stream.return_value = [chunk1, chunk2, chunk3]

        chunks = list(provider.generate_stream(
            system_prompt="test",
            user_prompt="test",
        ))

        assert chunks == ["Hello", " World", "!"]


class TestGigaChatProviderEmbeddings:
    """Tests for GigaChatProvider.get_embeddings()."""

    def test_get_embeddings_success(self):
        """Test successful embeddings generation."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat"):
                with patch("src.llm.gigachat_provider.GigaChatEmbeddings") as mock_embeddings_class:
                    mock_embeddings = MagicMock()
                    mock_embeddings.embed_documents.return_value = [
                        [0.1, 0.2, 0.3],
                        [0.4, 0.5, 0.6],
                    ]
                    mock_embeddings_class.return_value = mock_embeddings

                    from src.llm.gigachat_provider import GigaChatProvider

                    config = LLMConfig(
                        provider_type="gigachat",
                        extra_params={"credentials": "test_credentials"},
                    )

                    provider = GigaChatProvider(config)

                    embeddings = provider.get_embeddings(["text1", "text2"])

                    assert len(embeddings) == 2
                    assert len(embeddings[0]) == 3


class TestGigaChatProviderRateLimiting:
    """Tests for GigaChat rate limiting and retry logic."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked GigaChat provider."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat") as mock_gigachat:
                mock_client = MagicMock()
                mock_gigachat.return_value = mock_client

                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={"credentials": "test_credentials"},
                )

                provider = GigaChatProvider(config)
                yield provider, mock_client

    def test_is_rate_limit_error_detection(self, mock_provider):
        """Test rate limit error detection."""
        provider, _ = mock_provider

        assert provider._is_rate_limit_error(Exception("429 Too Many Requests")) is True
        assert provider._is_rate_limit_error(Exception("rate limit exceeded")) is True
        assert provider._is_rate_limit_error(Exception("too many requests")) is True
        assert provider._is_rate_limit_error(Exception("Connection error")) is False

    def test_retry_on_rate_limit(self, mock_provider):
        """Test retry logic on rate limit errors."""
        provider, mock_client = mock_provider

        # First two calls fail with rate limit, third succeeds
        mock_response = MagicMock()
        mock_response.content = "Success"

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("429 Too Many Requests")
            return mock_response

        mock_client.invoke.side_effect = side_effect

        with patch("time.sleep"):  # Skip actual sleep
            response = provider.generate(
                system_prompt="test",
                user_prompt="test",
            )

        assert response.content == "Success"
        assert call_count[0] == 3


class TestGigaChatProviderRepr:
    """Tests for GigaChatProvider string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        with patch("src.llm.gigachat_provider.GIGACHAT_AVAILABLE", True):
            with patch("src.llm.gigachat_provider.GigaChat"):
                from src.llm.gigachat_provider import GigaChatProvider

                config = LLMConfig(
                    provider_type="gigachat",
                    extra_params={
                        "credentials": "test_credentials",
                        "model": "GigaChat-Max",
                    },
                )

                provider = GigaChatProvider(config)

                repr_str = repr(provider)

                assert "GigaChatProvider" in repr_str
                assert "GigaChat-Max" in repr_str
