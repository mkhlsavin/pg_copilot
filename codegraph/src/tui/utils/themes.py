"""TUI Color Themes using Rich styles."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Theme:
    """Color theme for TUI."""

    # Main elements
    title: str = "bold cyan"
    subtitle: str = "dim cyan"

    # Messages
    user_message: str = "green"
    assistant_message: str = "blue"
    system_message: str = "dim yellow"
    error_message: str = "bold red"
    warning_message: str = "yellow"
    success_message: str = "bold green"

    # UI elements
    border: str = "cyan"
    panel_title: str = "bold white"
    prompt: str = "bold green"

    # Scenarios
    scenario_active: str = "bold green"
    scenario_inactive: str = "dim white"
    scenario_number: str = "cyan"

    # Status
    status_running: str = "yellow"
    status_complete: str = "green"
    status_failed: str = "red"

    # Code
    code_block: str = "white on grey23"
    sql_query: str = "cyan"
    function_name: str = "bold yellow"
    file_path: str = "blue underline"

    # Progress
    progress_bar: str = "cyan"
    progress_text: str = "white"


# Default theme instance
DEFAULT_THEME = Theme()


# Alternative themes
DARK_THEME = Theme(
    title="bold magenta",
    border="magenta",
    prompt="bold magenta",
)

LIGHT_THEME = Theme(
    title="bold blue",
    border="blue",
    code_block="black on grey85",
)


def get_theme(name: str = "default") -> Theme:
    """Get theme by name."""
    themes: Dict[str, Theme] = {
        "default": DEFAULT_THEME,
        "dark": DARK_THEME,
        "light": LIGHT_THEME,
    }
    return themes.get(name, DEFAULT_THEME)
