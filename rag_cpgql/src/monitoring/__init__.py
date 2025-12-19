"""
Monitoring Infrastructure for CodeGraph System

Components:
- Metrics: Prometheus metrics definitions
- Health: Health check endpoints
- StructuredLogger: JSON-formatted logging

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

from src.monitoring.metrics import (
    SCENARIO_DURATION,
    SCENARIO_SUCCESS,
    SCENARIO_FAILURE,
    AGENT_DURATION,
    CACHE_HITS,
    CACHE_MISSES,
    ACTIVE_REQUESTS,
    LLM_LATENCY,
    CPG_QUERY_LATENCY,
    RETRIEVAL_LATENCY,
    StructuredLogger,
    monitor_scenario,
    monitor_agent,
    monitor_cache,
    record_llm_call,
    record_cpg_query,
    record_retrieval,
    MetricsCollector,
    get_metrics_collector,
)

from src.monitoring.health import (
    HealthChecker,
    create_health_app,
)

__all__ = [
    # Prometheus Metrics
    'SCENARIO_DURATION',
    'SCENARIO_SUCCESS',
    'SCENARIO_FAILURE',
    'AGENT_DURATION',
    'CACHE_HITS',
    'CACHE_MISSES',
    'ACTIVE_REQUESTS',
    'LLM_LATENCY',
    'CPG_QUERY_LATENCY',
    'RETRIEVAL_LATENCY',
    # Logging
    'StructuredLogger',
    # Decorators
    'monitor_scenario',
    'monitor_agent',
    'monitor_cache',
    'record_llm_call',
    'record_cpg_query',
    'record_retrieval',
    # Metrics Collection
    'MetricsCollector',
    'get_metrics_collector',
    # Health Checks
    'HealthChecker',
    'create_health_app',
]
