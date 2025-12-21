# RBAC and Authorization

> Technical Documentation for IT and Security Teams

---

## Overview

CodeGraph implements a comprehensive Role-Based Access Control (RBAC) system with support for multiple authentication methods. The system provides granular access control to platform features.

### Key Capabilities

- **4 role levels** with hierarchical inheritance
- **21 granular permissions** across functional categories
- **Multiple authentication methods**: JWT, API keys, OAuth2, LDAP
- **Token blacklisting** for instant access revocation
- **SIEM integration** for authorization event auditing

---

## RBAC Architecture

### Role Hierarchy

```
                           ┌─────────────────────┐
                           │       ADMIN         │
                           │    (admin:all)      │
                           │    Full access      │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │      REVIEWER       │
                           │  Code review +      │
                           │  GitHub + GitLab    │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │      ANALYST        │
                           │  Query execution    │
                           │  + API keys         │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │       VIEWER        │
                           │    Read-only        │
                           └─────────────────────┘
```

### Permission Inheritance

Each role inherits all permissions from lower-level roles:
- `ADMIN` → all permissions (`admin:all`)
- `REVIEWER` → `ANALYST` permissions + code review
- `ANALYST` → `VIEWER` permissions + execution/export
- `VIEWER` → read-only (base level)

---

## Permission Catalog

### Permissions by Category

#### Scenarios (`scenarios:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `scenarios:read` | View scenario list | ✓ | ✓ | ✓ | ✓ |
| `scenarios:execute` | Run analysis scenarios | | ✓ | ✓ | ✓ |

#### Queries (`query:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `query:execute` | Execute SQL queries against CPG | | ✓ | ✓ | ✓ |
| `query:validate` | Validate query syntax | | ✓ | ✓ | ✓ |

#### Code Review (`review:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `review:execute` | Run automated review | | | ✓ | ✓ |
| `review:github` | GitHub PR integration | | | ✓ | ✓ |
| `review:gitlab` | GitLab MR integration | | | ✓ | ✓ |

#### Sessions (`sessions:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `sessions:read` | View sessions | ✓ | ✓ | ✓ | ✓ |
| `sessions:write` | Create/modify sessions | | ✓ | ✓ | ✓ |
| `sessions:delete` | Delete sessions | | ✓ | ✓ | ✓ |

#### History (`history:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `history:read` | View query history | ✓ | ✓ | ✓ | ✓ |
| `history:export` | Export history | | ✓ | ✓ | ✓ |

#### Users (`users:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `users:read` | View user list | | | | ✓ |
| `users:write` | Create/edit users | | | | ✓ |
| `users:delete` | Delete users | | | | ✓ |

#### API Keys (`api_keys:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `api_keys:read` | View own keys | | ✓ | ✓ | ✓ |
| `api_keys:write` | Create keys | | ✓ | ✓ | ✓ |
| `api_keys:delete` | Delete any keys | | | | ✓ |

#### Metrics (`stats:*`, `metrics:*`)
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `stats:read` | View statistics | ✓ | ✓ | ✓ | ✓ |
| `metrics:read` | Prometheus metrics | | | | ✓ |

#### Administration
| Permission | Description | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|-------------|:------:|:-------:|:--------:|:-----:|
| `admin:all` | Full access | | | | ✓ |

---

## Authentication Methods

### 1. JWT Bearer Token

Primary method for web applications and interactive sessions.

#### Token Structure

```python
class TokenPayload:
    sub: str       # User ID
    jti: str       # JWT ID (unique identifier)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str      # "access" or "refresh"
    scopes: list   # Permission list
    role: str      # User role
```

#### Token Parameters

| Token Type | TTL | Purpose |
|------------|-----|---------|
| Access Token | 30 minutes | API request authorization |
| Refresh Token | 7 days | Access token renewal |

#### Usage Example

```bash
# Get token
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst", "password": "***"}'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Use token
curl -X GET /api/v1/scenarios \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Token Revocation (Blacklisting)

```bash
# Logout - add token to blacklist
curl -X POST /api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

After blacklisting, the token becomes invalid immediately.

---

### 2. API Keys

For integrations, CI/CD, and automation.

#### API Key Format

```
Prefix: cgk_          (CodeGraph Key)
Secret: [36 chars]    (UUID v4)

Example: cgk_550e8400-e29b-41d4-a716-446655440000
```

#### Storage Security

- Keys are SHA-256 hashed before storage
- Full key shown only at creation time
- Support for expiration and revocation

#### Usage Example

```bash
# Create API key
curl -X POST /api/v1/auth/api-keys \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"name": "CI Pipeline", "scopes": ["query:execute", "scenarios:execute"]}'

# Response:
{
  "id": "key_123",
  "key": "cgk_550e8400-e29b-41d4-a716-446655440000",  # Shown only once!
  "name": "CI Pipeline",
  "scopes": ["query:execute", "scenarios:execute"],
  "expires_at": "2026-01-01T00:00:00Z"
}

# Use API key
curl -X GET /api/v1/scenarios \
  -H "X-API-Key: cgk_550e8400-e29b-41d4-a716-446655440000"
```

#### Default API Key Permissions

```python
default_scopes = [
    "scenarios:read",
    "scenarios:execute",
    "query:execute",
    "sessions:read",
    "sessions:write",
    "history:read",
]
```

---

### 3. OAuth2/OIDC (Integration-Ready)

Support for enterprise identity providers.

#### Supported Providers

| Provider | Status | Use Case |
|----------|--------|----------|
| GitHub | ✅ Ready | Developers, open-source |
| GitLab | ✅ Ready | Corporate GitLab |
| Google | ✅ Ready | Google Workspace |
| Keycloak | ✅ Ready | Enterprise IdP |
| Azure AD | ✅ Ready | Microsoft 365 |

#### Configuration (Keycloak Example)

```yaml
oauth2:
  providers:
    keycloak:
      enabled: true
      client_id: "codegraph"
      client_secret: "${KEYCLOAK_SECRET}"
      authorize_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/auth"
      token_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/token"
      userinfo_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/userinfo"
      scopes: ["openid", "profile", "email", "groups"]
      role_claim: "realm_access.roles"
      role_mapping:
        codegraph-admin: admin
        codegraph-reviewer: reviewer
        codegraph-analyst: analyst
        codegraph-viewer: viewer
```

---

### 4. LDAP/Active Directory (Integration-Ready)

Integration with corporate directory.

#### Configuration

```yaml
ldap:
  enabled: true
  server: "ldaps://ldap.company.com:636"
  base_dn: "dc=company,dc=com"
  bind_dn: "cn=codegraph,ou=services,dc=company,dc=com"
  bind_password: "${LDAP_PASSWORD}"
  user_search_base: "ou=users,dc=company,dc=com"
  user_search_filter: "(sAMAccountName={username})"
  group_search_base: "ou=groups,dc=company,dc=com"
  group_membership_attr: "memberOf"
  group_mapping:
    "CN=CodeGraph-Admins,OU=Groups,DC=company,DC=com": admin
    "CN=CodeGraph-Reviewers,OU=Groups,DC=company,DC=com": reviewer
    "CN=CodeGraph-Analysts,OU=Groups,DC=company,DC=com": analyst
    "CN=CodeGraph-Viewers,OU=Groups,DC=company,DC=com": viewer
  sync_interval_minutes: 15
```

#### Group Synchronization

- Automatic role sync with AD groups
- Nested group support
- Caching with configurable TTL

---

## API Reference

### Middleware Dependencies

```python
from src.api.auth.middleware import (
    get_auth_context,     # Get context (no error if unauthenticated)
    require_auth,         # Require any authentication
    require_permission,   # Require specific permission
    require_role,         # Require specific role
    require_admin,        # Shortcut for admin
    require_analyst,      # Shortcut for analyst+
    require_reviewer,     # Shortcut for reviewer+
)
```

### FastAPI Usage Examples

```python
from fastapi import Depends, APIRouter
from src.api.auth.middleware import require_permission, require_admin
from src.api.auth.permissions import Permission

router = APIRouter()

# Require specific permission
@router.post("/query/execute")
async def execute_query(
    query: str,
    auth = Depends(require_permission(Permission.QUERY_EXECUTE))
):
    # auth.user_id, auth.role, auth.scopes available
    return {"result": "..."}

# Require one of multiple permissions
@router.get("/reviews")
async def list_reviews(
    auth = Depends(require_any_permission(
        Permission.REVIEW_EXECUTE,
        Permission.REVIEW_GITHUB,
        Permission.REVIEW_GITLAB
    ))
):
    return {"reviews": [...]}

# Require Admin role
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    auth = Depends(require_admin)
):
    return {"deleted": user_id}
```

### AuthContext

```python
class AuthContext:
    user_id: str          # User ID
    username: str         # Username
    role: Role            # Role (VIEWER, ANALYST, REVIEWER, ADMIN)
    scopes: List[str]     # Permission list
    auth_method: str      # "jwt", "api_key", "oauth2", "ldap"

    @property
    def is_authenticated(self) -> bool:
        """Check authentication status"""

    def has_permission(self, permission: Permission) -> bool:
        """Check specific permission"""
```

---

## Auditing and Logging

### Authorization Events

All authorization events are logged and sent to SIEM:

| Event | Severity | Description |
|-------|----------|-------------|
| `AUTH_SUCCESS` | INFO | Successful authentication |
| `AUTH_FAILURE` | WARNING | Failed attempt |
| `TOKEN_ISSUED` | INFO | New token issued |
| `TOKEN_REVOKED` | INFO | Token revoked |
| `PERMISSION_DENIED` | WARNING | Access denied |
| `API_KEY_CREATED` | INFO | API key created |
| `API_KEY_REVOKED` | INFO | API key revoked |

### Log Format

```json
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "event_type": "AUTH_SUCCESS",
  "user_id": "user_123",
  "username": "analyst@company.com",
  "role": "analyst",
  "auth_method": "jwt",
  "ip_address": "10.0.0.50",
  "user_agent": "Mozilla/5.0...",
  "request_path": "/api/v1/scenarios",
  "request_method": "GET"
}
```

---

## Best Practices

### For Administrators

1. **Least privilege principle** — assign minimum necessary roles
2. **Use API keys with limited scopes** for automation
3. **Configure LDAP/AD sync** for centralized management
4. **Enable SIEM integration** for security event monitoring
5. **Regularly audit** active sessions and API keys

### For Developers

1. **Use JWT for web apps**, API keys for CI/CD
2. **Store refresh tokens securely** (httpOnly cookies)
3. **Handle 401/403** correctly in UI
4. **Never log tokens or keys** in plain text

---

## Related Documents

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Security overview
- [DLP Security](./DLP_SECURITY.md) — Data loss prevention
- [SIEM Integration](./SIEM.md) — SIEM integration
- [REST API Reference](../api/REST_API.md) — API reference

---

*Version: 1.0 | December 2025*
