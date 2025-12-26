# Installation Guide

Complete installation instructions for CodeGraph.

## Table of Contents

- [System Requirements](#system-requirements)
  - [Hardware](#hardware)
  - [Software](#software)
- [Step 1: Environment Setup](#step-1-environment-setup)
- [Step 2: PostgreSQL Database Setup](#step-2-postgresql-database-setup)
  - [Install PostgreSQL](#install-postgresql)
  - [Verify PostgreSQL Installation](#verify-postgresql-installation)
  - [Configure Database Password](#configure-database-password)
- [Step 3: Initialize Database](#step-3-initialize-database)
  - [Verify Database](#verify-database)
- [Step 4: Create Admin User](#step-4-create-admin-user)
- [Step 5: LLM Provider Setup (Optional)](#step-5-llm-provider-setup-optional)
  - [Option A: GigaChat (Recommended for Russia)](#option-a-gigachat-recommended-for-russia)
  - [Option B: Local LLM (llama-cpp-python)](#option-b-local-llm-llama-cpp-python)
  - [Option C: OpenAI API](#option-c-openai-api)
- [Step 6: Start API Server](#step-6-start-api-server)
- [Step 7: Verify Installation](#step-7-verify-installation)
  - [Access API Documentation](#access-api-documentation)
  - [Test Health Endpoint](#test-health-endpoint)
  - [Test Authentication](#test-authentication)
  - [Test Authenticated Endpoint](#test-authenticated-endpoint)
- [Step 8: CPG Data Setup](#step-8-cpg-data-setup)
- [Troubleshooting](#troubleshooting)
  - [PostgreSQL Connection Failed](#postgresql-connection-failed)
  - [Password Authentication Failed](#password-authentication-failed)
  - [Database Does Not Exist](#database-does-not-exist)
  - [Port 8000 Already in Use](#port-8000-already-in-use)
  - [CUDA Not Found (for local LLM)](#cuda-not-found-for-local-llm)
  - [Out of Memory](#out-of-memory)
- [Next Steps](#next-steps)

## System Requirements

### Hardware
- **CPU**: 8+ cores recommended
- **RAM**: 16GB minimum (32GB+ for large codebases with local LLM)
- **GPU**: NVIDIA RTX 3090 or better (optional, for local LLM)
- **Storage**: 50GB free space

### Software
- Windows 10/11 or Linux
- Python 3.10+ (3.11 recommended)
- PostgreSQL 15+ (required for API server)
- Git
- CUDA Toolkit 11.8+ (optional, for GPU-accelerated local LLM)

## Step 1: Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd codegraph

# Create conda environment (recommended)
conda create -n codegraph python=3.11
conda activate codegraph

# OR create venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: PostgreSQL Database Setup

### Install PostgreSQL

**Windows:**
```powershell
# Download and install PostgreSQL 17 from:
# https://www.postgresql.org/download/windows/

# Or use Chocolatey:
choco install postgresql
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Fedora/RHEL
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Verify PostgreSQL Installation

```bash
# Check if PostgreSQL is running
# Windows (PowerShell):
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql
```

### Configure Database Password

Set a password for the postgres user:

```bash
# Linux:
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

# Windows:
# Open psql as postgres user and run:
# ALTER USER postgres PASSWORD 'your_password';
```

**Important:** Remember this password - you'll need it for the DATABASE_URL.

## Step 3: Initialize Database

Set the database connection string as an environment variable:

```bash
# Replace 'your_password' with your actual postgres password
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# Windows PowerShell:
$env:DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"
```

Initialize the database using the project CLI:

```bash
# Create database and run migrations
python -m src.api.cli init-db
```

This command will:
1. Create the `codegraph` database
2. Run Alembic migrations to create all tables
3. Initialize the database schema

### Verify Database

```bash
# Check tables were created
# Windows:
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d codegraph -c "\dt"

# Linux:
psql -U postgres -d codegraph -c "\dt"
```

Expected tables:
- users
- api_keys
- sessions
- dialogue_turns
- audit_log
- background_jobs
- token_blacklist

## Step 4: Create Admin User

```bash
# Create admin user with username and password
python -m src.api.cli create-admin --username admin --password <your_admin_password>

# Optionally add email
python -m src.api.cli create-admin --username admin --password <password> --email admin@example.com
```

Save your admin credentials - you'll need them to access the API.

## Step 5: LLM Provider Setup (Optional)

The API server can run without an LLM provider configured (for testing). Configure an LLM provider for full functionality:

### Option A: GigaChat (Recommended for Russia)

```bash
# Set environment variable
export GIGACHAT_AUTH_KEY="your_auth_key"

# Update config.yaml
# llm:
#   provider: gigachat
```

See [GigaChat Integration](../integrations/GIGACHAT.md) for details.

### Option B: Local LLM (llama-cpp-python)

```bash
# Install llama-cpp-python with CUDA support
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python

# Download model (Qwen3-Coder-30B recommended)
# Place in: ~/.lmstudio/models/

# Update config.yaml
# llm:
#   provider: local
#   model_path: path/to/model.gguf
```

### Option C: OpenAI API

```bash
export OPENAI_API_KEY="your_api_key"

# Update config.yaml
# llm:
#   provider: openai
#   model: gpt-4
```

## Step 6: Start API Server

```bash
# Set database URL (if not already set)
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# Start the server
python -m src.api.cli run --host 127.0.0.1 --port 8000

# For development with auto-reload:
python -m src.api.cli run --host 127.0.0.1 --port 8000 --reload
```

The server will start on http://127.0.0.1:8000

## Step 7: Verify Installation

### Access API Documentation

Open your browser and visit:
- **Swagger UI**: http://127.0.0.1:8000/api/docs
- **ReDoc**: http://127.0.0.1:8000/api/redoc

### Test Health Endpoint

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "database": "postgresql",
      "version": "PostgreSQL 17.x ..."
    }
  }
}
```

### Test Authentication

```bash
# Get access token
curl -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_admin_password"}'
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

### Test Authenticated Endpoint

```bash
# Replace TOKEN with your access_token from above
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "Authorization: Bearer TOKEN"
```

## Step 8: CPG Data Setup

CodeGraph uses pre-exported CPG data stored in DuckDB. If you have CPG data:

```bash
# Place your CPG database in the project directory
cp /path/to/cpg.duckdb ./cpg.duckdb

# Update config.yaml with the path
# cpg:
#   db_path: cpg.duckdb
```

For creating new CPG exports from source code, see [CPG Export Guide](../guides/CPG_EXPORT.md).

> **Note:** Joern is no longer required for normal operation. CPG data is pre-exported to DuckDB format.
> For legacy Joern integration, see [Joern Legacy Guide](../archive/JOERN_LEGACY.md).

## Troubleshooting

### PostgreSQL Connection Failed

**Error:** `connection to server at "localhost" failed`

**Solution:**
```bash
# Check PostgreSQL is running
# Windows:
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql
```

### Password Authentication Failed

**Error:** `password authentication failed for user "postgres"`

**Solution:**
```bash
# Reset postgres password
# Linux:
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'new_password';"

# Update DATABASE_URL with new password
export DATABASE_URL="postgresql+asyncpg://postgres:new_password@localhost:5432/codegraph"
```

### Database Does Not Exist

**Error:** `database "codegraph" does not exist`

**Solution:**
```bash
# Create database manually
psql -U postgres -c "CREATE DATABASE codegraph ENCODING 'UTF8';"

# Then run init-db again
python -m src.api.cli init-db
```

### Port 8000 Already in Use

**Error:** `error while attempting to bind on address ('127.0.0.1', 8000)`

**Solution:**
```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>

# Linux:
lsof -ti:8000 | xargs kill -9

# Or use a different port
python -m src.api.cli run --host 127.0.0.1 --port 8001
```

### CUDA Not Found (for local LLM)

**Error:** `CUDA not available`

**Solution:**
```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Reinstall PyTorch with CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Out of Memory

For systems with limited RAM:

```yaml
# Reduce settings in config.yaml
retrieval:
  batch_size: 50  # Lower from 100
  top_k: 5        # Lower from 10
```

## Next Steps

- [Configuration](CONFIGURATION.md) - Customize API settings, authentication, and providers
- [Quick Start Guide](README.md) - Get started with common use cases
- [TUI User Guide](../guides/TUI_USER_GUIDE.md) - Learn to use the system
- [API Reference](../api/REST_API.md) - Explore API endpoints
- [Troubleshooting](../guides/TROUBLESHOOTING.md) - Common issues and solutions
