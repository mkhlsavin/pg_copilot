"""
Database Test Configuration and Fixtures.

Provides pytest fixtures for testing database repositories.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.api.database.models import (
    Base,
    User,
    UserRole,
    AuthProvider,
    Session,
    DialogueTurn,
    ApiKey,
)


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    admin = User(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        password_hash="hashed_password",
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture(scope="function")
async def test_session(db_session: AsyncSession, test_user: User) -> Session:
    """Create a test chat session."""
    session = Session(
        id=uuid.uuid4(),
        user_id=test_user.id,
        current_scenario="onboarding",
        metadata={"test": True},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture(scope="function")
async def test_api_key(db_session: AsyncSession, test_user: User) -> ApiKey:
    """Create a test API key."""
    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Test Key",
        key_hash="hashed_key_value",
        prefix="sk_test",
        scopes=["scenarios:read", "query:execute"],
        is_revoked=False,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key


@pytest_asyncio.fixture(scope="function")
async def expired_api_key(db_session: AsyncSession, test_user: User) -> ApiKey:
    """Create an expired API key."""
    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Expired Key",
        key_hash="expired_key_hash",
        prefix="sk_exp",
        scopes=["scenarios:read"],
        is_revoked=False,
        created_at=datetime.now(UTC) - timedelta(days=60),
        expires_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key
