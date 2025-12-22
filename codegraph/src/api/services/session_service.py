"""
Session Service Module.

Provides business logic for session management.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.api.database.repositories.session_repo import SessionRepository
from src.api.database.models import Session, DialogueTurn


class SessionSummary:
    """Summary of a session for listing."""

    def __init__(
        self,
        id: UUID,
        created_at: datetime,
        updated_at: datetime,
        current_scenario: Optional[str],
        turn_count: int,
        metadata: Dict[str, Any],
    ):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.current_scenario = current_scenario
        self.turn_count = turn_count
        self.metadata = metadata


class SessionService:
    """
    Session management service.

    Provides high-level operations for managing chat sessions.
    """

    def __init__(self, session_repo: SessionRepository):
        """
        Initialize the session service.

        Args:
            session_repo: Session repository
        """
        self.repo = session_repo

    async def create_session(
        self,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session for a user.

        Args:
            user_id: User ID
            metadata: Session metadata

        Returns:
            Created session
        """
        return await self.repo.create(
            user_id=user_id,
            metadata=metadata,
        )

    async def get_session(
        self,
        user_id: UUID,
        session_id: UUID,
        include_turns: bool = False,
    ) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            include_turns: Include dialogue turns

        Returns:
            Session or None
        """
        session = await self.repo.get_by_id(session_id, include_turns=include_turns)

        # Verify ownership
        if session and session.user_id != user_id:
            return None

        return session

    async def list_sessions(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SessionSummary]:
        """
        List sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum sessions
            offset: Skip count

        Returns:
            List of session summaries
        """
        sessions = await self.repo.get_by_user(user_id, limit=limit, offset=offset)

        summaries = []
        for session in sessions:
            turn_count = await self.repo.count_turns(session.id)
            summaries.append(
                SessionSummary(
                    id=session.id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    current_scenario=session.current_scenario,
                    turn_count=turn_count,
                    metadata=session.metadata or {},
                )
            )

        return summaries

    async def count_sessions(self, user_id: UUID) -> int:
        """
        Count sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Session count
        """
        return await self.repo.count_by_user(user_id)

    async def update_session(
        self,
        user_id: UUID,
        session_id: UUID,
        current_scenario: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Session]:
        """
        Update session metadata.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            current_scenario: Current scenario ID
            metadata: Updated metadata

        Returns:
            Updated session or None
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.repo.update(
            session_id=session_id,
            current_scenario=current_scenario,
            metadata=metadata,
        )

    async def delete_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> bool:
        """
        Delete a session.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID

        Returns:
            True if deleted
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return False

        return await self.repo.delete(session_id)

    async def add_turn(
        self,
        user_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        scenario_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DialogueTurn]:
        """
        Add a dialogue turn to a session.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            role: Turn role ('user' or 'assistant')
            content: Turn content
            scenario_id: Scenario ID
            metadata: Turn metadata

        Returns:
            Created turn or None
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.repo.add_turn(
            session_id=session_id,
            role=role,
            content=content,
            scenario_id=scenario_id,
            metadata=metadata,
        )

    async def get_history(
        self,
        user_id: UUID,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[List[DialogueTurn]]:
        """
        Get dialogue history for a session.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            limit: Maximum turns
            offset: Skip count

        Returns:
            List of turns or None
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.repo.get_turns(session_id, limit=limit, offset=offset)

    async def get_recent_context(
        self,
        user_id: UUID,
        session_id: UUID,
        count: int = 10,
    ) -> Optional[List[DialogueTurn]]:
        """
        Get recent dialogue context for a session.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            count: Number of recent turns

        Returns:
            List of recent turns or None
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.repo.get_recent_turns(session_id, count=count)

    async def clear_history(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> Optional[int]:
        """
        Clear dialogue history for a session.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID

        Returns:
            Number of deleted turns or None
        """
        # Verify ownership
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.repo.clear_turns(session_id)

    async def export_session(
        self,
        user_id: UUID,
        session_id: UUID,
        format: str = "json",
    ) -> Optional[bytes]:
        """
        Export session data.

        Args:
            user_id: User ID (for authorization)
            session_id: Session ID
            format: Export format ('json' or 'markdown')

        Returns:
            Exported data or None
        """
        # Get session with turns
        session = await self.get_session(user_id, session_id, include_turns=True)
        if not session:
            return None

        turns = await self.repo.get_turns(session_id)

        if format == "json":
            return self._export_json(session, turns)
        elif format == "markdown":
            return self._export_markdown(session, turns)
        else:
            return None

    def _export_json(
        self,
        session: Session,
        turns: List[DialogueTurn],
    ) -> bytes:
        """Export session as JSON."""
        data = {
            "session_id": str(session.id),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "current_scenario": session.current_scenario,
            "metadata": session.metadata or {},
            "turns": [
                {
                    "id": turn.id,
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "scenario_id": turn.scenario_id,
                    "metadata": turn.metadata or {},
                }
                for turn in turns
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    def _export_markdown(
        self,
        session: Session,
        turns: List[DialogueTurn],
    ) -> bytes:
        """Export session as Markdown."""
        lines = [
            f"# Session Export",
            "",
            f"**Session ID:** {session.id}",
            f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Last Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Dialogue",
            "",
        ]

        for turn in turns:
            role_label = "**User:**" if turn.role == "user" else "**Assistant:**"
            timestamp = turn.timestamp.strftime("%H:%M:%S")
            lines.append(f"### {role_label} ({timestamp})")
            if turn.scenario_id:
                lines.append(f"*Scenario: {turn.scenario_id}*")
            lines.append("")
            lines.append(turn.content)
            lines.append("")

        return "\n".join(lines).encode("utf-8")
