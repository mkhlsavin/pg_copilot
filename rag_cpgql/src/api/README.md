# API Module

FastAPI-based REST API providing web access to RAG-CPGQL functionality including authentication, analysis scenarios, code review, and real-time WebSocket communication.

## Overview

```
src/api/
├── main.py              # Application factory and lifespan
├── config.py            # API settings and configuration
├── dependencies.py      # FastAPI dependency injection
├── cli.py               # CLI commands for API management
├── auth/                # Authentication system
│   ├── jwt_handler.py   # JWT token management
│   ├── oauth.py         # OAuth2 providers (GitHub, GitLab, Google)
│   ├── ldap_auth.py     # LDAP/Active Directory integration
│   └── api_key.py       # API key authentication
├── routers/             # API route definitions
│   ├── auth.py          # Authentication endpoints
│   ├── scenarios.py     # Analysis scenarios
│   ├── chat.py          # Chat interface
│   ├── query.py         # Direct CPGQL queries
│   ├── review.py        # Code review endpoints
│   ├── sessions.py      # Session management
│   ├── history.py       # Query history
│   ├── health.py        # Health checks
│   ├── stats.py         # Statistics
│   ├── demo.py          # Demo mode
│   ├── import_project.py # Project import
│   ├── groups.py        # Project groups
│   └── projects.py      # Project management
├── services/            # Business logic layer
│   ├── job_service.py   # Background job management
│   └── session_service.py # Session handling
├── database/            # SQLAlchemy models and repositories
│   ├── models.py        # User, Session, Job, ApiKey models
│   ├── connection.py    # Async PostgreSQL connection
│   └── repositories/    # Data access layer
├── websocket/           # Real-time communication
│   ├── routes.py        # WebSocket endpoints
│   ├── manager.py       # Connection management
│   ├── models.py        # Message types
│   └── handlers.py      # Message handlers
├── models/              # Pydantic request/response models
├── rate_limit/          # Rate limiting
├── logging/             # Structured logging
└── utils/               # Utility functions
```

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | User login with username/password |
| POST | `/register` | User registration |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Revoke token (logout) |
| GET | `/me` | Get current user info |
| POST | `/oauth/{provider}` | OAuth2 login |

### Scenarios (`/api/v1/scenarios`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List available scenarios |
| GET | `/{id}` | Get scenario details |
| POST | `/{id}/query` | Execute scenario query |

### Query (`/api/v1/query`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Execute natural language query |
| POST | `/cpgql` | Execute raw CPGQL query |

### Health (`/api/v1/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Full system health check |
| GET | `/live` | Kubernetes liveness probe |
| GET | `/ready` | Kubernetes readiness probe |

### WebSocket (`/api/v1/ws`)

| Endpoint | Description |
|----------|-------------|
| `/chat` | Real-time chat with streaming responses |
| `/jobs/{job_id}` | Job progress updates |
| `/notifications` | Push notifications |

## Authentication

### JWT Tokens

```python
from src.api.auth.jwt_handler import create_access_token, verify_token

# Create token
token = create_access_token(user_id="123", scopes=["read", "write"])

# Verify token
payload = verify_token(token)
```

### OAuth2 Providers

Supported providers:
- GitHub
- GitLab
- Google

### API Keys

```python
# Use API key header
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/query
```

## Configuration

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 4

cors:
  origins: ["http://localhost:3000"]
  allow_credentials: true

jwt:
  secret: "${JWT_SECRET}"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7

database:
  url: "postgresql+asyncpg://user:pass@localhost/ragcpgql"
  pool_size: 5
  max_overflow: 10

rate_limit:
  enabled: true
  requests_per_minute: 60
```

## Running the API

### Development

```bash
# With uvicorn (auto-reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or via CLI
python -m src.api.cli run --reload
```

### Production

```bash
# With gunicorn
gunicorn src.api.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000

# With Docker
docker-compose up api
```

## Database Models

| Model | Description |
|-------|-------------|
| `User` | User accounts |
| `ApiKey` | API key authentication |
| `Session` | User sessions |
| `DialogueTurn` | Chat history |
| `BackgroundJob` | Async job tracking |
| `TokenBlacklist` | Revoked JWT tokens |
| `AuditLog` | Security audit log |
| `ProjectGroup` | Project grouping |
| `Project` | Project metadata |
| `ImportJob` | Import job tracking |

## Rate Limiting

```python
from src.api.rate_limit import RateLimiter

# Global rate limit
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    limiter = RateLimiter(requests_per_minute=60)
    if not await limiter.allow(request):
        raise HTTPException(429, "Rate limit exceeded")
    return await call_next(request)
```

## Error Handling

Standard error response format:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {},
  "request_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Dependencies

- `fastapi` - Web framework
- `sqlalchemy[asyncio]` - ORM with async support
- `asyncpg` - PostgreSQL async driver
- `python-jose` - JWT handling
- `passlib` - Password hashing
- `httpx` - HTTP client
- `websockets` - WebSocket support

## See Also

- `/docs/reference/API.md` - Full API reference
- `/src/workflow/scenarios/` - Scenario implementations
- `/docs/getting-started/README.md` - Quick start guide
