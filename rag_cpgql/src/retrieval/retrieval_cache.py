"""Enhanced Retrieval Cache with TTL, Metrics, and Invalidation Support

This module provides a production-grade caching system for retrieval operations
with the following features:

1. TTL (Time-To-Live) support for automatic expiration
2. Comprehensive metrics tracking (hit rate, memory usage, etc.)
3. Multiple invalidation strategies (by pattern, by age, manual)
4. Cache warming for common queries
5. Thread-safe operations
6. Configurable eviction policies

Usage:
    cache = RetrievalCache(max_size=256, ttl_seconds=3600)

    # Store result
    cache.set(key, value)

    # Retrieve result
    result = cache.get(key)  # Returns None if expired or not found

    # Get metrics
    metrics = cache.get_metrics()
    print(f"Hit rate: {metrics['hit_rate']:.2%}")

    # Invalidate by pattern
    cache.invalidate_pattern("domain:memory")
"""

import time
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from copy import deepcopy
import threading
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: Tuple[Any, ...]
    value: Dict
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0  # Approximate size

    def is_expired(self, ttl_seconds: Optional[float]) -> bool:
        """Check if entry has expired based on TTL."""
        if ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > ttl_seconds

    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheMetrics:
    """Comprehensive cache metrics."""
    # Hit/miss statistics
    hits: int = 0
    misses: int = 0

    # Size statistics
    current_size: int = 0  # Number of entries
    max_size: int = 0
    memory_bytes: int = 0  # Approximate memory usage

    # Timing statistics
    total_get_time_ms: float = 0.0
    total_set_time_ms: float = 0.0
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0

    # Eviction statistics
    evictions_by_size: int = 0
    evictions_by_ttl: int = 0
    evictions_by_invalidation: int = 0

    # Age statistics
    oldest_entry_age_seconds: float = 0.0
    newest_entry_age_seconds: float = 0.0
    avg_entry_age_seconds: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate

    @property
    def utilization(self) -> float:
        """Calculate cache utilization (0-1)."""
        return self.current_size / self.max_size if self.max_size > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary with computed properties."""
        d = asdict(self)
        d['hit_rate'] = self.hit_rate
        d['miss_rate'] = self.miss_rate
        d['utilization'] = self.utilization
        return d


class RetrievalCache:
    """
    Enhanced retrieval cache with TTL, metrics, and invalidation.

    Features:
    - LRU eviction policy
    - Optional TTL for automatic expiration
    - Comprehensive metrics tracking
    - Pattern-based invalidation
    - Thread-safe operations
    - Cache warming support
    """

    def __init__(
        self,
        max_size: int = 128,
        ttl_seconds: Optional[float] = None,
        enable_metrics: bool = True,
        name: str = "retrieval_cache"
    ):
        """
        Initialize retrieval cache.

        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live in seconds (None = no expiration)
            enable_metrics: Whether to collect detailed metrics
            name: Cache name for logging/identification
        """
        self.max_size = max(max_size, 0)
        self.ttl_seconds = ttl_seconds
        self.enable_metrics = enable_metrics
        self.name = name

        # Cache storage (LRU via OrderedDict)
        self._cache: OrderedDict[Tuple[Any, ...], CacheEntry] = OrderedDict()
        self._lock = threading.RLock()  # Thread-safe operations

        # Metrics
        self._metrics = CacheMetrics(max_size=max_size)

        logger.info(
            f"Initialized {name}: max_size={max_size}, ttl={ttl_seconds}s, "
            f"metrics={'enabled' if enable_metrics else 'disabled'}"
        )

    def get(self, key: Tuple[Any, ...]) -> Optional[Dict]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key (tuple)

        Returns:
            Cached value or None if not found/expired
        """
        start_time = time.time()

        with self._lock:
            entry = self._cache.get(key)

            # Cache miss
            if entry is None:
                self._metrics.misses += 1
                if self.enable_metrics:
                    elapsed_ms = (time.time() - start_time) * 1000
                    self._metrics.total_get_time_ms += elapsed_ms
                    self._update_avg_times()
                return None

            # Check expiration
            if entry.is_expired(self.ttl_seconds):
                logger.debug(f"{self.name}: Entry expired for key {key[:2]}...")
                self._evict_entry(key, reason="ttl")
                self._metrics.misses += 1
                if self.enable_metrics:
                    elapsed_ms = (time.time() - start_time) * 1000
                    self._metrics.total_get_time_ms += elapsed_ms
                    self._update_avg_times()
                return None

            # Cache hit - update access metadata
            entry.touch()
            self._cache.move_to_end(key)  # Mark as recently used
            self._metrics.hits += 1

            if self.enable_metrics:
                elapsed_ms = (time.time() - start_time) * 1000
                self._metrics.total_get_time_ms += elapsed_ms
                self._update_avg_times()

            # Return deep copy to prevent external mutations
            return deepcopy(entry.value)

    def set(self, key: Tuple[Any, ...], value: Dict) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key (tuple)
            value: Value to cache (will be deep copied)
        """
        start_time = time.time()

        with self._lock:
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=deepcopy(value),  # Store copy
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_bytes=self._estimate_size(value)
            )

            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            # Store entry
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Update metrics
            self._metrics.current_size = len(self._cache)
            self._metrics.memory_bytes = sum(e.size_bytes for e in self._cache.values())

            if self.enable_metrics:
                elapsed_ms = (time.time() - start_time) * 1000
                self._metrics.total_set_time_ms += elapsed_ms
                self._update_avg_times()

    def invalidate(self, key: Tuple[Any, ...]) -> bool:
        """
        Manually invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and invalidated
        """
        with self._lock:
            if key in self._cache:
                self._evict_entry(key, reason="manual")
                return True
            return False

    def invalidate_pattern(self, pattern: str, key_index: int = 0) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "domain:memory")
            key_index: Index in key tuple to match against (default: 0)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = []

            for key in self._cache.keys():
                if key_index < len(key):
                    key_value = str(key[key_index])
                    if pattern in key_value:
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                self._evict_entry(key, reason="pattern")

            logger.info(
                f"{self.name}: Invalidated {len(keys_to_remove)} entries matching pattern '{pattern}'"
            )
            return len(keys_to_remove)

    def invalidate_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._metrics.current_size = 0
            self._metrics.memory_bytes = 0
            self._metrics.evictions_by_invalidation += count
            logger.info(f"{self.name}: Cleared all {count} cache entries")
            return count

    def warm(self, entries: List[Tuple[Tuple[Any, ...], Dict]]) -> int:
        """
        Warm cache with pre-computed entries.

        Args:
            entries: List of (key, value) tuples to pre-load

        Returns:
            Number of entries successfully warmed
        """
        count = 0
        with self._lock:
            for key, value in entries:
                try:
                    self.set(key, value)
                    count += 1
                except Exception as e:
                    logger.warning(f"{self.name}: Failed to warm entry {key[:2]}...: {e}")

        logger.info(f"{self.name}: Warmed {count}/{len(entries)} cache entries")
        return count

    def get_metrics(self) -> Dict:
        """
        Get comprehensive cache metrics.

        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            # Update age statistics
            if self._cache:
                now = time.time()
                ages = [now - entry.created_at for entry in self._cache.values()]
                self._metrics.oldest_entry_age_seconds = max(ages)
                self._metrics.newest_entry_age_seconds = min(ages)
                self._metrics.avg_entry_age_seconds = sum(ages) / len(ages)

            return self._metrics.to_dict()

    def export_metrics(self, file_path: Optional[Path] = None) -> Dict:
        """
        Export metrics to JSON file.

        Args:
            file_path: Path to save metrics (optional)

        Returns:
            Metrics dictionary
        """
        metrics = self.get_metrics()

        if file_path:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2)

            logger.info(f"{self.name}: Exported metrics to {file_path}")

        return metrics

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            current_size = self._metrics.current_size
            max_size = self._metrics.max_size
            memory_bytes = self._metrics.memory_bytes

            self._metrics = CacheMetrics(max_size=max_size)
            self._metrics.current_size = current_size
            self._metrics.memory_bytes = memory_bytes

            logger.info(f"{self.name}: Reset metrics")

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)  # Remove first (oldest)
            self._metrics.evictions_by_size += 1
            self._metrics.current_size = len(self._cache)
            self._metrics.memory_bytes -= entry.size_bytes
            logger.debug(f"{self.name}: Evicted LRU entry {key[:2]}...")

    def _evict_entry(self, key: Tuple[Any, ...], reason: str = "unknown") -> None:
        """Evict specific entry."""
        if key in self._cache:
            entry = self._cache.pop(key)

            if reason == "ttl":
                self._metrics.evictions_by_ttl += 1
            elif reason in ["manual", "pattern"]:
                self._metrics.evictions_by_invalidation += 1

            self._metrics.current_size = len(self._cache)
            self._metrics.memory_bytes -= entry.size_bytes

    def _estimate_size(self, value: Dict) -> int:
        """Estimate memory size of value in bytes."""
        try:
            # Rough estimate using JSON serialization
            return len(json.dumps(value, default=str).encode('utf-8'))
        except Exception:
            # Fallback to a default estimate
            return 1024  # 1KB default

    def _update_avg_times(self) -> None:
        """Update average timing metrics."""
        total_ops = self._metrics.hits + self._metrics.misses
        if total_ops > 0:
            self._metrics.avg_get_time_ms = self._metrics.total_get_time_ms / total_ops

        if self._metrics.current_size > 0:
            # Estimate based on total entries created (hits + misses for simplicity)
            self._metrics.avg_set_time_ms = self._metrics.total_set_time_ms / max(1, total_ops)

    def __len__(self) -> int:
        """Return number of entries in cache."""
        return len(self._cache)

    def __contains__(self, key: Tuple[Any, ...]) -> bool:
        """Check if key exists and is not expired."""
        result = self.get(key)
        return result is not None

    def __repr__(self) -> str:
        """String representation."""
        metrics = self.get_metrics()
        return (
            f"RetrievalCache(name={self.name}, size={len(self)}/{self.max_size}, "
            f"hit_rate={metrics['hit_rate']:.2%}, ttl={self.ttl_seconds}s)"
        )
