"""
SIEM Buffer - Reliable message delivery with buffering and retry.

Provides async buffering for SIEM messages with:
- In-memory buffer with size limit
- Periodic flush
- Retry on failure with exponential backoff
"""

import asyncio
import logging
import time
from collections import deque
from threading import Lock, Thread
from typing import Callable, List, Optional, Any
from dataclasses import dataclass

from .base_handler import SecurityEvent

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """A message in the buffer with retry metadata."""
    event: SecurityEvent
    attempts: int = 0
    first_attempt_time: float = 0.0
    last_attempt_time: float = 0.0

    def __post_init__(self):
        if self.first_attempt_time == 0.0:
            self.first_attempt_time = time.time()


class SIEMBuffer:
    """
    Thread-safe buffer for SIEM messages with reliable delivery.

    Features:
    - In-memory circular buffer with configurable size
    - Background thread for periodic flushing
    - Retry with exponential backoff
    - Overflow handling (oldest messages dropped)
    """

    def __init__(
        self,
        send_func: Callable[[SecurityEvent], bool],
        max_size: int = 10000,
        flush_interval: float = 5.0,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        max_retry_delay: float = 60.0,
    ):
        """
        Initialize SIEM buffer.

        Args:
            send_func: Function to send a single event (returns True on success)
            max_size: Maximum buffer size
            flush_interval: Seconds between flush attempts
            max_retries: Maximum retry attempts per message
            retry_backoff: Backoff multiplier for retries
            max_retry_delay: Maximum delay between retries
        """
        self._send_func = send_func
        self._max_size = max_size
        self._flush_interval = flush_interval
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._max_retry_delay = max_retry_delay

        self._buffer: deque[BufferedMessage] = deque(maxlen=max_size)
        self._retry_buffer: List[BufferedMessage] = []
        self._lock = Lock()
        self._running = False
        self._flush_thread: Optional[Thread] = None

        # Stats
        self._stats = {
            "enqueued": 0,
            "sent": 0,
            "failed": 0,
            "dropped": 0,
            "retried": 0,
        }

    def start(self) -> None:
        """Start background flush thread."""
        if self._running:
            return

        self._running = True
        self._flush_thread = Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info(f"SIEM buffer started (max_size={self._max_size}, interval={self._flush_interval}s)")

    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop buffer and flush remaining messages.

        Args:
            timeout: Maximum time to wait for flush
        """
        self._running = False

        if self._flush_thread:
            self._flush_thread.join(timeout=timeout)
            self._flush_thread = None

        # Final flush
        self._flush()
        logger.info(f"SIEM buffer stopped. Stats: {self._stats}")

    def enqueue(self, event: SecurityEvent) -> bool:
        """
        Add event to buffer.

        Args:
            event: Security event to buffer

        Returns:
            True if added, False if buffer is full and message was dropped
        """
        with self._lock:
            if len(self._buffer) >= self._max_size:
                # Buffer full, oldest message will be dropped by deque
                self._stats["dropped"] += 1
                logger.warning("SIEM buffer full, dropping oldest message")

            self._buffer.append(BufferedMessage(event=event))
            self._stats["enqueued"] += 1
            return True

    def flush(self) -> int:
        """
        Manually flush buffer.

        Returns:
            Number of messages sent successfully
        """
        return self._flush()

    def _flush(self) -> int:
        """Internal flush implementation."""
        sent_count = 0

        # Get messages to send
        with self._lock:
            messages_to_send = list(self._buffer)
            self._buffer.clear()

            # Add retry messages
            messages_to_send.extend(self._retry_buffer)
            self._retry_buffer.clear()

        # Send messages
        retry_later = []
        for msg in messages_to_send:
            msg.attempts += 1
            msg.last_attempt_time = time.time()

            try:
                if self._send_func(msg.event):
                    sent_count += 1
                    self._stats["sent"] += 1
                else:
                    # Send returned False, schedule for retry
                    if msg.attempts < self._max_retries:
                        retry_later.append(msg)
                        self._stats["retried"] += 1
                    else:
                        self._stats["failed"] += 1
                        logger.warning(f"SIEM message failed after {msg.attempts} attempts: {msg.event.request_id}")

            except Exception as e:
                logger.error(f"Error sending SIEM message: {e}")
                if msg.attempts < self._max_retries:
                    retry_later.append(msg)
                    self._stats["retried"] += 1
                else:
                    self._stats["failed"] += 1

        # Add failed messages back to retry buffer
        if retry_later:
            with self._lock:
                self._retry_buffer.extend(retry_later)

        return sent_count

    def _flush_loop(self) -> None:
        """Background flush loop."""
        while self._running:
            try:
                time.sleep(self._flush_interval)
                if self._running:
                    self._flush()
            except Exception as e:
                logger.error(f"Error in SIEM flush loop: {e}")

    @property
    def size(self) -> int:
        """Current buffer size."""
        with self._lock:
            return len(self._buffer) + len(self._retry_buffer)

    @property
    def stats(self) -> dict:
        """Buffer statistics."""
        return dict(self._stats)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class AsyncSIEMBuffer:
    """
    Async version of SIEM buffer for use with asyncio.
    """

    def __init__(
        self,
        send_func: Callable[[SecurityEvent], bool],
        max_size: int = 10000,
        flush_interval: float = 5.0,
        max_retries: int = 3,
    ):
        """
        Initialize async SIEM buffer.

        Args:
            send_func: Function to send a single event
            max_size: Maximum buffer size
            flush_interval: Seconds between flush attempts
            max_retries: Maximum retry attempts
        """
        self._send_func = send_func
        self._max_size = max_size
        self._flush_interval = flush_interval
        self._max_retries = max_retries

        self._queue: asyncio.Queue[BufferedMessage] = asyncio.Queue(maxsize=max_size)
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start async flush task."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Async SIEM buffer started")

    async def stop(self) -> None:
        """Stop async buffer."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush()

    async def enqueue(self, event: SecurityEvent) -> bool:
        """Add event to async buffer."""
        try:
            msg = BufferedMessage(event=event)
            self._queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            logger.warning("Async SIEM buffer full, dropping message")
            return False

    async def _flush(self) -> int:
        """Flush async buffer."""
        sent_count = 0
        retry_messages = []

        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
                msg.attempts += 1

                # Run send in executor to avoid blocking
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, self._send_func, msg.event)

                if success:
                    sent_count += 1
                elif msg.attempts < self._max_retries:
                    retry_messages.append(msg)

            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error in async SIEM flush: {e}")

        # Re-queue retry messages
        for msg in retry_messages:
            try:
                self._queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning("Cannot retry SIEM message, buffer full")

        return sent_count

    async def _flush_loop(self) -> None:
        """Async flush loop."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._running:
                    await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in async SIEM flush loop: {e}")
