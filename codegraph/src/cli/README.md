# CLI Module

Command-line interface for CodeGraph providing direct access to analysis scenarios, project management, and system administration.

## Overview

```
src/cli/
├── main.py              # Main CLI entry point
├── commands/            # CLI command groups
│   ├── query.py         # Query commands
│   ├── scenarios.py     # Scenario commands
│   ├── projects.py      # Project management
│   ├── import_cmd.py    # Import commands
│   └── admin.py         # Admin commands
└── __init__.py          # Module exports
```

## Installation

```bash
# Install CLI
pip install -e .

# Verify installation
codegraph --version
```

## Usage

### Query Commands

```bash
# Natural language query
codegraph query "Where is heap_insert defined?"

# Run specific scenario
codegraph scenario security "Find SQL injection vulnerabilities"

# Execute raw CPGQL
codegraph cpgql 'cpg.method.name("heap_insert").l'
```

### Project Management

```bash
# List projects
codegraph projects list

# Import new project
codegraph import /path/to/source --language c

# Set active project
codegraph projects use postgresql-17
```

### Scenario Commands

```bash
# List available scenarios
codegraph scenarios list

# Run security audit
codegraph scenarios run security

# Run with specific query
codegraph scenarios run onboarding --query "Explain the executor"
```

### Admin Commands

```bash
# Check system health
codegraph health

# Initialize database
codegraph init

# Run migrations
codegraph migrate

# Clear cache
codegraph cache clear
```

## Configuration

CLI reads configuration from:
1. `~/.codegraph/config.yaml`
2. `./config.yaml`
3. Environment variables

```yaml
# ~/.codegraph/config.yaml
api:
  base_url: http://localhost:8000
  api_key: ${CODEGRAPH_API_KEY}

output:
  format: table  # table, json, yaml
  color: true
```

## Output Formats

```bash
# Table format (default)
codegraph query "Find main function"

# JSON output
codegraph query "Find main function" --format json

# YAML output
codegraph query "Find main function" --format yaml

# Quiet mode (just answer)
codegraph query "Find main function" -q
```

## Interactive Mode

```bash
# Start interactive shell
codegraph shell

> query Where is main defined?
> scenario security
> help
> exit
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CODEGRAPH_API_KEY` | API key for authentication |
| `CODEGRAPH_API_URL` | API base URL |
| `CODEGRAPH_CONFIG` | Config file path |
| `CODEGRAPH_OUTPUT` | Default output format |

## See Also

- `/src/tui/` - Terminal UI (rich interface)
- `/src/api/cli.py` - API CLI commands
- `/docs/guides/CLI.md` - CLI user guide
