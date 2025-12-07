"""Progress display component for workflow visualization."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table
from rich.text import Text
from rich.spinner import Spinner

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)


class WorkflowStep:
    """Represents a step in workflow execution."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status: str = "pending"  # pending, running, complete, failed
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.details: Dict[str, Any] = {}

    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None

    def start(self):
        """Mark step as started."""
        self.status = "running"
        self.start_time = datetime.now()

    def complete(self, details: Optional[Dict] = None):
        """Mark step as complete."""
        self.status = "complete"
        self.end_time = datetime.now()
        if details:
            self.details.update(details)

    def fail(self, error: Optional[str] = None):
        """Mark step as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        if error:
            self.details["error"] = error


class ProgressDisplay:
    """
    Real-time workflow progress visualization.

    Extends existing ProgressTracker concepts with TUI-specific features:
    - Rich Live display integration
    - SQL query preview
    - LLM call indicators
    - Workflow step tracking
    """

    def __init__(
        self,
        console: Console,
        theme: Theme = DEFAULT_THEME,
    ):
        """
        Initialize progress display.

        Args:
            console: Rich Console for output
            theme: Color theme
        """
        self.console = console
        self.theme = theme

        # Workflow tracking
        self.steps: List[WorkflowStep] = []
        self.current_step: Optional[WorkflowStep] = None

        # Live display
        self._live: Optional[Live] = None
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None

        # Query tracking
        self.last_sql_query: Optional[str] = None
        self.sql_row_count: Optional[int] = None

        # LLM tracking
        self.llm_calls: int = 0
        self.llm_tokens: int = 0

    def start_live(self):
        """Start live display context."""
        if self._live:
            return

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )

        self._task_id = self._progress.add_task("Processing...", total=100)
        self._live = Live(
            self._render_progress(),
            console=self.console,
            refresh_per_second=4,
        )
        self._live.start()

    def stop_live(self):
        """Stop live display."""
        if self._live:
            self._live.stop()
            self._live = None
            self._progress = None
            self._task_id = None

    def add_step(self, name: str, description: str = "") -> WorkflowStep:
        """Add a workflow step."""
        step = WorkflowStep(name, description)
        self.steps.append(step)
        return step

    def start_step(self, name: str, description: str = ""):
        """Start a workflow step."""
        step = self.add_step(name, description)
        step.start()
        self.current_step = step

        if self._live:
            self._update_live(f"Running: {name}")

        logger.debug(f"Started step: {name}")

    def complete_step(self, details: Optional[Dict] = None):
        """Complete current step."""
        if self.current_step:
            self.current_step.complete(details)
            logger.debug(f"Completed step: {self.current_step.name}")
            self.current_step = None

            if self._live:
                self._update_live("Step complete")

    def fail_step(self, error: Optional[str] = None):
        """Mark current step as failed."""
        if self.current_step:
            self.current_step.fail(error)
            logger.debug(f"Failed step: {self.current_step.name}")
            self.current_step = None

            if self._live:
                self._update_live(f"Error: {error or 'Unknown'}")

    def update_sql(self, query: str, row_count: Optional[int] = None):
        """Update SQL query info."""
        self.last_sql_query = query
        self.sql_row_count = row_count

        if self._live:
            self._update_live(f"SQL: {row_count or '?'} rows")

    def update_llm(self, tokens: int = 0):
        """Update LLM call info."""
        self.llm_calls += 1
        self.llm_tokens += tokens

        if self._live:
            self._update_live(f"LLM call #{self.llm_calls}")

    def set_progress(self, percentage: float, message: str = ""):
        """Set progress percentage (0-100)."""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=percentage,
                description=message or "Processing...",
            )

    def _update_live(self, message: str):
        """Update live display."""
        if self._live:
            self._live.update(self._render_progress(message))

    def _render_progress(self, message: str = "") -> RenderableType:
        """Render progress panel."""
        content = Table.grid(padding=1)
        content.add_column()
        content.add_column(justify="right")

        # Current step
        if self.current_step:
            status_icon = "[yellow]>[/yellow]" if self.current_step.status == "running" else "[dim]>[/dim]"
            content.add_row(
                f"{status_icon} {self.current_step.name}",
                f"[dim]{self.current_step.duration or 0:.1f}s[/dim]",
            )

        # SQL info
        if self.last_sql_query:
            query_preview = self.last_sql_query[:50] + "..." if len(self.last_sql_query) > 50 else self.last_sql_query
            content.add_row(
                f"[cyan]SQL:[/cyan] {query_preview}",
                f"[dim]{self.sql_row_count or '?'} rows[/dim]",
            )

        # LLM info
        if self.llm_calls > 0:
            content.add_row(
                f"[blue]LLM:[/blue] {self.llm_calls} calls",
                f"[dim]{self.llm_tokens} tokens[/dim]",
            )

        # Message
        if message:
            content.add_row(f"[dim]{message}[/dim]", "")

        return Panel(
            content,
            title="[bold]Progress[/bold]",
            border_style=self.theme.progress_bar,
        )

    def render_summary(self) -> Panel:
        """Render execution summary."""
        if not self.steps:
            return Panel("[dim]No steps executed[/dim]", title="Summary")

        table = Table(
            show_header=True,
            header_style="bold",
            border_style=self.theme.border,
        )

        table.add_column("Step", style="cyan")
        table.add_column("Status")
        table.add_column("Duration", justify="right")

        for step in self.steps:
            if step.status == "complete":
                status = "[green]OK[/green]"
            elif step.status == "failed":
                status = "[red]FAIL[/red]"
            elif step.status == "running":
                status = "[yellow]...[/yellow]"
            else:
                status = "[dim]pending[/dim]"

            duration = f"{step.duration:.2f}s" if step.duration else "-"

            table.add_row(step.name, status, duration)

        # Total
        total_duration = sum(
            s.duration or 0 for s in self.steps
        )
        table.add_row(
            "[bold]Total[/bold]",
            "",
            f"[bold]{total_duration:.2f}s[/bold]",
        )

        return Panel(
            table,
            title="[bold]Execution Summary[/bold]",
            border_style=self.theme.border,
        )

    def reset(self):
        """Reset progress state."""
        self.steps = []
        self.current_step = None
        self.last_sql_query = None
        self.sql_row_count = None
        self.llm_calls = 0
        self.llm_tokens = 0
