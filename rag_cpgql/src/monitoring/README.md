# Monitoring Module

System monitoring and observability for RAG-CPGQL including metrics, logging, and health checks.

## Overview

```
src/monitoring/
├── metrics.py           # Prometheus metrics
├── tracing.py           # Distributed tracing
├── health.py            # Health check utilities
└── __init__.py
```

## Metrics

- Query latency
- LLM token usage
- Cache hit rate
- Error rates
- Active sessions

## Usage

```python
from src.monitoring.metrics import track_query

@track_query
async def process_query(query: str):
    # Query processing
    pass
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/metrics` | Prometheus metrics |
| `/health` | Health check |
| `/ready` | Readiness probe |

## See Also

- `/src/api/routers/health.py` - Health endpoints
