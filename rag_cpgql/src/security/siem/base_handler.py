"""
Base SIEM Handler - Abstract base class for all SIEM integrations.

Provides common interface for SysLog, CEF, and LEEF handlers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import socket
import logging

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Types of security events to send to SIEM."""
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    DLP_BLOCK = "dlp.block"
    DLP_MASK = "dlp.mask"
    DLP_WARN = "dlp.warn"
    DLP_LOG = "dlp.log"
    VAULT_ACCESS = "vault.access"
    VAULT_ROTATE = "vault.rotate"
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    RATE_LIMIT = "rate.limit"
    SECURITY_ALERT = "security.alert"


@dataclass
class SecurityEvent:
    """
    Security event for SIEM logging.

    Attributes:
        event_type: Type of security event
        timestamp: Event timestamp (ISO format)
        request_id: Unique request identifier
        user_id: User identifier (optional)
        ip_address: Client IP address
        severity: Event severity (0-7, RFC 5424)
        message: Human-readable message
        details: Additional event details
    """
    event_type: SecurityEventType
    timestamp: str
    request_id: str
    message: str
    severity: int = 6  # INFO by default
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    action: Optional[str] = None
    dlp_category: Optional[str] = None
    dlp_pattern: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: SecurityEventType,
        message: str,
        request_id: str,
        severity: int = 6,
        **kwargs
    ) -> "SecurityEvent":
        """Create a new security event with current timestamp."""
        return cls(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            request_id=request_id,
            message=message,
            severity=severity,
            **kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        result = {
            "event_type": self.event_type.value if isinstance(self.event_type, Enum) else self.event_type,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "message": self.message,
            "severity": self.severity,
        }

        # Add optional fields if present
        optional_fields = [
            "user_id", "session_id", "ip_address", "user_agent",
            "provider", "model", "action", "dlp_category", "dlp_pattern",
            "tokens_used", "latency_ms"
        ]
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value

        if self.details:
            result["details"] = self.details

        return result


class BaseSIEMHandler(ABC):
    """
    Abstract base class for SIEM handlers.

    Subclasses must implement:
    - format_event(): Convert SecurityEvent to handler-specific format
    - _send_message(): Send formatted message to SIEM
    """

    def __init__(self, host: str, port: int, protocol: str = "udp"):
        """
        Initialize SIEM handler.

        Args:
            host: SIEM server hostname or IP
            port: SIEM server port
            protocol: Transport protocol (udp, tcp, tls)
        """
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self._socket: Optional[socket.socket] = None
        self._hostname = socket.gethostname()

    @abstractmethod
    def format_event(self, event: SecurityEvent) -> str:
        """
        Format security event for this SIEM type.

        Args:
            event: Security event to format

        Returns:
            Formatted message string
        """
        pass

    def send(self, event: SecurityEvent) -> bool:
        """
        Send security event to SIEM.

        Args:
            event: Security event to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = self.format_event(event)
            return self._send_message(message)
        except Exception as e:
            logger.error(f"Failed to send event to SIEM: {e}")
            return False

    def _send_message(self, message: str) -> bool:
        """
        Send formatted message to SIEM server.

        Args:
            message: Formatted message string

        Returns:
            True if sent successfully
        """
        try:
            if self.protocol == "udp":
                return self._send_udp(message)
            elif self.protocol == "tcp":
                return self._send_tcp(message)
            elif self.protocol == "tls":
                return self._send_tls(message)
            else:
                logger.error(f"Unknown protocol: {self.protocol}")
                return False
        except Exception as e:
            logger.error(f"Failed to send message to {self.host}:{self.port}: {e}")
            return False

    def _send_udp(self, message: str) -> bool:
        """Send message via UDP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode("utf-8"), (self.host, self.port))
            sock.close()
            return True
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            return False

    def _send_tcp(self, message: str) -> bool:
        """Send message via TCP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.host, self.port))
            # Add newline for message framing
            sock.sendall((message + "\n").encode("utf-8"))
            sock.close()
            return True
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            return False

    def _send_tls(self, message: str) -> bool:
        """Send message via TLS."""
        try:
            import ssl
            context = ssl.create_default_context()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)

            with context.wrap_socket(sock, server_hostname=self.host) as ssock:
                ssock.connect((self.host, self.port))
                ssock.sendall((message + "\n").encode("utf-8"))

            return True
        except Exception as e:
            logger.error(f"TLS send failed: {e}")
            return False

    def close(self) -> None:
        """Close any open connections."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
