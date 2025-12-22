"""
History Router.

Provides endpoints for accessing and exporting dialogue history.
"""

import io
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.database.repositories.session_repo import SessionRepository
from src.api.dependencies import get_current_active_user

logger = logging.getLogger("api.routers.history")
router = APIRouter()


# Models
class ExportFormat(str, Enum):
    """Export format options."""
    JSON = "json"
    MARKDOWN = "markdown"


class DialogueTurnInfo(BaseModel):
    """Dialogue turn information."""
    id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    scenario_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    """History response model."""
    session_id: str
    turns: List[DialogueTurnInfo]
    total_turns: int
    page: int
    page_size: int
    has_more: bool


# Endpoints
@router.get(
    "/{session_id}",
    response_model=HistoryResponse,
    summary="Get dialogue history",
    description="Get paginated dialogue history for a session.",
)
async def get_history(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    include_metadata: bool = Query(default=False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """
    Get dialogue history for a session.

    Args:
        session_id: Session ID
        page: Page number
        page_size: Items per page
        include_metadata: Include turn metadata
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated dialogue history
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session_repo = SessionRepository(db)

    # Get session and verify ownership
    session = await session_repo.get_by_id(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Get total count for pagination
    total_turns = await session_repo.count_turns(session_uuid)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get turns
    turns = await session_repo.get_turns(session_uuid, limit=page_size, offset=offset)

    # Convert to response model
    turn_infos = [
        DialogueTurnInfo(
            id=t.id,
            role=t.role,
            content=t.content,
            timestamp=t.timestamp,
            scenario_id=t.scenario_id,
            metadata=t.turn_metadata if include_metadata else None,
        )
        for t in turns
    ]

    has_more = offset + len(turns) < total_turns

    logger.debug(
        f"History retrieved for session {session_id}: "
        f"page={page}, returned={len(turns)}, total={total_turns}"
    )

    return HistoryResponse(
        session_id=session_id,
        turns=turn_infos,
        total_turns=total_turns,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.post(
    "/{session_id}/export",
    summary="Export history",
    description="Export dialogue history in JSON or Markdown format.",
)
async def export_history(
    session_id: str,
    format: ExportFormat = Query(default=ExportFormat.JSON),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Export dialogue history.

    Args:
        session_id: Session ID
        format: Export format (json or markdown)
        current_user: Authenticated user
        db: Database session

    Returns:
        Downloadable file with history
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session_repo = SessionRepository(db)

    # Get session and verify ownership
    session = await session_repo.get_by_id(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Get all turns (no limit for export)
    total_turns = await session_repo.count_turns(session_uuid)
    turns = await session_repo.get_turns(session_uuid, limit=total_turns, offset=0)

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if format == ExportFormat.JSON:
        # Export as JSON
        export_data = {
            "session_id": session_id,
            "exported_at": datetime.utcnow().isoformat(),
            "total_turns": len(turns),
            "turns": [
                {
                    "id": t.id,
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                    "scenario_id": t.scenario_id,
                    "metadata": t.turn_metadata,
                }
                for t in turns
            ],
        }

        content = json.dumps(export_data, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"history_{session_id[:8]}_{timestamp_str}.json"

    else:
        # Export as Markdown
        lines = [
            f"# Dialogue History",
            f"",
            f"**Session ID:** {session_id}",
            f"**Exported:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"**Total Turns:** {len(turns)}",
            f"",
            "---",
            "",
        ]

        for turn in turns:
            role_emoji = "👤" if turn.role == "user" else "🤖"
            role_name = "User" if turn.role == "user" else "Assistant"
            timestamp = turn.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            lines.append(f"## {role_emoji} {role_name}")
            lines.append(f"*{timestamp}*")
            if turn.scenario_id:
                lines.append(f"*Scenario: {turn.scenario_id}*")
            lines.append("")
            lines.append(turn.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        content = "\n".join(lines)
        media_type = "text/markdown"
        filename = f"history_{session_id[:8]}_{timestamp_str}.md"

    logger.info(f"History exported for session {session_id}: format={format.value}")

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.delete(
    "/{session_id}/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear history",
    description="Clear all dialogue history for a session (keeps the session).",
)
async def clear_history(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Clear dialogue history for a session.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        db: Database session
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session_repo = SessionRepository(db)

    # Get session and verify ownership
    session = await session_repo.get_by_id(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Clear turns
    deleted_count = await session_repo.clear_turns(session_uuid)
    await db.commit()

    logger.info(f"History cleared for session {session_id}: {deleted_count} turns deleted")
