"""Authentication panel for TUI."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class AuthPanel:
    """Panel for authentication management."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize AuthPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    def render_help(self) -> Panel:
        """Render auth command help."""
        content = Text()
        content.append("/auth ", style="bold cyan")
        content.append("[subcommand]\n\n", style="yellow")
        content.append("Subcommands:\n", style="bold")
        content.append("  login              - Login with username/password\n")
        content.append("  logout             - Logout and clear token\n")
        content.append("  me                 - Show current user info\n")
        content.append("  api-keys           - List API keys\n")
        content.append("  api-keys create <name>  - Create new API key\n")
        content.append("  api-keys revoke <id>    - Revoke API key\n")

        # Show auth status
        content.append("\n")
        if self.api_client.is_authenticated:
            content.append("Status: ", style="bold")
            content.append("Authenticated\n", style="green")
        else:
            content.append("Status: ", style="bold")
            content.append("Not authenticated\n", style="yellow")

        return Panel(
            content,
            title="[bold]Authentication[/bold]",
            border_style=self.theme.border,
        )

    async def login(self, console: Console) -> Panel:
        """Interactive login with username and password."""
        try:
            console.print("[bold]Login to CodeGraph[/bold]\n")

            username = Prompt.ask("[cyan]Username[/cyan]")
            password = Prompt.ask("[cyan]Password[/cyan]", password=True)

            if not username or not password:
                return Panel(
                    "[yellow]Login cancelled - empty credentials[/yellow]",
                    title="Login",
                    border_style="yellow",
                )

            result = await self.api_client.login(username, password)

            expires_in = result.get("expires_in", 1800)
            expires_hours = expires_in / 3600

            return Panel(
                f"[green]Login successful[/green]\n\n"
                f"Username: [cyan]{username}[/cyan]\n"
                f"Token expires in: {expires_hours:.1f} hours",
                title="Authenticated",
                border_style="green",
            )

        except KeyboardInterrupt:
            return Panel(
                "[yellow]Login cancelled[/yellow]",
                title="Login",
                border_style="yellow",
            )
        except Exception as e:
            return Panel(
                f"[red]Login failed: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def logout(self) -> Panel:
        """Logout and clear authentication token."""
        try:
            success = await self.api_client.logout()
            if success:
                return Panel(
                    "[green]Logged out successfully[/green]",
                    title="Logout",
                    border_style="green",
                )
            else:
                return Panel(
                    "[yellow]Logged out (token cleared locally)[/yellow]",
                    title="Logout",
                    border_style="yellow",
                )
        except Exception as e:
            # Clear token anyway
            self.api_client.clear_token()
            return Panel(
                f"[yellow]Logged out locally[/yellow]\n"
                f"[dim]Server error: {e}[/dim]",
                title="Logout",
                border_style="yellow",
            )

    async def get_current_user(self) -> Panel:
        """Get current authenticated user info."""
        try:
            if not self.api_client.is_authenticated:
                return Panel(
                    "[yellow]Not authenticated[/yellow]\n"
                    "[dim]Use /auth login to authenticate[/dim]",
                    title="Current User",
                    border_style="yellow",
                )

            user = await self.api_client.get_current_user()

            content = Text()
            content.append(f"Username: ", style="bold")
            content.append(f"{user.get('username', 'Unknown')}\n", style="cyan")

            if user.get("email"):
                content.append(f"Email: ", style="bold")
                content.append(f"{user['email']}\n")

            content.append(f"Role: ", style="bold")
            role = user.get("role", "user")
            role_style = {"admin": "red", "reviewer": "yellow"}.get(role, "green")
            content.append(f"{role}\n", style=role_style)

            content.append(f"Active: ", style="bold")
            is_active = user.get("is_active", True)
            content.append("Yes\n" if is_active else "No\n", style="green" if is_active else "red")

            if user.get("created_at"):
                content.append(f"Created: ", style="bold")
                content.append(f"{user['created_at'][:10]}\n", style="dim")

            return Panel(
                content,
                title="[bold]Current User[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error getting user info: {e}[/red]\n"
                "[dim]You may need to re-authenticate with /auth login[/dim]",
                title="Error",
                border_style="red",
            )

    async def list_api_keys(self) -> Panel:
        """List user's API keys."""
        try:
            if not self.api_client.is_authenticated:
                return Panel(
                    "[yellow]Not authenticated[/yellow]\n"
                    "[dim]Use /auth login to authenticate[/dim]",
                    title="API Keys",
                    border_style="yellow",
                )

            keys = await self.api_client.list_api_keys()

            if not keys:
                return Panel(
                    "[dim]No API keys found[/dim]\n"
                    "[dim]Use /auth api-keys create <name> to create one[/dim]",
                    title="API Keys",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("Name", style="cyan")
            table.add_column("Prefix")
            table.add_column("Expires")
            table.add_column("Last Used", style="dim")
            table.add_column("Status")
            table.add_column("ID", style="dim", width=10)

            for key in keys:
                is_revoked = key.get("is_revoked", False)
                status = "[red]Revoked[/red]" if is_revoked else "[green]Active[/green]"

                expires = key.get("expires_at", "-")
                if expires and len(expires) > 10:
                    expires = expires[:10]

                last_used = key.get("last_used_at", "Never")
                if last_used and last_used != "Never" and len(last_used) > 10:
                    last_used = last_used[:10]

                table.add_row(
                    key.get("name", "Unknown"),
                    key.get("prefix", "***"),
                    expires or "Never",
                    last_used,
                    status,
                    key.get("id", "")[:10] + "..." if len(key.get("id", "")) > 10 else key.get("id", "-"),
                )

            return Panel(
                table,
                title=f"[bold]API Keys ({len(keys)})[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing API keys: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def create_api_key(
        self, name: str, expires_days: int = 365
    ) -> Panel:
        """Create a new API key."""
        try:
            if not self.api_client.is_authenticated:
                return Panel(
                    "[yellow]Not authenticated[/yellow]\n"
                    "[dim]Use /auth login to authenticate[/dim]",
                    title="API Keys",
                    border_style="yellow",
                )

            result = await self.api_client.create_api_key(name, expires_days)

            # The key is only shown once!
            key_value = result.get("key", result.get("api_key", "N/A"))

            content = Text()
            content.append("[green]API key created successfully[/green]\n\n")
            content.append(f"Name: {result.get('name', name)}\n")
            content.append(f"Key: ", style="bold")
            content.append(f"{key_value}\n", style="bold yellow")
            content.append("\n")
            content.append(
                "[red bold]IMPORTANT:[/red bold] Save this key now!\n",
                style="red"
            )
            content.append(
                "It will not be shown again.\n",
                style="red dim"
            )

            return Panel(
                content,
                title="API Key Created",
                border_style="green",
            )

        except Exception as e:
            return Panel(
                f"[red]Failed to create API key: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def revoke_api_key(self, key_id: str) -> Panel:
        """Revoke an API key."""
        try:
            if not self.api_client.is_authenticated:
                return Panel(
                    "[yellow]Not authenticated[/yellow]\n"
                    "[dim]Use /auth login to authenticate[/dim]",
                    title="API Keys",
                    border_style="yellow",
                )

            success = await self.api_client.revoke_api_key(key_id)

            if success:
                return Panel(
                    f"[green]API key revoked[/green]\n\n"
                    f"Key ID: [dim]{key_id}[/dim]",
                    title="Key Revoked",
                    border_style="green",
                )
            else:
                return Panel(
                    f"[red]Failed to revoke API key[/red]",
                    title="Error",
                    border_style="red",
                )

        except Exception as e:
            return Panel(
                f"[red]Error revoking key: {e}[/red]",
                title="Error",
                border_style="red",
            )
