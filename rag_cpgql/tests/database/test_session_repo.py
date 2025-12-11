"""
Tests for Session Repository.

Tests for SessionRepository CRUD operations and dialogue turn management.
"""

import pytest
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import User, Session, DialogueTurn
from src.api.database.repositories.session_repo import SessionRepository


class TestSessionCreate:
    """Tests for SessionRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating a new session."""
        repo = SessionRepository(db_session)

        session = await repo.create(
            user_id=test_user.id,
            metadata={"scenario": "security"},
        )

        assert session is not None
        assert session.user_id == test_user.id
        assert session.session_metadata == {"scenario": "security"}
        assert session.id is not None

    @pytest.mark.asyncio
    async def test_create_session_without_metadata(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating session without metadata."""
        repo = SessionRepository(db_session)

        session = await repo.create(user_id=test_user.id)

        assert session is not None
        assert session.session_metadata == {}


class TestSessionGetById:
    """Tests for SessionRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test getting existing session by ID."""
        repo = SessionRepository(db_session)

        result = await repo.get_by_id(test_session.id)

        assert result is not None
        assert result.id == test_session.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent session."""
        repo = SessionRepository(db_session)

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_turns(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test getting session with dialogue turns loaded."""
        repo = SessionRepository(db_session)

        # Add some turns
        await repo.add_turn(test_session.id, "user", "Hello")
        await repo.add_turn(test_session.id, "assistant", "Hi there!")
        await db_session.commit()

        result = await repo.get_by_id(test_session.id, include_turns=True)

        assert result is not None
        assert len(result.dialogue_turns) == 2


class TestSessionGetByUser:
    """Tests for SessionRepository.get_by_user()."""

    @pytest.mark.asyncio
    async def test_get_by_user_success(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting sessions for a user."""
        repo = SessionRepository(db_session)

        # Create multiple sessions
        await repo.create(user_id=test_user.id)
        await repo.create(user_id=test_user.id)
        await repo.create(user_id=test_user.id)
        await db_session.commit()

        sessions = await repo.get_by_user(test_user.id)

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_by_user_with_limit(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting sessions with limit."""
        repo = SessionRepository(db_session)

        for _ in range(5):
            await repo.create(user_id=test_user.id)
        await db_session.commit()

        sessions = await repo.get_by_user(test_user.id, limit=2)

        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_get_by_user_empty(
        self,
        db_session: AsyncSession,
    ):
        """Test getting sessions for user with no sessions."""
        repo = SessionRepository(db_session)

        sessions = await repo.get_by_user(uuid.uuid4())

        assert sessions == []


class TestSessionCountByUser:
    """Tests for SessionRepository.count_by_user()."""

    @pytest.mark.asyncio
    async def test_count_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test counting sessions for a user."""
        repo = SessionRepository(db_session)

        for _ in range(5):
            await repo.create(user_id=test_user.id)
        await db_session.commit()

        count = await repo.count_by_user(test_user.id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_by_user_zero(
        self,
        db_session: AsyncSession,
    ):
        """Test counting sessions for user with none."""
        repo = SessionRepository(db_session)

        count = await repo.count_by_user(uuid.uuid4())

        assert count == 0


class TestSessionUpdate:
    """Tests for SessionRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_scenario(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test updating current scenario."""
        repo = SessionRepository(db_session)

        updated = await repo.update(
            test_session.id,
            current_scenario="security",
        )

        assert updated is not None
        assert updated.current_scenario == "security"

    @pytest.mark.asyncio
    async def test_update_metadata(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test updating metadata."""
        repo = SessionRepository(db_session)

        updated = await repo.update(
            test_session.id,
            metadata={"key": "value"},
        )

        assert updated is not None
        assert updated.session_metadata == {"key": "value"}


class TestSessionDelete:
    """Tests for SessionRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_existing(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting existing session."""
        repo = SessionRepository(db_session)
        session = await repo.create(user_id=test_user.id)
        await db_session.commit()

        result = await repo.delete(session.id)

        assert result is True

        # Verify deleted
        deleted = await repo.get_by_id(session.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting non-existent session."""
        repo = SessionRepository(db_session)

        result = await repo.delete(uuid.uuid4())

        assert result is False


class TestSessionDeleteByUser:
    """Tests for SessionRepository.delete_by_user()."""

    @pytest.mark.asyncio
    async def test_delete_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting all sessions for a user."""
        repo = SessionRepository(db_session)

        for _ in range(3):
            await repo.create(user_id=test_user.id)
        await db_session.commit()

        deleted_count = await repo.delete_by_user(test_user.id)

        assert deleted_count == 3

        # Verify all deleted
        remaining = await repo.get_by_user(test_user.id)
        assert len(remaining) == 0


class TestDialogueTurnAdd:
    """Tests for SessionRepository.add_turn()."""

    @pytest.mark.asyncio
    async def test_add_user_turn(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test adding a user turn."""
        repo = SessionRepository(db_session)

        turn = await repo.add_turn(
            session_id=test_session.id,
            role="user",
            content="What does malloc do?",
            scenario_id="onboarding",
        )

        assert turn is not None
        assert turn.role == "user"
        assert turn.content == "What does malloc do?"
        assert turn.session_id == test_session.id

    @pytest.mark.asyncio
    async def test_add_assistant_turn(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test adding an assistant turn."""
        repo = SessionRepository(db_session)

        turn = await repo.add_turn(
            session_id=test_session.id,
            role="assistant",
            content="malloc allocates memory...",
            metadata={"confidence": 0.95},
        )

        assert turn is not None
        assert turn.role == "assistant"
        assert turn.turn_metadata == {"confidence": 0.95}


class TestDialogueTurnGet:
    """Tests for SessionRepository.get_turns()."""

    @pytest.mark.asyncio
    async def test_get_turns_ordered(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test that turns are returned in chronological order."""
        repo = SessionRepository(db_session)

        await repo.add_turn(test_session.id, "user", "First message")
        await repo.add_turn(test_session.id, "assistant", "Second message")
        await repo.add_turn(test_session.id, "user", "Third message")
        await db_session.commit()

        turns = await repo.get_turns(test_session.id)

        assert len(turns) == 3
        assert turns[0].content == "First message"
        assert turns[1].content == "Second message"
        assert turns[2].content == "Third message"

    @pytest.mark.asyncio
    async def test_get_turns_with_limit(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test getting turns with limit."""
        repo = SessionRepository(db_session)

        for i in range(10):
            await repo.add_turn(test_session.id, "user", f"Message {i}")
        await db_session.commit()

        turns = await repo.get_turns(test_session.id, limit=5)

        assert len(turns) == 5


class TestDialogueTurnCount:
    """Tests for SessionRepository.count_turns()."""

    @pytest.mark.asyncio
    async def test_count_turns(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test counting turns in a session."""
        repo = SessionRepository(db_session)

        for i in range(5):
            await repo.add_turn(test_session.id, "user", f"Message {i}")
        await db_session.commit()

        count = await repo.count_turns(test_session.id)

        assert count == 5


class TestDialogueTurnClear:
    """Tests for SessionRepository.clear_turns()."""

    @pytest.mark.asyncio
    async def test_clear_turns(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test clearing all turns from a session."""
        repo = SessionRepository(db_session)

        for i in range(5):
            await repo.add_turn(test_session.id, "user", f"Message {i}")
        await db_session.commit()

        cleared = await repo.clear_turns(test_session.id)

        assert cleared == 5

        # Verify cleared
        count = await repo.count_turns(test_session.id)
        assert count == 0


class TestDialogueTurnRecent:
    """Tests for SessionRepository.get_recent_turns()."""

    @pytest.mark.asyncio
    async def test_get_recent_turns(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test getting recent turns for context."""
        repo = SessionRepository(db_session)

        for i in range(20):
            await repo.add_turn(test_session.id, "user", f"Message {i}")
        await db_session.commit()

        recent = await repo.get_recent_turns(test_session.id, count=5)

        assert len(recent) == 5
        # Should be the last 5 messages
        assert recent[0].content == "Message 15"
        assert recent[4].content == "Message 19"

    @pytest.mark.asyncio
    async def test_get_recent_turns_fewer_than_count(
        self,
        db_session: AsyncSession,
        test_session: Session,
    ):
        """Test getting recent turns when fewer exist than requested."""
        repo = SessionRepository(db_session)

        for i in range(3):
            await repo.add_turn(test_session.id, "user", f"Message {i}")
        await db_session.commit()

        recent = await repo.get_recent_turns(test_session.id, count=10)

        assert len(recent) == 3
