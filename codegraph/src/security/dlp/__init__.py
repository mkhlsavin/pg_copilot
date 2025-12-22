"""
DLP (Data Loss Prevention) Module.

Provides content scanning and filtering for sensitive data:
- Pattern-based detection (regex)
- Keyword blacklists/whitelists
- Configurable actions (BLOCK, MASK, WARN, LOG_ONLY)
- External webhook integration
"""

from .patterns import (
    PatternRegistry,
    DLPMatch,
    MatchType,
    CompiledPattern,
)
from .scanner import (
    ContentScanner,
    ScanResult,
    DLPBlockedException,
)
from .actions import (
    DLPActionHandler,
    ActionResult,
    create_action_handler,
)
from .webhook import (
    DLPWebhookClient,
    DLPAlert,
    create_webhook_alert_callback,
)

__all__ = [
    # Patterns
    "PatternRegistry",
    "DLPMatch",
    "MatchType",
    "CompiledPattern",
    # Scanner
    "ContentScanner",
    "ScanResult",
    "DLPBlockedException",
    # Actions
    "DLPActionHandler",
    "ActionResult",
    "create_action_handler",
    # Webhook
    "DLPWebhookClient",
    "DLPAlert",
    "create_webhook_alert_callback",
]
