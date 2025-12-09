"""
SIEM Integration Module.

Provides handlers for sending security events to SIEM systems:
- SysLog (RFC 5424)
- CEF (Common Event Format) for ArcSight
- LEEF (Log Event Extended Format) for QRadar
"""

from .base_handler import (
    BaseSIEMHandler,
    SecurityEvent,
    SecurityEventType,
)
from .syslog_handler import SysLogHandler, SysLogJSONHandler
from .cef_handler import CEFHandler
from .leef_handler import LEEFHandler
from .buffer import SIEMBuffer, AsyncSIEMBuffer
from .dispatcher import (
    SIEMDispatcher,
    get_siem_dispatcher,
    init_siem_dispatcher,
    dispatch_security_event,
)

__all__ = [
    # Base
    "BaseSIEMHandler",
    "SecurityEvent",
    "SecurityEventType",
    # Handlers
    "SysLogHandler",
    "SysLogJSONHandler",
    "CEFHandler",
    "LEEFHandler",
    # Buffer
    "SIEMBuffer",
    "AsyncSIEMBuffer",
    # Dispatcher
    "SIEMDispatcher",
    "get_siem_dispatcher",
    "init_siem_dispatcher",
    "dispatch_security_event",
]
