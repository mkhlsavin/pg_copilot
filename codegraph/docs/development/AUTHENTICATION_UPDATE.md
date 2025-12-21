# Authentication Update Summary

## Overview

Added authentication to all API endpoints except demo and health check endpoints.

## Changes Made

### 1. Protected Endpoints (Authentication Added)

#### `src/api/routers/scenarios.py`
- `GET /api/v1/scenarios` - List all scenarios
- `GET /api/v1/scenarios/{scenario_id}` - Get specific scenario
- `POST /api/v1/scenarios/{scenario_id}/query` - Query a scenario

All methods now require `current_user: User = Depends(get_current_active_user)`

#### `src/api/routers/import_project.py`
- `GET /api/v1/import/languages` - List supported languages
- `POST /api/v1/import/start` - Start project import
- `GET /api/v1/import/status/{job_id}` - Get import status
- `GET /api/v1/import/jobs` - List import jobs
- `DELETE /api/v1/import/cancel/{job_id}` - Cancel import job
- `POST /api/v1/import/step` - Run single import step

All methods now require `current_user: User = Depends(get_current_active_user)`

### 2. Unprotected Endpoints (Remain Public)

#### Demo Endpoints (`src/api/routers/demo.py`)
- `POST /api/v1/demo/chat` - Public demo with IP-based rate limiting (30 req/min)
- `GET /api/v1/demo/status` - Demo status check

These endpoints are intentionally kept public for landing page demonstration.

#### Health Check Endpoints (`src/api/routers/health.py`)
- `GET /api/v1/health` - Full health check
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/version` - API version

These endpoints are kept public for monitoring and orchestration systems.

#### Authentication Endpoints (`src/api/routers/auth.py`)
- `POST /api/v1/auth/token` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `DELETE /api/v1/auth/logout` - Logout
- All other auth endpoints

These endpoints must remain public for users to authenticate.

### 3. Test Infrastructure Updates

#### `tests/api/conftest.py`
Added automatic authentication bypass for all tests by overriding the `get_current_active_user` dependency in the test app fixture. This allows existing tests to continue working without modification.

```python
# Override authentication dependency - return mock user for all tests
async def override_get_current_active_user():
    return User(
        id=uuid.uuid4(),
        username="test_user",
        email="test@example.com",
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ANALYST,
        is_active=True,
        ...
    )
```

## Authentication Mechanism

All protected endpoints now use:
```python
from src.api.dependencies import get_current_active_user

async def endpoint(..., current_user: User = Depends(get_current_active_user)):
    ...
```

The `get_current_active_user` dependency:
1. Checks for JWT token in `Authorization: Bearer <token>` header
2. Checks for API key in `X-API-Key` header
3. Validates the token/key
4. Verifies the user is active
5. Returns the authenticated User object or raises HTTP 401/403

## Testing

All existing tests continue to work because the test fixture automatically overrides the authentication dependency with a mock user.

To test with actual authentication:
```python
# Use the auth_headers fixture
async def test_with_auth(async_client, test_user, auth_headers):
    response = await async_client.get("/api/v1/scenarios", headers=auth_headers)
    assert response.status_code == 200
```

## Impact

### Breaking Changes
- All previously unprotected endpoints now require authentication
- API clients must include either:
  - JWT token: `Authorization: Bearer <token>`
  - API key: `X-API-Key: <key>`

### No Breaking Changes For
- Demo endpoints (remain public)
- Health check endpoints (remain public)
- Authentication endpoints (remain public)
- Existing tests (automatic mock authentication)

## Migration Guide

For existing API clients:

1. Obtain JWT token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

2. Use token in requests:
```bash
curl http://localhost:8000/api/v1/scenarios \
  -H "Authorization: Bearer <your_token>"
```

Or use API key:
```bash
curl http://localhost:8000/api/v1/scenarios \
  -H "X-API-Key: <your_api_key>"
```

## Files Modified

1. `src/api/routers/scenarios.py` - Added auth to 3 endpoints
2. `src/api/routers/import_project.py` - Added auth to 6 endpoints
3. `tests/api/conftest.py` - Added automatic auth override for tests

## Security Considerations

- Demo endpoints use IP-based rate limiting to prevent abuse
- All authenticated endpoints verify user is active
- JWT tokens expire after 30 minutes
- API keys can be revoked by users
- No endpoints are accessible without authentication except explicitly designed public endpoints
