"""
Chat Router.

Provides endpoints for chat interactions with the RAG-CPGQL system.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.database.repositories.session_repo import SessionRepository
from src.api.dependencies import get_current_active_user
from src.api.services.chat_service import get_chat_service

logger = logging.getLogger("api.routers.chat")
router = APIRouter()


# Request/Response Models
class Evidence(BaseModel):
    """Evidence item from analysis."""
    type: str
    source: Optional[str] = None
    content: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    relevance: float = Field(default=1.0, ge=0, le=1)


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    scenario_id: Optional[str] = None  # If not specified, auto-detect
    language: str = Field(default="en", pattern="^(en|ru)$")


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    scenario_id: str
    confidence: float = Field(ge=0, le=1)
    evidence: List[Evidence] = Field(default_factory=list)
    session_id: str
    request_id: str
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Endpoints
@router.post(
    "",
    response_model=ChatResponse,
    summary="Send chat message",
    description="Send a query to the RAG-CPGQL system and get a response.",
)
async def chat(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Process a chat query.

    Args:
        request: Chat request with query and optional parameters
        req: FastAPI request object
        current_user: Authenticated user
        db: Database session

    Returns:
        Chat response with answer, evidence, and metadata
    """
    request_id = getattr(req.state, "request_id", str(uuid.uuid4()))

    logger.info(f"Chat request from {current_user.username}: scenario={request.scenario_id}")

    try:
        # Get or create session
        session_repo = SessionRepository(db)
        session_id = request.session_id

        if not session_id:
            # Create new session
            session = await session_repo.create(
                user_id=current_user.id,
                metadata={"language": request.language},
            )
            await db.commit()
            session_id = str(session.id)
            logger.info(f"Created new session: {session_id}")

        # Get chat context from session
        context = None
        if session_id:
            try:
                session_uuid = uuid.UUID(session_id)
                turns = await session_repo.get_recent_turns(session_uuid, count=10)
                context = [
                    {"role": t.role, "content": t.content}
                    for t in turns
                ]
            except (ValueError, Exception) as e:
                logger.debug(f"Could not load session context: {e}")

        # Process query via ChatService
        chat_service = get_chat_service()
        result = await chat_service.process_query(
            query=request.query,
            session_id=session_id,
            scenario_id=request.scenario_id,
            user_id=str(current_user.id),
            language=request.language,
            context=context,
        )

        # Store dialogue turns
        try:
            session_uuid = uuid.UUID(session_id)
            # User turn
            await session_repo.add_turn(
                session_id=session_uuid,
                role="user",
                content=request.query,
                scenario_id=result.scenario_id,
            )
            # Assistant turn
            await session_repo.add_turn(
                session_id=session_uuid,
                role="assistant",
                content=result.answer,
                scenario_id=result.scenario_id,
                metadata={"confidence": result.confidence},
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save dialogue turns: {e}")

        # Convert evidence
        evidence = [
            Evidence(
                type=e.type,
                content=e.content,
                file_path=e.file_path,
                line_number=e.line_number,
                relevance=e.confidence,
            )
            for e in result.evidence
        ]

        logger.info(
            f"Chat completed: scenario={result.scenario_id}, "
            f"confidence={result.confidence:.2f}, time={result.processing_time_ms:.0f}ms"
        )

        return ChatResponse(
            answer=result.answer,
            scenario_id=result.scenario_id,
            confidence=result.confidence,
            evidence=evidence,
            session_id=session_id,
            request_id=request_id,
            processing_time_ms=result.processing_time_ms,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            answer=f"An error occurred processing your request: {str(e)}",
            scenario_id=request.scenario_id or "error",
            confidence=0.0,
            evidence=[],
            session_id=request.session_id or "unknown",
            request_id=request_id,
            processing_time_ms=0.0,
        )


@router.post(
    "/stream",
    summary="Stream chat response",
    description="Send a query and receive streaming response via SSE.",
)
async def chat_stream(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Process a chat query with streaming response.

    Args:
        request: Chat request with query and optional parameters
        req: FastAPI request object
        current_user: Authenticated user
        db: Database session

    Returns:
        Server-Sent Events stream with response chunks
    """
    request_id = getattr(req.state, "request_id", str(uuid.uuid4()))

    logger.info(f"Stream chat request from {current_user.username}")

    async def generate():
        """Generate SSE events."""
        try:
            # Get or create session
            session_repo = SessionRepository(db)
            session_id = request.session_id

            if not session_id:
                session = await session_repo.create(
                    user_id=current_user.id,
                    metadata={"language": request.language, "streaming": True},
                )
                await db.commit()
                session_id = str(session.id)

            # Start event
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'request_id': request_id})}\n\n"

            # Get context
            context = None
            if session_id:
                try:
                    session_uuid = uuid.UUID(session_id)
                    turns = await session_repo.get_recent_turns(session_uuid, count=10)
                    context = [{"role": t.role, "content": t.content} for t in turns]
                except Exception as e:
                    logger.debug(f"Could not fetch session context: {e}")

            # Stream response
            chat_service = get_chat_service()
            full_response = ""

            async for chunk in chat_service.process_query_stream(
                query=request.query,
                session_id=session_id,
                scenario_id=request.scenario_id,
                user_id=str(current_user.id),
                language=request.language,
                context=context,
            ):
                # Forward chunks (service already formats as SSE)
                yield chunk
                # Accumulate for storage
                if '"type": "chunk"' in chunk and '"content":' in chunk:
                    try:
                        data = json.loads(chunk.replace("data: ", "").strip())
                        if data.get("type") == "chunk":
                            full_response += data.get("content", "")
                    except json.JSONDecodeError as e:
                        logger.debug(f"Ignored JSON decode error in chat stream: {e}")

            # Store dialogue turns
            try:
                session_uuid = uuid.UUID(session_id)
                await session_repo.add_turn(
                    session_id=session_uuid,
                    role="user",
                    content=request.query,
                    scenario_id=request.scenario_id,
                )
                await session_repo.add_turn(
                    session_id=session_uuid,
                    role="assistant",
                    content=full_response,
                    scenario_id=request.scenario_id,
                    metadata={"streaming": True},
                )
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to save streaming dialogue: {e}")

            # End event
            yield f"data: {json.dumps({'type': 'end', 'session_id': session_id})}\n\n"

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/scenarios",
    summary="List available scenarios",
    description="Get list of available analysis scenarios.",
)
async def list_scenarios(
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """
    List available scenarios for chat.

    Returns:
        List of scenario information
    """
    chat_service = get_chat_service()
    return chat_service.get_available_scenarios()


@router.get(
    "/scenarios/{scenario_id}",
    summary="Get scenario info",
    description="Get information about a specific scenario.",
)
async def get_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get scenario information.

    Args:
        scenario_id: Scenario ID

    Returns:
        Scenario details
    """
    chat_service = get_chat_service()
    scenario = chat_service.get_scenario_info(scenario_id)

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    return scenario
