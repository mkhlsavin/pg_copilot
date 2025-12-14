"""Progress tracking for CPG export with checkpoint/resume support.

This module handles saving and restoring export progress to allow
resuming interrupted exports.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExportProgress:
    """Export progress for a single entity type"""
    entity_type: str
    total_count: int
    exported_count: int
    last_offset: int
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    last_updated: datetime
    error_message: Optional[str] = None


class ProgressTracker:
    """Tracks export progress for checkpoint/resume functionality."""

    def __init__(self, conn):
        """
        Args:
            conn: DuckDB connection
        """
        self.conn = conn
        self._ensure_progress_table()

    def _ensure_progress_table(self):
        """Create progress tracking table if not exists"""
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

    def get_status(self, entity_type: str) -> Tuple[str, int]:
        """Get current export status for an entity type.

        Args:
            entity_type: Table name (e.g., 'nodes_method')

        Returns:
            Tuple of (status, last_offset)
        """
        result = self.conn.execute("""
            SELECT status, last_offset FROM export_progress
            WHERE entity_type = ?
        """, [entity_type]).fetchone()

        if result:
            return (result[0], result[1])
        return ('pending', 0)

    def update_progress(
        self,
        entity_type: str,
        total: int,
        exported: int,
        offset: int,
        status: str,
        error: Optional[str] = None
    ):
        """Update export progress for an entity type.

        Args:
            entity_type: Table name
            total: Total count to export
            exported: Count exported so far
            offset: Current offset
            status: Status string
            error: Optional error message
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO export_progress
            (entity_type, total_count, exported_count, last_offset, status, last_updated, error_message)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, [entity_type, total, exported, offset, status, error])

    def mark_started(self, entity_type: str, total: int):
        """Mark entity as started export.

        Args:
            entity_type: Table name
            total: Total count to export
        """
        self.update_progress(entity_type, total, 0, 0, 'in_progress')
        logger.info(f"Started export of {entity_type} ({total} items)")

    def mark_batch_complete(self, entity_type: str, total: int, exported: int, offset: int):
        """Mark a batch as complete.

        Args:
            entity_type: Table name
            total: Total count
            exported: Count exported so far
            offset: Current offset
        """
        self.update_progress(entity_type, total, exported, offset, 'in_progress')
        logger.debug(f"Progress: {entity_type} - {exported}/{total} (offset: {offset})")

    def mark_completed(self, entity_type: str, count: int):
        """Mark entity export as completed.

        Args:
            entity_type: Table name
            count: Total count exported
        """
        self.update_progress(entity_type, count, count, count, 'completed')
        logger.info(f"Completed export of {entity_type}: {count} items")

    def mark_failed(self, entity_type: str, error: str, offset: int = 0):
        """Mark entity export as failed.

        Args:
            entity_type: Table name
            error: Error message
            offset: Offset where failure occurred
        """
        self.update_progress(entity_type, 0, 0, offset, 'failed', error)
        logger.error(f"Failed export of {entity_type} at offset {offset}: {error}")

    def is_completed(self, entity_type: str) -> bool:
        """Check if entity export is completed.

        Args:
            entity_type: Table name

        Returns:
            True if completed
        """
        status, _ = self.get_status(entity_type)
        return status == 'completed'

    def get_resume_offset(self, entity_type: str) -> int:
        """Get offset to resume from for an entity.

        Args:
            entity_type: Table name

        Returns:
            Offset to resume from (0 if not started)
        """
        status, offset = self.get_status(entity_type)
        if status == 'in_progress':
            return offset
        return 0

    def get_all_progress(self) -> dict:
        """Get progress for all entities.

        Returns:
            Dict mapping entity_type to ExportProgress
        """
        results = self.conn.execute("""
            SELECT entity_type, total_count, exported_count, last_offset,
                   status, last_updated, error_message
            FROM export_progress
            ORDER BY entity_type
        """).fetchall()

        progress = {}
        for row in results:
            progress[row[0]] = ExportProgress(
                entity_type=row[0],
                total_count=row[1] or 0,
                exported_count=row[2] or 0,
                last_offset=row[3] or 0,
                status=row[4] or 'pending',
                last_updated=row[5],
                error_message=row[6]
            )
        return progress

    def print_status(self):
        """Print current export status for all entities."""
        progress = self.get_all_progress()

        if not progress:
            print("No export progress recorded yet.")
            return

        print("\n" + "=" * 60)
        print("EXPORT PROGRESS STATUS")
        print("=" * 60)

        for entity_type, p in sorted(progress.items()):
            status_icon = {
                'completed': '[OK]',
                'in_progress': '[...]',
                'failed': '[ERR]',
                'pending': '[ ]'
            }.get(p.status, '[?]')

            pct = (p.exported_count / p.total_count * 100) if p.total_count > 0 else 0
            print(f"{status_icon} {entity_type:30} {p.exported_count:>8} / {p.total_count:>8} ({pct:5.1f}%)")

            if p.error_message:
                print(f"     Error: {p.error_message[:50]}")

        print("=" * 60 + "\n")

    def reset(self, entity_type: Optional[str] = None):
        """Reset progress for an entity or all entities.

        Args:
            entity_type: If provided, reset only this entity. Otherwise reset all.
        """
        if entity_type:
            self.conn.execute(
                "DELETE FROM export_progress WHERE entity_type = ?",
                [entity_type]
            )
            logger.info(f"Reset progress for {entity_type}")
        else:
            self.conn.execute("DELETE FROM export_progress")
            logger.info("Reset all export progress")

    def get_existing_count(self, table_name: str) -> int:
        """Get count of existing records in a table.

        Args:
            table_name: Table name

        Returns:
            Count of existing records
        """
        try:
            result = self.conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
