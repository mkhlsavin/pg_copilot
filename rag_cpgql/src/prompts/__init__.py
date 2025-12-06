"""
Prompts Module - Централизованное управление промптами

Модуль для работы с промптами системы:
- PromptRegistry: Централизованный реестр промптов
- Domain-specific промпты (PostgreSQL, Linux Kernel, LLVM)
- Template rendering с подстановкой переменных

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025
"""

from .prompt_registry import (
    Prompt,
    PromptRegistry,
    get_global_registry,
    set_global_registry,
    reset_global_registry
)

__all__ = [
    'Prompt',
    'PromptRegistry',
    'get_global_registry',
    'set_global_registry',
    'reset_global_registry'
]
