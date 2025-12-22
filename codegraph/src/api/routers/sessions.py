"""
Sessions Router.

Provides endpoints for managing chat sessions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.database.repositories.session_repo import SessionRepository
from src.api.dependencies import get_current_active_user

logger = logging.getLogger("api.routers.sessions")
router = APIRouter()


# Request/Response Models
class SessionCreate(BaseModel):
    """Session creation request."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    """Session update request."""
    current_scenario: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionInfo(BaseModel):
    """Session information model."""
    id: str
    created_at: datetime
    updated_at: datetime
    current_scenario: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    turn_count: int = 0


class DialogueTurnInfo(BaseModel):
    """Dialogue turn information."""
    id: int
    role: str
    content: str
    timestamp: datetime
    scenario_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionDetail(SessionInfo):
    """Detailed session information with dialogue history."""
    dialogue_turns: List[DialogueTurnInfo] = Field(default_factory=list)


class SessionListResponse(BaseModel):
    """Paginated session list response."""
    items: List[SessionInfo]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# Endpoints
@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    description="Get paginated list of user's chat sessions.",
)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """
    List all sessions for current user.

    Args:
        page: Page number
        page_size: Items per page

    Returns:
        Paginated list of sessions
    """
    session_repo = SessionRepository(db)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get sessions and total count
    sessions = await session_repo.get_by_user(
        user_id=current_user.id,
        limit=page_size,
        offset=offset,
    )
    total = await session_repo.count_by_user(current_user.id)

    # Get turn counts for each session
    items = []
    for session in sessions:
        turn_count = await session_repo.count_turns(session.id)
        items.append(SessionInfo(
            id=str(session.id),
            created_at=session.created_at,
            updated_at=session.updated_at,
            current_scenario=session.current_scenario,
            metadata=session.session_metadata or {},
            turn_count=turn_count,
        ))

    return SessionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
        has_prev=page > 1,
    )


@router.post(
    "",
    response_model=SessionInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create session",
    description="Create a new chat session.",
)
async def create_session(
    request: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionInfo:
    """
    Create a new session.

    Args:
        request: Session creation parameters

    Returns:
        Created session info
    """
    session_repo = SessionRepository(db)

    session = await session_repo.create(
        user_id=current_user.id,
        metadata=request.metadata,
    )

    await db.commit()

    logger.info(f"Session created: {session.id} for user {current_user.username}")

    return SessionInfo(
        id=str(session.id),
        created_at=session.created_at,
        updated_at=session.updated_at,
        current_scenario=session.current_scenario,
        metadata=session.session_metadata or {},
        turn_count=0,
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Get session",
    description="Get detailed session information including dialogue history.",
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    """
    Get session details.

    Args:
        session_id: Session ID

    Returns:
        Session details with dialogue history
    """
    session_repo = SessionRepository(db)

    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await session_repo.get_by_id(session_uuid, include_turns=True)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Check ownership
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Convert dialogue turns
    turns = [
        DialogueTurnInfo(
            id=turn.id,
            role=turn.role,
            content=turn.content,
            timestamp=turn.timestamp,
            scenario_id=turn.scenario_id,
            metadata=turn.turn_metadata,
        )
        for turn in session.dialogue_turns
    ]

    return SessionDetail(
        id=str(session.id),
        created_at=session.created_at,
        updated_at=session.updated_at,
        current_scenario=session.current_scenario,
        metadata=session.session_metadata or {},
        turn_count=len(turns),
        dialogue_turns=turns,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete session",
    description="Delete a chat session and its history.",
)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a session.

    Args:
        session_id: Session ID to delete
    """
    session_repo = SessionRepository(db)

    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await session_repo.get_by_id(session_uuid)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Check ownership
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this session",
        )

    await session_repo.delete(session_uuid)
    await db.commit()

    logger.info(f"Session deleted: {session_id} by user {current_user.username}")


@router.patch(
    "/{session_id}",
    response_model=SessionInfo,
    summary="Update session",
    description="Update session metadata or scenario.",
)
async def update_session(
    session_id: str,
    request: SessionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionInfo:
    """
    Update session metadata.

    Args:
        session_id: Session ID
        request: Updated fields

    Returns:
        Updated session info
    """
    session_repo = SessionRepository(db)

    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await session_repo.get_by_id(session_uuid)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Check ownership
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this session",
        )

    # Update session
    updated_session = await session_repo.update(
        session_id=session_uuid,
        current_scenario=request.current_scenario,
        metadata=request.metadata,
    )

    await db.commit()

    turn_count = await session_repo.count_turns(session_uuid)

    logger.info(f"Session updated: {session_id} by user {current_user.username}")

    return SessionInfo(
        id=str(updated_session.id),
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at,
        current_scenario=updated_session.current_scenario,
        metadata=updated_session.session_metadata or {},
        turn_count=turn_count,
    )
