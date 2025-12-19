# CLI Tools Reference

This document describes all command-line tools available in CodeGraph.

---

## Table of Contents

- [API Server CLI](#api-server-cli)
- [Project Import CLI](#project-import-cli)
- [Security Audit CLI](#security-audit-cli)
- [Benchmark & Analysis Tools](#benchmark--analysis-tools)

---

## Quick Reference

| Tool | Purpose | Typical Usage |
|------|---------|---------------|
| `python -m src.api.cli run` | Start REST API server | Production/development server |
| `python -m src.cli.import_commands full` | Import project to CPG | Clone repo + create CPG |
| `python -m src.cli.security_audit full` | Security audit | Scan project for vulnerabilities |
| `demo_benchmark.py` | Synthetic benchmark demo | Quick performance testing |
| `tests/benchmark/run_benchmark.py` | Scenario benchmarks | Full multi-scenario evaluation |

---

## API Server CLI

**Module:** `src.api.cli`

**Usage:**
```bash
python -m src.api.cli <command> [options]
```

### Commands

#### `run` - Start API Server

Run the FastAPI REST API server.

```bash
python -m src.api.cli run [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host address to bind to |
| `--port` | `8000` | Port number to listen on |
| `--workers` | `1` | Number of uvicorn worker processes |
| `--reload` | `false` | Enable auto-reload for development |
| `--log-level` | `info` | Logging level (debug, info, warning, error) |

**Examples:**

```bash
# Start server with defaults
python -m src.api.cli run

# Development mode with auto-reload
python -m src.api.cli run --reload --log-level debug

# Production with multiple workers
python -m src.api.cli run --host 0.0.0.0 --port 8080 --workers 4
```

#### `init-db` - Initialize Database

Create database tables.

```bash
python -m src.api.cli init-db
```

This creates all required tables (users, sessions, api_keys, etc.) in the configured PostgreSQL database.

#### `migrate` - Run Migrations

Apply Alembic database migrations.

```bash
python -m src.api.cli migrate [--revision REVISION]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--revision` | `head` | Migration revision to upgrade to |

**Examples:**

```bash
# Apply all migrations
python -m src.api.cli migrate

# Upgrade to specific revision
python -m src.api.cli migrate --revision abc123
```

#### `create-admin` - Create Admin User

Create an administrator user account.

```bash
python -m src.api.cli create-admin --username USERNAME --password PASSWORD [--email EMAIL]
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--username` | Yes | Admin username |
| `--password` | Yes | Admin password |
| `--email` | No | Admin email address |

**Example:**

```bash
python -m src.api.cli create-admin --username admin --password SecurePass123! --email admin@example.com
```

---

## Project Import CLI

**Module:** `src.cli.import_commands`

**Usage:**
```bash
python -m src.cli.import_commands <command> [options]
```

### Commands

#### `full` - Full Import Pipeline

Run the complete project import pipeline: clone, detect language, create CPG, export to DuckDB, import docs.

```bash
python -m src.cli.import_commands full --repo URL [options]
python -m src.cli.import_commands full --path PATH [options]
```

**Source Options (one required):**

| Option | Description |
|--------|-------------|
| `--repo` | Git repository URL to clone |
| `--path` | Local path to existing source code |

**Additional Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--language` | auto | Programming language (c, cpp, python, java, go, javascript, php) |
| `--branch` | `main` | Git branch to clone |
| `--shallow` | `true` | Use shallow clone |
| `--include` | `[]` | Paths to include |
| `--exclude` | `[]` | Paths to exclude |
| `--mode` | `full` | Import mode (full, selective, incremental) |
| `--workspace` | auto | Joern workspace path |
| `--domain-name` | auto | Custom domain name |
| `--memory` | `16` | Joern memory allocation (GB) |
| `--batch-size` | `10000` | DuckDB batch insert size |
| `--no-docs` | `false` | Skip documentation import |
| `--no-plugin` | `false` | Skip domain plugin creation |

**Examples:**

```bash
# Import from GitHub
python -m src.cli.import_commands full --repo https://github.com/org/project

# Import local Python project
python -m src.cli.import_commands full --path ./myproject --language python

# Import with custom settings
python -m src.cli.import_commands full \
    --repo https://github.com/org/project \
    --branch develop \
    --memory 32 \
    --exclude tests docs
```

#### `clone` - Clone Repository

Clone a git repository without further processing.

```bash
python -m src.cli.import_commands clone --repo URL [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--repo` | (required) | Repository URL |
| `--branch` | `main` | Branch to clone |
| `--shallow` | `true` | Use shallow clone |
| `--depth` | `1` | Shallow clone depth |
| `--output` | auto | Output directory |

#### `detect` - Detect Language

Detect programming language of a codebase.

```bash
python -m src.cli.import_commands detect --path PATH
```

#### `cpg` - Create CPG

Create Joern Code Property Graph from source code.

```bash
python -m src.cli.import_commands cpg --path PATH [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--path` | Path to source code (required) |
| `--language` | Programming language (optional, auto-detected) |
| `--output` | Output CPG path |

#### `export` - Export to DuckDB

Export CPG to DuckDB database.

```bash
python -m src.cli.import_commands export --cpg PATH [--output PATH]
```

#### `validate` - Validate Export

Validate the DuckDB export.

```bash
python -m src.cli.import_commands validate --db PATH
```

#### `docs` - Import Documentation

Import documentation and code comments to ChromaDB.

```bash
python -m src.cli.import_commands docs --path PATH [--db DUCKDB_PATH]
```

#### `domain` - Create Domain Plugin

Generate a domain-specific plugin.

```bash
python -m src.cli.import_commands domain --path PATH [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--path` | Path to source code (required) |
| `--name` | Domain name |
| `--db` | DuckDB path |
| `--language` | Programming language |

#### `languages` - List Supported Languages

Show all supported programming languages.

```bash
python -m src.cli.import_commands languages
```

**Output:**

| Language | Joern Command | Extensions |
|----------|---------------|------------|
| c | c2cpg | .c, .h |
| cpp | c2cpg | .cpp, .hpp, .cc, .cxx |
| python | pysrc2cpg | .py |
| java | javasrc2cpg | .java |
| go | gosrc2cpg | .go |
| javascript | jssrc2cpg | .js, .jsx, .ts, .tsx |
| php | php2cpg | .php |

---

## Security Audit CLI

**Module:** `src.cli.security_audit`

**Usage:**
```bash
python -m src.cli.security_audit <command> [options]
```

### Commands

#### `full` - Full Security Audit

Run comprehensive security audit on a project.

```bash
python -m src.cli.security_audit full --path PATH [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--path, -p` | (required) | Path to project to audit |
| `--output, -o` | `./security_reports` | Output directory for reports |
| `--format, -f` | `json markdown sarif` | Output format(s) |
| `--exclude-dirs` | `[]` | Additional directories to exclude |
| `--no-cpg` | `false` | Skip CPG-based analysis |
| `--verbose, -v` | `false` | Verbose output |

**Format Options:**
- `json` - JSON report
- `markdown` / `md` - Markdown report
- `sarif` - SARIF format (for IDE integration)
- `all` - All formats

**Examples:**

```bash
# Basic audit
python -m src.cli.security_audit full --path ./myproject

# Full audit with all formats
python -m src.cli.security_audit full \
    --path ./myproject \
    --output ./reports \
    --format all \
    --verbose

# Exclude specific directories
python -m src.cli.security_audit full \
    --path ./myproject \
    --exclude-dirs vendor third_party
```

**Output:**

The audit generates reports in the specified directory:
- `security_audit_YYYYMMDD_HHMMSS.json`
- `security_audit_YYYYMMDD_HHMMSS.md`
- `security_audit_YYYYMMDD_HHMMSS.sarif`

#### `quick` - Quick Scan

Fast file-based scan without CPG analysis.

```bash
python -m src.cli.security_audit quick --path PATH [--output FILE]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--path, -p` | Path to project (required) |
| `--output, -o` | Output file for report |

**Example:**

```bash
python -m src.cli.security_audit quick --path ./myproject --output quick_scan.json
```

#### `settings` - Django Settings Scan

Scan Django settings.py for security issues.

```bash
python -m src.cli.security_audit settings --path PATH
```

**Options:**

| Option | Description |
|--------|-------------|
| `--path, -p` | Path to settings.py or project directory |

The tool will auto-detect settings.py if given a directory.

**Example:**

```bash
# Direct path
python -m src.cli.security_audit settings --path ./myproject/settings.py

# Auto-detect in directory
python -m src.cli.security_audit settings --path ./myproject
```

**Checks performed:**
- DEBUG = True in production
- Weak SECRET_KEY
- ALLOWED_HOSTS configuration
- CSRF_COOKIE_SECURE
- SESSION_COOKIE_SECURE
- SECURE_SSL_REDIRECT
- Hardcoded database credentials
- And more...

#### `secrets` - Secrets Scan

Scan for hardcoded secrets and credentials.

```bash
python -m src.cli.security_audit secrets --path PATH
```

**Detects:**
- API keys (AWS, GCP, Azure, GitHub, etc.)
- Private keys (RSA, SSH)
- Database connection strings
- JWT secrets
- OAuth tokens
- Generic passwords in code

**Example:**

```bash
python -m src.cli.security_audit secrets --path ./myproject
```

### Vulnerability Severities

| Severity | Icon | Description |
|----------|------|-------------|
| Critical | `[X]` | Immediate action required |
| High | `[!]` | Address before deployment |
| Medium | `[~]` | Should be fixed |
| Low | `[o]` | Minor issues |
| Info | `[i]` | Informational |

### Excluded Directories (Default)

The scanner automatically excludes:
- `__pycache__`
- `.git`
- `.venv`, `venv`, `env`
- `node_modules`
- `.tox`, `.pytest_cache`, `.mypy_cache`
- `migrations`
- `static`, `media`
- `dist`, `build`

---

## Benchmark & Analysis Tools

### demo_benchmark.py

Demonstrates the benchmark framework with synthetic retrieval results. Shows how hybrid retrieval improves over pure vector and pure graph approaches.

```bash
python demo_benchmark.py
```

**Features:**
- Simulates vector, graph, and hybrid retrieval
- Demonstrates P@K, R@K, F1@K, MRR, NDCG metrics
- Reproducible results with random seed

### demo_patch_review.py

Demonstrates the automated patch review pipeline with security analysis.

```bash
python demo_patch_review.py [--db cpg.duckdb]
```

**Pipeline Steps:**
1. Patch Parsing - Parse unified diff format
2. Delta CPG Generation - Create CPG delta for changes
3. Impact Analysis - Analyze call graph impact
4. Security Scanning - Detect vulnerabilities in new code
5. Verdict Generation - Generate review verdict

**Output Files:**
- `demo_review_output.json` - Structured analysis results
- `demo_review_output.md` - Markdown review report

### tests/benchmark/run_benchmark.py

Full multi-scenario benchmark runner for evaluating CodeGraph across all 17 scenarios.

```bash
python tests/benchmark/run_benchmark.py [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `--quick` | Run quick benchmark (subset of queries) |
| `--scenario N` | Run specific scenario (1-17) |
| `--all-scenarios` | Run all 17 scenarios |
| `--output DIR` | Output directory for results |
| `--verbose` | Verbose logging |

**Scenarios:**

| # | Scenario | Description |
|---|----------|-------------|
| 1 | Definition Search | Find function/struct definitions |
| 2 | Call Graph | Caller/callee analysis |
| 3 | Data Flow | Taint analysis, reaching definitions |
| 4 | Vulnerability | Security vulnerability detection |
| 5 | Dead Code | Unreachable code detection |
| 6 | Complexity | Cyclomatic complexity, hotspots |
| 7 | Duplicates | Code clone detection |
| 8 | Entry Points | API/CLI entry point detection |
| 9 | Concurrency | Race condition detection |
| 10 | Architecture | Layer/coupling analysis |
| 11 | Dependencies | Cross-repo analysis |
| 12 | Documentation | Comment/doc extraction |
| 13 | Subsystem | Subsystem boundary analysis |
| 14 | Debugging | Debugging-related queries |
| 15 | New Vulnerabilities | Zero-day pattern detection |
| 16 | Business Logic | Domain-specific logic analysis |
| 17 | Test Generation | Test coverage analysis |

---

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | API server |
| `GIGACHAT_CREDENTIALS` | GigaChat API credentials | LLM provider |
| `OPENAI_API_KEY` | OpenAI API key | LLM provider |
| `JOERN_HOME` | Joern installation directory | Import tools |
| `DUCKDB_PATH` | Path to DuckDB database | All tools |
| `LOG_LEVEL` | Default logging level | All tools |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error / Failure |
| 2 | Invalid arguments |

---

## See Also

- [REST API Documentation](api/REST_API.md)
- [TUI Guide](TUI_GUIDE.md)
- [User Guide](USER_GUIDE.md)
- [Security Documentation](SECURITY.md)
