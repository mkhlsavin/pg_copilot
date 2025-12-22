"""Extended statistics panel for TUI."""

from typing import Optional

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class ExtendedStatsPanel:
    """Panel for extended statistics from API."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize ExtendedStatsPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    async def get_scenario_stats(self) -> Panel:
        """Get scenario usage statistics."""
        try:
            stats = await self.api_client.get_scenario_stats()

            scenarios = stats.get("scenarios", {})

            if not scenarios:
                return Panel(
                    "[dim]No scenario statistics available[/dim]",
                    title="Scenario Statistics",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("Scenario", style="cyan")
            table.add_column("Queries", justify="right")
            table.add_column("Success", justify="right")
            table.add_column("Avg Time", justify="right")

            for scenario_id, data in scenarios.items():
                if isinstance(data, dict):
                    total = data.get("total", data.get("count", 0))
                    success = data.get("success", data.get("successful", 0))
                    avg_time = data.get("avg_time_ms", data.get("avg_response_time", 0))

                    success_rate = f"{(success/total*100):.0f}%" if total > 0 else "-"
                    avg_time_str = f"{avg_time:.0f}ms" if avg_time else "-"

                    table.add_row(
                        scenario_id,
                        str(total),
                        success_rate,
                        avg_time_str,
                    )
                else:
                    table.add_row(
                        scenario_id,
                        str(data),
                        "-",
                        "-",
                    )

            # Summary header
            header = Text()
            total_queries = stats.get("total_queries", stats.get("total", 0))
            header.append(f"Total queries: {total_queries:,}\n")

            period = stats.get("period", stats.get("time_range"))
            if period:
                header.append(f"Period: {period}\n", style="dim")

            header.append("\n")

            return Panel(
                Group(header, table),
                title="[bold]Scenario Statistics[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting scenario stats: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def get_performance_stats(self) -> Panel:
        """Get performance statistics."""
        try:
            stats = await self.api_client.get_performance_stats()

            content = Text()

            # Response times
            content.append("Response Times\n", style="bold")
            avg_time = stats.get("avg_response_time_ms", stats.get("avg_response_time", 0))
            content.append(f"  Average: {avg_time:.0f}ms\n")

            p50 = stats.get("p50_response_time_ms", stats.get("p50", 0))
            if p50:
                content.append(f"  P50: {p50:.0f}ms\n")

            p95 = stats.get("p95_response_time_ms", stats.get("p95", 0))
            if p95:
                content.append(f"  P95: {p95:.0f}ms\n")

            p99 = stats.get("p99_response_time_ms", stats.get("p99", 0))
            if p99:
                content.append(f"  P99: {p99:.0f}ms\n")

            content.append("\n")

            # Throughput
            content.append("Throughput\n", style="bold")
            rpm = stats.get("requests_per_minute", stats.get("rpm", 0))
            content.append(f"  Requests/min: {rpm:.1f}\n")

            rps = stats.get("requests_per_second", stats.get("rps", 0))
            if rps:
                content.append(f"  Requests/sec: {rps:.2f}\n")

            content.append("\n")

            # Error rate
            content.append("Quality\n", style="bold")
            error_rate = stats.get("error_rate", 0)
            error_color = "green" if error_rate < 1 else "yellow" if error_rate < 5 else "red"
            content.append(f"  Error rate: ", style="")
            content.append(f"{error_rate:.2f}%\n", style=error_color)

            success_rate = stats.get("success_rate", 100 - error_rate)
            content.append(f"  Success rate: {success_rate:.1f}%\n")

            # Cache stats if available
            cache_hit_rate = stats.get("cache_hit_rate")
            if cache_hit_rate is not None:
                content.append(f"\n")
                content.append("Cache\n", style="bold")
                content.append(f"  Hit rate: {cache_hit_rate:.1f}%\n")

            return Panel(
                content,
                title="[bold]Performance Statistics[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting performance stats: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def get_api_stats(self) -> Panel:
        """Get general API statistics."""
        try:
            stats = await self.api_client.get_stats()

            content = Text()

            # General metrics
            content.append("API Metrics\n", style="bold")

            total_requests = stats.get("total_requests", 0)
            content.append(f"  Total requests: {total_requests:,}\n")

            active_sessions = stats.get("active_sessions", 0)
            content.append(f"  Active sessions: {active_sessions}\n")

            active_jobs = stats.get("active_jobs", 0)
            content.append(f"  Active jobs: {active_jobs}\n")

            content.append("\n")

            # Performance
            content.append("Performance\n", style="bold")

            cache_hit_rate = stats.get("cache_hit_rate", 0)
            content.append(f"  Cache hit rate: {cache_hit_rate:.1f}%\n")

            avg_response = stats.get("avg_response_time_ms", 0)
            content.append(f"  Avg response: {avg_response:.0f}ms\n")

            # Resource usage if available
            memory_mb = stats.get("memory_usage_mb")
            if memory_mb:
                content.append(f"\n")
                content.append("Resources\n", style="bold")
                content.append(f"  Memory: {memory_mb:.0f} MB\n")

            cpu_percent = stats.get("cpu_percent")
            if cpu_percent is not None:
                content.append(f"  CPU: {cpu_percent:.1f}%\n")

            # Database stats if available
            db_connections = stats.get("db_connections", stats.get("database_connections"))
            if db_connections is not None:
                content.append(f"\n")
                content.append("Database\n", style="bold")
                content.append(f"  Active connections: {db_connections}\n")

            return Panel(
                content,
                title="[bold]API Statistics[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting API stats: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def get_all_stats(self) -> Panel:
        """Get combined statistics summary."""
        try:
            stats = await self.api_client.get_stats()

            # Build summary table
            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
                expand=True,
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")

            table.add_row("Total Requests", f"{stats.get('total_requests', 0):,}")
            table.add_row("Active Sessions", str(stats.get("active_sessions", 0)))
            table.add_row("Active Jobs", str(stats.get("active_jobs", 0)))
            table.add_row("Cache Hit Rate", f"{stats.get('cache_hit_rate', 0):.1f}%")
            table.add_row("Avg Response", f"{stats.get('avg_response_time_ms', 0):.0f}ms")

            return Panel(
                table,
                title="[bold]System Statistics[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting stats: {e}[/red]",
                title="Error",
                border_style="red",
            )
