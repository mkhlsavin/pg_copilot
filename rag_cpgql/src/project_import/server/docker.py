"""
Docker Joern Runner.

Manages Joern running in Docker container.
"""

import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..config import JoernConfig

logger = logging.getLogger(__name__)


class DockerJoernRunner:
    """
    Manages Joern running in Docker container.

    Provides a portable way to run Joern without local installation.
    """

    def __init__(self, config: JoernConfig):
        """
        Initialize Docker Joern runner.

        Args:
            config: Joern configuration.
        """
        self.config = config
        self.container_name = "joern-server"
        self._container_id: Optional[str] = None

    @property
    def image(self) -> str:
        """Get Docker image name."""
        return self.config.docker_image

    @property
    def workspace_mount(self) -> str:
        """Get container workspace mount path."""
        return self.config.docker_workspace_mount

    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_container_id(self) -> Optional[str]:
        """Get ID of existing container if running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            container_id = result.stdout.strip()
            return container_id if container_id else None
        except Exception:
            return None

    def _remove_container(self):
        """Remove existing container if any."""
        try:
            subprocess.run(
                ["docker", "rm", "-f", self.container_name],
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass

    def start(self, timeout: int = 120) -> bool:
        """
        Start Joern server in Docker container.

        Args:
            timeout: Maximum seconds to wait for server to start.

        Returns:
            True if server started successfully.

        Raises:
            RuntimeError: If Docker is not available or server fails to start.
        """
        if not self._check_docker_available():
            raise RuntimeError("Docker is not available")

        # Check if already running
        existing_id = self._get_container_id()
        if existing_id:
            self._container_id = existing_id
            if self.is_running():
                logger.info(f"Joern container already running: {existing_id}")
                return True
            # Container exists but not responsive, restart it
            self._remove_container()

        # Ensure workspace directory exists
        workspace_path = self.config.workspace_path
        if workspace_path:
            workspace_path.mkdir(parents=True, exist_ok=True)

        # Build docker run command
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "-p", f"{self.config.server_port}:8080",
        ]

        # Mount workspace
        if workspace_path:
            cmd.extend(["-v", f"{workspace_path.absolute()}:{self.workspace_mount}"])

        # Set memory limit
        cmd.extend(["-e", f"JAVA_OPTS=-Xmx{self.config.memory_gb}g"])

        # Add image and command
        cmd.extend([
            self.image,
            "joern",
            "--server",
            "--server-host", "0.0.0.0",
            "--server-port", "8080",
        ])

        logger.info(f"Starting Joern container: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                raise RuntimeError(f"Failed to start container: {result.stderr}")

            self._container_id = result.stdout.strip()[:12]
            logger.info(f"Container started: {self._container_id}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout starting Docker container")

        # Wait for server to be ready
        if not self._wait_for_server(timeout):
            self.stop()
            raise RuntimeError(f"Joern server did not start within {timeout} seconds")

        logger.info(f"Joern container ready at {self.config.server_endpoint}")
        return True

    def _wait_for_server(self, timeout: int) -> bool:
        """Wait for server to become responsive."""
        import socket

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.config.server_host, self.config.server_port))
                sock.close()

                if result == 0:
                    # Verify server is responsive
                    if self._verify_connection():
                        return True
            except Exception:
                pass

            time.sleep(2)

        return False

    def _verify_connection(self) -> bool:
        """Verify Joern server is responsive."""
        try:
            from src.execution.joern_client import JoernClient

            client = JoernClient(server_endpoint=self.config.server_endpoint)
            if client.connect():
                client.close()
                return True
        except Exception as e:
            logger.debug(f"Connection verification failed: {e}")

        return False

    def stop(self) -> bool:
        """
        Stop Joern container.

        Returns:
            True if container stopped.
        """
        logger.info("Stopping Joern container...")

        try:
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                timeout=30,
            )
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False

        self._container_id = None
        logger.info("Joern container stopped")
        return True

    def restart(self, timeout: int = 120) -> bool:
        """
        Restart Joern container.

        Args:
            timeout: Maximum seconds to wait for restart.

        Returns:
            True if container restarted successfully.
        """
        self.stop()
        time.sleep(2)
        return self.start(timeout)

    def is_running(self) -> bool:
        """Check if container is running and responsive."""
        container_id = self._get_container_id()
        if not container_id:
            return False

        return self._verify_connection()

    def get_status(self) -> Dict:
        """
        Get container status information.

        Returns:
            Dictionary with status information.
        """
        container_id = self._get_container_id()

        status = {
            "running": container_id is not None and self.is_running(),
            "container_id": container_id,
            "container_name": self.container_name,
            "image": self.image,
            "endpoint": self.config.server_endpoint,
            "memory_gb": self.config.memory_gb,
        }

        # Get more details if running
        if container_id:
            try:
                result = subprocess.run(
                    ["docker", "inspect", container_id],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    inspect_data = json.loads(result.stdout)
                    if inspect_data:
                        status["state"] = inspect_data[0].get("State", {}).get("Status")
                        status["started_at"] = inspect_data[0].get("State", {}).get("StartedAt")
            except Exception:
                pass

        return status

    def run_frontend(
        self,
        frontend_command: str,
        input_path: Path,
        output_path: Path,
        exclude_patterns: Optional[List[str]] = None,
        timeout: int = 3600,
    ) -> bool:
        """
        Run a Joern frontend in Docker container.

        Args:
            frontend_command: Frontend command (e.g., "c2cpg", "pysrc2cpg")
            input_path: Path to source code (will be mounted)
            output_path: Path for output CPG file
            exclude_patterns: Patterns to exclude
            timeout: Maximum runtime in seconds

        Returns:
            True if frontend completed successfully.
        """
        if not self._check_docker_available():
            raise RuntimeError("Docker is not available")

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build docker run command
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{input_path.absolute()}:/input:ro",
            "-v", f"{output_path.parent.absolute()}:/output",
            "-e", f"JAVA_OPTS=-Xmx{self.config.memory_gb}g",
            self.image,
            frontend_command,
            "/input",
            "-o", f"/output/{output_path.name}",
        ]

        # Add exclude patterns
        if exclude_patterns:
            for pattern in exclude_patterns:
                cmd.extend(["--exclude", pattern])

        logger.info(f"Running frontend in Docker: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error(f"Frontend failed: {result.stderr}")
                return False

            if not output_path.exists():
                logger.error(f"CPG file not created: {output_path}")
                return False

            logger.info(f"CPG created: {output_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Frontend timed out after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Frontend error: {e}")
            return False

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
        Run a Joern frontend in Docker container asynchronously.

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
        if not self._check_docker_available():
            raise RuntimeError("Docker is not available")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{input_path.absolute()}:/input:ro",
            "-v", f"{output_path.parent.absolute()}:/output",
            "-e", f"JAVA_OPTS=-Xmx{self.config.memory_gb}g",
            self.image,
            frontend_command,
            "/input",
            "-o", f"/output/{output_path.name}",
        ]

        if exclude_patterns:
            for pattern in exclude_patterns:
                cmd.extend(["--exclude", pattern])

        logger.info(f"Running frontend in Docker async: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def monitor_output():
            """Monitor output for progress."""
            while True:
                if process.stderr is None:
                    break
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode(errors="ignore").strip()
                if line_str:
                    logger.debug(f"Docker frontend: {line_str}")
                    if progress_callback:
                        lower = line_str.lower()
                        if "parsing" in lower:
                            progress_callback(30, "Parsing source files...")
                        elif "creating" in lower or "generating" in lower:
                            progress_callback(50, "Creating CPG nodes...")
                        elif "linking" in lower:
                            progress_callback(70, "Linking CPG edges...")
                        elif "writing" in lower or "serializing" in lower:
                            progress_callback(85, "Writing CPG to disk...")

        try:
            await asyncio.wait_for(
                asyncio.gather(process.wait(), monitor_output()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.error(f"Docker frontend timed out after {timeout}s")
            return False

        if process.returncode != 0:
            stderr = await process.stderr.read() if process.stderr else b""
            logger.error(f"Docker frontend failed: {stderr.decode(errors='ignore')}")
            return False

        if not output_path.exists():
            logger.error(f"CPG file not created: {output_path}")
            return False

        logger.info(f"CPG created: {output_path}")
        return True

    def pull_image(self) -> bool:
        """
        Pull the Joern Docker image.

        Returns:
            True if image pulled successfully.
        """
        logger.info(f"Pulling Docker image: {self.image}")

        try:
            result = subprocess.run(
                ["docker", "pull", self.image],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for large images
            )

            if result.returncode != 0:
                logger.error(f"Failed to pull image: {result.stderr}")
                return False

            logger.info("Docker image pulled successfully")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout pulling Docker image")
            return False
        except Exception as e:
            logger.error(f"Error pulling image: {e}")
            return False
