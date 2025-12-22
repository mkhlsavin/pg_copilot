"""
Tests for History Router.

Tests for GET /history/{session_id}, POST /history/{session_id}/export,
DELETE /history/{session_id}/clear
"""

import pytest
import uuid
from datetime import datetime

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User, Session, DialogueTurn
from tests.api.conftest import API_V1_PREFIX


class TestGetHistoryEndpoint:
    """Tests for GET /history/{session_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting dialogue history."""
        # Create session with turns
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        # Add turns
        for i, (role, content) in enumerate([
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "How are you?"),
        ]):
            turn = DialogueTurn(
                session_id=session.id,
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
            )
            test_session.add(turn)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session.id)
        assert data["total_turns"] == 3
        assert len(data["turns"]) == 3
        assert data["turns"][0]["role"] == "user"
        assert data["turns"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting history for session with no turns."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_turns"] == 0
        assert data["turns"] == []

    @pytest.mark.asyncio
    async def test_get_history_pagination(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test history pagination."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        # Add 10 turns
        for i in range(10):
            turn = DialogueTurn(
                session_id=session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.utcnow(),
            )
            test_session.add(turn)
        await test_session.commit()

        # Page 1 with 3 items
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
            params={"page": 1, "page_size": 3},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["turns"]) == 3
        assert data["total_turns"] == 10
        assert data["page"] == 1
        assert data["has_more"] is True

    @pytest.mark.asyncio
    async def test_get_history_with_metadata(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting history with metadata included."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        turn = DialogueTurn(
            session_id=session.id,
            role="user",
            content="Test",
            timestamp=datetime.utcnow(),
            turn_metadata={"tokens": 100},
        )
        test_session.add(turn)
        await test_session.commit()

        # Without metadata
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
            params={"include_metadata": False},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["turns"][0]["metadata"] is None

        # With metadata
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
            params={"include_metadata": True},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["turns"][0]["metadata"] == {"tokens": 100}

    @pytest.mark.asyncio
    async def test_get_history_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting history for non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_history_invalid_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting history with invalid session ID."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/invalid-id",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_history_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test getting another user's history."""
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestExportHistoryEndpoint:
    """Tests for POST /history/{session_id}/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_history_json(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test exporting history as JSON."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        turn = DialogueTurn(
            session_id=session.id,
            role="user",
            content="Test message",
            timestamp=datetime.utcnow(),
        )
        test_session.add(turn)
        await test_session.commit()

        response = await async_client.post(
            f"{API_V1_PREFIX}/history/{session.id}/export",
            headers=auth_headers,
            params={"format": "json"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_history_markdown(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test exporting history as Markdown."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        turn = DialogueTurn(
            session_id=session.id,
            role="user",
            content="Test message",
            timestamp=datetime.utcnow(),
        )
        test_session.add(turn)
        await test_session.commit()

        response = await async_client.post(
            f"{API_V1_PREFIX}/history/{session.id}/export",
            headers=auth_headers,
            params={"format": "markdown"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/markdown" in response.headers["content-type"]
        assert ".md" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_history_default_format(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test exporting history with default format (JSON)."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.post(
            f"{API_V1_PREFIX}/history/{session.id}/export",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_history_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test exporting history for non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"{API_V1_PREFIX}/history/{fake_id}/export",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_export_history_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test exporting another user's history."""
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.post(
            f"{API_V1_PREFIX}/history/{session.id}/export",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestClearHistoryEndpoint:
    """Tests for DELETE /history/{session_id}/clear endpoint."""

    @pytest.mark.asyncio
    async def test_clear_history_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test clearing dialogue history."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.flush()

        # Add turns
        for i in range(5):
            turn = DialogueTurn(
                session_id=session.id,
                role="user",
                content=f"Message {i}",
                timestamp=datetime.utcnow(),
            )
            test_session.add(turn)
        await test_session.commit()

        # Clear history
        response = await async_client.delete(
            f"{API_V1_PREFIX}/history/{session.id}/clear",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify history is cleared
        response = await async_client.get(
            f"{API_V1_PREFIX}/history/{session.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total_turns"] == 0

        # Session should still exist
        response = await async_client.get(
            f"{API_V1_PREFIX}/sessions/{session.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_clear_history_already_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test clearing already empty history."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.delete(
            f"{API_V1_PREFIX}/history/{session.id}/clear",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_clear_history_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test clearing history for non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"{API_V1_PREFIX}/history/{fake_id}/clear",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clear_history_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        test_session,
    ):
        """Test clearing another user's history."""
        session = Session(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client.delete(
            f"{API_V1_PREFIX}/history/{session.id}/clear",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_clear_history_unauthenticated(
        self,
        async_client_no_auth: AsyncClient,
        test_user: User,
        test_session,
    ):
        """Test clearing history without authentication."""
        session = Session(
            id=uuid.uuid4(),
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(session)
        await test_session.commit()

        response = await async_client_no_auth.delete(
            f"{API_V1_PREFIX}/history/{session.id}/clear",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
