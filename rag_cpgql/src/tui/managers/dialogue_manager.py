"""Dialogue manager for multi-turn conversations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DialogueTurn:
    """Single turn in a conversation."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    scenario_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "scenario_id": self.scenario_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueTurn":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            scenario_id=data.get("scenario_id"),
            metadata=data.get("metadata"),
        )


class DialogueManager:
    """
    Manages multi-turn conversation state.

    Tracks conversation history, manages context for follow-up queries,
    and determines when to reclassify intent.
    """

    def __init__(self, max_context_turns: int = 10):
        """
        Initialize dialogue manager.

        Args:
            max_context_turns: Maximum turns to include in context
        """
        self.turns: List[DialogueTurn] = []
        self.current_scenario: Optional[str] = None
        self.max_context_turns = max_context_turns
        self._last_intent: Optional[str] = None

    def add_user_turn(
        self,
        content: str,
        scenario_id: Optional[str] = None,
    ) -> DialogueTurn:
        """
        Add user message to dialogue.

        Args:
            content: User's message
            scenario_id: Optional scenario for this turn

        Returns:
            Created DialogueTurn
        """
        turn = DialogueTurn(
            role="user",
            content=content,
            scenario_id=scenario_id or self.current_scenario,
        )
        self.turns.append(turn)
        logger.debug(f"Added user turn: {content[:50]}...")
        return turn

    def add_assistant_turn(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scenario_id: Optional[str] = None,
    ) -> DialogueTurn:
        """
        Add assistant response with metadata.

        Args:
            content: Assistant's response
            metadata: Optional metadata (intent, confidence, etc.)
            scenario_id: Optional scenario for this turn

        Returns:
            Created DialogueTurn
        """
        # Extract intent from metadata for tracking
        if metadata and "intent" in metadata:
            self._last_intent = metadata["intent"]

        turn = DialogueTurn(
            role="assistant",
            content=content,
            scenario_id=scenario_id or self.current_scenario,
            metadata=metadata,
        )
        self.turns.append(turn)
        logger.debug(f"Added assistant turn: {content[:50]}...")
        return turn

    def get_context_for_query(self) -> Dict[str, Any]:
        """
        Build context dict for MultiScenarioCopilot.

        Returns:
            Context dictionary with:
            - messages: List of recent message dicts
            - current_scenario: Current scenario ID
            - last_intent: Last classified intent
        """
        # Get recent turns
        recent_turns = self.turns[-self.max_context_turns:]

        # Convert to message format for LangChain
        messages = []
        for turn in recent_turns:
            messages.append({
                "role": turn.role,
                "content": turn.content,
            })

        return {
            "messages": messages,
            "current_scenario": self.current_scenario,
            "last_intent": self._last_intent,
            "turn_count": len(self.turns),
        }

    def should_reclassify_intent(self, query: str) -> bool:
        """
        Determine if new query needs intent reclassification.

        Returns True if:
        - First query (no history)
        - Explicit topic change indicators
        - Query is significantly different from current context

        Args:
            query: New user query

        Returns:
            True if intent should be reclassified
        """
        # First query always needs classification
        if not self.turns:
            return True

        # No current scenario means we need classification
        if not self.current_scenario:
            return True

        query_lower = query.lower()

        # Explicit topic change indicators
        change_indicators = [
            "new topic",
            "different question",
            "change to",
            "switch to",
            "let's talk about",
            "moving on",
            "another thing",
            "unrelated question",
        ]

        for indicator in change_indicators:
            if indicator in query_lower:
                return True

        # Scenario selection commands
        if query_lower.startswith("/select"):
            return True

        # Query too short to determine - keep current context
        if len(query.split()) < 3:
            return False

        # Otherwise, keep current context for follow-ups
        return False

    def set_scenario(self, scenario_id: str):
        """Set current scenario."""
        self.current_scenario = scenario_id
        logger.info(f"Set scenario to: {scenario_id}")

    def get_history(
        self,
        limit: Optional[int] = None,
        as_dicts: bool = True,
    ) -> List:
        """
        Get conversation history.

        Args:
            limit: Maximum turns to return
            as_dicts: Return as dictionaries (True) or DialogueTurn objects (False)

        Returns:
            List of turns
        """
        turns = self.turns[-limit:] if limit else self.turns

        if as_dicts:
            return [t.to_dict() for t in turns]
        return turns

    def clear(self):
        """Clear conversation history."""
        self.turns = []
        self.current_scenario = None
        self._last_intent = None
        logger.info("Cleared dialogue history")

    def get_last_user_query(self) -> Optional[str]:
        """Get the last user query."""
        for turn in reversed(self.turns):
            if turn.role == "user":
                return turn.content
        return None

    def get_last_response(self) -> Optional[str]:
        """Get the last assistant response."""
        for turn in reversed(self.turns):
            if turn.role == "assistant":
                return turn.content
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize dialogue state."""
        return {
            "turns": [t.to_dict() for t in self.turns],
            "current_scenario": self.current_scenario,
            "last_intent": self._last_intent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueManager":
        """Deserialize dialogue state."""
        manager = cls()
        manager.turns = [
            DialogueTurn.from_dict(t) for t in data.get("turns", [])
        ]
        manager.current_scenario = data.get("current_scenario")
        manager._last_intent = data.get("last_intent")
        return manager

    def __len__(self) -> int:
        return len(self.turns)
