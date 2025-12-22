"""
Environment Variable Loader

Утилита для загрузки переменных окружения из .env файла.
Поддерживает автоматический поиск .env в корне проекта.

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def find_env_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Ищет .env файл начиная с заданной директории и двигаясь вверх.

    Args:
        start_path: Стартовая директория (если None, используется текущая)

    Returns:
        Path к .env файлу или None если не найден

    Example:
        env_path = find_env_file()
        if env_path:
            print(f"Found .env: {env_path}")
    """
    if start_path is None:
        start_path = Path.cwd()
    elif not isinstance(start_path, Path):
        start_path = Path(start_path)

    current = start_path.resolve()

    # Ищем .env двигаясь вверх по директориям
    while True:
        env_file = current / ".env"
        if env_file.exists():
            logger.debug(f"Found .env file: {env_file}")
            return env_file

        # Проверяем родительскую директорию
        parent = current.parent
        if parent == current:
            # Достигли корня файловой системы
            break
        current = parent

    logger.debug("No .env file found")
    return None


def load_env_file(env_path: Optional[Path] = None, override: bool = False) -> Dict[str, str]:
    """
    Загружает переменные из .env файла.

    Args:
        env_path: Путь к .env файлу (если None, ищет автоматически)
        override: Переопределять существующие переменные окружения (default: False)

    Returns:
        Dictionary с загруженными переменными

    Example:
        # Загрузить из автоматически найденного .env
        env_vars = load_env_file()

        # Загрузить из конкретного файла
        env_vars = load_env_file(Path("/path/to/.env"))

        # Переопределить существующие переменные
        env_vars = load_env_file(override=True)
    """
    if env_path is None:
        env_path = find_env_file()

    if env_path is None:
        logger.info("No .env file found, using system environment variables")
        return {}

    if not env_path.exists():
        logger.warning(f".env file not found: {env_path}")
        return {}

    logger.info(f"Loading environment variables from: {env_path}")

    loaded_vars = {}

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue

                # Парсим KEY=VALUE
                if '=' not in line:
                    logger.warning(f"Invalid line in .env (line {line_num}): {line}")
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Удаляем кавычки если есть
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Устанавливаем переменную окружения
                if override or key not in os.environ:
                    os.environ[key] = value
                    loaded_vars[key] = value
                    logger.debug(f"Loaded: {key}")
                else:
                    logger.debug(f"Skipped (already set): {key}")

        logger.info(f"Loaded {len(loaded_vars)} environment variables from .env")
        return loaded_vars

    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return {}


def get_env(
    key: str,
    default: Optional[str] = None,
    required: bool = False
) -> Optional[str]:
    """
    Получает значение переменной окружения с опциональным default значением.

    Args:
        key: Имя переменной
        default: Значение по умолчанию если переменная не установлена
        required: Если True, выбрасывает исключение если переменная не найдена

    Returns:
        Значение переменной или default

    Raises:
        ValueError: Если required=True и переменная не найдена

    Example:
        # С default значением
        api_key = get_env("API_KEY", default="default_key")

        # Обязательная переменная
        credentials = get_env("GIGACHAT_CREDENTIALS", required=True)
    """
    value = os.getenv(key, default)

    if required and value is None:
        raise ValueError(f"Required environment variable not set: {key}")

    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Получает boolean значение из переменной окружения.

    Поддерживаемые значения:
    - True: "true", "1", "yes", "on" (case-insensitive)
    - False: "false", "0", "no", "off" или отсутствие переменной

    Args:
        key: Имя переменной
        default: Значение по умолчанию

    Returns:
        Boolean значение

    Example:
        debug_mode = get_env_bool("DEBUG", default=False)
        use_gpu = get_env_bool("USE_GPU", default=True)
    """
    value = os.getenv(key)

    if value is None:
        return default

    value_lower = value.lower()

    if value_lower in ("true", "1", "yes", "on"):
        return True
    elif value_lower in ("false", "0", "no", "off"):
        return False
    else:
        logger.warning(
            f"Invalid boolean value for {key}: '{value}'. "
            f"Expected: true/false/1/0/yes/no/on/off. Using default: {default}"
        )
        return default


def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """
    Получает integer значение из переменной окружения.

    Args:
        key: Имя переменной
        default: Значение по умолчанию

    Returns:
        Integer значение или default

    Example:
        port = get_env_int("PORT", default=8080)
        timeout = get_env_int("TIMEOUT", default=30)
    """
    value = os.getenv(key)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning(
            f"Invalid integer value for {key}: '{value}'. Using default: {default}"
        )
        return default


def get_env_float(key: str, default: Optional[float] = None) -> Optional[float]:
    """
    Получает float значение из переменной окружения.

    Args:
        key: Имя переменной
        default: Значение по умолчанию

    Returns:
        Float значение или default

    Example:
        temperature = get_env_float("LLM_TEMPERATURE", default=0.7)
        threshold = get_env_float("THRESHOLD", default=0.5)
    """
    value = os.getenv(key)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        logger.warning(
            f"Invalid float value for {key}: '{value}'. Using default: {default}"
        )
        return default


def list_env_vars(prefix: Optional[str] = None) -> Dict[str, str]:
    """
    Возвращает словарь всех переменных окружения (опционально с префиксом).

    Args:
        prefix: Фильтр по префиксу (например, "GIGACHAT_")

    Returns:
        Dictionary с переменными окружения

    Example:
        # Все переменные
        all_vars = list_env_vars()

        # Только GigaChat переменные
        gigachat_vars = list_env_vars(prefix="GIGACHAT_")
    """
    if prefix is None:
        return dict(os.environ)

    return {
        key: value
        for key, value in os.environ.items()
        if key.startswith(prefix)
    }


# Автоматическая загрузка .env при импорте модуля
def auto_load_dotenv():
    """
    Автоматически загружает .env файл при импорте модуля.

    Вызывается автоматически при первом импорте env_loader.
    """
    try:
        from dotenv import load_dotenv
        # Используем python-dotenv если установлен
        env_path = find_env_file()
        if env_path:
            load_dotenv(env_path)
            logger.info(f"Loaded .env with python-dotenv: {env_path}")
    except ImportError:
        # Используем нашу реализацию если python-dotenv не установлен
        load_env_file()


# Автоматическая загрузка при импорте (можно отключить)
AUTO_LOAD_ENV = os.getenv("AUTO_LOAD_ENV", "true").lower() in ("true", "1", "yes")

if AUTO_LOAD_ENV:
    try:
        auto_load_dotenv()
    except Exception as e:
        logger.debug(f"Could not auto-load .env: {e}")
