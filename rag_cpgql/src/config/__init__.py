"""
Configuration Module

Управление конфигурацией системы:
- CPGConfig: Конфигурация CPG domain
- JoernConfig: Конфигурация Joern сервера
- Интеграция с PromptRegistry

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025
"""

from .cpg_config import (
    CPGConfig,
    CPGDomainInfo,
    get_global_cpg_config,
    set_global_cpg_config,
    reset_global_cpg_config
)

from .joern_config import (
    get_joern_endpoint,
    get_joern_home,
    get_joern_cpg_path,
    get_joern_source_path,
    clear_config_cache
)

__all__ = [
    # CPG Config
    'CPGConfig',
    'CPGDomainInfo',
    'get_global_cpg_config',
    'set_global_cpg_config',
    'reset_global_cpg_config',
    # Joern Config
    'get_joern_endpoint',
    'get_joern_home',
    'get_joern_cpg_path',
    'get_joern_source_path',
    'clear_config_cache',
]
