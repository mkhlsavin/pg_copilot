"""DuckDB Connection Pool.

Thread-safe connection pooling for DuckDB.
"""
import duckdb
import logging
import threading
import queue
import time
from typing import Dict, Optional, Any
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DuckDBConnectionPool:
    """
    Thread-safe connection pool for DuckDB connections.

    Features:
    - Configurable pool size
    - Connection health checking
    - Automatic connection recycling
    - Context manager support for automatic checkout/checkin
    - Thread-safe operations

    Example:
        pool = DuckDBConnectionPool("cpg.duckdb", pool_size=4)
        with pool.get_connection() as conn:
            result = conn.execute("SELECT * FROM nodes_method LIMIT 10").fetchall()
    """

    def __init__(
        self,
        db_path: str,
        pool_size: int = 4,
        max_idle_time: float = 300.0,
        load_extensions: bool = True
    ):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to DuckDB database file
            pool_size: Number of connections to maintain in the pool
            max_idle_time: Maximum time (seconds) a connection can be idle
            load_extensions: Whether to load DuckPGQ extension
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self.load_extensions = load_extensions

        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        self._lock = threading.RLock()
        self._connection_times: Dict[int, float] = {}
        self._created_count = 0
        self._active_count = 0
        self._total_checkouts = 0
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the pool by creating initial connections.

        Returns:
            True if at least one connection was created successfully
        """
        if self._initialized:
            return True

        if not Path(self.db_path).exists():
            logger.error(f"Database file not found: {self.db_path}")
            return False

        with self._lock:
            success_count = 0
            for _ in range(self.pool_size):
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn)
                    success_count += 1

            self._initialized = success_count > 0
            logger.info(f"Connection pool initialized: {success_count}/{self.pool_size} connections")
            return self._initialized

    def _create_connection(self) -> Optional[duckdb.DuckDBPyConnection]:
        """Create a new DuckDB connection."""
        try:
            conn = duckdb.connect(self.db_path)

            if self.load_extensions:
                try:
                    conn.execute("LOAD duckpgq;")
                except Exception as e:
                    logger.debug(f"DuckPGQ extension not available: {e}")

            conn_id = id(conn)
            self._connection_times[conn_id] = time.time()
            self._created_count += 1
            logger.debug(f"Created connection {conn_id}")
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

    def _is_connection_healthy(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Check if a connection is still healthy."""
        try:
            conn.execute("SELECT 1").fetchone()
            return True
        except duckdb.Error as e:
            logger.debug(f"Connection health check failed (DuckDB error): {e}")
            return False
        except Exception as e:
            logger.warning(f"Connection health check failed (unexpected): {e}")
            return False

    def _should_recycle(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Check if a connection should be recycled due to age."""
        conn_id = id(conn)
        last_used = self._connection_times.get(conn_id, time.time())
        return (time.time() - last_used) > self.max_idle_time

    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        Get a connection from the pool (context manager).

        Args:
            timeout: Maximum time to wait for a connection

        Yields:
            DuckDB connection

        Raises:
            TimeoutError: If no connection available within timeout
        """
        conn = None
        try:
            conn = self._checkout(timeout)
            yield conn
        finally:
            if conn:
                self._checkin(conn)

    def _checkout(self, timeout: float = 30.0) -> duckdb.DuckDBPyConnection:
        """Checkout a connection from the pool."""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Connection pool not initialized")

        start_time = time.time()
        while True:
            try:
                conn = self._pool.get(timeout=min(1.0, timeout))

                # Check health and recycle if needed
                if not self._is_connection_healthy(conn) or self._should_recycle(conn):
                    logger.debug(f"Recycling connection {id(conn)}")
                    try:
                        conn.close()
                    except duckdb.Error as e:
                        logger.debug(f"Error closing recycled connection: {e}")
                    except Exception as e:
                        logger.debug(f"Unexpected error closing connection: {e}")
                    conn = self._create_connection()
                    if not conn:
                        continue

                with self._lock:
                    self._active_count += 1
                    self._total_checkouts += 1
                    self._connection_times[id(conn)] = time.time()

                return conn

            except queue.Empty:
                if (time.time() - start_time) >= timeout:
                    raise TimeoutError(f"Could not get connection within {timeout}s")
                continue

    def _checkin(self, conn: duckdb.DuckDBPyConnection):
        """Return a connection to the pool."""
        with self._lock:
            self._active_count -= 1
            self._connection_times[id(conn)] = time.time()

        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            logger.debug(f"Pool full, closing connection {id(conn)}")
            try:
                conn.close()
            except duckdb.Error as e:
                logger.debug(f"Error closing excess connection: {e}")
            except Exception as e:
                logger.debug(f"Unexpected error closing excess connection: {e}")

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            closed_count = 0
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                    closed_count += 1
                except queue.Empty:
                    break
                except duckdb.Error as e:
                    logger.debug(f"Error closing connection during pool shutdown: {e}")
                    closed_count += 1
                except Exception as e:
                    logger.warning(f"Unexpected error during pool shutdown: {e}")
                    break
            self._initialized = False
            logger.info(f"Closed {closed_count} connections")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            'pool_size': self.pool_size,
            'available': self._pool.qsize(),
            'active': self._active_count,
            'total_created': self._created_count,
            'total_checkouts': self._total_checkouts,
            'initialized': self._initialized
        }

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()


# Global connection pool singleton
_global_pool: Optional[DuckDBConnectionPool] = None


def get_global_pool(db_path: str = "cpg.duckdb", pool_size: int = 4) -> DuckDBConnectionPool:
    """
    Get or create the global connection pool.

    Args:
        db_path: Path to DuckDB database
        pool_size: Pool size (only used on first call)

    Returns:
        Global DuckDBConnectionPool instance
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = DuckDBConnectionPool(db_path, pool_size)
        _global_pool.initialize()
    return _global_pool
