"""
Review Models.

Pydantic models for code review requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Code review finding."""

    severity: str  # critical, major, minor, info
    category: str  # security, performance, style, logic, etc.
    description: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


class PatchReviewRequest(BaseModel):
    """Request for patch review."""

    patch_content: str = Field(..., min_length=1, max_length=500000)
    task_description: Optional[str] = Field(default=None, max_length=5000)
    dod_items: Optional[List[str]] = None
    output_format: str = Field(default="json", pattern="^(json|markdown|yaml)$")


class GitHubPRReviewRequest(BaseModel):
    """Request for GitHub PR review."""

    owner: str = Field(..., min_length=1, max_length=100)
    repo: str = Field(..., min_length=1, max_length=100)
    pr_number: int = Field(..., ge=1)
    task_description: Optional[str] = Field(default=None, max_length=5000)
    dod_items: Optional[List[str]] = None


class GitLabMRReviewRequest(BaseModel):
    """Request for GitLab MR review."""

    project_id: str = Field(..., min_length=1, max_length=200)
    mr_iid: int = Field(..., ge=1)
    gitlab_url: str = Field(default="https://gitlab.com")
    task_description: Optional[str] = Field(default=None, max_length=5000)
    dod_items: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    """Response from code review."""

    recommendation: str  # APPROVE, REQUEST_CHANGES, COMMENT, BLOCK
    score: float = Field(..., ge=0.0, le=1.0)
    findings: List[Finding] = []
    summary: str
    processing_time_ms: float
    dod_compliance: Optional[Dict[str, bool]] = None
    metadata: Dict[str, Any] = {}
