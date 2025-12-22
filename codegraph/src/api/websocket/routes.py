"""
WebSocket Routes.

Provides WebSocket endpoints for real-time communication.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.api.websocket.manager import get_ws_manager
from src.api.websocket.models import (
    WSMessage,
    WSMessageType,
    create_error,
    create_chat_chunk,
    create_chat_response,
)
from src.api.websocket.handlers import get_chat_handler, get_job_handler

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT token and return user ID.

    Args:
        token: JWT token

    Returns:
        User ID if valid, None otherwise
    """
    try:
        from src.api.auth.jwt_handler import decode_token
        payload = decode_token(token)
        if payload:
            return payload.sub
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")

    # Fallback for development
    if token:
        return f"user_{token[:8]}"
    return None


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time chat.

    Supports streaming responses for chat queries.
    """
    # Verify token
    user_id = await verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    manager = get_ws_manager()
    conn_id = await manager.connect(user_id, websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = WSMessage.from_json(data)
            except Exception as e:
                await manager.send_to_connection(
                    user_id, conn_id, create_error("Invalid message format", str(e))
                )
                continue

            # Handle different message types
            if message.type == WSMessageType.CHAT_QUERY:
                await handle_chat_query(user_id, conn_id, message, manager)
            elif message.type == WSMessageType.PING:
                await manager.send_to_connection(
                    user_id,
                    conn_id,
                    WSMessage(type=WSMessageType.PONG, payload={}),
                )
            else:
                await manager.send_to_connection(
                    user_id,
                    conn_id,
                    create_error(f"Unknown message type: {message.type}"),
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}, conn={conn_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: user={user_id}, conn={conn_id}: {e}")
    finally:
        await manager.disconnect(user_id, conn_id)


async def handle_chat_query(
    user_id: str,
    conn_id: str,
    message: WSMessage,
    manager,
) -> None:
    """
    Handle a chat query message.

    Args:
        user_id: User ID
        conn_id: Connection ID
        message: Chat query message
        manager: WebSocket manager
    """
    chat_handler = get_chat_handler()
    await chat_handler.handle_query(user_id, conn_id, message)


async def fetch_job_status(job_id: str) -> Optional[dict]:
    """
    Fetch job status from database.

    Args:
        job_id: Job ID to fetch

    Returns:
        Job data dict if found, None otherwise
    """
    try:
        from src.api.database.connection import get_db_session
        from src.api.database.models import BackgroundJob
        from sqlalchemy import select

        async with get_db_session() as db:
            result = await db.execute(
                select(BackgroundJob).where(BackgroundJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if job:
                return job.to_dict()
    except Exception as e:
        logger.warning(f"Failed to fetch job status from database: {e}")

    return None


@router.websocket("/jobs/{job_id}")
async def websocket_job_status(
    websocket: WebSocket,
    job_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for job status updates.

    Streams progress updates for background jobs.
    """
    # Verify token
    user_id = await verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    manager = get_ws_manager()
    conn_id = await manager.connect(user_id, websocket)

    # Subscribe to job updates
    await manager.subscribe_to_job(user_id, job_id)

    try:
        # Fetch initial job status from database
        job_data = await fetch_job_status(job_id)

        if job_data is None:
            # Job not found in database
            await manager.send_to_connection(
                user_id,
                conn_id,
                WSMessage(
                    type=WSMessageType.ERROR,
                    payload={"error": "Job not found", "job_id": job_id},
                ),
            )
            await websocket.close(code=4004, reason="Job not found")
            return

        # Send initial job status
        await manager.send_to_connection(
            user_id,
            conn_id,
            WSMessage(
                type=WSMessageType.JOB_STARTED,
                payload={
                    "job_id": job_data["id"],
                    "status": job_data["status"],
                    "progress": job_data["progress"],
                    "job_type": job_data["job_type"],
                    "started_at": job_data["started_at"],
                    "created_at": job_data["created_at"],
                },
            ),
        )

        # If job is already completed, send completion message
        if job_data["status"] in ("completed", "failed", "cancelled"):
            completion_type = (
                WSMessageType.JOB_COMPLETED
                if job_data["status"] == "completed"
                else WSMessageType.JOB_FAILED
            )
            await manager.send_to_connection(
                user_id,
                conn_id,
                WSMessage(
                    type=completion_type,
                    payload={
                        "job_id": job_data["id"],
                        "status": job_data["status"],
                        "result": job_data.get("result"),
                        "error": job_data.get("error"),
                        "completed_at": job_data["completed_at"],
                    },
                ),
            )

        # Keep connection alive and handle pings
        while True:
            data = await websocket.receive_text()

            try:
                message = WSMessage.from_json(data)
                if message.type == WSMessageType.PING:
                    await manager.send_to_connection(
                        user_id,
                        conn_id,
                        WSMessage(type=WSMessageType.PONG, payload={}),
                    )
                elif message.type == WSMessageType.JOB_STATUS:
                    # Client requested fresh status - fetch from DB
                    updated_job = await fetch_job_status(job_id)
                    if updated_job:
                        await manager.send_to_connection(
                            user_id,
                            conn_id,
                            WSMessage(
                                type=WSMessageType.JOB_PROGRESS,
                                payload=updated_job,
                            ),
                        )
            except Exception as e:
                logger.debug(f"Ignored message parse error in job websocket: {e}")

    except WebSocketDisconnect:
        logger.info(f"Job WebSocket disconnected: user={user_id}, job={job_id}")
    finally:
        await manager.unsubscribe_from_job(user_id, job_id)
        await manager.disconnect(user_id, conn_id)


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for push notifications.

    Streams notifications about completed jobs, system alerts, etc.
    """
    # Verify token
    user_id = await verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    manager = get_ws_manager()
    conn_id = await manager.connect(user_id, websocket)

    try:
        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            try:
                message = WSMessage.from_json(data)
                if message.type == WSMessageType.PING:
                    await manager.send_to_connection(
                        user_id,
                        conn_id,
                        WSMessage(type=WSMessageType.PONG, payload={}),
                    )
            except Exception as e:
                logger.debug(f"Ignored message parse error in notification websocket: {e}")

    except WebSocketDisconnect:
        logger.info(f"Notification WebSocket disconnected: user={user_id}")
    finally:
        await manager.disconnect(user_id, conn_id)
