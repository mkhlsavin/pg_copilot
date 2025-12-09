"""
Tests for Scenarios Router.

Tests for GET /scenarios, GET /scenarios/{id}, POST /scenarios/{id}/query
"""

import pytest

from fastapi import status
from httpx import AsyncClient

from tests.api.conftest import API_V1_PREFIX


class TestListScenariosEndpoint:
    """Tests for GET /scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_list_scenarios_success(
        self,
        async_client: AsyncClient,
    ):
        """Test listing all scenarios."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 16  # 16 predefined scenarios

    @pytest.mark.asyncio
    async def test_list_scenarios_contains_required_fields(
        self,
        async_client: AsyncClient,
    ):
        """Test that each scenario has required fields."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for scenario in data:
            assert "id" in scenario
            assert "name" in scenario
            assert "description" in scenario
            assert "category" in scenario
            assert "keywords" in scenario
            assert "example_queries" in scenario

    @pytest.mark.asyncio
    async def test_list_scenarios_contains_expected_ids(
        self,
        async_client: AsyncClient,
    ):
        """Test that expected scenario IDs are present."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        ids = [s["id"] for s in data]

        expected_ids = [
            "onboarding",
            "security",
            "documentation",
            "feature_dev",
            "refactoring",
            "performance",
            "test_coverage",
            "compliance",
            "code_review",
            "cross_repo",
            "architecture",
            "tech_debt",
            "mass_refactoring",
            "security_incident",
            "debugging",
            "entry_points",
        ]

        for expected_id in expected_ids:
            assert expected_id in ids, f"Missing scenario: {expected_id}"

    @pytest.mark.asyncio
    async def test_list_scenarios_categories(
        self,
        async_client: AsyncClient,
    ):
        """Test that scenarios have valid categories."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        valid_categories = [
            "Learning",
            "Security",
            "Documentation",
            "Development",
            "Quality",
            "Performance",
            "Testing",
            "Review",
            "Architecture",
        ]

        for scenario in data:
            assert scenario["category"] in valid_categories, (
                f"Invalid category '{scenario['category']}' for {scenario['id']}"
            )


class TestGetScenarioEndpoint:
    """Tests for GET /scenarios/{scenario_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_success(
        self,
        async_client: AsyncClient,
    ):
        """Test getting a specific scenario."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios/security")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "security"
        assert data["name"] == "Security Audit"
        assert "vulnerability" in data["keywords"]

    @pytest.mark.asyncio
    async def test_get_scenario_onboarding(
        self,
        async_client: AsyncClient,
    ):
        """Test getting onboarding scenario."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios/onboarding")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "onboarding"
        assert data["category"] == "Learning"
        assert len(data["example_queries"]) > 0

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test getting non-existent scenario."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_scenario_debugging(
        self,
        async_client: AsyncClient,
    ):
        """Test getting debugging scenario."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios/debugging")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "debugging"
        assert "debug" in data["keywords"]
        assert "elog" in data["keywords"]


class TestQueryScenarioEndpoint:
    """Tests for POST /scenarios/{scenario_id}/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_scenario_success(
        self,
        async_client: AsyncClient,
    ):
        """Test querying a scenario."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/security/query",
            json={
                "query": "Find SQL injection vulnerabilities",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["scenario_id"] == "security"
        assert "answer" in data
        assert "confidence" in data
        assert "session_id" in data
        assert "request_id" in data
        assert "processing_time_ms" in data

    @pytest.mark.asyncio
    async def test_query_scenario_with_session(
        self,
        async_client: AsyncClient,
    ):
        """Test querying a scenario with existing session."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/onboarding/query",
            json={
                "query": "Where is the main function?",
                "session_id": "existing-session-123",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "existing-session-123"

    @pytest.mark.asyncio
    async def test_query_scenario_russian(
        self,
        async_client: AsyncClient,
    ):
        """Test querying a scenario in Russian."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/security/query",
            json={
                "query": "Find vulnerabilities",
                "language": "ru",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["scenario_id"] == "security"

    @pytest.mark.asyncio
    async def test_query_scenario_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test querying non-existent scenario."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/nonexistent/query",
            json={
                "query": "Test query",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_query_scenario_empty_query(
        self,
        async_client: AsyncClient,
    ):
        """Test querying with empty query string."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/security/query",
            json={
                "query": "",
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_query_scenario_invalid_language(
        self,
        async_client: AsyncClient,
    ):
        """Test querying with invalid language code."""
        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/security/query",
            json={
                "query": "Test query",
                "language": "de",  # Invalid - only en and ru allowed
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_query_scenario_query_too_long(
        self,
        async_client: AsyncClient,
    ):
        """Test querying with query exceeding max length."""
        long_query = "a" * 10001  # max_length is 10000

        response = await async_client.post(
            f"{API_V1_PREFIX}/scenarios/security/query",
            json={
                "query": long_query,
                "language": "en",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestScenarioData:
    """Tests for scenario data integrity."""

    @pytest.mark.asyncio
    async def test_all_scenarios_have_examples(
        self,
        async_client: AsyncClient,
    ):
        """Test that all scenarios have example queries."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for scenario in data:
            assert len(scenario["example_queries"]) > 0, (
                f"Scenario '{scenario['id']}' has no example queries"
            )

    @pytest.mark.asyncio
    async def test_all_scenarios_have_keywords(
        self,
        async_client: AsyncClient,
    ):
        """Test that all scenarios have keywords."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for scenario in data:
            assert len(scenario["keywords"]) > 0, (
                f"Scenario '{scenario['id']}' has no keywords"
            )

    @pytest.mark.asyncio
    async def test_security_scenarios_exist(
        self,
        async_client: AsyncClient,
    ):
        """Test that security-related scenarios exist."""
        response = await async_client.get(f"{API_V1_PREFIX}/scenarios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        security_scenarios = [s for s in data if s["category"] == "Security"]
        assert len(security_scenarios) >= 3  # security, security_incident, entry_points

        security_ids = [s["id"] for s in security_scenarios]
        assert "security" in security_ids
        assert "security_incident" in security_ids
        assert "entry_points" in security_ids
