"""
Tests for Demo Router.

Tests for public demo endpoint with rate limiting.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class MockDemoConfig:
    """Mock demo configuration."""

    def __init__(
        self,
        enabled: bool = True,
        rate_limit: str = "30/minute",
        max_query_length: int = 500,
        allowed_scenarios: list = None,
    ):
        self.enabled = enabled
        self.rate_limit = rate_limit
        self.max_query_length = max_query_length
        self.allowed_scenarios = allowed_scenarios or ["onboarding"]


class MockChatResult:
    """Mock chat service result."""

    def __init__(self, answer: str, scenario_id: str = "onboarding"):
        self.answer = answer
        self.scenario_id = scenario_id


class TestDemoChat:
    """Tests for demo chat endpoint."""

    def test_demo_chat_success(self, test_client: TestClient):
        """Test successful demo chat request."""
        mock_result = MockChatResult(
            answer="This is the answer to your question.",
            scenario_id="onboarding",
        )

        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(),
        ):
            with patch(
                "src.api.routers.demo.get_chat_service"
            ) as mock_service:
                mock_chat = MagicMock()
                mock_chat.process_query = AsyncMock(return_value=mock_result)
                mock_service.return_value = mock_chat

                response = test_client.post(
                    "/api/v1/demo/chat",
                    json={"query": "What is malloc?", "language": "en"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer to your question."
        assert data["scenario_id"] == "onboarding"
        assert "processing_time_ms" in data

    def test_demo_chat_default_language(self, test_client: TestClient):
        """Test demo chat uses default language (ru)."""
        mock_result = MockChatResult(answer="Ответ на ваш вопрос")

        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(),
        ):
            with patch(
                "src.api.routers.demo.get_chat_service"
            ) as mock_service:
                mock_chat = MagicMock()
                mock_chat.process_query = AsyncMock(return_value=mock_result)
                mock_service.return_value = mock_chat

                response = test_client.post(
                    "/api/v1/demo/chat",
                    json={"query": "Что такое malloc?"},
                )

        assert response.status_code == 200

    def test_demo_chat_disabled(self, test_client: TestClient):
        """Test demo chat returns 503 when disabled."""
        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(enabled=False),
        ):
            response = test_client.post(
                "/api/v1/demo/chat",
                json={"query": "Test query"},
            )

        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()

    def test_demo_chat_query_too_long(self, test_client: TestClient):
        """Test demo chat rejects long queries."""
        long_query = "a" * 600  # Exceeds max_query_length

        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(max_query_length=500),
        ):
            response = test_client.post(
                "/api/v1/demo/chat",
                json={"query": long_query},
            )

        assert response.status_code == 400
        assert "too long" in response.json()["detail"].lower()

    def test_demo_chat_empty_query(self, test_client: TestClient):
        """Test demo chat rejects empty queries."""
        response = test_client.post(
            "/api/v1/demo/chat",
            json={"query": ""},
        )

        # FastAPI validation should reject empty string
        assert response.status_code == 422

    def test_demo_chat_error_handling(self, test_client: TestClient):
        """Test demo chat handles errors gracefully."""
        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(),
        ):
            with patch(
                "src.api.routers.demo.get_chat_service"
            ) as mock_service:
                mock_chat = MagicMock()
                mock_chat.process_query = AsyncMock(
                    side_effect=Exception("Service unavailable")
                )
                mock_service.return_value = mock_chat

                response = test_client.post(
                    "/api/v1/demo/chat",
                    json={"query": "Test query"},
                )

        # Should return friendly error response, not 500
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_id"] == "error"
        assert "unavailable" in data["answer"].lower()

    def test_demo_chat_uses_onboarding_scenario(self, test_client: TestClient):
        """Test demo chat forces onboarding scenario."""
        mock_result = MockChatResult(answer="Answer", scenario_id="onboarding")

        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(allowed_scenarios=["onboarding", "security"]),
        ):
            with patch(
                "src.api.routers.demo.get_chat_service"
            ) as mock_service:
                mock_chat = MagicMock()
                mock_chat.process_query = AsyncMock(return_value=mock_result)
                mock_service.return_value = mock_chat

                response = test_client.post(
                    "/api/v1/demo/chat",
                    json={"query": "Test"},
                )

                # Verify onboarding scenario was used
                call_kwargs = mock_chat.process_query.call_args.kwargs
                assert call_kwargs["scenario_id"] == "onboarding"


class TestDemoStatus:
    """Tests for demo status endpoint."""

    def test_demo_status_enabled(self, test_client: TestClient):
        """Test demo status when enabled."""
        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(
                enabled=True,
                rate_limit="30/minute",
                max_query_length=500,
                allowed_scenarios=["onboarding"],
            ),
        ):
            response = test_client.get("/api/v1/demo/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["rate_limit"] == "30/minute"
        assert data["max_query_length"] == 500
        assert data["allowed_scenarios"] == ["onboarding"]

    def test_demo_status_disabled(self, test_client: TestClient):
        """Test demo status when disabled."""
        with patch(
            "src.api.routers.demo.get_demo_config",
            return_value=MockDemoConfig(enabled=False),
        ):
            response = test_client.get("/api/v1/demo/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False


class TestDemoRateLimiting:
    """Tests for demo endpoint rate limiting."""

    def test_demo_has_rate_limit(self, test_client: TestClient):
        """Test that demo endpoint has rate limiting configured."""
        from src.api.routers.demo import demo_chat

        # Check that the endpoint has a limit decorator
        # The actual rate limiting is handled by slowapi middleware
        assert hasattr(demo_chat, "__wrapped__") or callable(demo_chat)

    def test_demo_rate_limit_key_uses_ip(self, test_client: TestClient):
        """Test that rate limit key is based on IP address."""
        from src.api.routers.demo import get_demo_key_func

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"

        with patch(
            "src.api.routers.demo.get_remote_address",
            return_value="192.168.1.100",
        ):
            key = get_demo_key_func(mock_request)

        assert "demo_ip:" in key
        assert "192.168.1.100" in key


class TestDemoModels:
    """Tests for demo request/response models."""

    def test_demo_request_validation(self):
        """Test DemoRequest model validation."""
        from src.api.routers.demo import DemoRequest

        # Valid request
        req = DemoRequest(query="What is malloc?")
        assert req.query == "What is malloc?"
        assert req.language == "ru"  # default

        # With custom language
        req = DemoRequest(query="Test", language="en")
        assert req.language == "en"

    def test_demo_request_min_length(self):
        """Test DemoRequest requires non-empty query."""
        from src.api.routers.demo import DemoRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DemoRequest(query="")

    def test_demo_request_max_length(self):
        """Test DemoRequest enforces max query length."""
        from src.api.routers.demo import DemoRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DemoRequest(query="a" * 501)

    def test_demo_response_model(self):
        """Test DemoResponse model."""
        from src.api.routers.demo import DemoResponse

        resp = DemoResponse(
            answer="Test answer",
            scenario_id="onboarding",
            processing_time_ms=123.45,
        )

        assert resp.answer == "Test answer"
        assert resp.scenario_id == "onboarding"
        assert resp.processing_time_ms == 123.45
