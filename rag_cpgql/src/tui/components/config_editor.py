"""Configuration viewer/editor component."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import yaml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)

# Default config path
DEFAULT_CONFIG_PATH = Path("config.yaml")

# Editable sections (safe to modify at runtime)
EDITABLE_SECTIONS = ["llm", "retrieval", "analysis", "generation"]

# Read-only sections (should not be modified at runtime)
READONLY_SECTIONS = ["domain", "data", "joern"]


class ConfigEditor:
    """
    Interactive configuration viewer/editor.

    Provides safe viewing and editing of config.yaml parameters
    with validation and persistence.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        theme: Theme = DEFAULT_THEME,
    ):
        """
        Initialize config editor.

        Args:
            config_path: Path to config.yaml
            theme: Color theme
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.theme = theme
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.debug(f"Loaded config from: {self.config_path}")
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                self._config = {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = {}

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration."""
        return self._config.copy()

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get a specific configuration section."""
        return self._config.get(section)

    def render_overview(self) -> Panel:
        """Render configuration overview."""
        table = Table(
            show_header=True,
            header_style="bold",
            border_style=self.theme.border,
            expand=True,
        )

        table.add_column("Section", style="cyan")
        table.add_column("Keys", justify="right")
        table.add_column("Status")

        for section in sorted(self._config.keys()):
            value = self._config[section]
            key_count = len(value) if isinstance(value, dict) else 1

            if section in EDITABLE_SECTIONS:
                status = "[green]Editable[/green]"
            elif section in READONLY_SECTIONS:
                status = "[yellow]Read-only[/yellow]"
            else:
                status = "[dim]Unknown[/dim]"

            table.add_row(section, str(key_count), status)

        return Panel(
            table,
            title="[bold]Configuration[/bold]",
            subtitle=f"File: {self.config_path}",
            border_style=self.theme.border,
        )

    def render_section(self, section: str) -> Panel:
        """Render a specific section."""
        if section not in self._config:
            return Panel(
                f"[red]Section '{section}' not found[/red]",
                title="Error",
                border_style="red",
            )

        data = self._config[section]

        # Build tree view
        tree = Tree(f"[bold cyan]{section}[/bold cyan]")
        self._add_to_tree(tree, data)

        is_editable = section in EDITABLE_SECTIONS
        status = "[green]Editable[/green]" if is_editable else "[yellow]Read-only[/yellow]"

        return Panel(
            tree,
            title=f"[bold]Config: {section}[/bold]",
            subtitle=status,
            border_style=self.theme.border,
        )

    def _add_to_tree(self, tree: Tree, data: Any, prefix: str = ""):
        """Recursively add data to tree."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    branch = tree.add(f"[cyan]{key}[/cyan]")
                    self._add_to_tree(branch, value, f"{prefix}{key}.")
                elif isinstance(value, list):
                    branch = tree.add(f"[cyan]{key}[/cyan]: [dim][{len(value)} items][/dim]")
                    for i, item in enumerate(value[:5]):
                        branch.add(f"[dim]{i}:[/dim] {item}")
                    if len(value) > 5:
                        branch.add(f"[dim]... +{len(value) - 5} more[/dim]")
                else:
                    # Mask sensitive values
                    display_value = self._mask_sensitive(key, value)
                    tree.add(f"[cyan]{key}[/cyan]: {display_value}")
        else:
            tree.add(str(data))

    def _mask_sensitive(self, key: str, value: Any) -> str:
        """Mask sensitive values like passwords and API keys."""
        sensitive_keys = ["password", "secret", "key", "token", "auth"]

        if any(s in key.lower() for s in sensitive_keys):
            if isinstance(value, str) and len(value) > 4:
                return f"***{value[-4:]}"
            return "****"

        return str(value)

    def edit_value(
        self,
        section: str,
        key: str,
        value: Any,
    ) -> Tuple[bool, str]:
        """
        Edit a configuration value.

        Args:
            section: Configuration section
            key: Key within section (can use dot notation)
            value: New value

        Returns:
            Tuple of (success, message)
        """
        # Check if section is editable
        if section not in EDITABLE_SECTIONS:
            return False, f"Section '{section}' is read-only"

        if section not in self._config:
            return False, f"Section '{section}' not found"

        # Parse key path (e.g., "model.temperature")
        keys = key.split(".")
        target = self._config[section]

        # Navigate to parent
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                return False, f"Invalid key path: {key}"
            target = target[k]

        # Set value
        final_key = keys[-1]
        if final_key not in target:
            return False, f"Key '{final_key}' not found in {section}"

        old_value = target[final_key]

        # Type validation
        try:
            new_value = self._convert_value(value, type(old_value))
        except ValueError as e:
            return False, f"Invalid value: {e}"

        target[final_key] = new_value

        logger.info(f"Config changed: {section}.{key} = {new_value} (was: {old_value})")
        return True, f"Updated {section}.{key} = {new_value}"

    def _convert_value(self, value: str, target_type: type) -> Any:
        """Convert string value to target type."""
        if target_type == bool:
            if value.lower() in ("true", "yes", "1", "on"):
                return True
            elif value.lower() in ("false", "no", "0", "off"):
                return False
            raise ValueError(f"Cannot convert '{value}' to boolean")

        elif target_type == int:
            return int(value)

        elif target_type == float:
            return float(value)

        elif target_type == list:
            # Simple comma-separated list
            return [v.strip() for v in value.split(",")]

        else:
            return str(value)

    def save_changes(self) -> Tuple[bool, str]:
        """
        Save configuration changes to file.

        Returns:
            Tuple of (success, message)
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)

            logger.info(f"Saved config to: {self.config_path}")
            return True, f"Configuration saved to {self.config_path}"

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False, f"Failed to save: {e}"

    def reload(self):
        """Reload configuration from file."""
        self._load_config()

    def get_editable_keys(self, section: str) -> List[str]:
        """Get list of editable keys in a section."""
        if section not in EDITABLE_SECTIONS:
            return []

        data = self._config.get(section, {})
        return self._flatten_keys(data)

    def _flatten_keys(self, data: Dict, prefix: str = "") -> List[str]:
        """Flatten nested dict keys."""
        keys = []
        for key, value in data.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                keys.extend(self._flatten_keys(value, f"{full_key}."))
            else:
                keys.append(full_key)
        return keys
