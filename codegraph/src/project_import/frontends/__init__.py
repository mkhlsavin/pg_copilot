"""
Joern Language Frontends Module.

Configuration and utilities for all supported Joern language frontends.
"""

from .registry import (
    JoernFrontend,
    FRONTENDS,
    EXTENSION_TO_LANGUAGE,
    detect_language,
    detect_language_with_stats,
    get_frontend,
    get_frontend_command_path,
    get_exclude_patterns,
    is_binary_language,
    list_supported_languages,
)

__all__ = [
    "JoernFrontend",
    "FRONTENDS",
    "EXTENSION_TO_LANGUAGE",
    "detect_language",
    "detect_language_with_stats",
    "get_frontend",
    "get_frontend_command_path",
    "get_exclude_patterns",
    "is_binary_language",
    "list_supported_languages",
]
