# RAG-CPGQL REST API Documentation

Complete documentation for the RAG-CPGQL REST API server.

## Overview

- **Framework:** FastAPI
- **Base URL:** `http://localhost:8000/api/v1`
- **OpenAPI Docs:** `/docs` (Swagger UI), `/redoc` (ReDoc)
- **Authentication:** JWT tokens, API keys, OAuth2, LDAP

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file (see [Environment Variables](#environment-variables)):

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Initialize Database

```bash
# Create tables
python -m src.api.cli init-db

# Run migrations
python -m src.api.cli migrate
```

### 4. Create Admin User

```bash
python -m src.api.cli create-admin --username admin --password your-secure-password
```

### 5. Start Server

```bash
python -m src.api.cli run --host 0.0.0.0 --port 8000
```

---

## Environment Variables

### Required

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/rag_cpgql` |
| `API_JWT_SECRET` | JWT signing secret (64+ chars) | `change-me-in-production...` |

### Server Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Server bind address | `0.0.0.0` |
| `API_PORT` | Server port | `8000` |
| `API_WORKERS` | Number of workers | `4` |
| `API_DEBUG` | Debug mode | `false` |

### Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `API_JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `API_ADMIN_USERNAME` | Default admin username | `admin` |
| `API_ADMIN_PASSWORD` | Default admin password | `admin` |

### OAuth2 Providers

#### GitHub
| Variable | Description |
|----------|-------------|
| `OAUTH_GITHUB_CLIENT_ID` | GitHub OAuth App Client ID |
| `OAUTH_GITHUB_CLIENT_SECRET` | GitHub OAuth App Client Secret |

#### Google
| Variable | Description |
|----------|-------------|
| `OAUTH_GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |

#### Keycloak
| Variable | Description |
|----------|-------------|
| `OAUTH_KEYCLOAK_SERVER_URL` | Keycloak server URL |
| `OAUTH_KEYCLOAK_REALM` | Keycloak realm |
| `OAUTH_KEYCLOAK_CLIENT_ID` | Keycloak client ID |
| `OAUTH_KEYCLOAK_CLIENT_SECRET` | Keycloak client secret |

### LDAP/Active Directory

| Variable | Description |
|----------|-------------|
| `LDAP_SERVER` | LDAP server hostname |
| `LDAP_BASE_DN` | Base DN for searches |
| `LDAP_BIND_USER` | Bind user DN |
| `LDAP_BIND_PASSWORD` | Bind user password |
| `LDAP_USER_SEARCH_BASE` | User search base |
| `LDAP_GROUP_SEARCH_BASE` | Group search base |

### Rate Limiting

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_STORAGE` | Storage backend (`memory` or `redis://...`) | `memory` |

### Demo Endpoint

| Variable | Description | Default |
|----------|-------------|---------|
| `DEMO_ENABLED` | Enable demo endpoint | `true` |
| `DEMO_RATE_LIMIT` | Demo rate limit | `30/minute` |

---

## Authentication

### JWT Token Authentication

#### Login (Get Token)

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Using JWT in Requests

```http
Authorization: Bearer <access_token>
```

### API Key Authentication

#### Create API Key

```http
POST /api/v1/auth/api-keys
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "my-integration",
  "expires_days": 365,
  "scopes": ["scenarios:read", "query:execute"]
}
```

**Response:**
```json
{
  "id": "key_abc123",
  "name": "my-integration",
  "key": "rak_xxxxxxxxxxxxxxxxxxxx",
  "prefix": "rak_xxxx",
  "scopes": ["scenarios:read", "query:execute"],
  "expires_at": "2025-12-09T00:00:00Z",
  "created_at": "2024-12-09T00:00:00Z"
}
```

#### Using API Key in Requests

```http
X-API-Key: rak_xxxxxxxxxxxxxxxxxxxx
```

#### List API Keys

```http
GET /api/v1/auth/api-keys
Authorization: Bearer <token>
```

#### Delete API Key

```http
DELETE /api/v1/auth/api-keys/{key_id}
Authorization: Bearer <token>
```

### OAuth2 Authentication

#### Start OAuth Flow

```http
GET /api/v1/auth/oauth/{provider}/authorize
```

Supported providers: `github`, `google`, `gitlab`, `keycloak`

#### OAuth Callback

```http
GET /api/v1/auth/oauth/{provider}/callback?code=xxx&state=xxx
```

### LDAP Authentication

```http
POST /api/v1/auth/ldap
Content-Type: application/json

{
  "username": "jdoe",
  "password": "ldap-password"
}
```

---

## API Endpoints

### Demo (Public - No Auth Required)

#### POST /api/v1/demo/chat

Public demo endpoint for landing page integration. Rate limited by IP address.

**Request:**
```json
{
  "query": "Как работает MVCC?",
  "language": "ru"
}
```

**Response:**
```json
{
  "answer": "MVCC (Multi-Version Concurrency Control)...",
  "scenario_id": "onboarding",
  "processing_time_ms": 1523.45
}
```

**Rate Limit:** 30 requests per minute per IP

#### GET /api/v1/demo/status

Check demo endpoint status.

**Response:**
```json
{
  "enabled": true,
  "rate_limit": "30/minute",
  "max_query_length": 500,
  "allowed_scenarios": ["onboarding"]
}
```

---

### Chat

#### POST /api/v1/chat

Send a query to the RAG-CPGQL system.

**Request:**
```json
{
  "query": "Find SQL injection vulnerabilities",
  "session_id": "optional-session-id",
  "scenario_id": "security",
  "language": "en"
}
```

**Response:**
```json
{
  "answer": "Found 3 potential SQL injection vulnerabilities...",
  "scenario_id": "security",
  "confidence": 0.85,
  "evidence": [
    {
      "type": "code",
      "source": "src/executor.c:123",
      "content": "sprintf(query, \"SELECT * FROM %s\", user_input);",
      "relevance": 0.95
    }
  ],
  "session_id": "sess_abc123",
  "request_id": "req_xyz789",
  "processing_time_ms": 2341.5
}
```

#### POST /api/v1/chat/stream

Send a query and receive streaming response via Server-Sent Events (SSE).

**Request:** Same as `/chat`

**Response:** SSE stream
```
data: {"type": "start", "session_id": "sess_abc123"}

data: {"type": "chunk", "content": "Found 3 potential "}

data: {"type": "chunk", "content": "SQL injection vulnerabilities..."}

data: {"type": "end", "scenario_id": "security"}
```

---

### Scenarios

#### GET /api/v1/scenarios

List all 16 available analysis scenarios.

**Response:**
```json
[
  {
    "id": "onboarding",
    "name": "Onboarding",
    "description": "Get started with a codebase - find functions, trace call graphs",
    "category": "Learning",
    "keywords": ["find", "where", "what", "how", "explain"],
    "example_queries": ["Where is the main() function?", "What does exec_simple_query do?"]
  },
  {
    "id": "security",
    "name": "Security Audit",
    "description": "Find security vulnerabilities - SQL injection, buffer overflows",
    "category": "Security",
    "keywords": ["vulnerability", "injection", "unsafe"],
    "example_queries": ["Find SQL injection vulnerabilities"]
  }
  // ... 14 more scenarios
]
```

#### GET /api/v1/scenarios/{scenario_id}

Get information about a specific scenario.

#### POST /api/v1/scenarios/{scenario_id}/query

Send a query to a specific scenario.

**Request:**
```json
{
  "query": "Find buffer overflow vulnerabilities",
  "session_id": "optional-session-id",
  "language": "en"
}
```

---

### Available Scenarios (16 total)

| ID | Name | Category | Description |
|----|------|----------|-------------|
| `onboarding` | Onboarding | Learning | Get started with codebase |
| `security` | Security Audit | Security | Find vulnerabilities |
| `documentation` | Documentation | Documentation | Generate docs |
| `feature_dev` | Feature Development | Development | Find integration points |
| `refactoring` | Refactoring | Quality | Identify code smells |
| `performance` | Performance Analysis | Performance | Find bottlenecks |
| `test_coverage` | Test Coverage | Testing | Analyze test coverage |
| `compliance` | Compliance Check | Quality | Check coding standards |
| `code_review` | Code Review | Review | Automated code review |
| `cross_repo` | Cross-Repository | Architecture | Analyze dependencies |
| `architecture` | Architecture Violations | Architecture | Detect violations |
| `tech_debt` | Technical Debt | Quality | Quantify tech debt |
| `mass_refactoring` | Mass Refactoring | Development | Large-scale changes |
| `security_incident` | Security Incident | Security | Incident response |
| `debugging` | Debugging Support | Development | Find logging points |
| `entry_points` | Entry Points | Security | Find attack surface |

---

### Code Review

#### POST /api/v1/review/patch

Review a git patch/diff.

**Request:**
```json
{
  "patch_content": "diff --git a/src/file.c b/src/file.c\n...",
  "task_description": "Fix memory leak in transaction handler",
  "dod_items": ["No memory leaks", "Unit tests pass"],
  "output_format": "json"
}
```

**Response:**
```json
{
  "recommendation": "REQUEST_CHANGES",
  "confidence": 0.82,
  "findings": [
    {
      "category": "error",
      "severity": "high",
      "location": {"file": "src/file.c", "line_start": 45},
      "message": "Potential memory leak: allocated memory not freed on error path",
      "suggested_fix": "Add free(ptr) before return statement"
    }
  ],
  "dod_status": [
    {"description": "No memory leaks", "satisfied": false, "evidence": "Found 1 potential leak"}
  ],
  "summary": "Found 1 high-severity issue that should be addressed."
}
```

#### POST /api/v1/review/github-pr

Review a GitHub Pull Request.

**Request:**
```json
{
  "owner": "postgres",
  "repo": "postgres",
  "pr_number": 123,
  "github_token": "ghp_xxx"
}
```

#### POST /api/v1/review/gitlab-mr

Review a GitLab Merge Request.

**Request:**
```json
{
  "project_id": "123",
  "mr_iid": 456,
  "gitlab_token": "glpat-xxx",
  "gitlab_url": "https://gitlab.com"
}
```

---

### Sessions

#### GET /api/v1/sessions

List user sessions.

#### POST /api/v1/sessions

Create new session.

#### GET /api/v1/sessions/{session_id}

Get session details.

#### DELETE /api/v1/sessions/{session_id}

Delete session.

---

### History

#### GET /api/v1/history

Get conversation history.

**Query Parameters:**
- `session_id` - Filter by session
- `limit` - Number of items (default: 50)
- `offset` - Pagination offset

#### GET /api/v1/history/{message_id}

Get specific message.

#### GET /api/v1/history/export

Export conversation history.

**Query Parameters:**
- `format` - Export format (`json`, `csv`, `markdown`)
- `session_id` - Filter by session

---

### Query (CPGQL)

#### POST /api/v1/query/execute

Execute a CPGQL/SQL query directly.

**Request:**
```json
{
  "query": "SELECT name, file FROM nodes_method WHERE name LIKE '%transaction%' LIMIT 10",
  "timeout_ms": 30000
}
```

**Response:**
```json
{
  "results": [
    {"name": "StartTransaction", "file": "xact.c"},
    {"name": "CommitTransaction", "file": "xact.c"}
  ],
  "row_count": 2,
  "execution_time_ms": 45.2
}
```

---

### Project Import

Import new codebases into the RAG-CPGQL system.

> **Detailed documentation:** See [Project Import Guide](../guides/PROJECT_IMPORT.md) for comprehensive usage examples.

#### GET /api/v1/import/languages

Get list of supported programming languages.

**Response:**
```json
{
  "languages": [
    {
      "id": "c",
      "name": "C",
      "extensions": [".c", ".h", ".cpp", ".hpp"],
      "joern_command": "c2cpg",
      "joern_flag": "C"
    },
    {
      "id": "java",
      "name": "JAVA",
      "extensions": [".java"],
      "joern_command": "javasrc2cpg",
      "joern_flag": "JAVASRC"
    }
  ]
}
```

**Supported Languages (10):**

| ID | Name | Joern Command | Extensions |
|----|------|---------------|------------|
| `c` | C/C++ | c2cpg | `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx` |
| `csharp` | C# | csharp2cpg | `.cs` |
| `go` | Go | gosrc2cpg | `.go` |
| `java` | Java | javasrc2cpg | `.java` |
| `javascript` | JavaScript/TypeScript | jssrc2cpg | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` |
| `kotlin` | Kotlin | kotlin2cpg | `.kt`, `.kts` |
| `php` | PHP | php2cpg | `.php` |
| `python` | Python | pysrc2cpg | `.py`, `.pyw` |
| `ruby` | Ruby | rubysrc2cpg | `.rb` |
| `swift` | Swift | swiftsrc2cpg | `.swift` |

#### POST /api/v1/import/start

Start asynchronous import of a new codebase.

**Request:**
```json
{
  "repo_url": "https://github.com/llvm/llvm-project",
  "branch": "main",
  "shallow_clone": true,
  "language": null,
  "mode": "full",
  "include_paths": ["llvm/lib", "llvm/include"],
  "exclude_paths": ["test", "tests"],
  "create_domain_plugin": true,
  "import_docs": true,
  "joern_memory_gb": 16,
  "batch_size": 10000
}
```

**Request Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_url` | string | - | Git repository URL (required if no `local_path`) |
| `local_path` | string | - | Local path (required if no `repo_url`) |
| `branch` | string | `"main"` | Git branch to clone |
| `shallow_clone` | boolean | `true` | Use shallow clone |
| `shallow_depth` | int | `1` | Shallow clone depth |
| `language` | string | `null` | Language ID (auto-detect if null) |
| `mode` | string | `"full"` | Import mode: `full`, `selective`, `incremental` |
| `include_paths` | list | `[]` | Paths to include |
| `exclude_paths` | list | `[]` | Paths to exclude |
| `create_domain_plugin` | boolean | `true` | Generate Domain Plugin |
| `domain_name` | string | `null` | Custom domain name |
| `import_docs` | boolean | `true` | Import documentation |
| `import_readme` | boolean | `true` | Index README files |
| `import_comments` | boolean | `true` | Import code comments |
| `joern_memory_gb` | int | `16` | Memory for Joern (GB) |
| `batch_size` | int | `10000` | DuckDB batch size |

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Import started. Use job_id to track progress."
}
```

#### GET /api/v1/import/status/{job_id}

Get current status of an import job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "llvm-project",
  "status": "in_progress",
  "steps": [
    {"name": "Clone Repository", "status": "completed", "progress": 100},
    {"name": "Detect Language", "status": "completed", "progress": 100},
    {"name": "Create CPG", "status": "in_progress", "progress": 45, "message": "Creating CPG nodes..."},
    {"name": "Export to DuckDB", "status": "pending", "progress": 0},
    {"name": "Validate CPG", "status": "pending", "progress": 0},
    {"name": "Import Documentation", "status": "pending", "progress": 0},
    {"name": "Setup Domain Plugin", "status": "pending", "progress": 0}
  ],
  "current_step": "joern_import",
  "overall_progress": 35,
  "created_at": "2024-12-09T10:00:00Z",
  "updated_at": "2024-12-09T10:05:00Z"
}
```

**Import Status Values:**
- `pending` - Waiting to start
- `in_progress` - Currently running
- `completed` - Successfully finished
- `failed` - Error occurred
- `cancelled` - Cancelled by user

#### GET /api/v1/import/jobs

List all import jobs.

**Query Parameters:**
- `status_filter` - Filter by status (e.g., `in_progress`, `completed`)
- `limit` - Maximum number of jobs (default: 20)

**Response:** Array of `ProjectImportStatus` objects.

#### DELETE /api/v1/import/cancel/{job_id}

Cancel a running import job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled"
}
```

#### POST /api/v1/import/step

Run a single step of the import pipeline.

**Request:**
```json
{
  "step_id": "validate",
  "context": {
    "duckdb_path": "./workspace/project.duckdb"
  }
}
```

**Valid Steps:**
- `clone` - Clone repository
- `detect_language` - Auto-detect programming language
- `joern_import` - Create Joern CPG
- `cpg_export` - Export CPG to DuckDB
- `validate` - Validate CPG quality
- `chromadb_import` - Import documentation to ChromaDB
- `domain_setup` - Create Domain Plugin

**Response:**
```json
{
  "step": "validate",
  "status": "completed",
  "result": {
    "validation_report": {
      "status": "passed",
      "quality_score": 85,
      "metrics": {...}
    }
  }
}
```

#### WebSocket: Progress Tracking

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/jobs/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'job.progress':
      console.log(`Progress: ${msg.payload.progress}% - ${msg.payload.message}`);
      break;
    case 'job.completed':
      console.log('Import completed:', msg.payload.result);
      break;
    case 'job.failed':
      console.error('Import failed:', msg.payload.error);
      break;
  }
};
```

---

### Stats

#### GET /api/v1/stats

Get system statistics.

**Response:**
```json
{
  "total_queries": 12345,
  "queries_today": 234,
  "average_response_time_ms": 1523.4,
  "scenarios_usage": {
    "onboarding": 4521,
    "security": 2341
  }
}
```

---

### Health

#### GET /api/v1/health

Full health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "timestamp": "2024-12-09T12:00:00Z",
  "components": {
    "database": {"status": "healthy", "latency_ms": 5.2},
    "llm": {"status": "healthy", "provider": "gigachat"},
    "joern": {"status": "healthy", "server": "localhost:9000"}
  }
}
```

#### GET /api/v1/health/live

Kubernetes liveness probe.

**Response:** `200 OK` if service is running.

```json
{"status": "ok"}
```

#### GET /api/v1/health/ready

Kubernetes readiness probe.

**Response:** `200 OK` if ready, `503` if not ready.

```json
{"status": "ready"}
```

#### GET /api/v1/health/version

Get API version.

```json
{
  "version": "1.0.0",
  "name": "RAG-CPGQL API"
}
```

---

## WebSocket Endpoints

### /ws/chat

Real-time chat connection.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=<jwt_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.send(JSON.stringify({
  type: 'query',
  query: 'Find SQL injection vulnerabilities',
  scenario_id: 'security'
}));
```

### /ws/jobs/{job_id}

Monitor background job progress.

### /ws/notifications

Receive real-time notifications.

---

## Rate Limiting

### Default Limits

- **Global:** 100 requests/minute, 1000 requests/hour

### Endpoint-Specific Limits

| Endpoint | Limit |
|----------|-------|
| `/api/v1/review/*` | 10/minute |
| `/api/v1/chat` | 60/minute |
| `/api/v1/chat/stream` | 30/minute |
| `/api/v1/query/execute` | 30/minute |
| `/api/v1/demo/chat` | 30/minute per IP |

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702123456
```

### Using Redis for Rate Limiting

For production with multiple instances, use Redis:

```bash
RATE_LIMIT_STORAGE=redis://localhost:6379
```

---

## RBAC Roles

| Role | Permissions |
|------|-------------|
| `viewer` | Read scenarios, view history |
| `analyst` | All viewer + execute queries, create sessions |
| `reviewer` | All analyst + code review, patch review |
| `admin` | Full access including user management |

---

## Database Setup

### PostgreSQL Connection

Requires PostgreSQL 12+ with async support.

```bash
# Create database
createdb rag_cpgql

# Set connection string
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/rag_cpgql"
```

### Alembic Migrations

```bash
# Apply all migrations
python -m src.api.cli migrate

# Migrate to specific revision
python -m src.api.cli migrate --revision abc123
```

### Database Schema

Main tables:
- `users` - User accounts
- `api_keys` - API key storage
- `sessions` - Chat sessions
- `messages` - Message history
- `jobs` - Background job status

---

## CLI Commands

```bash
# Run API server
python -m src.api.cli run [--host HOST] [--port PORT] [--workers N] [--reload]

# Initialize database
python -m src.api.cli init-db

# Run migrations
python -m src.api.cli migrate [--revision REV]

# Create admin user
python -m src.api.cli create-admin --username USER --password PASS [--email EMAIL]
```

---

## Example Usage (curl)

### Demo Endpoint (No Auth)

```bash
curl -X POST http://localhost:8000/api/v1/demo/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Как работает MVCC?", "language": "ru"}'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

### Chat with JWT

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIs..."

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find SQL injection vulnerabilities", "scenario_id": "security"}'
```

### List Scenarios

```bash
curl http://localhost:8000/api/v1/scenarios \
  -H "Authorization: Bearer $TOKEN"
```

### Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-integration", "expires_days": 365}'
```

### Use API Key

```bash
curl http://localhost:8000/api/v1/scenarios \
  -H "X-API-Key: rak_xxxxxxxxxxxxxxxxxxxx"
```

### Review Patch

```bash
curl -X POST http://localhost:8000/api/v1/review/patch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patch_content": "diff --git a/src/file.c ...",
    "task_description": "Fix memory leak",
    "output_format": "json"
  }'
```

---

## Error Responses

All errors return JSON with the following structure:

```json
{
  "detail": "Error message here",
  "error_code": "VALIDATION_ERROR",
  "request_id": "req_abc123"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Missing or invalid auth |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found |
| `429` | Too Many Requests - Rate limit exceeded |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

---

## Related Documentation

- [User Guide](../guides/USER_GUIDE.md)
- [Scenarios Guide](../guides/SCENARIOS.md)
- [Project Import Guide](../guides/PROJECT_IMPORT.md)
- [API Reference (Internal)](../reference/API.md)
- [Troubleshooting](../guides/TROUBLESHOOTING.md)
