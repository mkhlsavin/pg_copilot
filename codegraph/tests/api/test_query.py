"""
Tests for Query Router.

Tests for POST /query/execute, POST /query/validate
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User
from tests.api.conftest import API_V1_PREFIX


class TestExecuteQueryEndpoint:
    """Tests for POST /query/execute endpoint."""

    @pytest.mark.asyncio
    async def test_execute_query_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful query execution."""
        mock_results = [
            {"name": "malloc", "filename": "memory.c"},
            {"name": "free", "filename": "memory.c"},
        ]

        with patch("src.services.cpg_query_service.CPGQueryService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.__enter__ = MagicMock(return_value=mock_service)
            mock_service.__exit__ = MagicMock(return_value=False)
            mock_service.execute_query.return_value = mock_results
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                f"{API_V1_PREFIX}/query/execute",
                headers=auth_headers,
                json={
                    "query": "SELECT name, filename FROM nodes_method LIMIT 10",
                    "timeout": 60,
                    "limit": 100,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["result"]["row_count"] == 2
        assert data["result"]["columns"] == ["name", "filename"]

    @pytest.mark.asyncio
    async def test_execute_query_empty_result(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test query execution with empty result."""
        with patch("src.services.cpg_query_service.CPGQueryService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.__enter__ = MagicMock(return_value=mock_service)
            mock_service.__exit__ = MagicMock(return_value=False)
            mock_service.execute_query.return_value = []
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                f"{API_V1_PREFIX}/query/execute",
                headers=auth_headers,
                json={
                    "query": "SELECT name FROM nodes_method WHERE name = 'nonexistent'",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["result"]["row_count"] == 0
        assert data["result"]["rows"] == []

    @pytest.mark.asyncio
    async def test_execute_query_forbidden_drop(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that DROP statements are rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "DROP TABLE nodes_method",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "forbidden" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_query_forbidden_delete(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that DELETE statements are rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "DELETE FROM nodes_method WHERE id = 1",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "forbidden" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_query_forbidden_insert(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that INSERT statements are rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "INSERT INTO nodes_method (name) VALUES ('test')",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "forbidden" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_query_forbidden_update(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that UPDATE statements are rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "UPDATE nodes_method SET name = 'test' WHERE id = 1",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "forbidden" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_query_non_select_rejected(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that non-SELECT queries are rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "DESCRIBE nodes_method",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "SELECT" in data["error"]

    @pytest.mark.asyncio
    async def test_execute_query_empty_query(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that empty query is rejected."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/execute",
            headers=auth_headers,
            json={
                "query": "",
            },
        )

        # Empty query should fail validation (min_length=1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_execute_query_database_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test query execution when database not found."""
        with patch("src.services.cpg_query_service.CPGQueryService") as mock_service_class:
            mock_service_class.side_effect = FileNotFoundError("Database not found")

            response = await async_client.post(
                f"{API_V1_PREFIX}/query/execute",
                headers=auth_headers,
                json={
                    "query": "SELECT * FROM nodes_method",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_query_unauthenticated(
        self,
        async_client_no_auth: AsyncClient,
    ):
        """Test query execution without authentication."""
        response = await async_client_no_auth.post(
            f"{API_V1_PREFIX}/query/execute",
            json={
                "query": "SELECT * FROM nodes_method",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestValidateQueryEndpoint:
    """Tests for POST /query/validate endpoint."""

    @pytest.mark.asyncio
    async def test_validate_query_valid_select(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation of valid SELECT query."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "SELECT name FROM nodes_method LIMIT 10"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert data["message"] == "Query syntax is valid"

    @pytest.mark.asyncio
    async def test_validate_query_wildcard_warning(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation warns about SELECT *."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "SELECT * FROM nodes_method LIMIT 10"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) > 0
        assert any("SELECT *" in w for w in data["warnings"])

    @pytest.mark.asyncio
    async def test_validate_query_no_limit_warning(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation warns about missing LIMIT."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "SELECT name FROM nodes_method"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) > 0
        assert any("LIMIT" in w for w in data["warnings"])

    @pytest.mark.asyncio
    async def test_validate_query_invalid_drop(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation rejects DROP."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "DROP TABLE nodes_method"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "forbidden" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_validate_query_invalid_non_select(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation rejects non-SELECT queries."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "SHOW TABLES"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "SELECT" in data["message"]

    @pytest.mark.asyncio
    async def test_validate_query_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation rejects empty query."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": ""},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "empty" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_validate_query_unauthenticated(
        self,
        async_client_no_auth: AsyncClient,
    ):
        """Test validation without authentication."""
        response = await async_client_no_auth.post(
            f"{API_V1_PREFIX}/query/validate",
            params={"query": "SELECT * FROM nodes_method"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_validate_query_sql_injection_attempt(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test validation catches SQL injection attempts."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/query/validate",
            headers=auth_headers,
            params={"query": "SELECT * FROM nodes_method; -- DROP TABLE users"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
