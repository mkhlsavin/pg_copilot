"""
Pydantic models for Lead API.

Defines request/response models for lead management.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class TeamSize(str, Enum):
    """Team size options matching the CTA form."""

    SMALL = "1-10"
    MEDIUM = "11-50"
    LARGE = "51-200"
    ENTERPRISE = "200+"


class ProgrammingLanguage(str, Enum):
    """Programming language options matching the CTA form."""

    C_CPP = "c-cpp"
    JAVA = "java"
    PYTHON = "python"
    GO = "go"
    JAVASCRIPT = "javascript"
    CSHARP = "csharp"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Lead processing status."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DEMO_SCHEDULED = "demo_scheduled"
    CONVERTED = "converted"
    CLOSED = "closed"


class LeadCreateRequest(BaseModel):
    """Request model for creating a new lead from CTA form."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Contact name",
        examples=["Иван Петров"],
    )
    email: EmailStr = Field(
        ...,
        description="Corporate email address",
        examples=["ivan@company.ru"],
    )
    company: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Company name",
        examples=["ООО Технологии"],
    )
    position: Optional[str] = Field(
        None,
        max_length=100,
        description="Job position/title",
        examples=["CTO", "Lead Developer"],
    )
    team_size: Optional[TeamSize] = Field(
        None,
        description="Development team size",
    )
    language: Optional[ProgrammingLanguage] = Field(
        None,
        description="Primary codebase programming language",
    )


class LeadUpdateRequest(BaseModel):
    """Request model for updating lead status/notes."""

    status: Optional[LeadStatus] = Field(None, description="Lead status")
    notes: Optional[str] = Field(None, max_length=2000, description="Admin notes")


class LeadResponse(BaseModel):
    """Response model for lead data."""

    id: UUID
    name: str
    email: str
    company: str
    position: Optional[str] = None
    team_size: Optional[str] = None
    language: Optional[str] = None
    status: LeadStatus
    source: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("ip_address", mode="before")
    @classmethod
    def convert_ip_to_str(cls, v):
        """Convert IPv4Address to string."""
        if v is None:
            return None
        return str(v)


class LeadListResponse(BaseModel):
    """Response model for paginated lead list."""

    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadFilters(BaseModel):
    """Query filters for lead listing."""

    status: Optional[LeadStatus] = None
    company: Optional[str] = None
    language: Optional[ProgrammingLanguage] = None
    team_size: Optional[TeamSize] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    search: Optional[str] = Field(None, description="Search in name, email, company")


class LeadCreateResponse(BaseModel):
    """Response model for successful lead creation."""

    id: UUID
    message: str = "Lead created successfully"
