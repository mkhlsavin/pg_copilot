"""
Tests for Sessions Router.

Tests for GET /sessions, POST /sessions, GET /sessions/{id},
DELETE /sessions/{id}, PATCH /sessions/{id}
"""

import pytest
import uuid
from datetime import datetime

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User, Session, DialogueTurn
from tests.api.conftest import API_V1_PREFIX


class TestListSessionsEndpoint:
    """Tests for GET /sessions endpoint."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test listing sessions when none exist."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["has_next"] is False
        assert data["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test listing sessions with existing data."""
        # Create a session
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            current_scenario="security",
            session_metadata={"project": "test"},
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["current_scenario"] == "security"

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test session list pagination."""
        # Create multiple sessions
        for i in range(5):
            session = Session(
                id=uuid.uuid4(),
                user_id=test_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                session_metadata={"index": i},
            )
            test_session.add(session)
        await test_session.commit()

        # Request page 1 with 2 items
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["has_next"] is True
        assert data["has_prev"] is False

        # Request page 2
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
            params={"page": 2, "page_size": 2},
        )

        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_next"] is True
        assert data["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_sessions_unauthenticated(self, async_client_no_auth: AsyncClient):
        """Test listing sessions without authentication."""
        response = await async_client_no_auth.get(f"{API_V1_PREFIX}/sessions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_sessions_only_own(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test that users only see their own sessions."""
        # Create session for admin user
        admin_session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(admin_session)

        # Create session for test user
        test_user_session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(test_user_session)
        await test_session.commit()

        # Request with test_user credentials
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(test_user_session.id)


class TestCreateSessionEndpoint:
    """Tests for POST /sessions endpoint."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful session creation."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
            json={"metadata": {"project": "test-project"}},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["metadata"]["project"] == "test-project"
        assert data["turn_count"] == 0

    @pytest.mark.asyncio
    async def test_create_session_empty_metadata(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test session creation with empty metadata."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/sessions",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["metadata"] == {}

    @pytest.mark.asyncio
    async def test_create_session_unauthenticated(self, async_client_no_auth: AsyncClient):
        """Test session creation without authentication."""
        response = await async_client_no_auth.post(
            f"{API_V1_PREFIX}/sessions",
            json={},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetSessionEndpoint:
    """Tests for GET /sessions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_session_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting session details."""
        # Create session with turns
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            current_scenario="security",
        )
        test_session.add(session)
        await test_session.flush()

        # Add dialogue turn
        turn = DialogueTurn(
            session_id=session.id,
            role="user",
            content="Test message",
            timestamp=datetime.utcnow(),
        )
        test_session.add(turn)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(session.id)
        assert data["current_scenario"] == "security"
        assert len(data["dialogue_turns"]) == 1
        assert data["dialogue_turns"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_invalid_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting session with invalid ID format."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/invalid-id",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_session_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting another user's session."""
        # Create session for admin
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        # Try to access with test_user credentials
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteSessionEndpoint:
    """Tests for DELETE /sessions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_session_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test successful session deletion."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.delete(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_session_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test deleting non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"{API_V1_PREFIX}/sessions/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_session_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test deleting another user's session."""
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.delete(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateSessionEndpoint:
    """Tests for PATCH /sessions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_session_scenario(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test updating session scenario."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.patch(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
            json={"current_scenario": "debugging"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_scenario"] == "debugging"

    @pytest.mark.asyncio
    async def test_update_session_metadata(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test updating session metadata."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            session_metadata={"old_key": "old_value"},
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.patch(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
            json={"metadata": {"new_key": "new_value"}},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "new_key" in data["metadata"]

    @pytest.mark.asyncio
    async def test_update_session_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test updating non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"{API_V1_PREFIX}/sessions/{fake_id}",
            headers=auth_headers,
            json={"current_scenario": "test"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_session_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test updating another user's session."""
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.patch(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
            json={"current_scenario": "test"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
