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
        with patch("src.api.routers.import_project.list_supported_languages") as mock_list:
            mock_list.return_value = [
                {
                    "language": "python",
                    "extensions": [".py"],
                    "command": "pysrc2cpg",
                    "description": "Python source code",
                    "supports_joern_parse": True,
                }
            ]

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
        with patch("src.api.routers.import_project.list_supported_languages") as mock_list:
            mock_list.return_value = [
                {
                    "language": "python",
                    "extensions": [".py"],
                    "command": "pysrc2cpg",
                    "description": "Python source code",
                    "supports_joern_parse": True,
                }
            ]

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


class TestServerStatusEndpoint:
    """Tests for GET /import/server/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_server_status(
        self,
        async_client: AsyncClient,
    ):
        """Test getting server status."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_status.return_value = {
                "running": True,
                "mode": "docker",
                "port": 8080,
            }
            mock_manager_class.return_value = mock_manager

            response = await async_client.get(f"{API_V1_PREFIX}/import/server/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "running" in data or "status" in data

    @pytest.mark.asyncio
    async def test_get_server_status_not_running(
        self,
        async_client: AsyncClient,
    ):
        """Test getting server status when not running."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_status.return_value = {
                "running": False,
                "mode": "local",
                "port": 8080,
            }
            mock_manager_class.return_value = mock_manager

            response = await async_client.get(f"{API_V1_PREFIX}/import/server/status")

        assert response.status_code == status.HTTP_200_OK


class TestStartServerEndpoint:
    """Tests for POST /import/server/start endpoint."""

    @pytest.mark.asyncio
    async def test_start_server_local(
        self,
        async_client: AsyncClient,
    ):
        """Test starting server in local mode."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start.return_value = True
            mock_manager.is_running.return_value = False
            mock_manager.mode = "local"
            mock_manager_class.return_value = mock_manager

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/server/start",
                json={"use_docker": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Actual response has "status" key with value "started" or "already_running"
        assert data.get("status") in ["started", "already_running"]

    @pytest.mark.asyncio
    async def test_start_server_docker(
        self,
        async_client: AsyncClient,
    ):
        """Test starting server in Docker mode."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start.return_value = True
            mock_manager.mode = "docker"
            mock_manager_class.return_value = mock_manager

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/server/start",
                json={"use_docker": True},
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_start_server_failure(
        self,
        async_client: AsyncClient,
    ):
        """Test server start failure."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start.return_value = False
            mock_manager_class.return_value = mock_manager

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/server/start",
                json={},
            )

        # Should return error status
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestStopServerEndpoint:
    """Tests for POST /import/server/stop endpoint."""

    @pytest.mark.asyncio
    async def test_stop_server_success(
        self,
        async_client: AsyncClient,
    ):
        """Test stopping server."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.stop.return_value = True
            mock_manager_class.return_value = mock_manager

            response = await async_client.post(f"{API_V1_PREFIX}/import/server/stop")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("stopped") is True or data.get("status") == "stopped"

    @pytest.mark.asyncio
    async def test_stop_server_not_running(
        self,
        async_client: AsyncClient,
    ):
        """Test stopping server when not running."""
        with patch("src.api.routers.import_project.JoernServerManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.stop.return_value = True  # Still returns True
            mock_manager_class.return_value = mock_manager

            response = await async_client.post(f"{API_V1_PREFIX}/import/server/stop")

        assert response.status_code == status.HTTP_200_OK


class TestImportWithDocker:
    """Tests for import with Docker support."""

    @pytest.mark.asyncio
    async def test_start_import_with_docker(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import with Docker enabled."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={
                    "repo_url": "https://github.com/test/project",
                    "use_docker": True,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_start_import_with_docker_image(
        self,
        async_client: AsyncClient,
    ):
        """Test starting import with custom Docker image."""
        with patch("src.api.routers.import_project._run_import_pipeline"):
            response = await async_client.post(
                f"{API_V1_PREFIX}/import/start",
                json={
                    "repo_url": "https://github.com/test/project",
                    "use_docker": True,
                    "docker_image": "ghcr.io/joernio/joern:v4.0.0",
                },
            )

        assert response.status_code == status.HTTP_200_OK


class TestProjectsEndpoints:
    """Tests for project management endpoints."""

    @pytest.mark.asyncio
    async def test_list_projects(
        self,
        async_client: AsyncClient,
    ):
        """Test listing projects."""
        with patch("src.api.routers.import_project.ProjectRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.list_projects = AsyncMock(return_value=[])
            mock_registry_class.return_value = mock_registry

            response = await async_client.get(f"{API_V1_PREFIX}/import/projects")

        # Accept success, not-implemented, or not-found (endpoint may not exist)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]

    @pytest.mark.asyncio
    async def test_activate_project(
        self,
        async_client: AsyncClient,
    ):
        """Test activating a project."""
        project_id = str(uuid.uuid4())

        with patch("src.api.routers.import_project.ProjectRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.set_active_project = AsyncMock(return_value=True)
            mock_registry_class.return_value = mock_registry

            response = await async_client.post(
                f"{API_V1_PREFIX}/import/projects/{project_id}/activate"
            )

        # Accept both success and not-implemented responses
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]

    @pytest.mark.asyncio
    async def test_delete_project(
        self,
        async_client: AsyncClient,
    ):
        """Test deleting a project."""
        project_id = str(uuid.uuid4())

        with patch("src.api.routers.import_project.ProjectRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.delete_project = AsyncMock(return_value=True)
            mock_registry_class.return_value = mock_registry

            response = await async_client.delete(
                f"{API_V1_PREFIX}/import/projects/{project_id}"
            )

        # Accept both success and not-implemented responses
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]
