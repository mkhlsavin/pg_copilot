"""Joern Server Client for CPGQL Query Execution.

Provides HTTP client for connecting to Joern server and executing CPGQL queries.
"""
import os
import logging
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class JoernClient:
    """Client for Joern server communication.

    Connects to a running Joern server and executes CPGQL queries.

    Example:
        client = JoernClient("localhost:8080", "myproject.cpg")
        if client.connect():
            result = client.execute_query("cpg.method.name.l")
            client.disconnect()
    """

    def __init__(
        self,
        server_endpoint: Optional[str] = None,
        workspace: str = "workspace.cpg",
        timeout: int = 300
    ):
        """
        Initialize Joern client.

        Args:
            server_endpoint: Joern server endpoint (host:port).
                If None, uses JOERN_ENDPOINT env var or defaults to localhost:8080.
            workspace: CPG workspace/file to open
            timeout: Request timeout in seconds
        """
        self.server_endpoint = server_endpoint or os.getenv(
            "JOERN_ENDPOINT", "localhost:8080"
        )
        self.workspace = workspace
        self.timeout = timeout
        self._connected = False
        self._session: Optional[requests.Session] = None

        # Ensure endpoint has protocol
        if not self.server_endpoint.startswith(('http://', 'https://')):
            self.server_endpoint = f"http://{self.server_endpoint}"

    @property
    def base_url(self) -> str:
        """Get base URL for API calls."""
        return self.server_endpoint.rstrip('/')

    def connect(self) -> bool:
        """
        Connect to Joern server and open workspace.

        Returns:
            True if connection successful
        """
        try:
            self._session = requests.Session()

            # Check server health
            health_url = f"{self.base_url}/health"
            response = self._session.get(health_url, timeout=10)

            if response.status_code != 200:
                logger.error(f"Joern server health check failed: {response.status_code}")
                return False

            # Open workspace
            if self.workspace:
                open_result = self._open_workspace()
                if not open_result:
                    logger.warning(f"Failed to open workspace: {self.workspace}")
                    # Continue anyway - workspace might already be open

            self._connected = True
            logger.info(f"Connected to Joern server: {self.base_url}")
            return True

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Joern server at {self.base_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Joern connection error: {e}")
            return False

    def disconnect(self):
        """Close connection to Joern server."""
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("Disconnected from Joern server")

    def _open_workspace(self) -> bool:
        """Open CPG workspace."""
        try:
            query = f'open("{self.workspace}")'
            result = self._execute_raw(query)
            return result is not None
        except Exception as e:
            logger.debug(f"Failed to open workspace: {e}")
            return False

    def execute_query(self, query: str) -> Optional[str]:
        """
        Execute CPGQL query and return raw result.

        Args:
            query: CPGQL query string

        Returns:
            Raw query result string, or None on error
        """
        return self._execute_raw(query)

    def query(self, query: str) -> Optional[str]:
        """
        Execute CPGQL query (alias for execute_query).

        Args:
            query: CPGQL query string

        Returns:
            Raw query result string, or None on error
        """
        return self.execute_query(query)

    def run_query(self, query: str) -> Optional[str]:
        """
        Execute CPGQL query (alias for execute_query).

        Args:
            query: CPGQL query string

        Returns:
            Raw query result string, or None on error
        """
        return self.execute_query(query)

    def _execute_raw(self, query: str) -> Optional[str]:
        """
        Execute raw query via HTTP.

        Args:
            query: Query string

        Returns:
            Raw response text, or None on error
        """
        if not self._session:
            logger.error("Not connected to Joern server. Call connect() first.")
            return None

        try:
            # Joern server expects POST to /query endpoint
            query_url = f"{self.base_url}/query"
            response = self._session.post(
                query_url,
                json={"query": query},
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Query failed with status {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Query timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Query request failed: {e}")
            return None

    def execute_query_json(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Execute query and return JSON result.

        Args:
            query: CPGQL query string

        Returns:
            Parsed JSON response, or None on error
        """
        result = self._execute_raw(query)
        if result:
            try:
                import json
                return json.loads(result)
            except json.JSONDecodeError:
                logger.debug("Response is not JSON, returning raw text wrapped")
                return {"result": result}
        return None

    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._session is not None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
