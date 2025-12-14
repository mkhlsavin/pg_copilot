"""Tests for project_import registry module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

import pytest

from src.project_import.registry import ProjectRegistry


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def registry(mock_session):
    """Create ProjectRegistry with mock session."""
    return ProjectRegistry(mock_session)


class TestProjectRegistry:
    """Tests for ProjectRegistry project operations."""

    @pytest.mark.asyncio
    async def test_create_project(self, registry, mock_session):
        """Test creating a new project."""
        group_id = uuid4()
        project_id = uuid4()

        # Mock the project model
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test_project"

        with patch("src.project_import.registry.Project", return_value=mock_project):
            result = await registry.create_project(
                name="test_project",
                group_id=group_id,
                source_path="/path/to/source",
                cpg_path="/path/to/cpg",
                duckdb_path="/path/to/db",
                language="python",
                description="Test project",
                metadata={"key": "value"},
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_project(self, registry, mock_session):
        """Test getting project by ID."""
        project_id = uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        result = await registry.get_project(project_id)

        assert result == mock_project
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, registry, mock_session):
        """Test getting non-existent project."""
        project_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await registry.get_project(project_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_by_name(self, registry, mock_session):
        """Test getting project by name."""
        mock_project = MagicMock()
        mock_project.name = "my_project"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        result = await registry.get_project_by_name("my_project")

        assert result == mock_project

    @pytest.mark.asyncio
    async def test_list_projects(self, registry, mock_session):
        """Test listing projects."""
        mock_projects = [MagicMock(), MagicMock()]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_projects

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await registry.list_projects()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_projects_filtered(self, registry, mock_session):
        """Test listing projects with filters."""
        group_id = uuid4()
        mock_projects = [MagicMock()]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_projects

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await registry.list_projects(
            group_id=group_id,
            language="python",
            active_only=True,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_active_project(self, registry, mock_session):
        """Test getting active project."""
        mock_project = MagicMock()
        mock_project.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        result = await registry.get_active_project()

        assert result == mock_project
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_set_active_project(self, registry, mock_session):
        """Test activating a project."""
        project_id = uuid4()
        group_id = uuid4()

        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.group_id = group_id
        mock_project.name = "test_project"

        # Mock get_project to return the project
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        with patch.object(registry, "get_project", return_value=mock_project):
            result = await registry.set_active_project(project_id)

            assert result is True
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_set_active_project_not_found(self, registry, mock_session):
        """Test activating non-existent project."""
        project_id = uuid4()

        with patch.object(registry, "get_project", return_value=None):
            result = await registry.set_active_project(project_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_project(self, registry, mock_session):
        """Test deleting a project."""
        project_id = uuid4()

        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test_project"
        mock_project.cpg_path = None
        mock_project.db_path = None
        mock_project.source_path = None

        with patch.object(registry, "get_project", return_value=mock_project):
            result = await registry.delete_project(project_id)

            assert result is True
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_project_with_files(self, registry, mock_session, tmp_path):
        """Test deleting project with files."""
        project_id = uuid4()

        cpg_path = tmp_path / "test.cpg"
        cpg_path.touch()

        db_path = tmp_path / "test.duckdb"
        db_path.touch()

        source_path = tmp_path / "source"
        source_path.mkdir()

        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test_project"
        mock_project.cpg_path = str(cpg_path)
        mock_project.db_path = str(db_path)
        mock_project.source_path = str(source_path)

        with patch.object(registry, "get_project", return_value=mock_project):
            result = await registry.delete_project(project_id, delete_files=True)

            assert result is True
            assert not cpg_path.exists()
            assert not db_path.exists()
            assert not source_path.exists()

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, registry, mock_session):
        """Test deleting non-existent project."""
        project_id = uuid4()

        with patch.object(registry, "get_project", return_value=None):
            result = await registry.delete_project(project_id)

            assert result is False


class TestImportJobRegistry:
    """Tests for ProjectRegistry import job operations."""

    @pytest.mark.asyncio
    async def test_create_import_job(self, registry, mock_session):
        """Test creating import job."""
        user_id = uuid4()
        group_id = uuid4()
        job_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.project_name = "test_project"

        with patch("src.project_import.registry.ImportJob", return_value=mock_job):
            with patch("src.project_import.registry.ImportStatus"):
                with patch("src.project_import.registry.ImportMode"):
                    result = await registry.create_import_job(
                        user_id=user_id,
                        group_id=group_id,
                        project_name="test_project",
                        source_url="https://github.com/test/repo",
                        language="python",
                        import_mode="full",
                    )

                    mock_session.add.assert_called_once()
                    mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_import_job(self, registry, mock_session):
        """Test getting import job by ID."""
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result

        result = await registry.get_import_job(job_id)

        assert result == mock_job

    @pytest.mark.asyncio
    async def test_list_import_jobs(self, registry, mock_session):
        """Test listing import jobs."""
        mock_jobs = [MagicMock(), MagicMock()]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_jobs

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await registry.list_import_jobs()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_update_import_job(self, registry, mock_session):
        """Test updating import job progress."""
        job_id = uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result

        with patch.object(registry, "get_import_job", return_value=mock_job):
            result = await registry.update_import_job(
                job_id=job_id,
                status="in_progress",
                progress=50,
                current_step="joern_import",
            )

            mock_session.execute.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_complete_import_job(self, registry, mock_session):
        """Test marking job as completed."""
        job_id = uuid4()
        project_id = uuid4()
        mock_job = MagicMock()

        with patch.object(registry, "update_import_job", return_value=mock_job) as mock_update:
            result = await registry.complete_import_job(
                job_id=job_id,
                project_id=project_id,
                result={"cpg_path": "/path/to/cpg"},
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args.kwargs["progress"] == 100

    @pytest.mark.asyncio
    async def test_fail_import_job(self, registry, mock_session):
        """Test marking job as failed."""
        job_id = uuid4()
        mock_job = MagicMock()

        with patch.object(registry, "update_import_job", return_value=mock_job) as mock_update:
            result = await registry.fail_import_job(
                job_id=job_id,
                error_message="Something went wrong",
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args.kwargs["error_message"] == "Something went wrong"


class TestProjectGroupRegistry:
    """Tests for project group operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_default_group_exists(self, registry, mock_session):
        """Test getting existing default group."""
        mock_group = MagicMock()
        mock_group.name = "default"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_group
        mock_session.execute.return_value = mock_result

        result = await registry.get_or_create_default_group()

        assert result == mock_group
        # Should not create new group
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_default_group_creates(self, registry, mock_session):
        """Test creating default group when not exists."""
        mock_group = MagicMock()
        mock_group.name = "default"

        # First call returns None (not found), then returns created group
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("src.project_import.registry.ProjectGroup", return_value=mock_group):
            result = await registry.get_or_create_default_group()

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_list_groups(self, registry, mock_session):
        """Test listing all project groups."""
        mock_groups = [MagicMock(), MagicMock()]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_groups

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await registry.list_groups()

        assert len(result) == 2
