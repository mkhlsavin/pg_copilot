"""Dialogue display panel for conversation history."""

from typing import List, Optional
from datetime import datetime
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

from ..utils.themes import Theme, DEFAULT_THEME


class DialoguePanel:
    """Panel for displaying conversation history."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        max_display_turns: int = 10
    ):
        self.theme = theme
        self.max_display_turns = max_display_turns

    def render_turn(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        scenario_id: Optional[str] = None,
        is_latest: bool = False,
    ) -> Panel:
        """
        Render a single conversation turn.

        Args:
            role: 'user' or 'assistant'
            content: Message content
            timestamp: When the message was sent
            scenario_id: Associated scenario
            is_latest: Whether this is the most recent message

        Returns:
            Rich Panel with formatted message
        """
        if role == "user":
            style = self.theme.user_message
            title = "You"
            border_style = "green"
        else:
            style = self.theme.assistant_message
            title = "Assistant"
            border_style = "blue"

        # Add timestamp if available
        if timestamp:
            time_str = timestamp.strftime("%H:%M")
            title = f"{title} [{time_str}]"

        # Add scenario indicator
        if scenario_id:
            title = f"{title} (S{scenario_id})"

        # Format content - try markdown for assistant
        if role == "assistant" and len(content) > 100:
            formatted_content = Markdown(content)
        else:
            formatted_content = Text(content, style=style)

        return Panel(
            formatted_content,
            title=f"[bold]{title}[/bold]",
            border_style=border_style if is_latest else "dim",
            expand=True,
        )

    def render_history(
        self,
        turns: List[dict],
        console: Optional[Console] = None,
    ) -> List[RenderableType]:
        """
        Render conversation history.

        Args:
            turns: List of dialogue turns
            console: Optional console for output

        Returns:
            List of renderable panels
        """
        # Take only recent turns
        display_turns = turns[-self.max_display_turns:]

        panels = []
        for i, turn in enumerate(display_turns):
            is_latest = i == len(display_turns) - 1
            panel = self.render_turn(
                role=turn.get("role", "user"),
                content=turn.get("content", ""),
                timestamp=turn.get("timestamp"),
                scenario_id=turn.get("scenario_id"),
                is_latest=is_latest,
            )
            panels.append(panel)

        # Add indicator if history was truncated
        if len(turns) > self.max_display_turns:
            truncated = len(turns) - self.max_display_turns
            panels.insert(0, Text(
                f"... ({truncated} earlier messages hidden)",
                style="dim"
            ))

        return panels

    def render_summary(self, turns: List[dict]) -> Panel:
        """Render a summary of the conversation."""
        if not turns:
            return Panel(
                "[dim]No conversation history[/dim]",
                title="History",
                border_style="dim",
            )

        content = Text()

        # Count by role
        user_count = sum(1 for t in turns if t.get("role") == "user")
        assistant_count = len(turns) - user_count

        content.append(f"Messages: {len(turns)}\n", style="bold")
        content.append(f"  User: {user_count}\n", style="green")
        content.append(f"  Assistant: {assistant_count}\n", style="blue")

        # Unique scenarios used
        scenarios = set(t.get("scenario_id") for t in turns if t.get("scenario_id"))
        if scenarios:
            content.append(f"\nScenarios used: {', '.join(sorted(scenarios))}\n", style="cyan")

        # First and last message times
        if turns:
            first = turns[0].get("timestamp")
            last = turns[-1].get("timestamp")
            if first and last:
                content.append(f"\nStarted: {first.strftime('%Y-%m-%d %H:%M')}\n", style="dim")
                content.append(f"Latest: {last.strftime('%Y-%m-%d %H:%M')}\n", style="dim")

        return Panel(
            content,
            title="[bold]Session Summary[/bold]",
            border_style=self.theme.border,
        )
