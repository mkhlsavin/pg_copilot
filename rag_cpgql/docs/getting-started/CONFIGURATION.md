# Configuration Guide

Configure CodeGraph for your environment.

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, database URLs) |
| `config.yaml` | Main configuration (LLM, retrieval, analysis) |
| `src/api/config.py` | API server configuration |
| `config/prompts/*.yaml` | Prompt templates |

## API Server Configuration

### Server Settings

Configure server host, port, and workers in environment variables or by passing CLI arguments:

**Via Environment Variables:**
```bash
export API_HOST="0.0.0.0"        # Bind to all interfaces
export API_PORT="8000"            # Port number
export API_WORKERS="4"            # Number of worker processes
export API_DEBUG="false"          # Debug mode (auto-reload)
```

**Via CLI Arguments:**
```bash
python -m src.api.cli run --host 0.0.0.0 --port 8000 --workers 4
```

### Database Configuration

The API requires PostgreSQL for user management, sessions, and audit logs.

**Connection String Format:**
```
postgresql+asyncpg://username:password@host:port/database
```

**Configuration via Environment Variable:**
```bash
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"
```

**Database Pool Settings:**

Edit `src/api/config.py` to customize connection pool:

```python
class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codegraph"
    pool_size: int = 10          # Number of connections to maintain
    max_overflow: int = 20        # Extra connections when pool is full
    pool_timeout: int = 30        # Seconds to wait for connection
    pool_recycle: int = 1800      # Recycle connections after 30 minutes
    echo: bool = False            # Log all SQL statements (debug only)
```

### Authentication Configuration

#### JWT Authentication

Configure JWT token settings:

```bash
# Secret key for signing tokens (CHANGE IN PRODUCTION!)
export API_JWT_SECRET="your-secret-key-min-64-chars-recommended"

# Token expiration (default: 30 minutes for access, 7 days for refresh)
export API_JWT_ACCESS_EXPIRE_MINUTES="30"
export API_JWT_REFRESH_EXPIRE_DAYS="7"
```

**In config.py:**
```python
class JWTConfig(BaseModel):
    secret_key: str = "change-me-in-production-use-64-chars-minimum"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
```

**Generate a secure secret key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### API Keys

Enable API key authentication for programmatic access:

```python
class AuthConfig(BaseModel):
    api_keys_enabled: bool = True  # Enable API key authentication
```

Create API keys via the API:
```bash
# Requires JWT token
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "expires_days": 365,
    "scopes": ["scenarios:read", "query:execute"]
  }'
```

#### OAuth Providers

Configure OAuth 2.0 providers (GitHub, Google, GitLab, Keycloak):

```bash
# GitHub OAuth
export OAUTH_GITHUB_CLIENT_ID="your_github_client_id"
export OAUTH_GITHUB_CLIENT_SECRET="your_github_client_secret"

# Google OAuth
export OAUTH_GOOGLE_CLIENT_ID="your_google_client_id"
export OAUTH_GOOGLE_CLIENT_SECRET="your_google_client_secret"

# Keycloak
export OAUTH_KEYCLOAK_SERVER_URL="https://keycloak.example.com"
export OAUTH_KEYCLOAK_REALM="your_realm"
export OAUTH_KEYCLOAK_CLIENT_ID="your_client_id"
export OAUTH_KEYCLOAK_CLIENT_SECRET="your_client_secret"
```

#### LDAP/Active Directory

Configure LDAP for enterprise authentication:

```bash
export LDAP_SERVER="ldap.example.com"
export LDAP_BASE_DN="dc=example,dc=com"
export LDAP_BIND_USER="cn=admin,dc=example,dc=com"
export LDAP_BIND_PASSWORD="admin_password"
export LDAP_USER_SEARCH_BASE="ou=users,dc=example,dc=com"
export LDAP_GROUP_SEARCH_BASE="ou=groups,dc=example,dc=com"
```

### Rate Limiting Configuration

Protect your API with rate limiting:

```python
class RateLimitConfig(BaseModel):
    enabled: bool = True
    storage: str = "memory"  # "memory" or "redis://localhost:6379"
    default_limits: List[str] = ["100/minute", "1000/hour"]

    endpoint_limits: Dict[str, str] = {
        "/api/v1/review/*": "10/minute",
        "/api/v1/chat": "60/minute",
        "/api/v1/chat/stream": "30/minute",
        "/api/v1/query/execute": "30/minute",
        "/api/v1/demo/chat": "30/minute",
    }
```

**Use Redis for production** (shared across workers):
```bash
export RATE_LIMIT_STORAGE="redis://localhost:6379"
```

### CORS Configuration

Configure Cross-Origin Resource Sharing for web frontends:

```python
class CORSConfig(BaseModel):
    allowed_origins: List[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: List[str] = ["*"]
    allow_credentials: bool = True
    max_age: int = 600  # Preflight cache duration (seconds)
```

### Demo Endpoint Configuration

Configure the public demo endpoint:

```bash
export DEMO_ENABLED="true"
export DEMO_RATE_LIMIT="30/minute"
```

```python
class DemoConfig(BaseModel):
    enabled: bool = True
    rate_limit: str = "30/minute"
    allowed_scenarios: List[str] = ["onboarding"]
    max_query_length: int = 500
```

## LLM Provider Configuration

Configure the LLM provider used for code analysis and query generation.

### GigaChat

```bash
export GIGACHAT_AUTH_KEY="your_gigachat_key"
```

```yaml
# config.yaml
llm:
  provider: gigachat
  model: GigaChat-2-Pro
  temperature: 0.1
  max_tokens: 4096
```

### Local LLM (llama-cpp-python)

```bash
export LLMXCPG_MODEL_PATH="/path/to/llmxcpg/model.gguf"
```

```yaml
# config.yaml
llm:
  provider: local
  model_path: ${LLMXCPG_MODEL_PATH}
  n_gpu_layers: -1   # Use all GPU layers (-1)
  n_ctx: 8192        # Context window size
  n_threads: 8       # CPU threads for inference
  temperature: 0.1
  max_tokens: 4096
```

### OpenAI

```bash
export OPENAI_API_KEY="your_openai_key"
```

```yaml
# config.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.1
  max_tokens: 4096
  api_base: https://api.openai.com/v1
```

## Domain Configuration

Switch between different codebases for analysis:

```yaml
# config.yaml
domain:
  name: postgresql  # postgresql, linux_kernel, llvm, generic
  auto_activate: true
```

Available domains:
- `postgresql` - PostgreSQL 17.6 database
- `linux_kernel` - Linux Kernel 6.x
- `llvm` - LLVM 18.x compiler infrastructure
- `generic` - Generic C/C++ codebase

## CPG Database Configuration

Configure the Code Property Graph database (for code analysis):

```yaml
# config.yaml
cpg:
  type: postgresql  # Database type for CPG storage
  db_path: cpg.duckdb  # Legacy: DuckDB path (if using DuckDB)
```

## Retrieval Settings

Configure semantic search and retrieval:

```yaml
# config.yaml
retrieval:
  embedding_model: all-MiniLM-L6-v2  # Sentence transformer model
  embedding_dimension: 384            # Vector dimension
  top_k_qa: 3                         # Top results for Q&A retrieval
  top_k_cpgql: 5                      # Top results for CPGQL retrieval
  max_results: 50                     # Maximum search results
  chunk_size: 512                     # Text chunk size for embeddings

  # Hybrid retrieval (vector + graph)
  hybrid:
    enabled: true
    vector_weight: 0.6      # Semantic search weight
    graph_weight: 0.4       # Structural search weight
    rrf_k: 60               # Reciprocal Rank Fusion constant
```

### Query Limits

```yaml
# config.yaml
query:
  default_limit: 100   # Default LIMIT for SQL queries
  max_limit: 1000      # Maximum allowed LIMIT
```

## Analysis Settings

Configure analysis thresholds:

```yaml
# config.yaml
analysis:
  sanitization_confidence_threshold: 0.7  # Confidence for sanitization detection
  similarity_threshold: 0.8                # Semantic similarity threshold
  complexity_threshold: 10                 # Cyclomatic complexity threshold
```

## Environment Variables Reference

Create a `.env` file in the project root:

```bash
# =============================================================================
# API Server Configuration
# =============================================================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_DEBUG=false

# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph

# =============================================================================
# Authentication
# =============================================================================
API_JWT_SECRET=your-secret-key-min-64-chars-change-in-production
API_JWT_ALGORITHM=HS256

# Admin user (for initial setup)
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=change-this-password

# =============================================================================
# LLM API Providers
# =============================================================================
GIGACHAT_AUTH_KEY=your_gigachat_key
OPENAI_API_KEY=your_openai_key

# =============================================================================
# Local Model Paths
# =============================================================================
LLMXCPG_MODEL_PATH=/path/to/llmxcpg/model.gguf
QWEN3_MODEL_PATH=/path/to/qwen3/model.gguf

# =============================================================================
# OAuth Providers (Optional)
# =============================================================================
OAUTH_GITHUB_CLIENT_ID=your_github_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret

# =============================================================================
# LDAP Configuration (Optional)
# =============================================================================
LDAP_SERVER=ldap.example.com
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=admin_password
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com

# =============================================================================
# Rate Limiting
# =============================================================================
RATE_LIMIT_STORAGE=memory  # or redis://localhost:6379

# =============================================================================
# Demo Endpoint
# =============================================================================
DEMO_ENABLED=true
DEMO_RATE_LIMIT=30/minute

# =============================================================================
# Joern Server (Optional)
# =============================================================================
JOERN_HOST=localhost
JOERN_PORT=8080
JOERN_QUERY_TIMEOUT=60

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=INFO
LLM_VERBOSE=false

# =============================================================================
# Performance
# =============================================================================
CUDA_VISIBLE_DEVICES=0
OMP_NUM_THREADS=8
```

## Performance Tuning

### For Production (Multiple Workers)

```bash
# Use multiple workers for better throughput
python -m src.api.cli run --host 0.0.0.0 --port 8000 --workers 4

# Use Redis for rate limiting (shared across workers)
export RATE_LIMIT_STORAGE="redis://localhost:6379"

# Increase database pool size
# Edit src/api/config.py:
# pool_size: 20
# max_overflow: 40
```

### For Development (Fast Reload)

```bash
# Single worker with auto-reload
python -m src.api.cli run --host 127.0.0.1 --port 8000 --reload --log-level debug

# Enable SQL logging
# Edit src/api/config.py:
# echo: True
```

### For Limited Resources

```yaml
# config.yaml
retrieval:
  batch_size: 50    # Lower from 100
  top_k_qa: 3       # Lower from 10
  top_k_cpgql: 3

llm:
  max_tokens: 2048  # Lower from 4096
```

## Security Best Practices

1. **Change default passwords:**
   ```bash
   # Generate secure JWT secret
   python -c "import secrets; print(secrets.token_urlsafe(64))"

   # Set strong admin password
   python -m src.api.cli create-admin --username admin --password <strong_password>
   ```

2. **Use environment variables for secrets:**
   - Never commit `.env` files to version control
   - Add `.env` to `.gitignore`

3. **Enable HTTPS in production:**
   - Use a reverse proxy (nginx, Caddy, Traefik)
   - Or configure uvicorn with SSL certificates

4. **Restrict CORS origins:**
   ```python
   allowed_origins: List[str] = [
       "https://yourapp.example.com",  # Production frontend only
   ]
   ```

5. **Configure rate limiting:**
   - Use Redis for distributed rate limiting
   - Adjust limits based on your capacity

## Validation

Test your configuration:

```bash
# Test database connection
python -c "
from src.api.database.connection import check_db_connection
import asyncio
print('Database OK' if asyncio.run(check_db_connection()) else 'Database FAILED')
"

# Test API health
curl http://localhost:8000/api/v1/health
```

## Next Steps

- [Installation Guide](INSTALLATION.md) - Set up the system
- [Quick Start Guide](README.md) - Get started quickly
- [User Guide](../guides/USER_GUIDE.md) - Learn to use the system
- [API Reference](../api/REST_API.md) - Explore API endpoints
