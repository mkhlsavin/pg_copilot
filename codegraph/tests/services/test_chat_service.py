"""
Tests for Chat Service.

Tests for ChatService, ChatResponse, Evidence, and related functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time


class MockCopilot:
    """Mock MultiScenarioCopilot for testing."""

    def __init__(self, response: dict = None):
        self.default_response = response or {
            "answer": "Test answer from copilot",
            "confidence": 0.95,
            "scenario_id": "security",
            "cpg_results": [
                {"code": "def test():", "filename": "test.py", "line": 10}
            ],
            "methods": [
                {"name": "authenticate", "filename": "auth.py", "line": 25}
            ],
        }

    def run(self, query: str, context: dict = None) -> dict:
        return self.default_response


class MockIntentClassifier:
    """Mock IntentClassifier for testing."""

    def __init__(self, scenario_id: str = "security", confidence: float = 0.9):
        self.scenario_id = scenario_id
        self.confidence = confidence

    def classify(self, query: str):
        result = MagicMock()
        result.scenario_id = self.scenario_id
        result.confidence = self.confidence
        return result


class TestEvidence:
    """Tests for Evidence model."""

    def test_evidence_creation(self):
        """Test creating Evidence instance."""
        from src.api.services.chat_service import Evidence

        evidence = Evidence(
            type="code",
            content="def test(): pass",
            file_path="test.py",
            line_number=10,
            confidence=0.95,
        )

        assert evidence.type == "code"
        assert evidence.content == "def test(): pass"
        assert evidence.file_path == "test.py"
        assert evidence.line_number == 10
        assert evidence.confidence == 0.95

    def test_evidence_defaults(self):
        """Test Evidence default values."""
        from src.api.services.chat_service import Evidence

        evidence = Evidence(type="method", content="test_method")

        assert evidence.file_path is None
        assert evidence.line_number is None
        assert evidence.confidence == 1.0


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_response_creation(self):
        """Test creating ChatResponse."""
        from src.api.services.chat_service import ChatResponse, Evidence

        response = ChatResponse(
            answer="Test answer",
            scenario_id="security",
            confidence=0.9,
            evidence=[
                Evidence(type="code", content="test")
            ],
            session_id="sess-123",
            request_id="req-456",
            processing_time_ms=150.5,
            metadata={"key": "value"},
        )

        assert response.answer == "Test answer"
        assert response.scenario_id == "security"
        assert response.confidence == 0.9
        assert len(response.evidence) == 1
        assert response.session_id == "sess-123"
        assert response.request_id == "req-456"
        assert response.processing_time_ms == 150.5
        assert response.metadata["key"] == "value"

    def test_response_defaults(self):
        """Test ChatResponse default values."""
        from src.api.services.chat_service import ChatResponse

        response = ChatResponse(
            answer="Answer",
            scenario_id="test",
            confidence=0.5,
            request_id="req-1",
            processing_time_ms=100.0,
        )

        assert response.evidence == []
        assert response.session_id is None
        assert response.metadata == {}


class TestChatServiceInit:
    """Tests for ChatService initialization."""

    def test_service_creation(self):
        """Test creating ChatService."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        assert service._copilot is None
        assert service._intent_classifier is None

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        with patch(
            "src.workflow.multi_scenario_workflow.MultiScenarioCopilot"
        ) as mock_copilot_class:
            with patch(
                "src.intent.intent_classifier.IntentClassifier"
            ) as mock_classifier_class:
                mock_copilot_class.return_value = MagicMock()
                mock_classifier_class.return_value = MagicMock()

                await service.initialize()

                assert service._copilot is not None
                assert service._intent_classifier is not None
                mock_copilot_class.assert_called_once()
                mock_classifier_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_copilot_failure(self):
        """Test initialization when copilot fails."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        with patch(
            "src.workflow.multi_scenario_workflow.MultiScenarioCopilot"
        ) as mock_copilot_class:
            mock_copilot_class.side_effect = Exception("Copilot init failed")

            with pytest.raises(Exception, match="Copilot init failed"):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        with patch(
            "src.workflow.multi_scenario_workflow.MultiScenarioCopilot"
        ) as mock_copilot_class:
            with patch(
                "src.intent.intent_classifier.IntentClassifier"
            ) as mock_classifier_class:
                mock_copilot = MagicMock()
                mock_copilot_class.return_value = mock_copilot
                mock_classifier_class.return_value = MagicMock()

                await service.initialize()
                await service.initialize()  # Second call

                # Should only be created once
                assert mock_copilot_class.call_count == 1


class TestChatServiceProcessQuery:
    """Tests for ChatService.process_query method."""

    @pytest.fixture
    def service(self):
        """Create ChatService with mocked dependencies."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        service._copilot = MockCopilot()
        service._intent_classifier = MockIntentClassifier()
        return service

    @pytest.mark.asyncio
    async def test_process_query_basic(self, service):
        """Test basic query processing."""
        response = await service.process_query(
            query="Find security vulnerabilities",
            user_id="user-1",
        )

        assert response.answer == "Test answer from copilot"
        assert response.scenario_id == "security"
        assert response.confidence == 0.9
        assert response.processing_time_ms > 0
        assert "user-1" in response.request_id

    @pytest.mark.asyncio
    async def test_process_query_with_session(self, service):
        """Test query processing with session ID."""
        response = await service.process_query(
            query="Test query",
            session_id="sess-123",
            user_id="user-1",
        )

        assert response.session_id == "sess-123"

    @pytest.mark.asyncio
    async def test_process_query_specific_scenario(self, service):
        """Test query processing with specific scenario."""
        response = await service.process_query(
            query="Test query",
            scenario_id="performance",
            user_id="user-1",
        )

        # When scenario is specified, confidence should be 1.0
        assert response.confidence == 1.0

    @pytest.mark.asyncio
    async def test_process_query_with_context(self, service):
        """Test query processing with dialogue context."""
        context = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        response = await service.process_query(
            query="Follow-up question",
            context=context,
            user_id="user-1",
        )

        assert response.answer is not None

    @pytest.mark.asyncio
    async def test_process_query_error_handling(self):
        """Test query processing error handling."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        service._copilot = MagicMock()
        service._copilot.run.side_effect = Exception("Processing error")
        service._intent_classifier = None

        response = await service.process_query(
            query="Test query",
            scenario_id="security",
            user_id="user-1",
        )

        # When copilot.run fails, _process_with_copilot returns fallback response
        assert "unavailable" in response.answer.lower()
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_process_query_without_classifier(self):
        """Test query processing without intent classifier."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        service._copilot = MockCopilot()
        service._intent_classifier = None  # No classifier

        response = await service.process_query(
            query="Test query",
            user_id="user-1",
        )

        assert response.scenario_id == "general_qa"  # Falls back to default
        assert response.confidence == 1.0


class TestChatServiceFallback:
    """Tests for ChatService fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_response_no_copilot(self):
        """Test fallback when copilot is unavailable."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        # Mock initialize to prevent actual copilot creation
        async def mock_initialize():
            service._copilot = None  # Simulate copilot unavailable
            service._intent_classifier = None

        service.initialize = mock_initialize

        response = await service.process_query(
            query="Test query",
            scenario_id="security",
            user_id="user-1",
        )

        assert "unavailable" in response.answer.lower()
        assert response.metadata.get("fallback") is True

    def test_generate_fallback_response(self):
        """Test fallback response generation."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        result = service._generate_fallback_response("Test query")

        assert "unavailable" in result["answer"].lower()
        assert result["evidence"] == []
        assert result["metadata"]["fallback"] is True


class TestChatServiceEvidenceConversion:
    """Tests for evidence conversion."""

    def test_convert_evidence_from_cpg_results(self):
        """Test converting CPG results to evidence."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        result = {
            "cpg_results": [
                {"code": "def test():", "filename": "test.py", "line": 10},
                {"code": "class Foo:", "filename": "foo.py", "line": 20},
            ],
            "methods": [],
        }

        evidence = service._convert_evidence(result)

        assert len(evidence) == 2
        assert evidence[0]["type"] == "code"
        assert evidence[0]["content"] == "def test():"
        assert evidence[0]["file_path"] == "test.py"
        assert evidence[0]["line_number"] == 10

    def test_convert_evidence_from_methods(self):
        """Test converting methods to evidence."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        result = {
            "cpg_results": [],
            "methods": [
                {"name": "authenticate", "filename": "auth.py", "line": 25},
            ],
        }

        evidence = service._convert_evidence(result)

        assert len(evidence) == 1
        assert evidence[0]["type"] == "method"
        assert evidence[0]["content"] == "authenticate"
        assert evidence[0]["confidence"] == 0.9

    def test_convert_evidence_limit(self):
        """Test evidence conversion respects limits."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        result = {
            "cpg_results": [
                {"code": f"code_{i}", "filename": f"file_{i}.py", "line": i}
                for i in range(20)  # More than limit
            ],
            "methods": [
                {"name": f"method_{i}", "filename": f"file_{i}.py", "line": i}
                for i in range(10)  # More than limit
            ],
        }

        evidence = service._convert_evidence(result)

        # 10 from cpg_results + 5 from methods = 15
        assert len(evidence) == 15

    def test_convert_evidence_empty_results(self):
        """Test evidence conversion with empty results."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        result = {}

        evidence = service._convert_evidence(result)

        assert evidence == []


class TestChatServiceScenarios:
    """Tests for scenario-related methods."""

    def test_get_available_scenarios_returns_empty_when_scenarios_unavailable(self):
        """Test get_available_scenarios returns empty list when SCENARIOS doesn't exist.

        Note: The current codebase doesn't define SCENARIOS, so this method returns [].
        """
        from src.api.services.chat_service import ChatService

        service = ChatService()
        scenarios = service.get_available_scenarios()

        # SCENARIOS doesn't exist in codebase, so returns empty list
        assert scenarios == []

    def test_get_scenario_info_returns_none_when_scenarios_unavailable(self):
        """Test get_scenario_info returns None when SCENARIOS doesn't exist.

        Note: The current codebase doesn't define SCENARIOS, so this method returns None.
        """
        from src.api.services.chat_service import ChatService

        service = ChatService()
        info = service.get_scenario_info("security")

        # SCENARIOS doesn't exist in codebase, so returns None
        assert info is None


class TestChatServiceStreaming:
    """Tests for streaming response."""

    @pytest.fixture
    def service(self):
        """Create ChatService with mocked dependencies."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        service._copilot = MockCopilot()
        service._intent_classifier = MockIntentClassifier()
        return service

    @pytest.mark.asyncio
    async def test_stream_yields_scenario_first(self, service):
        """Test streaming yields scenario info first."""
        chunks = []
        async for chunk in service.process_query_stream(
            query="Test query",
            user_id="user-1",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "scenario" in chunks[0]

    @pytest.mark.asyncio
    async def test_stream_yields_done_last(self, service):
        """Test streaming yields done at end."""
        chunks = []
        async for chunk in service.process_query_stream(
            query="Test query",
            user_id="user-1",
        ):
            chunks.append(chunk)

        assert "done" in chunks[-1]

    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Test streaming error handling."""
        from src.api.services.chat_service import ChatService

        service = ChatService()
        service._copilot = MagicMock()

        # Make _process_with_copilot raise error
        async def mock_process(*args, **kwargs):
            raise Exception("Stream error")

        service._process_with_copilot = mock_process
        service._intent_classifier = None

        chunks = []
        async for chunk in service.process_query_stream(
            query="Test query",
            scenario_id="security",
            user_id="user-1",
        ):
            chunks.append(chunk)

        # Should contain error message
        assert any("error" in chunk for chunk in chunks)


class TestGlobalChatService:
    """Tests for global chat service instance."""

    def test_get_chat_service_creates_instance(self):
        """Test get_chat_service creates instance."""
        from src.api.services import chat_service as chat_module

        # Reset global
        chat_module._chat_service = None

        service = chat_module.get_chat_service()

        assert service is not None
        assert isinstance(service, chat_module.ChatService)

    def test_get_chat_service_returns_same_instance(self):
        """Test get_chat_service returns singleton."""
        from src.api.services import chat_service as chat_module

        # Reset global
        chat_module._chat_service = None

        service1 = chat_module.get_chat_service()
        service2 = chat_module.get_chat_service()

        assert service1 is service2


class TestChatServiceIntegration:
    """Integration-style tests for ChatService."""

    @pytest.mark.asyncio
    async def test_full_query_flow(self):
        """Test complete query processing flow."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        # Setup mocks
        mock_copilot = MagicMock()
        mock_copilot.run.return_value = {
            "answer": "The code has potential SQL injection in user_input handling.",
            "confidence": 0.85,
            "scenario_id": "security",
            "cpg_results": [
                {
                    "code": 'cursor.execute(f"SELECT * FROM users WHERE id={user_input}")',
                    "filename": "db.py",
                    "line": 42,
                }
            ],
            "methods": [],
        }

        mock_classifier = MagicMock()
        classification = MagicMock()
        classification.scenario_id = "security"
        classification.confidence = 0.92
        mock_classifier.classify.return_value = classification

        service._copilot = mock_copilot
        service._intent_classifier = mock_classifier

        response = await service.process_query(
            query="Find SQL injection vulnerabilities",
            session_id="integration-test-session",
            user_id="test-user",
            language="en",
        )

        assert "SQL injection" in response.answer
        assert response.scenario_id == "security"
        assert response.confidence == 0.92
        assert len(response.evidence) == 1
        assert response.evidence[0].type == "code"
        assert "db.py" in response.evidence[0].file_path
        assert response.session_id == "integration-test-session"
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_query_with_history(self):
        """Test query processing with conversation history."""
        from src.api.services.chat_service import ChatService

        service = ChatService()

        mock_copilot = MagicMock()
        mock_copilot.run.return_value = {
            "answer": "Yes, the authenticate function also has issues.",
            "confidence": 0.88,
        }
        service._copilot = mock_copilot
        service._intent_classifier = None

        context = [
            {"role": "user", "content": "Check login.py for vulnerabilities"},
            {"role": "assistant", "content": "Found XSS in render_template"},
            {"role": "user", "content": "What about the authenticate function?"},
        ]

        response = await service.process_query(
            query="Tell me more about authenticate",
            scenario_id="security",
            context=context,
            user_id="test-user",
        )

        # Verify copilot was called with context
        call_args = mock_copilot.run.call_args
        assert call_args is not None
        context_dict = call_args[0][1]  # Second positional arg
        assert "history" in context_dict
        assert len(context_dict["history"]) <= 5  # Limited to last 5
