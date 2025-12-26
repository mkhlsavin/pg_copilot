"""
Pytest fixtures for Leads service tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import StaticPool, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import Settings, get_settings
from src.database.connection import get_db
from src.database.models import Base
from src.main import app

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        leads_api_key="test-api-key",
        telegram_bot_token="",
        telegram_chat_id="",
        smtp_user="",
        smtp_password="",
        admin_email="",
        environment="test",
    )


@pytest_asyncio.fixture
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def override_get_db(async_session: AsyncSession):
    """Override database dependency."""

    async def _override():
        yield async_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_lead_data() -> dict:
    """Sample lead data for tests."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "company": "Test Company",
        "position": "Developer",
        "team_size": "11-50",
        "language": "python",
    }


@pytest.fixture
def mock_telegram_notifier():
    """Mock Telegram notifier."""
    mock = MagicMock()
    mock.enabled = False
    mock.send_new_lead_notification = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_email_notifier():
    """Mock Email notifier."""
    mock = MagicMock()
    mock.enabled = False
    mock.send_new_lead_notification = AsyncMock(return_value=True)
    return mock
