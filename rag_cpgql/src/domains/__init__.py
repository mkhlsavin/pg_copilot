"""
Domain Plugin System for RAG-CPGQL Copilot.

This module provides a plugin architecture for supporting different code domains
(PostgreSQL, Linux Kernel, LLVM, etc.) in a unified way.

Usage:
    from src.domains import DomainRegistry, get_active_domain

    # Activate a domain
    DomainRegistry.activate('postgresql')

    # Get the active domain plugin
    domain = get_active_domain()
    subsystems = domain.subsystems
    prompts = domain.get_prompts()
"""

from .base import DomainPlugin
from .registry import DomainRegistry, get_active_domain, register_domain
from .generic_cpp import GenericCppDomainPlugin, generic_cpp_plugin
from .postgresql.plugin import PostgreSQLDomainPlugin

# Create plugin instances
postgresql_plugin = PostgreSQLDomainPlugin()

# Auto-register available plugins
DomainRegistry.register(generic_cpp_plugin)
DomainRegistry.register(postgresql_plugin)

# Activate PostgreSQL as default (since this is a PostgreSQL-focused project)
DomainRegistry.activate('postgresql')

__all__ = [
    'DomainPlugin',
    'DomainRegistry',
    'get_active_domain',
    'register_domain',
    'GenericCppDomainPlugin',
    'generic_cpp_plugin',
    'PostgreSQLDomainPlugin',
    'postgresql_plugin',
]
