"""
LEEF Handler - Log Event Extended Format for IBM QRadar.

LEEF Format:
LEEF:Version|Vendor|Product|Version|EventID|Extension
"""

from typing import Dict, Any
from .base_handler import BaseSIEMHandler, SecurityEvent
from ..config import LEEFConfig


class LEEFHandler(BaseSIEMHandler):
    """
    Log Event Extended Format (LEEF) handler for IBM QRadar.

    LEEF Message Format:
    LEEF:2.0|Vendor|Product|Version|EventID|key1=value1\tkey2=value2

    Example:
    LEEF:2.0|RAG-CPGQL|CodeAnalysis|1.0|DLP001|src=192.168.1.1\tusrName=user123\tmsg=Credential detected
    """

    # LEEF version
    LEEF_VERSION = "2.0"

    # Field delimiter (tab for LEEF 2.0)
    DELIMITER = "\t"

    # Event type to EventID mapping
    EVENT_ID_MAP = {
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

    # Severity mapping to QRadar categories
    SEVERITY_MAP = {
        0: "Emergency",
        1: "Alert",
        2: "Critical",
        3: "Error",
        4: "Warning",
        5: "Notice",
        6: "Information",
        7: "Debug",
    }

    def __init__(self, config: LEEFConfig):
        """
        Initialize LEEF handler.

        Args:
            config: LEEF configuration
        """
        super().__init__(
            host=config.host,
            port=config.port,
            protocol=config.protocol if isinstance(config.protocol, str) else config.protocol.value
        )
        self.product_vendor = config.product_vendor
        self.product_name = config.product_name
        self.product_version = config.product_version

    @staticmethod
    def _escape_leef_value(value: str) -> str:
        """
        Escape special characters in LEEF values.

        Tab, newline, carriage return, and backslash must be escaped.
        """
        if not value:
            return ""
        return (value
                .replace("\\", "\\\\")
                .replace("\t", "\\t")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("=", "\\="))

    def _get_event_id(self, event: SecurityEvent) -> str:
        """Get EventID for event type."""
        event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        return self.EVENT_ID_MAP.get(event_type, "GEN001")

    def _build_extension(self, event: SecurityEvent) -> str:
        """
        Build LEEF extension string.

        Standard LEEF fields:
        - src: Source IP
        - usrName: Username
        - cat: Category
        - sev: Severity
        - devTime: Device time
        - msg: Message
        """
        fields = []

        # Standard LEEF fields
        if event.ip_address:
            fields.append(f"src={self._escape_leef_value(event.ip_address)}")
        if event.user_id:
            fields.append(f"usrName={self._escape_leef_value(event.user_id)}")

        # Category based on event type
        event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        category = event_type.split(".")[0].upper()
        fields.append(f"cat={category}")

        # Severity
        sev_name = self.SEVERITY_MAP.get(event.severity, "Information")
        fields.append(f"sev={sev_name}")

        # Timestamp
        fields.append(f"devTime={self._escape_leef_value(event.timestamp)}")

        # Message
        fields.append(f"msg={self._escape_leef_value(event.message)}")

        # Request ID
        fields.append(f"externalId={self._escape_leef_value(event.request_id)}")

        # LLM-specific fields
        if event.provider:
            fields.append(f"llmProvider={self._escape_leef_value(event.provider)}")
        if event.model:
            fields.append(f"llmModel={self._escape_leef_value(event.model)}")
        if event.action:
            fields.append(f"action={self._escape_leef_value(event.action)}")

        # DLP-specific fields
        if event.dlp_category:
            fields.append(f"dlpCategory={self._escape_leef_value(event.dlp_category)}")
        if event.dlp_pattern:
            fields.append(f"dlpPattern={self._escape_leef_value(event.dlp_pattern)}")

        # Metrics
        if event.tokens_used is not None:
            fields.append(f"tokensUsed={event.tokens_used}")
        if event.latency_ms is not None:
            fields.append(f"latencyMs={int(event.latency_ms)}")

        # Session info
        if event.session_id:
            fields.append(f"sessionId={self._escape_leef_value(event.session_id)}")
        if event.user_agent:
            fields.append(f"userAgent={self._escape_leef_value(event.user_agent)}")

        return self.DELIMITER.join(fields)

    def format_event(self, event: SecurityEvent) -> str:
        """
        Format event as LEEF message.

        Format:
        LEEF:Version|Vendor|Product|Version|EventID|Extension
        """
        event_id = self._get_event_id(event)
        extension = self._build_extension(event)

        # Build LEEF header (pipe-delimited)
        header_parts = [
            f"LEEF:{self.LEEF_VERSION}",
            self.product_vendor,
            self.product_name,
            self.product_version,
            event_id,
        ]

        return "|".join(header_parts) + f"|{extension}"
