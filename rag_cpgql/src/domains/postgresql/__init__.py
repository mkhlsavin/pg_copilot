"""
PostgreSQL Domain Plugin.

Provides PostgreSQL-specific configurations for the RAG-CPGQL Copilot,
including subsystem definitions, prompts, and security patterns.
"""

from .plugin import PostgreSQLDomainPlugin

__all__ = ['PostgreSQLDomainPlugin']
