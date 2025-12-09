"""
Rate Limiting Middleware Module.

Provides rate limiting middleware for FastAPI.
"""

import logging
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.api.rate_limit.limiter import get_limiter, RateLimitExceeded
from src.api.logging.audit_logger import get_audit_logger

logger = logging.getLogger("api.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.

    Applies rate limits based on client IP or API key.
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and apply rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        limiter = get_limiter()

        # Check if rate limiting is enabled
        if not limiter.enabled:
            return await call_next(request)

        # Check if path is exempt
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Get rate limit key (IP or API key)
        key = self._get_rate_limit_key(request)

        # Get limit for this endpoint
        limit = self._get_endpoint_limit(request.url.path)

        try:
            # Check rate limit
            allowed, remaining, reset_time = await limiter.check_limit(key, limit)

            if not allowed:
                # Log rate limit exceeded
                audit_logger = get_audit_logger()
                audit_logger.log_rate_limit_exceeded(
                    identifier=key,
                    limit=limit,
                    ip_address=self._get_client_ip(request),
                )

                logger.warning(f"Rate limit exceeded for {key}: {limit}")

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again in {reset_time} seconds.",
                        "retry_after": reset_time,
                    },
                    headers={
                        "Retry-After": str(reset_time),
                        "X-RateLimit-Limit": str(limiter.get_limit_value(limit)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                    },
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limiter.get_limit_value(limit))
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

            return response

        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": str(e),
                },
                headers={"Retry-After": "60"},
            )

    def _is_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from rate limiting.

        Args:
            path: Request path

        Returns:
            True if exempt
        """
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True
        return False

    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Get the key for rate limiting.

        Uses API key if present, otherwise uses IP address.

        Args:
            request: HTTP request

        Returns:
            Rate limit key
        """
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Use prefix of API key for rate limiting
            return f"api_key:{api_key[:8]}"

        # Check for authenticated user
        if hasattr(request.state, "user"):
            return f"user:{request.state.user.id}"

        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    def _get_endpoint_limit(self, path: str) -> str:
        """
        Get rate limit for specific endpoint.

        Args:
            path: Request path

        Returns:
            Rate limit string (e.g., "100/minute")
        """
        limiter = get_limiter()

        # Check endpoint-specific limits
        for pattern, limit in limiter.endpoint_limits.items():
            if self._match_pattern(path, pattern):
                return limit

        # Return default limit
        return limiter.default_limit

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if path matches pattern.

        Supports simple wildcard matching with *.

        Args:
            path: Request path
            pattern: Pattern to match

        Returns:
            True if matches
        """
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        return path == pattern


class SlowAPIMiddleware:
    """
    Alternative middleware using slowapi library.

    Use this if slowapi is installed for more advanced rate limiting.
    """

    def __init__(self, app):
        """
        Initialize slowapi middleware.

        Args:
            app: FastAPI application
        """
        self.app = app

        try:
            from slowapi import Limiter, _rate_limit_exceeded_handler
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded as SlowAPIRateLimitExceeded

            self.limiter = Limiter(key_func=get_remote_address)
            self.rate_limit_exceeded_handler = _rate_limit_exceeded_handler
            self.RateLimitExceeded = SlowAPIRateLimitExceeded
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("slowapi not installed. Using built-in rate limiter.")

    def setup(self):
        """Setup slowapi with the application."""
        if not self.available:
            return

        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(
            self.RateLimitExceeded,
            self.rate_limit_exceeded_handler,
        )
