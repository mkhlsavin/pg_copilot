# Quick Start Guide

Get CodeGraph API running in 10 minutes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start: API Server](#quick-start-api-server)
  - [Step 1: Clone and Install](#step-1-clone-and-install)
  - [Step 2: Set Database Password](#step-2-set-database-password)
  - [Step 3: Initialize Database](#step-3-initialize-database)
  - [Step 4: Create Admin User](#step-4-create-admin-user)
  - [Step 5: Start API Server](#step-5-start-api-server)
  - [Step 6: Verify Installation](#step-6-verify-installation)
- [Common Use Cases](#common-use-cases)
  - [Use Case 1: Access API Documentation](#use-case-1-access-api-documentation)
  - [Use Case 2: Test with Sample Queries](#use-case-2-test-with-sample-queries)
  - [Use Case 3: Create an API Key for Programmatic Access](#use-case-3-create-an-api-key-for-programmatic-access)
- [Quick Configuration](#quick-configuration)
  - [Change Server Port](#change-server-port)
  - [Enable Auto-Reload for Development](#enable-auto-reload-for-development)
  - [Run with Multiple Workers (Production)](#run-with-multiple-workers-production)
- [Troubleshooting](#troubleshooting)
  - [Database Connection Failed](#database-connection-failed)
  - [Port Already in Use](#port-already-in-use)
  - [PostgreSQL Not Running](#postgresql-not-running)
- [API Endpoints Overview](#api-endpoints-overview)
- [Next Steps](#next-steps)
  - [Essential Reading](#essential-reading)
  - [Advanced Topics](#advanced-topics)
  - [Optional Integrations](#optional-integrations)
- [Example: Complete Workflow](#example-complete-workflow)
- [Tips for Success](#tips-for-success)
- [Getting Help](#getting-help)

## Prerequisites

- Python 3.10+ (3.11 recommended)
- PostgreSQL 15+ (running and accessible)
- 16GB RAM minimum
- 50GB free disk space

## Quick Start: API Server

### Step 1: Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd codegraph

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Set Database Password

```bash
# Set your PostgreSQL password
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# On Windows PowerShell:
$env:DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"
```

**Note:** Replace `your_password` with your actual PostgreSQL postgres user password.

### Step 3: Initialize Database

```bash
# Create database and tables
python -m src.api.cli init-db
```

Expected output:
```
Database initialized successfully
```

### Step 4: Create Admin User

```bash
# Create admin account
python -m src.api.cli create-admin --username admin --password admin123

# For production, use a strong password:
python -m src.api.cli create-admin --username admin --password <strong_password>
```

Expected output:
```
Admin user created: admin (ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
```

### Step 5: Start API Server

```bash
# Start the server
python -m src.api.cli run --host 127.0.0.1 --port 8000
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 6: Verify Installation

#### Option A: Use Swagger UI (Recommended)

Open your browser and visit:
**http://127.0.0.1:8000/api/docs**

You'll see the interactive API documentation where you can:
1. Click "Authorize" button
2. Use POST /api/v1/auth/token to get a JWT token
3. Try out API endpoints interactively

#### Option B: Use curl

```bash
# 1. Check health
curl http://127.0.0.1:8000/api/v1/health

# 2. Get authentication token
curl -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Expected response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

```bash
# 3. Use the token (replace TOKEN with your access_token)
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "Authorization: Bearer TOKEN"
```

## Common Use Cases

### Use Case 1: Access API Documentation

```bash
# Start server
python -m src.api.cli run --host 127.0.0.1 --port 8000

# Open browser to:
# http://127.0.0.1:8000/api/docs (Swagger UI)
# http://127.0.0.1:8000/api/redoc (ReDoc)
```

### Use Case 2: Test with Sample Queries

```bash
# Get token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Query scenarios
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "Authorization: Bearer $TOKEN"

# Start a chat session
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find all functions that handle user authentication",
    "scenario_id": "security_review"
  }'
```

### Use Case 3: Create an API Key for Programmatic Access

```bash
# Get JWT token first
TOKEN="your_access_token"

# Create API key
curl -X POST http://127.0.0.1:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application",
    "expires_days": 365,
    "scopes": ["scenarios:read", "query:execute"]
  }'

# Use API key for requests
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "X-API-Key: your_api_key"
```

## Quick Configuration

### Change Server Port

```bash
# Run on different port
python -m src.api.cli run --host 127.0.0.1 --port 8080
```

### Enable Auto-Reload for Development

```bash
# Auto-reload on code changes
python -m src.api.cli run --host 127.0.0.1 --port 8000 --reload
```

### Run with Multiple Workers (Production)

```bash
# Use 4 worker processes
python -m src.api.cli run --host 0.0.0.0 --port 8000 --workers 4
```

## Troubleshooting

### Database Connection Failed

```bash
# Error: "database does not exist"
# Solution: Run init-db command
python -m src.api.cli init-db
```

```bash
# Error: "password authentication failed"
# Solution: Check your DATABASE_URL password
export DATABASE_URL="postgresql+asyncpg://postgres:correct_password@localhost:5432/codegraph"
```

### Port Already in Use

```bash
# Error: "Address already in use"
# Solution: Kill process on port 8000

# Windows:
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# Linux:
lsof -ti:8000 | xargs kill -9

# Or use a different port:
python -m src.api.cli run --host 127.0.0.1 --port 8001
```

### PostgreSQL Not Running

```bash
# Check PostgreSQL status
# Windows:
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql
```

## API Endpoints Overview

Once your server is running, you have access to:

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Auth** | `POST /api/v1/auth/token` | Get JWT access token |
| | `POST /api/v1/auth/refresh` | Refresh access token |
| | `POST /api/v1/auth/api-keys` | Create API key |
| **Chat** | `POST /api/v1/chat` | Send chat message |
| | `POST /api/v1/chat/stream` | Streaming chat |
| **Scenarios** | `GET /api/v1/scenarios` | List analysis scenarios |
| | `POST /api/v1/scenarios/{id}/query` | Execute scenario query |
| **Query** | `POST /api/v1/query/execute` | Execute custom query |
| **Review** | `POST /api/v1/review/patch` | Review code patch |
| | `POST /api/v1/review/pr` | Review pull request |
| **Sessions** | `GET /api/v1/sessions` | List user sessions |
| | `GET /api/v1/sessions/{id}` | Get session details |
| **Health** | `GET /api/v1/health` | System health check |

For complete API documentation, visit **http://127.0.0.1:8000/api/docs** after starting the server.

## Next Steps

### Essential Reading

- **[Installation Guide](INSTALLATION.md)** - Detailed setup including PostgreSQL, LLM providers, and Joern
- **[Configuration Guide](CONFIGURATION.md)** - Configure authentication, rate limiting, CORS, and LLM providers
- **[API Reference](../api/REST_API.md)** - Complete API endpoint documentation

### Advanced Topics

- **[TUI User Guide](../guides/TUI_USER_GUIDE.md)** - Learn how to use scenarios and workflows
- **[Scenarios Guide](../guides/SCENARIOS.md)** - Pre-built analysis scenarios
- **[Troubleshooting](../guides/TROUBLESHOOTING.md)** - Common issues and solutions

### Optional Integrations

- **[GigaChat Integration](../integrations/GIGACHAT.md)** - Russian LLM provider
- **[Joern Legacy](../archive/JOERN_LEGACY.md)** - CPG analysis (archived, migrated to DuckDB)
- **[Project Import](../guides/PROJECT_IMPORT.md)** - Import and analyze projects

## Example: Complete Workflow

Here's a complete example workflow for analyzing code security:

```bash
# 1. Set environment
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# 2. Initialize database
python -m src.api.cli init-db

# 3. Create admin user
python -m src.api.cli create-admin --username admin --password SecurePass123

# 4. Start server
python -m src.api.cli run --host 127.0.0.1 --port 8000 &

# 5. Get auth token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SecurePass123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 6. List available scenarios
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 7. Execute security review scenario
curl -X POST http://127.0.0.1:8000/api/v1/scenarios/security_review/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find potential SQL injection vulnerabilities",
    "options": {"detailed": true}
  }' | python -m json.tool

# 8. Start interactive chat
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all authentication-related functions",
    "scenario_id": "security_review"
  }' | python -m json.tool
```

## Tips for Success

1. **Use Swagger UI for exploration** - The interactive docs at `/api/docs` make it easy to try endpoints
2. **Save your access token** - Tokens are valid for 30 minutes by default
3. **Check logs for errors** - Server logs show detailed error messages
4. **Start with health check** - Always verify `/api/v1/health` shows healthy status
5. **Use API keys for automation** - Create API keys for scripts and applications

## Getting Help

- Check the [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)
- Review logs for error messages
- Verify database connection with health endpoint
- Ensure PostgreSQL is running and accessible
- Check that DATABASE_URL is correctly set

---

**Ready to dive deeper?** Check out the [Installation Guide](INSTALLATION.md) for full setup options and the [Configuration Guide](CONFIGURATION.md) for advanced settings.
