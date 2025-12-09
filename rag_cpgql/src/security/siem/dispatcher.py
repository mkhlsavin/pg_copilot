"""
SIEM Dispatcher - Routes security events to multiple SIEM handlers.

Supports simultaneous delivery to SysLog, CEF, and LEEF endpoints.
"""

import logging
from typing import List, Optional
from threading import Lock

from .base_handler import BaseSIEMHandler, SecurityEvent
from .syslog_handler import SysLogHandler
from .cef_handler import CEFHandler
from .leef_handler import LEEFHandler
from .buffer import SIEMBuffer
from ..config import SIEMConfig

logger = logging.getLogger(__name__)


class SIEMDispatcher:
    """
    Dispatches security events to multiple SIEM handlers.

    Features:
    - Support for multiple handlers (SysLog, CEF, LEEF)
    - Buffered delivery with retry
    - Thread-safe operation
    - Graceful degradation on handler failure
    """

    def __init__(self, config: SIEMConfig):
        """
        Initialize SIEM dispatcher from configuration.

        Args:
            config: SIEM configuration
        """
        self._config = config
        self._handlers: List[BaseSIEMHandler] = []
        self._buffer: Optional[SIEMBuffer] = None
        self._lock = Lock()
        self._enabled = config.enabled

        if self._enabled:
            self._init_handlers()
            self._init_buffer()

    def _init_handlers(self) -> None:
        """Initialize configured handlers."""
        # SysLog handler
        if self._config.syslog.enabled and self._config.syslog.host:
            try:
                handler = SysLogHandler(self._config.syslog)
                self._handlers.append(handler)
                logger.info(f"SysLog handler initialized: {self._config.syslog.host}:{self._config.syslog.port}")
            except Exception as e:
                logger.error(f"Failed to initialize SysLog handler: {e}")

        # CEF handler
        if self._config.cef.enabled and self._config.cef.host:
            try:
                handler = CEFHandler(self._config.cef)
                self._handlers.append(handler)
                logger.info(f"CEF handler initialized: {self._config.cef.host}:{self._config.cef.port}")
            except Exception as e:
                logger.error(f"Failed to initialize CEF handler: {e}")

        # LEEF handler
        if self._config.leef.enabled and self._config.leef.host:
            try:
                handler = LEEFHandler(self._config.leef)
                self._handlers.append(handler)
                logger.info(f"LEEF handler initialized: {self._config.leef.host}:{self._config.leef.port}")
            except Exception as e:
                logger.error(f"Failed to initialize LEEF handler: {e}")

        if not self._handlers:
            logger.warning("No SIEM handlers configured")

    def _init_buffer(self) -> None:
        """Initialize message buffer."""
        if self._handlers:
            self._buffer = SIEMBuffer(
                send_func=self._send_to_all,
                max_size=self._config.buffer.max_size,
                flush_interval=self._config.buffer.flush_interval_seconds,
                max_retries=self._config.buffer.retry_attempts,
                retry_backoff=self._config.buffer.retry_backoff_seconds,
            )
            self._buffer.start()

    def _send_to_all(self, event: SecurityEvent) -> bool:
        """
        Send event to all handlers.

        Returns True if at least one handler succeeded.
        """
        success_count = 0

        for handler in self._handlers:
            try:
                if handler.send(event):
                    success_count += 1
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} failed: {e}")

        return success_count > 0

    def dispatch(self, event: SecurityEvent) -> bool:
        """
        Dispatch security event to all SIEM handlers.

        Args:
            event: Security event to dispatch

        Returns:
            True if event was queued successfully
        """
        if not self._enabled:
            return False

        if not self._handlers:
            logger.debug("No SIEM handlers available, event not sent")
            return False

        with self._lock:
            if self._buffer:
                return self._buffer.enqueue(event)
            else:
                # Direct send without buffering
                return self._send_to_all(event)

    def dispatch_sync(self, event: SecurityEvent) -> bool:
        """
        Dispatch event synchronously (bypass buffer).

        Use for critical events that must be sent immediately.

        Args:
            event: Security event to dispatch

        Returns:
            True if sent successfully
        """
        if not self._enabled or not self._handlers:
            return False

        return self._send_to_all(event)

    def flush(self) -> int:
        """
        Flush buffer immediately.

        Returns:
            Number of messages sent
        """
        if self._buffer:
            return self._buffer.flush()
        return 0

    @property
    def stats(self) -> dict:
        """Get buffer statistics."""
        if self._buffer:
            return self._buffer.stats
        return {}

    @property
    def handler_count(self) -> int:
        """Number of active handlers."""
        return len(self._handlers)

    @property
    def is_enabled(self) -> bool:
        """Check if dispatcher is enabled and has handlers."""
        return self._enabled and len(self._handlers) > 0

    def close(self) -> None:
        """Close all handlers and stop buffer."""
        if self._buffer:
            self._buffer.stop()

        for handler in self._handlers:
            try:
                handler.close()
            except Exception as e:
                logger.error(f"Error closing handler: {e}")

        self._handlers.clear()
        logger.info("SIEM dispatcher closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Singleton dispatcher instance
_dispatcher: Optional[SIEMDispatcher] = None


def get_siem_dispatcher() -> Optional[SIEMDispatcher]:
    """
    Get the global SIEM dispatcher instance.

    Returns:
        SIEMDispatcher or None if not initialized
    """
    return _dispatcher


def init_siem_dispatcher(config: SIEMConfig) -> SIEMDispatcher:
    """
    Initialize the global SIEM dispatcher.

    Args:
        config: SIEM configuration

    Returns:
        Initialized SIEMDispatcher
    """
    global _dispatcher

    if _dispatcher is not None:
        _dispatcher.close()

    _dispatcher = SIEMDispatcher(config)
    return _dispatcher


def dispatch_security_event(event: SecurityEvent) -> bool:
    """
    Convenience function to dispatch event via global dispatcher.

    Args:
        event: Security event to dispatch

    Returns:
        True if dispatched successfully
    """
    if _dispatcher:
        return _dispatcher.dispatch(event)
    return False
