"""
Generic C/C++ Domain Plugin.

Provides domain-specific configurations for analyzing generic C/C++ codebases.
This plugin covers common C/C++ patterns, security vulnerabilities, and
D3FEND hardening checks.
"""

from .plugin import GenericCppDomainPlugin, generic_cpp_plugin

__all__ = [
    "GenericCppDomainPlugin",
    "generic_cpp_plugin",
]
