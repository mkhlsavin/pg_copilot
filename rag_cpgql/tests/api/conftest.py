"""
API Test Configuration and Fixtures.

Provides pytest fixtures for testing FastAPI endpoints.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.api.main import create_app
from src.api.database.models import Base, User, UserRole, AuthProvider
from src.api.database.connection import get_db
from src.api.auth.jwt_handler import create_access_token, create_refresh_token
from src.api.routers.auth import hash_password


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
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
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session for dependency injection.

    This fixture overrides the get_db dependency in FastAPI.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
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


@pytest.fixture(scope="function")
def app(test_engine):
    """Create a test FastAPI application."""
    from src.api.dependencies import get_current_active_user

    application = create_app()

    # Override database dependency
    async def override_get_db():
        session_factory = async_sessionmaker(
            bind=test_engine,
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

    # Override authentication dependency - return mock user for all tests
    async def override_get_current_active_user():
        # Return a mock authenticated user for tests
        return User(
            id=uuid.uuid4(),
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password",
            auth_provider=AuthProvider.LOCAL,
            role=UserRole.ANALYST,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_current_active_user] = override_get_current_active_user

    yield application

    application.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def test_client(client) -> Generator[TestClient, None, None]:
    """Alias for client fixture (backwards compatibility)."""
    yield client


@pytest_asyncio.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_user(test_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_user(test_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def inactive_user(test_session: AsyncSession) -> User:
    """Create an inactive test user."""
    user = User(
        id=uuid.uuid4(),
        username="inactive",
        email="inactive@example.com",
        password_hash=hash_password("inactivepassword123"),
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ANALYST,
        is_active=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """Create authorization headers for a test user."""
    access_token = create_access_token(
        user_id=str(test_user.id),
        scopes=["scenarios:read", "query:execute"],
        role=test_user.role.value,
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(admin_user: User) -> dict:
    """Create authorization headers for an admin user."""
    access_token = create_access_token(
        user_id=str(admin_user.id),
        scopes=["scenarios:read", "query:execute", "admin:all"],
        role=admin_user.role.value,
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def refresh_token_fixture(test_user: User) -> str:
    """Create a refresh token for a test user."""
    return create_refresh_token(user_id=str(test_user.id))


# API URL prefix
API_V1_PREFIX = "/api/v1"


@pytest.fixture(scope="function")
def api_prefix() -> str:
    """Return the API v1 prefix."""
    return API_V1_PREFIX


@pytest.fixture(scope="function")
def app_no_auth(test_engine):
    """Create a test FastAPI application WITHOUT auth override.

    Use this fixture for testing unauthenticated request behavior.
    """
    application = create_app()

    # Override only database dependency, NOT auth
    async def override_get_db():
        session_factory = async_sessionmaker(
            bind=test_engine,
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

    application.dependency_overrides[get_db] = override_get_db

    yield application

    application.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client_no_auth(app_no_auth) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client WITHOUT auth override.

    Use this for testing endpoints that should return 401 without credentials.
    """
    transport = ASGITransport(app=app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
