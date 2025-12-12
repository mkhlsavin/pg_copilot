"""
Database Connection Module.

Provides async PostgreSQL connection pool using SQLAlchemy 2.0 and asyncpg.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool

from src.api.config import get_database_config, DatabaseConfig

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(config: Optional[DatabaseConfig] = None) -> AsyncEngine:
    """
    Get or create the async database engine.

    Args:
        config: Database configuration. If None, uses default from settings.

    Returns:
        AsyncEngine instance.
    """
    global _engine

    if _engine is None:
        if config is None:
            config = get_database_config()

        _engine = create_async_engine(
            config.url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            future=True,
        )
        logger.info(f"Database engine created: {config.url.split('@')[-1]}")

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.

    Returns:
        Async session factory.
    """
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _async_session_factory


# Alias for convenience
AsyncSessionLocal = get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession instance.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(...)

    Yields:
        AsyncSession instance.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(config: Optional[DatabaseConfig] = None) -> None:
    """
    Initialize database connection and create tables if needed.

    Args:
        config: Database configuration. If None, uses default from settings.
    """
    from src.api.database.models import Base

    engine = get_engine(config)

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database connections and dispose engine."""
    global _engine, _async_session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connections closed")


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if connection is healthy, False otherwise.
    """
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


class DatabaseHealthCheck:
    """Database health check for monitoring."""

    @staticmethod
    async def check() -> dict:
        """
        Perform database health check.

        Returns:
            Dict with status and details.
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()

            return {
                "status": "healthy",
                "database": "postgresql",
                "version": version,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "postgresql",
                "error": str(e),
            }
