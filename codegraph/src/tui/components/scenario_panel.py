"""Scenario selection panel using Rich."""

from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME


# Scenario definitions with metadata
SCENARIOS: Dict[str, Dict] = {
    "01": {
        "name": "Onboarding",
        "description": "Get started with codebase exploration",
        "group": "Exploration",
        "examples": ["What does function X do?", "Explain module Y"],
    },
    "02": {
        "name": "Security Audit",
        "description": "Analyze code for security vulnerabilities",
        "group": "Security",
        "examples": ["Find SQL injection risks", "Check input validation"],
    },
    "03": {
        "name": "Documentation",
        "description": "Generate and analyze documentation",
        "group": "Exploration",
        "examples": ["Document function X", "What does this module do?"],
    },
    "04": {
        "name": "Feature Development",
        "description": "Understand code for adding new features",
        "group": "Architecture",
        "examples": ["Where to add new handler?", "How to extend X?"],
    },
    "05": {
        "name": "Refactoring",
        "description": "Find refactoring opportunities",
        "group": "Quality",
        "examples": ["Find duplicate code", "Suggest improvements"],
    },
    "06": {
        "name": "Performance",
        "description": "Identify performance bottlenecks",
        "group": "Performance",
        "examples": ["Find slow functions", "Analyze memory usage"],
    },
    "07": {
        "name": "Test Coverage",
        "description": "Analyze test coverage and suggest tests",
        "group": "Quality",
        "examples": ["What code is untested?", "Suggest test cases"],
    },
    "08": {
        "name": "Compliance",
        "description": "Check coding standards compliance",
        "group": "Quality",
        "examples": ["Check naming conventions", "Find style violations"],
    },
    "09": {
        "name": "Code Review",
        "description": "Assist with code review process",
        "group": "Quality",
        "examples": ["Review this function", "Find issues in patch"],
    },
    "10": {
        "name": "Cross-Repo Impact",
        "description": "Analyze cross-repository dependencies",
        "group": "Architecture",
        "examples": ["What depends on X?", "Impact of changing Y?"],
    },
    "11": {
        "name": "Architecture Violations",
        "description": "Find architecture pattern violations",
        "group": "Architecture",
        "examples": ["Find layer violations", "Check dependencies"],
    },
    "12": {
        "name": "Tech Debt",
        "description": "Identify technical debt areas",
        "group": "Maintenance",
        "examples": ["Find TODO comments", "List deprecated usage"],
    },
    "13": {
        "name": "Mass Refactoring",
        "description": "Plan large-scale code changes",
        "group": "Maintenance",
        "examples": ["Find all uses of X", "Rename pattern Y"],
    },
    "14": {
        "name": "Security Incident",
        "description": "Analyze potential security incidents",
        "group": "Security",
        "examples": ["Trace data flow from X", "Find attack vectors"],
    },
    "15": {
        "name": "Debugging",
        "description": "Assist with debugging issues",
        "group": "Exploration",
        "examples": ["Trace call to X", "Find error handlers"],
    },
    "16": {
        "name": "Entry Points",
        "description": "Find and analyze entry points",
        "group": "Security",
        "examples": ["List API endpoints", "Find exposed functions"],
    },
}

# Group colors
GROUP_STYLES: Dict[str, str] = {
    "Exploration": "cyan",
    "Security": "red",
    "Quality": "green",
    "Performance": "yellow",
    "Architecture": "blue",
    "Maintenance": "magenta",
}


class ScenarioPanel:
    """Interactive scenario selection panel."""

    def __init__(self, theme: Theme = DEFAULT_THEME):
        self.theme = theme
        self.current_scenario: Optional[str] = None
        self.scenarios = SCENARIOS

    def render(self, show_examples: bool = False) -> Panel:
        """
        Render the scenario selection panel.

        Args:
            show_examples: Whether to show example queries

        Returns:
            Rich Panel with scenarios table
        """
        table = Table(
            show_header=True,
            header_style="bold",
            border_style=self.theme.border,
            expand=True,
        )

        table.add_column("#", style="cyan", width=3)
        table.add_column("Scenario", style="bold")
        table.add_column("Description")
        table.add_column("Group", width=12)

        for scenario_id, info in self.scenarios.items():
            is_active = scenario_id == self.current_scenario
            group_style = GROUP_STYLES.get(info["group"], "white")

            # Format row
            num = f"[bold green]{scenario_id}[/]" if is_active else scenario_id
            name = f"[bold green]{info['name']}[/]" if is_active else info['name']
            desc = info['description']
            group = f"[{group_style}]{info['group']}[/]"

            if is_active:
                desc = f"[green]{desc}[/]"

            table.add_row(num, name, desc, group)

        return Panel(
            table,
            title="[bold]Scenarios[/bold]",
            subtitle="Use /select <n> to choose",
            border_style=self.theme.border,
        )

    def render_compact(self) -> Text:
        """Render a compact scenario list."""
        text = Text()
        text.append("Scenarios: ", style="bold")

        for i, (sid, info) in enumerate(self.scenarios.items()):
            if i > 0:
                text.append(" | ", style="dim")

            style = "bold green" if sid == self.current_scenario else "dim"
            text.append(f"{sid}:{info['name']}", style=style)

        return text

    def render_scenario_detail(self, scenario_id: str) -> Panel:
        """Render detailed view of a single scenario."""
        if scenario_id not in self.scenarios:
            return Panel(
                f"[red]Scenario '{scenario_id}' not found[/red]",
                title="Error",
                border_style="red",
            )

        info = self.scenarios[scenario_id]
        group_style = GROUP_STYLES.get(info["group"], "white")

        content = Text()
        content.append(f"{info['name']}\n", style="bold cyan")
        content.append(f"{info['description']}\n\n", style="white")

        content.append("Group: ", style="bold")
        content.append(f"{info['group']}\n\n", style=group_style)

        content.append("Example queries:\n", style="bold")
        for example in info.get("examples", []):
            content.append(f"  - {example}\n", style="dim")

        return Panel(
            content,
            title=f"[bold]Scenario {scenario_id}[/bold]",
            border_style=self.theme.border,
        )

    def select_scenario(self, scenario_id: str) -> Tuple[bool, str]:
        """
        Select a scenario.

        Args:
            scenario_id: Two-digit scenario ID (e.g., "01")

        Returns:
            Tuple of (success, message)
        """
        # Normalize ID
        if scenario_id.isdigit():
            scenario_id = scenario_id.zfill(2)

        if scenario_id not in self.scenarios:
            return False, f"Unknown scenario: {scenario_id}"

        self.current_scenario = scenario_id
        info = self.scenarios[scenario_id]
        return True, f"Selected: {info['name']} ({scenario_id})"

    def get_current_scenario(self) -> Optional[Dict]:
        """Get current scenario info."""
        if self.current_scenario:
            return self.scenarios.get(self.current_scenario)
        return None

    def get_scenario_by_name(self, name: str) -> Optional[str]:
        """Find scenario ID by name (partial match)."""
        name_lower = name.lower()
        for sid, info in self.scenarios.items():
            if name_lower in info["name"].lower():
                return sid
        return None

    def get_scenarios_by_group(self, group: str) -> List[str]:
        """Get all scenario IDs in a group."""
        return [
            sid for sid, info in self.scenarios.items()
            if info["group"].lower() == group.lower()
        ]
