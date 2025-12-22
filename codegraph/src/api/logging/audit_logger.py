"""
Audit Logger Module.

Provides security audit logging for sensitive operations.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("api.audit")


class AuditAction(str, Enum):
    """Audit action types."""

    # Authentication
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_TOKEN_REVOKED = "auth.token.revoked"

    # OAuth
    OAUTH_LOGIN_START = "oauth.login.start"
    OAUTH_LOGIN_SUCCESS = "oauth.login.success"
    OAUTH_LOGIN_FAILURE = "oauth.login.failure"

    # LDAP
    LDAP_LOGIN_SUCCESS = "ldap.login.success"
    LDAP_LOGIN_FAILURE = "ldap.login.failure"

    # API Keys
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    API_KEY_DELETED = "api_key.deleted"
    API_KEY_USED = "api_key.used"

    # Users
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role.changed"

    # Sessions
    SESSION_CREATED = "session.created"
    SESSION_DELETED = "session.deleted"

    # Security
    PERMISSION_DENIED = "security.permission.denied"
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    INVALID_TOKEN = "security.token.invalid"
    SUSPICIOUS_ACTIVITY = "security.suspicious"

    # Sensitive operations
    QUERY_EXECUTED = "query.executed"
    REVIEW_STARTED = "review.started"
    REVIEW_COMPLETED = "review.completed"
    EXPORT_REQUESTED = "export.requested"


class AuditLogger:
    """
    Security audit logger.

    Logs security-related events for compliance and monitoring.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the audit logger.

        Args:
            enabled: Whether audit logging is enabled
        """
        self.enabled = enabled

    def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """
        Log an audit event.

        Args:
            action: Audit action type
            user_id: User ID (if authenticated)
            resource: Resource being accessed
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
            success: Whether the action was successful
        """
        if not self.enabled:
            return

        log_data = {
            "event": "audit",
            "timestamp": datetime.utcnow().isoformat(),
            "action": action.value,
            "success": success,
            "user_id": user_id,
            "resource": resource,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }

        # Use appropriate log level
        if not success or action.value.startswith("security."):
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))

    # Convenience methods for common audit events

    def log_auth_success(
        self,
        user_id: str,
        method: str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log successful authentication."""
        self.log(
            action=AuditAction.AUTH_LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"method": method},
        )

    def log_auth_failure(
        self,
        identifier: str,
        reason: str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log failed authentication."""
        self.log(
            action=AuditAction.AUTH_LOGIN_FAILURE,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"identifier": identifier, "reason": reason},
            success=False,
        )

    def log_permission_denied(
        self,
        user_id: Optional[str],
        resource: str,
        action: str,
        ip_address: str,
    ) -> None:
        """Log permission denied event."""
        self.log(
            action=AuditAction.PERMISSION_DENIED,
            user_id=user_id,
            resource=resource,
            ip_address=ip_address,
            details={"attempted_action": action},
            success=False,
        )

    def log_rate_limit_exceeded(
        self,
        identifier: str,
        limit: str,
        ip_address: str,
    ) -> None:
        """Log rate limit exceeded event."""
        self.log(
            action=AuditAction.RATE_LIMIT_EXCEEDED,
            ip_address=ip_address,
            details={"identifier": identifier, "limit": limit},
            success=False,
        )

    def log_api_key_created(
        self,
        user_id: str,
        key_id: str,
        key_name: str,
        ip_address: str,
    ) -> None:
        """Log API key creation."""
        self.log(
            action=AuditAction.API_KEY_CREATED,
            user_id=user_id,
            resource=f"api_key:{key_id}",
            ip_address=ip_address,
            details={"key_name": key_name},
        )

    def log_api_key_revoked(
        self,
        user_id: str,
        key_id: str,
        ip_address: str,
    ) -> None:
        """Log API key revocation."""
        self.log(
            action=AuditAction.API_KEY_REVOKED,
            user_id=user_id,
            resource=f"api_key:{key_id}",
            ip_address=ip_address,
        )

    def log_sensitive_operation(
        self,
        user_id: str,
        operation: str,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a sensitive operation."""
        action = AuditAction.QUERY_EXECUTED
        if operation == "review":
            action = AuditAction.REVIEW_STARTED
        elif operation == "export":
            action = AuditAction.EXPORT_REQUESTED

        self.log(
            action=action,
            user_id=user_id,
            resource=resource,
            ip_address=ip_address,
            details=details,
        )


# Global instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
