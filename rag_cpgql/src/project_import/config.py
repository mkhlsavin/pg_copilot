"""
Project Import Configuration.

Configuration management for project import pipeline.
Supports YAML config, environment variables, and auto-detection.
"""

import logging
import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class JoernConfig:
    """Configuration for Joern installation and server."""

    home: Optional[Path] = None
    server_host: str = "localhost"
    server_port: int = 8080
    memory_gb: int = 16
    query_timeout: int = 60
    use_docker: bool = False
    docker_image: str = "ghcr.io/joernio/joern:latest"
    docker_workspace_mount: str = "/workspace"

    def __post_init__(self):
        """Auto-detect Joern home if not specified."""
        if self.home is None:
            self.home = self._detect_joern_home()
        elif isinstance(self.home, str):
            if self.home.lower() == "auto":
                self.home = self._detect_joern_home()
            else:
                self.home = Path(self.home)

    def _detect_joern_home(self) -> Optional[Path]:
        """
        Auto-detect Joern installation path.

        Checks in order:
        1. JOERN_HOME environment variable
        2. Common installation paths
        3. PATH lookup for joern binary
        """
        # Check environment variable
        env_home = os.environ.get("JOERN_HOME")
        if env_home:
            path = Path(env_home)
            if path.exists():
                logger.info(f"Found Joern via JOERN_HOME: {path}")
                return path

        # Check common paths
        system = platform.system()
        common_paths = []

        if system == "Windows":
            common_paths = [
                Path("C:/Users") / os.environ.get("USERNAME", "user") / "joern",
                Path("C:/joern"),
                Path(os.environ.get("LOCALAPPDATA", "")) / "joern",
                Path(os.environ.get("PROGRAMFILES", "")) / "joern",
            ]
        elif system == "Darwin":  # macOS
            common_paths = [
                Path.home() / "joern",
                Path("/usr/local/joern"),
                Path("/opt/joern"),
                Path.home() / ".local" / "joern",
            ]
        else:  # Linux
            common_paths = [
                Path.home() / "joern",
                Path("/opt/joern"),
                Path("/usr/local/joern"),
                Path.home() / ".local" / "joern",
            ]

        for path in common_paths:
            if path.exists() and (path / "joern-cli").exists():
                logger.info(f"Found Joern at common path: {path}")
                return path

        # Try to find joern in PATH
        joern_bin = shutil.which("joern")
        if joern_bin:
            # joern binary is usually in joern-cli/ subdirectory
            joern_path = Path(joern_bin).resolve()
            # Go up to find the joern home
            for parent in joern_path.parents:
                if (parent / "joern-cli").exists():
                    logger.info(f"Found Joern via PATH: {parent}")
                    return parent

        logger.warning("Could not auto-detect Joern installation")
        return None

    @property
    def joern_cli_path(self) -> Optional[Path]:
        """Get path to joern-cli directory."""
        if self.home:
            return self.home / "joern-cli"
        return None

    @property
    def workspace_path(self) -> Optional[Path]:
        """Get path to Joern workspace directory."""
        if self.home:
            return self.home / "workspace"
        return None

    def get_frontend_path(self, frontend_command: str) -> Optional[Path]:
        """
        Get full path to a frontend binary.

        Checks multiple locations:
        1. joern-cli/{command}
        2. joern-cli/{command}.bat (Windows)
        3. joern-cli/bin/{command}
        4. joern-cli/frontends/{command}/bin/{command}
        """
        if not self.joern_cli_path:
            return None

        candidates = [
            self.joern_cli_path / frontend_command,
            self.joern_cli_path / f"{frontend_command}.bat",
            self.joern_cli_path / "bin" / frontend_command,
            self.joern_cli_path / "bin" / f"{frontend_command}.bat",
            self.joern_cli_path / "frontends" / frontend_command / "bin" / frontend_command,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def get_joern_parse_path(self) -> Optional[Path]:
        """Get path to joern-parse unified command."""
        return self.get_frontend_path("joern-parse")

    @property
    def server_endpoint(self) -> str:
        """Get server endpoint string."""
        return f"{self.server_host}:{self.server_port}"

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of error messages (empty if valid).
        """
        errors = []

        if not self.use_docker:
            if self.home is None:
                errors.append("Joern home not set and could not be auto-detected")
            elif not self.home.exists():
                errors.append(f"Joern home does not exist: {self.home}")
            elif not self.joern_cli_path or not self.joern_cli_path.exists():
                errors.append(f"joern-cli not found at: {self.joern_cli_path}")

        if self.memory_gb < 1:
            errors.append(f"Invalid memory setting: {self.memory_gb}GB (minimum 1GB)")

        if self.server_port < 1 or self.server_port > 65535:
            errors.append(f"Invalid server port: {self.server_port}")

        return errors


@dataclass
class ProjectImportConfig:
    """Configuration for project import pipeline."""

    joern: JoernConfig = field(default_factory=JoernConfig)
    workspace_path: Optional[Path] = None
    duckdb_path: Optional[Path] = None
    batch_size: int = 10000
    default_excludes: List[str] = field(default_factory=lambda: [
        ".git", ".svn", ".hg",
        "node_modules", "__pycache__", ".venv", "venv",
        "vendor", "third_party", "build", "dist", "target",
        "bin", "obj", ".idea", ".vscode",
    ])

    def __post_init__(self):
        """Initialize paths."""
        if self.workspace_path is None and self.joern.workspace_path:
            self.workspace_path = self.joern.workspace_path

        if self.duckdb_path is None:
            self.duckdb_path = Path("./data/projects")

        if isinstance(self.workspace_path, str):
            self.workspace_path = Path(self.workspace_path)

        if isinstance(self.duckdb_path, str):
            self.duckdb_path = Path(self.duckdb_path)

    def ensure_paths(self):
        """Create required directories if they don't exist."""
        if self.workspace_path:
            self.workspace_path.mkdir(parents=True, exist_ok=True)

        if self.duckdb_path:
            self.duckdb_path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of error messages (empty if valid).
        """
        errors = self.joern.validate()

        if self.batch_size < 100:
            errors.append(f"Batch size too small: {self.batch_size} (minimum 100)")

        return errors


def load_config_from_yaml(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Supports environment variable interpolation with ${VAR} or ${VAR:-default} syntax.
    """
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Interpolate environment variables
    import re

    def replace_env(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return os.environ.get(var_name, default)
        else:
            return os.environ.get(var_expr, match.group(0))

    content = re.sub(r"\$\{([^}]+)\}", replace_env, content)

    return yaml.safe_load(content) or {}


def load_project_import_config(config_path: Optional[Path] = None) -> ProjectImportConfig:
    """
    Load project import configuration.

    Args:
        config_path: Path to config.yaml (default: ./config.yaml)

    Returns:
        ProjectImportConfig instance.
    """
    if config_path is None:
        config_path = Path("config.yaml")

    config_data = load_config_from_yaml(config_path)

    # Get project_import section
    import_config = config_data.get("project_import", {})
    joern_config_data = import_config.get("joern", {})

    # Also check top-level joern section for backward compatibility
    if not joern_config_data:
        joern_config_data = config_data.get("joern", {})

    # Build JoernConfig
    joern_config = JoernConfig(
        home=joern_config_data.get("home") or joern_config_data.get("installation_path"),
        server_host=joern_config_data.get("server_host", "localhost"),
        server_port=joern_config_data.get("server_port", 8080),
        memory_gb=joern_config_data.get("memory_gb", 16),
        query_timeout=joern_config_data.get("query_timeout", 60),
        use_docker=joern_config_data.get("use_docker", False),
        docker_image=joern_config_data.get("docker_image", "ghcr.io/joernio/joern:latest"),
    )

    # Build ProjectImportConfig
    return ProjectImportConfig(
        joern=joern_config,
        workspace_path=import_config.get("workspace_path"),
        duckdb_path=import_config.get("duckdb_path"),
        batch_size=import_config.get("batch_size", 10000),
        default_excludes=import_config.get("default_excludes", [
            ".git", ".svn", ".hg",
            "node_modules", "__pycache__", ".venv", "venv",
            "vendor", "third_party", "build", "dist", "target",
        ]),
    )


# Singleton for global config
_global_config: Optional[ProjectImportConfig] = None


def get_config(config_path: Optional[Path] = None) -> ProjectImportConfig:
    """
    Get global project import configuration.

    Loads and caches configuration on first call.

    Args:
        config_path: Path to config.yaml (only used on first call)

    Returns:
        ProjectImportConfig instance.
    """
    global _global_config

    if _global_config is None:
        _global_config = load_project_import_config(config_path)

    return _global_config


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _global_config
    _global_config = None
