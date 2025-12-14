# Monitoring Guide

This guide covers monitoring, metrics, and health checks for RAG-CPGQL in production environments.

## Overview

The monitoring module provides:
- **Prometheus metrics** for observability
- **Structured JSON logging** for analysis
- **Health check endpoints** for orchestration
- **Monitoring decorators** for instrumentation

---

## Quick Start

### Enable Metrics

```python
from src.monitoring import (
    MetricsCollector,
    track_execution,
    track_agent,
    setup_structured_logging
)

# Setup structured logging
setup_structured_logging(log_level="INFO")

# Get metrics collector
metrics = MetricsCollector()

# Use decorators for automatic tracking
@track_execution("my_operation")
def process_query(query: str):
    # Your code here
    return result
```

### Health Check Server

```python
from src.monitoring.health import HealthCheckServer

# Start health check server (runs alongside main app)
health_server = HealthCheckServer(port=8081)
health_server.start()

# Endpoints available:
# GET /health    - Overall health status
# GET /ready     - Readiness probe
# GET /live      - Liveness probe
# GET /metrics   - Prometheus metrics
# GET /stats     - System statistics
```

---

## Prometheus Metrics

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rag_scenario_duration_seconds` | Histogram | scenario_name | Scenario execution time |
| `rag_scenario_success_total` | Counter | scenario_name | Successful executions |
| `rag_scenario_failure_total` | Counter | scenario_name, error_type | Failed executions |
| `rag_agent_duration_seconds` | Histogram | agent_name, scenario | Agent execution time |
| `rag_agent_success_total` | Counter | agent_name, scenario | Agent successes |
| `rag_agent_failure_total` | Counter | agent_name, scenario, error_type | Agent failures |
| `rag_cache_hits_total` | Counter | cache_name | Cache hits |
| `rag_cache_misses_total` | Counter | cache_name | Cache misses |
| `rag_llm_requests_total` | Counter | model, status | LLM API requests |
| `rag_llm_duration_seconds` | Histogram | model | LLM latency |
| `rag_llm_tokens_total` | Counter | model, type | Tokens used |
| `rag_query_duration_seconds` | Histogram | query_type | Database query time |
| `rag_active_connections` | Gauge | - | Active connections |

### Histogram Buckets

```python
# Scenario duration buckets (seconds)
[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]

# Agent duration buckets (seconds)
[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

# Query duration buckets (milliseconds)
[1, 5, 10, 25, 50, 100, 250, 500, 1000]
```

### Recording Metrics

```python
from src.monitoring.metrics import (
    SCENARIO_DURATION,
    SCENARIO_SUCCESS,
    SCENARIO_FAILURE,
    LLM_REQUESTS,
    LLM_DURATION,
    LLM_TOKENS
)

# Record scenario execution
with SCENARIO_DURATION.labels(scenario_name="security_audit").time():
    result = run_scenario()

SCENARIO_SUCCESS.labels(scenario_name="security_audit").inc()

# Record LLM usage
LLM_REQUESTS.labels(model="GigaChat-2-Pro", status="success").inc()
LLM_DURATION.labels(model="GigaChat-2-Pro").observe(2.5)
LLM_TOKENS.labels(model="GigaChat-2-Pro", type="completion").inc(150)
```

---

## Decorators

### @track_execution

Automatically tracks function execution time and success/failure.

```python
from src.monitoring import track_execution

@track_execution("data_processing")
def process_data(data: list) -> dict:
    # Automatically records:
    # - Duration to rag_operation_duration_seconds
    # - Success/failure to rag_operation_total
    return processed_data

@track_execution("api_call", log_args=True)
def call_api(url: str, params: dict) -> dict:
    # Also logs function arguments
    return response
```

### @track_agent

Track agent execution with scenario context.

```python
from src.monitoring import track_agent

@track_agent("analyzer")
def run_analyzer(question: str, scenario: str):
    # Records to rag_agent_* metrics
    return analysis
```

### @track_scenario

Track complete scenario execution.

```python
from src.monitoring import track_scenario

@track_scenario("security_audit")
def run_security_audit(codebase: str):
    # Records to rag_scenario_* metrics
    return findings
```

---

## Health Checks

### Health Status

```python
class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
```

### Component Health

The system checks these components:

| Component | Check | Threshold |
|-----------|-------|-----------|
| Database | Query latency | < 100ms |
| LLM Provider | API response | < 5s |
| Vector Store | Query latency | < 200ms |
| Cache | Read/write | < 50ms |
| Joern | Connection | < 1s |

### Custom Health Checks

```python
from src.monitoring.health import HealthChecker, ComponentHealth, HealthStatus

checker = HealthChecker()

# Add custom component check
def check_custom_service():
    try:
        response_time = ping_service()
        if response_time < 100:
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.HEALTHY,
                latency_ms=response_time
            )
        else:
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.DEGRADED,
                latency_ms=response_time,
                message="High latency"
            )
    except Exception as e:
        return ComponentHealth(
            name="custom_service",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )

checker.add_check("custom_service", check_custom_service)
```

### Health Endpoints

**GET /health**
```json
{
  "status": "healthy",
  "components": [
    {
      "name": "database",
      "status": "healthy",
      "latency_ms": 2.5,
      "message": ""
    },
    {
      "name": "llm_provider",
      "status": "healthy",
      "latency_ms": 450.0,
      "message": ""
    }
  ],
  "timestamp": 1702580000.0,
  "uptime_seconds": 3600.0,
  "version": "2.0.0"
}
```

**GET /ready**
```json
{
  "ready": true,
  "checks_passed": 4,
  "checks_total": 4
}
```

**GET /live**
```json
{
  "alive": true,
  "uptime_seconds": 3600.0
}
```

---

## Structured Logging

### Setup

```python
from src.monitoring import setup_structured_logging

# Configure structured logging
setup_structured_logging(
    log_level="INFO",
    json_format=True,
    include_timestamp=True,
    include_caller=True
)
```

### Log Format

```json
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "level": "INFO",
  "logger": "src.agents.analyzer",
  "message": "Query processed",
  "context": {
    "scenario": "security_audit",
    "query_id": "abc123",
    "duration_ms": 245
  },
  "caller": {
    "file": "analyzer.py",
    "line": 45,
    "function": "process_query"
  }
}
```

### Context Logging

```python
from src.monitoring import log_context, get_logger

logger = get_logger(__name__)

# Add context to all logs in scope
with log_context(request_id="abc123", user_id="user1"):
    logger.info("Processing request")  # Includes request_id and user_id

    result = process()

    logger.info("Request completed", extra={"result_count": len(result)})
```

---

## Grafana Dashboards

### Recommended Panels

**Request Rate:**
```promql
rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m])
```

**Error Rate:**
```promql
rate(rag_scenario_failure_total[5m]) / (rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m]))
```

**P95 Latency:**
```promql
histogram_quantile(0.95, rate(rag_scenario_duration_seconds_bucket[5m]))
```

**LLM Token Usage:**
```promql
sum(rate(rag_llm_tokens_total[1h])) by (model)
```

**Cache Hit Rate:**
```promql
rate(rag_cache_hits_total[5m]) / (rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))
```

### Alert Rules

```yaml
groups:
  - name: rag-cpgql
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(rag_scenario_failure_total[5m]))
          / sum(rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m]))
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(rag_scenario_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 30s"

      - alert: ComponentUnhealthy
        expr: rag_component_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Component {{ $labels.component }} is unhealthy"
```

---

## Kubernetes Integration

### Deployment Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-cpgql
spec:
  template:
    spec:
      containers:
        - name: rag-cpgql
          ports:
            - containerPort: 8000
              name: api
            - containerPort: 8081
              name: health
          livenessProbe:
            httpGet:
              path: /live
              port: health
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: health
            initialDelaySeconds: 10
            periodSeconds: 5
```

### ServiceMonitor for Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: rag-cpgql
spec:
  selector:
    matchLabels:
      app: rag-cpgql
  endpoints:
    - port: health
      path: /metrics
      interval: 30s
```

---

## Best Practices

1. **Use decorators** for automatic instrumentation
2. **Add context** to logs for traceability
3. **Set appropriate thresholds** for alerts
4. **Monitor token usage** to control costs
5. **Check P95/P99 latencies** not just averages
6. **Export metrics** to Prometheus for persistence
7. **Use structured logging** for log aggregation

---

## See Also

- [REST API Reference](../api/REST_API.md) - API endpoints
- [Deployment Readiness](../development/DEPLOYMENT_READINESS_PLAN.md) - Production setup
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
