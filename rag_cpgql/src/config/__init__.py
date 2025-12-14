"""
Configuration Module

Unified configuration management for the RAG-CPGQL system.

Components:
- UnifiedConfig: Single entry point for all configuration
- CPGConfig: CPG domain configuration
- JoernConfig: Joern server configuration

Usage:
    from src.config import get_unified_config

    config = get_unified_config()
    endpoint = config.joern.endpoint
    provider = config.llm.provider

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

from .unified_config import (
    UnifiedConfig,
    JoernSettings,
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

from .joern_config import (
    get_joern_endpoint,
    get_joern_home,
    get_joern_cpg_path,
    get_joern_source_path,
    clear_config_cache
)

__all__ = [
    # Unified Config (recommended)
    'UnifiedConfig',
    'JoernSettings',
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
    # Joern Config (legacy, use UnifiedConfig.joern instead)
    'get_joern_endpoint',
    'get_joern_home',
    'get_joern_cpg_path',
    'get_joern_source_path',
    'clear_config_cache',
]
