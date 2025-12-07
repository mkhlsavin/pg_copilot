"""Status bar component for TUI."""

from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME


class StatusBar:
    """Bottom status bar with session and system info."""

    def __init__(self, theme: Theme = DEFAULT_THEME):
        self.theme = theme
        self.session_id: Optional[str] = None
        self.current_scenario: Optional[str] = None
        self.message_count: int = 0
        self.last_activity: Optional[datetime] = None
        self.is_processing: bool = False
        self.status_message: str = ""

    def update(
        self,
        session_id: Optional[str] = None,
        scenario: Optional[str] = None,
        message_count: Optional[int] = None,
        is_processing: bool = False,
        status_message: str = "",
    ):
        """Update status bar values."""
        if session_id is not None:
            self.session_id = session_id
        if scenario is not None:
            self.current_scenario = scenario
        if message_count is not None:
            self.message_count = message_count
        self.is_processing = is_processing
        self.status_message = status_message
        self.last_activity = datetime.now()

    def render(self) -> Text:
        """Render status bar as a single line."""
        text = Text()

        # Session indicator
        text.append(" ", style="on blue")
        if self.session_id:
            text.append(f" Session: {self.session_id[:8]}... ", style="white on blue")
        else:
            text.append(" New Session ", style="dim white on blue")

        # Scenario indicator
        text.append(" ", style="on cyan")
        if self.current_scenario:
            text.append(f" S{self.current_scenario} ", style="white on cyan")
        else:
            text.append(" No Scenario ", style="dim white on cyan")

        # Message count
        text.append(" ", style="on green")
        text.append(f" Msgs: {self.message_count} ", style="white on green")

        # Processing indicator
        if self.is_processing:
            text.append(" ", style="on yellow")
            text.append(" Processing... ", style="black on yellow")
        elif self.status_message:
            text.append(" ", style="on dim")
            text.append(f" {self.status_message} ", style="dim")

        # Time
        if self.last_activity:
            time_str = self.last_activity.strftime("%H:%M:%S")
            text.append(f" [{time_str}]", style="dim")

        return text

    def render_panel(self) -> Panel:
        """Render status bar as a panel."""
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="center", ratio=2)
        table.add_column(justify="right", ratio=1)

        # Left: Session
        left = Text()
        if self.session_id:
            left.append(f"Session: {self.session_id[:12]}", style="cyan")
        else:
            left.append("New Session", style="dim")

        # Center: Scenario and status
        center = Text()
        if self.current_scenario:
            center.append(f"Scenario {self.current_scenario}", style="green")
        if self.is_processing:
            center.append(" | Processing...", style="yellow")
        elif self.status_message:
            center.append(f" | {self.status_message}", style="dim")

        # Right: Message count and time
        right = Text()
        right.append(f"Messages: {self.message_count}", style="blue")
        if self.last_activity:
            right.append(f" | {self.last_activity.strftime('%H:%M')}", style="dim")

        table.add_row(left, center, right)

        return Panel(
            table,
            border_style="dim",
            padding=(0, 1),
        )
