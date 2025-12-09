"""
Request Logger Module.

Provides structured logging for HTTP requests and responses.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from src.api.config import LoggingConfig

logger = logging.getLogger("api.request")


class RequestLogger:
    """
    Structured request/response logger.

    Logs requests and responses in a structured JSON format for easy parsing.
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """
        Initialize the request logger.

        Args:
            config: Logging configuration
        """
        self.config = config or LoggingConfig()
        self._exclude_paths = set(self.config.exclude_paths)

    def should_log(self, path: str) -> bool:
        """
        Check if a path should be logged.

        Args:
            path: Request path

        Returns:
            True if should log
        """
        if not self.config.request_logging:
            return False

        # Check exclusions
        for excluded in self._exclude_paths:
            if path.startswith(excluded.rstrip("*")):
                return False

        return True

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: str = "",
        user_agent: Optional[str] = None,
        body_preview: Optional[str] = None,
    ) -> None:
        """
        Log an incoming request.

        Args:
            request_id: Unique request ID
            method: HTTP method
            path: Request path
            query_params: Query parameters
            user_id: Authenticated user ID
            ip_address: Client IP address
            user_agent: Client user agent
            body_preview: First N chars of request body
        """
        if not self.should_log(path):
            return

        log_data = {
            "event": "request",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "path": path,
            "query_params": query_params,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        if self.config.log_request_body and body_preview:
            # Truncate body preview
            if len(body_preview) > self.config.max_body_log_size:
                body_preview = body_preview[: self.config.max_body_log_size] + "..."
            log_data["body_preview"] = body_preview

        logger.info(json.dumps(log_data))

    def log_response(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        response_size: Optional[int] = None,
        path: str = "",
    ) -> None:
        """
        Log a response.

        Args:
            request_id: Unique request ID
            status_code: HTTP status code
            duration_ms: Processing time in milliseconds
            response_size: Response body size in bytes
            path: Request path (for filtering)
        """
        if not self.should_log(path):
            return

        log_data = {
            "event": "response",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "response_size": response_size,
        }

        # Use appropriate log level based on status code
        if status_code >= 500:
            logger.error(json.dumps(log_data))
        elif status_code >= 400:
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))

    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        traceback: Optional[str] = None,
        path: str = "",
    ) -> None:
        """
        Log an error.

        Args:
            request_id: Unique request ID
            error_type: Error type/class name
            error_message: Error message
            traceback: Full traceback string
            path: Request path
        """
        log_data = {
            "event": "error",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "path": path,
        }

        if traceback:
            log_data["traceback"] = traceback

        logger.error(json.dumps(log_data))


# Global instance
_request_logger: Optional[RequestLogger] = None


def get_request_logger() -> RequestLogger:
    """Get the global request logger instance."""
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger()
    return _request_logger


class RequestLoggingContext:
    """
    Context manager for request logging.

    Usage:
        async with RequestLoggingContext(request) as ctx:
            # Process request
            response = await handler(request)
        # Logging happens automatically
    """

    def __init__(
        self,
        request_id: str,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        ip_address: str = "",
    ):
        self.request_id = request_id
        self.method = method
        self.path = path
        self.user_id = user_id
        self.ip_address = ip_address
        self.start_time = 0.0
        self.logger = get_request_logger()

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log_request(
            request_id=self.request_id,
            method=self.method,
            path=self.path,
            user_id=self.user_id,
            ip_address=self.ip_address,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.log_error(
                request_id=self.request_id,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                path=self.path,
            )

        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def log_response(self, status_code: int, response_size: Optional[int] = None):
        """Log the response after processing."""
        duration_ms = (time.time() - self.start_time) * 1000
        self.logger.log_response(
            request_id=self.request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            response_size=response_size,
            path=self.path,
        )
