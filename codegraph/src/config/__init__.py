"""
Configuration Module

Unified configuration management for the CodeGraph system.

Components:
- UnifiedConfig: Single entry point for all configuration
- CPGConfig: CPG domain configuration

Usage:
    from src.config import get_unified_config

    config = get_unified_config()
    provider = config.llm.provider

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

from .unified_config import (
    UnifiedConfig,
    LLMSettings,
    APISettings,
    RetrievalSettings,
    CPGSettings,
    TimeoutSettings,
    LimitSettings,
    get_unified_config,
    reset_unified_config,
)

from .cpg_config import (
    CPGConfig,
    CPGDomainInfo,
    get_global_cpg_config,
    set_global_cpg_config,
    reset_global_cpg_config
)

__all__ = [
    # Unified Config (recommended)
    'UnifiedConfig',
    'LLMSettings',
    'APISettings',
    'RetrievalSettings',
    'CPGSettings',
    'TimeoutSettings',
    'LimitSettings',
    'get_unified_config',
    'reset_unified_config',
    # CPG Config
    'CPGConfig',
    'CPGDomainInfo',
    'get_global_cpg_config',
    'set_global_cpg_config',
    'reset_global_cpg_config',
]
