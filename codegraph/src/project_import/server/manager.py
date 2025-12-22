"""
Joern Server Manager.

Unified interface for managing Joern server (local or Docker).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..config import JoernConfig, ProjectImportConfig
from .local import LocalJoernRunner
from .docker import DockerJoernRunner

logger = logging.getLogger(__name__)


class JoernServerManager:
    """
    Cross-platform Joern server management.

    Provides a unified interface for managing Joern server,
    whether running locally or in Docker.
    """

    def __init__(
        self,
        config: Union[JoernConfig, ProjectImportConfig],
    ):
        """
        Initialize server manager.

        Args:
            config: Joern configuration or full import configuration.
        """
        if isinstance(config, ProjectImportConfig):
            self.config = config.joern
            self.import_config = config
        else:
            self.config = config
            self.import_config = None

        # Initialize appropriate runner
        if self.config.use_docker:
            self._runner = DockerJoernRunner(self.config)
            self._mode = "docker"
        else:
            self._runner = LocalJoernRunner(self.config)
            self._mode = "local"

        self._current_workspace: Optional[str] = None

    @property
    def mode(self) -> str:
        """Get current mode ('local' or 'docker')."""
        return self._mode

    @property
    def runner(self) -> Union[LocalJoernRunner, DockerJoernRunner]:
        """Get underlying runner."""
        return self._runner

    def start(self, timeout: int = 90) -> bool:
        """
        Start Joern server.

        Args:
            timeout: Maximum seconds to wait for server to start.

        Returns:
            True if server started successfully.
        """
        return self._runner.start(timeout)

    def stop(self) -> bool:
        """
        Stop Joern server.

        Returns:
            True if server stopped.
        """
        self._current_workspace = None
        return self._runner.stop()

    def restart(self, timeout: int = 90) -> bool:
        """
        Restart Joern server.

        Args:
            timeout: Maximum seconds to wait for restart.

        Returns:
            True if server restarted successfully.
        """
        self._current_workspace = None
        return self._runner.restart(timeout)

    def is_running(self) -> bool:
        """Check if server is running and responsive."""
        return self._runner.is_running()

    def ensure_running(self, timeout: int = 90) -> bool:
        """
        Ensure server is running, starting it if necessary.

        Args:
            timeout: Maximum seconds to wait if starting.

        Returns:
            True if server is running.
        """
        if self.is_running():
            return True

        logger.info("Server not running, starting...")
        return self.start(timeout)

    def get_status(self) -> Dict:
        """
        Get server status information.

        Returns:
            Dictionary with status information.
        """
        status = self._runner.get_status()
        status["mode"] = self._mode
        status["current_workspace"] = self._current_workspace
        return status

    def get_client(self):
        """
        Get a connected JoernClient.

        Returns:
            Connected JoernClient instance.

        Raises:
            RuntimeError: If unable to connect.
        """
        from src.execution.joern_client import JoernClient

        client = JoernClient(
            server_endpoint=self.config.server_endpoint,
            workspace=self._current_workspace,
        )

        if not client.connect():
            raise RuntimeError(f"Failed to connect to Joern at {self.config.server_endpoint}")

        return client

    def open_workspace(self, cpg_name: str) -> bool:
        """
        Open a CPG workspace in Joern.

        Args:
            cpg_name: Name of the CPG file to open.

        Returns:
            True if workspace opened successfully.
        """
        if not self.ensure_running():
            return False

        try:
            client = self.get_client()

            # Try opening with just the name first
            result = client.execute_query(f'Joern.open("{cpg_name}")')

            if not result.get("success"):
                # Try with full path
                if self.config.workspace_path:
                    full_path = self.config.workspace_path / cpg_name
                    result = client.execute_query(f'Joern.open("{full_path}")')

            if result.get("success"):
                self._current_workspace = cpg_name
                logger.info(f"Opened workspace: {cpg_name}")
                client.close()
                return True
            else:
                logger.error(f"Failed to open workspace: {result.get('error')}")
                client.close()
                return False

        except Exception as e:
            logger.error(f"Error opening workspace: {e}")
            return False

    def close_workspace(self) -> bool:
        """
        Close current workspace.

        Returns:
            True if workspace closed successfully.
        """
        if not self._current_workspace:
            return True

        try:
            client = self.get_client()
            result = client.execute_query("Joern.close()")
            client.close()

            self._current_workspace = None
            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error closing workspace: {e}")
            return False

    @property
    def current_workspace(self) -> Optional[str]:
        """Get currently open workspace name."""
        return self._current_workspace

    def run_frontend(
        self,
        frontend_command: str,
        input_path: Path,
        output_path: Path,
        exclude_patterns: Optional[List[str]] = None,
        timeout: int = 3600,
    ) -> bool:
        """
        Run a Joern frontend to create CPG.

        Args:
            frontend_command: Frontend command (e.g., "c2cpg")
            input_path: Path to source code
            output_path: Path for output CPG file
            exclude_patterns: Patterns to exclude
            timeout: Maximum runtime in seconds

        Returns:
            True if frontend completed successfully.
        """
        return self._runner.run_frontend(
            frontend_command=frontend_command,
            input_path=input_path,
            output_path=output_path,
            exclude_patterns=exclude_patterns,
            timeout=timeout,
        )

    async def run_frontend_async(
        self,
        frontend_command: str,
        input_path: Path,
        output_path: Path,
        exclude_patterns: Optional[List[str]] = None,
        timeout: int = 3600,
        progress_callback=None,
    ) -> bool:
        """
        Run a Joern frontend asynchronously.

        Args:
            frontend_command: Frontend command
            input_path: Path to source code
            output_path: Path for output CPG file
            exclude_patterns: Patterns to exclude
            timeout: Maximum runtime in seconds
            progress_callback: Optional callback for progress updates

        Returns:
            True if frontend completed successfully.
        """
        return await self._runner.run_frontend_async(
            frontend_command=frontend_command,
            input_path=input_path,
            output_path=output_path,
            exclude_patterns=exclude_patterns,
            timeout=timeout,
            progress_callback=progress_callback,
        )

    def run_joern_parse(
        self,
        input_path: Path,
        output_path: Path,
        language: str,
        exclude_patterns: Optional[List[str]] = None,
        timeout: int = 3600,
    ) -> bool:
        """
        Run unified joern-parse command.

        Args:
            input_path: Path to source code
            output_path: Path for output CPG file
            language: Language flag (e.g., "C", "PYTHONSRC")
            exclude_patterns: Patterns to exclude
            timeout: Maximum runtime in seconds

        Returns:
            True if completed successfully.
        """
        # For local runner, check if joern-parse is available
        if isinstance(self._runner, LocalJoernRunner):
            joern_parse = self.config.get_joern_parse_path()
            if joern_parse:
                # Use joern-parse with --language flag
                import subprocess

                cmd = [
                    str(joern_parse),
                    str(input_path),
                    "--language", language,
                    "-o", str(output_path),
                ]

                if exclude_patterns:
                    for pattern in exclude_patterns:
                        cmd.extend(["--exclude", pattern])

                logger.info(f"Running joern-parse: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=str(self.config.home) if self.config.home else None,
                        env=self._runner._get_env(),
                    )

                    if result.returncode == 0 and output_path.exists():
                        logger.info(f"CPG created via joern-parse: {output_path}")
                        return True

                    logger.warning(f"joern-parse failed, falling back to specific frontend")

                except Exception as e:
                    logger.warning(f"joern-parse error: {e}, falling back to specific frontend")

        # Fallback: use specific frontend based on language
        frontend_map = {
            "C": "c2cpg",
            "CSHARPSRC": "csharp2cpg",
            "GOLANG": "gosrc2cpg",
            "JAVASRC": "javasrc2cpg",
            "JAVASCRIPT": "jssrc2cpg",
            "KOTLIN": "kotlin2cpg",
            "PHP": "php2cpg",
            "PYTHONSRC": "pysrc2cpg",
            "RUBYSRC": "rubysrc2cpg",
            "SWIFTSRC": "swiftsrc2cpg",
            "GHIDRA": "ghidra2cpg",
        }

        frontend_command = frontend_map.get(language)
        if not frontend_command:
            raise ValueError(f"Unknown language: {language}")

        return self.run_frontend(
            frontend_command=frontend_command,
            input_path=input_path,
            output_path=output_path,
            exclude_patterns=exclude_patterns,
            timeout=timeout,
        )

    def validate_config(self) -> List[str]:
        """
        Validate server configuration.

        Returns:
            List of error messages (empty if valid).
        """
        return self.config.validate()

    def __enter__(self):
        """Context manager entry."""
        self.ensure_running()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Don't stop the server automatically - it may be used by other processes
        pass
