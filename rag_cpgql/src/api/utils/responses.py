"""
Response Utilities.

Provides helper functions for creating standardized API responses.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from fastapi import status
from fastapi.responses import JSONResponse

from src.api.models.common import (
    ErrorResponse,
    ErrorDetail,
    SuccessResponse,
    PaginatedResponse,
    PaginationMeta,
)

T = TypeVar("T")


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


def success_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Optional success message
        request_id: Request ID for tracking
        status_code: HTTP status code

    Returns:
        JSONResponse with success format
    """
    response = SuccessResponse(
        success=True,
        data=data,
        message=message,
        request_id=request_id or generate_request_id(),
    )

    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=status_code,
    )


def error_response(
    error: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error: Error type/code
        message: Human-readable error message
        details: Optional list of error details
        request_id: Request ID for tracking
        status_code: HTTP status code

    Returns:
        JSONResponse with error format
    """
    error_details = None
    if details:
        error_details = [
            ErrorDetail(
                loc=d.get("loc", []),
                msg=d.get("msg", ""),
                type=d.get("type", "unknown"),
            )
            for d in details
        ]

    response = ErrorResponse(
        error=error,
        message=message,
        details=error_details,
        request_id=request_id or generate_request_id(),
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=status_code,
    )


def paginated_response(
    items: List[Any],
    total_items: int,
    page: int,
    page_size: int,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a paginated response dictionary.

    Args:
        items: List of items for current page
        total_items: Total count of all items
        page: Current page number
        page_size: Items per page
        request_id: Request ID for tracking

    Returns:
        Dictionary with paginated response format
    """
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "request_id": request_id or generate_request_id(),
    }


# Common error responses
def not_found_response(
    resource: str = "Resource",
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 404 Not Found response."""
    return error_response(
        error="not_found",
        message=f"{resource} not found",
        request_id=request_id,
        status_code=status.HTTP_404_NOT_FOUND,
    )


def unauthorized_response(
    message: str = "Authentication required",
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 401 Unauthorized response."""
    return error_response(
        error="unauthorized",
        message=message,
        request_id=request_id,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def forbidden_response(
    message: str = "Access denied",
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 403 Forbidden response."""
    return error_response(
        error="forbidden",
        message=message,
        request_id=request_id,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def validation_error_response(
    details: List[Dict[str, Any]],
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 422 Validation Error response."""
    return error_response(
        error="validation_error",
        message="Request validation failed",
        details=details,
        request_id=request_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def rate_limit_response(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 429 Rate Limit response."""
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(
        content={
            "error": "rate_limit_exceeded",
            "message": message,
            "request_id": request_id or generate_request_id(),
            "timestamp": datetime.utcnow().isoformat(),
        },
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers=headers,
    )


def internal_error_response(
    message: str = "Internal server error",
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 500 Internal Server Error response."""
    return error_response(
        error="internal_error",
        message=message,
        request_id=request_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def service_unavailable_response(
    message: str = "Service temporarily unavailable",
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Create a 503 Service Unavailable response."""
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(
        content={
            "error": "service_unavailable",
            "message": message,
            "request_id": request_id or generate_request_id(),
            "timestamp": datetime.utcnow().isoformat(),
        },
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers=headers,
    )
