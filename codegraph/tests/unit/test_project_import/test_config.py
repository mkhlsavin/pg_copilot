"""Tests for project_import configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.project_import.config import (
    JoernConfig,
    ProjectImportConfig,
    get_config,
    load_config_from_yaml,
    load_project_import_config,
    reset_config,
)


class TestJoernConfig:
    """Tests for JoernConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = JoernConfig()
        assert config.server_host == "localhost"
        assert config.server_port == 8080
        assert config.memory_gb == 16
        assert config.query_timeout == 60
        assert config.use_docker is False
        assert config.docker_image == "ghcr.io/joernio/joern:latest"

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = JoernConfig(
            server_host="192.168.1.100",
            server_port=9090,
            memory_gb=32,
            use_docker=True,
            docker_image="custom/joern:v1.0",
        )
        assert config.server_host == "192.168.1.100"
        assert config.server_port == 9090
        assert config.memory_gb == 32
        assert config.use_docker is True
        assert config.docker_image == "custom/joern:v1.0"

    def test_joern_home_from_env(self, tmp_path):
        """Test Joern home detection from environment variable."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        with patch.dict(os.environ, {"JOERN_HOME": str(joern_home)}):
            config = JoernConfig(home=None)
            assert config.home == joern_home

    def test_joern_home_explicit(self, tmp_path):
        """Test explicit Joern home path."""
        joern_home = tmp_path / "joern"
        config = JoernConfig(home=joern_home)
        assert config.home == joern_home

    def test_joern_home_auto_string(self):
        """Test 'auto' string triggers auto-detection."""
        with patch.object(JoernConfig, "_detect_joern_home", return_value=Path("/detected/joern")):
            config = JoernConfig(home="auto")
            assert config.home == Path("/detected/joern")

    def test_server_endpoint(self):
        """Test server endpoint property."""
        config = JoernConfig(server_host="example.com", server_port=8888)
        assert config.server_endpoint == "example.com:8888"

    def test_joern_cli_path(self, tmp_path):
        """Test joern_cli_path property."""
        config = JoernConfig(home=tmp_path / "joern")
        assert config.joern_cli_path == tmp_path / "joern" / "joern-cli"

    def test_joern_cli_path_none(self):
        """Test joern_cli_path when home is None."""
        config = JoernConfig(home=None)
        config.home = None  # Force home to None
        assert config.joern_cli_path is None

    def test_workspace_path(self, tmp_path):
        """Test workspace_path property."""
        config = JoernConfig(home=tmp_path / "joern")
        assert config.workspace_path == tmp_path / "joern" / "workspace"

    def test_validate_docker_mode(self):
        """Test validation passes in Docker mode without local Joern."""
        config = JoernConfig(use_docker=True, home=None)
        errors = config.validate()
        assert not errors

    def test_validate_local_mode_missing_home(self):
        """Test validation fails when Joern home is missing."""
        config = JoernConfig(use_docker=False, home=None)
        config.home = None  # Force home to None
        errors = config.validate()
        assert any("home" in e.lower() for e in errors)

    def test_validate_invalid_memory(self):
        """Test validation fails for invalid memory."""
        config = JoernConfig(memory_gb=0)
        errors = config.validate()
        assert any("memory" in e.lower() for e in errors)

    def test_validate_invalid_port(self):
        """Test validation fails for invalid port."""
        config = JoernConfig(server_port=99999)
        errors = config.validate()
        assert any("port" in e.lower() for e in errors)

    def test_get_frontend_path(self, tmp_path):
        """Test frontend path resolution."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        # Create a frontend binary
        frontend_path = joern_cli / "pysrc2cpg"
        frontend_path.touch()

        config = JoernConfig(home=joern_home)
        result = config.get_frontend_path("pysrc2cpg")
        assert result == frontend_path

    def test_get_frontend_path_bat(self, tmp_path):
        """Test frontend path resolution for .bat files (Windows)."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        # Create a .bat frontend
        frontend_path = joern_cli / "pysrc2cpg.bat"
        frontend_path.touch()

        config = JoernConfig(home=joern_home)
        result = config.get_frontend_path("pysrc2cpg")
        assert result == frontend_path

    def test_get_frontend_path_not_found(self, tmp_path):
        """Test frontend path returns None when not found."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        config = JoernConfig(home=joern_home)
        result = config.get_frontend_path("nonexistent")
        assert result is None


class TestProjectImportConfig:
    """Tests for ProjectImportConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProjectImportConfig()
        assert config.batch_size == 10000
        assert isinstance(config.default_excludes, list)
        assert ".git" in config.default_excludes
        assert "node_modules" in config.default_excludes

    def test_custom_workspace_path(self, tmp_path):
        """Test custom workspace path."""
        config = ProjectImportConfig(workspace_path=tmp_path / "workspace")
        assert config.workspace_path == tmp_path / "workspace"

    def test_workspace_path_from_string(self, tmp_path):
        """Test workspace path conversion from string."""
        config = ProjectImportConfig(workspace_path=str(tmp_path / "workspace"))
        assert config.workspace_path == tmp_path / "workspace"

    def test_ensure_paths(self, tmp_path):
        """Test directory creation."""
        workspace = tmp_path / "workspace"
        duckdb = tmp_path / "duckdb"

        config = ProjectImportConfig(workspace_path=workspace, duckdb_path=duckdb)
        config.ensure_paths()

        assert workspace.exists()
        assert duckdb.exists()

    def test_validate_batch_size_too_small(self):
        """Test validation fails for small batch size."""
        config = ProjectImportConfig(batch_size=50)
        errors = config.validate()
        assert any("batch" in e.lower() for e in errors)

    def test_validate_propagates_joern_errors(self):
        """Test validation includes Joern config errors."""
        config = ProjectImportConfig()
        config.joern.memory_gb = 0  # Invalid
        errors = config.validate()
        assert any("memory" in e.lower() for e in errors)


class TestLoadConfig:
    """Tests for configuration loading functions."""

    def test_load_config_from_yaml(self, tmp_path):
        """Test YAML config loading."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
project_import:
  joern:
    use_docker: true
    memory_gb: 32
  batch_size: 5000
""")
        config = load_config_from_yaml(config_file)
        assert config["project_import"]["joern"]["use_docker"] is True
        assert config["project_import"]["joern"]["memory_gb"] == 32
        assert config["project_import"]["batch_size"] == 5000

    def test_load_config_with_env_interpolation(self, tmp_path):
        """Test environment variable interpolation in YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
project_import:
  joern:
    home: ${TEST_JOERN_HOME:-/default/joern}
""")
        with patch.dict(os.environ, {"TEST_JOERN_HOME": "/custom/joern"}):
            config = load_config_from_yaml(config_file)
            assert config["project_import"]["joern"]["home"] == "/custom/joern"

    def test_load_config_with_default_env(self, tmp_path):
        """Test environment variable default values."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
project_import:
  joern:
    home: ${NONEXISTENT_VAR:-/default/path}
""")
        with patch.dict(os.environ, {}, clear=False):
            # Make sure NONEXISTENT_VAR is not set
            os.environ.pop("NONEXISTENT_VAR", None)
            config = load_config_from_yaml(config_file)
            assert config["project_import"]["joern"]["home"] == "/default/path"

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading non-existent config returns empty dict."""
        config = load_config_from_yaml(tmp_path / "nonexistent.yaml")
        assert config == {}

    def test_load_project_import_config(self, tmp_path):
        """Test full config loading."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
project_import:
  joern:
    use_docker: true
    memory_gb: 24
  batch_size: 20000
""")
        config = load_project_import_config(config_file)
        assert isinstance(config, ProjectImportConfig)
        assert config.joern.use_docker is True
        assert config.joern.memory_gb == 24
        assert config.batch_size == 20000

    def test_get_config_singleton(self, tmp_path):
        """Test get_config returns singleton."""
        reset_config()
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
project_import:
  batch_size: 15000
""")
        config1 = get_config(config_file)
        config2 = get_config()  # Should return cached
        assert config1 is config2
        reset_config()

    def test_reset_config(self, tmp_path):
        """Test config reset."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config1 = get_config(config_file)
        reset_config()
        config2 = get_config(config_file)
        assert config1 is not config2
        reset_config()
