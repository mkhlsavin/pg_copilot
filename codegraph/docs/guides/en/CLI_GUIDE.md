# CLI Guide

Complete command-line interface documentation for CodeGraph.

---

## Table of Contents

- [Quick Reference](#quick-reference)
- [codegraph CLI](#codegraph-cli)
  - [Import Command](#import-command)
  - [Projects Management](#projects-management)
  - [Server Management](#server-management)
  - [Single Step Commands](#single-step-commands)
- [API Server CLI](#api-server-cli)
- [security-audit CLI](#security-audit-cli)
  - [Full Audit](#full-audit)
  - [Quick Scan](#quick-scan)
  - [Settings Scan](#settings-scan)
  - [Secrets Scan](#secrets-scan)
- [patch-review CLI](#patch-review-cli)
  - [Analyze Command](#analyze-command)
  - [Diff Review](#diff-review)
  - [GitHub PR Review](#github-pr-review)
  - [GitLab MR Review](#gitlab-mr-review)
- [Benchmark & Analysis Tools](#benchmark--analysis-tools)
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Quick Reference

| Tool | Purpose | Typical Usage |
|------|---------|---------------|
| `python -m src.api.cli run` | Start REST API server | Production/development server |
| `codegraph import` | Import project to CPG | Clone repo + create CPG |
| `codegraph projects` | Manage imported projects | List, activate, delete projects |
| `security-audit full` | Security audit | Scan project for vulnerabilities |
| `patch-review analyze` | Code review | Analyze codebase for issues |
| `patch-review github` | PR review | Review GitHub pull requests |

---

## codegraph CLI

Main CLI for importing projects and managing the CodeGraph system.

### Installation

```bash
# From the codegraph directory
pip install -e .

# Or run directly
python -m src.cli.import_commands [command] [options]
```

### Import Command

Import a project from Git repository or local path.

```bash
codegraph import [options]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--repo` | Git repository URL | - |
| `--path` | Local path to source code | - |
| `--language` | Programming language (auto-detect if not specified) | auto |
| `--branch` | Git branch to clone | `main` |
| `--shallow` | Use shallow clone | `true` |
| `--include` | Paths to include (multiple) | all |
| `--exclude` | Paths to exclude (multiple) | none |
| `--mode` | Import mode: `full`, `selective`, `incremental` | `full` |
| `--workspace` | Joern workspace path | auto |
| `--domain-name` | Custom domain name | auto |
| `--group` | Project group name | `default` |
| `--memory` | Joern memory in GB | `16` |
| `--batch-size` | DuckDB batch size | `10000` |
| `--docker` | Use Docker for Joern | `false` |
| `--no-docs` | Skip documentation import | `false` |
| `--no-plugin` | Skip domain plugin creation | `false` |

**Examples:**

```bash
# Import from GitHub
codegraph import --repo https://github.com/postgres/postgres --branch REL_17_STABLE

# Import local code with Docker
codegraph import --path ./myproject --docker

# Import with specific language
codegraph import --repo https://github.com/org/repo --language python

# Selective import (specific paths only)
codegraph import --path ./code --mode selective --include src/core src/api

# Import to specific group
codegraph import --repo https://github.com/org/repo --group security-team
```

### Projects Management

Manage imported projects.

```bash
codegraph projects [subcommand] [options]
```

#### List Projects

```bash
codegraph projects list [options]
```

| Option | Description |
|--------|-------------|
| `--group` | Filter by group name |
| `--language` | Filter by language |
| `--active` | Show only active project |

**Examples:**

```bash
# List all projects
codegraph projects list

# List projects in a group
codegraph projects list --group security-team

# Show active project only
codegraph projects list --active
```

#### Activate Project

```bash
codegraph projects activate <name> [--group <group>]
```

#### Delete Project

```bash
codegraph projects delete <name> [options]
```

| Option | Description |
|--------|-------------|
| `--group` | Project group name |
| `--delete-files` | Also delete CPG and DuckDB files |

#### Project Info

```bash
codegraph projects info <name> [--group <group>]
```

### Server Management

Manage the Joern server.

```bash
codegraph server [subcommand] [options]
```

**Subcommands:**

```bash
# Check server status
codegraph server status

# Start server
codegraph server start [--docker] [--memory 16]

# Stop server
codegraph server stop

# Restart server
codegraph server restart [--docker]
```

### Single Step Commands

Execute individual pipeline steps.

```bash
# Clone repository
codegraph clone --repo <url> [--branch main] [--shallow] [--depth 1] [--output dir]

# Detect programming language
codegraph detect --path <source_path>

# Create Joern CPG
codegraph cpg --path <source_path> [--language c] [--output cpg.bin] [--docker]

# Export CPG to DuckDB
codegraph export --cpg <cpg_path> [--output db.duckdb]

# Validate export
codegraph validate --db <duckdb_path>

# List supported languages
codegraph languages
```

**Supported Languages:**

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

## API Server CLI

**Module:** `src.api.cli`

```bash
python -m src.api.cli <command> [options]
```

### `run` - Start API Server

```bash
python -m src.api.cli run [options]
```

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

### `init-db` - Initialize Database

```bash
python -m src.api.cli init-db
```

### `migrate` - Run Migrations

```bash
python -m src.api.cli migrate [--revision REVISION]
```

### `create-admin` - Create Admin User

```bash
python -m src.api.cli create-admin --username USERNAME --password PASSWORD [--email EMAIL]
```

---

## security-audit CLI

Security scanning CLI for Python/Django projects.

**Module:** `src.cli.security_audit`

```bash
python -m src.cli.security_audit <command> [options]
```

### Full Audit

Run comprehensive security audit with multiple output formats.

```bash
security-audit full --path <project_path> [options]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to project to audit | required |
| `--output` | `-o` | Output directory for reports | `./security_reports` |
| `--format` | `-f` | Output format(s): json, markdown, sarif, all | `json markdown sarif` |
| `--exclude-dirs` | | Additional directories to exclude | none |
| `--no-cpg` | | Skip CPG-based analysis (faster) | `false` |
| `--verbose` | `-v` | Verbose output | `false` |

**Examples:**

```bash
# Full audit with all formats
security-audit full --path ./myproject

# JSON output only
security-audit full --path ./myproject --format json

# Exclude directories
security-audit full --path ./myproject --exclude-dirs vendor third_party

# Quick file-based scan only (no CPG)
security-audit full --path ./myproject --no-cpg
```

**Output:**

The audit generates reports in the specified directory:
- `security_audit_YYYYMMDD_HHMMSS.json`
- `security_audit_YYYYMMDD_HHMMSS.md`
- `security_audit_YYYYMMDD_HHMMSS.sarif`

### Quick Scan

Fast file-based security scan without full CPG analysis.

```bash
security-audit quick --path <project_path> [--output <file>]
```

### Settings Scan

Scan Django settings file for security issues.

```bash
security-audit settings --path <settings_path>
```

**Checks performed:**
- DEBUG = True in production
- Weak SECRET_KEY
- ALLOWED_HOSTS configuration
- CSRF_COOKIE_SECURE
- SESSION_COOKIE_SECURE
- SECURE_SSL_REDIRECT
- Hardcoded database credentials

### Secrets Scan

Scan for hardcoded secrets and credentials.

```bash
security-audit secrets --path <project_path>
```

**Detects:**
- API keys (AWS, GCP, Azure, GitHub, etc.)
- Private keys (RSA, SSH)
- Database connection strings
- JWT secrets
- OAuth tokens
- Generic passwords in code

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
- `__pycache__`, `.git`
- `.venv`, `venv`, `env`
- `node_modules`
- `.tox`, `.pytest_cache`, `.mypy_cache`
- `migrations`
- `static`, `media`
- `dist`, `build`

---

## patch-review CLI

Automated code review using Code Property Graph analysis.

**Module:** `src.patch_review.cli`

```bash
python -m src.patch_review.cli [command] [options]
```

### Analyze Command

Run security and dead code analysis on the entire codebase.

```bash
patch-review analyze [options]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--type` | `-t` | Analysis type: `security`, `dead-code`, `all` | `all` |
| `--severity` | `-s` | Minimum severity: `critical`, `high`, `medium`, `low`, `all` | `all` |
| `--patterns` | `-p` | Comma-separated pattern IDs to check | all patterns |
| `--limit` | `-l` | Max findings per pattern | 50 |

**Examples:**

```bash
# Full analysis (security + dead code)
patch-review analyze --db cpg.duckdb

# Security only, critical severity
patch-review analyze --type security --severity critical

# Specific patterns
patch-review analyze --patterns SQL_INJECTION,BUFFER_OVERFLOW,DEAD_CODE
```

### Diff Review

Review changes from a unified diff file.

```bash
patch-review diff [file] [options]
```

| Option | Description |
|--------|-------------|
| `file` | Path to diff file (or `-` for stdin) |
| `--dead-code` | Include dead code analysis in review |
| `--security-only` | Only run security analysis |

**Examples:**

```bash
# Review a diff file
patch-review diff changes.diff

# Read from stdin
git diff | patch-review diff -

# With dead code analysis
patch-review diff changes.diff --dead-code
```

### GitHub PR Review

Fetch and review a GitHub Pull Request.

```bash
patch-review github <pr_number> [options]
```

| Option | Description |
|--------|-------------|
| `--owner` | Repository owner (or `GITHUB_OWNER` env) |
| `--repo` | Repository name (or `GITHUB_REPO` env) |
| `--token` | GitHub token (or `GITHUB_TOKEN` env) |
| `--post-review` | Post review comments to PR |
| `--dead-code` | Include dead code analysis |

**Example:**

```bash
patch-review github 123 --owner myorg --repo myrepo --token $GITHUB_TOKEN --post-review
```

### GitLab MR Review

Fetch and review a GitLab Merge Request.

```bash
patch-review gitlab <mr_iid> [options]
```

| Option | Description |
|--------|-------------|
| `--project` | Project ID or path (or `GITLAB_PROJECT_ID` env) |
| `--token` | GitLab token (or `GITLAB_TOKEN` env) |
| `--post-review` | Post review comments to MR |

### Global Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--db` | `-d` | Path to DuckDB CPG database | `cpg.duckdb` |
| `--output` | `-o` | Output format: `json`, `markdown`, `summary`, `score` | `markdown` |
| `--output-file` | `-f` | Write output to file | stdout |
| `--verbose` | `-v` | Enable verbose logging | false |
| `--quiet` | `-q` | Only output result, no status messages | false |
| `--security-threshold` | | Minimum security score to pass | 60.0 |
| `--block-on-critical` | | Block if any critical findings | true |

---

## Benchmark & Analysis Tools

### demo_benchmark.py

Demonstrates the benchmark framework with synthetic retrieval results.

```bash
python examples/demo_benchmark.py
```

**Features:**
- Simulates vector, graph, and hybrid retrieval
- Demonstrates P@K, R@K, F1@K, MRR, NDCG metrics
- Reproducible results with random seed

### demo_patch_review.py

Demonstrates the automated patch review pipeline.

```bash
python examples/demo_patch_review.py [--db cpg.duckdb]
```

**Output Files:**
- `demo_review_output.json` - Structured analysis results
- `demo_review_output.md` - Markdown review report

### tests/benchmark/run_benchmark.py

Full multi-scenario benchmark runner.

```bash
python tests/benchmark/run_benchmark.py [OPTIONS]
```

| Argument | Description |
|----------|-------------|
| `--quick` | Run quick benchmark (subset of queries) |
| `--scenario N` | Run specific scenario (1-17) |
| `--all-scenarios` | Run all 17 scenarios |
| `--output DIR` | Output directory for results |

---

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | API server |
| `GIGACHAT_CREDENTIALS` | GigaChat API credentials | LLM provider |
| `OPENAI_API_KEY` | OpenAI API key | LLM provider |
| `JOERN_HOME` | Joern installation directory | Import tools |
| `JOERN_SERVER_HOST` | Joern server host | codegraph |
| `JOERN_SERVER_PORT` | Joern server port | codegraph |
| `DUCKDB_PATH` | Path to DuckDB database | All tools |
| `LOG_LEVEL` | Default logging level | All tools |
| `GITHUB_TOKEN` | GitHub API token | patch-review |
| `GITHUB_OWNER` | Default repository owner | patch-review |
| `GITHUB_REPO` | Default repository name | patch-review |
| `GITLAB_TOKEN` | GitLab API token | patch-review |
| `GITLAB_PROJECT_ID` | Default GitLab project | patch-review |

---

## Exit Codes

### codegraph

| Code | Meaning |
|------|---------|
| 0 | Command completed successfully |
| 1 | Error occurred |
| 2 | Invalid arguments |

### security-audit

| Code | Meaning |
|------|---------|
| 0 | Audit completed successfully |
| 1 | Error or critical findings |

### patch-review

| Code | Meaning |
|------|---------|
| 0 | Review approved / No critical findings |
| 1 | Review requests changes / High severity findings |
| 2 | Review blocks merge / Critical findings |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Security Analysis
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Security Audit
        run: |
          security-audit full --path . --format sarif --output ./reports

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: reports/security_audit_*.sarif

      - name: Patch Review
        if: github.event_name == 'pull_request'
        run: |
          patch-review analyze --type security --severity high --output json > analysis.json
          exit_code=$?
          if [ $exit_code -eq 2 ]; then
            echo "Critical vulnerabilities found!"
            exit 1
          fi
```

### GitLab CI

```yaml
stages:
  - security

security_scan:
  stage: security
  script:
    - pip install -e .
    - security-audit full --path . --format json --output ./reports
    - patch-review analyze --type security --severity critical
  artifacts:
    reports:
      sast: reports/security_audit_*.json
  allow_failure: false
```

---

## Troubleshooting

### Database Connection Error

```bash
# Verify database exists and is readable
ls -la cpg.duckdb

# Try with explicit path
patch-review analyze --db /full/path/to/cpg.duckdb
```

### No Findings

```bash
# Check with verbose logging
patch-review analyze --verbose

# Lower severity threshold
patch-review analyze --severity all
```

### Joern Server Issues

```bash
# Check server status
codegraph server status

# Restart with more memory
codegraph server restart --memory 32
```

### Import Failures

```bash
# Check supported languages
codegraph languages

# Try with Docker
codegraph import --path ./code --docker

# Check import job status
codegraph jobs --status failed
```

---

## See Also

- [Project Import Guide](./PROJECT_IMPORT.md) - Detailed import documentation
- [CPG Export Guide](./CPG_EXPORT.md) - Export CPG to DuckDB
- [REST API Reference](../api/REST_API.md) - API endpoints
- [TUI User Guide](./TUI_USER_GUIDE.md) - Interactive terminal interface
- [Security Documentation](../reference/SECURITY.md) - Security features
