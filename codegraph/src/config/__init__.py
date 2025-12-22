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
    # Backward compatibility
    'get_joern_endpoint',
    'get_joern_cpg_path',
    'get_joern_source_path',
]


# =============================================================================
# Backward Compatibility Functions
# =============================================================================
# These functions are kept for backward compatibility.
# New code should use UnifiedConfig directly:
#   config = get_unified_config()
#   endpoint = config.joern.endpoint
# =============================================================================

def get_joern_endpoint() -> str:
    """
    Get Joern server endpoint (backward compatibility).

    Returns:
        str: Joern endpoint in format "host:port"
    """
    config = get_unified_config()
    return config.joern.endpoint


def get_joern_cpg_path() -> str:
    """
    Get CPG file path (backward compatibility).

    Returns:
        str: Path to CPG file or empty string if not configured
    """
    config = get_unified_config()
    if config.joern.cpg_path:
        return str(config.joern.cpg_path)
    return ""


def get_joern_source_path() -> str:
    """
    Get source code path (backward compatibility).

    Returns:
        str: Path to source code or empty string if not configured
    """
    config = get_unified_config()
    if config.joern.source_path:
        return str(config.joern.source_path)
    return ""
