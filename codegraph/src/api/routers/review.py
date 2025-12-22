"""
Code Review Router.

Provides endpoints for patch review, PR review, and MR review.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.dependencies import get_current_active_user
from src.api.services.review_service import get_review_service

logger = logging.getLogger("api.routers.review")
router = APIRouter()


# Enums
class Recommendation(str, Enum):
    """Review recommendation types."""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"
    BLOCK = "BLOCK"


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Finding categories."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"
    ARCHITECTURE = "architecture"
    STYLE = "style"


# Request/Response Models
class SourceLocation(BaseModel):
    """Source code location."""
    file: str
    line_start: int
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None


class Finding(BaseModel):
    """Review finding model."""
    category: str
    severity: str
    location: Optional[SourceLocation] = None
    message: str
    suggested_fix: Optional[str] = None
    evidence: Optional[str] = None


class DODItem(BaseModel):
    """Definition of Done item."""
    description: str
    satisfied: bool
    evidence: Optional[str] = None


class PatchReviewRequest(BaseModel):
    """Patch review request model."""
    patch_content: str = Field(..., min_length=1, description="Git diff content")
    task_description: Optional[str] = Field(default=None, description="PR/task description")
    dod_items: Optional[List[str]] = Field(default=None, description="Definition of Done items")
    output_format: str = Field(default="json", pattern="^(json|markdown|yaml)$")


class GitHubPRReviewRequest(BaseModel):
    """GitHub PR review request model."""
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    pr_number: int = Field(..., gt=0)
    task_description: Optional[str] = None
    dod_items: Optional[List[str]] = None


class GitLabMRReviewRequest(BaseModel):
    """GitLab MR review request model."""
    project_id: str = Field(..., min_length=1)
    mr_iid: int = Field(..., gt=0)
    gitlab_url: str = Field(default="https://gitlab.com")
    task_description: Optional[str] = None
    dod_items: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    """Review response model."""
    recommendation: str
    score: float = Field(ge=0, le=100)
    findings: List[Finding] = Field(default_factory=list)
    dod_validation: Optional[List[DODItem]] = None
    summary: str
    processing_time_ms: float
    request_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _convert_service_finding_to_response(finding: Dict[str, Any]) -> Finding:
    """Convert service finding to response model."""
    location = None
    if finding.get("file_path"):
        location = SourceLocation(
            file=finding["file_path"],
            line_start=finding.get("line_start", 1),
            line_end=finding.get("line_end"),
        )

    return Finding(
        category=finding.get("category", "general"),
        severity=finding.get("severity", "info"),
        location=location,
        message=finding.get("description", ""),
        suggested_fix=finding.get("suggestion"),
        evidence=finding.get("code_snippet"),
    )


# Endpoints
@router.post(
    "/patch",
    response_model=ReviewResponse,
    summary="Review patch",
    description="Review a git diff/patch for issues and best practices.",
)
async def review_patch(
    request: PatchReviewRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
) -> ReviewResponse:
    """
    Review a git patch/diff.

    Args:
        request: Patch content and options
        req: FastAPI request
        current_user: Authenticated user

    Returns:
        Review results with findings and recommendation
    """
    request_id = getattr(req.state, "request_id", "unknown")

    logger.info(f"Patch review requested by {current_user.username}")

    try:
        service = get_review_service()
        result = await service.review_patch(
            patch_content=request.patch_content,
            task_description=request.task_description,
            dod_items=request.dod_items,
            output_format=request.output_format,
        )

        # Convert findings
        findings = [
            _convert_service_finding_to_response(f.model_dump())
            for f in result.findings
        ]

        # Convert DoD compliance to DODItem list
        dod_validation = None
        if result.dod_compliance:
            dod_validation = [
                DODItem(
                    description=item,
                    satisfied=satisfied,
                    evidence=None,
                )
                for item, satisfied in result.dod_compliance.items()
            ]

        logger.info(
            f"Patch review completed: {result.recommendation}, "
            f"{len(findings)} findings, score={result.score:.2f}"
        )

        return ReviewResponse(
            recommendation=result.recommendation,
            score=result.score * 100,  # Convert to 0-100 scale
            findings=findings,
            dod_validation=dod_validation,
            summary=result.summary,
            processing_time_ms=result.processing_time_ms,
            request_id=request_id,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"Patch review error: {e}")
        return ReviewResponse(
            recommendation="COMMENT",
            score=0.0,
            findings=[
                Finding(
                    category="error",
                    severity="critical",
                    message=f"Review failed: {str(e)}",
                )
            ],
            summary="Review could not be completed due to an error.",
            processing_time_ms=0.0,
            request_id=request_id,
        )


@router.post(
    "/pr",
    response_model=ReviewResponse,
    summary="Review GitHub PR",
    description="Review a GitHub Pull Request.",
)
async def review_github_pr(
    request: GitHubPRReviewRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
) -> ReviewResponse:
    """
    Review a GitHub Pull Request.

    Args:
        request: GitHub PR information
        req: FastAPI request
        current_user: Authenticated user
        x_github_token: GitHub access token from header

    Returns:
        Review results
    """
    request_id = getattr(req.state, "request_id", "unknown")

    if not x_github_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-GitHub-Token header is required for GitHub PR review",
        )

    logger.info(
        f"GitHub PR review requested by {current_user.username}: "
        f"{request.owner}/{request.repo}#{request.pr_number}"
    )

    try:
        service = get_review_service()
        result = await service.review_github_pr(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            github_token=x_github_token,
            task_description=request.task_description,
            dod_items=request.dod_items,
        )

        # Convert findings
        findings = [
            _convert_service_finding_to_response(f.model_dump())
            for f in result.findings
        ]

        dod_validation = None
        if result.dod_compliance:
            dod_validation = [
                DODItem(description=item, satisfied=satisfied)
                for item, satisfied in result.dod_compliance.items()
            ]

        logger.info(
            f"GitHub PR review completed: {result.recommendation}, "
            f"{len(findings)} findings"
        )

        return ReviewResponse(
            recommendation=result.recommendation,
            score=result.score * 100,
            findings=findings,
            dod_validation=dod_validation,
            summary=result.summary,
            processing_time_ms=result.processing_time_ms,
            request_id=request_id,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"GitHub PR review error: {e}")
        return ReviewResponse(
            recommendation="COMMENT",
            score=0.0,
            findings=[
                Finding(
                    category="error",
                    severity="critical",
                    message=f"GitHub PR review failed: {str(e)}",
                )
            ],
            summary="Review could not be completed.",
            processing_time_ms=0.0,
            request_id=request_id,
        )


@router.post(
    "/mr",
    response_model=ReviewResponse,
    summary="Review GitLab MR",
    description="Review a GitLab Merge Request.",
)
async def review_gitlab_mr(
    request: GitLabMRReviewRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    x_gitlab_token: Optional[str] = Header(None, alias="X-GitLab-Token"),
) -> ReviewResponse:
    """
    Review a GitLab Merge Request.

    Args:
        request: GitLab MR information
        req: FastAPI request
        current_user: Authenticated user
        x_gitlab_token: GitLab access token from header

    Returns:
        Review results
    """
    request_id = getattr(req.state, "request_id", "unknown")

    if not x_gitlab_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-GitLab-Token header is required for GitLab MR review",
        )

    logger.info(
        f"GitLab MR review requested by {current_user.username}: "
        f"{request.project_id}!{request.mr_iid}"
    )

    try:
        service = get_review_service()
        result = await service.review_gitlab_mr(
            project_id=request.project_id,
            mr_iid=request.mr_iid,
            gitlab_token=x_gitlab_token,
            gitlab_url=request.gitlab_url,
            task_description=request.task_description,
            dod_items=request.dod_items,
        )

        # Convert findings
        findings = [
            _convert_service_finding_to_response(f.model_dump())
            for f in result.findings
        ]

        dod_validation = None
        if result.dod_compliance:
            dod_validation = [
                DODItem(description=item, satisfied=satisfied)
                for item, satisfied in result.dod_compliance.items()
            ]

        logger.info(
            f"GitLab MR review completed: {result.recommendation}, "
            f"{len(findings)} findings"
        )

        return ReviewResponse(
            recommendation=result.recommendation,
            score=result.score * 100,
            findings=findings,
            dod_validation=dod_validation,
            summary=result.summary,
            processing_time_ms=result.processing_time_ms,
            request_id=request_id,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"GitLab MR review error: {e}")
        return ReviewResponse(
            recommendation="COMMENT",
            score=0.0,
            findings=[
                Finding(
                    category="error",
                    severity="critical",
                    message=f"GitLab MR review failed: {str(e)}",
                )
            ],
            summary="Review could not be completed.",
            processing_time_ms=0.0,
            request_id=request_id,
        )
