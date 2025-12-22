"""
Chat Models.

Pydantic models for chat requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Evidence from code analysis."""

    type: str
    content: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 1.0


class ChatRequest(BaseModel):
    """Request for chat query."""

    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    scenario_id: Optional[str] = None
    language: str = Field(default="en", max_length=10)


class ChatResponse(BaseModel):
    """Response from chat query."""

    answer: str
    scenario_id: str
    confidence: float
    evidence: List[Evidence] = []
    session_id: Optional[str] = None
    request_id: str
    processing_time_ms: float


class ChatStreamEvent(BaseModel):
    """Server-Sent Event for streaming chat."""

    event: str  # scenario, chunk, done, error
    data: Dict[str, Any]


# Scenario Models
class ScenarioInfo(BaseModel):
    """Information about a scenario."""

    id: str
    name: str
    description: str
    keywords: List[str] = []
    examples: List[str] = []


class ScenarioListResponse(BaseModel):
    """Response with list of scenarios."""

    scenarios: List[ScenarioInfo]
    total: int


class ScenarioQueryRequest(BaseModel):
    """Request for scenario-specific query."""

    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    language: str = Field(default="en", max_length=10)
