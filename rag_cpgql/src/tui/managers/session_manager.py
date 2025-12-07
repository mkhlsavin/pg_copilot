"""Session manager for TUI state persistence."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import uuid

from .dialogue_manager import DialogueManager, DialogueTurn

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    """Brief session summary for listing."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    current_scenario: Optional[str] = None

    @classmethod
    def from_session(cls, session: "Session") -> "SessionSummary":
        return cls(
            session_id=session.session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.dialogues),
            current_scenario=session.current_scenario,
        )


@dataclass
class Session:
    """Session state container."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    dialogues: List[DialogueTurn] = field(default_factory=list)
    current_scenario: Optional[str] = None
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "dialogues": [d.to_dict() for d in self.dialogues],
            "current_scenario": self.current_scenario,
            "config_overrides": self.config_overrides,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Deserialize session from dictionary."""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            dialogues=[
                DialogueTurn.from_dict(d) for d in data.get("dialogues", [])
            ],
            current_scenario=data.get("current_scenario"),
            config_overrides=data.get("config_overrides", {}),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """
    Manages session lifecycle and persistence.

    Features:
    - Create new sessions with unique IDs
    - Save/load sessions to/from storage
    - Auto-save on changes
    - Session listing and browsing
    """

    def __init__(
        self,
        store: Optional["SessionStore"] = None,
        auto_save: bool = True,
    ):
        """
        Initialize session manager.

        Args:
            store: Optional persistence store
            auto_save: Whether to auto-save on changes
        """
        # Import here to avoid circular import
        from ..persistence.session_store import SessionStore

        self.store = store or SessionStore()
        self.auto_save = auto_save
        self.current_session: Optional[Session] = None
        self._dialogue_manager: Optional[DialogueManager] = None

    def new_session(self, metadata: Optional[Dict] = None) -> Session:
        """
        Create a new session.

        Args:
            metadata: Optional session metadata

        Returns:
            New Session object
        """
        session_id = self._generate_session_id()
        now = datetime.now()

        self.current_session = Session(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        # Create fresh dialogue manager
        self._dialogue_manager = DialogueManager()

        logger.info(f"Created new session: {session_id}")
        return self.current_session

    def save_session(self, path: Optional[Path] = None) -> str:
        """
        Save current session to storage.

        Args:
            path: Optional custom path

        Returns:
            Session ID that was saved
        """
        if not self.current_session:
            raise ValueError("No active session to save")

        # Sync dialogue state
        if self._dialogue_manager:
            self.current_session.dialogues = self._dialogue_manager.turns.copy()
            self.current_session.current_scenario = self._dialogue_manager.current_scenario

        # Update timestamp
        self.current_session.updated_at = datetime.now()

        # Save
        session_id = self.store.save(self.current_session, path)
        logger.info(f"Saved session: {session_id}")

        return session_id

    def load_session(self, session_id: str) -> Session:
        """
        Load session from storage.

        Args:
            session_id: ID of session to load

        Returns:
            Loaded Session object
        """
        session = self.store.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        self.current_session = session

        # Restore dialogue manager
        self._dialogue_manager = DialogueManager()
        self._dialogue_manager.turns = session.dialogues.copy()
        self._dialogue_manager.current_scenario = session.current_scenario

        logger.info(f"Loaded session: {session_id}")
        return session

    def list_sessions(self) -> List[SessionSummary]:
        """List all saved sessions."""
        return self.store.list_sessions()

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a saved session.

        Args:
            session_id: ID of session to delete

        Returns:
            True if deleted, False if not found
        """
        result = self.store.delete(session_id)
        if result:
            logger.info(f"Deleted session: {session_id}")
        return result

    def get_dialogue_manager(self) -> DialogueManager:
        """Get the dialogue manager for current session."""
        if not self._dialogue_manager:
            self._dialogue_manager = DialogueManager()
        return self._dialogue_manager

    def add_user_message(self, content: str) -> DialogueTurn:
        """Add user message and optionally auto-save."""
        dm = self.get_dialogue_manager()
        turn = dm.add_user_turn(content)

        if self.auto_save and self.current_session:
            self._sync_and_save()

        return turn

    def add_assistant_message(
        self,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> DialogueTurn:
        """Add assistant message and optionally auto-save."""
        dm = self.get_dialogue_manager()
        turn = dm.add_assistant_turn(content, metadata)

        if self.auto_save and self.current_session:
            self._sync_and_save()

        return turn

    def set_scenario(self, scenario_id: str):
        """Set current scenario."""
        dm = self.get_dialogue_manager()
        dm.set_scenario(scenario_id)

        if self.current_session:
            self.current_session.current_scenario = scenario_id

    def get_session_info(self) -> Optional[Dict]:
        """Get current session info."""
        if not self.current_session:
            return None

        return {
            "session_id": self.current_session.session_id,
            "created_at": self.current_session.created_at.isoformat(),
            "updated_at": self.current_session.updated_at.isoformat(),
            "message_count": len(self.current_session.dialogues),
            "current_scenario": self.current_session.current_scenario,
        }

    def _sync_and_save(self):
        """Sync dialogue state and save session."""
        if self._dialogue_manager and self.current_session:
            self.current_session.dialogues = self._dialogue_manager.turns.copy()
            self.current_session.current_scenario = self._dialogue_manager.current_scenario
            self.current_session.updated_at = datetime.now()
            try:
                self.store.save(self.current_session)
            except Exception as e:
                logger.warning(f"Auto-save failed: {e}")

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"session_{timestamp}_{short_uuid}"
