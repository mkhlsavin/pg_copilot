"""
Rate Limiter Module.

Provides rate limiting using slowapi with configurable storage.
"""

import logging
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.config import get_settings, get_rate_limit_config

logger = logging.getLogger(__name__)

# Global limiter instance
_limiter: Optional[Limiter] = None


def get_key_func(request: Request) -> str:
    """
    Get rate limit key for a request.

    Uses API key or user ID if authenticated, otherwise IP address.

    Args:
        request: FastAPI request

    Returns:
        Rate limit key string
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use prefix only (first 12 chars)
        return f"apikey:{api_key[:12]}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_limiter() -> Limiter:
    """
    Get or create the rate limiter instance.

    Returns:
        Configured Limiter instance
    """
    global _limiter

    if _limiter is None:
        config = get_rate_limit_config()

        if not config.enabled:
            # Create a no-op limiter
            _limiter = Limiter(
                key_func=get_key_func,
                enabled=False,
            )
        else:
            _limiter = Limiter(
                key_func=get_key_func,
                default_limits=config.default_limits,
                storage_uri=config.storage if config.storage != "memory" else "memory://",
                strategy="fixed-window",
            )

        logger.info(
            f"Rate limiter initialized: enabled={config.enabled}, "
            f"storage={config.storage}, limits={config.default_limits}"
        )

    return _limiter


# Global limiter instance for decorator usage
limiter = get_limiter()


# Decorator helpers for common rate limits
def limit_heavy_operation(limit: str = "10/minute"):
    """
    Decorator for heavy operations like patch review.

    Args:
        limit: Rate limit string

    Returns:
        Limiter decorator
    """
    return get_limiter().limit(limit)


def limit_standard_operation(limit: str = "60/minute"):
    """
    Decorator for standard operations like chat.

    Args:
        limit: Rate limit string

    Returns:
        Limiter decorator
    """
    return get_limiter().limit(limit)


def limit_light_operation(limit: str = "200/minute"):
    """
    Decorator for light operations like health checks.

    Args:
        limit: Rate limit string

    Returns:
        Limiter decorator
    """
    return get_limiter().limit(limit)


# Re-export RateLimitExceeded for convenience
__all__ = ["limiter", "get_limiter", "RateLimitExceeded", "get_key_func"]
