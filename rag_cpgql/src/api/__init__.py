"""
RAG-CPGQL REST API Package.

This package provides a FastAPI-based REST API for the RAG-CPGQL code analysis system,
exposing all 16 analysis scenarios, patch review functionality, and integrations.

Features:
- JWT and API Key authentication
- OAuth2/OIDC and LDAP/AD integration
- Rate limiting with configurable limits per endpoint
- Structured request/response logging
- Audit logging for security events
- Session and dialogue history persistence (PostgreSQL)
- WebSocket support for real-time chat and job updates
- All 16 TUI analysis scenarios
- Patch review for git diffs, GitHub PRs, GitLab MRs
"""

__version__ = "1.0.0"

from src.api.main import create_app

__all__ = ["create_app", "__version__"]
