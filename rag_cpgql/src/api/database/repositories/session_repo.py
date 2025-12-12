"""
Session Repository.

Provides data access for chat session operations.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.database.models import Session, DialogueTurn


class SessionRepository:
    """
    Session repository for database operations.

    Handles CRUD operations for chat sessions and dialogue turns.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Database session
        """
        self.db = session

    async def create(
        self,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: Owner user ID
            metadata: Session metadata

        Returns:
            Created session
        """
        session = Session(
            user_id=user_id,
            session_metadata=metadata or {},
        )

        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def get_by_id(
        self,
        session_id: UUID,
        include_turns: bool = False,
    ) -> Optional[Session]:
        """
        Get session by ID.

        Args:
            session_id: Session ID
            include_turns: Include dialogue turns

        Returns:
            Session or None
        """
        query = select(Session).where(Session.id == session_id)

        if include_turns:
            query = query.options(selectinload(Session.dialogue_turns))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """
        Get sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum sessions
            offset: Skip count

        Returns:
            List of sessions
        """
        query = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        """
        Count sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Session count
        """
        query = select(func.count(Session.id)).where(Session.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update(
        self,
        session_id: UUID,
        current_scenario: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Session]:
        """
        Update session.

        Args:
            session_id: Session ID
            current_scenario: Current scenario ID
            metadata: Updated metadata

        Returns:
            Updated session or None
        """
        updates = {"updated_at": datetime.now(UTC)}

        if current_scenario is not None:
            updates["current_scenario"] = current_scenario

        if metadata is not None:
            updates["session_metadata"] = metadata

        await self.db.execute(
            update(Session).where(Session.id == session_id).values(**updates)
        )

        return await self.get_by_id(session_id)

    async def delete(self, session_id: UUID) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted
        """
        result = await self.db.execute(
            delete(Session).where(Session.id == session_id)
        )
        return result.rowcount > 0

    async def delete_by_user(self, user_id: UUID) -> int:
        """
        Delete all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted sessions
        """
        result = await self.db.execute(
            delete(Session).where(Session.user_id == user_id)
        )
        return result.rowcount

    # Dialogue Turn operations

    async def add_turn(
        self,
        session_id: UUID,
        role: str,
        content: str,
        scenario_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DialogueTurn:
        """
        Add a dialogue turn to a session.

        Args:
            session_id: Session ID
            role: Turn role ('user' or 'assistant')
            content: Turn content
            scenario_id: Scenario ID
            metadata: Turn metadata

        Returns:
            Created turn
        """
        turn = DialogueTurn(
            session_id=session_id,
            role=role,
            content=content,
            scenario_id=scenario_id,
            turn_metadata=metadata,
        )

        self.db.add(turn)
        await self.db.flush()
        await self.db.refresh(turn)

        # Update session timestamp
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(updated_at=datetime.now(UTC))
        )

        return turn

    async def get_turns(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DialogueTurn]:
        """
        Get dialogue turns for a session.

        Args:
            session_id: Session ID
            limit: Maximum turns
            offset: Skip count

        Returns:
            List of turns (oldest first)
        """
        query = (
            select(DialogueTurn)
            .where(DialogueTurn.session_id == session_id)
            .order_by(DialogueTurn.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_turns(self, session_id: UUID) -> int:
        """
        Count turns in a session.

        Args:
            session_id: Session ID

        Returns:
            Turn count
        """
        query = select(func.count(DialogueTurn.id)).where(
            DialogueTurn.session_id == session_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def clear_turns(self, session_id: UUID) -> int:
        """
        Clear all turns from a session.

        Args:
            session_id: Session ID

        Returns:
            Number of deleted turns
        """
        result = await self.db.execute(
            delete(DialogueTurn).where(DialogueTurn.session_id == session_id)
        )
        return result.rowcount

    async def get_recent_turns(
        self,
        session_id: UUID,
        count: int = 10,
    ) -> List[DialogueTurn]:
        """
        Get most recent turns for context.

        Args:
            session_id: Session ID
            count: Number of recent turns

        Returns:
            List of recent turns (oldest first)
        """
        # Get total count
        total = await self.count_turns(session_id)

        # Calculate offset for recent turns
        offset = max(0, total - count)

        return await self.get_turns(session_id, limit=count, offset=offset)
