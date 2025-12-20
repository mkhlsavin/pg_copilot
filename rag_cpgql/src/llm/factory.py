"""
LLM Provider Factory

Фабрика для создания LLM провайдеров из конфигурации.
Автоматически выбирает правильный провайдер на основе config.yaml.

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderConfigError,
)

logger = logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Загружает конфигурацию из config.yaml.

    Args:
        config_path: Путь к config.yaml (если None, ищет в корне проекта)

    Returns:
        Словарь с конфигурацией
    """
    import yaml

    if config_path is None:
        # Ищем config.yaml в корне проекта
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        config_path = project_root / "config.yaml"

    if not Path(config_path).exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config or {}


def resolve_env_vars(value: Any) -> Any:
    """
    Рекурсивно разрешает переменные окружения в конфигурации.

    Поддерживает синтаксис ${VAR_NAME} и ${VAR_NAME:-default_value}

    Args:
        value: Значение из конфига (может быть str, dict, list)

    Returns:
        Значение с разрешенными env переменными
    """
    import os
    import re

    if isinstance(value, str):
        # Паттерн: ${VAR_NAME} или ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]+))?\}'

        def replace_env(match):
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                logger.warning(
                    f"Environment variable {var_name} not set and no default provided"
                )
                return match.group(0)  # Оставить как есть

        return re.sub(pattern, replace_env, value)

    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]

    return value


def create_llm_provider(
    config: Optional[Dict[str, Any]] = None
) -> BaseLLMProvider:
    """
    Создает LLM провайдер из конфигурации.

    Args:
        config: Конфигурация (если None, загружается из config.yaml)

    Returns:
        Экземпляр BaseLLMProvider (LocalLLMProvider или GigaChatProvider)

    Raises:
        LLMProviderConfigError: Если конфигурация некорректна

    Example:
        # Из config.yaml
        provider = create_llm_provider()

        # С кастомной конфигурацией
        provider = create_llm_provider({
            'llm': {
                'provider': 'gigachat',
                'gigachat': {
                    'credentials': 'YOUR_CREDENTIALS',
                    'model': 'GigaChat-Pro'
                }
            }
        })
    """
    # Загрузка конфигурации
    if config is None:
        config = load_config()

    llm_config = config.get('llm', {})

    if not llm_config:
        logger.warning(
            "No LLM configuration found in config.yaml, using default local provider"
        )
        llm_config = {'provider': 'local'}

    # Разрешение env переменных
    llm_config = resolve_env_vars(llm_config)

    provider_type = llm_config.get('provider', 'local')

    logger.info(f"Creating LLM provider: {provider_type}")

    # Создание провайдера на основе типа
    if provider_type == 'local':
        return _create_local_provider(llm_config)

    elif provider_type == 'gigachat':
        return _create_gigachat_provider(llm_config)

    elif provider_type == 'openai':
        return _create_openai_provider(llm_config)

    elif provider_type == 'yandex':
        return _create_yandex_provider(llm_config)

    else:
        raise LLMProviderConfigError(
            f"Unknown provider type: {provider_type}. "
            f"Supported: local, gigachat, openai, yandex"
        )


def _create_local_provider(config: Dict[str, Any]) -> BaseLLMProvider:
    """
    Создает LocalLLMProvider (llama-cpp-python).

    Args:
        config: Конфигурация LLM из config.yaml

    Returns:
        LocalLLMProvider instance
    """
    from .local_provider import LocalLLMProvider

    local_config = config.get('local', {})

    # Базовые параметры
    base_config = LLMConfig(
        provider_type='local',
        temperature=local_config.get('temperature', 0.7),
        max_tokens=local_config.get('max_tokens', 512),
        top_p=local_config.get('top_p'),
        top_k=local_config.get('top_k'),
    )

    # Специфичные параметры для LocalLLM
    local_params = {
        'model_path': local_config.get('model_path'),
        'use_llmxcpg': local_config.get('use_llmxcpg', True),
        'n_ctx': local_config.get('n_ctx', 8192),
        'n_gpu_layers': local_config.get('n_gpu_layers', -1),
        'n_batch': local_config.get('n_batch', 512),
        'n_threads': local_config.get('n_threads', 8),
        'verbose': local_config.get('verbose', False),
    }

    base_config.extra_params = local_params

    provider = LocalLLMProvider(base_config)

    if not provider.is_available():
        logger.error("Local LLM provider is not available!")
        raise LLMProviderConfigError(
            "Local LLM provider initialization failed. "
            "Check model_path and llama-cpp-python installation."
        )

    logger.info("LocalLLMProvider created successfully")

    # Wrap with security layer if enabled
    provider = _wrap_with_security(provider)

    return provider


def _create_gigachat_provider(config: Dict[str, Any]) -> BaseLLMProvider:
    """
    Создает GigaChatProvider (langchain-gigachat).

    Args:
        config: Конфигурация LLM из config.yaml

    Returns:
        GigaChatProvider instance
    """
    try:
        from .gigachat_provider import GigaChatProvider
    except ImportError as e:
        raise LLMProviderConfigError(
            "GigaChat provider requires langchain-gigachat. "
            "Install with: pip install langchain-gigachat"
        ) from e

    gigachat_config = config.get('gigachat', {})

    # Проверка обязательных параметров
    credentials = gigachat_config.get('credentials')
    if not credentials:
        raise LLMProviderConfigError(
            "GigaChat credentials not provided. "
            "Set GIGACHAT_CREDENTIALS environment variable or add to config.yaml"
        )

    # Базовые параметры
    base_config = LLMConfig(
        provider_type='gigachat',
        temperature=gigachat_config.get('temperature', 0.7),
        max_tokens=gigachat_config.get('max_tokens', 512),
        top_p=gigachat_config.get('top_p'),
    )

    # Специфичные параметры для GigaChat
    gigachat_params = {
        'credentials': credentials,
        'model': gigachat_config.get('model', 'GigaChat-Pro'),
        'base_url': gigachat_config.get('base_url'),
        'verify_ssl_certs': gigachat_config.get('verify_ssl_certs', True),
        'scope': gigachat_config.get('scope', 'GIGACHAT_API_PERS'),
    }

    base_config.extra_params = gigachat_params

    provider = GigaChatProvider(base_config)

    if not provider.is_available():
        logger.error("GigaChat provider is not available!")
        raise LLMProviderConfigError(
            "GigaChat provider initialization failed. "
            "Check credentials and API access."
        )

    logger.info("GigaChatProvider created successfully")

    # Wrap with security layer if enabled
    provider = _wrap_with_security(provider)

    return provider


def _wrap_with_security(provider: BaseLLMProvider) -> BaseLLMProvider:
    """
    Wrap LLM provider with security layer if enabled.

    Args:
        provider: Base LLM provider to wrap

    Returns:
        SecureLLMProvider if security enabled, otherwise original provider
    """
    try:
        from src.security import get_security_config, SecureLLMProvider

        security_config = get_security_config()

        if security_config.enabled:
            secure_provider = SecureLLMProvider(provider, security_config)
            logger.info(
                f"LLM provider wrapped with security layer "
                f"(DLP={security_config.dlp.enabled}, "
                f"SIEM={security_config.siem.enabled})"
            )
            return secure_provider

    except ImportError as e:
        logger.debug(f"Security module not available: {e}")
    except Exception as e:
        logger.warning(f"Could not initialize security wrapper: {e}")

    return provider


def _create_openai_provider(config: Dict[str, Any]) -> BaseLLMProvider:
    """
    Создает OpenAI API provider.

    Поддерживает стандартный OpenAI API и Azure OpenAI.

    Args:
        config: Конфигурация LLM из config.yaml

    Returns:
        OpenAIProvider instance
    """
    try:
        from .openai_provider import OpenAIProvider
    except ImportError as e:
        raise LLMProviderConfigError(
            "OpenAI provider requires openai library. "
            "Install with: pip install openai"
        ) from e

    openai_config = config.get('openai', {})

    # Check for API key
    api_key = openai_config.get('api_key')
    azure_endpoint = openai_config.get('azure_endpoint')

    if not api_key and not azure_endpoint:
        raise LLMProviderConfigError(
            "OpenAI API key not provided. "
            "Set OPENAI_API_KEY environment variable or add to config.yaml"
        )

    # Base parameters
    base_config = LLMConfig(
        provider_type='openai',
        temperature=openai_config.get('temperature', 0.7),
        max_tokens=openai_config.get('max_tokens', 512),
        top_p=openai_config.get('top_p'),
    )

    # OpenAI-specific parameters
    openai_params = {
        'api_key': api_key,
        'model': openai_config.get('model', 'gpt-4o-mini'),
        'base_url': openai_config.get('base_url'),
        'organization': openai_config.get('organization'),
        'timeout': openai_config.get('timeout', 60),
        'embedding_model': openai_config.get('embedding_model', 'text-embedding-3-small'),
        # Azure parameters
        'azure_endpoint': azure_endpoint,
        'azure_deployment': openai_config.get('azure_deployment'),
        'api_version': openai_config.get('api_version', '2024-02-01'),
    }

    base_config.extra_params = openai_params

    provider = OpenAIProvider(base_config)

    if not provider.is_available():
        logger.error("OpenAI provider is not available!")
        raise LLMProviderConfigError(
            "OpenAI provider initialization failed. "
            "Check API key and network access."
        )

    logger.info("OpenAIProvider created successfully")

    # Wrap with security layer if enabled
    provider = _wrap_with_security(provider)

    return provider


def _create_yandex_provider(config: Dict[str, Any]) -> BaseLLMProvider:
    """
    Создает Yandex Cloud AI Studio provider.

    Uses OpenAI-compatible API with Yandex-specific model URIs.

    Args:
        config: Конфигурация LLM из config.yaml

    Returns:
        YandexProvider instance
    """
    try:
        from .yandex_provider import YandexProvider
    except ImportError as e:
        raise LLMProviderConfigError(
            "Yandex provider requires openai library. "
            "Install with: pip install openai"
        ) from e

    yandex_config = config.get('yandex', {})

    # Check for required parameters
    api_key = yandex_config.get('api_key')
    folder_id = yandex_config.get('folder_id')

    if not api_key:
        raise LLMProviderConfigError(
            "Yandex API key not provided. "
            "Set YANDEX_API_KEY environment variable or add to config.yaml"
        )

    if not folder_id:
        raise LLMProviderConfigError(
            "Yandex folder ID not provided. "
            "Set YANDEX_FOLDER_ID environment variable or add to config.yaml"
        )

    # Base parameters
    base_config = LLMConfig(
        provider_type='yandex',
        temperature=yandex_config.get('temperature', 0.7),
        max_tokens=yandex_config.get('max_tokens', 2000),
        top_p=yandex_config.get('top_p'),
    )

    # Yandex-specific parameters
    yandex_params = {
        'api_key': api_key,
        'folder_id': folder_id,
        'model': yandex_config.get('model', 'yandexgpt/latest'),
        'base_url': yandex_config.get('base_url', 'https://llm.api.cloud.yandex.net/v1'),
        'timeout': yandex_config.get('timeout', 60),
        'embedding_model': yandex_config.get('embedding_model', 'text-search-doc/latest'),
    }

    base_config.extra_params = yandex_params

    provider = YandexProvider(base_config)

    if not provider.is_available():
        logger.error("Yandex provider is not available!")
        raise LLMProviderConfigError(
            "Yandex provider initialization failed. "
            "Check API key, folder ID, and network access."
        )

    logger.info("YandexProvider created successfully")

    # Wrap with security layer if enabled
    provider = _wrap_with_security(provider)

    return provider


def get_available_providers() -> Dict[str, bool]:
    """
    Возвращает список доступных провайдеров.

    Returns:
        Dict с провайдерами и их доступностью

    Example:
        available = get_available_providers()
        # {'local': True, 'gigachat': False, 'openai': False}
    """
    providers = {}

    # Проверка local provider
    try:
        from .local_provider import LocalLLMProvider
        providers['local'] = True
    except ImportError:
        providers['local'] = False

    # Проверка GigaChat provider
    try:
        from .gigachat_provider import GigaChatProvider
        providers['gigachat'] = True
    except ImportError:
        providers['gigachat'] = False

    # OpenAI provider
    try:
        from .openai_provider import OpenAIProvider
        providers['openai'] = True
    except ImportError:
        providers['openai'] = False

    # Yandex provider (uses openai library)
    try:
        from .yandex_provider import YandexProvider
        providers['yandex'] = True
    except ImportError:
        providers['yandex'] = False

    return providers


# Singleton pattern для провайдера (опционально)
_global_provider: Optional[BaseLLMProvider] = None


def get_global_provider() -> BaseLLMProvider:
    """
    Возвращает глобальный экземпляр провайдера (singleton).

    Returns:
        Глобальный BaseLLMProvider

    Example:
        # Первый вызов создает провайдер из config.yaml
        provider = get_global_provider()

        # Последующие вызовы возвращают тот же экземпляр
        same_provider = get_global_provider()
    """
    global _global_provider

    if _global_provider is None:
        _global_provider = create_llm_provider()

    return _global_provider


def reset_global_provider():
    """
    Сбрасывает глобальный провайдер (для тестирования).
    """
    global _global_provider
    _global_provider = None
