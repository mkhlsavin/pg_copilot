"""Session management panel for TUI."""

import json
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class SessionPanel:
    """Panel for managing chat sessions."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize SessionPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    def render_help(self) -> Panel:
        """Render session command help."""
        content = Text()
        content.append("/session ", style="bold cyan")
        content.append("[subcommand]\n\n", style="yellow")
        content.append("Subcommands:\n", style="bold")
        content.append("  list                  - List all sessions\n")
        content.append("  switch <id>           - Switch to a session\n")
        content.append("  export <id> [format]  - Export session history\n")
        content.append("  delete <id>           - Delete a session\n")
        content.append("\n")
        content.append("Export formats: ", style="bold")
        content.append("json, md (markdown)\n", style="dim")

        return Panel(
            content,
            title="[bold]Session Management[/bold]",
            border_style=self.theme.border,
        )

    async def list_sessions(self, page: int = 1, page_size: int = 20) -> Panel:
        """List all chat sessions."""
        try:
            data = await self.api_client.list_sessions(page=page, page_size=page_size)
            sessions = data.get("items", data.get("sessions", []))

            if not sessions:
                return Panel(
                    "[dim]No sessions found[/dim]",
                    title="Sessions",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("ID", style="cyan", width=14)
            table.add_column("Scenario")
            table.add_column("Messages", justify="right")
            table.add_column("Updated", style="dim")

            for session in sessions:
                session_id = session.get("id", session.get("session_id", ""))
                scenario = session.get("current_scenario", session.get("scenario_id", "-")) or "-"
                turn_count = session.get("turn_count", session.get("message_count", 0))
                updated = session.get("updated_at", session.get("created_at", "-"))

                if updated and len(updated) > 16:
                    updated = updated[:16]

                table.add_row(
                    session_id[:14] + "..." if len(session_id) > 14 else session_id,
                    scenario,
                    str(turn_count),
                    updated,
                )

            # Pagination info
            total = data.get("total", len(sessions))
            current_page = data.get("page", page)
            subtitle = f"Page {current_page}"

            return Panel(
                table,
                title=f"[bold]Sessions ({total})[/bold]",
                subtitle=subtitle,
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing sessions: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def export_session(
        self, session_id: str, format: str = "json"
    ) -> Panel:
        """Export session history to file."""
        try:
            session = await self.api_client.get_session(session_id)

            if format.lower() == "md":
                content = self._format_markdown(session)
                ext = "md"
            else:
                content = json.dumps(session, indent=2, default=str)
                ext = "json"

            # Generate filename
            short_id = session_id[:8]
            filename = f"session_{short_id}.{ext}"

            # Save to file
            Path(filename).write_text(content, encoding="utf-8")

            # Count messages
            turns = session.get("dialogue_turns", session.get("history", []))
            message_count = len(turns)

            return Panel(
                f"[green]Session exported successfully[/green]\n\n"
                f"File: [cyan]{filename}[/cyan]\n"
                f"Format: {ext.upper()}\n"
                f"Messages: {message_count}",
                title="Session Exported",
                border_style="green",
            )

        except Exception as e:
            return Panel(
                f"[red]Error exporting session: {e}[/red]",
                title="Error",
                border_style="red",
            )

    def _format_markdown(self, session: dict) -> str:
        """Format session as Markdown."""
        lines = [
            "# Session Export",
            "",
            f"**Session ID:** {session.get('id', session.get('session_id', 'Unknown'))}",
            f"**Created:** {session.get('created_at', 'Unknown')}",
            f"**Updated:** {session.get('updated_at', 'Unknown')}",
            f"**Scenario:** {session.get('current_scenario', 'None')}",
            "",
            "---",
            "",
            "## Dialogue History",
            "",
        ]

        turns = session.get("dialogue_turns", session.get("history", []))

        for i, turn in enumerate(turns, 1):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", "")

            if timestamp and len(timestamp) > 16:
                timestamp = timestamp[:16]

            if role == "user":
                lines.append(f"### User ({timestamp})")
            else:
                lines.append(f"### Assistant ({timestamp})")

            lines.append("")
            lines.append(content)
            lines.append("")

        # Add metadata if present
        metadata = session.get("metadata")
        if metadata:
            lines.extend([
                "---",
                "",
                "## Metadata",
                "",
                "```json",
                json.dumps(metadata, indent=2, default=str),
                "```",
            ])

        return "\n".join(lines)

    async def delete_session(self, session_id: str) -> Panel:
        """Delete a chat session."""
        try:
            success = await self.api_client.delete_session(session_id)

            if success:
                return Panel(
                    f"[green]Session deleted[/green]\n\n"
                    f"Session ID: [dim]{session_id}[/dim]",
                    title="Session Deleted",
                    border_style="green",
                )
            else:
                return Panel(
                    f"[red]Failed to delete session[/red]",
                    title="Error",
                    border_style="red",
                )

        except Exception as e:
            return Panel(
                f"[red]Error deleting session: {e}[/red]",
                title="Error",
                border_style="red",
            )
