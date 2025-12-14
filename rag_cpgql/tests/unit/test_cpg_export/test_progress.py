"""Tests for CPG export progress tracking module."""
import pytest
import duckdb


class TestExportProgress:
    """Tests for ExportProgress dataclass."""

    def test_export_progress_creation(self):
        """Test ExportProgress instantiation."""
        from src.cpg_export.progress import ExportProgress
        from datetime import datetime

        progress = ExportProgress(
            entity_type='nodes_method',
            total_count=1000,
            exported_count=500,
            last_offset=500,
            status='in_progress',
            last_updated=datetime.now()
        )

        assert progress.entity_type == 'nodes_method'
        assert progress.total_count == 1000
        assert progress.exported_count == 500
        assert progress.last_offset == 500
        assert progress.status == 'in_progress'

    def test_export_progress_with_error(self):
        """Test ExportProgress with error message."""
        from src.cpg_export.progress import ExportProgress
        from datetime import datetime

        progress = ExportProgress(
            entity_type='nodes_method',
            total_count=1000,
            exported_count=500,
            last_offset=500,
            status='failed',
            last_updated=datetime.now(),
            error_message='Connection timeout'
        )

        assert progress.status == 'failed'
        assert progress.error_message == 'Connection timeout'


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a ProgressTracker with temp database."""
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        from src.cpg_export.progress import ProgressTracker
        return ProgressTracker(conn), conn

    def test_tracker_creates_table(self, tracker):
        """Test that tracker creates progress table."""
        pt, conn = tracker

        # Check table exists
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        assert 'export_progress' in tables

    def test_get_status_pending(self, tracker):
        """Test get_status returns pending for new entity."""
        pt, conn = tracker

        status, offset = pt.get_status('nodes_method')
        assert status == 'pending'
        assert offset == 0

    def test_update_progress(self, tracker):
        """Test update_progress stores data."""
        pt, conn = tracker

        pt.update_progress(
            entity_type='nodes_method',
            total=1000,
            exported=500,
            offset=500,
            status='in_progress'
        )

        status, offset = pt.get_status('nodes_method')
        assert status == 'in_progress'
        assert offset == 500

    def test_mark_started(self, tracker):
        """Test mark_started."""
        pt, conn = tracker

        pt.mark_started('nodes_method', 1000)

        status, _ = pt.get_status('nodes_method')
        assert status == 'in_progress'

    def test_mark_completed(self, tracker):
        """Test mark_completed."""
        pt, conn = tracker

        pt.mark_completed('nodes_method', 1000)

        status, _ = pt.get_status('nodes_method')
        assert status == 'completed'

    def test_is_completed(self, tracker):
        """Test is_completed."""
        pt, conn = tracker

        assert pt.is_completed('nodes_method') is False

        pt.mark_completed('nodes_method', 1000)
        assert pt.is_completed('nodes_method') is True

    def test_mark_failed(self, tracker):
        """Test mark_failed."""
        pt, conn = tracker

        pt.mark_failed('nodes_method', 'Test error', 500)

        status, offset = pt.get_status('nodes_method')
        assert status == 'failed'

    def test_get_resume_offset(self, tracker):
        """Test get_resume_offset."""
        pt, conn = tracker

        # Pending entity returns 0
        assert pt.get_resume_offset('nodes_method') == 0

        # In progress entity returns last offset
        pt.update_progress('nodes_method', 1000, 500, 500, 'in_progress')
        assert pt.get_resume_offset('nodes_method') == 500

        # Completed entity returns 0
        pt.mark_completed('nodes_method', 1000)
        assert pt.get_resume_offset('nodes_method') == 0

    def test_get_all_progress(self, tracker):
        """Test get_all_progress."""
        pt, conn = tracker

        pt.mark_completed('nodes_method', 1000)
        pt.update_progress('nodes_call', 500, 250, 250, 'in_progress')

        all_progress = pt.get_all_progress()

        assert 'nodes_method' in all_progress
        assert 'nodes_call' in all_progress
        assert all_progress['nodes_method'].status == 'completed'
        assert all_progress['nodes_call'].status == 'in_progress'

    def test_reset_single(self, tracker):
        """Test reset for single entity."""
        pt, conn = tracker

        pt.mark_completed('nodes_method', 1000)
        pt.mark_completed('nodes_call', 500)

        pt.reset('nodes_method')

        assert pt.is_completed('nodes_method') is False
        assert pt.is_completed('nodes_call') is True

    def test_reset_all(self, tracker):
        """Test reset for all entities."""
        pt, conn = tracker

        pt.mark_completed('nodes_method', 1000)
        pt.mark_completed('nodes_call', 500)

        pt.reset()

        assert pt.is_completed('nodes_method') is False
        assert pt.is_completed('nodes_call') is False

    def test_get_existing_count(self, tracker):
        """Test get_existing_count."""
        pt, conn = tracker

        # Create a test table
        conn.execute("CREATE TABLE test_table (id INTEGER)")
        conn.execute("INSERT INTO test_table VALUES (1), (2), (3)")

        count = pt.get_existing_count('test_table')
        assert count == 3

    def test_get_existing_count_nonexistent_table(self, tracker):
        """Test get_existing_count for nonexistent table."""
        pt, conn = tracker

        count = pt.get_existing_count('nonexistent_table')
        assert count == 0

    def test_print_status(self, tracker, capsys):
        """Test print_status output."""
        pt, conn = tracker

        pt.mark_completed('nodes_method', 1000)
        pt.update_progress('nodes_call', 500, 250, 250, 'in_progress')

        pt.print_status()

        captured = capsys.readouterr()
        assert 'EXPORT PROGRESS STATUS' in captured.out
        assert 'nodes_method' in captured.out
        assert 'nodes_call' in captured.out
