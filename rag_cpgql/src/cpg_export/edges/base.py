"""Base class for edge exporters.

Provides common functionality for exporting edges from Joern to DuckDB.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class EdgeExporter(ABC):
    """Base class for edge exporters."""

    def __init__(self, joern_client, conn, batch_size: int = 10000):
        """
        Args:
            joern_client: JoernClient for executing CPGQL queries
            conn: DuckDB connection
            batch_size: Number of nodes to iterate per batch
        """
        self.joern_client = joern_client
        self.conn = conn
        self.batch_size = batch_size

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """DuckDB table name (e.g., 'edges_ast')"""
        pass

    @property
    @abstractmethod
    def edge_query_template(self) -> str:
        """Scala query template with {offset} and {batch_size} placeholders"""
        pass

    @property
    @abstractmethod
    def insert_sql(self) -> str:
        """SQL INSERT statement"""
        pass

    @property
    def count_query(self) -> str:
        """Query to get total node count for iteration. Default: cpg.all.size"""
        return "cpg.all.size"

    def parse_edge(self, parts: list) -> tuple:
        """Parse edge from parts. Default: simple (src, dst) tuple.

        Override for edges with additional properties (e.g., REACHING_DEF has variable).
        """
        return (int(parts[0]), int(parts[1]))

    def export(self, limit: Optional[int] = None, start_offset: int = 0) -> int:
        """Export edges from Joern to DuckDB.

        Args:
            limit: Optional limit on number of nodes to iterate
            start_offset: Offset to start from (for resume)

        Returns:
            Count of edges exported
        """
        logger.info(f"Exporting {self.entity_type} (batch: {self.batch_size}, offset: {start_offset})...")

        # Get total count
        total_nodes = self._get_total_count()

        if total_nodes == 0:
            logger.info(f"No nodes found for {self.entity_type}")
            return 0

        if limit:
            total_nodes = min(total_nodes, limit)

        logger.info(f"Iterating through {total_nodes} nodes for {self.entity_type}")

        offset = start_offset
        total_exported = self._get_existing_count() if start_offset > 0 else 0

        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset} (already exported: {total_exported})")

        while offset < total_nodes:
            current_batch_size = min(self.batch_size, total_nodes - offset)
            batch_count = self._export_batch(offset, current_batch_size)
            total_exported += batch_count
            offset += current_batch_size

            logger.info(f"Progress: {self.entity_type} {total_exported} edges (offset: {offset}/{total_nodes})")

        logger.info(f"Completed {self.entity_type}: {total_exported} edges")
        return total_exported

    def _get_total_count(self) -> int:
        """Get total count from Joern."""
        result = self.joern_client.execute_query(self.count_query)

        if not result or not result.get('success'):
            logger.warning(f"Failed to get node count for {self.entity_type}")
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
        """Export a single batch of edges.

        Args:
            offset: Starting offset
            batch_size: Batch size

        Returns:
            Count of edges exported in this batch
        """
        query = self.edge_query_template.format(offset=offset, batch_size=batch_size)

        logger.debug(f"Fetching {self.entity_type} for nodes {offset} to {offset + batch_size}...")
        result = self.joern_client.execute_query(query)

        if not result or not result.get('success'):
            logger.warning(f"Query failed for {self.entity_type}")
            return 0

        raw_output = result.get('result', '')
        if not raw_output or not raw_output.strip():
            return 0

        # Skip Scala REPL header lines
        lines = raw_output.strip().split('\n')
        data_lines = [l for l in lines if not l.startswith('val ') and '\t' in l]

        if not data_lines:
            return 0

        edges = []
        for line in data_lines:
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) < 2:
                continue

            try:
                edge = self.parse_edge(parts)
                edges.append(edge)
            except Exception as e:
                logger.debug(f"Error parsing edge: {e}")
                continue

        if edges:
            self.conn.executemany(self.insert_sql, edges)

        return len(edges)
