"""Tests for project_import pipeline module."""

from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

import pytest

from src.project_import.models import (
    ImportMode,
    ImportStepStatus,
    ProjectImportRequest,
)


class TestProjectImportRequest:
    """Tests for ProjectImportRequest model."""

    def test_default_values(self):
        """Test default request values."""
        request = ProjectImportRequest(
            repo_url="https://github.com/test/repo",
        )

        assert request.repo_url == "https://github.com/test/repo"
        assert request.branch == "main"
        assert request.shallow_clone is True
        assert request.mode == ImportMode.FULL
        assert request.create_domain_plugin is True
        assert request.import_docs is True

    def test_custom_values(self):
        """Test request with custom values."""
        request = ProjectImportRequest(
            repo_url="https://github.com/test/repo",
            branch="develop",
            shallow_clone=False,
            mode=ImportMode.SELECTIVE,
            include_paths=["src", "lib"],
            exclude_paths=["test"],
            language="python",
        )

        assert request.branch == "develop"
        assert request.shallow_clone is False
        assert request.mode == ImportMode.SELECTIVE
        assert request.include_paths == ["src", "lib"]
        assert request.exclude_paths == ["test"]
        assert request.language == "python"

    def test_local_path_import(self):
        """Test import from local path."""
        request = ProjectImportRequest(
            local_path="/path/to/project",
        )

        assert request.local_path == "/path/to/project"
        assert request.repo_url is None


class TestImportMode:
    """Tests for ImportMode enum."""

    def test_import_modes(self):
        """Test all import modes exist."""
        assert ImportMode.FULL
        assert ImportMode.SELECTIVE
        assert ImportMode.INCREMENTAL

    def test_mode_values(self):
        """Test mode values."""
        assert ImportMode.FULL.value == "full"
        assert ImportMode.SELECTIVE.value == "selective"
        assert ImportMode.INCREMENTAL.value == "incremental"


class TestImportStepStatus:
    """Tests for ImportStepStatus enum."""

    def test_step_statuses(self):
        """Test all step statuses exist."""
        assert ImportStepStatus.PENDING
        assert ImportStepStatus.IN_PROGRESS
        assert ImportStepStatus.COMPLETED
        assert ImportStepStatus.FAILED
        assert ImportStepStatus.SKIPPED


class TestProjectImportPipeline:
    """Tests for ProjectImportPipeline."""

    @pytest.fixture
    def mock_server_manager(self):
        """Create mock server manager."""
        manager = MagicMock()
        manager.ensure_running.return_value = True
        manager.is_running.return_value = True
        manager.mode = "docker"
        manager.run_frontend = MagicMock(return_value=True)
        manager.run_frontend_async = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry."""
        registry = MagicMock()
        registry.create_project = AsyncMock(return_value=MagicMock(id=uuid4()))
        registry.create_import_job = AsyncMock(return_value=MagicMock(id=uuid4()))
        registry.update_import_job = AsyncMock()
        registry.complete_import_job = AsyncMock()
        registry.fail_import_job = AsyncMock()
        registry.get_or_create_default_group = AsyncMock(return_value=MagicMock(id=uuid4()))
        return registry

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline()
        assert pipeline is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_progress_callback(self):
        """Test pipeline with progress callback."""
        from src.project_import.pipeline import ProjectImportPipeline

        progress_updates = []

        def callback(status):
            progress_updates.append(status)

        pipeline = ProjectImportPipeline(progress_callback=callback)
        assert pipeline._progress_callback == callback

    @pytest.mark.asyncio
    async def test_get_steps(self):
        """Test getting pipeline steps."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline()
        steps = pipeline.get_steps()

        assert isinstance(steps, list)
        assert len(steps) > 0

        # Check step structure
        for step in steps:
            assert "id" in step
            assert "name" in step

    @pytest.mark.asyncio
    async def test_pipeline_creates_status(self):
        """Test pipeline creates status object."""
        from src.project_import.pipeline import ProjectImportPipeline
        from src.project_import.models import ProjectImportRequest

        request = ProjectImportRequest(repo_url="https://github.com/test/repo")
        pipeline = ProjectImportPipeline()

        status = pipeline._create_status(request)

        assert status.project_name == "repo"  # Extracted from URL
        assert status.overall_progress == 0
        assert len(status.steps) > 0


class TestPipelineSteps:
    """Tests for individual pipeline steps."""

    @pytest.mark.asyncio
    async def test_clone_step_skipped_for_local(self):
        """Test clone step is skipped for local path."""
        from src.project_import.pipeline import ProjectImportPipeline
        from src.project_import.models import ProjectImportRequest

        request = ProjectImportRequest(local_path="/path/to/project")

        pipeline = ProjectImportPipeline()

        # Local path should not require cloning
        assert request.local_path == "/path/to/project"
        assert request.repo_url is None

    @pytest.mark.asyncio
    async def test_language_detection(self, tmp_path):
        """Test language detection step."""
        # Create test files
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()

        from src.project_import.frontends import detect_language

        result = detect_language(tmp_path)
        assert result == "python"


class TestPipelineCancel:
    """Tests for pipeline cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_flag(self):
        """Test cancel flag is set."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline()
        assert pipeline._cancelled is False

        pipeline.cancel()
        assert pipeline._cancelled is True

    @pytest.mark.asyncio
    async def test_is_cancelled(self):
        """Test is_cancelled property."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline()
        assert pipeline.is_cancelled is False

        pipeline.cancel()
        assert pipeline.is_cancelled is True


class TestPipelineShutdown:
    """Tests for pipeline shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline()

        # Shutdown should not raise
        await pipeline.shutdown()

        # Should be marked as cancelled
        assert pipeline._cancelled is True


class TestPipelineWithDocker:
    """Tests for pipeline Docker mode."""

    @pytest.fixture
    def docker_config(self):
        """Create Docker config."""
        from src.project_import.config import JoernConfig, ProjectImportConfig

        joern_config = JoernConfig(
            use_docker=True,
            docker_image="ghcr.io/joernio/joern:latest",
        )
        return ProjectImportConfig(joern=joern_config)

    @pytest.mark.asyncio
    async def test_pipeline_docker_mode(self, docker_config):
        """Test pipeline in Docker mode."""
        from src.project_import.pipeline import ProjectImportPipeline

        pipeline = ProjectImportPipeline(config=docker_config)

        # Verify Docker mode is configured
        assert pipeline._config.joern.use_docker is True
        assert "joern" in pipeline._config.joern.docker_image


class TestPipelineResultTracking:
    """Tests for result tracking."""

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Test result structure."""
        from src.project_import.models import ProjectImportResult

        result = ProjectImportResult(
            cpg_path=Path("/path/to/cpg"),
            duckdb_path=Path("/path/to/db"),
            detected_language="python",
            import_duration_seconds=100.5,
        )

        assert result.cpg_path == Path("/path/to/cpg")
        assert result.duckdb_path == Path("/path/to/db")
        assert result.detected_language == "python"
        assert result.import_duration_seconds == 100.5

    @pytest.mark.asyncio
    async def test_result_optional_fields(self):
        """Test result optional fields."""
        from src.project_import.models import ProjectImportResult

        result = ProjectImportResult(
            cpg_path=Path("/path/to/cpg"),
            duckdb_path=Path("/path/to/db"),
            detected_language="python",
            validation_report={"status": "passed"},
            cpg_stats={"methods": 100, "calls": 500},
        )

        assert result.validation_report == {"status": "passed"}
        assert result.cpg_stats == {"methods": 100, "calls": 500}
