"""Tests for project_import server module."""

from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from src.project_import.config import JoernConfig, ProjectImportConfig
from src.project_import.server import (
    JoernServerManager,
    LocalJoernRunner,
    DockerJoernRunner,
)


class TestLocalJoernRunner:
    """Tests for LocalJoernRunner."""

    def test_init_with_config(self, tmp_path):
        """Test initialization with JoernConfig."""
        config = JoernConfig(home=tmp_path / "joern", use_docker=False)
        runner = LocalJoernRunner(config)
        assert runner.config == config

    def test_find_joern_home(self, tmp_path):
        """Test finding Joern home directory."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        config = JoernConfig(home=joern_home)
        runner = LocalJoernRunner(config)

        assert runner.config.home == joern_home

    def test_is_running_true(self):
        """Test is_running returns True when server responds."""
        config = JoernConfig(use_docker=False)
        runner = LocalJoernRunner(config)

        # Mock the verification
        with patch.object(runner, "_verify_connection", return_value=True):
            assert runner.is_running() is True

    def test_is_running_false(self):
        """Test is_running returns False when server not running."""
        config = JoernConfig(use_docker=False)
        runner = LocalJoernRunner(config)

        with patch.object(runner, "_verify_connection", return_value=False):
            assert runner.is_running() is False

    def test_get_status_not_running(self):
        """Test get_status when server is not running."""
        config = JoernConfig(use_docker=False)
        runner = LocalJoernRunner(config)

        with patch.object(runner, "is_running", return_value=False):
            status = runner.get_status()
            assert status["running"] is False
            assert "endpoint" in status

    def test_get_status_running(self):
        """Test get_status when server is running."""
        config = JoernConfig(server_port=8080)
        runner = LocalJoernRunner(config)

        with patch.object(runner, "is_running", return_value=True):
            status = runner.get_status()
            assert status["running"] is True
            assert "8080" in status["endpoint"]


class TestDockerJoernRunner:
    """Tests for DockerJoernRunner."""

    def test_init_with_config(self):
        """Test initialization with JoernConfig."""
        config = JoernConfig(
            use_docker=True,
            docker_image="ghcr.io/joernio/joern:latest"
        )
        runner = DockerJoernRunner(config)
        assert runner.config == config
        assert runner.image == "ghcr.io/joernio/joern:latest"

    def test_default_image(self):
        """Test default Docker image."""
        config = JoernConfig(use_docker=True)
        runner = DockerJoernRunner(config)
        assert "joern" in runner.image

    @patch("subprocess.run")
    def test_is_docker_available_true(self, mock_run):
        """Test Docker availability check when Docker is available."""
        mock_run.return_value = MagicMock(returncode=0)

        config = JoernConfig(use_docker=True)
        runner = DockerJoernRunner(config)

        assert runner._check_docker_available() is True

    @patch("subprocess.run")
    def test_is_docker_available_false(self, mock_run):
        """Test Docker availability check when Docker is not available."""
        mock_run.side_effect = Exception("Docker not found")

        config = JoernConfig(use_docker=True)
        runner = DockerJoernRunner(config)

        assert runner._check_docker_available() is False

    def test_get_status_not_running(self):
        """Test get_status when container is not running."""
        config = JoernConfig(use_docker=True)
        runner = DockerJoernRunner(config)

        with patch.object(runner, "is_running", return_value=False):
            status = runner.get_status()
            assert status["running"] is False
            assert status["container_id"] is None


class TestJoernServerManager:
    """Tests for JoernServerManager."""

    def test_init_local_mode(self, tmp_path):
        """Test initialization in local mode."""
        config = JoernConfig(home=tmp_path / "joern", use_docker=False)
        manager = JoernServerManager(config)

        assert manager.mode == "local"
        assert isinstance(manager.runner, LocalJoernRunner)

    def test_init_docker_mode(self):
        """Test initialization in Docker mode."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        assert manager.mode == "docker"
        assert isinstance(manager.runner, DockerJoernRunner)

    def test_init_from_project_import_config(self, tmp_path):
        """Test initialization from ProjectImportConfig."""
        joern_config = JoernConfig(home=tmp_path / "joern", use_docker=False)
        import_config = ProjectImportConfig(joern=joern_config)

        manager = JoernServerManager(import_config)
        assert manager.mode == "local"
        assert manager.import_config == import_config

    def test_ensure_running_already_running(self):
        """Test ensure_running when already running."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager, "is_running", return_value=True):
            result = manager.ensure_running()
            assert result is True

    def test_ensure_running_starts_server(self):
        """Test ensure_running starts server when not running."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager, "is_running", return_value=False):
            with patch.object(manager, "start", return_value=True) as mock_start:
                result = manager.ensure_running()
                mock_start.assert_called_once()
                assert result is True

    def test_get_status(self):
        """Test get_status includes mode and workspace."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager._runner, "get_status", return_value={"running": True, "port": 8080}):
            status = manager.get_status()

            assert status["mode"] == "docker"
            assert "running" in status
            assert "current_workspace" in status

    def test_start(self):
        """Test start delegates to runner."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager._runner, "start", return_value=True) as mock_start:
            result = manager.start(timeout=60)
            mock_start.assert_called_once_with(60)
            assert result is True

    def test_stop(self):
        """Test stop delegates to runner and clears workspace."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)
        manager._current_workspace = "test.cpg"

        with patch.object(manager._runner, "stop", return_value=True) as mock_stop:
            result = manager.stop()
            mock_stop.assert_called_once()
            assert result is True
            assert manager._current_workspace is None

    def test_restart(self):
        """Test restart delegates to runner."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)
        manager._current_workspace = "test.cpg"

        with patch.object(manager._runner, "restart", return_value=True) as mock_restart:
            result = manager.restart(timeout=60)
            mock_restart.assert_called_once_with(60)
            assert result is True
            assert manager._current_workspace is None

    def test_is_running(self):
        """Test is_running delegates to runner."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager._runner, "is_running", return_value=True):
            assert manager.is_running() is True

    def test_run_frontend(self, tmp_path):
        """Test run_frontend delegates to runner."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        input_path = tmp_path / "source"
        output_path = tmp_path / "output.cpg"

        with patch.object(manager._runner, "run_frontend", return_value=True) as mock_run:
            result = manager.run_frontend(
                frontend_command="pysrc2cpg",
                input_path=input_path,
                output_path=output_path,
                exclude_patterns=["test"],
                timeout=600,
            )

            mock_run.assert_called_once_with(
                frontend_command="pysrc2cpg",
                input_path=input_path,
                output_path=output_path,
                exclude_patterns=["test"],
                timeout=600,
            )
            assert result is True

    def test_validate_config(self):
        """Test validate_config delegates to config."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        errors = manager.validate_config()
        assert isinstance(errors, list)

    def test_context_manager(self):
        """Test context manager behavior."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        with patch.object(manager, "ensure_running", return_value=True) as mock_ensure:
            with manager as m:
                assert m == manager
                mock_ensure.assert_called_once()

    def test_current_workspace_property(self):
        """Test current_workspace property."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        assert manager.current_workspace is None
        manager._current_workspace = "test.cpg"
        assert manager.current_workspace == "test.cpg"


class TestJoernServerManagerOpenWorkspace:
    """Tests for workspace operations."""

    def test_close_workspace_no_workspace(self):
        """Test closing workspace when none open."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        result = manager.close_workspace()
        assert result is True


@pytest.mark.asyncio
class TestJoernServerManagerAsync:
    """Async tests for JoernServerManager."""

    async def test_run_frontend_async(self, tmp_path):
        """Test async frontend execution."""
        config = JoernConfig(use_docker=True)
        manager = JoernServerManager(config)

        input_path = tmp_path / "source"
        output_path = tmp_path / "output.cpg"

        async_mock = AsyncMock(return_value=True)
        with patch.object(manager._runner, "run_frontend_async", async_mock):
            result = await manager.run_frontend_async(
                frontend_command="pysrc2cpg",
                input_path=input_path,
                output_path=output_path,
            )

            assert result is True
            async_mock.assert_called_once()
