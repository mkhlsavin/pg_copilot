"""
Domain Plugin System for CodeGraph Copilot.

This module provides a plugin architecture for supporting different code domains
(PostgreSQL, Python/Django, JavaScript, Go, Ruby, C#, Kotlin, Swift, etc.) in a unified way.

Usage:
    from src.domains import DomainRegistry, get_active_domain

    # Activate a domain
    DomainRegistry.activate('postgresql')

    # Get the active domain plugin
    domain = get_active_domain()
    subsystems = domain.subsystems
    prompts = domain.get_prompts()

Available domains:
    - postgresql: PostgreSQL database source code
    - python_django: Python/Django web applications
    - generic_cpp: Generic C/C++ projects
    - javascript: JavaScript/TypeScript (Node.js, React, Vue)
    - go: Go backend services
    - ruby: Ruby/Rails applications
    - csharp: C#/.NET applications
    - kotlin: Kotlin/Android applications
    - swift: Swift/iOS applications
"""

from .base import DomainPlugin
from .registry import DomainRegistry, get_active_domain, register_domain
from .generic_cpp import GenericCppDomainPlugin, generic_cpp_plugin
from .postgresql.plugin import PostgreSQLDomainPlugin
from .python_django.plugin import PythonDjangoPlugin
from .javascript.plugin import JavaScriptPlugin
from .go.plugin import GoPlugin
from .ruby.plugin import RubyPlugin
from .csharp.plugin import CSharpPlugin
from .kotlin.plugin import KotlinPlugin
from .swift.plugin import SwiftPlugin

# NOTE: generic_cpp is now a package (directory) instead of a single file.
# The import above still works because generic_cpp/__init__.py exports the same symbols.

# Create plugin instances
postgresql_plugin = PostgreSQLDomainPlugin()
python_django_plugin = PythonDjangoPlugin()
javascript_plugin = JavaScriptPlugin()
go_plugin = GoPlugin()
ruby_plugin = RubyPlugin()
csharp_plugin = CSharpPlugin()
kotlin_plugin = KotlinPlugin()
swift_plugin = SwiftPlugin()

# Auto-register available plugins
DomainRegistry.register(generic_cpp_plugin)
DomainRegistry.register(postgresql_plugin)
DomainRegistry.register(python_django_plugin)
DomainRegistry.register(javascript_plugin)
DomainRegistry.register(go_plugin)
DomainRegistry.register(ruby_plugin)
DomainRegistry.register(csharp_plugin)
DomainRegistry.register(kotlin_plugin)
DomainRegistry.register(swift_plugin)

# Activate PostgreSQL as default (since this is a PostgreSQL-focused project)
DomainRegistry.activate('postgresql')

__all__ = [
    'DomainPlugin',
    'DomainRegistry',
    'get_active_domain',
    'register_domain',
    # C/C++
    'GenericCppDomainPlugin',
    'generic_cpp_plugin',
    # PostgreSQL
    'PostgreSQLDomainPlugin',
    'postgresql_plugin',
    # Python/Django
    'PythonDjangoPlugin',
    'python_django_plugin',
    # JavaScript/TypeScript
    'JavaScriptPlugin',
    'javascript_plugin',
    # Go
    'GoPlugin',
    'go_plugin',
    # Ruby/Rails
    'RubyPlugin',
    'ruby_plugin',
    # C#/.NET
    'CSharpPlugin',
    'csharp_plugin',
    # Kotlin/Android
    'KotlinPlugin',
    'kotlin_plugin',
    # Swift/iOS
    'SwiftPlugin',
    'swift_plugin',
]
