"""Joern Server Client for executing CPGQL queries."""
import logging
from typing import Dict, Optional
import time

try:
    from cpgqls_client import CPGQLSClient
except ImportError:
    CPGQLSClient = None

logger = logging.getLogger(__name__)


class JoernClient:
    """
    Client for connecting to Joern server and executing CPGQL queries.

    Requires Joern server to be running with --server flag.
    """

    def __init__(
        self,
        server_endpoint: str = "localhost:8080"
    ):
        """
        Initialize Joern client.

        Args:
            server_endpoint: Joern server endpoint (host:port)
        """
        if CPGQLSClient is None:
            raise ImportError("cpgqls-client not installed. Run: pip install cpgqls-client")

        self.server_endpoint = server_endpoint
        self.client = None

        logger.info(f"JoernClient initialized (endpoint={server_endpoint})")

    def connect(self) -> bool:
        """
        Connect to Joern server.

        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to Joern server at {self.server_endpoint}")

            self.client = CPGQLSClient(self.server_endpoint)

            # Test connection with simple query
            result = self.execute_query("cpg.method.name.l.size")

            if result['success']:
                logger.info(f"Connected to Joern server (CPG has {result['result']} methods)")
                return True
            else:
                logger.error(f"Connection test failed: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def execute_query(
        self,
        query: str
    ) -> Dict:
        """
        Execute CPGQL query on server.

        Args:
            query: CPGQL query string

        Returns:
            Dict with 'success', 'result', 'error', 'execution_time'
        """
        if not self.client:
            return {
                'success': False,
                'result': None,
                'error': 'Not connected to server',
                'execution_time': 0
            }

        try:
            start_time = time.time()

            logger.debug(f"Executing query: {query}")

            # Execute query
            response = self.client.execute(query)

            execution_time = time.time() - start_time

            # Parse response (cpgqls_client returns dict with 'success', 'stdout', 'stderr')
            if response.get('success'):
                result = response.get('stdout', '')
                logger.info(f"Query executed successfully in {execution_time:.2f}s")
                return {
                    'success': True,
                    'result': result,
                    'error': None,
                    'execution_time': execution_time,
                    'raw_response': response
                }
            else:
                error = response.get('stderr', 'Unknown error')
                logger.warning(f"Query failed: {error}")
                return {
                    'success': False,
                    'result': None,
                    'error': error,
                    'execution_time': execution_time,
                    'raw_response': response
                }

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'execution_time': 0
            }

    def get_cpg_stats(self) -> Dict:
        """
        Get statistics about loaded CPG.

        Returns:
            Dict with CPG statistics
        """
        if not self.client:
            return {'error': 'Not connected'}

        stats = {}

        # Count nodes
        queries = {
            'methods': 'cpg.method.size',
            'calls': 'cpg.call.size',
            'files': 'cpg.file.size',
            'namespaces': 'cpg.namespace.size',
            'types': 'cpg.typeDecl.size',
            'parameters': 'cpg.parameter.size',
            'locals': 'cpg.local.size'
        }

        for name, query in queries.items():
            result = self.execute_query(query)
            if result['success']:
                try:
                    stats[name] = int(result['result'].strip())
                except:
                    stats[name] = 0
            else:
                stats[name] = 0

        return stats

    def close(self):
        """Close connection."""
        if self.client:
            self.client = None
            logger.info("Disconnected from server")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
