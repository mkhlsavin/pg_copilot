"""
WebSocket Connection Manager.

Manages WebSocket connections and message broadcasting.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from src.api.websocket.models import WSMessage, WSMessageType

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for all users.

    Supports:
    - Multiple connections per user
    - Broadcasting to specific users
    - Job-specific subscriptions
    - Connection health monitoring
    """

    def __init__(self):
        # user_id -> {conn_id: WebSocket}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}

        # job_id -> Set[user_id] (users subscribed to job updates)
        self._job_subscriptions: Dict[str, Set[str]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> str:
        """
        Register a new WebSocket connection.

        Args:
            user_id: User ID
            websocket: WebSocket connection

        Returns:
            Connection ID
        """
        await websocket.accept()
        conn_id = f"conn_{uuid.uuid4().hex[:12]}"

        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = {}
            self._connections[user_id][conn_id] = websocket

        logger.info(f"WebSocket connected: user={user_id}, conn={conn_id}")

        # Send connected message
        await self._send(
            websocket,
            WSMessage(
                type=WSMessageType.CONNECTED,
                payload={"connection_id": conn_id, "user_id": user_id},
            ),
        )

        return conn_id

    async def disconnect(self, user_id: str, conn_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            user_id: User ID
            conn_id: Connection ID
        """
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].pop(conn_id, None)
                if not self._connections[user_id]:
                    del self._connections[user_id]

        logger.info(f"WebSocket disconnected: user={user_id}, conn={conn_id}")

    async def send_to_user(self, user_id: str, message: WSMessage) -> int:
        """
        Send a message to all connections of a user.

        Args:
            user_id: User ID
            message: Message to send

        Returns:
            Number of connections that received the message
        """
        sent_count = 0

        async with self._lock:
            connections = self._connections.get(user_id, {})

        for conn_id, websocket in list(connections.items()):
            try:
                await self._send(websocket, message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user={user_id}, conn={conn_id}: {e}")
                await self.disconnect(user_id, conn_id)

        return sent_count

    async def send_to_connection(self, user_id: str, conn_id: str, message: WSMessage) -> bool:
        """
        Send a message to a specific connection.

        Args:
            user_id: User ID
            conn_id: Connection ID
            message: Message to send

        Returns:
            True if sent successfully
        """
        async with self._lock:
            websocket = self._connections.get(user_id, {}).get(conn_id)

        if not websocket:
            return False

        try:
            await self._send(websocket, message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to conn={conn_id}: {e}")
            await self.disconnect(user_id, conn_id)
            return False

    async def broadcast(self, message: WSMessage, exclude_users: Optional[Set[str]] = None) -> int:
        """
        Broadcast a message to all connected users.

        Args:
            message: Message to send
            exclude_users: User IDs to exclude

        Returns:
            Number of users that received the message
        """
        exclude_users = exclude_users or set()
        sent_count = 0

        async with self._lock:
            user_ids = list(self._connections.keys())

        for user_id in user_ids:
            if user_id not in exclude_users:
                count = await self.send_to_user(user_id, message)
                if count > 0:
                    sent_count += 1

        return sent_count

    # Job subscriptions
    async def subscribe_to_job(self, user_id: str, job_id: str) -> None:
        """
        Subscribe a user to job updates.

        Args:
            user_id: User ID
            job_id: Job ID
        """
        async with self._lock:
            if job_id not in self._job_subscriptions:
                self._job_subscriptions[job_id] = set()
            self._job_subscriptions[job_id].add(user_id)

        logger.debug(f"User {user_id} subscribed to job {job_id}")

    async def unsubscribe_from_job(self, user_id: str, job_id: str) -> None:
        """
        Unsubscribe a user from job updates.

        Args:
            user_id: User ID
            job_id: Job ID
        """
        async with self._lock:
            if job_id in self._job_subscriptions:
                self._job_subscriptions[job_id].discard(user_id)
                if not self._job_subscriptions[job_id]:
                    del self._job_subscriptions[job_id]

    async def send_job_update(self, job_id: str, message: WSMessage) -> int:
        """
        Send an update to all users subscribed to a job.

        Args:
            job_id: Job ID
            message: Message to send

        Returns:
            Number of users that received the message
        """
        async with self._lock:
            user_ids = list(self._job_subscriptions.get(job_id, set()))

        sent_count = 0
        for user_id in user_ids:
            count = await self.send_to_user(user_id, message)
            if count > 0:
                sent_count += 1

        return sent_count

    async def cleanup_job_subscriptions(self, job_id: str) -> None:
        """
        Remove all subscriptions for a completed job.

        Args:
            job_id: Job ID
        """
        async with self._lock:
            self._job_subscriptions.pop(job_id, None)

    # Utility methods
    async def _send(self, websocket: WebSocket, message: WSMessage) -> None:
        """Send a message through a WebSocket."""
        await websocket.send_text(message.to_json())

    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """
        Get number of active connections.

        Args:
            user_id: Optional user ID to filter

        Returns:
            Number of connections
        """
        if user_id:
            return len(self._connections.get(user_id, {}))
        return sum(len(conns) for conns in self._connections.values())

    def get_user_count(self) -> int:
        """Get number of connected users."""
        return len(self._connections)

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._connections and len(self._connections[user_id]) > 0


# Global instance
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
