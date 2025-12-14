# CLI Module

Command-line interface for RAG-CPGQL providing direct access to analysis scenarios, project management, and system administration.

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
rag-cpgql --version
```

## Usage

### Query Commands

```bash
# Natural language query
rag-cpgql query "Where is heap_insert defined?"

# Run specific scenario
rag-cpgql scenario security "Find SQL injection vulnerabilities"

# Execute raw CPGQL
rag-cpgql cpgql 'cpg.method.name("heap_insert").l'
```

### Project Management

```bash
# List projects
rag-cpgql projects list

# Import new project
rag-cpgql import /path/to/source --language c

# Set active project
rag-cpgql projects use postgresql-17
```

### Scenario Commands

```bash
# List available scenarios
rag-cpgql scenarios list

# Run security audit
rag-cpgql scenarios run security

# Run with specific query
rag-cpgql scenarios run onboarding --query "Explain the executor"
```

### Admin Commands

```bash
# Check system health
rag-cpgql health

# Initialize database
rag-cpgql init

# Run migrations
rag-cpgql migrate

# Clear cache
rag-cpgql cache clear
```

## Configuration

CLI reads configuration from:
1. `~/.rag-cpgql/config.yaml`
2. `./config.yaml`
3. Environment variables

```yaml
# ~/.rag-cpgql/config.yaml
api:
  base_url: http://localhost:8000
  api_key: ${RAG_CPGQL_API_KEY}

output:
  format: table  # table, json, yaml
  color: true
```

## Output Formats

```bash
# Table format (default)
rag-cpgql query "Find main function"

# JSON output
rag-cpgql query "Find main function" --format json

# YAML output
rag-cpgql query "Find main function" --format yaml

# Quiet mode (just answer)
rag-cpgql query "Find main function" -q
```

## Interactive Mode

```bash
# Start interactive shell
rag-cpgql shell

> query Where is main defined?
> scenario security
> help
> exit
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RAG_CPGQL_API_KEY` | API key for authentication |
| `RAG_CPGQL_API_URL` | API base URL |
| `RAG_CPGQL_CONFIG` | Config file path |
| `RAG_CPGQL_OUTPUT` | Default output format |

## See Also

- `/src/tui/` - Terminal UI (rich interface)
- `/src/api/cli.py` - API CLI commands
- `/docs/guides/CLI.md` - CLI user guide
