"""Group management panel for TUI."""

from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME
from ..api_client import TUIApiClient


class GroupPanel:
    """Panel for managing project groups."""

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize GroupPanel.

        Args:
            theme: Color theme
            api_client: API client for server communication
        """
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

    def render_help(self) -> Panel:
        """Render group command help."""
        content = Text()
        content.append("/group ", style="bold cyan")
        content.append("[subcommand] [args]\n\n", style="yellow")
        content.append("Subcommands:\n", style="bold")
        content.append("  list                         - List all groups\n")
        content.append("  create <name> [description]  - Create new group\n")
        content.append("  delete <name>                - Delete group\n")
        content.append("  users <name>                 - List users in group\n")
        content.append("  add-user <grp> <uid> <role>  - Add user to group\n")
        content.append("  remove-user <grp> <uid>      - Remove user from group\n")
        content.append("\n")
        content.append("Roles: ", style="bold")
        content.append("viewer, editor, admin\n", style="dim")

        return Panel(
            content,
            title="[bold]Group Management[/bold]",
            border_style=self.theme.border,
        )

    async def list_groups(self) -> Panel:
        """List all accessible groups."""
        try:
            data = await self.api_client.list_groups()
            groups = data.get("groups", data.get("items", []))

            if not groups:
                return Panel(
                    "[dim]No groups found[/dim]",
                    title="Groups",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            table.add_column("Projects", justify="right")
            table.add_column("ID", style="dim", width=12)

            for group in groups:
                table.add_row(
                    group.get("name", "Unknown"),
                    group.get("description", "-") or "-",
                    str(group.get("project_count", 0)),
                    group.get("id", "")[:12] + "..." if group.get("id") else "-",
                )

            return Panel(
                table,
                title=f"[bold]Groups ({len(groups)})[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing groups: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def create_group(
        self, name: str, description: Optional[str] = None
    ) -> Panel:
        """Create a new group."""
        try:
            result = await self.api_client.create_group(name, description)
            return Panel(
                f"[green]Group created successfully[/green]\n\n"
                f"Name: [cyan]{result.get('name', name)}[/cyan]\n"
                f"ID: [dim]{result.get('id', 'N/A')}[/dim]",
                title="Group Created",
                border_style="green",
            )
        except Exception as e:
            return Panel(
                f"[red]Failed to create group: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def delete_group(self, name: str) -> Panel:
        """Delete a group by name."""
        try:
            # First find group by name
            data = await self.api_client.list_groups()
            groups = data.get("groups", data.get("items", []))
            group = next(
                (g for g in groups if g.get("name") == name),
                None
            )

            if not group:
                return Panel(
                    f"[red]Group not found: {name}[/red]",
                    title="Error",
                    border_style="red",
                )

            success = await self.api_client.delete_group(group["id"])
            if success:
                return Panel(
                    f"[green]Group '{name}' deleted successfully[/green]",
                    title="Group Deleted",
                    border_style="green",
                )
            else:
                return Panel(
                    f"[red]Failed to delete group '{name}'[/red]",
                    title="Error",
                    border_style="red",
                )

        except Exception as e:
            return Panel(
                f"[red]Error deleting group: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def list_users(self, group_name: str) -> Panel:
        """List users in a group."""
        try:
            # Find group by name
            data = await self.api_client.list_groups()
            groups = data.get("groups", data.get("items", []))
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

            users_data = await self.api_client.list_group_users(group["id"])
            users = users_data.get("users", users_data.get("items", []))

            if not users:
                return Panel(
                    f"[dim]No users in group '{group_name}'[/dim]",
                    title="Group Users",
                    border_style=self.theme.border,
                )

            table = Table(
                show_header=True,
                header_style="bold",
                border_style=self.theme.border,
            )
            table.add_column("Username", style="cyan")
            table.add_column("Role")
            table.add_column("Added", style="dim")

            for user in users:
                role = user.get("role", "unknown")
                role_style = {
                    "admin": "red",
                    "editor": "yellow",
                    "viewer": "green"
                }.get(role, "")

                table.add_row(
                    user.get("username", user.get("user_id", "Unknown")),
                    f"[{role_style}]{role}[/{role_style}]" if role_style else role,
                    (user.get("created_at", "-") or "-")[:10],
                )

            return Panel(
                table,
                title=f"[bold]Users in '{group_name}' ({len(users)})[/bold]",
                border_style=self.theme.border,
            )

        except Exception as e:
            return Panel(
                f"[red]Error listing users: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def add_user(
        self, group_name: str, user_id: str, role: str
    ) -> Panel:
        """Add user to group with role."""
        try:
            if role.lower() not in ("viewer", "editor", "admin"):
                return Panel(
                    f"[red]Invalid role: {role}[/red]\n"
                    "[dim]Valid roles: viewer, editor, admin[/dim]",
                    title="Error",
                    border_style="red",
                )

            # Find group by name
            data = await self.api_client.list_groups()
            groups = data.get("groups", data.get("items", []))
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

            result = await self.api_client.add_group_user(
                group["id"], user_id, role.lower()
            )

            return Panel(
                f"[green]User added to group[/green]\n\n"
                f"User: [cyan]{result.get('username', user_id)}[/cyan]\n"
                f"Group: {group_name}\n"
                f"Role: [yellow]{role}[/yellow]",
                title="User Added",
                border_style="green",
            )

        except Exception as e:
            return Panel(
                f"[red]Error adding user: {e}[/red]",
                title="Error",
                border_style="red",
            )

    async def remove_user(self, group_name: str, user_id: str) -> Panel:
        """Remove user from group."""
        try:
            # Find group by name
            data = await self.api_client.list_groups()
            groups = data.get("groups", data.get("items", []))
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

            success = await self.api_client.remove_group_user(group["id"], user_id)

            if success:
                return Panel(
                    f"[green]User removed from group[/green]\n\n"
                    f"User: [cyan]{user_id}[/cyan]\n"
                    f"Group: {group_name}",
                    title="User Removed",
                    border_style="green",
                )
            else:
                return Panel(
                    f"[red]Failed to remove user[/red]",
                    title="Error",
                    border_style="red",
                )

        except Exception as e:
            return Panel(
                f"[red]Error removing user: {e}[/red]",
                title="Error",
                border_style="red",
            )
