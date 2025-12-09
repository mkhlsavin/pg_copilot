"""
Tests for Review Router.

Tests for POST /review/patch, POST /review/pr, POST /review/mr
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User
from tests.api.conftest import API_V1_PREFIX


def create_mock_review_result(
    recommendation: str = "APPROVE",
    score: float = 0.85,
    findings_count: int = 2,
):
    """Create a mock review result."""
    mock_result = MagicMock()
    mock_result.recommendation = recommendation
    mock_result.score = score
    mock_result.summary = "Code review completed successfully."
    mock_result.processing_time_ms = 150.5
    mock_result.metadata = {"version": "1.0"}
    mock_result.dod_compliance = None

    # Create mock findings
    mock_result.findings = []
    for i in range(findings_count):
        finding = MagicMock()
        finding.model_dump.return_value = {
            "category": "style" if i % 2 == 0 else "security",
            "severity": "low" if i % 2 == 0 else "high",
            "file_path": f"src/file{i}.py",
            "line_start": 10 + i,
            "line_end": 15 + i,
            "description": f"Finding {i} description",
            "suggestion": f"Fix suggestion {i}",
            "code_snippet": f"def func{i}(): pass",
        }
        mock_result.findings.append(finding)

    return mock_result


class TestReviewPatchEndpoint:
    """Tests for POST /review/patch endpoint."""

    @pytest.mark.asyncio
    async def test_review_patch_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful patch review."""
        mock_result = create_mock_review_result()

        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_patch = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                f"{API_V1_PREFIX}/review/patch",
                headers=auth_headers,
                json={
                    "patch_content": "diff --git a/file.py b/file.py\n+def new_func(): pass",
                    "task_description": "Add new function",
                    "output_format": "json",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "APPROVE"
        assert data["score"] == 85.0  # 0.85 * 100
        assert len(data["findings"]) == 2
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_review_patch_with_dod_items(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test patch review with Definition of Done items."""
        mock_result = create_mock_review_result()
        mock_result.dod_compliance = {
            "Unit tests added": True,
            "Documentation updated": False,
        }

        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_patch = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                f"{API_V1_PREFIX}/review/patch",
                headers=auth_headers,
                json={
                    "patch_content": "diff --git a/file.py b/file.py\n+def new_func(): pass",
                    "dod_items": ["Unit tests added", "Documentation updated"],
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dod_validation"] is not None
        assert len(data["dod_validation"]) == 2

    @pytest.mark.asyncio
    async def test_review_patch_empty_content(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test patch review with empty content."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/patch",
            headers=auth_headers,
            json={
                "patch_content": "",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_review_patch_invalid_format(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test patch review with invalid output format."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/patch",
            headers=auth_headers,
            json={
                "patch_content": "some diff content",
                "output_format": "invalid",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_review_patch_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test patch review without authentication."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/patch",
            json={
                "patch_content": "diff content",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_review_patch_service_error(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test patch review when service raises error."""
        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_patch = AsyncMock(side_effect=Exception("Service error"))
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                f"{API_V1_PREFIX}/review/patch",
                headers=auth_headers,
                json={
                    "patch_content": "diff --git a/file.py b/file.py",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "COMMENT"
        assert data["score"] == 0.0
        assert len(data["findings"]) == 1
        assert "error" in data["findings"][0]["category"]


class TestReviewGitHubPREndpoint:
    """Tests for POST /review/pr endpoint."""

    @pytest.mark.asyncio
    async def test_review_github_pr_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful GitHub PR review."""
        mock_result = create_mock_review_result()

        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_github_pr = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            headers = {**auth_headers, "X-GitHub-Token": "ghp_test_token"}
            response = await async_client.post(
                f"{API_V1_PREFIX}/review/pr",
                headers=headers,
                json={
                    "owner": "testorg",
                    "repo": "testrepo",
                    "pr_number": 123,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "APPROVE"
        assert data["score"] == 85.0

    @pytest.mark.asyncio
    async def test_review_github_pr_missing_token(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitHub PR review without token."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/pr",
            headers=auth_headers,
            json={
                "owner": "testorg",
                "repo": "testrepo",
                "pr_number": 123,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "X-GitHub-Token" in data["detail"]

    @pytest.mark.asyncio
    async def test_review_github_pr_invalid_pr_number(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitHub PR review with invalid PR number."""
        headers = {**auth_headers, "X-GitHub-Token": "ghp_test_token"}
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/pr",
            headers=headers,
            json={
                "owner": "testorg",
                "repo": "testrepo",
                "pr_number": 0,  # Invalid - must be > 0
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_review_github_pr_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test GitHub PR review without API authentication."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/pr",
            headers={"X-GitHub-Token": "ghp_test_token"},
            json={
                "owner": "testorg",
                "repo": "testrepo",
                "pr_number": 123,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_review_github_pr_service_error(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitHub PR review when service raises error."""
        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_github_pr = AsyncMock(side_effect=Exception("GitHub API error"))
            mock_get_service.return_value = mock_service

            headers = {**auth_headers, "X-GitHub-Token": "ghp_test_token"}
            response = await async_client.post(
                f"{API_V1_PREFIX}/review/pr",
                headers=headers,
                json={
                    "owner": "testorg",
                    "repo": "testrepo",
                    "pr_number": 123,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "COMMENT"
        assert "GitHub" in data["findings"][0]["message"]


class TestReviewGitLabMREndpoint:
    """Tests for POST /review/mr endpoint."""

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful GitLab MR review."""
        mock_result = create_mock_review_result()

        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_gitlab_mr = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            headers = {**auth_headers, "X-GitLab-Token": "glpat_test_token"}
            response = await async_client.post(
                f"{API_V1_PREFIX}/review/mr",
                headers=headers,
                json={
                    "project_id": "12345",
                    "mr_iid": 456,
                    "gitlab_url": "https://gitlab.com",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "APPROVE"
        assert data["score"] == 85.0

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_missing_token(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitLab MR review without token."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/mr",
            headers=auth_headers,
            json={
                "project_id": "12345",
                "mr_iid": 456,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "X-GitLab-Token" in data["detail"]

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_custom_url(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitLab MR review with custom GitLab URL."""
        mock_result = create_mock_review_result()

        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_gitlab_mr = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            headers = {**auth_headers, "X-GitLab-Token": "glpat_test_token"}
            response = await async_client.post(
                f"{API_V1_PREFIX}/review/mr",
                headers=headers,
                json={
                    "project_id": "mygroup/myproject",
                    "mr_iid": 789,
                    "gitlab_url": "https://gitlab.mycompany.com",
                },
            )

        assert response.status_code == status.HTTP_200_OK

        # Verify custom URL was passed to service
        call_args = mock_service.review_gitlab_mr.call_args
        assert call_args.kwargs["gitlab_url"] == "https://gitlab.mycompany.com"

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_invalid_mr_iid(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitLab MR review with invalid MR IID."""
        headers = {**auth_headers, "X-GitLab-Token": "glpat_test_token"}
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/mr",
            headers=headers,
            json={
                "project_id": "12345",
                "mr_iid": -1,  # Invalid - must be > 0
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test GitLab MR review without API authentication."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/review/mr",
            headers={"X-GitLab-Token": "glpat_test_token"},
            json={
                "project_id": "12345",
                "mr_iid": 456,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_review_gitlab_mr_service_error(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test GitLab MR review when service raises error."""
        with patch("src.api.routers.review.get_review_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.review_gitlab_mr = AsyncMock(side_effect=Exception("GitLab API error"))
            mock_get_service.return_value = mock_service

            headers = {**auth_headers, "X-GitLab-Token": "glpat_test_token"}
            response = await async_client.post(
                f"{API_V1_PREFIX}/review/mr",
                headers=headers,
                json={
                    "project_id": "12345",
                    "mr_iid": 456,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "COMMENT"
        assert "GitLab" in data["findings"][0]["message"]
