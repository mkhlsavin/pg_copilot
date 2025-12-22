"""
Tests for Yandex Cloud AI Studio LLM Provider.

Tests for YandexProvider initialization, generation, streaming, embeddings,
and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.llm.base_provider import (
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
    LLMProviderAPIError,
)


class TestYandexProviderInit:
    """Tests for YandexProvider initialization."""

    def test_init_success(self):
        """Test successful initialization with API key and folder ID."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    temperature=0.7,
                    max_tokens=2000,
                    extra_params={
                        "api_key": "test-api-key",
                        "folder_id": "b1g123456789",
                        "model": "yandexgpt/latest",
                    },
                )

                provider = YandexProvider(config)

                assert provider.is_available() is True
                assert provider.model_name == "yandexgpt/latest"
                assert provider.folder_id == "b1g123456789"
                mock_openai.assert_called_once()

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            from src.llm.yandex_provider import YandexProvider

            config = LLMConfig(
                provider_type="yandex",
                extra_params={
                    "folder_id": "b1g123456789",
                },
            )

            with pytest.raises(ValueError) as exc_info:
                YandexProvider(config)

            assert "api key" in str(exc_info.value).lower()

    def test_init_missing_folder_id(self):
        """Test initialization fails without folder ID."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            from src.llm.yandex_provider import YandexProvider

            config = LLMConfig(
                provider_type="yandex",
                extra_params={
                    "api_key": "test-api-key",
                },
            )

            with pytest.raises(ValueError) as exc_info:
                YandexProvider(config)

            assert "folder id" in str(exc_info.value).lower()

    def test_init_library_not_available(self):
        """Test initialization fails when openai not installed."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", False):
            from src.llm.yandex_provider import YandexProvider

            config = LLMConfig(
                provider_type="yandex",
                extra_params={
                    "api_key": "test",
                    "folder_id": "b1g123",
                },
            )

            with pytest.raises(ImportError):
                YandexProvider(config)

    def test_init_default_model(self):
        """Test default model is qwen3-235b-a22b-fp8/latest."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)

                assert provider.model_name == "qwen3-235b-a22b-fp8/latest"

    def test_init_default_base_url(self):
        """Test default base URL is Yandex endpoint."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)

                # Verify base_url was passed
                call_kwargs = mock_openai.call_args.kwargs
                assert call_kwargs.get("base_url") == "https://llm.api.cloud.yandex.net/v1"

    def test_init_with_custom_base_url(self):
        """Test custom base URL."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test_key",
                        "folder_id": "b1g123456789",
                        "base_url": "https://custom.yandex.api/v1",
                    },
                )

                provider = YandexProvider(config)

                call_kwargs = mock_openai.call_args.kwargs
                assert call_kwargs.get("base_url") == "https://custom.yandex.api/v1"


class TestYandexProviderModelUri:
    """Tests for Yandex model URI construction."""

    def test_get_model_uri(self):
        """Test model URI construction."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                        "model": "yandexgpt/latest",
                    },
                )

                provider = YandexProvider(config)

                model_uri = provider._get_model_uri()
                assert model_uri == "gpt://b1g123456789/yandexgpt/latest"

    def test_get_model_uri_with_custom_model(self):
        """Test model URI with custom model name."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)

                model_uri = provider._get_model_uri("yandexgpt-lite/latest")
                assert model_uri == "gpt://b1g123456789/yandexgpt-lite/latest"

    def test_get_embedding_model_uri(self):
        """Test embedding model URI construction."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                        "embedding_model": "text-search-doc/latest",
                    },
                )

                provider = YandexProvider(config)

                embedding_uri = provider._get_embedding_model_uri()
                assert embedding_uri == "emb://b1g123456789/text-search-doc/latest"


class TestYandexProviderGenerate:
    """Tests for YandexProvider.generate()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked Yandex provider."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    temperature=0.7,
                    max_tokens=2000,
                    extra_params={
                        "api_key": "test-api-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)
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
        mock_response.model = "gpt://b1g123456789/yandexgpt/latest"
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
        assert response.metadata['tokens_used'] == 150
        assert response.metadata['provider'] == 'yandex'
        mock_client.chat.completions.create.assert_called_once()

    def test_generate_uses_model_uri(self, mock_provider):
        """Test that generation uses correct model URI."""
        provider, mock_client = mock_provider

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Response"),
                finish_reason="stop"
            )
        ]
        mock_response.model = "gpt://b1g123456789/yandexgpt/latest"
        mock_response.usage = MagicMock(
            total_tokens=100, prompt_tokens=50, completion_tokens=50
        )
        mock_client.chat.completions.create.return_value = mock_response

        provider.generate(
            system_prompt="test",
            user_prompt="test",
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt://b1g123456789/qwen3-235b-a22b-fp8/latest"

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
        mock_response.model = "gpt://b1g123456789/yandexgpt/latest"
        mock_response.usage = MagicMock(
            total_tokens=100, prompt_tokens=50, completion_tokens=50
        )
        mock_client.chat.completions.create.return_value = mock_response

        provider.generate(
            system_prompt="test",
            user_prompt="test",
            temperature=0.2,
            max_tokens=3000,
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 3000

    def test_generate_not_available(self):
        """Test generate when provider not available."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_openai.side_effect = Exception("Connection failed")

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123",
                    },
                )

                with pytest.raises(LLMProviderNotAvailableError):
                    YandexProvider(config)

    def test_generate_api_error(self, mock_provider):
        """Test API error handling."""
        provider, mock_client = mock_provider
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(LLMProviderAPIError):
            provider.generate(
                system_prompt="test",
                user_prompt="test",
            )


class TestYandexProviderRateLimiting:
    """Tests for rate limit and auth error handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked Yandex provider."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-api-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)
                yield provider, mock_client

    def test_rate_limit_error(self, mock_provider):
        """Test rate limit error handling."""
        provider, mock_client = mock_provider

        import openai

        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None,
        )

        from src.llm.yandex_provider import YandexRateLimitError

        with pytest.raises(YandexRateLimitError):
            provider.generate(
                system_prompt="test",
                user_prompt="test",
            )

    def test_auth_error(self, mock_provider):
        """Test authentication error handling."""
        provider, mock_client = mock_provider

        import openai

        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        from src.llm.yandex_provider import YandexAuthError

        with pytest.raises(YandexAuthError):
            provider.generate(
                system_prompt="test",
                user_prompt="test",
            )


class TestYandexProviderStream:
    """Tests for YandexProvider.generate_stream()."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mocked Yandex provider."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-api-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)
                yield provider, mock_client

    def test_generate_stream_success(self, mock_provider):
        """Test streaming generation."""
        provider, mock_client = mock_provider

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

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=None))]
        chunk3 = MagicMock()
        chunk3.choices = []

        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]

        chunks = list(provider.generate_stream(
            system_prompt="test",
            user_prompt="test",
        ))

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


class TestYandexProviderEmbeddings:
    """Tests for YandexProvider.get_embeddings()."""

    def test_get_embeddings_success(self):
        """Test successful embeddings generation."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()

                mock_embedding1 = MagicMock()
                mock_embedding1.embedding = [0.1, 0.2, 0.3]
                mock_embedding2 = MagicMock()
                mock_embedding2.embedding = [0.4, 0.5, 0.6]

                mock_response1 = MagicMock()
                mock_response1.data = [mock_embedding1]
                mock_response2 = MagicMock()
                mock_response2.data = [mock_embedding2]

                mock_client.embeddings.create.side_effect = [mock_response1, mock_response2]
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                        "embedding_model": "text-search-doc/latest",
                    },
                )

                provider = YandexProvider(config)

                embeddings = provider.get_embeddings(["text1", "text2"])

                assert len(embeddings) == 2
                assert embeddings[0] == [0.1, 0.2, 0.3]
                assert embeddings[1] == [0.4, 0.5, 0.6]

    def test_get_embeddings_uses_correct_model_uri(self):
        """Test that embeddings use correct model URI."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()

                mock_embedding = MagicMock()
                mock_embedding.embedding = [0.1, 0.2, 0.3]
                mock_response = MagicMock()
                mock_response.data = [mock_embedding]
                mock_client.embeddings.create.return_value = mock_response
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                        "embedding_model": "text-search-doc/latest",
                    },
                )

                provider = YandexProvider(config)
                provider.get_embeddings(["text"])

                call_kwargs = mock_client.embeddings.create.call_args.kwargs
                assert call_kwargs["model"] == "emb://b1g123456789/text-search-doc/latest"

    def test_get_embeddings_default_model(self):
        """Test default embedding model."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)

                assert provider.embedding_model == "text-search-doc/latest"

    def test_get_embeddings_error(self):
        """Test embeddings error handling."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.embeddings.create.side_effect = Exception("Embeddings error")
                mock_openai.return_value = mock_client

                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                    },
                )

                provider = YandexProvider(config)

                with pytest.raises(LLMProviderAPIError):
                    provider.get_embeddings(["text"])


class TestYandexProviderRepr:
    """Tests for YandexProvider string representation."""

    def test_repr(self):
        """Test __repr__."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                config = LLMConfig(
                    provider_type="yandex",
                    extra_params={
                        "api_key": "test-key",
                        "folder_id": "b1g123456789",
                        "model": "yandexgpt-lite/latest",
                    },
                )

                provider = YandexProvider(config)

                repr_str = repr(provider)

                assert "YandexProvider" in repr_str
                assert "yandexgpt-lite/latest" in repr_str
                assert "b1g12345..." in repr_str  # Folder ID preview
                assert "initialized=True" in repr_str


class TestYandexProviderSupportedModels:
    """Tests for model lists."""

    def test_supported_models_list(self):
        """Test that supported models list is correct."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                expected_models = [
                    "qwen3-235b-a22b-fp8/latest",
                    "yandexgpt/latest",
                    "yandexgpt-lite/latest",
                    "yandexgpt/rc",
                    "yandexgpt-32k/latest",
                    "yandexgpt-32k/rc",
                ]

                assert YandexProvider.SUPPORTED_MODELS == expected_models

    def test_embedding_models_list(self):
        """Test that embedding models list is correct."""
        with patch("src.llm.yandex_provider.OPENAI_AVAILABLE", True):
            with patch("src.llm.yandex_provider.OpenAI"):
                from src.llm.yandex_provider import YandexProvider

                expected_models = [
                    "text-search-doc/latest",
                    "text-search-query/latest",
                ]

                assert YandexProvider.EMBEDDING_MODELS == expected_models
