"""
SysLog Handler - RFC 5424 compliant syslog messages.

Supports UDP, TCP, and TLS transport protocols.
"""

import socket
from datetime import datetime
from typing import Optional

from .base_handler import BaseSIEMHandler, SecurityEvent
from ..config import SysLogConfig, SIEMFacility


class SysLogHandler(BaseSIEMHandler):
    """
    RFC 5424 SysLog handler.

    Message format:
    <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD-ID SD-PARAMS] MSG

    Example:
    <134>1 2024-12-09T10:30:00.000Z server01 codegraph 1234 LLM001 [meta@47450 request_id="abc123"] LLM request logged
    """

    # Structured Data ID (enterprise number 47450 is a placeholder)
    SD_ID = "meta@47450"

    def __init__(self, config: SysLogConfig):
        """
        Initialize SysLog handler.

        Args:
            config: SysLog configuration
        """
        super().__init__(
            host=config.host,
            port=config.port,
            protocol=config.protocol if isinstance(config.protocol, str) else config.protocol.value
        )
        self.facility = config.facility
        self.app_name = config.app_name
        self.hostname = config.hostname or socket.gethostname()
        self._procid = str(self._get_procid())

    @staticmethod
    def _get_procid() -> int:
        """Get current process ID."""
        import os
        return os.getpid()

    def _calculate_priority(self, severity: int) -> int:
        """
        Calculate PRI value from facility and severity.

        PRI = facility * 8 + severity
        """
        return (self.facility * 8) + severity

    def _format_timestamp(self, timestamp: str) -> str:
        """
        Format timestamp to RFC 5424 format.

        Input: ISO format (2024-12-09T10:30:00.000Z)
        Output: RFC 5424 format (2024-12-09T10:30:00.000000Z)
        """
        try:
            # Parse and reformat
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1]
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        except Exception:
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    def _format_structured_data(self, event: SecurityEvent) -> str:
        """
        Format structured data section.

        Format: [SD-ID key1="value1" key2="value2"]
        """
        params = []

        # Add core identifiers
        params.append(f'request_id="{event.request_id}"')
        params.append(f'event_type="{event.event_type.value if hasattr(event.event_type, "value") else event.event_type}"')

        # Add optional fields
        if event.user_id:
            params.append(f'user_id="{event.user_id}"')
        if event.ip_address:
            params.append(f'src_ip="{event.ip_address}"')
        if event.provider:
            params.append(f'provider="{event.provider}"')
        if event.model:
            params.append(f'model="{event.model}"')
        if event.action:
            params.append(f'action="{event.action}"')
        if event.dlp_category:
            params.append(f'dlp_category="{event.dlp_category}"')
        if event.dlp_pattern:
            params.append(f'dlp_pattern="{event.dlp_pattern}"')
        if event.tokens_used is not None:
            params.append(f'tokens="{event.tokens_used}"')
        if event.latency_ms is not None:
            params.append(f'latency_ms="{event.latency_ms:.2f}"')

        return f"[{self.SD_ID} {' '.join(params)}]"

    def _generate_msgid(self, event: SecurityEvent) -> str:
        """
        Generate message ID based on event type.

        Format: {PREFIX}{NUMBER}
        """
        type_map = {
            "llm.request": "LLM001",
            "llm.response": "LLM002",
            "llm.error": "LLM003",
            "dlp.block": "DLP001",
            "dlp.mask": "DLP002",
            "dlp.warn": "DLP003",
            "dlp.log": "DLP004",
            "vault.access": "VLT001",
            "vault.rotate": "VLT002",
            "auth.success": "AUTH01",
            "auth.failure": "AUTH02",
            "rate.limit": "RATE01",
            "security.alert": "SEC001",
        }
        event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        return type_map.get(event_type, "GEN001")

    def format_event(self, event: SecurityEvent) -> str:
        """
        Format event as RFC 5424 syslog message.

        Format:
        <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD] MSG
        """
        pri = self._calculate_priority(event.severity)
        timestamp = self._format_timestamp(event.timestamp)
        msgid = self._generate_msgid(event)
        structured_data = self._format_structured_data(event)

        # Escape special characters in message
        message = event.message.replace("\\", "\\\\").replace('"', '\\"')

        # RFC 5424 format
        return f"<{pri}>1 {timestamp} {self.hostname} {self.app_name} {self._procid} {msgid} {structured_data} {message}"


class SysLogJSONHandler(SysLogHandler):
    """
    SysLog handler that sends JSON-formatted messages.

    Useful for SIEM systems that parse JSON payloads.
    """

    def format_event(self, event: SecurityEvent) -> str:
        """
        Format event as syslog message with JSON payload.
        """
        import json

        pri = self._calculate_priority(event.severity)
        timestamp = self._format_timestamp(event.timestamp)
        msgid = self._generate_msgid(event)

        # JSON payload
        json_payload = json.dumps(event.to_dict(), ensure_ascii=False)

        # RFC 5424 format with JSON as message
        return f"<{pri}>1 {timestamp} {self.hostname} {self.app_name} {self._procid} {msgid} - {json_payload}"
