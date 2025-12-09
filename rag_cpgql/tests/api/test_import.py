"""
Tests for Import Project Router.

Tests for:
- GET /import/languages
- POST /import/start
- GET /import/status/{job_id}
- GET /import/jobs
- DELETE /import/cancel/{job_id}
- POST /import/step
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient

from tests.api.conftest import API_V1_PREFIX


class TestListLanguagesEndpoint:
    """Tests for GET /import/languages endpoint."""

    @pytest.mark.asyncio
    async def test_list_languages_success(
        self,
        async_client: AsyncClient,
    ):
        """Test listing supported languages."""
        with patch("src.api.routers.import_project.JOERN_FRONTENDS") as mock_frontends:
            # Create mock frontend
            mock_frontend = MagicMock()
            mock_frontend.file_extensions = [".py"]
            mock_frontend.command = "pysrc2cpg"
            mock_frontend.joern_language_flag = "python"

            # Create mock enum-like key
            mock_lang = MagicMock()
            mock_lang.value = "python"
            mock_lang.name = "PYTHON"

            mock_frontends.items.return_value = [(mock_lang, mock_frontend)]

            response = await async_client.get(f"{API_V1_PREFIX}/import/languages")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "languages" in data
        assert isinstance(data["languages"], list)

    @pytest.mark.asyncio
    async def test_list_languages_contains_python(
        self,
        async_client: AsyncClient,
    ):
        """Test that Python is in supported languages."""
        with patch("src.api.routers.import_project.JOERN_FRONTENDS") as mock_frontends:
            mock_frontend = MagicMock()
            mock_frontend.file_extensions = [".py"]
            mock_frontend.command = "pysrc2cpg"
            mock_frontend.joern_language_flag = "python"

            mock_lang = MagicMock()
            mock_lang.value = "python"
            mock_lang.name = "PYTHON"

            mock_frontends.items.return_value = [(mock_lang, mock_frontend)]

            response = await async_client.get(f"{API_V1_PREFIX}/import/languages")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        ids = [lang["id"] for lang in data["languages"]]
        assert "python" in ids


class TestStartImportEndpoint:
    """Tests for POST /import/start endpoint."""

    @pytest.mark.asyncio
    async def test_start_import_with_repo_url(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import with repository URL."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={
                    "repo_url": "https://github.com/test/project.git",
                    "branch": "main",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    @pytest.mark.asyncio
    async def test_start_import_with_local_path(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import with local path."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={
                    "local_path": "/path/to/project",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_start_import_missing_source(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import without repo_url or local_path."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/import/start",
            json={
                "branch": "main",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "repo_url or local_path" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_import_with_options(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import with all options."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={
                    "repo_url": "https://github.com/test/project",
                    "branch": "develop",
                    "shallow_clone": True,
                    "shallow_depth": 1,
                    "language": "python",
                    "mode": "full",
                    "include_paths": ["src/"],
                    "exclude_paths": ["tests/"],
                    "create_domain_plugin": True,
                    "domain_name": "my_project",
                    "import_docs": True,
                    "joern_memory_gb": 32,
                    "batch_size": 5000,
                },
            )

        assert response.status_code == status.HTTP_200_OK


class TestGetImportStatusEndpoint:
    """Tests for GET /import/status/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_success(
        self,
        async_client: AsyncClient,
    ):
        """Test getting import status."""
        # First start an import to create a job
        with patch("src.api.routers.import_project._run_import_pipeline"):
            start_response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={"repo_url": "https://github.com/test/project"},
            )

        job_id = start_response.json()["job_id"]

        # Get status
        response = await async_client.get(
            f"{API_V1_PREFIX}/import/status/{job_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "project_name" in data

    @pytest.mark.asyncio
    async def test_get_status_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test getting status for non-existent job."""
        fake_job_id = str(uuid.uuid4())

        response = await async_client.get(
            f"{API_V1_PREFIX}/import/status/{fake_job_id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestListImportJobsEndpoint:
    """Tests for GET /import/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self,
        async_client: AsyncClient,
    ):
        """Test listing jobs when none exist."""
        # Clear any existing jobs
        with patch("src.api.routers.import_project._import_jobs", {}):
            response = await async_client.get(f"{API_V1_PREFIX}/import/jobs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_jobs_with_limit(
        self,
        async_client: AsyncClient,
    ):
        """Test listing jobs with limit."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/import/jobs",
            params={"limit": 5},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 5

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(
        self,
        async_client: AsyncClient,
    ):
        """Test listing jobs filtered by status."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/import/jobs",
            params={"status_filter": "completed"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for job in data:
            assert job["status"] == "completed"


class TestCancelImportEndpoint:
    """Tests for DELETE /import/cancel/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_job_success(
        self,
        async_client: AsyncClient,
    ):
        """Test cancelling a pending job."""
        # Start an import
        with patch("src.api.routers.import_project._run_import_pipeline"):
            start_response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={"repo_url": "https://github.com/test/project"},
            )

        job_id = start_response.json()["job_id"]

        # Cancel it
        response = await async_client.delete(
            f"{API_V1_PREFIX}/import/cancel/{job_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test cancelling non-existent job."""
        fake_job_id = str(uuid.uuid4())

        response = await async_client.delete(
            f"{API_V1_PREFIX}/import/cancel/{fake_job_id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cancel_completed_job(
        self,
        async_client: AsyncClient,
    ):
        """Test that completed jobs cannot be cancelled."""
        # Start and manually complete a job
        with patch("src.api.routers.import_project._run_import_pipeline"):
            start_response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={"repo_url": "https://github.com/test/project"},
            )

        job_id = start_response.json()["job_id"]

        # Manually set status to completed
        from src.api.routers import import_project
        import_project._import_jobs[job_id].status = "completed"

        # Try to cancel
        response = await async_client.delete(
            f"{API_V1_PREFIX}/import/cancel/{job_id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "cannot cancel" in data["detail"].lower()


class TestRunSingleStepEndpoint:
    """Tests for POST /import/step endpoint."""

    @pytest.mark.asyncio
    async def test_run_step_success(
        self,
        async_client: AsyncClient,
    ):
        """Test running a single import step."""
        with patch("src.api.routers.import_project.ProjectImportPipeline") as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.run_step = AsyncMock(return_value={"status": "success"})
            mock_pipeline_class.return_value = mock_pipeline

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/step",
                json={
                    "step_id": "detect_language",
                    "context": {"path": "/some/path"},
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["step"] == "detect_language"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_step_invalid_step(
        self,
        async_client: AsyncClient,
    ):
        """Test running an invalid step."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/import/step",
            json={
                "step_id": "invalid_step",
                "context": {},
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid step" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_run_step_all_valid_steps(
        self,
        async_client: AsyncClient,
    ):
        """Test that all documented steps are valid."""
        valid_steps = [
            "clone",
            "detect_language",
            "joern_import",
            "cpg_export",
            "validate",
            "chromadb_import",
            "domain_setup",
        ]

        for step_id in valid_steps:
            with patch("src.api.routers.import_project.ProjectImportPipeline") as mock_pipeline_class:
                mock_pipeline = MagicMock()
                mock_pipeline.run_step = AsyncMock(return_value={})
                mock_pipeline_class.return_value = mock_pipeline

                response = await async_client.post(
                    f"{API_V1_PREFIX}/import/step",
                    json={
                        "step_id": step_id,
                        "context": {},
                    },
                )

            assert response.status_code == status.HTTP_200_OK, (
                f"Step '{step_id}' should be valid"
            )

    @pytest.mark.asyncio
    async def test_run_step_pipeline_error(
        self,
        async_client: AsyncClient,
    ):
        """Test handling pipeline errors."""
        with patch("src.api.routers.import_project.ProjectImportPipeline") as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.run_step = AsyncMock(side_effect=Exception("Pipeline failed"))
            mock_pipeline_class.return_value = mock_pipeline

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/step",
                json={
                    "step_id": "clone",
                    "context": {"repo_url": "invalid"},
                },
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestProjectNameExtraction:
    """Tests for project name extraction logic."""

    @pytest.mark.asyncio
    async def test_extracts_name_from_repo_url(
        self,
        async_client: AsyncClient,
    ):
        """Test project name extraction from repo URL."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={"repo_url": "https://github.com/org/my-project.git"},
            )

        job_id = response.json()["job_id"]

        status_response = await async_client.get(
            f"{API_V1_PREFIX}/import/status/{job_id}"
        )

        assert status_response.json()["project_name"] == "my-project"

    @pytest.mark.asyncio
    async def test_extracts_name_from_local_path(
        self,
        async_client: AsyncClient,
    ):
        """Test project name extraction from local path."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={"local_path": "/home/user/projects/my_project"},
            )

        job_id = response.json()["job_id"]

        status_response = await async_client.get(
            f"{API_V1_PREFIX}/import/status/{job_id}"
        )

        assert status_response.json()["project_name"] == "my_project"
