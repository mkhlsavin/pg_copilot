"""
Yandex Cloud AI Studio LLM Provider

Provider for Yandex Cloud AI Studio (YandexGPT) using OpenAI-compatible API.
Supports YandexGPT, YandexGPT-Lite, and embedding models.

Requires:
    - openai >= 1.0.0
    - YANDEX_API_KEY environment variable or api_key in config
    - YANDEX_FOLDER_ID environment variable or folder_id in config

Documentation: https://yandex.cloud/en/docs/ai-studio/concepts/openai-compatibility

Author: Configurable LLM Architecture
Date: December 2024
"""

import logging
import time
from typing import Generator, List, Optional

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
    LLMProviderAPIError,
)

logger = logging.getLogger(__name__)

# Lazy import for openai (may not be installed)
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning(
        "openai not installed. "
        "Install with: pip install openai"
    )


class YandexProvider(BaseLLMProvider):
    """
    Yandex Cloud AI Studio provider using OpenAI-compatible API.

    Supported models:
    - qwen3-235b-a22b-fp8/latest (Qwen3 235B - default, high quality)
    - yandexgpt/latest (YandexGPT - main model)
    - yandexgpt-lite/latest (YandexGPT Lite - faster, smaller)
    - yandexgpt/rc (Release Candidate with reasoning)

    Note: All requests include x-data-logging-enabled: false header
    to disable logging on Yandex side (GDPR/privacy compliance).

    Example:
        config = LLMConfig(
            provider_type='yandex',
            temperature=0.7,
            max_tokens=2000,
            extra_params={
                'api_key': 'AQVNw...',
                'folder_id': 'b1g...',
                'model': 'yandexgpt/latest',
            }
        )

        provider = YandexProvider(config)
        response = provider.generate(
            system_prompt="You are a code analysis expert",
            user_prompt="Explain how MVCC works in PostgreSQL"
        )
        print(response.content)
    """

    # Default Yandex API endpoint
    DEFAULT_BASE_URL = "https://llm.api.cloud.yandex.net/v1"

    # Supported text generation models
    SUPPORTED_MODELS = [
        "qwen3-235b-a22b-fp8/latest",  # Qwen3 235B (default)
        "yandexgpt/latest",
        "yandexgpt-lite/latest",
        "yandexgpt/rc",
        "yandexgpt-32k/latest",
        "yandexgpt-32k/rc",
    ]

    # Embedding models
    EMBEDDING_MODELS = [
        "text-search-doc/latest",
        "text-search-query/latest",
    ]

    def __init__(self, config: LLMConfig):
        """
        Initialize Yandex provider.

        Args:
            config: LLMConfig with extra_params containing:
                - api_key: Yandex Cloud API key (required)
                - folder_id: Yandex Cloud folder ID (required)
                - model: Model name (default: "yandexgpt/latest")
                - base_url: Custom API endpoint (optional)
                - timeout: Request timeout in seconds (default: 60)
                - embedding_model: Model for embeddings (default: "text-search-doc/latest")

        Raises:
            ImportError: If openai not installed
            ValueError: If api_key or folder_id not provided
        """
        super().__init__(config)

        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )

        # Extract parameters
        params = config.extra_params or {}

        self.api_key = params.get('api_key')
        self.folder_id = params.get('folder_id')
        self.model_name = params.get('model', 'qwen3-235b-a22b-fp8/latest')
        self.base_url = params.get('base_url', self.DEFAULT_BASE_URL)
        self.timeout = params.get('timeout', 60)
        self.embedding_model = params.get('embedding_model', 'text-search-doc/latest')

        # Validate required parameters
        if not self.api_key:
            raise ValueError(
                "Yandex API key not provided. "
                "Set YANDEX_API_KEY environment variable or add to config.yaml"
            )

        if not self.folder_id:
            raise ValueError(
                "Yandex folder ID not provided. "
                "Set YANDEX_FOLDER_ID environment variable or add to config.yaml"
            )

        # Initialize client
        try:
            logger.info(
                f"Initializing Yandex provider: model={self.model_name}, "
                f"folder_id={self.folder_id[:8]}..."
            )

            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                default_headers={
                    "x-data-logging-enabled": "false",
                    "x-folder-id": self.folder_id,
                },
            )

            self._initialized = True
            logger.info("Yandex provider initialized successfully")

        except Exception as e:
            self._initialized = False
            logger.error(f"Failed to initialize Yandex client: {e}")
            raise LLMProviderNotAvailableError(
                f"Yandex initialization failed: {e}"
            ) from e

    def _get_model_uri(self, model_name: Optional[str] = None) -> str:
        """
        Construct full model URI with folder_id.

        Yandex requires model format: gpt://<folder_id>/<model_name>

        Args:
            model_name: Model name (uses self.model_name if None)

        Returns:
            Full model URI string
        """
        name = model_name or self.model_name
        return f"gpt://{self.folder_id}/{name}"

    def _get_embedding_model_uri(self, model_name: Optional[str] = None) -> str:
        """
        Construct embedding model URI with folder_id.

        Args:
            model_name: Embedding model name (uses self.embedding_model if None)

        Returns:
            Full embedding model URI string
        """
        name = model_name or self.embedding_model
        return f"emb://{self.folder_id}/{name}"

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._initialized and OPENAI_AVAILABLE

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using Yandex API.

        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content

        Raises:
            LLMProviderAPIError: If API call fails
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError("Yandex provider not available")

        params = self._merge_config(**kwargs)
        model_uri = self._get_model_uri()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model_uri,
                messages=messages,
                temperature=params.get('temperature', 0.7),
                max_tokens=params.get('max_tokens', 2000),
                top_p=params.get('top_p'),
                stop=params.get('stop'),
            )

            elapsed_time = time.time() - start_time

            content = response.choices[0].message.content or ""
            usage = response.usage

            return LLMResponse(
                content=content,
                metadata={
                    'model': response.model,
                    'tokens_used': usage.total_tokens if usage else 0,
                    'prompt_tokens': usage.prompt_tokens if usage else 0,
                    'completion_tokens': usage.completion_tokens if usage else 0,
                    'latency_ms': elapsed_time * 1000,
                    'finish_reason': response.choices[0].finish_reason,
                    'provider': 'yandex',
                    'folder_id': self.folder_id,
                },
            )

        except openai.RateLimitError as e:
            logger.error(f"Yandex rate limit exceeded: {e}")
            raise YandexRateLimitError(f"Rate limit exceeded: {e}") from e

        except openai.AuthenticationError as e:
            logger.error(f"Yandex authentication error: {e}")
            raise YandexAuthError(f"Authentication failed: {e}") from e

        except openai.APIError as e:
            logger.error(f"Yandex API error: {e}")
            raise LLMProviderAPIError(f"Yandex API error: {e}") from e

        except Exception as e:
            logger.error(f"Yandex unexpected error: {e}")
            raise LLMProviderAPIError(f"Yandex call failed: {e}") from e

    def generate_simple(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with a single prompt (no system/user split).

        Args:
            prompt: The full prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content
        """
        return self.generate(
            system_prompt="",
            user_prompt=prompt,
            **kwargs
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream response using Yandex API.

        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional parameters

        Yields:
            Response chunks as strings
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError("Yandex provider not available")

        params = self._merge_config(**kwargs)
        model_uri = self._get_model_uri()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            stream = self.client.chat.completions.create(
                model=model_uri,
                messages=messages,
                temperature=params.get('temperature', 0.7),
                max_tokens=params.get('max_tokens', 2000),
                top_p=params.get('top_p'),
                stop=params.get('stop'),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Yandex streaming error: {e}")
            raise LLMProviderAPIError(f"Yandex streaming failed: {e}") from e

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings using Yandex embeddings API.

        Note: Yandex embeddings API has some limitations compared to OpenAI.
        It supports single strings with encoding_format set to float.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            LLMProviderAPIError: If API call fails
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError("Yandex provider not available")

        embedding_model_uri = self._get_embedding_model_uri()

        try:
            # Process texts one by one due to Yandex API limitations
            embeddings = []
            for text in texts:
                response = self.client.embeddings.create(
                    model=embedding_model_uri,
                    input=text,
                    encoding_format="float",
                )
                embeddings.append(response.data[0].embedding)

            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Yandex embeddings error: {e}")
            raise LLMProviderAPIError(f"Yandex embeddings failed: {e}") from e

    def __repr__(self) -> str:
        folder_preview = self.folder_id[:8] + "..." if self.folder_id else "None"
        return (
            f"YandexProvider("
            f"model='{self.model_name}', "
            f"folder_id='{folder_preview}', "
            f"initialized={self._initialized})"
        )


class YandexRateLimitError(LLMProviderAPIError):
    """Rate limit exceeded error for Yandex API."""
    pass


class YandexAuthError(LLMProviderAPIError):
    """Authentication error for Yandex API."""
    pass
