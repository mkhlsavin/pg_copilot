"""
Joern Configuration Module.

Centralized configuration for Joern CPG server and paths.
All Joern-related configuration should be accessed through this module.

Environment Variables:
- JOERN_ENDPOINT: Joern server endpoint (default: localhost:8080)
- JOERN_HOME: Path to Joern installation directory
- JOERN_CPG_PATH: Path to CPG file (relative to JOERN_HOME or absolute)
- JOERN_SOURCE_PATH: Path to source code directory
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for config values
_config_cache: dict = {}


def _load_yaml_config() -> dict:
    """Load config.yaml file if available."""
    if "yaml" in _config_cache:
        return _config_cache["yaml"]

    config = {}
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}")

    _config_cache["yaml"] = config
    return config


def get_joern_endpoint() -> str:
    """Get Joern server endpoint from environment or config.

    Priority:
    1. JOERN_ENDPOINT environment variable
    2. config.yaml joern.endpoint
    3. Default: localhost:8080

    Returns:
        Joern server endpoint in format "host:port"
    """
    # Check environment first
    env_endpoint = os.environ.get("JOERN_ENDPOINT")
    if env_endpoint:
        return env_endpoint

    # Check config.yaml
    config = _load_yaml_config()
    yaml_endpoint = config.get("joern", {}).get("endpoint")
    if yaml_endpoint:
        return yaml_endpoint

    # Default for development
    logger.debug("Using default Joern endpoint localhost:8080")
    return "localhost:8080"


def get_joern_home() -> Optional[Path]:
    """Get Joern installation directory.

    Priority:
    1. JOERN_HOME environment variable
    2. config.yaml joern.home
    3. None (not configured)

    Returns:
        Path to Joern home directory or None if not configured
    """
    # Check environment first
    env_home = os.environ.get("JOERN_HOME")
    if env_home:
        return Path(env_home)

    # Check config.yaml
    config = _load_yaml_config()
    yaml_home = config.get("joern", {}).get("home")
    if yaml_home:
        # Resolve environment variables in path
        yaml_home = os.path.expandvars(yaml_home)
        return Path(yaml_home)

    return None


def get_joern_cpg_path() -> Optional[Path]:
    """Get path to CPG file.

    Priority:
    1. JOERN_CPG_PATH environment variable
    2. config.yaml joern.cpg_path
    3. None (not configured)

    Returns:
        Absolute path to CPG file or None if not configured
    """
    # Check environment first
    env_path = os.environ.get("JOERN_CPG_PATH")
    if env_path:
        path = Path(env_path)
        if path.is_absolute():
            return path
        # Relative to JOERN_HOME
        home = get_joern_home()
        if home:
            return home / path
        return path

    # Check config.yaml
    config = _load_yaml_config()
    yaml_path = config.get("joern", {}).get("cpg_path")
    if yaml_path:
        yaml_path = os.path.expandvars(yaml_path)
        path = Path(yaml_path)
        if path.is_absolute():
            return path
        home = get_joern_home()
        if home:
            return home / path
        return path

    return None


def get_joern_source_path() -> Optional[Path]:
    """Get path to source code directory.

    Priority:
    1. JOERN_SOURCE_PATH environment variable
    2. config.yaml joern.source_path
    3. None (not configured)

    Returns:
        Absolute path to source directory or None if not configured
    """
    # Check environment first
    env_path = os.environ.get("JOERN_SOURCE_PATH")
    if env_path:
        path = Path(env_path)
        if path.is_absolute():
            return path
        home = get_joern_home()
        if home:
            return home / path
        return path

    # Check config.yaml
    config = _load_yaml_config()
    yaml_path = config.get("joern", {}).get("source_path")
    if yaml_path:
        yaml_path = os.path.expandvars(yaml_path)
        path = Path(yaml_path)
        if path.is_absolute():
            return path
        home = get_joern_home()
        if home:
            return home / path
        return path

    return None


def clear_config_cache() -> None:
    """Clear the configuration cache. Useful for testing."""
    _config_cache.clear()
