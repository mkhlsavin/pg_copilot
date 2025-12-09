"""
Logging Middleware Module.

Provides request/response logging middleware for FastAPI.
"""

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.logging.request_logger import get_request_logger
from src.api.logging.audit_logger import get_audit_logger, AuditAction


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs request details, response status, and timing information.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        logger = get_request_logger()

        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store request ID in state for later use
        request.state.request_id = request_id

        # Get user ID if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = str(request.state.user.id)

        # Get client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Get request body preview for POST/PUT requests
        body_preview = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                body_preview = body.decode("utf-8", errors="replace")[:500]
                # Reset body for downstream handlers
                request._body = body
            except Exception:
                pass

        # Log request
        logger.log_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            body_preview=body_preview,
        )

        # Process request and measure time
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Get response size
            response_size = None
            if hasattr(response, "body"):
                response_size = len(response.body)
            elif "content-length" in response.headers:
                response_size = int(response.headers["content-length"])

            # Log response
            logger.log_response(
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
                response_size=response_size,
                path=request.url.path,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.log_error(
                request_id=request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                path=request.url.path,
            )

            raise

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security audit logging.

    Logs sensitive operations and security events.
    """

    # Paths that should be audit logged
    AUDIT_PATHS = {
        "/api/v1/auth/": ["POST", "DELETE"],
        "/api/v1/review/": ["POST"],
        "/api/v1/query/": ["POST"],
        "/api/v1/sessions/": ["POST", "DELETE"],
        "/api/v1/api-keys/": ["POST", "DELETE"],
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and log audit events.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        audit_logger = get_audit_logger()

        # Check if this path should be audited
        should_audit = False
        for path_prefix, methods in self.AUDIT_PATHS.items():
            if request.url.path.startswith(path_prefix):
                if request.method in methods:
                    should_audit = True
                    break

        if not should_audit:
            return await call_next(request)

        # Get request details
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        user_id = None
        if hasattr(request.state, "user"):
            user_id = str(request.state.user.id)

        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Process request
        response = await call_next(request)

        # Log audit event based on path
        self._log_audit_event(
            audit_logger=audit_logger,
            path=request.url.path,
            method=request.method,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=response.status_code,
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    def _log_audit_event(
        self,
        audit_logger,
        path: str,
        method: str,
        user_id: str,
        ip_address: str,
        user_agent: str,
        status_code: int,
    ) -> None:
        """Log appropriate audit event based on path."""
        success = 200 <= status_code < 300

        # Determine audit action based on path
        if "/auth/token" in path and method == "POST":
            if success:
                audit_logger.log_auth_success(
                    user_id=user_id or "unknown",
                    method="password",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            else:
                audit_logger.log_auth_failure(
                    identifier="unknown",
                    reason=f"HTTP {status_code}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        elif "/auth/logout" in path:
            audit_logger.log(
                action=AuditAction.AUTH_LOGOUT,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
            )

        elif "/review/" in path:
            audit_logger.log_sensitive_operation(
                user_id=user_id or "unknown",
                operation="review",
                resource=path,
                ip_address=ip_address,
            )

        elif "/query/" in path:
            audit_logger.log_sensitive_operation(
                user_id=user_id or "unknown",
                operation="query",
                resource=path,
                ip_address=ip_address,
            )

        elif "/sessions/" in path:
            action = (
                AuditAction.SESSION_CREATED
                if method == "POST"
                else AuditAction.SESSION_DELETED
            )
            audit_logger.log(
                action=action,
                user_id=user_id,
                resource=path,
                ip_address=ip_address,
                success=success,
            )

        elif "/api-keys/" in path:
            action = (
                AuditAction.API_KEY_CREATED
                if method == "POST"
                else AuditAction.API_KEY_DELETED
            )
            audit_logger.log(
                action=action,
                user_id=user_id,
                resource=path,
                ip_address=ip_address,
                success=success,
            )
