"""
Tests for Health Check Router.

Tests for health check endpoints, Kubernetes probes, and version info.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for full health check endpoint."""

    def test_health_check_all_healthy(self, test_client: TestClient):
        """Test health check returns healthy when all components are up."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy", "latency_ms": 5.0},
        ):
            with patch(
                "src.api.routers.health.check_llm_health",
                new_callable=AsyncMock,
                return_value={"status": "healthy", "provider": "MockProvider"},
            ):
                with patch(
                    "src.api.routers.health.check_joern_health",
                    new_callable=AsyncMock,
                    return_value={"status": "healthy", "server": "localhost:8080"},
                ):
                    response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data
        assert "components" in data
        assert data["components"]["database"]["status"] == "healthy"

    def test_health_check_database_degraded(self, test_client: TestClient):
        """Test health check returns degraded when database is slow."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "degraded", "latency_ms": 500.0},
        ):
            response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_check_database_unhealthy(self, test_client: TestClient):
        """Test health check returns unhealthy when database is down."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "unhealthy", "error": "Connection refused"},
        ):
            response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_health_check_has_timestamp(self, test_client: TestClient):
        """Test health check includes timestamp."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ):
            response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data

    def test_health_check_has_uptime(self, test_client: TestClient):
        """Test health check includes uptime."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ):
            response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["uptime_seconds"] >= 0


class TestLivenessProbe:
    """Tests for Kubernetes liveness probe endpoint."""

    def test_liveness_probe_returns_ok(self, test_client: TestClient):
        """Test liveness probe returns OK."""
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_liveness_probe_no_dependencies(self, test_client: TestClient):
        """Test liveness probe doesn't check dependencies."""
        # Even if database is down, liveness should return OK
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadinessProbe:
    """Tests for Kubernetes readiness probe endpoint."""

    def test_readiness_probe_ready(self, test_client: TestClient):
        """Test readiness probe returns ready when DB connected."""
        with patch(
            "src.api.routers.health.check_db_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_readiness_probe_not_ready(self, test_client: TestClient):
        """Test readiness probe returns 503 when DB not connected."""
        with patch(
            "src.api.routers.health.check_db_connection",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "reason" in data


class TestVersionEndpoint:
    """Tests for version endpoint."""

    def test_get_version(self, test_client: TestClient):
        """Test version endpoint returns version info."""
        response = test_client.get("/api/v1/health/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "name" in data
        assert data["name"] == "CodeGraph API"

    def test_version_format(self, test_client: TestClient):
        """Test version follows semver format."""
        response = test_client.get("/api/v1/health/version")

        data = response.json()
        version = data["version"]
        # Check basic semver structure (x.y.z)
        parts = version.split(".")
        assert len(parts) >= 2  # At least major.minor


class TestHealthComponents:
    """Tests for component health details."""

    def test_health_includes_llm_component(self, test_client: TestClient):
        """Test health check includes LLM component status."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ):
            response = test_client.get("/api/v1/health")

        data = response.json()
        assert "llm" in data["components"]

    def test_health_includes_joern_component(self, test_client: TestClient):
        """Test health check includes Joern component status."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ):
            response = test_client.get("/api/v1/health")

        data = response.json()
        assert "joern" in data["components"]

    def test_health_includes_database_component(self, test_client: TestClient):
        """Test health check includes database component status."""
        with patch(
            "src.api.routers.health.DatabaseHealthCheck.check",
            new_callable=AsyncMock,
            return_value={"status": "healthy", "latency_ms": 3.5},
        ):
            response = test_client.get("/api/v1/health")

        data = response.json()
        assert "database" in data["components"]
        assert data["components"]["database"]["status"] == "healthy"
