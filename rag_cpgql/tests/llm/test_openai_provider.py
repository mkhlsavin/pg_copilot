"""
Tests for OpenAI LLM Provider.

Tests for OpenAIProvider initialization, generation, streaming, embeddings,
and Azure OpenAI support.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.llm.base_provider import (
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
    LLMProviderAPIError,
)


class TestOpenAIProviderInit:
    """Tests for OpenAIProvider initialization."""

    def test_init_success(self):
        """Test successful initialization with API key."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    temperature=0.7,
                    max_tokens=512,
                    extra_params={
                        "api_key": "sk-test-key",
                        "model": "gpt-4o-mini",
                    },
                )

                provider = OpenAIProvider(config)

                assert provider.is_available() is True
                assert provider.model_name == "gpt-4o-mini"
                assert provider.is_azure is False
                mock_openai.assert_called_once()

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            from src.llm.openai_provider import OpenAIProvider

            config = LLMConfig(
                provider_type="openai",
                extra_params={},
            )

            with pytest.raises(ValueError) as exc_info:
                OpenAIProvider(config)

            assert "api key" in str(exc_info.value).lower()

    def test_init_library_not_available(self):
        """Test initialization fails when openai not installed."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", False):
            from src.llm.openai_provider import OpenAIProvider

            config = LLMConfig(
                provider_type="openai",
                extra_params={"api_key": "test"},
            )

            with pytest.raises(ImportError):
                OpenAIProvider(config)

    def test_init_default_model(self):
        """Test default model is gpt-4o-mini."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI"):
                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test-key"},
                )

                provider = OpenAIProvider(config)

                assert provider.model_name == "gpt-4o-mini"

    def test_init_with_custom_base_url(self):
        """Test custom base URL for compatible APIs."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "test_key",
                        "base_url": "http://localhost:8000/v1",
                    },
                )

                provider = OpenAIProvider(config)

                # Verify base_url was passed
                call_kwargs = mock_openai.call_args.kwargs
                assert call_kwargs.get("base_url") == "http://localhost:8000/v1"

    def test_init_with_organization(self):
        """Test initialization with organization ID."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "test_key",
                        "organization": "org-123456",
                    },
                )

                provider = OpenAIProvider(config)

                call_kwargs = mock_openai.call_args.kwargs
                assert call_kwargs.get("organization") == "org-123456"


class TestOpenAIProviderAzure:
    """Tests for Azure OpenAI support."""

    def test_init_azure_success(self):
        """Test Azure OpenAI initialization."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.AzureOpenAI") as mock_azure:
                mock_client = MagicMock()
                mock_azure.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "azure-key",
                        "azure_endpoint": "https://myresource.openai.azure.com",
                        "azure_deployment": "gpt-4",
                        "api_version": "2024-02-01",
                    },
                )

                provider = OpenAIProvider(config)

                assert provider.is_azure is True
                assert provider.azure_endpoint == "https://myresource.openai.azure.com"
                assert provider.azure_deployment == "gpt-4"
                mock_azure.assert_called_once()

    def test_azure_uses_deployment_name(self):
        """Test that Azure uses deployment name for API calls."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.AzureOpenAI") as mock_azure:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(content="Response"),
                        finish_reason="stop"
                    )
                ]
                mock_response.model = "gpt-4"
                mock_response.usage = MagicMock(
                    total_tokens=100,
                    prompt_tokens=50,
                    completion_tokens=50
                )
                mock_client.chat.completions.create.return_value = mock_response
                mock_azure.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "azure-key",
                        "azure_endpoint": "https://test.openai.azure.com",
                        "azure_deployment": "my-gpt4-deployment",
                    },
                )

                provider = OpenAIProvider(config)
                provider.generate("system", "user")

                # Verify deployment name was used
                call_kwargs = mock_client.chat.completions.create.call_args.kwargs
                assert call_kwargs["model"] == "my-gpt4-deployment"


class TestOpenAIProviderGenerate:
    """Tests for OpenAIProvider.generate()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked OpenAI provider."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    temperature=0.7,
                    max_tokens=512,
                    extra_params={"api_key": "sk-test-key"},
                )

                provider = OpenAIProvider(config)
                yield provider, mock_client

    def test_generate_success(self, mock_provider):
        """Test successful generation."""
        provider, mock_client = mock_provider

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Generated response"),
                finish_reason="stop"
            )
        ]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock(
            total_tokens=150,
            prompt_tokens=100,
            completion_tokens=50
        )
        mock_client.chat.completions.create.return_value = mock_response

        response = provider.generate(
            system_prompt="You are a code expert",
            user_prompt="Explain malloc",
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "Generated response"
        assert response.tokens_used == 150
        mock_client.chat.completions.create.assert_called_once()

    def test_generate_with_custom_params(self, mock_provider):
        """Test generation with custom parameters."""
        provider, mock_client = mock_provider

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Response"),
                finish_reason="stop"
            )
        ]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock(
            total_tokens=100, prompt_tokens=50, completion_tokens=50
        )
        mock_client.chat.completions.create.return_value = mock_response

        provider.generate(
            system_prompt="test",
            user_prompt="test",
            temperature=0.2,
            max_tokens=1000,
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 1000

    def test_generate_not_available(self):
        """Test generate when provider not available."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_openai.side_effect = Exception("Connection failed")

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test"},
                )

                with pytest.raises(LLMProviderNotAvailableError):
                    OpenAIProvider(config)

    def test_generate_api_error(self, mock_provider):
        """Test API error handling."""
        provider, mock_client = mock_provider
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(LLMProviderAPIError):
            provider.generate(
                system_prompt="test",
                user_prompt="test",
            )


class TestOpenAIProviderRateLimiting:
    """Tests for rate limit and auth error handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked OpenAI provider."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test-key"},
                )

                provider = OpenAIProvider(config)
                yield provider, mock_client

    def test_rate_limit_error(self, mock_provider):
        """Test rate limit error handling."""
        provider, mock_client = mock_provider

        with patch("src.llm.openai_provider.openai") as mock_openai_module:
            # Create a mock RateLimitError
            rate_limit_error = Exception("Rate limit exceeded")
            rate_limit_error.__class__.__name__ = "RateLimitError"
            mock_openai_module.RateLimitError = type(
                "RateLimitError", (Exception,), {}
            )

            mock_client.chat.completions.create.side_effect = (
                mock_openai_module.RateLimitError("Rate limit exceeded")
            )

            from src.llm.openai_provider import OpenAIRateLimitError

            with pytest.raises(OpenAIRateLimitError):
                provider.generate(
                    system_prompt="test",
                    user_prompt="test",
                )

    def test_auth_error(self, mock_provider):
        """Test authentication error handling."""
        provider, mock_client = mock_provider

        with patch("src.llm.openai_provider.openai") as mock_openai_module:
            mock_openai_module.AuthenticationError = type(
                "AuthenticationError", (Exception,), {}
            )

            mock_client.chat.completions.create.side_effect = (
                mock_openai_module.AuthenticationError("Invalid API key")
            )

            from src.llm.openai_provider import OpenAIAuthError

            with pytest.raises(OpenAIAuthError):
                provider.generate(
                    system_prompt="test",
                    user_prompt="test",
                )


class TestOpenAIProviderStream:
    """Tests for OpenAIProvider.generate_stream()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked OpenAI provider."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test-key"},
                )

                provider = OpenAIProvider(config)
                yield provider, mock_client

    def test_generate_stream_success(self, mock_provider):
        """Test streaming generation."""
        provider, mock_client = mock_provider

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=" World"))]
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock(delta=MagicMock(content="!"))]

        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]

        chunks = list(provider.generate_stream(
            system_prompt="test",
            user_prompt="test",
        ))

        assert chunks == ["Hello", " World", "!"]

    def test_generate_stream_empty_chunks(self, mock_provider):
        """Test streaming with empty chunks."""
        provider, mock_client = mock_provider

        # Create chunks with some empty content
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=None))]  # Empty
        chunk3 = MagicMock()
        chunk3.choices = []  # No choices

        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]

        chunks = list(provider.generate_stream(
            system_prompt="test",
            user_prompt="test",
        ))

        # Should only get non-empty chunks
        assert chunks == ["Hello"]

    def test_generate_stream_error(self, mock_provider):
        """Test streaming error handling."""
        provider, mock_client = mock_provider
        mock_client.chat.completions.create.side_effect = Exception("Stream error")

        with pytest.raises(LLMProviderAPIError):
            list(provider.generate_stream(
                system_prompt="test",
                user_prompt="test",
            ))


class TestOpenAIProviderEmbeddings:
    """Tests for OpenAIProvider.get_embeddings()."""

    def test_get_embeddings_success(self):
        """Test successful embeddings generation."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()

                # Create mock embedding response
                mock_embedding1 = MagicMock()
                mock_embedding1.embedding = [0.1, 0.2, 0.3]
                mock_embedding2 = MagicMock()
                mock_embedding2.embedding = [0.4, 0.5, 0.6]

                mock_response = MagicMock()
                mock_response.data = [mock_embedding1, mock_embedding2]
                mock_client.embeddings.create.return_value = mock_response

                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "sk-test",
                        "embedding_model": "text-embedding-3-small",
                    },
                )

                provider = OpenAIProvider(config)

                embeddings = provider.get_embeddings(["text1", "text2"])

                assert len(embeddings) == 2
                assert len(embeddings[0]) == 3
                assert embeddings[0] == [0.1, 0.2, 0.3]
                assert embeddings[1] == [0.4, 0.5, 0.6]

    def test_get_embeddings_default_model(self):
        """Test default embedding model is text-embedding-3-small."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test"},
                )

                provider = OpenAIProvider(config)

                assert provider.embedding_model == "text-embedding-3-small"

    def test_get_embeddings_error(self):
        """Test embeddings error handling."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.embeddings.create.side_effect = Exception("Embeddings error")
                mock_openai.return_value = mock_client

                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={"api_key": "sk-test"},
                )

                provider = OpenAIProvider(config)

                with pytest.raises(LLMProviderAPIError):
                    provider.get_embeddings(["text"])


class TestOpenAIProviderRepr:
    """Tests for OpenAIProvider string representation."""

    def test_repr_openai(self):
        """Test __repr__ for OpenAI."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI"):
                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "sk-test",
                        "model": "gpt-4o",
                    },
                )

                provider = OpenAIProvider(config)

                repr_str = repr(provider)

                assert "OpenAIProvider" in repr_str
                assert "gpt-4o" in repr_str
                assert "azure=False" in repr_str

    def test_repr_azure(self):
        """Test __repr__ for Azure OpenAI."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.AzureOpenAI"):
                from src.llm.openai_provider import OpenAIProvider

                config = LLMConfig(
                    provider_type="openai",
                    extra_params={
                        "api_key": "azure-key",
                        "azure_endpoint": "https://test.openai.azure.com",
                        "azure_deployment": "gpt-4",
                    },
                )

                provider = OpenAIProvider(config)

                repr_str = repr(provider)

                assert "OpenAIProvider" in repr_str
                assert "azure=True" in repr_str


class TestOpenAIProviderSupportedModels:
    """Tests for model lists."""

    def test_supported_models_list(self):
        """Test that supported models list is correct."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI"):
                from src.llm.openai_provider import OpenAIProvider

                expected_models = [
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-4-turbo",
                    "gpt-4-turbo-preview",
                    "gpt-4",
                    "gpt-4-32k",
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                ]

                assert OpenAIProvider.SUPPORTED_MODELS == expected_models

    def test_embedding_models_list(self):
        """Test that embedding models list is correct."""
        with patch("src.llm.openai_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.openai_provider.OpenAI"):
                from src.llm.openai_provider import OpenAIProvider

                expected_models = [
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                    "text-embedding-ada-002",
                ]

                assert OpenAIProvider.EMBEDDING_MODELS == expected_models
