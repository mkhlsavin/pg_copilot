"""
Base LLM Provider Interface

Абстрактный базовый класс для всех LLM провайдеров.
Обеспечивает единый интерфейс для локальных моделей и API-сервисов.

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Unified response from LLM providers"""
    content: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Base configuration for LLM providers"""
    provider_type: str  # "local", "gigachat", "openai", etc.
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None

    # Additional provider-specific config
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseLLMProvider(ABC):
    """
    Базовый интерфейс для всех LLM провайдеров.

    Все провайдеры должны реализовать методы:
    - generate(): Генерация с system/user промптами
    - generate_simple(): Генерация с одним промптом
    - is_available(): Проверка доступности

    Опциональные методы:
    - generate_stream(): Потоковая генерация
    - get_embeddings(): Получение эмбеддингов (для совместимости)
    """

    def __init__(self, config: LLMConfig):
        """
        Инициализация провайдера.

        Args:
            config: Конфигурация провайдера
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Генерация с раздельными system и user промптами.

        Args:
            system_prompt: Системный промпт (роль, инструкции)
            user_prompt: Пользовательский промпт (запрос)
            **kwargs: Дополнительные параметры (temperature, max_tokens, etc.)

        Returns:
            LLMResponse с сгенерированным текстом

        Example:
            response = provider.generate(
                system_prompt="You are a code analyst",
                user_prompt="Explain this function: ...",
                temperature=0.5
            )
            print(response.content)
        """
        pass

    @abstractmethod
    def generate_simple(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Генерация с одним промптом (без разделения на system/user).

        Args:
            prompt: Полный промпт
            **kwargs: Дополнительные параметры

        Returns:
            LLMResponse с сгенерированным текстом

        Example:
            response = provider.generate_simple(
                prompt="Explain MVCC in PostgreSQL",
                max_tokens=200
            )
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Проверка доступности провайдера.

        Returns:
            True если провайдер готов к работе, False иначе

        Example:
            if not provider.is_available():
                print("Provider not available, using fallback")
        """
        pass

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ):
        """
        Потоковая генерация (опционально).

        Не все провайдеры поддерживают потоковую генерацию.
        По умолчанию вызывает обычный generate().

        Args:
            system_prompt: Системный промпт
            user_prompt: Пользовательский промпт
            **kwargs: Дополнительные параметры

        Yields:
            Части сгенерированного текста
        """
        # Default: no streaming support, return full response
        response = self.generate(system_prompt, user_prompt, **kwargs)
        yield response.content

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получение эмбеддингов (опционально).

        Не все провайдеры поддерживают эмбеддинги.
        Используется для совместимости с RAGAS.

        Args:
            texts: Список текстов для эмбеддинга

        Returns:
            Список векторов эмбеддингов

        Raises:
            NotImplementedError если провайдер не поддерживает эмбеддинги
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support embeddings"
        )

    def _merge_config(self, **kwargs) -> Dict[str, Any]:
        """
        Объединение конфигурации провайдера с параметрами вызова.

        Args:
            **kwargs: Параметры вызова (переопределяют config)

        Returns:
            Объединенная конфигурация
        """
        merged = {
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
        }

        if self.config.top_p is not None:
            merged['top_p'] = self.config.top_p

        if self.config.top_k is not None:
            merged['top_k'] = self.config.top_k

        if self.config.stop_sequences:
            merged['stop'] = self.config.stop_sequences

        # Переопределение из kwargs
        merged.update(kwargs)

        return merged

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider_type='{self.config.provider_type}', "
            f"temperature={self.config.temperature})"
        )


class LLMProviderError(Exception):
    """Базовое исключение для ошибок LLM провайдеров"""
    pass


class LLMProviderNotAvailableError(LLMProviderError):
    """Провайдер недоступен"""
    pass


class LLMProviderConfigError(LLMProviderError):
    """Ошибка конфигурации провайдера"""
    pass


class LLMProviderAPIError(LLMProviderError):
    """Ошибка API провайдера"""
    pass
