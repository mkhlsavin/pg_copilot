"""Base handler class for workflow handlers.

All workflow handlers inherit from BaseHandler which provides
common functionality like logging, error handling, and metrics.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HandlerResult:
    """Result from a handler operation."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


class BaseHandler(ABC):
    """
    Abstract base class for workflow handlers.

    Provides common functionality:
    - Logging with handler name prefix
    - Timing/metrics collection
    - Error handling wrapper
    - Configuration management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize handler.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._name = self.__class__.__name__
        self._call_count = 0
        self._total_duration_ms = 0.0
        self._error_count = 0

    @property
    def name(self) -> str:
        """Handler name for logging."""
        return self._name

    def log_debug(self, msg: str):
        """Log debug message with handler prefix."""
        logger.debug(f"[{self._name}] {msg}")

    def log_info(self, msg: str):
        """Log info message with handler prefix."""
        logger.info(f"[{self._name}] {msg}")

    def log_warning(self, msg: str):
        """Log warning message with handler prefix."""
        logger.warning(f"[{self._name}] {msg}")

    def log_error(self, msg: str):
        """Log error message with handler prefix."""
        logger.error(f"[{self._name}] {msg}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get handler metrics."""
        avg_duration = (
            self._total_duration_ms / self._call_count
            if self._call_count > 0 else 0.0
        )
        return {
            "handler_name": self._name,
            "call_count": self._call_count,
            "error_count": self._error_count,
            "total_duration_ms": self._total_duration_ms,
            "avg_duration_ms": avg_duration,
            "error_rate": self._error_count / max(self._call_count, 1)
        }

    def _track_call(self, duration_ms: float, success: bool):
        """Track call metrics."""
        self._call_count += 1
        self._total_duration_ms += duration_ms
        if not success:
            self._error_count += 1

    @abstractmethod
    def handle(self, *args, **kwargs) -> HandlerResult:
        """
        Execute handler logic.

        Must be implemented by subclasses.

        Returns:
            HandlerResult with success status and data
        """
        pass

    def __repr__(self) -> str:
        return f"<{self._name} calls={self._call_count}>"
