"""
Configuration Module

Управление конфигурацией системы:
- CPGConfig: Конфигурация CPG domain
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

__all__ = [
    'CPGConfig',
    'CPGDomainInfo',
    'get_global_cpg_config',
    'set_global_cpg_config',
    'reset_global_cpg_config'
]
