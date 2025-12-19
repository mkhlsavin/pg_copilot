"""Import management panel for TUI with WebSocket progress support."""

import asyncio
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class ImportPanel:
    """Panel for managing project imports with real-time progress."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize ImportPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    def render_help(self) -> Panel:
        """Render import command help."""
        content = Text()
        content.append("/import ", style="bold cyan")
        content.append("[subcommand] [args]\n\n", style="yellow")
        content.append("Subcommands:\n", style="bold")
        content.append("  start <source>       - Start import from URL or path\n")
        content.append("  status [job_id]      - Status of current/specified job\n")
        content.append("  watch <job_id>       - Watch import progress in real-time\n")
        content.append("  jobs                 - List all import jobs\n")
        content.append("  cancel <job_id>      - Cancel running import\n")
        content.append("\n")
        content.append("Options:\n", style="bold")
        content.append("  --language <lang>    - Programming language (auto-detect)\n")
        content.append("  --group <name>       - Target project group\n")
        content.append("\n")
        content.append("Examples:\n", style="bold dim")
        content.append("  /import start https://github.com/org/repo\n", style="dim")
        content.append("  /import start /path/to/code --language python\n", style="dim")
        content.append("  /import watch abc123\n", style="dim")

        return Panel(
            content,
            title="[bold]Import Management[/bold]",
            border_style=self.theme.border,
        )

    async def start_import(
        self,
        source: str,
        language: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> Panel:
        """Start a new import job."""
        try:
            # Find group ID if name provided
            group_id = None
            if group_name:
                groups_data = await self.api_client.list_groups()
                groups = groups_data.get("groups", groups_data.get("items", []))
                group = next(
                    (g for g in groups if g.get("name") == group_name),
                    None
                )
                if group:
                    group_id = group["id"]
                else:
                    return Panel(
                        f"[red]Group not found: {group_name}[/red]",
                        title="Error",
                        border_style="red",
                    )

            result = await self.api_client.start_import(
                source=source,
                language=language,
                group_id=group_id,
            )

            job_id = result.get("job_id", result.get("id", "unknown"))

            return Panel(
                f"[green]Import started successfully[/green]\n\n"
                f"Job ID: [cyan]{job_id}[/cyan]\n"
                f"Status: {result.get('status', 'pending')}\n"
                f"Source: [dim]{source}[/dim]\n\n"
                f"[dim]Use /import status {job_id} to track progress[/dim]\n"
                f"[dim]Use /import watch {job_id} for real-time updates[/dim]",
                title="Import Started",
                border_style="green",
            )

        except Exception as e:
            return Panel(
                f"[red]Failed to start import: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def get_status(self, job_id: Optional[str] = None) -> Panel:
        """Get import job status."""
        try:
            if not job_id:
                # Get latest job
                jobs = await self.api_client.list_import_jobs(limit=1)
                if not jobs:
                    return Panel(
                        "[dim]No import jobs found[/dim]",
                        title="Import Status",
                        border_style=self.theme.border,
                    )
                job_id = jobs[0].get("job_id", jobs[0].get("id"))

            status = await self.api_client.get_import_status(job_id)

            # Build status display
            status_value = status.get("status", "unknown")
            status_color = {
                "pending": "yellow",
                "running": "blue",
                "in_progress": "blue",
                "completed": "green",
                "failed": "red",
                "cancelled": "dim",
            }.get(status_value, "white")

            content = Text()
            content.append(f"Job ID: ", style="bold")
            content.append(f"{job_id[:16]}...\n" if len(job_id) > 16 else f"{job_id}\n", style="dim")
            content.append(f"Project: ", style="bold")
            content.append(f"{status.get('project_name', 'Unknown')}\n")
            content.append(f"Status: ", style="bold")
            content.append(f"{status_value}\n", style=status_color)

            # Progress
            progress = status.get("overall_progress", status.get("progress", 0))
            if progress:
                content.append(f"Progress: ", style="bold")
                content.append(f"{progress:.0f}%\n")

            # Current step
            current_step = status.get("current_step")
            if current_step:
                content.append(f"Current step: ", style="bold")
                content.append(f"{current_step}\n")

            # Steps details
            steps = status.get("steps", [])
            if steps:
                content.append("\nSteps:\n", style="bold")
                for step in steps:
                    step_status = step.get("status", "pending")
                    step_icon = {
                        "completed": "[green]v[/green]",
                        "running": "[blue]>[/blue]",
                        "failed": "[red]x[/red]",
                        "skipped": "[dim]-[/dim]",
                    }.get(step_status, "[dim]o[/dim]")
                    content.append(f"  {step_icon} {step.get('name', 'Unknown')}\n")

            # Error message
            error = status.get("error", status.get("error_message"))
            if error:
                content.append(f"\n[red]Error: {error}[/red]")

            return Panel(
                content,
                title="[bold]Import Status[/bold]",
                border_style=status_color,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting status: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def list_jobs(self, limit: int = 20) -> Panel:
        """List all import jobs."""
        try:
            jobs = await self.api_client.list_import_jobs(limit=limit)

            if not jobs:
                return Panel(
                    "[dim]No import jobs found[/dim]",
                    title="Import Jobs",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("ID", style="dim", width=14)
            table.add_column("Project")
            table.add_column("Status")
            table.add_column("Progress", justify="right")
            table.add_column("Created", style="dim")

            for job in jobs:
                job_id = job.get("job_id", job.get("id", ""))
                status = job.get("status", "unknown")
                status_color = {
                    "pending": "yellow",
                    "running": "blue",
                    "in_progress": "blue",
                    "completed": "green",
                    "failed": "red",
                    "cancelled": "dim",
                }.get(status, "")

                progress = job.get("overall_progress", job.get("progress", 0))
                progress_str = f"{progress:.0f}%" if progress else "-"

                created = job.get("created_at", "-")
                if created and len(created) > 16:
                    created = created[:16]

                table.add_row(
                    job_id[:14] + "..." if len(job_id) > 14 else job_id,
                    job.get("project_name", "Unknown"),
                    f"[{status_color}]{status}[/{status_color}]" if status_color else status,
                    progress_str,
                    created,
                )

            return Panel(
                table,
                title=f"[bold]Import Jobs ({len(jobs)})[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing jobs: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def cancel_job(self, job_id: str) -> Panel:
        """Cancel a running import job."""
        try:
            result = await self.api_client.cancel_import(job_id)
            return Panel(
                f"[green]Import job cancelled[/green]\n\n"
                f"Job ID: [cyan]{job_id}[/cyan]",
                title="Import Cancelled",
                border_style="green",
            )
        except Exception as e:
            return Panel(
                f"[red]Failed to cancel job: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def watch_progress(self, job_id: str, console: Console) -> None:
        """Watch import progress with real-time updates via WebSocket."""
        console.print(f"[cyan]Watching import job: {job_id}[/cyan]")
        console.print("[dim]Press Ctrl+C to stop watching[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting import...", total=100)

            def update_progress(data: dict) -> None:
                """Callback for WebSocket progress updates."""
                status = data.get("status", "unknown")
                current_step = data.get("current_step", "")
                overall_progress = data.get("overall_progress", data.get("progress", 0))

                description = f"[{status}] {current_step}" if current_step else f"[{status}]"
                progress.update(task, completed=overall_progress, description=description)

                # Log step completions
                if data.get("event_type") == "step_completed":
                    step_name = data.get("step_name", "Step")
                    console.print(f"  [green]v[/green] {step_name} completed")

                # Handle terminal states
                if status == "completed":
                    progress.update(task, completed=100, description="[green]Completed[/green]")
                    console.print("\n[green]Import completed successfully![/green]")
                elif status == "failed":
                    error = data.get("error", "Unknown error")
                    progress.update(task, description=f"[red]Failed: {error}[/red]")
                    console.print(f"\n[red]Import failed: {error}[/red]")
                elif status == "cancelled":
                    progress.update(task, description="[yellow]Cancelled[/yellow]")
                    console.print("\n[yellow]Import was cancelled[/yellow]")

            try:
                await self.api_client.watch_import_progress(job_id, update_progress)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped watching[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error watching progress: {e}[/red]")
