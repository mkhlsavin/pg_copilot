"""
WebSocket Message Handlers.

Provides handlers for different WebSocket message types.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.api.websocket.manager import WebSocketManager
from src.api.websocket.models import (
    WSMessage,
    WSMessageType,
    create_error,
    create_chat_chunk,
    create_chat_response,
)
from src.api.services.chat_service import get_chat_service

logger = logging.getLogger("api.websocket.handlers")


class ChatHandler:
    """
    Handler for chat-related WebSocket messages.

    Processes chat queries and streams responses.
    """

    def __init__(self, manager: WebSocketManager):
        """
        Initialize the chat handler.

        Args:
            manager: WebSocket manager
        """
        self.manager = manager
        self.chat_service = get_chat_service()

    async def handle_query(
        self,
        user_id: str,
        conn_id: str,
        message: WSMessage,
    ) -> None:
        """
        Handle a chat query message.

        Args:
            user_id: User ID
            conn_id: Connection ID
            message: Chat query message
        """
        query = message.payload.get("query", "")
        session_id = message.payload.get("session_id")
        scenario_id = message.payload.get("scenario_id")
        language = message.payload.get("language", "en")
        request_id = message.request_id

        if not query:
            await self.manager.send_to_connection(
                user_id,
                conn_id,
                create_error("Query is required", request_id=request_id),
            )
            return

        try:
            # Initialize chat service if needed
            await self.chat_service.initialize()

            # Stream the response
            async for chunk in self.chat_service.process_query_stream(
                query=query,
                session_id=session_id,
                scenario_id=scenario_id,
                user_id=user_id,
                language=language,
            ):
                # Parse SSE data
                if chunk.startswith("data: "):
                    import json
                    try:
                        data = json.loads(chunk[6:].strip())
                        chunk_type = data.get("type")

                        if chunk_type == "scenario":
                            await self.manager.send_to_connection(
                                user_id,
                                conn_id,
                                WSMessage(
                                    type=WSMessageType.CHAT_SCENARIO,
                                    payload={"scenario_id": data.get("scenario_id")},
                                    request_id=request_id,
                                ),
                            )
                        elif chunk_type == "chunk":
                            await self.manager.send_to_connection(
                                user_id,
                                conn_id,
                                create_chat_chunk(
                                    data.get("content", ""),
                                    request_id=request_id,
                                ),
                            )
                        elif chunk_type == "done":
                            await self.manager.send_to_connection(
                                user_id,
                                conn_id,
                                WSMessage(
                                    type=WSMessageType.CHAT_DONE,
                                    payload={},
                                    request_id=request_id,
                                ),
                            )
                        elif chunk_type == "error":
                            await self.manager.send_to_connection(
                                user_id,
                                conn_id,
                                create_error(data.get("message", "Unknown error"), request_id=request_id),
                            )
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.exception(f"Error handling chat query: {e}")
            await self.manager.send_to_connection(
                user_id,
                conn_id,
                create_error(str(e), request_id=request_id),
            )


class JobHandler:
    """
    Handler for job-related WebSocket messages.

    Manages job status subscriptions and updates.
    """

    def __init__(self, manager: WebSocketManager):
        """
        Initialize the job handler.

        Args:
            manager: WebSocket manager
        """
        self.manager = manager

    async def handle_subscribe(
        self,
        user_id: str,
        conn_id: str,
        job_id: str,
    ) -> None:
        """
        Handle job subscription request.

        Args:
            user_id: User ID
            conn_id: Connection ID
            job_id: Job ID
        """
        await self.manager.subscribe_to_job(user_id, job_id)

        # Get and send current job status
        try:
            from src.api.services.job_service import JobService
            from src.api.database.connection import get_db
            from src.api.database.repositories.job_repo import JobRepository
            from uuid import UUID

            async for db in get_db():
                job_repo = JobRepository(db)
                job_service = JobService(job_repo)
                job = await job_service.get_job(UUID(job_id), UUID(user_id))

                if job:
                    await self.manager.send_to_connection(
                        user_id,
                        conn_id,
                        WSMessage(
                            type=WSMessageType.JOB_PROGRESS,
                            payload={
                                "job_id": str(job.id),
                                "status": job.status.value,
                                "progress": job.progress,
                                "job_type": job.job_type.value,
                            },
                        ),
                    )
                else:
                    await self.manager.send_to_connection(
                        user_id,
                        conn_id,
                        create_error(f"Job {job_id} not found"),
                    )
                break
        except Exception as e:
            logger.error(f"Error fetching job status: {e}")
            await self.manager.send_to_connection(
                user_id,
                conn_id,
                WSMessage(
                    type=WSMessageType.JOB_STARTED,
                    payload={"job_id": job_id, "status": "subscribed"},
                ),
            )

    async def handle_unsubscribe(
        self,
        user_id: str,
        job_id: str,
    ) -> None:
        """
        Handle job unsubscription request.

        Args:
            user_id: User ID
            job_id: Job ID
        """
        await self.manager.unsubscribe_from_job(user_id, job_id)

    async def send_job_update(
        self,
        job_id: str,
        status: str,
        progress: int,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Send job update to all subscribed users.

        Args:
            job_id: Job ID
            status: Job status
            progress: Progress percentage
            result: Job result (for completed jobs)
            error: Error message (for failed jobs)
        """
        if status == "completed":
            message_type = WSMessageType.JOB_COMPLETED
        elif status == "failed":
            message_type = WSMessageType.JOB_FAILED
        else:
            message_type = WSMessageType.JOB_PROGRESS

        payload = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
        }

        if result:
            payload["result"] = result
        if error:
            payload["error"] = error

        await self.manager.send_job_update(
            job_id,
            WSMessage(type=message_type, payload=payload),
        )

        # Cleanup subscriptions for completed/failed jobs
        if status in ["completed", "failed", "cancelled"]:
            await self.manager.cleanup_job_subscriptions(job_id)


class NotificationHandler:
    """
    Handler for notification-related WebSocket messages.

    Manages push notifications to users.
    """

    def __init__(self, manager: WebSocketManager):
        """
        Initialize the notification handler.

        Args:
            manager: WebSocket manager
        """
        self.manager = manager

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification to a user.

        Args:
            user_id: User ID
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            data: Additional data

        Returns:
            True if notification was sent
        """
        payload = {
            "title": title,
            "message": message,
            "type": notification_type,
        }

        if data:
            payload["data"] = data

        count = await self.manager.send_to_user(
            user_id,
            WSMessage(type=WSMessageType.NOTIFICATION, payload=payload),
        )

        return count > 0

    async def broadcast_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
    ) -> int:
        """
        Broadcast a notification to all connected users.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)

        Returns:
            Number of users notified
        """
        return await self.manager.broadcast(
            WSMessage(
                type=WSMessageType.NOTIFICATION,
                payload={
                    "title": title,
                    "message": message,
                    "type": notification_type,
                },
            )
        )


# Handler instances
_chat_handler: Optional[ChatHandler] = None
_job_handler: Optional[JobHandler] = None
_notification_handler: Optional[NotificationHandler] = None


def get_chat_handler() -> ChatHandler:
    """Get the chat handler instance."""
    global _chat_handler
    if _chat_handler is None:
        from src.api.websocket.manager import get_ws_manager
        _chat_handler = ChatHandler(get_ws_manager())
    return _chat_handler


def get_job_handler() -> JobHandler:
    """Get the job handler instance."""
    global _job_handler
    if _job_handler is None:
        from src.api.websocket.manager import get_ws_manager
        _job_handler = JobHandler(get_ws_manager())
    return _job_handler


def get_notification_handler() -> NotificationHandler:
    """Get the notification handler instance."""
    global _notification_handler
    if _notification_handler is None:
        from src.api.websocket.manager import get_ws_manager
        _notification_handler = NotificationHandler(get_ws_manager())
    return _notification_handler
