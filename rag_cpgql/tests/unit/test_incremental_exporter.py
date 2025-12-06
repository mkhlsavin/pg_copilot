"""
Unit tests for Incremental CPG Exporter

Tests:
- Change detection
- Update result handling
- Backup creation
- Validation
- Statistics

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import pytest
import os
import sys
import stat
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def remove_readonly(func, path, excinfo):
    """Handle read-only files on Windows when deleting."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

from src.cpg_export.incremental_exporter import (
    IncrementalCPGExporter,
    UpdateResult,
    UpdateStatus,
    ChangedFile,
    quick_incremental_update,
    detect_changes,
)


class TestUpdateStatus:
    """Test UpdateStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert UpdateStatus.PENDING.value == "pending"
        assert UpdateStatus.IN_PROGRESS.value == "in_progress"
        assert UpdateStatus.COMPLETED.value == "completed"
        assert UpdateStatus.FAILED.value == "failed"
        assert UpdateStatus.ROLLED_BACK.value == "rolled_back"


class TestChangedFile:
    """Test ChangedFile dataclass."""

    def test_creation(self):
        """Test creating changed file."""
        cf = ChangedFile(
            path=Path("/repo/file.c"),
            change_type="modified"
        )

        assert cf.path == Path("/repo/file.c")
        assert cf.change_type == "modified"
        assert cf.old_path is None

    def test_with_rename(self):
        """Test changed file with rename."""
        cf = ChangedFile(
            path=Path("/repo/new_file.c"),
            change_type="renamed",
            old_path=Path("/repo/old_file.c")
        )

        assert cf.old_path == Path("/repo/old_file.c")

    def test_str_representation(self):
        """Test string representation."""
        cf = ChangedFile(
            path=Path("/repo/file.c"),
            change_type="added"
        )

        str_repr = str(cf)
        assert "added" in str_repr
        assert "file.c" in str_repr


class TestUpdateResult:
    """Test UpdateResult dataclass."""

    def test_creation(self):
        """Test creating update result."""
        result = UpdateResult(
            status=UpdateStatus.COMPLETED,
            changed_files=[],
            nodes_added=10,
            nodes_updated=5,
            duration_seconds=2.5
        )

        assert result.status == UpdateStatus.COMPLETED
        assert result.nodes_added == 10
        assert result.duration_seconds == 2.5

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = UpdateResult(
            status=UpdateStatus.COMPLETED,
            changed_files=[
                ChangedFile(path=Path("/repo/file.c"), change_type="added")
            ],
            nodes_added=10,
            nodes_updated=5,
            duration_seconds=2.5
        )

        data = result.to_dict()

        assert data['status'] == 'completed'
        assert data['nodes_added'] == 10
        assert data['duration_seconds'] == 2.5
        assert len(data['changed_files']) == 1

    def test_failed_result(self):
        """Test failed update result."""
        result = UpdateResult(
            status=UpdateStatus.FAILED,
            changed_files=[],
            error="Something went wrong"
        )

        data = result.to_dict()

        assert data['status'] == 'failed'
        assert data['error'] == "Something went wrong"


class TestIncrementalCPGExporter:
    """Test IncrementalCPGExporter class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)

        # Initialize git repo
        os.system(f'cd "{temp_dir}" && git init')
        os.system(f'cd "{temp_dir}" && git config user.email "test@test.com"')
        os.system(f'cd "{temp_dir}" && git config user.name "Test"')

        # Create initial file
        (repo_path / "test.c").write_text("int main() { return 0; }")
        os.system(f'cd "{temp_dir}" && git add . && git commit -m "Initial"')

        yield repo_path

        # Cleanup with Windows-compatible handler
        shutil.rmtree(temp_dir, onerror=remove_readonly)

    @pytest.fixture
    def temp_cpg(self):
        """Create a temporary CPG database."""
        fd, path = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        # Delete the empty file so DuckDB can create a valid database
        os.unlink(path)

        # Initialize with schema
        import duckdb
        conn = duckdb.connect(path)
        conn.execute('''
            CREATE TABLE nodes_method (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                filename VARCHAR,
                signature VARCHAR
            )
        ''')
        conn.execute('''
            CREATE TABLE nodes_call (
                id VARCHAR PRIMARY KEY,
                name VARCHAR
            )
        ''')
        conn.execute('''
            CREATE TABLE edges_call (
                src VARCHAR,
                dst VARCHAR
            )
        ''')
        conn.commit()
        conn.close()

        yield path

        os.unlink(path)

    def test_initialization(self, temp_repo, temp_cpg):
        """Test exporter initialization."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        assert exporter.repo_path == temp_repo
        assert exporter.cpg_path == Path(temp_cpg)

    def test_initialization_invalid_repo(self):
        """Test initialization with invalid repo path."""
        with pytest.raises(ValueError):
            IncrementalCPGExporter(
                repo_path="/nonexistent/path",
                cpg_path="test.db"
            )

    def test_get_stats(self, temp_repo, temp_cpg):
        """Test getting exporter statistics."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        stats = exporter.get_stats()

        assert 'repo_path' in stats
        assert 'cpg_path' in stats
        assert 'cpg_exists' in stats
        assert 'backup_enabled' in stats
        assert stats['total_updates'] == 0

    def test_validate_cpg(self, temp_repo, temp_cpg):
        """Test CPG validation."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        validation = exporter.validate_cpg()

        assert 'valid' in validation
        assert 'issues' in validation
        assert 'stats' in validation

    def test_get_update_history_empty(self, temp_repo, temp_cpg):
        """Test getting empty update history."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        history = exporter.get_update_history()
        assert history == []

    @patch('subprocess.run')
    def test_get_changed_files(self, mock_run, temp_repo, temp_cpg):
        """Test getting changed files."""
        # Mock git diff output
        mock_run.return_value = Mock(
            stdout="A\tfile1.c\nM\tfile2.c\nD\tfile3.c\n",
            returncode=0
        )

        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        changes = exporter.get_changed_files()

        assert len(changes) == 3
        assert changes[0].change_type == "added"
        assert changes[1].change_type == "modified"
        assert changes[2].change_type == "deleted"

    @patch('subprocess.run')
    def test_get_changed_files_filters_extensions(self, mock_run, temp_repo, temp_cpg):
        """Test that only supported extensions are included."""
        # Mock git diff with mixed file types
        mock_run.return_value = Mock(
            stdout="A\tfile1.c\nA\tfile2.txt\nA\tfile3.py\n",
            returncode=0
        )

        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg
        )

        changes = exporter.get_changed_files()

        # Should only include .c and .py, not .txt
        assert len(changes) == 2

    @patch('subprocess.run')
    def test_incremental_update_no_changes(self, mock_run, temp_repo, temp_cpg):
        """Test incremental update with no changes."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg,
            backup_enabled=False
        )

        result = exporter.incremental_update()

        assert result.status == UpdateStatus.COMPLETED
        assert len(result.changed_files) == 0

    @patch('subprocess.run')
    def test_incremental_update_dry_run(self, mock_run, temp_repo, temp_cpg):
        """Test dry run mode."""
        mock_run.return_value = Mock(
            stdout="A\tfile1.c\n",
            returncode=0
        )

        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg,
            backup_enabled=False
        )

        result = exporter.incremental_update(dry_run=True)

        assert result.status == UpdateStatus.COMPLETED
        assert len(result.changed_files) == 1
        # Dry run should not modify database

    def test_backup_creation(self, temp_repo, temp_cpg):
        """Test backup creation."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path=temp_cpg,
            backup_enabled=True
        )

        backup_path = exporter._create_backup()

        assert backup_path.exists()
        assert "backup" in backup_path.name

        # Cleanup
        backup_path.unlink()


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)

        # Initialize git repo
        os.system(f'cd "{temp_dir}" && git init')
        os.system(f'cd "{temp_dir}" && git config user.email "test@test.com"')
        os.system(f'cd "{temp_dir}" && git config user.name "Test"')

        # Create initial file
        (repo_path / "test.c").write_text("int main() { return 0; }")
        os.system(f'cd "{temp_dir}" && git add . && git commit -m "Initial"')

        yield str(repo_path)

        shutil.rmtree(temp_dir, onerror=remove_readonly)

    @patch('subprocess.run')
    def test_detect_changes(self, mock_run, temp_git_repo):
        """Test detect_changes helper."""
        mock_run.return_value = Mock(
            stdout="A\tfile.c\n",
            returncode=0
        )

        changes = detect_changes(repo_path=temp_git_repo)

        assert isinstance(changes, list)


class TestSupportedExtensions:
    """Test supported file extension handling."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)

        os.system(f'cd "{temp_dir}" && git init')
        os.system(f'cd "{temp_dir}" && git config user.email "test@test.com"')
        os.system(f'cd "{temp_dir}" && git config user.name "Test"')

        (repo_path / "test.c").write_text("int main() {}")
        os.system(f'cd "{temp_dir}" && git add . && git commit -m "Initial"')

        yield repo_path

        shutil.rmtree(temp_dir, onerror=remove_readonly)

    def test_default_extensions(self, temp_repo):
        """Test default supported extensions."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path="test.db"
        )

        assert '.c' in exporter.supported_extensions
        assert '.h' in exporter.supported_extensions
        assert '.py' in exporter.supported_extensions

    def test_custom_extensions(self, temp_repo):
        """Test custom supported extensions."""
        exporter = IncrementalCPGExporter(
            repo_path=str(temp_repo),
            cpg_path="test.db",
            supported_extensions=['.rs', '.go']
        )

        assert '.rs' in exporter.supported_extensions
        assert '.go' in exporter.supported_extensions
        assert '.c' not in exporter.supported_extensions


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
