"""
WebSocket Package.

Provides WebSocket functionality for real-time communication.
"""

from src.api.websocket.manager import WebSocketManager, get_ws_manager
from src.api.websocket.models import WSMessageType, WSMessage
from src.api.websocket.handlers import (
    ChatHandler,
    JobHandler,
    NotificationHandler,
    get_chat_handler,
    get_job_handler,
    get_notification_handler,
)

__all__ = [
    "WebSocketManager",
    "get_ws_manager",
    "WSMessageType",
    "WSMessage",
    "ChatHandler",
    "JobHandler",
    "NotificationHandler",
    "get_chat_handler",
    "get_job_handler",
    "get_notification_handler",
]
