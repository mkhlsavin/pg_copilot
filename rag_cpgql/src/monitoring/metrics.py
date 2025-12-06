"""
Prometheus Metrics and Structured Logging for RAG-CPGQL System

Provides:
- Prometheus metrics for observability
- Structured JSON logging
- Monitoring decorators for functions
- Metrics collector singleton

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import time
import json
import logging
import functools
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

# Try to import prometheus_client, fallback to stub if not available
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stub implementations for environments without prometheus
    class StubMetric:
        def __init__(self, *args, **kwargs):
            self._labels = {}
            self._value = 0

        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            self._value += amount

        def dec(self, amount=1):
            self._value -= amount

        def observe(self, value):
            self._value = value

        def set(self, value):
            self._value = value

    Counter = Histogram = Gauge = Summary = StubMetric

logger = logging.getLogger(__name__)


# ============================================================================
# PROMETHEUS METRICS DEFINITIONS
# ============================================================================

# Scenario metrics
SCENARIO_DURATION = Histogram(
    'rag_scenario_duration_seconds',
    'Time spent in scenario execution',
    ['scenario_name'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
)

SCENARIO_SUCCESS = Counter(
    'rag_scenario_success_total',
    'Number of successful scenario executions',
    ['scenario_name']
)

SCENARIO_FAILURE = Counter(
    'rag_scenario_failure_total',
    'Number of failed scenario executions',
    ['scenario_name', 'error_type']
)

# Agent metrics
AGENT_DURATION = Histogram(
    'rag_agent_duration_seconds',
    'Time spent in agent execution',
    ['agent_name', 'scenario'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

AGENT_SUCCESS = Counter(
    'rag_agent_success_total',
    'Number of successful agent executions',
    ['agent_name', 'scenario']
)

AGENT_FAILURE = Counter(
    'rag_agent_failure_total',
    'Number of failed agent executions',
    ['agent_name', 'scenario', 'error_type']
)

# Cache metrics
CACHE_HITS = Counter(
    'rag_cache_hits_total',
    'Number of cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'rag_cache_misses_total',
    'Number of cache misses',
    ['cache_type']
)

CACHE_SIZE = Gauge(
    'rag_cache_size',
    'Current cache size',
    ['cache_type']
)

# Request metrics
ACTIVE_REQUESTS = Gauge(
    'rag_active_requests',
    'Number of requests currently being processed'
)

TOTAL_REQUESTS = Counter(
    'rag_total_requests',
    'Total number of requests processed'
)

# LLM metrics
LLM_LATENCY = Histogram(
    'rag_llm_latency_seconds',
    'LLM API call latency',
    ['model', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0)
)

LLM_TOKENS = Counter(
    'rag_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'token_type']
)

LLM_ERRORS = Counter(
    'rag_llm_errors_total',
    'Number of LLM API errors',
    ['model', 'error_type']
)

# CPG Query metrics
CPG_QUERY_LATENCY = Histogram(
    'rag_cpg_query_latency_seconds',
    'CPG query execution latency',
    ['query_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

CPG_QUERY_RESULTS = Histogram(
    'rag_cpg_query_results',
    'Number of results returned by CPG queries',
    ['query_type'],
    buckets=(0, 1, 5, 10, 50, 100, 500, 1000)
)

# Retrieval metrics
RETRIEVAL_LATENCY = Histogram(
    'rag_retrieval_latency_seconds',
    'Retrieval operation latency',
    ['retrieval_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

RETRIEVAL_RESULTS = Histogram(
    'rag_retrieval_results_count',
    'Number of results from retrieval',
    ['retrieval_type'],
    buckets=(0, 1, 5, 10, 20, 50)
)


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

class StructuredLogger:
    """
    JSON-formatted structured logger for production environments.

    Outputs logs in a format suitable for log aggregation systems
    like Elasticsearch, Splunk, or CloudWatch.

    Usage:
        logger = StructuredLogger("my_component")
        logger.info("Processing request", request_id="abc123", user="test")
    """

    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger.

        Args:
            name: Logger name (usually component name)
            level: Logging level
        """
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Add JSON handler if not already present
        if not any(isinstance(h, logging.StreamHandler) for h in self._logger.handlers):
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self._logger.addHandler(handler)

    def _format_log(self, message: str, level: str, **kwargs) -> str:
        """Format log entry as JSON."""
        log_data = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'level': level,
            'logger': self.name,
            'message': message,
        }
        log_data.update(kwargs)
        return json.dumps(log_data)

    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self._logger.debug(self._format_log(message, 'DEBUG', **kwargs))

    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self._logger.info(self._format_log(message, 'INFO', **kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self._logger.warning(self._format_log(message, 'WARNING', **kwargs))

    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        self._logger.error(self._format_log(message, 'ERROR', **kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message with structured data."""
        self._logger.critical(self._format_log(message, 'CRITICAL', **kwargs))

    @contextmanager
    def timed_operation(self, operation: str, **context):
        """
        Context manager for timing operations.

        Usage:
            with logger.timed_operation("query_generation", scenario="security"):
                result = generate_query()
        """
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time
            self.info(
                f"Operation completed: {operation}",
                operation=operation,
                duration_ms=round(duration * 1000, 2),
                status="success",
                **context
            )
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Operation failed: {operation}",
                operation=operation,
                duration_ms=round(duration * 1000, 2),
                status="error",
                error_type=type(e).__name__,
                error_message=str(e),
                **context
            )
            raise


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs JSON when given JSON strings."""

    def format(self, record):
        # If message is already JSON, return as-is
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, TypeError):
            # Standard formatting for non-JSON messages
            return super().format(record)


# ============================================================================
# MONITORING DECORATORS
# ============================================================================

def monitor_scenario(scenario_name: str):
    """
    Decorator to monitor scenario execution.

    Records:
    - Duration histogram
    - Success/failure counters
    - Active requests gauge

    Args:
        scenario_name: Name of the scenario (e.g., "security_audit")

    Usage:
        @monitor_scenario("security_audit")
        def run_security_scenario(question: str) -> Dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.inc()
            TOTAL_REQUESTS.inc()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                SCENARIO_DURATION.labels(scenario_name=scenario_name).observe(duration)
                SCENARIO_SUCCESS.labels(scenario_name=scenario_name).inc()

                logger.debug(
                    f"Scenario {scenario_name} completed in {duration:.2f}s"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                SCENARIO_DURATION.labels(scenario_name=scenario_name).observe(duration)
                SCENARIO_FAILURE.labels(
                    scenario_name=scenario_name,
                    error_type=type(e).__name__
                ).inc()

                logger.error(
                    f"Scenario {scenario_name} failed after {duration:.2f}s: {e}"
                )

                raise

            finally:
                ACTIVE_REQUESTS.dec()

        return wrapper
    return decorator


def monitor_agent(agent_name: str, scenario: str = "unknown"):
    """
    Decorator to monitor agent execution.

    Records:
    - Agent duration histogram
    - Success/failure counters

    Args:
        agent_name: Name of the agent
        scenario: Scenario context

    Usage:
        @monitor_agent("retriever_agent", scenario="security")
        def retrieve_context(query: str) -> List[Dict]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                AGENT_DURATION.labels(
                    agent_name=agent_name,
                    scenario=scenario
                ).observe(duration)

                AGENT_SUCCESS.labels(
                    agent_name=agent_name,
                    scenario=scenario
                ).inc()

                return result

            except Exception as e:
                duration = time.time() - start_time

                AGENT_DURATION.labels(
                    agent_name=agent_name,
                    scenario=scenario
                ).observe(duration)

                AGENT_FAILURE.labels(
                    agent_name=agent_name,
                    scenario=scenario,
                    error_type=type(e).__name__
                ).inc()

                raise

        return wrapper
    return decorator


def monitor_cache(cache_type: str = "query_plan"):
    """
    Decorator to monitor cache operations.

    Records cache hit/miss based on return value.
    Expected function signature: returns None on miss, value on hit.

    Args:
        cache_type: Type of cache (e.g., "query_plan", "embedding")

    Usage:
        @monitor_cache("query_plan")
        def get_cached_query(key: str) -> Optional[Dict]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if result is not None:
                CACHE_HITS.labels(cache_type=cache_type).inc()
            else:
                CACHE_MISSES.labels(cache_type=cache_type).inc()

            return result

        return wrapper
    return decorator


# ============================================================================
# RECORDING FUNCTIONS
# ============================================================================

def record_llm_call(
    model: str,
    operation: str,
    duration: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    error: Optional[str] = None
):
    """
    Record LLM call metrics.

    Args:
        model: LLM model name
        operation: Type of operation (generate, classify, etc.)
        duration: Call duration in seconds
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        error: Error type if failed
    """
    LLM_LATENCY.labels(model=model, operation=operation).observe(duration)

    if input_tokens > 0:
        LLM_TOKENS.labels(model=model, token_type='input').inc(input_tokens)

    if output_tokens > 0:
        LLM_TOKENS.labels(model=model, token_type='output').inc(output_tokens)

    if error:
        LLM_ERRORS.labels(model=model, error_type=error).inc()


def record_cpg_query(
    query_type: str,
    duration: float,
    result_count: int = 0
):
    """
    Record CPG query metrics.

    Args:
        query_type: Type of query (method_lookup, edge_traversal, etc.)
        duration: Query duration in seconds
        result_count: Number of results returned
    """
    CPG_QUERY_LATENCY.labels(query_type=query_type).observe(duration)
    CPG_QUERY_RESULTS.labels(query_type=query_type).observe(result_count)


def record_retrieval(
    retrieval_type: str,
    duration: float,
    result_count: int = 0
):
    """
    Record retrieval operation metrics.

    Args:
        retrieval_type: Type of retrieval (vector, keyword, hybrid)
        duration: Retrieval duration in seconds
        result_count: Number of results returned
    """
    RETRIEVAL_LATENCY.labels(retrieval_type=retrieval_type).observe(duration)
    RETRIEVAL_RESULTS.labels(retrieval_type=retrieval_type).observe(result_count)


# ============================================================================
# METRICS COLLECTOR (SINGLETON)
# ============================================================================

@dataclass
class MetricsSummary:
    """Summary of collected metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0
    active_requests: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': round(self.success_rate, 4),
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'p50_latency_ms': round(self.p50_latency_ms, 2),
            'p95_latency_ms': round(self.p95_latency_ms, 2),
            'p99_latency_ms': round(self.p99_latency_ms, 2),
            'cache_hit_rate': round(self.cache_hit_rate, 4),
            'active_requests': self.active_requests,
        }


class MetricsCollector:
    """
    Singleton metrics collector for in-memory metric aggregation.

    Provides local metric storage when Prometheus server is not available.
    """

    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._lock = threading.Lock()

        # In-memory metric storage
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)

        # Scenario-specific metrics
        self._scenario_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'success': 0, 'failure': 0, 'latencies': []}
        )

        # Cache metrics
        self._cache_hits: Dict[str, int] = defaultdict(int)
        self._cache_misses: Dict[str, int] = defaultdict(int)

        # Start time
        self._start_time = time.time()

    def record_latency(self, metric_name: str, value: float):
        """Record a latency observation."""
        with self._lock:
            self._latencies[metric_name].append(value)
            # Keep last 1000 observations per metric
            if len(self._latencies[metric_name]) > 1000:
                self._latencies[metric_name] = self._latencies[metric_name][-1000:]

    def increment_counter(self, metric_name: str, amount: int = 1):
        """Increment a counter."""
        with self._lock:
            self._counters[metric_name] += amount

    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge value."""
        with self._lock:
            self._gauges[metric_name] = value

    def record_scenario(
        self,
        scenario: str,
        success: bool,
        latency: float
    ):
        """Record scenario execution."""
        with self._lock:
            stats = self._scenario_stats[scenario]
            if success:
                stats['success'] += 1
            else:
                stats['failure'] += 1
            stats['latencies'].append(latency)
            # Keep last 100 latencies per scenario
            if len(stats['latencies']) > 100:
                stats['latencies'] = stats['latencies'][-100:]

    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache access."""
        with self._lock:
            if hit:
                self._cache_hits[cache_type] += 1
            else:
                self._cache_misses[cache_type] += 1

    def get_summary(self) -> MetricsSummary:
        """Get metrics summary."""
        with self._lock:
            # Calculate totals
            total_success = sum(s['success'] for s in self._scenario_stats.values())
            total_failure = sum(s['failure'] for s in self._scenario_stats.values())
            total_requests = total_success + total_failure

            # Calculate success rate
            success_rate = total_success / total_requests if total_requests > 0 else 0.0

            # Calculate latency percentiles
            all_latencies = []
            for stats in self._scenario_stats.values():
                all_latencies.extend(stats['latencies'])

            if all_latencies:
                all_latencies.sort()
                avg_latency = sum(all_latencies) / len(all_latencies) * 1000
                p50_idx = int(len(all_latencies) * 0.5)
                p95_idx = int(len(all_latencies) * 0.95)
                p99_idx = int(len(all_latencies) * 0.99)

                p50_latency = all_latencies[p50_idx] * 1000
                p95_latency = all_latencies[min(p95_idx, len(all_latencies) - 1)] * 1000
                p99_latency = all_latencies[min(p99_idx, len(all_latencies) - 1)] * 1000
            else:
                avg_latency = p50_latency = p95_latency = p99_latency = 0.0

            # Calculate cache hit rate
            total_cache_hits = sum(self._cache_hits.values())
            total_cache_misses = sum(self._cache_misses.values())
            total_cache = total_cache_hits + total_cache_misses
            cache_hit_rate = total_cache_hits / total_cache if total_cache > 0 else 0.0

            return MetricsSummary(
                total_requests=total_requests,
                successful_requests=total_success,
                failed_requests=total_failure,
                success_rate=success_rate,
                avg_latency_ms=avg_latency,
                p50_latency_ms=p50_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                cache_hit_rate=cache_hit_rate,
                active_requests=int(self._gauges.get('active_requests', 0))
            )

    def get_scenario_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get per-scenario statistics."""
        with self._lock:
            result = {}
            for scenario, stats in self._scenario_stats.items():
                total = stats['success'] + stats['failure']
                latencies = stats['latencies']

                result[scenario] = {
                    'total_requests': total,
                    'success_count': stats['success'],
                    'failure_count': stats['failure'],
                    'success_rate': stats['success'] / total if total > 0 else 0.0,
                    'avg_latency_ms': (
                        sum(latencies) / len(latencies) * 1000
                        if latencies else 0.0
                    ),
                }

            return result

    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache statistics."""
        with self._lock:
            result = {}
            all_types = set(self._cache_hits.keys()) | set(self._cache_misses.keys())

            for cache_type in all_types:
                hits = self._cache_hits.get(cache_type, 0)
                misses = self._cache_misses.get(cache_type, 0)
                total = hits + misses

                result[cache_type] = {
                    'hits': hits,
                    'misses': misses,
                    'total': total,
                    'hit_rate': hits / total if total > 0 else 0.0,
                }

            return result

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._latencies.clear()
            self._counters.clear()
            self._gauges.clear()
            self._scenario_stats.clear()
            self._cache_hits.clear()
            self._cache_misses.clear()
            self._start_time = time.time()

    def get_uptime_seconds(self) -> float:
        """Get collector uptime in seconds."""
        return time.time() - self._start_time


# Module-level singleton
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
