"""
Leads API router.

Provides endpoints for lead management.
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.connection import get_db
from src.models.lead import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadStatus,
    LeadUpdateRequest,
    ProgrammingLanguage,
    TeamSize,
)
from src.services.export_service import ExportService
from src.services.lead_service import LeadService

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def get_lead_key_func(request: Request) -> str:
    """Get rate limit key for lead creation."""
    return f"leads_ip:{get_remote_address(request)}"


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Verify API key for admin endpoints.

    Args:
        x_api_key: API key from header

    Returns:
        Validated API key

    Raises:
        HTTPException 401 if invalid
    """
    settings = get_settings()

    if not settings.leads_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    if not x_api_key or x_api_key != settings.leads_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# =============================================================================
# Public Endpoints (rate-limited)
# =============================================================================


@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create Lead",
    description="Submit a new lead from CTA form. Rate limited to 10 requests per minute per IP.",
    responses={
        201: {"description": "Lead created successfully"},
        429: {"description": "Rate limit exceeded"},
        422: {"description": "Validation error"},
    },
)
@limiter.limit("10/minute", key_func=get_lead_key_func)
async def create_lead(
    data: LeadCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create a new lead from CTA form submission.

    This is a public endpoint with IP-based rate limiting.
    Sends notifications to configured channels (Telegram, Email).

    Args:
        data: Lead creation data
        request: FastAPI request object
        session: Database session

    Returns:
        Created lead ID and success message
    """
    # Get client info
    ip_address = get_remote_address(request)
    user_agent = request.headers.get("user-agent", "")[:500]  # Limit length

    service = LeadService(session)
    lead = await service.create_lead(
        data=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        f"Lead created: id={lead.id}, email={lead.email}, "
        f"company={lead.company}, ip={ip_address}"
    )

    return {
        "id": str(lead.id),
        "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.",
    }


# =============================================================================
# Admin Endpoints (API key required)
# =============================================================================


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List Leads",
    description="Get paginated list of leads with optional filters. Requires API key.",
    dependencies=[Depends(verify_api_key)],
)
async def list_leads(
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[LeadStatus] = Query(None, description="Filter by status"),
    company: Optional[str] = Query(None, description="Filter by company (partial match)"),
    language: Optional[ProgrammingLanguage] = Query(None, description="Filter by language"),
    team_size: Optional[TeamSize] = Query(None, description="Filter by team size"),
    created_from: Optional[datetime] = Query(None, description="Filter from date"),
    created_to: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search in name, email, company"),
) -> LeadListResponse:
    """
    List leads with filters and pagination.

    Args:
        session: Database session
        page: Page number (1-indexed)
        page_size: Items per page
        status: Filter by status
        company: Filter by company name
        language: Filter by programming language
        team_size: Filter by team size
        created_from: Filter by created date (from)
        created_to: Filter by created date (to)
        search: Search term

    Returns:
        Paginated list of leads
    """
    service = LeadService(session)
    leads, total = await service.list_leads(
        page=page,
        page_size=page_size,
        status=status.value if status else None,
        company=company,
        language=language.value if language else None,
        team_size=team_size.value if team_size else None,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )

    pages = math.ceil(total / page_size) if total > 0 else 1

    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get Statistics",
    description="Get lead statistics. Requires API key.",
    dependencies=[Depends(verify_api_key)],
)
async def get_statistics(
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get lead statistics.

    Args:
        session: Database session

    Returns:
        Statistics dictionary
    """
    service = LeadService(session)
    return await service.get_statistics()


@router.get(
    "/export",
    summary="Export Leads",
    description="Export leads to CSV file. Requires API key.",
    dependencies=[Depends(verify_api_key)],
    response_class=StreamingResponse,
)
async def export_leads(
    session: AsyncSession = Depends(get_db),
    status: Optional[LeadStatus] = Query(None, description="Filter by status"),
    created_from: Optional[datetime] = Query(None, description="Filter from date"),
    created_to: Optional[datetime] = Query(None, description="Filter to date"),
) -> StreamingResponse:
    """
    Export leads to CSV file.

    Args:
        session: Database session
        status: Filter by status
        created_from: Filter by created date (from)
        created_to: Filter by created date (to)

    Returns:
        CSV file as streaming response
    """
    service = LeadService(session)
    leads, _ = await service.list_leads(
        page=1,
        page_size=10000,  # Max export size
        status=status.value if status else None,
        created_from=created_from,
        created_to=created_to,
    )

    csv_content = ExportService.export_to_csv(leads)
    filename = ExportService.generate_filename(
        created_from=created_from,
        created_to=created_to,
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get Lead",
    description="Get single lead by ID. Requires API key.",
    dependencies=[Depends(verify_api_key)],
)
async def get_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """
    Get lead by ID.

    Args:
        lead_id: Lead UUID
        session: Database session

    Returns:
        Lead details

    Raises:
        HTTPException 404 if not found
    """
    service = LeadService(session)
    lead = await service.get_lead(lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    return LeadResponse.model_validate(lead)


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update Lead",
    description="Update lead status/notes. Requires API key.",
    dependencies=[Depends(verify_api_key)],
)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """
    Update lead status or notes.

    Args:
        lead_id: Lead UUID
        data: Update data
        session: Database session

    Returns:
        Updated lead

    Raises:
        HTTPException 404 if not found
    """
    service = LeadService(session)
    lead = await service.update_lead(lead_id, data)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    return LeadResponse.model_validate(lead)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Lead",
    description="Delete lead by ID. Requires API key.",
    dependencies=[Depends(verify_api_key)],
)
async def delete_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete lead by ID.

    Args:
        lead_id: Lead UUID
        session: Database session

    Raises:
        HTTPException 404 if not found
    """
    service = LeadService(session)
    deleted = await service.delete_lead(lead_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )
