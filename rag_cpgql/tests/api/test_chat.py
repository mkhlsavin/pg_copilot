"""
Tests for Chat Router.

Tests for POST /chat, POST /chat/stream, GET /chat/scenarios, GET /chat/scenarios/{id}
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User, Session
from tests.api.conftest import API_V1_PREFIX


class TestChatEndpoint:
    """Tests for POST /chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful chat request."""
        # Mock the chat service
        mock_result = MagicMock()
        mock_result.answer = "This function handles memory allocation."
        mock_result.scenario_id = "security"
        mock_result.confidence = 0.85
        mock_result.evidence = []
        mock_result.processing_time_ms = 150.5
        mock_result.metadata = {}

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.process_query = AsyncMock(return_value=mock_result)

            response = await async_client.post(
                f"{API_V1_PREFIX}/chat",
                headers=auth_headers,
                json={
                    "query": "What does the malloc function do?",
                    "language": "en",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
        assert "scenario_id" in data
        assert "confidence" in data
        assert "session_id" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_chat_with_session(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test chat request with existing session."""
        # Create session
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        mock_result = MagicMock()
        mock_result.answer = "Test answer"
        mock_result.scenario_id = "onboarding"
        mock_result.confidence = 0.9
        mock_result.evidence = []
        mock_result.processing_time_ms = 100.0
        mock_result.metadata = {}

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.process_query = AsyncMock(return_value=mock_result)

            response = await async_client.post(
                f"{API_V1_PREFIX}/chat",
                headers=auth_headers,
                json={
                    "query": "Explain the main function",
                    "session_id": str(session.id),
                    "language": "en",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session.id)

    @pytest.mark.asyncio
    async def test_chat_with_scenario(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test chat request with specific scenario."""
        mock_result = MagicMock()
        mock_result.answer = "Found 3 potential SQL injection vulnerabilities."
        mock_result.scenario_id = "security"
        mock_result.confidence = 0.95
        mock_result.evidence = []
        mock_result.processing_time_ms = 200.0
        mock_result.metadata = {}

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.process_query = AsyncMock(return_value=mock_result)

            response = await async_client.post(
                f"{API_V1_PREFIX}/chat",
                headers=auth_headers,
                json={
                    "query": "Find SQL injection vulnerabilities",
                    "scenario_id": "security",
                    "language": "en",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["scenario_id"] == "security"

    @pytest.mark.asyncio
    async def test_chat_empty_query(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test chat with empty query."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/chat",
            headers=auth_headers,
            json={
                "query": "",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_chat_invalid_language(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test chat with invalid language code."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/chat",
            headers=auth_headers,
            json={
                "query": "Test query",
                "language": "invalid",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_chat_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test chat without authentication."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/chat",
            json={
                "query": "Test query",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChatStreamEndpoint:
    """Tests for POST /chat/stream endpoint."""

    @pytest.mark.asyncio
    async def test_chat_stream_returns_sse(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that streaming endpoint returns SSE response."""
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "start", "session_id": "test"}\n\n'
            yield 'data: {"type": "chunk", "content": "Hello"}\n\n'
            yield 'data: {"type": "end", "session_id": "test"}\n\n'

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.process_query_stream = mock_stream

            response = await async_client.post(
                f"{API_V1_PREFIX}/chat/stream",
                headers=auth_headers,
                json={
                    "query": "Test streaming query",
                    "language": "en",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_chat_stream_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test streaming chat without authentication."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/chat/stream",
            json={
                "query": "Test query",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChatScenariosEndpoint:
    """Tests for GET /chat/scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_list_scenarios(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test listing chat scenarios."""
        mock_scenarios = [
            {"id": "security", "name": "Security Audit"},
            {"id": "onboarding", "name": "Onboarding"},
        ]

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.get_available_scenarios.return_value = mock_scenarios

            response = await async_client.get(
                f"{API_V1_PREFIX}/chat/scenarios",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_scenarios_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test listing scenarios without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/chat/scenarios")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetScenarioEndpoint:
    """Tests for GET /chat/scenarios/{scenario_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting specific scenario."""
        mock_scenario = {
            "id": "security",
            "name": "Security Audit",
            "description": "Find security vulnerabilities",
        }

        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.get_scenario_info.return_value = mock_scenario

            response = await async_client.get(
                f"{API_V1_PREFIX}/chat/scenarios/security",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "security"

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting non-existent scenario."""
        with patch("src.api.routers.chat.get_chat_service") as mock_service:
            mock_service.return_value.get_scenario_info.return_value = None

            response = await async_client.get(
                f"{API_V1_PREFIX}/chat/scenarios/nonexistent",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_scenario_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test getting scenario without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/chat/scenarios/security")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
