"""Progress Tracker for CPG Export.

Tracks export progress for resumable exports.
Stores state in DuckDB export_progress table.
"""
import logging
from typing import Optional, Tuple
import duckdb

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks export progress for resumable CPG exports.

    Maintains state in DuckDB export_progress table allowing
    exports to be resumed after interruption.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize progress tracker.

        Args:
            conn: DuckDB connection
        """
        self.conn = conn
        self._initialized = False

    def initialize(self):
        """Create export_progress table if not exists."""
        if self._initialized:
            return

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS export_progress (
                entity_type VARCHAR PRIMARY KEY,
                total_count BIGINT,
                exported_count BIGINT,
                last_offset BIGINT,
                status VARCHAR,
                last_updated TIMESTAMP,
                error_message VARCHAR
            )
        """)
        self._initialized = True
        logger.info("Export progress table ready")

    def get_status(self, entity_type: str) -> Tuple[str, int]:
        """
        Get export status and last offset for entity type.

        Args:
            entity_type: Type of entity (e.g., 'methods', 'calls')

        Returns:
            tuple: (status, last_offset) or ('pending', 0) if not found
        """
        self.initialize()
        result = self.conn.execute("""
            SELECT status, last_offset FROM export_progress
            WHERE entity_type = ?
        """, [entity_type]).fetchone()
        return (result[0], result[1]) if result else ('pending', 0)

    def update_progress(
        self,
        entity_type: str,
        total: int,
        exported: int,
        offset: int,
        status: str,
        error: Optional[str] = None
    ):
        """
        Update export progress for entity type.

        Args:
            entity_type: Type of entity
            total: Total count to export
            exported: Count exported so far
            offset: Current offset
            status: Status ('pending', 'in_progress', 'completed', 'failed')
            error: Error message if failed
        """
        self.initialize()
        self.conn.execute("""
            INSERT OR REPLACE INTO export_progress
            (entity_type, total_count, exported_count, last_offset, status, last_updated, error_message)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, [entity_type, total, exported, offset, status, error])

    def mark_completed(self, entity_type: str, total: int = 0):
        """
        Mark entity export as completed.

        Args:
            entity_type: Type of entity
            total: Total records exported
        """
        self.update_progress(entity_type, total, total, total, 'completed')
        logger.info(f"[OK] {entity_type} export completed ({total} records)")

    def mark_failed(self, entity_type: str, error: str, offset: int = 0):
        """
        Mark entity export as failed.

        Args:
            entity_type: Type of entity
            error: Error message
            offset: Offset at which failure occurred
        """
        self.update_progress(entity_type, 0, 0, offset, 'failed', error)
        logger.error(f"[FAIL] {entity_type} export failed at offset {offset}: {error}")

    def mark_in_progress(
        self,
        entity_type: str,
        total: int,
        exported: int,
        offset: int
    ):
        """
        Mark entity export as in progress.

        Args:
            entity_type: Type of entity
            total: Total count to export
            exported: Count exported so far
            offset: Current offset
        """
        self.update_progress(entity_type, total, exported, offset, 'in_progress')

    def is_completed(self, entity_type: str) -> bool:
        """
        Check if entity export is already completed.

        Args:
            entity_type: Type of entity

        Returns:
            True if export is completed
        """
        status, _ = self.get_status(entity_type)
        return status == 'completed'

    def get_existing_count(self, table_name: str) -> int:
        """
        Get count of existing records in table.

        Args:
            table_name: Name of DuckDB table

        Returns:
            Row count, or 0 if table doesn't exist
        """
        try:
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except duckdb.CatalogException:
            return 0
        except duckdb.Error as e:
            logger.debug(f"Error counting table {table_name}: {e}")
            return 0

    def get_all_status(self) -> dict:
        """
        Get status of all entity types.

        Returns:
            Dict mapping entity_type to (status, exported_count, total_count)
        """
        self.initialize()
        results = self.conn.execute("""
            SELECT entity_type, status, exported_count, total_count
            FROM export_progress
            ORDER BY entity_type
        """).fetchall()

        return {
            row[0]: {
                'status': row[1],
                'exported': row[2],
                'total': row[3]
            }
            for row in results
        }

    def reset(self, entity_type: Optional[str] = None):
        """
        Reset progress tracking.

        Args:
            entity_type: If specified, reset only this entity.
                        If None, reset all entities.
        """
        self.initialize()
        if entity_type:
            self.conn.execute("""
                DELETE FROM export_progress WHERE entity_type = ?
            """, [entity_type])
            logger.info(f"Reset progress for {entity_type}")
        else:
            self.conn.execute("DELETE FROM export_progress")
            logger.info("Reset all export progress")

    def get_resume_offset(self, entity_type: str) -> int:
        """
        Get offset to resume export from.

        Args:
            entity_type: Type of entity

        Returns:
            Offset to resume from, or 0 if starting fresh
        """
        status, offset = self.get_status(entity_type)
        if status == 'completed':
            return -1  # Already done
        elif status == 'in_progress' or status == 'failed':
            return offset  # Resume from last offset
        else:
            return 0  # Start fresh
