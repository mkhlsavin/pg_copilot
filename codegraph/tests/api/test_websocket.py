"""
Tests for WebSocket components.

Tests for WebSocketManager, message models, and handlers.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        self.sent_messages.append(data)

    async def send_json(self, data: dict):
        self.sent_messages.append(json.dumps(data))

    async def receive_text(self):
        return '{"type": "ping"}'

    async def close(self):
        self.closed = True


class TestWSMessageType:
    """Tests for WSMessageType enum."""

    def test_chat_message_types(self):
        """Test chat-related message types."""
        from src.api.websocket.models import WSMessageType

        assert WSMessageType.CHAT_QUERY.value == "chat.query"
        assert WSMessageType.CHAT_RESPONSE.value == "chat.response"
        assert WSMessageType.CHAT_CHUNK.value == "chat.chunk"
        assert WSMessageType.CHAT_ERROR.value == "chat.error"

    def test_job_message_types(self):
        """Test job-related message types."""
        from src.api.websocket.models import WSMessageType

        assert WSMessageType.JOB_STARTED.value == "job.started"
        assert WSMessageType.JOB_PROGRESS.value == "job.progress"
        assert WSMessageType.JOB_COMPLETED.value == "job.completed"
        assert WSMessageType.JOB_FAILED.value == "job.failed"

    def test_system_message_types(self):
        """Test system message types."""
        from src.api.websocket.models import WSMessageType

        assert WSMessageType.NOTIFICATION.value == "notification"
        assert WSMessageType.ERROR.value == "error"
        assert WSMessageType.PING.value == "ping"
        assert WSMessageType.PONG.value == "pong"

    def test_connection_message_types(self):
        """Test connection message types."""
        from src.api.websocket.models import WSMessageType

        assert WSMessageType.CONNECTED.value == "connected"
        assert WSMessageType.DISCONNECTED.value == "disconnected"
        assert WSMessageType.AUTHENTICATED.value == "authenticated"


class TestWSMessage:
    """Tests for WSMessage model."""

    def test_create_message(self):
        """Test creating a WebSocket message."""
        from src.api.websocket.models import WSMessage, WSMessageType

        message = WSMessage(
            type=WSMessageType.CHAT_QUERY,
            payload={"query": "test query"},
            request_id="req-123",
        )

        assert message.type == WSMessageType.CHAT_QUERY
        assert message.payload["query"] == "test query"
        assert message.request_id == "req-123"
        assert message.timestamp is not None

    def test_message_defaults(self):
        """Test message default values."""
        from src.api.websocket.models import WSMessage, WSMessageType

        message = WSMessage(type=WSMessageType.PING)

        assert message.payload == {}
        assert message.request_id is None

    def test_to_json(self):
        """Test message serialization to JSON."""
        from src.api.websocket.models import WSMessage, WSMessageType

        message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            payload={"title": "Test"},
        )

        json_str = message.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["type"] == "notification"
        assert data["payload"]["title"] == "Test"

    def test_from_json(self):
        """Test message deserialization from JSON."""
        from src.api.websocket.models import WSMessage, WSMessageType

        json_str = '{"type": "ping", "payload": {}, "timestamp": "2024-12-10T10:00:00"}'
        message = WSMessage.from_json(json_str)

        assert message.type == WSMessageType.PING


class TestMessagePayloads:
    """Tests for specific message payload models."""

    def test_chat_query_payload(self):
        """Test ChatQueryPayload model."""
        from src.api.websocket.models import ChatQueryPayload

        payload = ChatQueryPayload(
            query="Find vulnerabilities",
            session_id="sess-123",
            scenario_id="security",
            language="ru",
        )

        assert payload.query == "Find vulnerabilities"
        assert payload.session_id == "sess-123"
        assert payload.scenario_id == "security"
        assert payload.language == "ru"

    def test_chat_query_payload_defaults(self):
        """Test ChatQueryPayload defaults."""
        from src.api.websocket.models import ChatQueryPayload

        payload = ChatQueryPayload(query="Test")

        assert payload.session_id is None
        assert payload.scenario_id is None
        assert payload.language == "en"

    def test_job_progress_payload(self):
        """Test JobProgressPayload model."""
        from src.api.websocket.models import JobProgressPayload

        payload = JobProgressPayload(
            job_id="job-123",
            progress=50,
            message="Processing...",
        )

        assert payload.job_id == "job-123"
        assert payload.progress == 50
        assert payload.message == "Processing..."

    def test_job_progress_validation(self):
        """Test JobProgressPayload validation."""
        from src.api.websocket.models import JobProgressPayload
        from pydantic import ValidationError

        # Valid range 0-100
        JobProgressPayload(job_id="j1", progress=0)
        JobProgressPayload(job_id="j2", progress=100)

        with pytest.raises(ValidationError):
            JobProgressPayload(job_id="j3", progress=-1)

        with pytest.raises(ValidationError):
            JobProgressPayload(job_id="j4", progress=101)

    def test_notification_payload(self):
        """Test NotificationPayload model."""
        from src.api.websocket.models import NotificationPayload

        payload = NotificationPayload(
            title="Alert",
            message="Something happened",
            level="warning",
            action_url="/dashboard",
        )

        assert payload.title == "Alert"
        assert payload.message == "Something happened"
        assert payload.level == "warning"
        assert payload.action_url == "/dashboard"


class TestMessageHelpers:
    """Tests for message helper functions."""

    def test_create_chat_chunk(self):
        """Test create_chat_chunk helper."""
        from src.api.websocket.models import create_chat_chunk, WSMessageType

        message = create_chat_chunk(
            content="Hello, ",
            request_id="req-1",
            is_final=False,
        )

        assert message.type == WSMessageType.CHAT_CHUNK
        assert message.payload["content"] == "Hello, "
        assert message.payload["is_final"] is False
        assert message.request_id == "req-1"

    def test_create_chat_response(self):
        """Test create_chat_response helper."""
        from src.api.websocket.models import create_chat_response, WSMessageType

        message = create_chat_response(
            answer="The vulnerability is in auth.py",
            scenario_id="security",
            confidence=0.95,
            session_id="sess-1",
            request_id="req-2",
        )

        assert message.type == WSMessageType.CHAT_RESPONSE
        assert message.payload["answer"] == "The vulnerability is in auth.py"
        assert message.payload["scenario_id"] == "security"
        assert message.payload["confidence"] == 0.95

    def test_create_job_progress(self):
        """Test create_job_progress helper."""
        from src.api.websocket.models import create_job_progress, WSMessageType

        message = create_job_progress(
            job_id="job-abc",
            progress=75,
            message="Analyzing files...",
        )

        assert message.type == WSMessageType.JOB_PROGRESS
        assert message.payload["job_id"] == "job-abc"
        assert message.payload["progress"] == 75
        assert message.payload["message"] == "Analyzing files..."

    def test_create_job_completed(self):
        """Test create_job_completed helper."""
        from src.api.websocket.models import create_job_completed, WSMessageType

        message = create_job_completed(
            job_id="job-xyz",
            result={"findings": 5, "status": "success"},
        )

        assert message.type == WSMessageType.JOB_COMPLETED
        assert message.payload["job_id"] == "job-xyz"
        assert message.payload["result"]["findings"] == 5

    def test_create_job_failed(self):
        """Test create_job_failed helper."""
        from src.api.websocket.models import create_job_failed, WSMessageType

        message = create_job_failed(
            job_id="job-fail",
            error="Analysis failed",
            details="Out of memory",
        )

        assert message.type == WSMessageType.JOB_FAILED
        assert message.payload["error"] == "Analysis failed"
        assert message.payload["details"] == "Out of memory"

    def test_create_notification(self):
        """Test create_notification helper."""
        from src.api.websocket.models import create_notification, WSMessageType

        message = create_notification(
            title="Success",
            message="Analysis complete",
            level="info",
            action_url="/results",
        )

        assert message.type == WSMessageType.NOTIFICATION
        assert message.payload["title"] == "Success"
        assert message.payload["action_url"] == "/results"

    def test_create_error(self):
        """Test create_error helper."""
        from src.api.websocket.models import create_error, WSMessageType

        message = create_error(
            error="Invalid query",
            details="Query cannot be empty",
            request_id="req-err",
        )

        assert message.type == WSMessageType.ERROR
        assert message.payload["error"] == "Invalid query"
        assert message.payload["details"] == "Query cannot be empty"
        assert message.request_id == "req-err"


class TestWebSocketManager:
    """Tests for WebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Create WebSocketManager for testing."""
        from src.api.websocket.manager import WebSocketManager

        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect(self, manager):
        """Test connecting a WebSocket."""
        websocket = MockWebSocket()

        conn_id = await manager.connect("user-1", websocket)

        assert conn_id.startswith("conn_")
        assert websocket.accepted is True
        assert manager.is_user_connected("user-1")
        assert len(websocket.sent_messages) == 1  # CONNECTED message

    @pytest.mark.asyncio
    async def test_connect_multiple_for_user(self, manager):
        """Test multiple connections for same user."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        conn_id1 = await manager.connect("user-1", ws1)
        conn_id2 = await manager.connect("user-1", ws2)

        assert conn_id1 != conn_id2
        assert manager.get_connection_count("user-1") == 2

    @pytest.mark.asyncio
    async def test_disconnect(self, manager):
        """Test disconnecting a WebSocket."""
        websocket = MockWebSocket()
        conn_id = await manager.connect("user-1", websocket)

        await manager.disconnect("user-1", conn_id)

        assert not manager.is_user_connected("user-1")
        assert manager.get_connection_count("user-1") == 0

    @pytest.mark.asyncio
    async def test_disconnect_one_of_many(self, manager):
        """Test disconnecting one of multiple connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        conn_id1 = await manager.connect("user-1", ws1)
        conn_id2 = await manager.connect("user-1", ws2)

        await manager.disconnect("user-1", conn_id1)

        assert manager.is_user_connected("user-1")
        assert manager.get_connection_count("user-1") == 1

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager):
        """Test sending message to all user connections."""
        from src.api.websocket.models import WSMessage, WSMessageType

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("user-1", ws1)
        await manager.connect("user-1", ws2)

        message = WSMessage(type=WSMessageType.NOTIFICATION, payload={"text": "test"})
        sent_count = await manager.send_to_user("user-1", message)

        assert sent_count == 2
        assert len(ws1.sent_messages) == 2  # CONNECTED + NOTIFICATION
        assert len(ws2.sent_messages) == 2

    @pytest.mark.asyncio
    async def test_send_to_connection(self, manager):
        """Test sending message to specific connection."""
        from src.api.websocket.models import WSMessage, WSMessageType

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        conn_id1 = await manager.connect("user-1", ws1)
        await manager.connect("user-1", ws2)

        message = WSMessage(type=WSMessageType.PING, payload={})
        result = await manager.send_to_connection("user-1", conn_id1, message)

        assert result is True
        assert len(ws1.sent_messages) == 2  # CONNECTED + PING
        assert len(ws2.sent_messages) == 1  # Only CONNECTED

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_connection(self, manager):
        """Test sending to nonexistent connection."""
        from src.api.websocket.models import WSMessage, WSMessageType

        message = WSMessage(type=WSMessageType.PING, payload={})
        result = await manager.send_to_connection("user-x", "conn-x", message)

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all users."""
        from src.api.websocket.models import WSMessage, WSMessageType

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("user-1", ws1)
        await manager.connect("user-2", ws2)

        message = WSMessage(
            type=WSMessageType.NOTIFICATION, payload={"message": "broadcast"}
        )
        sent_count = await manager.broadcast(message)

        assert sent_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_with_exclusion(self, manager):
        """Test broadcasting with user exclusion."""
        from src.api.websocket.models import WSMessage, WSMessageType

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("user-1", ws1)
        await manager.connect("user-2", ws2)

        message = WSMessage(type=WSMessageType.NOTIFICATION, payload={})
        sent_count = await manager.broadcast(message, exclude_users={"user-1"})

        assert sent_count == 1
        assert len(ws2.sent_messages) == 2  # CONNECTED + broadcast

    @pytest.mark.asyncio
    async def test_job_subscription(self, manager):
        """Test job subscription."""
        ws = MockWebSocket()
        await manager.connect("user-1", ws)

        await manager.subscribe_to_job("user-1", "job-123")

        # Job subscription is internal state
        assert "job-123" in manager._job_subscriptions
        assert "user-1" in manager._job_subscriptions["job-123"]

    @pytest.mark.asyncio
    async def test_job_unsubscription(self, manager):
        """Test job unsubscription."""
        ws = MockWebSocket()
        await manager.connect("user-1", ws)

        await manager.subscribe_to_job("user-1", "job-123")
        await manager.unsubscribe_from_job("user-1", "job-123")

        assert "job-123" not in manager._job_subscriptions

    @pytest.mark.asyncio
    async def test_send_job_update(self, manager):
        """Test sending job update to subscribers."""
        from src.api.websocket.models import WSMessage, WSMessageType

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("user-1", ws1)
        await manager.connect("user-2", ws2)

        await manager.subscribe_to_job("user-1", "job-abc")
        # user-2 is not subscribed

        message = WSMessage(
            type=WSMessageType.JOB_PROGRESS,
            payload={"job_id": "job-abc", "progress": 50},
        )
        sent_count = await manager.send_job_update("job-abc", message)

        assert sent_count == 1  # Only user-1 should receive

    @pytest.mark.asyncio
    async def test_cleanup_job_subscriptions(self, manager):
        """Test cleaning up job subscriptions."""
        await manager.subscribe_to_job("user-1", "job-done")
        await manager.subscribe_to_job("user-2", "job-done")

        await manager.cleanup_job_subscriptions("job-done")

        assert "job-done" not in manager._job_subscriptions

    def test_get_connection_count(self, manager):
        """Test getting connection count."""
        assert manager.get_connection_count() == 0
        assert manager.get_connection_count("user-1") == 0

    def test_get_user_count(self, manager):
        """Test getting user count."""
        assert manager.get_user_count() == 0

    @pytest.mark.asyncio
    async def test_user_count_after_connections(self, manager):
        """Test user count with connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect("user-1", ws1)
        await manager.connect("user-1", ws2)
        await manager.connect("user-2", ws3)

        assert manager.get_user_count() == 2
        assert manager.get_connection_count() == 3


class TestGlobalWSManager:
    """Tests for global WebSocket manager."""

    def test_get_ws_manager_singleton(self):
        """Test get_ws_manager returns singleton."""
        from src.api.websocket import manager as ws_module

        # Reset global
        ws_module._ws_manager = None

        mgr1 = ws_module.get_ws_manager()
        mgr2 = ws_module.get_ws_manager()

        assert mgr1 is mgr2


class TestChatHandler:
    """Tests for ChatHandler."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock WebSocket manager."""
        manager = MagicMock()
        manager.send_to_connection = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def handler(self, mock_manager):
        """Create ChatHandler with mock manager."""
        from src.api.websocket.handlers import ChatHandler

        handler = ChatHandler(mock_manager)
        handler.chat_service = MagicMock()
        handler.chat_service.initialize = AsyncMock()
        return handler

    @pytest.mark.asyncio
    async def test_handle_query_empty(self, handler, mock_manager):
        """Test handling empty query."""
        from src.api.websocket.models import WSMessage, WSMessageType

        message = WSMessage(
            type=WSMessageType.CHAT_QUERY,
            payload={"query": ""},
            request_id="req-1",
        )

        await handler.handle_query("user-1", "conn-1", message)

        # Should send error
        mock_manager.send_to_connection.assert_called()
        call_args = mock_manager.send_to_connection.call_args
        assert call_args[0][0] == "user-1"
        assert call_args[0][1] == "conn-1"

    @pytest.mark.asyncio
    async def test_handle_query_with_streaming(self, handler, mock_manager):
        """Test handling query with streaming response."""
        from src.api.websocket.models import WSMessage, WSMessageType

        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "scenario", "scenario_id": "security"}\n\n'
            yield 'data: {"type": "chunk", "content": "Hello"}\n\n'
            yield 'data: {"type": "done"}\n\n'

        handler.chat_service.process_query_stream = mock_stream

        message = WSMessage(
            type=WSMessageType.CHAT_QUERY,
            payload={"query": "Find bugs"},
            request_id="req-stream",
        )

        await handler.handle_query("user-1", "conn-1", message)

        # Should send multiple messages
        assert mock_manager.send_to_connection.call_count >= 3


class TestJobHandler:
    """Tests for JobHandler."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock WebSocket manager."""
        manager = MagicMock()
        manager.subscribe_to_job = AsyncMock()
        manager.unsubscribe_from_job = AsyncMock()
        manager.send_job_update = AsyncMock(return_value=1)
        manager.cleanup_job_subscriptions = AsyncMock()
        manager.send_to_connection = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def handler(self, mock_manager):
        """Create JobHandler with mock manager."""
        from src.api.websocket.handlers import JobHandler

        return JobHandler(mock_manager)

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self, handler, mock_manager):
        """Test job unsubscription."""
        await handler.handle_unsubscribe("user-1", "job-123")

        mock_manager.unsubscribe_from_job.assert_called_once_with("user-1", "job-123")

    @pytest.mark.asyncio
    async def test_send_job_update_progress(self, handler, mock_manager):
        """Test sending job progress update."""
        await handler.send_job_update(
            job_id="job-abc",
            status="running",
            progress=50,
        )

        mock_manager.send_job_update.assert_called_once()
        call_args = mock_manager.send_job_update.call_args
        assert call_args[0][0] == "job-abc"

    @pytest.mark.asyncio
    async def test_send_job_update_completed(self, handler, mock_manager):
        """Test sending job completed update."""
        await handler.send_job_update(
            job_id="job-done",
            status="completed",
            progress=100,
            result={"findings": 10},
        )

        mock_manager.send_job_update.assert_called_once()
        mock_manager.cleanup_job_subscriptions.assert_called_once_with("job-done")

    @pytest.mark.asyncio
    async def test_send_job_update_failed(self, handler, mock_manager):
        """Test sending job failed update."""
        await handler.send_job_update(
            job_id="job-fail",
            status="failed",
            progress=30,
            error="Out of memory",
        )

        mock_manager.cleanup_job_subscriptions.assert_called_once_with("job-fail")


class TestNotificationHandler:
    """Tests for NotificationHandler."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock WebSocket manager."""
        manager = MagicMock()
        manager.send_to_user = AsyncMock(return_value=1)
        manager.broadcast = AsyncMock(return_value=5)
        return manager

    @pytest.fixture
    def handler(self, mock_manager):
        """Create NotificationHandler with mock manager."""
        from src.api.websocket.handlers import NotificationHandler

        return NotificationHandler(mock_manager)

    @pytest.mark.asyncio
    async def test_send_notification(self, handler, mock_manager):
        """Test sending notification to user."""
        result = await handler.send_notification(
            user_id="user-1",
            title="Alert",
            message="Check your code",
            notification_type="warning",
            data={"link": "/code"},
        )

        assert result is True
        mock_manager.send_to_user.assert_called_once()
        call_args = mock_manager.send_to_user.call_args
        assert call_args[0][0] == "user-1"

    @pytest.mark.asyncio
    async def test_send_notification_not_delivered(self, handler, mock_manager):
        """Test notification not delivered."""
        mock_manager.send_to_user = AsyncMock(return_value=0)

        result = await handler.send_notification(
            user_id="offline-user",
            title="Test",
            message="Test",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_notification(self, handler, mock_manager):
        """Test broadcasting notification."""
        count = await handler.broadcast_notification(
            title="System Update",
            message="Maintenance in 1 hour",
            notification_type="info",
        )

        assert count == 5
        mock_manager.broadcast.assert_called_once()
