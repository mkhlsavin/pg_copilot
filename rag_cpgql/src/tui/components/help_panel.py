"""Help panel with command documentation."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME


# Command definitions
COMMANDS = {
    "/help": {
        "args": "",
        "description": "Show this help message",
        "examples": ["/help"],
    },
    "/scenarios": {
        "args": "[group]",
        "description": "List available scenarios, optionally filtered by group",
        "examples": ["/scenarios", "/scenarios security"],
    },
    "/select": {
        "args": "<number>",
        "description": "Select a scenario by number",
        "examples": ["/select 1", "/select 02"],
    },
    "/history": {
        "args": "[count]",
        "description": "Show conversation history",
        "examples": ["/history", "/history 5"],
    },
    "/save": {
        "args": "[filename]",
        "description": "Save current session to file",
        "examples": ["/save", "/save my_session"],
    },
    "/load": {
        "args": "<filename>",
        "description": "Load session from file",
        "examples": ["/load my_session"],
    },
    "/config": {
        "args": "[section] [key] [value]",
        "description": "View/edit config with interactive section list",
        "examples": [
            "/config",
            "/config 1",
            "/config llm",
            "/config llm temperature 0.7",
        ],
    },
    "/stat": {
        "args": "[scenarios|performance|api]",
        "description": "Show CPG/ChromaDB stats, or API metrics",
        "examples": [
            "/stat",
            "/stats",
            "/stat scenarios",
            "/stat performance",
            "/stat api",
        ],
    },
    "/query": {
        "args": "<SQL>",
        "description": "Execute SQL query on CPG database (read-only)",
        "examples": [
            "/query SELECT * FROM nodes_method LIMIT 5",
            "/query SELECT name FROM nodes_call WHERE name LIKE '%alloc%'",
            "/sql DESCRIBE nodes_method",
        ],
    },
    "/demo": {
        "args": "[--scenarios N,N] [--lang en|ru]",
        "description": "Run quick benchmark with one question per scenario",
        "examples": ["/demo", "/demo --scenarios 01,02", "/demo --lang ru"],
    },
    "/review": {
        "args": "[source] [id] [--format fmt] [--inline]",
        "description": "Launch code review on diff/PR/MR",
        "examples": [
            "/review",
            "/review github 123",
            "/review gitlab 456",
            "/review git",
            "/review file diff.patch",
            "/review --format json --inline",
        ],
    },
    "/project": {
        "args": "[list|switch|add|remove|info|create] [name]",
        "description": "Manage CPG projects",
        "examples": [
            "/project",
            "/project list",
            "/project switch myproject",
            "/project add myproject ./db.duckdb python",
            "/project remove myproject",
            "/project info myproject",
            "/project create newproj --group mygroup",
        ],
    },
    "/group": {
        "args": "[list|create|delete|users|add-user|remove-user]",
        "description": "Manage project groups and user access",
        "examples": [
            "/group list",
            "/group create mygroup Description here",
            "/group delete mygroup",
            "/group users mygroup",
            "/group add-user mygroup user123 editor",
            "/group remove-user mygroup user123",
        ],
    },
    "/import": {
        "args": "[start|status|jobs|watch|cancel] [args]",
        "description": "Import projects from repositories",
        "examples": [
            "/import start https://github.com/org/repo",
            "/import start /path/to/code --language python",
            "/import status",
            "/import jobs",
            "/import watch abc123",
            "/import cancel abc123",
        ],
    },
    "/auth": {
        "args": "[login|logout|me|api-keys] [args]",
        "description": "Authentication and API key management",
        "examples": [
            "/auth login",
            "/auth logout",
            "/auth me",
            "/auth api-keys",
            "/auth api-keys create my-key",
            "/auth api-keys revoke key-id",
        ],
    },
    "/session": {
        "args": "[list|switch|export|delete] [args]",
        "description": "Manage chat sessions",
        "examples": [
            "/session list",
            "/session switch abc123",
            "/session export abc123 md",
            "/session delete abc123",
        ],
    },
    "/health": {
        "args": "",
        "description": "Show system health status (API, DB, Joern, LLM)",
        "examples": ["/health"],
    },
    "/clear": {
        "args": "",
        "description": "Clear the screen",
        "examples": ["/clear"],
    },
    "/exit": {
        "args": "",
        "description": "Exit the application",
        "examples": ["/exit", "/quit", "/q"],
    },
}


class HelpPanel:
    """Help documentation panel."""

    def __init__(self, theme: Theme = DEFAULT_THEME):
        self.theme = theme
        self.commands = COMMANDS

    def render(self, command: str = None) -> Panel:
        """
        Render help panel.

        Args:
            command: Specific command to show help for, or None for all

        Returns:
            Rich Panel with help content
        """
        if command:
            return self._render_command_help(command)
        return self._render_all_commands()

    def _render_all_commands(self) -> Panel:
        """Render help for all commands."""
        table = Table(
            show_header=True,
            header_style="bold",
            border_style=self.theme.border,
            expand=True,
        )

        table.add_column("Command", style="cyan", width=15)
        table.add_column("Arguments", style="yellow", width=15)
        table.add_column("Description")

        for cmd, info in self.commands.items():
            table.add_row(
                cmd,
                info["args"] or "-",
                info["description"],
            )

        content = Text()
        content.append("RAG-CPGQL Interactive Console\n\n", style="bold cyan")
        content.append("Type a question to query the code analysis system.\n", style="dim")
        content.append("Use commands below for additional functionality.\n\n", style="dim")

        return Panel(
            table,
            title="[bold]Help[/bold]",
            subtitle="Type /help <command> for details",
            border_style=self.theme.border,
        )

    def _render_command_help(self, command: str) -> Panel:
        """Render detailed help for a specific command."""
        # Normalize command
        if not command.startswith("/"):
            command = "/" + command

        if command not in self.commands:
            return Panel(
                f"[red]Unknown command: {command}[/red]\n\n"
                "Use /help to see available commands.",
                title="Error",
                border_style="red",
            )

        info = self.commands[command]

        content = Text()
        content.append(f"{command}", style="bold cyan")
        if info["args"]:
            content.append(f" {info['args']}", style="yellow")
        content.append("\n\n")

        content.append("Description:\n", style="bold")
        content.append(f"  {info['description']}\n\n")

        if info.get("examples"):
            content.append("Examples:\n", style="bold")
            for example in info["examples"]:
                content.append(f"  {example}\n", style="dim")

        return Panel(
            content,
            title=f"[bold]Help: {command}[/bold]",
            border_style=self.theme.border,
        )

    def render_quick_help(self) -> Text:
        """Render quick help line."""
        text = Text()
        text.append("Commands: ", style="bold dim")
        text.append("/help", style="cyan")
        text.append(" | ", style="dim")
        text.append("/scenarios", style="cyan")
        text.append(" | ", style="dim")
        text.append("/project", style="cyan")
        text.append(" | ", style="dim")
        text.append("/stat", style="cyan")
        text.append(" | ", style="dim")
        text.append("/query", style="cyan")
        text.append(" | ", style="dim")
        text.append("/review", style="cyan")
        text.append(" | ", style="dim")
        text.append("/exit", style="cyan")
        return text
