"""
Session Models.

Pydantic models for session and history requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Session Models
class SessionCreate(BaseModel):
    """Request to create session."""

    metadata: Optional[Dict[str, Any]] = None


class SessionUpdate(BaseModel):
    """Request to update session."""

    current_scenario: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionResponse(BaseModel):
    """Response with session info."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    current_scenario: Optional[str]
    metadata: Dict[str, Any] = {}


class SessionSummary(BaseModel):
    """Summary of a session."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    current_scenario: Optional[str]
    turn_count: int
    metadata: Dict[str, Any] = {}


class SessionListResponse(BaseModel):
    """Response with list of sessions."""

    sessions: List[SessionSummary]
    total: int
    limit: int
    offset: int


# Dialogue Turn Models
class DialogueTurnResponse(BaseModel):
    """Response with dialogue turn info."""

    id: int
    role: str
    content: str
    timestamp: datetime
    scenario_id: Optional[str]
    metadata: Dict[str, Any] = {}


class HistoryResponse(BaseModel):
    """Response with dialogue history."""

    session_id: UUID
    turns: List[DialogueTurnResponse]
    total: int
    limit: int
    offset: int


class ExportRequest(BaseModel):
    """Request to export session."""

    format: str = Field(default="json", pattern="^(json|markdown)$")


# Job Models
class JobCreate(BaseModel):
    """Request to create background job."""

    job_type: str
    params: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Response with job info."""

    id: UUID
    job_type: str
    status: str
    progress: int
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Response with list of jobs."""

    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int
