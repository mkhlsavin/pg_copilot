"""
DLP Action Handlers - Execute DLP actions based on scan results.

Provides action handlers for:
- BLOCK: Reject the request
- MASK: Replace sensitive data
- WARN: Allow but log warning
- LOG_ONLY: Silent logging
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime

from .patterns import DLPMatch
from .scanner import ScanResult
from ..config import DLPAction, DLPConfig

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """
    Result of executing a DLP action.

    Attributes:
        action: The action that was executed
        allowed: Whether the request is allowed to proceed
        content: Modified content (if masked)
        message: Human-readable message
        alert_sent: Whether an external alert was sent
    """
    action: DLPAction
    allowed: bool
    content: Optional[str]
    message: str
    alert_sent: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DLPActionHandler:
    """
    Handles execution of DLP actions.

    Provides:
    - Action execution based on scan results
    - Alert callbacks for external integration
    - Audit logging
    """

    def __init__(
        self,
        config: DLPConfig,
        alert_callback: Optional[Callable[[List[DLPMatch], DLPAction], None]] = None,
    ):
        """
        Initialize action handler.

        Args:
            config: DLP configuration
            alert_callback: Optional callback for sending alerts
        """
        self._config = config
        self._alert_callback = alert_callback

        # Statistics
        self._stats = {
            "block_count": 0,
            "mask_count": 0,
            "warn_count": 0,
            "log_count": 0,
        }

    def execute(
        self,
        scan_result: ScanResult,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Execute DLP action based on scan result.

        Args:
            scan_result: Result from content scanner
            content: Original content
            context: Additional context for logging

        Returns:
            ActionResult with action outcome
        """
        if not scan_result.has_matches:
            return ActionResult(
                action=DLPAction.LOG_ONLY,
                allowed=True,
                content=content,
                message="No sensitive data detected",
            )

        action = scan_result.action
        context = context or {}

        if action == DLPAction.BLOCK:
            return self._handle_block(scan_result, content, context)
        elif action == DLPAction.MASK:
            return self._handle_mask(scan_result, content, context)
        elif action == DLPAction.WARN:
            return self._handle_warn(scan_result, content, context)
        else:  # LOG_ONLY
            return self._handle_log(scan_result, content, context)

    def _handle_block(
        self,
        scan_result: ScanResult,
        content: str,
        context: Dict[str, Any],
    ) -> ActionResult:
        """Handle BLOCK action - reject the request."""
        self._stats["block_count"] += 1

        # Log the block
        self._log_action("BLOCK", scan_result.matches, context)

        # Send alert if configured
        alert_sent = self._send_alert(scan_result.matches, DLPAction.BLOCK)

        categories = set(m.category for m in scan_result.matches)
        message = (f"Request blocked: detected {len(scan_result.matches)} "
                  f"violation(s) in {', '.join(categories)}")

        return ActionResult(
            action=DLPAction.BLOCK,
            allowed=False,
            content=None,
            message=message,
            alert_sent=alert_sent,
            metadata={
                "match_count": len(scan_result.matches),
                "categories": list(categories),
            },
        )

    def _handle_mask(
        self,
        scan_result: ScanResult,
        content: str,
        context: Dict[str, Any],
    ) -> ActionResult:
        """Handle MASK action - replace sensitive data."""
        self._stats["mask_count"] += 1

        # Log the mask action
        self._log_action("MASK", scan_result.matches, context)

        # Use pre-masked content from scan result
        masked_content = scan_result.modified_content or content

        return ActionResult(
            action=DLPAction.MASK,
            allowed=True,
            content=masked_content,
            message=f"Masked {len(scan_result.matches)} sensitive data occurrence(s)",
            metadata={
                "masked_count": len(scan_result.matches),
                "categories": list(set(m.category for m in scan_result.matches)),
            },
        )

    def _handle_warn(
        self,
        scan_result: ScanResult,
        content: str,
        context: Dict[str, Any],
    ) -> ActionResult:
        """Handle WARN action - allow but log warning."""
        self._stats["warn_count"] += 1

        # Log warning
        self._log_action("WARN", scan_result.matches, context)

        # Send alert if configured
        alert_sent = self._send_alert(scan_result.matches, DLPAction.WARN)

        categories = set(m.category for m in scan_result.matches)
        message = (f"Warning: detected {len(scan_result.matches)} potential "
                  f"sensitive data in {', '.join(categories)}")

        logger.warning(message)

        return ActionResult(
            action=DLPAction.WARN,
            allowed=True,
            content=content,
            message=message,
            alert_sent=alert_sent,
            metadata={
                "match_count": len(scan_result.matches),
                "categories": list(categories),
            },
        )

    def _handle_log(
        self,
        scan_result: ScanResult,
        content: str,
        context: Dict[str, Any],
    ) -> ActionResult:
        """Handle LOG_ONLY action - silent logging."""
        self._stats["log_count"] += 1

        # Log silently
        self._log_action("LOG", scan_result.matches, context)

        return ActionResult(
            action=DLPAction.LOG_ONLY,
            allowed=True,
            content=content,
            message=f"Logged {len(scan_result.matches)} match(es)",
        )

    def _log_action(
        self,
        action: str,
        matches: List[DLPMatch],
        context: Dict[str, Any],
    ) -> None:
        """Log DLP action with details."""
        log_data = {
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "match_count": len(matches),
            "categories": list(set(m.category for m in matches)),
            "patterns": [m.pattern_name for m in matches[:5]],  # Limit
            **context,
        }

        if action == "BLOCK":
            logger.warning(f"DLP {action}: {log_data}")
        else:
            logger.info(f"DLP {action}: {log_data}")

    def _send_alert(self, matches: List[DLPMatch], action: DLPAction) -> bool:
        """
        Send alert via callback if configured.

        Returns True if alert was sent.
        """
        if self._alert_callback is None:
            return False

        try:
            self._alert_callback(matches, action)
            return True
        except Exception as e:
            logger.error(f"Failed to send DLP alert: {e}")
            return False

    @property
    def stats(self) -> Dict[str, int]:
        """Get action statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0


def create_action_handler(config: DLPConfig) -> DLPActionHandler:
    """
    Create a DLP action handler from configuration.

    Args:
        config: DLP configuration

    Returns:
        Configured DLPActionHandler
    """
    return DLPActionHandler(config)
