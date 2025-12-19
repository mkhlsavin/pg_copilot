"""
Domain Plugin System for CodeGraph Copilot.

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
from .python_django.plugin import PythonDjangoPlugin

# NOTE: generic_cpp is now a package (directory) instead of a single file.
# The import above still works because generic_cpp/__init__.py exports the same symbols.

# Create plugin instances
postgresql_plugin = PostgreSQLDomainPlugin()
python_django_plugin = PythonDjangoPlugin()

# Auto-register available plugins
DomainRegistry.register(generic_cpp_plugin)
DomainRegistry.register(postgresql_plugin)
DomainRegistry.register(python_django_plugin)

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
    'PythonDjangoPlugin',
    'python_django_plugin',
]
