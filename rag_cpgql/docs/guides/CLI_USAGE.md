# Command Line Interface Usage Guide

RAG-CPGQL provides three command-line interfaces for different use cases:

1. **rag-cpgql** - Project import and management
2. **security-audit** - Security scanning for Python/Django projects
3. **patch-review** - Automated code review using CPG analysis

---

## Table of Contents

- [rag-cpgql CLI](#rag-cpgql-cli)
  - [Import Command](#import-command)
  - [Projects Management](#projects-management)
  - [Server Management](#server-management)
  - [Single Step Commands](#single-step-commands)
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
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)

---

## rag-cpgql CLI

Main CLI for importing projects and managing the RAG-CPGQL system.

### Installation

```bash
# From the rag_cpgql directory
pip install -e .

# Or run directly
python -m src.cli.import_commands [command] [options]
```

### Import Command

Import a project from Git repository or local path.

```bash
rag-cpgql import [options]
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
rag-cpgql import --repo https://github.com/postgres/postgres --branch REL_17_STABLE

# Import local code with Docker
rag-cpgql import --path ./myproject --docker

# Import with specific language
rag-cpgql import --repo https://github.com/org/repo --language python

# Selective import (specific paths only)
rag-cpgql import --path ./code --mode selective --include src/core src/api

# Import to specific group
rag-cpgql import --repo https://github.com/org/repo --group security-team
```

### Projects Management

Manage imported projects.

```bash
rag-cpgql projects [subcommand] [options]
```

**Subcommands:**

#### List Projects

```bash
rag-cpgql projects list [options]
```

| Option | Description |
|--------|-------------|
| `--group` | Filter by group name |
| `--language` | Filter by language |
| `--active` | Show only active project |

**Examples:**

```bash
# List all projects
rag-cpgql projects list

# List projects in a group
rag-cpgql projects list --group security-team

# Show active project only
rag-cpgql projects list --active
```

#### Activate Project

```bash
rag-cpgql projects activate <name> [--group <group>]
```

**Example:**

```bash
rag-cpgql projects activate postgresql-17 --group default
```

#### Delete Project

```bash
rag-cpgql projects delete <name> [options]
```

| Option | Description |
|--------|-------------|
| `--group` | Project group name |
| `--delete-files` | Also delete CPG and DuckDB files |

**Examples:**

```bash
# Delete project, keep files
rag-cpgql projects delete old-project

# Delete project and files
rag-cpgql projects delete old-project --delete-files
```

#### Project Info

```bash
rag-cpgql projects info <name> [--group <group>]
```

**Example:**

```bash
rag-cpgql projects info postgresql-17
```

### Server Management

Manage the Joern server.

```bash
rag-cpgql server [subcommand] [options]
```

**Subcommands:**

```bash
# Check server status
rag-cpgql server status

# Start server
rag-cpgql server start [--docker] [--memory 16]

# Stop server
rag-cpgql server stop

# Restart server
rag-cpgql server restart [--docker]
```

**Examples:**

```bash
# Check if Joern is running
rag-cpgql server status

# Start with Docker and 32GB memory
rag-cpgql server start --docker --memory 32

# Restart the server
rag-cpgql server restart
```

### Single Step Commands

Execute individual pipeline steps.

```bash
# Clone repository
rag-cpgql clone --repo <url> [--branch main] [--shallow] [--depth 1] [--output dir]

# Detect programming language
rag-cpgql detect --path <source_path>

# Create Joern CPG
rag-cpgql cpg --path <source_path> [--language c] [--output cpg.bin] [--docker]

# Export CPG to DuckDB
rag-cpgql export --cpg <cpg_path> [--output db.duckdb]

# Validate export
rag-cpgql validate --db <duckdb_path>
```

**Examples:**

```bash
# Clone a repository
rag-cpgql clone --repo https://github.com/postgres/postgres --branch REL_17_STABLE

# Detect language in local directory
rag-cpgql detect --path ./myproject

# Create CPG with Docker
rag-cpgql cpg --path ./myproject --language python --docker

# Export to DuckDB
rag-cpgql export --cpg ./workspace/cpg.bin --output ./cpg.duckdb

# Validate the export
rag-cpgql validate --db ./cpg.duckdb
```

### Other Commands

```bash
# List supported languages
rag-cpgql languages

# List import jobs
rag-cpgql jobs [--limit 10] [--status pending|running|completed|failed]
```

---

## security-audit CLI

Security scanning CLI for Python/Django projects.

### Installation

```bash
# Run directly
python -m src.cli.security_audit [command] [options]
```

### Full Audit

Run comprehensive security audit with multiple output formats.

```bash
security-audit full --path <project_path> [options]
```

**Options:**

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

# Custom output directory
security-audit full --path ./myproject --output ./reports

# Exclude directories
security-audit full --path ./myproject --exclude-dirs vendor third_party

# Quick file-based scan only (no CPG)
security-audit full --path ./myproject --no-cpg
```

### Quick Scan

Fast file-based security scan without full CPG analysis.

```bash
security-audit quick --path <project_path> [--output <file>]
```

**Examples:**

```bash
# Quick scan with console output
security-audit quick --path ./myproject

# Quick scan with output file
security-audit quick --path ./myproject --output scan_results.json
```

### Settings Scan

Scan Django settings file for security issues.

```bash
security-audit settings --path <settings_path>
```

**Examples:**

```bash
# Scan specific settings file
security-audit settings --path ./myproject/settings.py

# Auto-find settings in project
security-audit settings --path ./myproject
```

### Secrets Scan

Scan for hardcoded secrets and credentials.

```bash
security-audit secrets --path <project_path>
```

**Example:**

```bash
# Scan for secrets
security-audit secrets --path ./myproject
```

### Output Formats

| Format | Description |
|--------|-------------|
| `json` | Machine-readable JSON report |
| `markdown` | Human-readable markdown report |
| `sarif` | SARIF format for IDE integration |
| `all` | Generate all formats |

---

## patch-review CLI

Automated code review using Code Property Graph analysis.

### Installation

```bash
# From the rag_cpgql directory
pip install -e .

# Or run directly
python -m src.patch_review.cli [command] [options]
```

### Analyze Command

Run security and dead code analysis on the entire codebase.

```bash
patch-review analyze [options]
```

**Options:**

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

# Dead code analysis only
patch-review analyze --type dead-code --output markdown

# Specific patterns
patch-review analyze --patterns SQL_INJECTION,BUFFER_OVERFLOW,DEAD_CODE

# Output as JSON
patch-review analyze --output json --output-file analysis.json

# Limit findings
patch-review analyze --limit 100
```

### Diff Review

Review changes from a unified diff file.

```bash
patch-review diff [file] [options]
```

**Options:**

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

# Security-only review
patch-review diff changes.diff --security-only
```

### GitHub PR Review

Fetch and review a GitHub Pull Request.

```bash
patch-review github <pr_number> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--owner` | Repository owner (or `GITHUB_OWNER` env) |
| `--repo` | Repository name (or `GITHUB_REPO` env) |
| `--token` | GitHub token (or `GITHUB_TOKEN` env) |
| `--post-review` | Post review comments to PR |
| `--dead-code` | Include dead code analysis |
| `--security-only` | Only run security analysis |

**Examples:**

```bash
# Review PR #123
patch-review github 123 --owner myorg --repo myrepo --token $GITHUB_TOKEN

# Post review to PR
patch-review github 123 --post-review

# With dead code analysis
patch-review github 123 --dead-code
```

### GitLab MR Review

Fetch and review a GitLab Merge Request.

```bash
patch-review gitlab <mr_iid> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--project` | Project ID or path (or `GITLAB_PROJECT_ID` env) |
| `--token` | GitLab token (or `GITLAB_TOKEN` env) |
| `--post-review` | Post review comments to MR |
| `--dead-code` | Include dead code analysis |
| `--security-only` | Only run security analysis |

**Examples:**

```bash
# Review MR !456
patch-review gitlab 456 --project myorg/myrepo --token $GITLAB_TOKEN

# Post review to MR
patch-review gitlab 456 --post-review
```

### Initialize Database

Initialize delta tables for incremental analysis.

```bash
patch-review init [--db cpg.duckdb]
```

### Global Options

These options apply to all patch-review commands:

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

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub API token | patch-review |
| `GITHUB_OWNER` | Default repository owner | patch-review |
| `GITHUB_REPO` | Default repository name | patch-review |
| `GITLAB_TOKEN` | GitLab API token | patch-review |
| `GITLAB_PROJECT_ID` | Default GitLab project | patch-review |
| `JOERN_HOME` | Joern installation path | rag-cpgql |
| `JOERN_SERVER_HOST` | Joern server host | rag-cpgql |
| `JOERN_SERVER_PORT` | Joern server port | rag-cpgql |

---

## Exit Codes

### patch-review

| Code | Meaning |
|------|---------|
| 0 | Review approved / No critical findings |
| 1 | Review requests changes / High severity findings |
| 2 | Review blocks merge / Critical findings |

### security-audit

| Code | Meaning |
|------|---------|
| 0 | Audit completed successfully |
| 1 | Error or critical findings |

### rag-cpgql

| Code | Meaning |
|------|---------|
| 0 | Command completed successfully |
| 1 | Error occurred |

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
rag-cpgql server status

# Restart with more memory
rag-cpgql server restart --memory 32
```

### Import Failures

```bash
# Check supported languages
rag-cpgql languages

# Try with Docker
rag-cpgql import --path ./code --docker

# Check import job status
rag-cpgql jobs --status failed
```

---

## See Also

- [Project Import Guide](./PROJECT_IMPORT.md) - Detailed import documentation
- [CPG Export Guide](./CPG_EXPORT.md) - Export CPG to DuckDB
- [REST API Reference](../api/REST_API.md) - API endpoints
- [WebSocket API](../api/WEBSOCKET_API.md) - Real-time streaming
