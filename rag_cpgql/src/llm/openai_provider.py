"""
OpenAI LLM Provider

Provider for OpenAI API and OpenAI-compatible APIs (Azure, local servers).
Supports GPT-4, GPT-3.5, and compatible models.

Requires:
    - openai >= 1.0.0
    - OPENAI_API_KEY environment variable or api_key in config

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
    from openai import OpenAI, AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning(
        "openai not installed. "
        "Install with: pip install openai"
    )


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider using official openai library.

    Supported models:
    - gpt-4o, gpt-4o-mini (recommended)
    - gpt-4-turbo, gpt-4
    - gpt-3.5-turbo
    - Any OpenAI-compatible API

    Example:
        config = LLMConfig(
            provider_type='openai',
            temperature=0.7,
            max_tokens=512,
            extra_params={
                'api_key': 'sk-...',
                'model': 'gpt-4o-mini',
            }
        )

        provider = OpenAIProvider(config)
        response = provider.generate(
            system_prompt="You are a code analysis expert",
            user_prompt="Explain how MVCC works in PostgreSQL"
        )
        print(response.content)
    """

    # Common OpenAI models
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-4-32k",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    # Embedding models
    EMBEDDING_MODELS = [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ]

    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: LLMConfig with extra_params containing:
                - api_key: OpenAI API key (required unless using Azure)
                - model: Model name (default: "gpt-4o-mini")
                - base_url: Custom API endpoint (optional, for compatible APIs)
                - organization: OpenAI organization ID (optional)
                - timeout: Request timeout in seconds (default: 60)
                - azure_endpoint: Azure OpenAI endpoint (for Azure)
                - azure_deployment: Azure deployment name (for Azure)
                - api_version: API version for Azure (default: "2024-02-01")
                - embedding_model: Model for embeddings (default: "text-embedding-3-small")

        Raises:
            ImportError: If openai not installed
            ValueError: If api_key not provided
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
        self.model_name = params.get('model', 'gpt-4o-mini')
        self.base_url = params.get('base_url')
        self.organization = params.get('organization')
        self.timeout = params.get('timeout', 60)
        self.embedding_model = params.get('embedding_model', 'text-embedding-3-small')

        # Azure-specific params
        self.azure_endpoint = params.get('azure_endpoint')
        self.azure_deployment = params.get('azure_deployment')
        self.api_version = params.get('api_version', '2024-02-01')

        # Determine if using Azure
        self.is_azure = bool(self.azure_endpoint)

        # Validate
        if not self.api_key and not self.is_azure:
            raise ValueError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY environment variable or add to config.yaml"
            )

        # Initialize client
        try:
            if self.is_azure:
                logger.info(
                    f"Initializing Azure OpenAI: endpoint={self.azure_endpoint}, "
                    f"deployment={self.azure_deployment}"
                )
                self.client = AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.api_version,
                    timeout=self.timeout,
                )
            else:
                logger.info(f"Initializing OpenAI: model={self.model_name}")
                client_params = {
                    'api_key': self.api_key,
                    'timeout': self.timeout,
                }
                if self.base_url:
                    client_params['base_url'] = self.base_url
                if self.organization:
                    client_params['organization'] = self.organization

                self.client = OpenAI(**client_params)

            self._initialized = True
            logger.info("OpenAI provider initialized successfully")

        except Exception as e:
            self._initialized = False
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise LLMProviderNotAvailableError(
                f"OpenAI initialization failed: {e}"
            ) from e

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
        Generate response using OpenAI API.

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
            raise LLMProviderNotAvailableError("OpenAI provider not available")

        params = self._merge_config(**kwargs)
        model = self.azure_deployment if self.is_azure else self.model_name

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=params.get('temperature', 0.7),
                max_tokens=params.get('max_tokens', 512),
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
                    'provider': 'azure_openai' if self.is_azure else 'openai',
                },
            )

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise OpenAIRateLimitError(f"Rate limit exceeded: {e}") from e

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise OpenAIAuthError(f"Authentication failed: {e}") from e

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMProviderAPIError(f"OpenAI API error: {e}") from e

        except Exception as e:
            logger.error(f"OpenAI unexpected error: {e}")
            raise LLMProviderAPIError(f"OpenAI call failed: {e}") from e

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
        # Delegate to generate with prompt as user message and empty system
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
        Stream response using OpenAI API.

        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional parameters

        Yields:
            Response chunks as strings
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError("OpenAI provider not available")

        params = self._merge_config(**kwargs)
        model = self.azure_deployment if self.is_azure else self.model_name

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=params.get('temperature', 0.7),
                max_tokens=params.get('max_tokens', 512),
                top_p=params.get('top_p'),
                stop=params.get('stop'),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise LLMProviderAPIError(f"OpenAI streaming failed: {e}") from e

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings using OpenAI embeddings API.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            LLMProviderAPIError: If API call fails
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError("OpenAI provider not available")

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            logger.error(f"OpenAI embeddings error: {e}")
            raise LLMProviderAPIError(f"OpenAI embeddings failed: {e}") from e

    def __repr__(self) -> str:
        return (
            f"OpenAIProvider("
            f"model='{self.model_name}', "
            f"azure={self.is_azure}, "
            f"initialized={self._initialized})"
        )


class OpenAIRateLimitError(LLMProviderAPIError):
    """Rate limit exceeded error"""
    pass


class OpenAIAuthError(LLMProviderAPIError):
    """Authentication error"""
    pass
