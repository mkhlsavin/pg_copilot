"""
LLM Providers Module

Модуль для работы с различными LLM провайдерами (локальные модели и API).

Основные компоненты:
- BaseLLMProvider: Базовый интерфейс для всех провайдеров
- LocalLLMProvider: Локальные модели через llama-cpp-python
- GigaChatProvider: GigaChat API через langchain-gigachat
- create_llm_provider(): Фабрика для создания провайдеров из конфига

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderError,
    LLMProviderNotAvailableError,
    LLMProviderConfigError,
    LLMProviderAPIError,
)

__all__ = [
    'BaseLLMProvider',
    'LLMConfig',
    'LLMResponse',
    'LLMProviderError',
    'LLMProviderNotAvailableError',
    'LLMProviderConfigError',
    'LLMProviderAPIError',
    'create_langchain_adapter',
    'get_ragas_llm',
]

# Lazy imports для провайдеров (чтобы не ломалось если зависимости не установлены)
def get_local_provider():
    """Lazy import LocalLLMProvider"""
    from .local_provider import LocalLLMProvider
    return LocalLLMProvider

def get_gigachat_provider():
    """Lazy import GigaChatProvider"""
    try:
        from .gigachat_provider import GigaChatProvider
        return GigaChatProvider
    except ImportError as e:
        raise ImportError(
            "GigaChat provider requires langchain-gigachat. "
            "Install with: pip install langchain-gigachat"
        ) from e

def create_llm_provider(config: dict = None):
    """
    Фабрика для создания LLM провайдера из конфигурации.

    Args:
        config: Конфигурация (если None, загружается из config.yaml)

    Returns:
        Экземпляр BaseLLMProvider

    Example:
        # Из config.yaml
        provider = create_llm_provider()

        # С кастомной конфигурацией
        provider = create_llm_provider({
            'provider': 'gigachat',
            'gigachat': {'credentials': '...', 'model': 'GigaChat-Pro'}
        })
    """
    from .factory import create_llm_provider as factory_create
    return factory_create(config)

def create_langchain_adapter(provider):
    """
    Создает LangChain-совместимый адаптер для RAGAS.

    Args:
        provider: BaseLLMProvider instance

    Returns:
        LangChain LLM instance

    Example:
        provider = create_llm_provider()
        langchain_llm = create_langchain_adapter(provider)
    """
    from .langchain_adapter import create_langchain_adapter as create_adapter
    return create_adapter(provider)

def get_ragas_llm(provider=None):
    """
    Получить LLM для RAGAS evaluation.

    Args:
        provider: Optional BaseLLMProvider (если None, создается из config.yaml)

    Returns:
        LangChain LLM instance готовый для RAGAS

    Example:
        # Использовать default provider из config.yaml
        llm = get_ragas_llm()

        # Использовать конкретный provider
        provider = create_llm_provider()
        llm = get_ragas_llm(provider)
    """
    from .langchain_adapter import get_ragas_llm as get_llm
    return get_llm(provider)
