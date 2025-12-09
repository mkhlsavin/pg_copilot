"""
CEF Handler - Common Event Format for ArcSight and compatible SIEM systems.

CEF Format:
CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
"""

from typing import Dict, Any
from .base_handler import BaseSIEMHandler, SecurityEvent
from ..config import CEFConfig


class CEFHandler(BaseSIEMHandler):
    """
    Common Event Format (CEF) handler for ArcSight.

    CEF Message Format:
    CEF:0|Vendor|Product|Version|SignatureID|Name|Severity|Extension

    Example:
    CEF:0|RAG-CPGQL|CodeAnalysis|1.0|DLP001|DLP Block|7|src=192.168.1.1 suser=user123 msg=Credential detected
    """

    # CEF version
    CEF_VERSION = "0"

    # Severity mapping (0-10 scale for CEF)
    SEVERITY_MAP = {
        0: 10,  # Emergency -> 10
        1: 9,   # Alert -> 9
        2: 8,   # Critical -> 8
        3: 7,   # Error -> 7
        4: 6,   # Warning -> 6
        5: 5,   # Notice -> 5
        6: 3,   # Info -> 3
        7: 1,   # Debug -> 1
    }

    # Event type to Signature ID mapping
    SIGNATURE_MAP = {
        "llm.request": ("LLM001", "LLM Request"),
        "llm.response": ("LLM002", "LLM Response"),
        "llm.error": ("LLM003", "LLM Error"),
        "dlp.block": ("DLP001", "DLP Block"),
        "dlp.mask": ("DLP002", "DLP Mask"),
        "dlp.warn": ("DLP003", "DLP Warning"),
        "dlp.log": ("DLP004", "DLP Log"),
        "vault.access": ("VLT001", "Vault Access"),
        "vault.rotate": ("VLT002", "Vault Rotate"),
        "auth.success": ("AUTH01", "Auth Success"),
        "auth.failure": ("AUTH02", "Auth Failure"),
        "rate.limit": ("RATE01", "Rate Limit"),
        "security.alert": ("SEC001", "Security Alert"),
    }

    def __init__(self, config: CEFConfig):
        """
        Initialize CEF handler.

        Args:
            config: CEF configuration
        """
        super().__init__(
            host=config.host,
            port=config.port,
            protocol=config.protocol if isinstance(config.protocol, str) else config.protocol.value
        )
        self.device_vendor = config.device_vendor
        self.device_product = config.device_product
        self.device_version = config.device_version

    @staticmethod
    def _escape_cef_value(value: str) -> str:
        """
        Escape special characters in CEF values.

        Pipe (|), backslash (\), and equals (=) must be escaped.
        """
        if not value:
            return ""
        return value.replace("\\", "\\\\").replace("|", "\\|").replace("=", "\\=")

    @staticmethod
    def _escape_extension_value(value: str) -> str:
        """
        Escape special characters in CEF extension values.

        Backslash (\), equals (=), and newlines must be escaped.
        """
        if not value:
            return ""
        return (value
                .replace("\\", "\\\\")
                .replace("=", "\\=")
                .replace("\n", "\\n")
                .replace("\r", "\\r"))

    def _get_signature(self, event: SecurityEvent) -> tuple:
        """Get signature ID and name for event type."""
        event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        return self.SIGNATURE_MAP.get(event_type, ("GEN001", "Generic Event"))

    def _map_severity(self, severity: int) -> int:
        """Map syslog severity (0-7) to CEF severity (0-10)."""
        return self.SEVERITY_MAP.get(severity, 3)

    def _build_extension(self, event: SecurityEvent) -> str:
        """
        Build CEF extension string.

        Common CEF extension fields:
        - src: Source IP
        - suser: Source user
        - msg: Message
        - rt: Receipt time
        - externalId: External ID
        - cs1-cs6: Custom strings
        - cn1-cn3: Custom numbers
        """
        extensions = []

        # Standard CEF fields
        if event.ip_address:
            extensions.append(f"src={self._escape_extension_value(event.ip_address)}")
        if event.user_id:
            extensions.append(f"suser={self._escape_extension_value(event.user_id)}")
        if event.request_id:
            extensions.append(f"externalId={self._escape_extension_value(event.request_id)}")

        # Message
        extensions.append(f"msg={self._escape_extension_value(event.message)}")

        # Receipt time (milliseconds since epoch)
        extensions.append(f"rt={event.timestamp}")

        # Custom fields for LLM-specific data
        if event.provider:
            extensions.append(f"cs1={self._escape_extension_value(event.provider)}")
            extensions.append("cs1Label=LLM Provider")
        if event.model:
            extensions.append(f"cs2={self._escape_extension_value(event.model)}")
            extensions.append("cs2Label=LLM Model")
        if event.action:
            extensions.append(f"cs3={self._escape_extension_value(event.action)}")
            extensions.append("cs3Label=Action")
        if event.dlp_category:
            extensions.append(f"cs4={self._escape_extension_value(event.dlp_category)}")
            extensions.append("cs4Label=DLP Category")
        if event.dlp_pattern:
            extensions.append(f"cs5={self._escape_extension_value(event.dlp_pattern)}")
            extensions.append("cs5Label=DLP Pattern")

        # Custom numbers
        if event.tokens_used is not None:
            extensions.append(f"cn1={event.tokens_used}")
            extensions.append("cn1Label=Tokens Used")
        if event.latency_ms is not None:
            extensions.append(f"cn2={int(event.latency_ms)}")
            extensions.append("cn2Label=Latency MS")

        return " ".join(extensions)

    def format_event(self, event: SecurityEvent) -> str:
        """
        Format event as CEF message.

        Format:
        CEF:Version|Vendor|Product|Version|SignatureID|Name|Severity|Extension
        """
        signature_id, name = self._get_signature(event)
        severity = self._map_severity(event.severity)
        extension = self._build_extension(event)

        # Build CEF header
        header_parts = [
            f"CEF:{self.CEF_VERSION}",
            self._escape_cef_value(self.device_vendor),
            self._escape_cef_value(self.device_product),
            self._escape_cef_value(self.device_version),
            self._escape_cef_value(signature_id),
            self._escape_cef_value(name),
            str(severity),
        ]

        return "|".join(header_parts) + f"|{extension}"
