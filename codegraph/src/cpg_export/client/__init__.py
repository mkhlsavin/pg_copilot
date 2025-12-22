"""DuckDB CPG Client Package.

Provides Python interface for querying CPG data stored in DuckDB.

Main components:
- DuckDBCPGClient: Main client for CPG queries
- DuckDBConnectionPool: Thread-safe connection pooling
- CPGStatistics: CPG statistics dataclass

Example usage:
    from src.cpg_export.client import DuckDBCPGClient

    client = DuckDBCPGClient("cpg.duckdb")
    if client.connect():
        methods = client.find_method_by_name("malloc", exact=False)
        print(f"Found {len(methods)} methods")
        client.disconnect()

    # Or use context manager:
    with DuckDBCPGClient("cpg.duckdb") as client:
        stats = client.get_statistics()
        print(f"Total methods: {stats.method_count}")

    # Pooled mode (thread-safe):
    client = DuckDBCPGClient("cpg.duckdb", use_pool=True, pool_size=4)
    client.connect()
    # Multiple threads can safely query
    client.disconnect()
"""

from .connection import DuckDBConnectionPool, get_global_pool
from .models import CPGStatistics
from .client import DuckDBCPGClient

__all__ = [
    "DuckDBCPGClient",
    "DuckDBConnectionPool",
    "get_global_pool",
    "CPGStatistics",
]
