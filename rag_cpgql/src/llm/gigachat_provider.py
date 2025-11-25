"""
GigaChat LLM Provider

Provider for Sber GigaChat API using langchain-gigachat.
Supports GigaChat-Pro, GigaChat-Max, and other models.

Requires:
    - langchain-gigachat >= 0.2.0
    - GIGACHAT_CREDENTIALS environment variable or credentials in config

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

import logging
from typing import Optional, List

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
    LLMProviderAPIError,
)

logger = logging.getLogger(__name__)

# Lazy import для langchain-gigachat (может быть не установлен)
try:
    from langchain_gigachat import GigaChat
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    logger.warning(
        "langchain-gigachat not installed. "
        "Install with: pip install langchain-gigachat"
    )


class GigaChatProvider(BaseLLMProvider):
    """
    GigaChat API provider using langchain-gigachat.

    Supported models:
    - GigaChat-Pro (рекомендуется для большинства задач)
    - GigaChat-Max (максимальное качество, медленнее)
    - GigaChat (базовая версия)

    Example:
        config = LLMConfig(
            provider_type='gigachat',
            temperature=0.7,
            max_tokens=512,
            extra_params={
                'credentials': 'YOUR_GIGACHAT_CREDENTIALS',
                'model': 'GigaChat-Pro',
                'verify_ssl_certs': True,
                'scope': 'GIGACHAT_API_PERS'
            }
        )

        provider = GigaChatProvider(config)
        response = provider.generate(
            system_prompt="Вы - эксперт по анализу кода",
            user_prompt="Объясните как работает MVCC в PostgreSQL"
        )
        print(response.content)
    """

    # Поддерживаемые модели
    SUPPORTED_MODELS = [
        "GigaChat",        # Базовая модель
        "GigaChat-Pro",    # Продвинутая
        "GigaChat-Plus",   # Расширенная
        "GigaChat-Max",    # Максимальное качество
        "GigaChat-2-Pro",  # Новая версия Pro (рекомендуется)
    ]

    # Доступные scope
    SCOPES = [
        "GIGACHAT_API_PERS",  # Персональный
        "GIGACHAT_API_CORP",  # Корпоративный
        "GIGACHAT_API_B2B",   # B2B
    ]

    def __init__(self, config: LLMConfig):
        """
        Initialize GigaChat provider.

        Args:
            config: LLMConfig with extra_params containing:
                - credentials: GigaChat API credentials (обязательно)
                - model: Model name (default: "GigaChat-Pro")
                - base_url: Custom API endpoint (optional)
                - verify_ssl_certs: Verify SSL certificates (default: True)
                - scope: API scope (default: "GIGACHAT_API_PERS")
                - timeout: Request timeout in seconds (default: 30)

        Raises:
            ImportError: If langchain-gigachat not installed
            ValueError: If credentials not provided
        """
        super().__init__(config)

        if not GIGACHAT_AVAILABLE:
            raise ImportError(
                "langchain-gigachat not installed. "
                "Install with: pip install langchain-gigachat"
            )

        # Извлечение параметров
        params = config.extra_params or {}

        self.credentials = params.get('credentials')
        if not self.credentials:
            raise ValueError(
                "GigaChat credentials not provided. "
                "Set GIGACHAT_CREDENTIALS environment variable or add to config.yaml"
            )

        self.model_name = params.get('model', 'GigaChat-Pro')
        self.base_url = params.get('base_url')
        self.verify_ssl_certs = params.get('verify_ssl_certs', True)
        self.scope = params.get('scope', 'GIGACHAT_API_PERS')
        self.timeout = params.get('timeout', 30)

        # Валидация модели
        if self.model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Unknown model: {self.model_name}. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
            )

        # Инициализация GigaChat client
        try:
            logger.info(f"Initializing GigaChat: model={self.model_name}, scope={self.scope}")

            gigachat_params = {
                'credentials': self.credentials,
                'model': self.model_name,
                'verify_ssl_certs': self.verify_ssl_certs,
                'scope': self.scope,
                'timeout': self.timeout,
            }

            if self.base_url:
                gigachat_params['base_url'] = self.base_url

            self.client = GigaChat(**gigachat_params)
            self._initialized = True

            logger.info("GigaChat client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GigaChat: {e}")
            self.client = None
            self._initialized = False

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using GigaChat API.

        Args:
            system_prompt: System instructions (роль, инструкции)
            user_prompt: User input (запрос)
            **kwargs: Optional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated text

        Raises:
            LLMProviderNotAvailableError: If client not initialized
            LLMProviderAPIError: If API request fails
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "GigaChat provider not initialized. Check credentials and API access."
            )

        try:
            # Объединение конфигурации с параметрами вызова
            params = self._merge_config(**kwargs)

            # Построение messages для chat format
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            logger.debug(
                f"GigaChat request: model={self.model_name}, "
                f"temp={params['temperature']}, max_tokens={params['max_tokens']}"
            )

            # API вызов
            response = self.client.invoke(
                messages,
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
                top_p=params.get('top_p') if params.get('top_p') is not None else 1.0,
            )

            content = response.content if hasattr(response, 'content') else str(response)

            # Метаданные
            metadata = {
                'model': self.model_name,
                'provider': 'gigachat',
                'scope': self.scope,
            }

            # Добавляем usage если доступно
            if hasattr(response, 'response_metadata'):
                metadata['usage'] = response.response_metadata.get('usage', {})

            return LLMResponse(content=content, metadata=metadata)

        except Exception as e:
            logger.error(f"GigaChat API error: {e}")
            raise LLMProviderAPIError(f"GigaChat API request failed: {e}") from e

    def generate_simple(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Simple generation without system/user separation.

        Для GigaChat просто отправляем prompt как HumanMessage.

        Args:
            prompt: Direct prompt text
            **kwargs: Optional parameters

        Returns:
            LLMResponse with generated text

        Raises:
            LLMProviderNotAvailableError: If client not initialized
            LLMProviderAPIError: If API request fails
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "GigaChat provider not initialized"
            )

        try:
            params = self._merge_config(**kwargs)

            logger.debug(
                f"GigaChat simple request: model={self.model_name}, "
                f"temp={params['temperature']}, max_tokens={params['max_tokens']}"
            )

            # Отправляем как обычное сообщение
            response = self.client.invoke(
                prompt,
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
                top_p=params.get('top_p') if params.get('top_p') is not None else 1.0,
            )

            content = response.content if hasattr(response, 'content') else str(response)

            metadata = {
                'model': self.model_name,
                'provider': 'gigachat',
            }

            return LLMResponse(content=content, metadata=metadata)

        except Exception as e:
            logger.error(f"GigaChat API error: {e}")
            raise LLMProviderAPIError(f"GigaChat API request failed: {e}") from e

    def is_available(self) -> bool:
        """
        Check if GigaChat provider is ready.

        Returns:
            True if client initialized successfully, False otherwise
        """
        return self._initialized and self.client is not None

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ):
        """
        Streaming generation with GigaChat API.

        Args:
            system_prompt: System instructions
            user_prompt: User input
            **kwargs: Optional parameters

        Yields:
            Chunks of generated text
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "GigaChat provider not initialized"
            )

        try:
            params = self._merge_config(**kwargs)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            logger.debug(f"GigaChat streaming request: model={self.model_name}")

            # Streaming generation
            for chunk in self.client.stream(
                messages,
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
            ):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"GigaChat streaming error: {e}")
            raise LLMProviderAPIError(f"GigaChat streaming failed: {e}") from e

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings using GigaChat embeddings API.

        Note: GigaChat может не поддерживать embeddings API.
        Используйте отдельный embeddings provider для RAGAS.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            NotImplementedError: If GigaChat doesn't support embeddings
        """
        # TODO: Проверить поддерживает ли GigaChat embeddings API
        # Если нет, использовать отдельный provider для embeddings
        raise NotImplementedError(
            "GigaChat embeddings not yet implemented. "
            "Use separate embedding model for RAGAS."
        )

    def __repr__(self) -> str:
        return (
            f"GigaChatProvider("
            f"model='{self.model_name}', "
            f"scope='{self.scope}', "
            f"initialized={self._initialized})"
        )


class GigaChatRateLimitError(LLMProviderAPIError):
    """Rate limit exceeded error"""
    pass


class GigaChatAuthError(LLMProviderAPIError):
    """Authentication error"""
    pass
