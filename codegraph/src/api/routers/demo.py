"""
Demo Router Module.

Provides a public demo endpoint for the landing page.
No authentication required - uses IP-based rate limiting.
"""

import logging
import time

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address

from src.api.config import get_demo_config
from src.api.rate_limit.limiter import get_limiter
from src.api.services.chat_service import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = get_limiter()


class DemoRequest(BaseModel):
    """Request model for demo chat endpoint."""

    query: str = Field(..., min_length=1, max_length=500, description="User query")
    language: str = Field(default="ru", description="Response language")


class DemoResponse(BaseModel):
    """Response model for demo chat endpoint."""

    answer: str = Field(..., description="Response from the system")
    scenario_id: str = Field(default="onboarding", description="Scenario used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


def get_demo_key_func(request: Request) -> str:
    """Get rate limit key for demo endpoint - always use IP address."""
    return f"demo_ip:{get_remote_address(request)}"


@router.post(
    "/chat",
    response_model=DemoResponse,
    summary="Demo Chat",
    description="Public demo endpoint for landing page. Rate limited to 30 requests per minute per IP.",
    responses={
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Demo endpoint disabled"},
    },
)
@limiter.limit("30/minute", key_func=get_demo_key_func)
async def demo_chat(demo_request: DemoRequest, request: Request) -> DemoResponse:
    """
    Process a demo chat query with rate limiting.

    This endpoint is publicly accessible with IP-based rate limiting.
    Designed for the landing page "Try it yourself" feature.

    Rate limit: 30 requests per minute per IP (configurable via DEMO_RATE_LIMIT).

    Args:
        demo_request: Demo chat request with query and language
        request: FastAPI request object (required for rate limiting)

    Returns:
        Demo chat response with answer and processing time

    Raises:
        HTTPException 429: If rate limit exceeded
        HTTPException 503: If demo is disabled
    """
    config = get_demo_config()

    # Check if demo is enabled
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo endpoint is currently disabled",
        )

    # Validate query length
    if len(demo_request.query) > config.max_query_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query too long. Maximum length is {config.max_query_length} characters.",
        )

    start_time = time.time()

    try:
        # Get chat service and process query
        chat_service = get_chat_service()

        # Force onboarding scenario for demo
        scenario_id = "onboarding"
        if config.allowed_scenarios and scenario_id not in config.allowed_scenarios:
            scenario_id = config.allowed_scenarios[0]

        # Process query
        result = await chat_service.process_query(
            query=demo_request.query,
            scenario_id=scenario_id,
            user_id="demo_user",
            language=demo_request.language,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Demo chat processed: query_len={len(demo_request.query)}, "
            f"scenario={result.scenario_id}, time_ms={processing_time_ms:.2f}, "
            f"ip={get_remote_address(request)}"
        )

        return DemoResponse(
            answer=result.answer,
            scenario_id=result.scenario_id,
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.exception(f"Demo chat error: {e}")
        processing_time_ms = (time.time() - start_time) * 1000

        # Return a friendly error response
        return DemoResponse(
            answer="Sorry, the analysis system is temporarily unavailable. Please try again later.",
            scenario_id="error",
            processing_time_ms=processing_time_ms,
        )


@router.get(
    "/status",
    summary="Demo Status",
    description="Check if demo endpoint is enabled and view configuration.",
)
async def demo_status() -> dict:
    """
    Get demo endpoint status.

    Returns:
        Status information including enabled state and rate limit.
    """
    config = get_demo_config()
    return {
        "enabled": config.enabled,
        "rate_limit": config.rate_limit,
        "max_query_length": config.max_query_length,
        "allowed_scenarios": config.allowed_scenarios,
    }
