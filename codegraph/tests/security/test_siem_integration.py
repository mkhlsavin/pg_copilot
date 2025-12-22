"""
Tests for SIEM Integration components.

Tests for SecurityEvent, handlers (SysLog, CEF, LEEF), buffer, and dispatcher.
"""

import pytest
import socket
import time
from unittest.mock import MagicMock, patch, call
from datetime import datetime


class MockSysLogConfig:
    """Mock SysLog configuration."""
    enabled = True
    host = "localhost"
    port = 514
    protocol = "udp"
    facility = 16  # local0
    app_name = "codegraph"
    hostname = "testhost"


class MockCEFConfig:
    """Mock CEF configuration."""
    enabled = True
    host = "localhost"
    port = 514
    protocol = "udp"
    device_vendor = "TestVendor"
    device_product = "TestProduct"
    device_version = "1.0"


class MockLEEFConfig:
    """Mock LEEF configuration."""
    enabled = True
    host = "localhost"
    port = 514
    protocol = "udp"
    product_name = "CodeGraph"
    product_version = "1.0"


class MockBufferConfig:
    """Mock buffer configuration."""
    max_size = 1000
    flush_interval_seconds = 5.0
    retry_attempts = 3
    retry_backoff_seconds = 2.0


class MockSIEMConfig:
    """Mock SIEM configuration."""

    def __init__(
        self,
        enabled: bool = True,
        syslog_enabled: bool = True,
        cef_enabled: bool = False,
        leef_enabled: bool = False,
    ):
        self.enabled = enabled
        self.syslog = MockSysLogConfig()
        self.syslog.enabled = syslog_enabled
        self.cef = MockCEFConfig()
        self.cef.enabled = cef_enabled
        self.leef = MockLEEFConfig()
        self.leef.enabled = leef_enabled
        self.buffer = MockBufferConfig()


class TestSecurityEvent:
    """Tests for SecurityEvent dataclass."""

    def test_create_event(self):
        """Test creating a security event."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test LLM request",
            request_id="req-123",
            severity=6,
            user_id="user-456",
            ip_address="192.168.1.1",
        )

        assert event.event_type == SecurityEventType.LLM_REQUEST
        assert event.message == "Test LLM request"
        assert event.request_id == "req-123"
        assert event.severity == 6
        assert event.user_id == "user-456"
        assert event.ip_address == "192.168.1.1"
        assert event.timestamp.endswith("Z")

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent(
            event_type=SecurityEventType.DLP_BLOCK,
            timestamp="2024-12-09T10:30:00.000Z",
            request_id="req-789",
            message="DLP blocked content",
            severity=3,
            user_id="user-123",
            dlp_category="credentials",
            dlp_pattern="api_key",
        )

        result = event.to_dict()

        assert result["event_type"] == "dlp.block"
        assert result["timestamp"] == "2024-12-09T10:30:00.000Z"
        assert result["request_id"] == "req-789"
        assert result["message"] == "DLP blocked content"
        assert result["severity"] == 3
        assert result["user_id"] == "user-123"
        assert result["dlp_category"] == "credentials"
        assert result["dlp_pattern"] == "api_key"

    def test_event_optional_fields(self):
        """Test that optional fields are excluded when None."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent(
            event_type=SecurityEventType.LLM_REQUEST,
            timestamp="2024-12-09T10:30:00.000Z",
            request_id="req-001",
            message="Basic event",
            severity=6,
        )

        result = event.to_dict()

        assert "user_id" not in result
        assert "ip_address" not in result
        assert "provider" not in result
        assert "model" not in result

    def test_event_with_details(self):
        """Test event with additional details."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.SECURITY_ALERT,
            message="Custom alert",
            request_id="req-alert",
            severity=2,
            details={"custom_key": "custom_value", "count": 42},
        )

        result = event.to_dict()

        assert result["details"]["custom_key"] == "custom_value"
        assert result["details"]["count"] == 42


class TestSecurityEventTypes:
    """Tests for SecurityEventType enum."""

    def test_all_event_types_exist(self):
        """Test that all expected event types exist."""
        from src.security.siem.base_handler import SecurityEventType

        expected_types = [
            "LLM_REQUEST",
            "LLM_RESPONSE",
            "LLM_ERROR",
            "DLP_BLOCK",
            "DLP_MASK",
            "DLP_WARN",
            "DLP_LOG",
            "VAULT_ACCESS",
            "VAULT_ROTATE",
            "AUTH_SUCCESS",
            "AUTH_FAILURE",
            "RATE_LIMIT",
            "SECURITY_ALERT",
        ]

        for event_type in expected_types:
            assert hasattr(SecurityEventType, event_type)

    def test_event_type_values(self):
        """Test that event types have correct string values."""
        from src.security.siem.base_handler import SecurityEventType

        assert SecurityEventType.LLM_REQUEST.value == "llm.request"
        assert SecurityEventType.DLP_BLOCK.value == "dlp.block"
        assert SecurityEventType.AUTH_SUCCESS.value == "auth.success"


class TestSysLogHandler:
    """Tests for SysLog handler."""

    @pytest.fixture
    def handler(self):
        """Create SysLog handler for testing."""
        from src.security.siem.syslog_handler import SysLogHandler

        return SysLogHandler(MockSysLogConfig())

    def test_handler_initialization(self, handler):
        """Test handler initializes correctly."""
        assert handler.host == "localhost"
        assert handler.port == 514
        assert handler.protocol == "udp"
        assert handler.facility == 16
        assert handler.app_name == "codegraph"

    def test_calculate_priority(self, handler):
        """Test priority calculation."""
        # facility 16 (local0) * 8 + severity
        assert handler._calculate_priority(0) == 128  # emergency
        assert handler._calculate_priority(3) == 131  # error
        assert handler._calculate_priority(6) == 134  # info
        assert handler._calculate_priority(7) == 135  # debug

    def test_format_timestamp(self, handler):
        """Test timestamp formatting."""
        result = handler._format_timestamp("2024-12-09T10:30:00.000Z")

        assert "2024-12-09T10:30:00" in result
        assert result.endswith("Z")

    def test_generate_msgid(self, handler):
        """Test message ID generation."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test",
            request_id="req-1",
        )

        msgid = handler._generate_msgid(event)
        assert msgid == "LLM001"

    def test_format_event(self, handler):
        """Test full event formatting."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.DLP_BLOCK,
            message="Credential detected",
            request_id="req-dlp-1",
            severity=3,
            user_id="user-123",
            ip_address="192.168.1.1",
            dlp_category="credentials",
        )

        result = handler.format_event(event)

        # Check syslog format components
        assert "<131>" in result  # PRI (16*8+3)
        assert "testhost" in result  # hostname
        assert "codegraph" in result  # app name
        assert "DLP001" in result  # message ID
        assert "Credential detected" in result  # message
        assert 'request_id="req-dlp-1"' in result  # structured data

    def test_format_structured_data(self, handler):
        """Test structured data formatting."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_RESPONSE,
            message="Response logged",
            request_id="req-llm",
            provider="gigachat",
            model="GigaChat-Pro",
            tokens_used=500,
            latency_ms=150.5,
        )

        sd = handler._format_structured_data(event)

        assert "meta@47450" in sd
        assert 'request_id="req-llm"' in sd
        assert 'provider="gigachat"' in sd
        assert 'model="GigaChat-Pro"' in sd
        assert 'tokens="500"' in sd
        assert "latency_ms=" in sd

    @patch("socket.socket")
    def test_send_udp(self, mock_socket_class, handler):
        """Test UDP sending."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test message",
            request_id="req-test",
        )

        result = handler.send(event)

        assert result is True
        mock_socket.sendto.assert_called_once()
        mock_socket.close.assert_called_once()


class TestCEFHandler:
    """Tests for CEF handler."""

    @pytest.fixture
    def handler(self):
        """Create CEF handler for testing."""
        from src.security.siem.cef_handler import CEFHandler

        return CEFHandler(MockCEFConfig())

    def test_handler_initialization(self, handler):
        """Test handler initializes correctly."""
        assert handler.host == "localhost"
        assert handler.port == 514
        assert handler.device_vendor == "TestVendor"
        assert handler.device_product == "TestProduct"
        assert handler.device_version == "1.0"

    def test_escape_cef_value(self, handler):
        """Test CEF value escaping."""
        # Pipe, backslash, equals must be escaped
        assert handler._escape_cef_value("test|value") == "test\\|value"
        assert handler._escape_cef_value("test\\value") == "test\\\\value"
        assert handler._escape_cef_value("test=value") == "test\\=value"
        assert handler._escape_cef_value("") == ""

    def test_escape_extension_value(self, handler):
        """Test CEF extension value escaping."""
        # Backslash, equals, newlines must be escaped
        assert handler._escape_extension_value("test=value") == "test\\=value"
        assert handler._escape_extension_value("line1\nline2") == "line1\\nline2"
        assert handler._escape_extension_value("line1\rline2") == "line1\\rline2"

    def test_map_severity(self, handler):
        """Test severity mapping from syslog to CEF."""
        assert handler._map_severity(0) == 10  # emergency
        assert handler._map_severity(2) == 8  # critical
        assert handler._map_severity(4) == 6  # warning
        assert handler._map_severity(6) == 3  # info
        assert handler._map_severity(7) == 1  # debug

    def test_get_signature(self, handler):
        """Test signature lookup."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.DLP_BLOCK,
            message="Test",
            request_id="req-1",
        )

        sig_id, name = handler._get_signature(event)

        assert sig_id == "DLP001"
        assert name == "DLP Block"

    def test_format_event(self, handler):
        """Test full CEF event formatting."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="LLM request logged",
            request_id="req-cef-1",
            severity=6,
            user_id="user-abc",
            ip_address="10.0.0.1",
            provider="openai",
            model="gpt-4",
            tokens_used=1000,
        )

        result = handler.format_event(event)

        # Check CEF format
        assert result.startswith("CEF:0|")
        assert "TestVendor" in result
        assert "TestProduct" in result
        assert "LLM001" in result  # signature ID
        assert "LLM Request" in result  # name
        assert "|3|" in result  # severity (info = 3)
        assert "src=10.0.0.1" in result
        assert "suser=user-abc" in result
        assert "cn1=1000" in result  # tokens

    def test_build_extension(self, handler):
        """Test CEF extension building."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.DLP_MASK,
            message="Content masked",
            request_id="req-ext",
            ip_address="192.168.1.100",
            user_id="admin",
            dlp_category="pii",
            dlp_pattern="email_address",
            latency_ms=50.5,
        )

        ext = handler._build_extension(event)

        assert "src=192.168.1.100" in ext
        assert "suser=admin" in ext
        assert "cs4=pii" in ext
        assert "cs4Label=DLP Category" in ext
        assert "cs5=email_address" in ext
        assert "cn2=50" in ext  # latency as int


class TestSIEMBuffer:
    """Tests for SIEM buffer."""

    @pytest.fixture
    def mock_send_func(self):
        """Create mock send function."""
        return MagicMock(return_value=True)

    @pytest.fixture
    def buffer(self, mock_send_func):
        """Create SIEM buffer for testing."""
        from src.security.siem.buffer import SIEMBuffer

        return SIEMBuffer(
            send_func=mock_send_func,
            max_size=100,
            flush_interval=1.0,
            max_retries=3,
        )

    def test_buffer_initialization(self, buffer):
        """Test buffer initializes correctly."""
        assert buffer._max_size == 100
        assert buffer._flush_interval == 1.0
        assert buffer._max_retries == 3
        assert buffer._running is False

    def test_enqueue_event(self, buffer):
        """Test enqueueing events."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test",
            request_id="req-1",
        )

        result = buffer.enqueue(event)

        assert result is True
        assert buffer.size == 1
        assert buffer.stats["enqueued"] == 1

    def test_enqueue_multiple_events(self, buffer):
        """Test enqueueing multiple events."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        for i in range(10):
            event = SecurityEvent.create(
                event_type=SecurityEventType.LLM_REQUEST,
                message=f"Test {i}",
                request_id=f"req-{i}",
            )
            buffer.enqueue(event)

        assert buffer.size == 10
        assert buffer.stats["enqueued"] == 10

    def test_flush_sends_events(self, buffer, mock_send_func):
        """Test flush sends all events."""
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        for i in range(5):
            event = SecurityEvent.create(
                event_type=SecurityEventType.LLM_REQUEST,
                message=f"Test {i}",
                request_id=f"req-{i}",
            )
            buffer.enqueue(event)

        sent = buffer.flush()

        assert sent == 5
        assert mock_send_func.call_count == 5
        assert buffer.size == 0
        assert buffer.stats["sent"] == 5

    def test_flush_handles_failures(self, mock_send_func):
        """Test flush handles send failures with retry."""
        from src.security.siem.buffer import SIEMBuffer
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        # First call fails, second succeeds
        mock_send_func.side_effect = [False, True]

        buffer = SIEMBuffer(
            send_func=mock_send_func,
            max_size=100,
            flush_interval=1.0,
            max_retries=3,
        )

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test",
            request_id="req-retry",
        )
        buffer.enqueue(event)

        # First flush - fails, goes to retry
        buffer.flush()
        assert buffer.stats["retried"] == 1

        # Second flush - succeeds
        mock_send_func.side_effect = None
        mock_send_func.return_value = True
        buffer.flush()

    def test_buffer_overflow_drops_oldest(self, mock_send_func):
        """Test buffer overflow drops oldest messages."""
        from src.security.siem.buffer import SIEMBuffer
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        buffer = SIEMBuffer(
            send_func=mock_send_func,
            max_size=5,
            flush_interval=1.0,
        )

        # Enqueue more than max_size
        for i in range(10):
            event = SecurityEvent.create(
                event_type=SecurityEventType.LLM_REQUEST,
                message=f"Test {i}",
                request_id=f"req-{i}",
            )
            buffer.enqueue(event)

        assert buffer.stats["dropped"] == 5  # 10 - 5 = 5 dropped
        assert buffer.size == 5

    def test_start_stop_buffer(self, buffer):
        """Test starting and stopping buffer."""
        buffer.start()
        assert buffer._running is True
        assert buffer._flush_thread is not None

        buffer.stop(timeout=2.0)
        assert buffer._running is False

    def test_context_manager(self, mock_send_func):
        """Test buffer as context manager."""
        from src.security.siem.buffer import SIEMBuffer

        with SIEMBuffer(send_func=mock_send_func) as buffer:
            assert buffer._running is True

        assert buffer._running is False


class TestSIEMDispatcher:
    """Tests for SIEM dispatcher."""

    def test_dispatcher_disabled(self):
        """Test dispatcher when disabled."""
        from src.security.siem.dispatcher import SIEMDispatcher

        config = MockSIEMConfig(enabled=False)
        dispatcher = SIEMDispatcher(config)

        assert dispatcher.is_enabled is False
        assert dispatcher.handler_count == 0

    def test_dispatcher_no_handlers(self):
        """Test dispatcher with no handlers enabled."""
        from src.security.siem.dispatcher import SIEMDispatcher

        config = MockSIEMConfig(
            enabled=True,
            syslog_enabled=False,
            cef_enabled=False,
            leef_enabled=False,
        )
        config.syslog.host = None
        config.cef.host = None
        config.leef.host = None

        dispatcher = SIEMDispatcher(config)

        assert dispatcher.is_enabled is False
        assert dispatcher.handler_count == 0

    @patch("src.security.siem.dispatcher.SysLogHandler")
    def test_dispatcher_with_syslog(self, mock_syslog_class):
        """Test dispatcher initializes SysLog handler."""
        from src.security.siem.dispatcher import SIEMDispatcher

        mock_handler = MagicMock()
        mock_syslog_class.return_value = mock_handler

        config = MockSIEMConfig(
            enabled=True,
            syslog_enabled=True,
            cef_enabled=False,
            leef_enabled=False,
        )

        dispatcher = SIEMDispatcher(config)

        assert dispatcher.is_enabled is True
        assert dispatcher.handler_count == 1
        mock_syslog_class.assert_called_once()

    @patch("src.security.siem.dispatcher.SysLogHandler")
    @patch("src.security.siem.dispatcher.CEFHandler")
    def test_dispatcher_with_multiple_handlers(
        self, mock_cef_class, mock_syslog_class
    ):
        """Test dispatcher with multiple handlers."""
        from src.security.siem.dispatcher import SIEMDispatcher

        mock_syslog_class.return_value = MagicMock()
        mock_cef_class.return_value = MagicMock()

        config = MockSIEMConfig(
            enabled=True,
            syslog_enabled=True,
            cef_enabled=True,
            leef_enabled=False,
        )

        dispatcher = SIEMDispatcher(config)

        assert dispatcher.handler_count == 2

    @patch("src.security.siem.dispatcher.SysLogHandler")
    @patch("src.security.siem.dispatcher.SIEMBuffer")
    def test_dispatch_event(self, mock_buffer_class, mock_syslog_class):
        """Test dispatching event."""
        from src.security.siem.dispatcher import SIEMDispatcher
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        mock_handler = MagicMock()
        mock_syslog_class.return_value = mock_handler

        mock_buffer = MagicMock()
        mock_buffer.enqueue.return_value = True
        mock_buffer_class.return_value = mock_buffer

        config = MockSIEMConfig(enabled=True, syslog_enabled=True)
        dispatcher = SIEMDispatcher(config)

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test dispatch",
            request_id="req-disp-1",
        )

        result = dispatcher.dispatch(event)

        assert result is True
        mock_buffer.enqueue.assert_called_once_with(event)

    @patch("src.security.siem.dispatcher.SysLogHandler")
    def test_dispatch_sync(self, mock_syslog_class):
        """Test synchronous dispatch (bypass buffer)."""
        from src.security.siem.dispatcher import SIEMDispatcher
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        mock_handler = MagicMock()
        mock_handler.send.return_value = True
        mock_syslog_class.return_value = mock_handler

        config = MockSIEMConfig(enabled=True, syslog_enabled=True)
        dispatcher = SIEMDispatcher(config)

        event = SecurityEvent.create(
            event_type=SecurityEventType.SECURITY_ALERT,
            message="Critical alert",
            request_id="req-sync-1",
            severity=2,
        )

        result = dispatcher.dispatch_sync(event)

        assert result is True
        mock_handler.send.assert_called_once_with(event)

    @patch("src.security.siem.dispatcher.SysLogHandler")
    @patch("src.security.siem.dispatcher.SIEMBuffer")
    def test_dispatcher_close(self, mock_buffer_class, mock_syslog_class):
        """Test dispatcher close."""
        from src.security.siem.dispatcher import SIEMDispatcher

        mock_handler = MagicMock()
        mock_syslog_class.return_value = mock_handler

        mock_buffer = MagicMock()
        mock_buffer_class.return_value = mock_buffer

        config = MockSIEMConfig(enabled=True, syslog_enabled=True)
        dispatcher = SIEMDispatcher(config)
        dispatcher.close()

        mock_buffer.stop.assert_called_once()
        mock_handler.close.assert_called_once()
        assert dispatcher.handler_count == 0

    @patch("src.security.siem.dispatcher.SysLogHandler")
    @patch("src.security.siem.dispatcher.SIEMBuffer")
    def test_dispatcher_stats(self, mock_buffer_class, mock_syslog_class):
        """Test dispatcher stats property."""
        from src.security.siem.dispatcher import SIEMDispatcher

        mock_syslog_class.return_value = MagicMock()

        mock_buffer = MagicMock()
        mock_buffer.stats = {"sent": 10, "failed": 2}
        mock_buffer_class.return_value = mock_buffer

        config = MockSIEMConfig(enabled=True, syslog_enabled=True)
        dispatcher = SIEMDispatcher(config)

        stats = dispatcher.stats

        assert stats["sent"] == 10
        assert stats["failed"] == 2


class TestGlobalDispatcherFunctions:
    """Tests for global dispatcher functions."""

    def test_get_dispatcher_none(self):
        """Test get_siem_dispatcher when not initialized."""
        from src.security.siem import dispatcher as disp_module

        # Reset global state
        disp_module._dispatcher = None

        result = disp_module.get_siem_dispatcher()

        assert result is None

    @patch("src.security.siem.dispatcher.SIEMDispatcher")
    def test_init_dispatcher(self, mock_dispatcher_class):
        """Test init_siem_dispatcher."""
        from src.security.siem import dispatcher as disp_module

        mock_dispatcher = MagicMock()
        mock_dispatcher_class.return_value = mock_dispatcher

        # Reset global state
        disp_module._dispatcher = None

        config = MockSIEMConfig()
        result = disp_module.init_siem_dispatcher(config)

        assert result == mock_dispatcher
        mock_dispatcher_class.assert_called_once_with(config)

    @patch("src.security.siem.dispatcher.SIEMDispatcher")
    def test_init_dispatcher_closes_existing(self, mock_dispatcher_class):
        """Test init_siem_dispatcher closes existing dispatcher."""
        from src.security.siem import dispatcher as disp_module

        old_dispatcher = MagicMock()
        new_dispatcher = MagicMock()
        mock_dispatcher_class.return_value = new_dispatcher

        # Set existing dispatcher
        disp_module._dispatcher = old_dispatcher

        config = MockSIEMConfig()
        disp_module.init_siem_dispatcher(config)

        old_dispatcher.close.assert_called_once()

    def test_dispatch_security_event_no_dispatcher(self):
        """Test dispatch_security_event when no dispatcher."""
        from src.security.siem import dispatcher as disp_module
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        # Reset global state
        disp_module._dispatcher = None

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test",
            request_id="req-1",
        )

        result = disp_module.dispatch_security_event(event)

        assert result is False

    def test_dispatch_security_event_with_dispatcher(self):
        """Test dispatch_security_event with dispatcher."""
        from src.security.siem import dispatcher as disp_module
        from src.security.siem.base_handler import SecurityEvent, SecurityEventType

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = True
        disp_module._dispatcher = mock_dispatcher

        event = SecurityEvent.create(
            event_type=SecurityEventType.LLM_REQUEST,
            message="Test",
            request_id="req-1",
        )

        result = disp_module.dispatch_security_event(event)

        assert result is True
        mock_dispatcher.dispatch.assert_called_once_with(event)


class TestBaseSIEMHandler:
    """Tests for BaseSIEMHandler abstract class."""

    def test_handler_context_manager(self):
        """Test handler as context manager."""
        from src.security.siem.syslog_handler import SysLogHandler

        with SysLogHandler(MockSysLogConfig()) as handler:
            assert handler is not None

    @patch("socket.socket")
    def test_send_tcp(self, mock_socket_class):
        """Test TCP sending."""
        from src.security.siem.syslog_handler import SysLogHandler

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        config = MockSysLogConfig()
        config.protocol = "tcp"
        handler = SysLogHandler(config)

        result = handler._send_tcp("test message")

        assert result is True
        mock_socket.connect.assert_called_once_with(("localhost", 514))
        mock_socket.sendall.assert_called_once()
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_send_tcp_failure(self, mock_socket_class):
        """Test TCP sending failure."""
        from src.security.siem.syslog_handler import SysLogHandler

        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_class.return_value = mock_socket

        config = MockSysLogConfig()
        config.protocol = "tcp"
        handler = SysLogHandler(config)

        result = handler._send_tcp("test message")

        assert result is False

    def test_unknown_protocol(self):
        """Test handling of unknown protocol."""
        from src.security.siem.syslog_handler import SysLogHandler

        config = MockSysLogConfig()
        config.protocol = "invalid"
        handler = SysLogHandler(config)

        result = handler._send_message("test message")

        assert result is False
