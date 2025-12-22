"""Session persistence using JSON files."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default sessions directory
DEFAULT_SESSIONS_DIR = Path("sessions")


class SessionStore:
    """
    JSON-based session persistence.

    Stores sessions as individual JSON files in a directory.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize session store.

        Args:
            base_dir: Directory for session files
        """
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_SESSIONS_DIR
        self._ensure_dir()

    def _ensure_dir(self):
        """Ensure sessions directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get path for a session file."""
        return self.base_dir / f"{session_id}.json"

    def save(
        self,
        session: "Session",
        path: Optional[Path] = None,
    ) -> str:
        """
        Save session to JSON file.

        Args:
            session: Session object to save
            path: Optional custom path

        Returns:
            Session ID
        """
        from ..managers.session_manager import Session

        file_path = path or self._get_session_path(session.session_id)

        try:
            data = session.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved session to: {file_path}")
            return session.session_id

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise

    def load(self, session_id: str) -> Optional["Session"]:
        """
        Load session from JSON file.

        Args:
            session_id: Session ID to load

        Returns:
            Session object or None if not found
        """
        from ..managers.session_manager import Session

        file_path = self._get_session_path(session_id)

        if not file_path.exists():
            # Try without extension
            file_path = self.base_dir / session_id
            if not file_path.exists():
                logger.warning(f"Session not found: {session_id}")
                return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = Session.from_dict(data)
            logger.debug(f"Loaded session from: {file_path}")
            return session

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def list_sessions(self) -> List["SessionSummary"]:
        """
        List all saved sessions.

        Returns:
            List of SessionSummary objects
        """
        from ..managers.session_manager import SessionSummary

        summaries = []

        for file_path in self.base_dir.glob("session_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                summary = SessionSummary(
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    message_count=len(data.get("dialogues", [])),
                    current_scenario=data.get("current_scenario"),
                )
                summaries.append(summary)

            except Exception as e:
                logger.warning(f"Failed to read session file {file_path}: {e}")

        # Sort by updated_at descending
        summaries.sort(key=lambda s: s.updated_at, reverse=True)

        return summaries

    def delete(self, session_id: str) -> bool:
        """
        Delete a session file.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_session_path(session_id)

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.debug(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def export_session(
        self,
        session_id: str,
        output_path: Path,
        format: str = "json",
    ) -> bool:
        """
        Export session to a custom location.

        Args:
            session_id: Session to export
            output_path: Destination path
            format: Export format (json, markdown)

        Returns:
            True if exported successfully
        """
        session = self.load(session_id)
        if not session:
            return False

        try:
            if format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

            elif format == "markdown":
                md_content = self._session_to_markdown(session)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md_content)

            else:
                logger.error(f"Unknown export format: {format}")
                return False

            logger.info(f"Exported session to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def _session_to_markdown(self, session) -> str:
        """Convert session to markdown format."""
        lines = [
            f"# Session: {session.session_id}",
            "",
            f"Created: {session.created_at.isoformat()}",
            f"Updated: {session.updated_at.isoformat()}",
            f"Messages: {len(session.dialogues)}",
            "",
            "---",
            "",
        ]

        for turn in session.dialogues:
            role = "**You**" if turn.role == "user" else "**Assistant**"
            time_str = turn.timestamp.strftime("%H:%M:%S")

            lines.append(f"### {role} ({time_str})")
            if turn.scenario_id:
                lines.append(f"*Scenario: {turn.scenario_id}*")
            lines.append("")
            lines.append(turn.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
