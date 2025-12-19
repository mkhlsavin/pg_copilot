"""Health status panel for TUI."""

from typing import Optional

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class HealthPanel:
    """Panel for displaying system health status."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize HealthPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    async def render(self) -> Panel:
        """Render health status panel."""
        try:
            health = await self.api_client.get_health()

            overall_status = health.get("status", "unknown")
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(overall_status, "dim")

            # Build header
            header = Text()
            header.append("Overall Status: ", style="bold")
            header.append(f"{overall_status.upper()}\n", style=f"bold {status_color}")

            version = health.get("version", "unknown")
            header.append(f"Version: {version}\n", style="dim")

            uptime = health.get("uptime_seconds", 0)
            if uptime:
                uptime_str = self._format_uptime(uptime)
                header.append(f"Uptime: {uptime_str}\n", style="dim")

            header.append("\n")

            # Build components table
            table = Table(
                show_header=True,
                header_style="bold",
                border_style="dim",
            )
            table.add_column("Component", style="cyan")
            table.add_column("Status")
            table.add_column("Details")

            components = health.get("components", {})

            for name, component in components.items():
                if isinstance(component, dict):
                    comp_status = component.get("status", "unknown")
                    comp_color = {
                        "healthy": "green",
                        "degraded": "yellow",
                        "unhealthy": "red",
                        "unavailable": "dim",
                    }.get(comp_status, "white")

                    # Build details string
                    details_parts = []
                    if component.get("provider"):
                        details_parts.append(f"provider: {component['provider']}")
                    if component.get("server"):
                        details_parts.append(f"server: {component['server']}")
                    if component.get("host"):
                        details_parts.append(f"host: {component['host']}")
                    if component.get("latency_ms"):
                        details_parts.append(f"latency: {component['latency_ms']}ms")
                    if component.get("error"):
                        details_parts.append(f"error: {component['error']}")

                    details = ", ".join(details_parts) if details_parts else "-"
                    if len(details) > 50:
                        details = details[:47] + "..."

                    table.add_row(
                        name.replace("_", " ").title(),
                        f"[{comp_color}]{comp_status}[/{comp_color}]",
                        details,
                    )
                else:
                    # Simple status value
                    table.add_row(
                        name.replace("_", " ").title(),
                        str(component),
                        "-",
                    )

            return Panel(
                Group(header, table),
                title="[bold]System Health[/bold]",
                border_style=status_color,
            )

        except Exception as e:
            return Panel(
                f"[red]Failed to get health status[/red]\n\n"
                f"Error: {e}\n\n"
                f"[dim]Make sure the API server is running.[/dim]\n"
                f"[dim]Default URL: {self.api_client.config.base_url}[/dim]",
                title="Health Check Failed",
                border_style="red",
            )

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}d"

    async def render_detailed(self) -> Panel:
        """Render detailed health status with version info."""
        try:
            health = await self.api_client.get_health()
            version_info = await self.api_client.get_version()

            content = Text()

            # Version info
            content.append("Version Information\n", style="bold")
            content.append(f"  API Version: {version_info.get('version', 'unknown')}\n")
            content.append(f"  Build: {version_info.get('build', 'unknown')}\n")
            if version_info.get("commit"):
                content.append(f"  Commit: {version_info['commit'][:8]}\n")
            content.append("\n")

            # Health summary
            overall_status = health.get("status", "unknown")
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(overall_status, "dim")

            content.append("System Status\n", style="bold")
            content.append(f"  Status: ", style="")
            content.append(f"{overall_status.upper()}\n", style=status_color)
            content.append(f"  Uptime: {self._format_uptime(health.get('uptime_seconds', 0))}\n")
            content.append("\n")

            # Components
            content.append("Components\n", style="bold")
            components = health.get("components", {})
            for name, comp in components.items():
                if isinstance(comp, dict):
                    comp_status = comp.get("status", "unknown")
                    comp_color = {
                        "healthy": "green",
                        "degraded": "yellow",
                        "unhealthy": "red",
                    }.get(comp_status, "dim")
                    content.append(f"  {name}: ", style="")
                    content.append(f"{comp_status}\n", style=comp_color)
                else:
                    content.append(f"  {name}: {comp}\n", style="dim")

            return Panel(
                content,
                title="[bold]System Health (Detailed)[/bold]",
                border_style=status_color,
            )

        except Exception as e:
            return Panel(
                f"[red]Error: {e}[/red]",
                title="Health Check Failed",
                border_style="red",
            )
