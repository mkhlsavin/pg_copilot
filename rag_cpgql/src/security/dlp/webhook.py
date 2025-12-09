"""
DLP Webhook Client - Send alerts to external DLP systems.

Provides async webhook delivery with retry and batching.
"""

import asyncio
import logging
import json
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor

from .patterns import DLPMatch
from ..config import DLPWebhookConfig, DLPAction

logger = logging.getLogger(__name__)


@dataclass
class DLPAlert:
    """
    Alert to send to external DLP system.

    Attributes:
        alert_id: Unique alert identifier
        timestamp: Alert timestamp (ISO format)
        action: DLP action taken
        matches: List of DLP matches
        request_id: Associated request ID
        user_id: User who triggered the alert (optional)
        context: Additional context
    """
    alert_id: str
    timestamp: str
    action: str
    match_count: int
    categories: List[str]
    patterns: List[str]
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    severity: str = "medium"
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}

    @classmethod
    def from_matches(
        cls,
        matches: List[DLPMatch],
        action: DLPAction,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> "DLPAlert":
        """Create alert from DLP matches."""
        import uuid

        categories = list(set(m.category for m in matches))
        patterns = list(set(m.pattern_name for m in matches))

        # Determine severity from highest match severity
        severity_order = ["critical", "high", "medium", "low"]
        highest_severity = "low"
        for match in matches:
            if severity_order.index(match.severity) < severity_order.index(highest_severity):
                highest_severity = match.severity

        return cls(
            alert_id=str(uuid.uuid4())[:12],
            timestamp=datetime.utcnow().isoformat() + "Z",
            action=action.value if isinstance(action, DLPAction) else action,
            match_count=len(matches),
            categories=categories,
            patterns=patterns,
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            severity=highest_severity,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "match_count": self.match_count,
            "categories": self.categories,
            "patterns": self.patterns,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "severity": self.severity,
            "context": self.context,
        }


class DLPWebhookClient:
    """
    Client for sending DLP alerts to external systems via webhook.

    Features:
    - Async delivery with queue
    - Retry with exponential backoff
    - Configurable notification filters
    """

    def __init__(self, config: DLPWebhookConfig):
        """
        Initialize webhook client.

        Args:
            config: Webhook configuration
        """
        self._config = config
        self._enabled = config.enabled and config.endpoint
        self._notify_on = set(config.notify_on)

        # Queue for async delivery
        self._queue: Queue[DLPAlert] = Queue(maxsize=1000)
        self._running = False
        self._worker_thread: Optional[Thread] = None

        # HTTP session (created lazily)
        self._session = None

        if self._enabled:
            self._start_worker()

    def _start_worker(self) -> None:
        """Start background worker thread."""
        if self._running:
            return

        self._running = True
        self._worker_thread = Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info(f"DLP webhook client started: {self._config.endpoint}")

    def _worker_loop(self) -> None:
        """Background worker for sending alerts."""
        while self._running:
            try:
                # Wait for alert with timeout
                alert = self._queue.get(timeout=1.0)
                self._send_alert_sync(alert)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in webhook worker: {e}")

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()

                # Set auth header if configured
                if self._config.auth_header:
                    self._session.headers["Authorization"] = self._config.auth_header

                self._session.headers["Content-Type"] = "application/json"
                self._session.headers["User-Agent"] = "RAG-CPGQL-DLP/1.0"

            except ImportError:
                logger.error("requests library not installed, webhook disabled")
                self._enabled = False

        return self._session

    def _send_alert_sync(self, alert: DLPAlert) -> bool:
        """
        Send alert synchronously with retry.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully
        """
        session = self._get_session()
        if session is None:
            return False

        payload = json.dumps(alert.to_dict())

        for attempt in range(self._config.retry_attempts):
            try:
                response = session.post(
                    self._config.endpoint,
                    data=payload,
                    timeout=self._config.timeout_seconds,
                )

                if response.status_code < 400:
                    logger.debug(f"DLP alert sent: {alert.alert_id}")
                    return True
                else:
                    logger.warning(f"Webhook returned {response.status_code}: {response.text[:200]}")

            except Exception as e:
                logger.error(f"Webhook request failed (attempt {attempt + 1}): {e}")

            # Exponential backoff
            if attempt < self._config.retry_attempts - 1:
                time.sleep(2 ** attempt)

        logger.error(f"Failed to send DLP alert after {self._config.retry_attempts} attempts")
        return False

    def send_alert(
        self,
        matches: List[DLPMatch],
        action: DLPAction,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Queue alert for async delivery.

        Args:
            matches: DLP matches that triggered the alert
            action: DLP action taken
            request_id: Associated request ID
            user_id: User ID
            ip_address: Client IP

        Returns:
            True if alert was queued
        """
        if not self._enabled:
            return False

        # Check if we should notify for this action
        if action not in self._notify_on:
            return False

        alert = DLPAlert.from_matches(
            matches=matches,
            action=action,
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
        )

        try:
            self._queue.put_nowait(alert)
            return True
        except Exception:
            logger.warning("DLP webhook queue full, alert dropped")
            return False

    def send_alert_sync(
        self,
        matches: List[DLPMatch],
        action: DLPAction,
        **kwargs
    ) -> bool:
        """
        Send alert synchronously (blocking).

        Use for critical alerts that must be confirmed.
        """
        if not self._enabled:
            return False

        if action not in self._notify_on:
            return False

        alert = DLPAlert.from_matches(matches=matches, action=action, **kwargs)
        return self._send_alert_sync(alert)

    def stop(self) -> None:
        """Stop webhook client and flush queue."""
        self._running = False

        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None

        if self._session:
            self._session.close()
            self._session = None

        logger.info("DLP webhook client stopped")

    @property
    def is_enabled(self) -> bool:
        """Check if webhook is enabled."""
        return self._enabled

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# Convenience function for creating alert callback
def create_webhook_alert_callback(config: DLPWebhookConfig):
    """
    Create a callback function for use with DLPActionHandler.

    Args:
        config: Webhook configuration

    Returns:
        Callback function that sends alerts via webhook
    """
    client = DLPWebhookClient(config)

    def callback(matches: List[DLPMatch], action: DLPAction) -> None:
        client.send_alert(matches, action)

    return callback, client
