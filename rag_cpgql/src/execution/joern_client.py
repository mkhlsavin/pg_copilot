"""Joern Server Client for executing CPGQL queries with session bootstrap."""
import asyncio
import logging
import time
from typing import Dict, Optional

try:
    from cpgqls_client import CPGQLSClient
except ImportError:
    CPGQLSClient = None

logger = logging.getLogger(__name__)


class JoernClient:
    """Client for connecting to Joern server and executing CPGQL queries."""

    def __init__(
        self,
        server_endpoint: str = "localhost:8080",
        workspace: str = "pg17_full.cpg",
    ):
        """
        Initialize Joern client.

        Args:
            server_endpoint: Joern server endpoint (host:port).
            workspace: Name of the workspace to open if no CPG is loaded.
        """
        if CPGQLSClient is None:
            raise ImportError("cpgqls-client not installed. Run: pip install cpgqls-client")

        self.server_endpoint = server_endpoint
        self.workspace = workspace
        self.client: Optional[CPGQLSClient] = None

        logger.info("JoernClient initialized (endpoint=%s)", server_endpoint)

    def connect(self) -> bool:
        """Connect to Joern server and bootstrap the interactive session."""
        try:
            logger.info("Connecting to Joern server at %s", self.server_endpoint)

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            self.client = CPGQLSClient(self.server_endpoint)

            if not self._bootstrap_session():
                logger.error("Failed to bootstrap Joern session")
                return False

            test = self.execute_query("cpg.method.name.l.size")
            if test["success"]:
                logger.info("Connected to Joern server (CPG has %s methods)", test["result"])
                return True

            logger.error("Connection test failed: %s", test.get("error"))
            return False

        except Exception as exc:
            logger.error("Failed to connect: %s", exc)
            return False

    def execute_query(self, query: str) -> Dict:
        """Execute a CPGQL query on the server."""
        if not self.client:
            return {
                "success": False,
                "result": None,
                "error": "Not connected to server",
                "execution_time": 0,
            }

        try:
            start_time = time.time()

            if not self._ensure_cpg_bound():
                return {
                    "success": False,
                    "result": None,
                    "error": "Joern workspace not loaded",
                    "execution_time": 0,
                }

            logger.debug("Executing query: %s", query)
            response = self.client.execute(query)
            execution_time = time.time() - start_time

            stdout = response.get("stdout", "") or ""
            stderr = response.get("stderr", "") or ""
            raw_error = response.get("error")

            lowered = (stdout + "\n" + stderr).lower()
            error_markers = [
                "io.joern.console.error",
                "not found",
                "no cpg loaded",
                "exception",
                "-- error",
                "invalid escape",
            ]

            if raw_error or not response.get("success", False) or any(marker in lowered for marker in error_markers):
                error_message = raw_error or stderr or stdout.strip() or "Unknown error"
                logger.warning("Query failed: %s", error_message)
                return {
                    "success": False,
                    "result": None,
                    "error": error_message,
                    "execution_time": execution_time,
                    "raw_response": response,
                }

            logger.info("Query executed successfully in %.2fs", execution_time)
            return {
                "success": True,
                "result": stdout,
                "error": None,
                "execution_time": execution_time,
                "raw_response": response,
            }

        except Exception as exc:
            logger.error("Query execution error: %s", exc)
            return {
                "success": False,
                "result": None,
                "error": str(exc),
                "execution_time": 0,
            }

    def get_cpg_stats(self) -> Dict:
        """Return a set of simple statistics about the loaded CPG."""
        if not self.client:
            return {"error": "Not connected"}

        stats: Dict[str, int] = {}

        queries = {
            "methods": "cpg.method.size",
            "calls": "cpg.call.size",
            "files": "cpg.file.size",
            "namespaces": "cpg.namespace.size",
            "types": "cpg.typeDecl.size",
            "parameters": "cpg.parameter.size",
            "locals": "cpg.local.size",
        }

        for name, query in queries.items():
            result = self.execute_query(query)
            if result["success"]:
                try:
                    stats[name] = int(result["result"].strip())
                except Exception:
                    stats[name] = 0
            else:
                stats[name] = 0

        return stats

    def close(self) -> None:
        """Close the Joern client connection."""
        if self.client:
            self.client = None
            logger.info("Disconnected from server")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _bootstrap_session(self) -> bool:
        if not self.client:
            return False

        try:
            for command in (
                'import _root_.io.joern.joerncli.console.Joern',
                'import _root_.io.shiftleft.semanticcpg.language._',
            ):
                if self._run_command(command) is None:
                    return False

            if not self._ensure_cpg_bound():
                open_response = self._run_command(f'Joern.open("{self.workspace}")')
                if open_response is None:
                    return False
                if not self._ensure_cpg_bound():
                    return False

            return True
        except Exception as exc:
            logger.error("Joern session bootstrap failed: %s", exc)
            return False

    def _ensure_cpg_bound(self) -> bool:
        response = self._run_command("val cpg = Joern.cpg")
        if response is None:
            return False
        stdout = response.get("stdout", "") or ""
        if "No CPG loaded" in stdout:
            return False
        return True

    def _run_command(self, command: str) -> Optional[Dict]:
        if not self.client:
            return None

        response = self.client.execute(command)
        if not response.get("success", False):
            logger.error("Bootstrap command failed (%s): %s", command, response.get("stderr", ""))
            return None

        stderr = response.get("stderr")
        if stderr:
            logger.error("Bootstrap command stderr (%s): %s", command, stderr)
            return None

        stdout = response.get("stdout", "")
        if stdout and "io.joern.console.Error" in stdout:
            logger.error("Bootstrap command error (%s): %s", command, stdout)
            return None

        return response
