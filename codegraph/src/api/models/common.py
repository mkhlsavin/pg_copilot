"""
Common Pydantic Models.

Provides shared models for API responses, pagination, and errors.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail model."""

    loc: List[str] = Field(default_factory=list, description="Error location path")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Detailed error information")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Request validation failed",
                "details": [
                    {"loc": ["body", "query"], "msg": "field required", "type": "value_error.missing"}
                ],
                "request_id": "req_abc123",
                "timestamp": "2025-01-01T12:00:00Z",
            }
        }


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response model."""

    success: bool = Field(default=True, description="Operation success status")
    data: Optional[T] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Optional message")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "example"},
                "message": "Operation completed successfully",
                "request_id": "req_abc123",
            }
        }


class PaginationParams(BaseModel):
    """Pagination parameters model."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata model."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""

    items: List[T] = Field(default_factory=list, description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")

    @classmethod
    def create(
        cls,
        items: List[T],
        total_items: int,
        page: int,
        page_size: int,
        request_id: Optional[str] = None,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

        return cls(
            items=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
            request_id=request_id,
        )


class HealthStatus(BaseModel):
    """Health check status model."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    components: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Component health statuses"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "timestamp": "2025-01-01T12:00:00Z",
                "components": {
                    "database": {"status": "healthy", "latency_ms": 2.5},
                    "llm": {"status": "healthy", "provider": "gigachat"},
                    "joern": {"status": "healthy", "server": "localhost:8080"},
                },
            }
        }


class RequestInfo(BaseModel):
    """Request information model for logging."""

    request_id: str = Field(..., description="Unique request ID")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")


class MetricsResponse(BaseModel):
    """Metrics response model."""

    total_requests: int = Field(..., description="Total requests processed")
    active_sessions: int = Field(..., description="Active chat sessions")
    active_jobs: int = Field(..., description="Running background jobs")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    avg_response_time_ms: float = Field(..., description="Average response time in ms")
    scenarios_usage: Dict[str, int] = Field(
        default_factory=dict, description="Usage count per scenario"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 15000,
                "active_sessions": 42,
                "active_jobs": 3,
                "cache_hit_rate": 0.75,
                "avg_response_time_ms": 250.5,
                "scenarios_usage": {
                    "security": 500,
                    "code_review": 300,
                    "performance": 200,
                },
            }
        }
