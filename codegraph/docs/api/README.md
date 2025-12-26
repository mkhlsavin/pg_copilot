# API Documentation

> REST API and WebSocket interface documentation for CodeGraph.


## API Reference

| Document | Description |
|----------|-------------|
| [REST API](en/REST_API.md) | Complete HTTP API reference with examples |
| [WebSocket API](en/WEBSOCKET_API.md) | Real-time streaming interface |

## Quick Start

```bash
# Start the API server
python -m src.api.cli serve

# Check API health
curl http://localhost:8000/health

# Get auth token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

## Authentication

All endpoints (except `/health`) require JWT authentication:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/scenarios
```

## Related Documentation

- [Getting Started](../getting-started/README.md)
- [TUI User Guide](../guides/en/TUI_USER_GUIDE.md)
- [Configuration](../getting-started/en/CONFIGURATION.md)
