"""
WebSocket Message Models.

Defines message types and structures for WebSocket communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    """WebSocket message types."""

    # Chat messages
    CHAT_QUERY = "chat.query"
    CHAT_RESPONSE = "chat.response"
    CHAT_CHUNK = "chat.chunk"
    CHAT_ERROR = "chat.error"

    # Job messages
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"

    # System messages
    NOTIFICATION = "notification"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

    # Connection messages
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    AUTH_REQUIRED = "auth_required"


class WSMessage(BaseModel):
    """WebSocket message model."""

    type: WSMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        """Deserialize from JSON string."""
        return cls.model_validate_json(data)


# Specific message payloads
class ChatQueryPayload(BaseModel):
    """Chat query payload."""
    query: str
    session_id: Optional[str] = None
    scenario_id: Optional[str] = None
    language: str = "en"


class ChatResponsePayload(BaseModel):
    """Chat response payload."""
    answer: str
    scenario_id: str
    confidence: float
    session_id: str


class ChatChunkPayload(BaseModel):
    """Chat streaming chunk payload."""
    content: str
    is_final: bool = False


class JobProgressPayload(BaseModel):
    """Job progress payload."""
    job_id: str
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None


class JobCompletedPayload(BaseModel):
    """Job completed payload."""
    job_id: str
    result: Dict[str, Any] = Field(default_factory=dict)


class JobFailedPayload(BaseModel):
    """Job failed payload."""
    job_id: str
    error: str
    details: Optional[str] = None


class NotificationPayload(BaseModel):
    """Notification payload."""
    title: str
    message: str
    level: str = "info"  # info, warning, error
    action_url: Optional[str] = None


# Helper functions for creating messages
def create_chat_chunk(content: str, request_id: Optional[str] = None, is_final: bool = False) -> WSMessage:
    """Create a chat chunk message."""
    return WSMessage(
        type=WSMessageType.CHAT_CHUNK,
        payload=ChatChunkPayload(content=content, is_final=is_final).model_dump(),
        request_id=request_id,
    )


def create_chat_response(
    answer: str,
    scenario_id: str,
    confidence: float,
    session_id: str,
    request_id: Optional[str] = None,
) -> WSMessage:
    """Create a chat response message."""
    return WSMessage(
        type=WSMessageType.CHAT_RESPONSE,
        payload=ChatResponsePayload(
            answer=answer,
            scenario_id=scenario_id,
            confidence=confidence,
            session_id=session_id,
        ).model_dump(),
        request_id=request_id,
    )


def create_job_progress(job_id: str, progress: int, message: Optional[str] = None) -> WSMessage:
    """Create a job progress message."""
    return WSMessage(
        type=WSMessageType.JOB_PROGRESS,
        payload=JobProgressPayload(job_id=job_id, progress=progress, message=message).model_dump(),
    )


def create_job_completed(job_id: str, result: Dict[str, Any]) -> WSMessage:
    """Create a job completed message."""
    return WSMessage(
        type=WSMessageType.JOB_COMPLETED,
        payload=JobCompletedPayload(job_id=job_id, result=result).model_dump(),
    )


def create_job_failed(job_id: str, error: str, details: Optional[str] = None) -> WSMessage:
    """Create a job failed message."""
    return WSMessage(
        type=WSMessageType.JOB_FAILED,
        payload=JobFailedPayload(job_id=job_id, error=error, details=details).model_dump(),
    )


def create_notification(
    title: str,
    message: str,
    level: str = "info",
    action_url: Optional[str] = None,
) -> WSMessage:
    """Create a notification message."""
    return WSMessage(
        type=WSMessageType.NOTIFICATION,
        payload=NotificationPayload(
            title=title,
            message=message,
            level=level,
            action_url=action_url,
        ).model_dump(),
    )


def create_error(error: str, details: Optional[str] = None, request_id: Optional[str] = None) -> WSMessage:
    """Create an error message."""
    return WSMessage(
        type=WSMessageType.ERROR,
        payload={"error": error, "details": details},
        request_id=request_id,
    )
