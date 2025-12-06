# Patch Review CLI Usage Guide

The `patch-review` CLI provides automated code review capabilities using Code Property Graph (CPG) analysis.

## Installation

```bash
# From the rag_cpgql directory
pip install -e .

# Or run directly
python -m src.patch_review.cli [command] [options]
```

## Commands

### 1. `analyze` - Standalone Code Analysis

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

### 2. `diff` - Review a Diff File

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

### 3. `github` - Review a GitHub PR

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

### 4. `gitlab` - Review a GitLab MR

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

### 5. `init` - Initialize Database

Initialize delta tables for incremental analysis.

```bash
patch-review init [options]
```

**Example:**
```bash
patch-review init --db cpg.duckdb
```

## Global Options

These options apply to all commands:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--db` | `-d` | Path to DuckDB CPG database | `cpg.duckdb` |
| `--output` | `-o` | Output format: `json`, `markdown`, `summary`, `score` | `markdown` |
| `--output-file` | `-f` | Write output to file | stdout |
| `--verbose` | `-v` | Enable verbose logging | false |
| `--quiet` | `-q` | Only output result, no status messages | false |
| `--security-threshold` | | Minimum security score to pass | 60.0 |
| `--block-on-critical` | | Block if any critical findings | true |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Review approved / No critical findings |
| 1 | Review requests changes / High severity findings |
| 2 | Review blocks merge / Critical findings |

## Output Formats

### Markdown (default)
Human-readable report with tables and sections.

```bash
patch-review analyze --output markdown
```

### JSON
Machine-readable full results.

```bash
patch-review analyze --output json
```

### Summary
Condensed JSON summary.

```bash
patch-review analyze --output summary
```

### Score
Minimal score information.

```bash
patch-review analyze --output score
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Code Analysis
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
security_scan:
  script:
    - patch-review analyze --type security --severity critical
  allow_failure: false
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API token for PR reviews |
| `GITHUB_OWNER` | Default repository owner |
| `GITHUB_REPO` | Default repository name |
| `GITLAB_TOKEN` | GitLab API token for MR reviews |
| `GITLAB_PROJECT_ID` | Default project ID |

## Pattern Filtering

Run specific patterns by ID:

```bash
# Single pattern
patch-review analyze --patterns SQL_INJECTION

# Multiple patterns
patch-review analyze --patterns SQL_INJECTION,BUFFER_OVERFLOW,USE_AFTER_FREE

# All dead code patterns
patch-review analyze --type dead-code
```

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

### Performance Issues
```bash
# Limit findings per pattern
patch-review analyze --limit 25

# Run specific analysis type
patch-review analyze --type security
```
