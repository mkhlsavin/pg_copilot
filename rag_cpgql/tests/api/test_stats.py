"""
Tests for Stats Router.

Tests for GET /stats, GET /stats/scenarios, GET /stats/users, GET /stats/performance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient

from src.api.database.models import User, UserRole
from tests.api.conftest import API_V1_PREFIX


class TestGetStatsEndpoint:
    """Tests for GET /stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful stats retrieval."""
        mock_metrics = {
            "total_requests": 1000,
            "active_sessions": 25,
            "active_jobs": 3,
            "cache_hit_rate": 0.75,
            "avg_response_time_ms": 150.5,
            "scenarios_usage": {"security": 100, "onboarding": 50},
        }

        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_system_metrics = AsyncMock(return_value=mock_metrics)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_requests"] == 1000
        assert data["active_sessions"] == 25
        assert data["active_jobs"] == 3
        assert data["cache_hit_rate"] == 0.75
        assert data["avg_response_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_get_stats_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test stats without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/stats")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetScenarioStatsEndpoint:
    """Tests for GET /stats/scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_stats_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful scenario stats retrieval."""
        mock_stats = {
            "scenarios": {
                "security": {"total": 100, "success": 95},
                "onboarding": {"total": 50, "success": 48},
            },
            "total_queries": 150,
            "period": "7d",
        }

        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_scenario_statistics = AsyncMock(return_value=mock_stats)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats/scenarios",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "scenarios" in data
        assert data["total_queries"] == 150
        assert data["period"] == "7d"

    @pytest.mark.asyncio
    async def test_get_scenario_stats_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test scenario stats without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/stats/scenarios")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetUserStatsEndpoint:
    """Tests for GET /stats/users endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_stats_admin_success(
        self,
        async_client: AsyncClient,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test successful user stats retrieval by admin."""
        mock_stats = {
            "total_users": 100,
            "active_users_24h": 25,
            "active_users_7d": 60,
            "new_users_7d": 10,
        }

        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_statistics = AsyncMock(return_value=mock_stats)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats/users",
                headers=admin_auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_users"] == 100
        assert data["active_users_24h"] == 25
        assert data["active_users_7d"] == 60
        assert data["new_users_7d"] == 10

    @pytest.mark.asyncio
    async def test_get_user_stats_non_admin_forbidden(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test user stats access denied for non-admin."""
        response = await async_client.get(
            f"{API_V1_PREFIX}/stats/users",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "admin" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_user_stats_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test user stats without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/stats/users")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetPerformanceStatsEndpoint:
    """Tests for GET /stats/performance endpoint."""

    @pytest.mark.asyncio
    async def test_get_performance_stats_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful performance stats retrieval."""
        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.count_total_turns = AsyncMock(return_value=1000)
            mock_repo.count_turns_period = AsyncMock(return_value=100)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats/performance",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "avg_response_time_ms" in data
        assert "p50_response_time_ms" in data
        assert "p95_response_time_ms" in data
        assert "p99_response_time_ms" in data
        assert "requests_per_minute" in data
        assert "error_rate" in data

    @pytest.mark.asyncio
    async def test_get_performance_stats_calculates_rpm(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that requests_per_minute is calculated from 24h data."""
        turns_24h = 1440  # 1 request per minute

        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.count_total_turns = AsyncMock(return_value=10000)
            mock_repo.count_turns_period = AsyncMock(return_value=turns_24h)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats/performance",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 1440 turns / (24 * 60 minutes) = 1.0 rpm
        assert data["requests_per_minute"] == 1.0

    @pytest.mark.asyncio
    async def test_get_performance_stats_zero_turns(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test performance stats with no turns."""
        with patch("src.api.routers.stats.StatsRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.count_total_turns = AsyncMock(return_value=0)
            mock_repo.count_turns_period = AsyncMock(return_value=0)
            mock_repo_class.return_value = mock_repo

            response = await async_client.get(
                f"{API_V1_PREFIX}/stats/performance",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["requests_per_minute"] == 0.0

    @pytest.mark.asyncio
    async def test_get_performance_stats_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Test performance stats without authentication."""
        response = await async_client.get(f"{API_V1_PREFIX}/stats/performance")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
