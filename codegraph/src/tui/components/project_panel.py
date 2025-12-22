"""Extended project management panel for TUI."""

from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class ProjectPanel:
    """Extended panel for project management operations."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize ProjectPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    async def get_project_info(self, project_name: str) -> Panel:
        """Get detailed project information."""
        try:
            # Try local project manager first
            try:
                from src.project_manager import get_project_manager

                pm = get_project_manager()
                project = pm.get_project_by_name(project_name)

                if project:
                    return self._render_local_project(project)
            except ImportError:
                pass

            # Fall back to API
            projects_data = await self.api_client.list_projects()
            projects = projects_data.get("projects", projects_data.get("items", []))

            project = next(
                (p for p in projects if p.get("name") == project_name),
                None
            )

            if not project:
                return Panel(
                    f"[red]Project not found: {project_name}[/red]",
                    title="Error",
                    border_style="red",
                )

            return self._render_api_project(project)

        except Exception as e:
            return Panel(
                f"[red]Error getting project info: {e}[/red]",
                title="Error",
                border_style="red",
            )

    def _render_local_project(self, project) -> Panel:
        """Render project info from local project manager."""
        content = Text()
        content.append(f"Name: ", style="bold")
        content.append(f"{project.name}\n", style="bold cyan")

        content.append(f"Language: ", style="bold")
        content.append(f"{project.language or 'Unknown'}\n")

        content.append(f"Description: ", style="bold")
        content.append(f"{project.description or '-'}\n")

        content.append("\n")
        content.append("Paths:\n", style="bold")
        content.append(f"  Database: ", style="")
        content.append(f"{project.db_path}\n", style="dim")

        if project.cpg_path:
            content.append(f"  CPG: ", style="")
            content.append(f"{project.cpg_path}\n", style="dim")

        if project.source_path:
            content.append(f"  Source: ", style="")
            content.append(f"{project.source_path}\n", style="dim")

        content.append("\n")
        content.append(f"Active: ", style="bold")
        is_active = getattr(project, "is_active", False)
        content.append(
            "Yes\n" if is_active else "No\n",
            style="green" if is_active else "dim"
        )

        # Try to get file stats
        try:
            db_path = Path(project.db_path)
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                content.append(f"Database size: ", style="bold")
                content.append(f"{size_mb:.1f} MB\n")
        except Exception:
            pass

        return Panel(
            content,
            title=f"[bold]Project: {project.name}[/bold]",
            border_style=self.theme.border,
        )

    def _render_api_project(self, project: dict) -> Panel:
        """Render project info from API response."""
        content = Text()
        content.append(f"Name: ", style="bold")
        content.append(f"{project.get('name', 'Unknown')}\n", style="bold cyan")

        content.append(f"Language: ", style="bold")
        content.append(f"{project.get('language', 'Unknown')}\n")

        content.append(f"Description: ", style="bold")
        content.append(f"{project.get('description', '-') or '-'}\n")

        content.append(f"ID: ", style="bold")
        content.append(f"{project.get('id', 'N/A')}\n", style="dim")

        content.append("\n")
        content.append("Paths:\n", style="bold")
        content.append(f"  Database: ", style="")
        content.append(f"{project.get('db_path', '-')}\n", style="dim")

        if project.get("cpg_path"):
            content.append(f"  CPG: ", style="")
            content.append(f"{project['cpg_path']}\n", style="dim")

        if project.get("source_path"):
            content.append(f"  Source: ", style="")
            content.append(f"{project['source_path']}\n", style="dim")

        content.append("\n")
        content.append(f"Active: ", style="bold")
        is_active = project.get("is_active", False)
        content.append(
            "Yes\n" if is_active else "No\n",
            style="green" if is_active else "dim"
        )

        if project.get("group_id"):
            content.append(f"Group ID: ", style="bold")
            content.append(f"{project['group_id']}\n", style="dim")

        if project.get("created_at"):
            content.append(f"Created: ", style="bold")
            content.append(f"{project['created_at'][:10]}\n", style="dim")

        return Panel(
            content,
            title=f"[bold]Project: {project.get('name', 'Unknown')}[/bold]",
            border_style=self.theme.border,
        )

    async def create_project(
        self,
        name: str,
        group_name: str,
        db_path: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Panel:
        """Create a new project in a group."""
        try:
            # Find group by name
            groups_data = await self.api_client.list_groups()
            groups = groups_data.get("groups", groups_data.get("items", []))

            group = next(
                (g for g in groups if g.get("name") == group_name),
                None
            )

            if not group:
                return Panel(
                    f"[red]Group not found: {group_name}[/red]",
                    title="Error",
                    border_style="red",
                )

            result = await self.api_client.create_project(
                name=name,
                group_id=group["id"],
                db_path=db_path,
                language=language,
                description=description,
            )

            return Panel(
                f"[green]Project created successfully[/green]\n\n"
                f"Name: [cyan]{result.get('name', name)}[/cyan]\n"
                f"Group: {group_name}\n"
                f"ID: [dim]{result.get('id', 'N/A')}[/dim]",
                title="Project Created",
                border_style="green",
            )

        except Exception as e:
            return Panel(
                f"[red]Error creating project: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def list_projects_in_group(self, group_name: str) -> Panel:
        """List all projects in a group."""
        try:
            # Find group by name
            groups_data = await self.api_client.list_groups()
            groups = groups_data.get("groups", groups_data.get("items", []))

            group = next(
                (g for g in groups if g.get("name") == group_name),
                None
            )

            if not group:
                return Panel(
                    f"[red]Group not found: {group_name}[/red]",
                    title="Error",
                    border_style="red",
                )

            projects_data = await self.api_client.list_projects(group_id=group["id"])
            projects = projects_data.get("projects", projects_data.get("items", []))

            if not projects:
                return Panel(
                    f"[dim]No projects in group '{group_name}'[/dim]",
                    title="Projects",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("Name", style="cyan")
            table.add_column("Language")
            table.add_column("Active")
            table.add_column("Description")

            for project in projects:
                is_active = project.get("is_active", False)
                active_str = "[green]Yes[/green]" if is_active else "[dim]No[/dim]"
                desc = project.get("description", "-") or "-"
                if len(desc) > 30:
                    desc = desc[:27] + "..."

                table.add_row(
                    project.get("name", "Unknown"),
                    project.get("language", "-"),
                    active_str,
                    desc,
                )

            return Panel(
                table,
                title=f"[bold]Projects in '{group_name}' ({len(projects)})[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing projects: {e}[/red]",
                title="Error",
                border_style="red",
            )
