"""
Local Joern Server Runner.

Manages Joern server running on local machine.
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..config import JoernConfig

logger = logging.getLogger(__name__)


class LocalJoernRunner:
    """
    Manages locally installed Joern server.

    Handles starting, stopping, and monitoring the Joern server process.
    Works cross-platform (Windows, Linux, macOS).
    """

    def __init__(self, config: JoernConfig):
        """
        Initialize local Joern runner.

        Args:
            config: Joern configuration.
        """
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._pid: Optional[int] = None

    @property
    def joern_executable(self) -> Optional[Path]:
        """Get path to joern executable."""
        if not self.config.home:
            return None

        system = platform.system()

        candidates = [
            self.config.home / "joern.bat" if system == "Windows" else self.config.home / "joern",
            self.config.home / "joern-cli" / "joern.bat" if system == "Windows"
                else self.config.home / "joern-cli" / "joern",
            self.config.home / "joern-cli" / "bin" / "joern.bat" if system == "Windows"
                else self.config.home / "joern-cli" / "bin" / "joern",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _build_server_command(self) -> List[str]:
        """Build command to start Joern server."""
        joern_exe = self.joern_executable

        if not joern_exe:
            raise RuntimeError("Joern executable not found")

        cmd = [
            str(joern_exe),
            f"-J-Xmx{self.config.memory_gb}g",
            "--server",
            "--server-host", self.config.server_host,
            "--server-port", str(self.config.server_port),
        ]

        return cmd

    def _get_env(self) -> Dict[str, str]:
        """Get environment variables for Joern process."""
        env = os.environ.copy()
        env["JAVA_OPTS"] = f"-Xmx{self.config.memory_gb}g"

        # Add JOERN_HOME if set
        if self.config.home:
            env["JOERN_HOME"] = str(self.config.home)

        return env

    def start(self, timeout: int = 90) -> bool:
        """
        Start Joern server.

        Args:
            timeout: Maximum seconds to wait for server to start.

        Returns:
            True if server started successfully.

        Raises:
            RuntimeError: If server fails to start.
        """
        if self.is_running():
            logger.info("Joern server already running")
            return True

        cmd = self._build_server_command()
        env = self._get_env()

        logger.info(f"Starting Joern server: {' '.join(cmd)}")

        try:
            # Start process
            if platform.system() == "Windows":
                # On Windows, use CREATE_NEW_PROCESS_GROUP for proper signal handling
                self._process = subprocess.Popen(
                    cmd,
                    env=env,
                    cwd=str(self.config.home) if self.config.home else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # On Unix, start in new session
                self._process = subprocess.Popen(
                    cmd,
                    env=env,
                    cwd=str(self.config.home) if self.config.home else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )

            self._pid = self._process.pid
            logger.info(f"Joern server started with PID {self._pid}")

        except Exception as e:
            logger.error(f"Failed to start Joern server: {e}")
            raise RuntimeError(f"Failed to start Joern server: {e}")

        # Wait for server to be ready
        if not self._wait_for_server(timeout):
            self.stop()
            raise RuntimeError(f"Joern server did not start within {timeout} seconds")

        logger.info(f"Joern server is ready at {self.config.server_endpoint}")
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
                    # Port is open, but verify server is responsive
                    if self._verify_connection():
                        return True
            except Exception:
                pass

            time.sleep(1)

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

    def stop(self, timeout: int = 10) -> bool:
        """
        Stop Joern server.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown.

        Returns:
            True if server stopped.
        """
        if self._process is None and self._pid is None:
            return True

        logger.info("Stopping Joern server...")

        try:
            if self._process:
                # Try graceful termination first
                if platform.system() == "Windows":
                    self._process.terminate()
                else:
                    self._process.send_signal(signal.SIGTERM)

                try:
                    self._process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Graceful shutdown timed out, forcing kill")
                    self._process.kill()
                    self._process.wait()

            elif self._pid:
                # Process started externally, try to kill by PID
                self._kill_by_pid(self._pid, timeout)

        except Exception as e:
            logger.error(f"Error stopping Joern server: {e}")
            return False

        finally:
            self._process = None
            self._pid = None

        logger.info("Joern server stopped")
        return True

    def _kill_by_pid(self, pid: int, timeout: int):
        """Kill process by PID."""
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(min(timeout, 5))
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def restart(self, timeout: int = 90) -> bool:
        """
        Restart Joern server.

        Args:
            timeout: Maximum seconds to wait for server restart.

        Returns:
            True if server restarted successfully.
        """
        self.stop()
        time.sleep(2)  # Brief pause before restart
        return self.start(timeout)

    def is_running(self) -> bool:
        """Check if server is running and responsive."""
        # First check if process is alive
        if self._process:
            if self._process.poll() is not None:
                # Process has terminated
                self._process = None
                self._pid = None
                return False

        # Check if server is responsive
        return self._verify_connection()

    def get_status(self) -> Dict:
        """
        Get server status information.

        Returns:
            Dictionary with status information.
        """
        return {
            "running": self.is_running(),
            "pid": self._pid,
            "endpoint": self.config.server_endpoint,
            "memory_gb": self.config.memory_gb,
            "joern_home": str(self.config.home) if self.config.home else None,
        }

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
            frontend_command: Frontend command (e.g., "c2cpg", "pysrc2cpg")
            input_path: Path to source code
            output_path: Path for output CPG file
            exclude_patterns: Patterns to exclude
            timeout: Maximum runtime in seconds

        Returns:
            True if frontend completed successfully.
        """
        frontend_path = self.config.get_frontend_path(frontend_command)

        if not frontend_path:
            raise RuntimeError(f"Frontend not found: {frontend_command}")

        cmd = [
            str(frontend_path),
            str(input_path),
            "-o", str(output_path),
        ]

        # Add exclude patterns
        if exclude_patterns:
            for pattern in exclude_patterns:
                cmd.extend(["--exclude", pattern])

        env = self._get_env()

        logger.info(f"Running frontend: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                env=env,
                cwd=str(self.config.home) if self.config.home else None,
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
        frontend_path = self.config.get_frontend_path(frontend_command)

        if not frontend_path:
            raise RuntimeError(f"Frontend not found: {frontend_command}")

        cmd = [
            str(frontend_path),
            str(input_path),
            "-o", str(output_path),
        ]

        if exclude_patterns:
            for pattern in exclude_patterns:
                cmd.extend(["--exclude", pattern])

        env = self._get_env()

        logger.info(f"Running frontend async: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            cwd=str(self.config.home) if self.config.home else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def monitor_stderr():
            """Monitor stderr for progress."""
            while True:
                if process.stderr is None:
                    break
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode(errors="ignore").strip()
                if line_str:
                    logger.debug(f"Frontend: {line_str}")
                    if progress_callback:
                        # Parse progress from output
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
                asyncio.gather(process.wait(), monitor_stderr()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.error(f"Frontend timed out after {timeout}s")
            return False

        if process.returncode != 0:
            stderr = await process.stderr.read() if process.stderr else b""
            logger.error(f"Frontend failed: {stderr.decode(errors='ignore')}")
            return False

        if not output_path.exists():
            logger.error(f"CPG file not created: {output_path}")
            return False

        logger.info(f"CPG created: {output_path}")
        return True
