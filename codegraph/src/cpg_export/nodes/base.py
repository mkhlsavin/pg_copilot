"""Base class for node exporters.

Provides common functionality for exporting nodes from Joern to DuckDB.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class NodeExporter(ABC):
    """Base class for node exporters."""

    def __init__(self, joern_client, conn, batch_size: int = 10000):
        """
        Args:
            joern_client: JoernClient for executing CPGQL queries
            conn: DuckDB connection
            batch_size: Number of nodes to export per batch
        """
        self.joern_client = joern_client
        self.conn = conn
        self.batch_size = batch_size

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """DuckDB table name (e.g., 'nodes_method')"""
        pass

    @property
    @abstractmethod
    def cpg_type(self) -> str:
        """Joern CPG type name (e.g., 'method')"""
        pass

    @property
    @abstractmethod
    def query_template(self) -> str:
        """Scala query template with {offset} and {batch_size} placeholders"""
        pass

    @property
    @abstractmethod
    def insert_sql(self) -> str:
        """SQL INSERT statement"""
        pass

    @property
    @abstractmethod
    def field_count(self) -> int:
        """Expected number of fields in parsed row"""
        pass

    @abstractmethod
    def parse_row(self, parts: list) -> tuple:
        """Parse a row of tab-separated values into a tuple for insertion.

        Args:
            parts: List of string values from splitting on tab

        Returns:
            Tuple of values for SQL INSERT
        """
        pass

    def export(self, limit: Optional[int] = None, start_offset: int = 0) -> int:
        """Export nodes from Joern to DuckDB.

        Args:
            limit: Optional limit on number of nodes to export
            start_offset: Offset to start from (for resume)

        Returns:
            Count of nodes exported
        """
        logger.info(f"Exporting {self.entity_type} (batch: {self.batch_size}, offset: {start_offset})...")

        # Get total count
        total_count = self._get_total_count()

        if total_count == 0:
            logger.info(f"No {self.cpg_type} nodes found in CPG")
            return 0

        if limit:
            total_count = min(total_count, limit)

        logger.info(f"Total {self.cpg_type} to export: {total_count}")

        offset = start_offset
        total_exported = self._get_existing_count() if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_exported})")

        while offset < total_count:
            current_batch_size = min(self.batch_size, total_count - offset)
            batch_count = self._export_batch(offset, current_batch_size)
            total_exported += batch_count
            offset += current_batch_size

            logger.info(f"Progress: {self.entity_type} {total_exported}/{total_count}")

        logger.info(f"Completed {self.entity_type}: {total_exported} nodes")
        return total_exported

    def _get_total_count(self) -> int:
        """Get total count from Joern."""
        count_query = f"cpg.{self.cpg_type}.size"
        result = self.joern_client.execute_query(count_query)

        if not result or not result.get('success'):
            logger.warning(f"Failed to get {self.cpg_type} count")
            return 0

        count_str = result.get('result', '0')
        match = re.search(r'=\s*(\d+)', count_str)
        return int(match.group(1)) if match else 0

    def _get_existing_count(self) -> int:
        """Get count of existing records in DuckDB."""
        try:
            result = self.conn.execute(
                f"SELECT COUNT(*) FROM {self.entity_type}"
            ).fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def _export_batch(self, offset: int, batch_size: int) -> int:
        """Export a single batch of nodes.

        Args:
            offset: Starting offset
            batch_size: Batch size

        Returns:
            Count of nodes exported in this batch
        """
        query = self.query_template.format(offset=offset, batch_size=batch_size)

        logger.debug(f"Fetching {self.cpg_type} {offset} to {offset + batch_size}...")
        result = self.joern_client.execute_query(query)

        if not result or not result.get('success'):
            error = result.get('error', 'Unknown error') if result else 'No result'
            logger.warning(f"Query failed for {self.entity_type}: {error}")
            return 0

        raw_output = result.get('result', '')
        if not raw_output or not raw_output.strip():
            return 0

        # Skip Scala REPL header lines
        lines = raw_output.strip().split('\n')
        data_lines = [l for l in lines if not l.startswith('val ') and '\t' in l]

        if not data_lines:
            return 0

        rows = []
        for line in data_lines:
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) < self.field_count:
                continue

            try:
                row = self.parse_row(parts)
                rows.append(row)
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue

        if rows:
            self.conn.executemany(self.insert_sql, rows)

        return len(rows)


# Utility functions for common parsing patterns

def parse_int(value: str) -> Optional[int]:
    """Parse string to int, handling '-1' and empty values."""
    if value and value.lstrip('-').isdigit():
        val = int(value)
        return val if val >= 0 else None
    return None


def parse_bool(value: str) -> bool:
    """Parse string to bool."""
    return value.lower() == 'true'


def escape_code(code: str) -> str:
    """Escape newlines in code for storage."""
    return code.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
