"""
Database Package.

Provides PostgreSQL database connectivity, SQLAlchemy models, and repositories.
"""

from src.api.database.connection import (
    get_db,
    get_db_session,
    init_db,
    close_db,
    AsyncSessionLocal,
)
from src.api.database.models import (
    Base,
    User,
    ApiKey,
    Session,
    DialogueTurn,
    BackgroundJob,
    TokenBlacklist,
    AuditLog,
)

__all__ = [
    "get_db",
    "get_db_session",
    "init_db",
    "close_db",
    "AsyncSessionLocal",
    "Base",
    "User",
    "ApiKey",
    "Session",
    "DialogueTurn",
    "BackgroundJob",
    "TokenBlacklist",
    "AuditLog",
]
