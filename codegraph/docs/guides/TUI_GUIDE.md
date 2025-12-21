# TUI (Terminal User Interface) Guide

This document provides a complete guide to using the CodeGraph interactive terminal interface.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Starting the TUI](#starting-the-tui)
- [Interface Overview](#interface-overview)
- [Commands Reference](#commands-reference)
- [Scenarios](#scenarios)
- [Project Management](#project-management)
- [Code Review Mode](#code-review-mode)
- [Configuration](#configuration)
- [Themes](#themes)
- [Sessions](#sessions)
- [Tips & Tricks](#tips--tricks)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Start TUI with default settings
python -m src.tui.app

# Start with dark theme
python -m src.tui.app --theme dark

# Restore previous session
python -m src.tui.app --session my_session_id
```

Once started, type `/help` to see available commands, or simply type a question about your codebase.

---

## Starting the TUI

### Basic Usage

```bash
python -m src.tui.app [OPTIONS]
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config PATH` | Path to config.yaml | Auto-detect |
| `--session ID` | Session ID to restore | New session |
| `--theme NAME` | Color theme (default, dark, light) | default |
| `--session-dir PATH` | Directory for session storage | `./sessions` |
| `--debug` | Enable debug logging | False |

### Examples

```bash
# Basic start
python -m src.tui.app

# Use custom config
python -m src.tui.app --config /path/to/config.yaml

# Dark theme with debug logging
python -m src.tui.app --theme dark --debug

# Restore a specific session
python -m src.tui.app --session abc123
```

---

## Interface Overview

### Main Components

```
┌─────────────────────────────────────────────────────────────┐
│  CodeGraph v1.0.0  │ Session: abc123  │ Scenario: Security  │  <- Status Bar
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Your query results and conversation history appear here    │  <- Main Area
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  codegraph >                                                │  <- Prompt
└─────────────────────────────────────────────────────────────┘
```

### Interaction Modes

1. **Natural Language Mode**: Type questions about your code
   ```
   codegraph > What functions call malloc?
   ```

2. **Command Mode**: Use `/` prefix for commands
   ```
   codegraph > /scenarios
   codegraph > /select 2
   ```

---

## Commands Reference

### Quick Reference Table

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/help` | `[command]` | Show help message |
| `/scenarios` | `[group]` | List available scenarios |
| `/select` | `<number>` | Select a scenario |
| `/history` | `[count]` | Show conversation history |
| `/save` | `[filename]` | Save current session |
| `/load` | `[filename]` | Load session from file |
| `/config` | `[section] [key] [value]` | View/edit configuration |
| `/stat` | `[subcommand]` | Show statistics (CPG, scenarios, performance, api) |
| `/query` | `<SQL>` | Execute SQL on CPG database |
| `/demo` | `[options]` | Run quick benchmark demo |
| `/review` | `[source] [options]` | Launch code review mode |
| `/project` | `[subcommand]` | Manage projects |
| `/group` | `[subcommand]` | Manage project groups |
| `/import` | `[path] [options]` | Import projects with real-time progress |
| `/auth` | `[subcommand]` | Authentication management |
| `/session` | `[subcommand]` | Manage chat sessions |
| `/health` | - | Display system health status |
| `/clear` | - | Clear the screen |
| `/exit` | - | Exit the application |

### Detailed Command Reference

#### `/help` - Help System

Show help for all commands or a specific command.

```bash
/help              # Show all commands
/help config       # Show help for /config command
/help review       # Show help for /review command
```

#### `/scenarios` - Scenario Browser

List all available analysis scenarios.

```bash
/scenarios         # List all scenarios
/scenarios security  # Filter by group
```

#### `/select` - Scenario Selection

Select a scenario to focus your queries.

```bash
/select 1          # Select scenario 1 (Onboarding)
/select 02         # Select scenario 2 (Security Audit)
/select 14         # Select scenario 14 (Security Incident)
```

#### `/history` - Conversation History

View recent conversation history.

```bash
/history           # Show last 10 messages
/history 20        # Show last 20 messages
```

#### `/save` and `/load` - Session Management

Save and restore sessions.

```bash
/save              # Auto-save with generated ID
/save my_analysis  # Save with custom name

/load              # List available sessions
/load my_analysis  # Load specific session
```

#### `/config` - Configuration Editor

Interactive configuration viewer and editor.

```bash
/config            # Show section list with numbers
/config 1          # View section by number
/config llm        # View LLM configuration
/config llm temperature 0.5  # Edit value
```

**Configuration Sections:**
- `llm` - LLM provider settings
- `retrieval` - Retrieval system settings
- `cpg` - Code Property Graph settings
- `security` - Security features

#### `/stat` - Statistics

Show CPG database and system statistics.

```bash
/stat              # Show CPG database statistics
/stat scenarios    # Show scenario usage statistics
/stat performance  # Show performance metrics
/stat api          # Show API usage statistics
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| (none) | CPG database statistics (default) |
| `scenarios` | Scenario usage: query counts, popular scenarios |
| `performance` | Response times, cache hit rates, query latency |
| `api` | API endpoint usage, request counts, error rates |

**Default output includes:**
- Node counts by type (functions, calls, etc.)
- Database size
- ChromaDB collection statistics
- Memory usage

**Example: Performance Statistics**
```
/stat performance

╭─────────────── Performance Metrics ─────────────────────────╮
│                                                              │
│  Response Times (last 24h):                                  │
│    Average: 1.2s    Median: 0.8s    P95: 3.4s               │
│                                                              │
│  Cache Performance:                                          │
│    Hit rate: 78%    Misses: 234    Evictions: 45            │
│                                                              │
│  Query Stats:                                                │
│    Total queries: 1,234    Errors: 12 (0.9%)                │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/query` - SQL Query Executor

Execute read-only SQL queries on the CPG database.

```bash
# Basic queries
/query SELECT * FROM nodes_method LIMIT 5
/query SELECT name FROM nodes_call WHERE name LIKE '%alloc%'
/sql DESCRIBE nodes_method

# Count queries
/query SELECT COUNT(*) FROM nodes_method
/query SELECT COUNT(*) FROM edges_call
```

**Available Tables:**
- `nodes_method` - Function definitions
- `nodes_call` - Function calls
- `nodes_identifier` - Variables
- `nodes_literal` - Literal values
- `edges_call` - Call graph edges
- `edges_cfg` - Control flow edges
- `edges_ddg` - Data dependency edges

#### `/demo` - Quick Benchmark

Run a quick demonstration with sample queries.

```bash
/demo                         # Run all scenarios
/demo --scenarios 01,02       # Run specific scenarios
/demo --lang ru               # Use Russian questions
```

#### `/review` - Code Review Mode

Launch the integrated code review system.

```bash
/review                       # Interactive source selection
/review github 123            # Review GitHub PR #123
/review gitlab 456            # Review GitLab MR !456
/review git                   # Review current git diff
/review file diff.patch       # Review patch file
/review --format json         # Output as JSON
/review --inline              # Show inline comments
```

**Review Sources:**
1. GitHub Pull Request
2. GitLab Merge Request
3. Local Git diff
4. Patch file
5. Pasted diff

#### `/project` - Project Management

Manage multiple CPG projects.

```bash
/project                      # Show current project
/project list                 # List all projects
/project info [name]          # Show detailed project information
/project switch myproject     # Switch to project
/project add name db.duckdb python "Description"  # Add project
/project create name --path /src --language python --group mygroup  # Create with group
/project remove myproject     # Remove project
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| (none) | Show current project |
| `list` | List all available projects |
| `info [name]` | Show detailed project information (CPG stats, last updated, etc.) |
| `switch <name>` | Switch to specified project |
| `add <name> <db> <lang> [desc]` | Add existing CPG database |
| `create <name> --path --language [--group]` | Create new project, optionally in a group |
| `remove <name>` | Remove project from configuration |

**Example: Project Info**
```
/project info postgres_core

╭─────────────── Project Details ─────────────────────────────╮
│                                                              │
│  Name: postgres_core                                         │
│  Database: ./workspace/postgres/cpg.duckdb                   │
│  Language: c                                                 │
│  Group: database_projects                                    │
│                                                              │
│  CPG Statistics:                                             │
│    Methods: 12,456    Calls: 89,234    Files: 1,234         │
│                                                              │
│  Last Updated: 2024-12-20 10:30 UTC                          │
│  Size: 256 MB                                                │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/group` - Project Group Management

Manage project groups for organizing related projects.

```bash
/group                        # List all groups
/group list                   # List all groups with details
/group create mygroup "My project group"  # Create new group
/group delete mygroup         # Delete group
/group users mygroup          # List users with access to group
/group add-user mygroup user@email.com  # Add user to group
/group remove-user mygroup user@email.com  # Remove user from group
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| (none) / `list` | List all project groups |
| `create <name> [description]` | Create a new project group |
| `delete <name>` | Delete a project group |
| `users <name>` | List users with access to group |
| `add-user <group> <email>` | Add user to group |
| `remove-user <group> <email>` | Remove user from group |

**Example: Group Management**
```
/group list

╭─────────────── Project Groups ──────────────────────────────╮
│                                                              │
│  Group                Projects  Users  Created               │
│  ─────────────────────────────────────────────────────────── │
│  database_projects    3         5      2024-11-15            │
│  web_applications     7         12     2024-10-20            │
│  microservices        4         8      2024-12-01            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/import` - Project Import

Import new projects with real-time progress via WebSocket.

```bash
/import /path/to/source                    # Import with auto-detection
/import /path/to/source --language python  # Specify language
/import /path/to/source --name myproject   # Custom project name
/import /path/to/source --group mygroup    # Import into group
```

**Options:**

| Option | Description |
|--------|-------------|
| `--language <lang>` | Source language (c, python, java, go, etc.) |
| `--name <name>` | Custom project name |
| `--group <group>` | Import into specified group |
| `--no-embeddings` | Skip vector embedding generation |
| `--frontend <type>` | Joern frontend to use |

**Progress Display:**
```
/import /home/user/myproject --language python

╭─────────────── Import Progress ─────────────────────────────╮
│                                                              │
│  Project: myproject                                          │
│  Source: /home/user/myproject                                │
│  Language: python                                            │
│                                                              │
│  Step 1/4: Detecting language...          ✅ Complete        │
│  Step 2/4: Generating CPG...              ████████░░ 80%    │
│  Step 3/4: Exporting to DuckDB...         ⏳ Pending         │
│  Step 4/4: Creating embeddings...         ⏳ Pending         │
│                                                              │
│  Files processed: 234/289                                    │
│  Elapsed: 2m 34s                                             │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/auth` - Authentication Management

Manage authentication for API access.

```bash
/auth                         # Show current authentication status
/auth login                   # Interactive login
/auth logout                  # Log out current session
/auth me                      # Show current user info
/auth api-keys                # List API keys
/auth api-keys create "key name"  # Create new API key
/auth api-keys revoke <key-id>    # Revoke API key
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| (none) | Show authentication status |
| `login` | Interactive login (OAuth/LDAP) |
| `logout` | Log out and clear session |
| `me` | Show current user information |
| `api-keys` | List API keys |
| `api-keys create <name>` | Create new API key |
| `api-keys revoke <id>` | Revoke existing API key |

**Example: Authentication Status**
```
/auth me

╭─────────────── User Information ────────────────────────────╮
│                                                              │
│  Username: john.developer                                    │
│  Email: john@company.com                                     │
│  Roles: developer, reviewer                                  │
│                                                              │
│  Session:                                                    │
│    Created: 2024-12-20 08:00 UTC                             │
│    Expires: 2024-12-20 20:00 UTC                             │
│                                                              │
│  Groups: database_projects, web_applications                 │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/session` - Session Management

Manage chat sessions for conversation history.

```bash
/session                      # Show current session info
/session list                 # List all saved sessions
/session switch <id>          # Switch to different session
/session export <id> [format] # Export session (md, json, html)
/session delete <id>          # Delete a session
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| (none) | Show current session information |
| `list` | List all saved sessions |
| `switch <id>` | Switch to a different session |
| `export <id> [format]` | Export session (formats: md, json, html) |
| `delete <id>` | Delete a saved session |

**Example: Session List**
```
/session list

╭─────────────── Saved Sessions ──────────────────────────────╮
│                                                              │
│  ID          Scenario      Messages  Last Active            │
│  ─────────────────────────────────────────────────────────── │
│  abc123*     Security      45        2024-12-20 14:30       │
│  def456      Onboarding    23        2024-12-19 16:45       │
│  ghi789      Performance   12        2024-12-18 09:15       │
│                                                              │
│  * = current session                                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

#### `/health` - System Health

Display system health status and diagnostics.

```bash
/health                       # Show full health status
```

**Output:**
```
/health

╭─────────────── System Health ───────────────────────────────╮
│                                                              │
│  Component           Status    Details                       │
│  ─────────────────────────────────────────────────────────── │
│  CPG Database        ✅ OK     256 MB, 12,456 methods        │
│  ChromaDB            ✅ OK     5 collections, 89,234 vectors │
│  LLM Provider        ✅ OK     GigaChat, latency: 234ms      │
│  Joern Server        ✅ OK     Connected, port 8080          │
│  Memory              ⚠️ WARN   78% used (6.2/8.0 GB)         │
│  Disk                ✅ OK     45% used (123/256 GB)         │
│                                                              │
│  Uptime: 4h 23m                                              │
│  Last check: 2024-12-20 14:35 UTC                            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

---

## Scenarios

CodeGraph provides 16 specialized analysis scenarios:

### Exploration Group

| # | Name | Description |
|---|------|-------------|
| 01 | Onboarding | Get started with codebase exploration |
| 03 | Documentation | Generate and analyze documentation |
| 15 | Debugging | Assist with debugging issues |

### Security Group

| # | Name | Description |
|---|------|-------------|
| 02 | Security Audit | Analyze code for security vulnerabilities |
| 14 | Security Incident | Analyze potential security incidents |
| 16 | Entry Points | Find and analyze entry points |

### Quality Group

| # | Name | Description |
|---|------|-------------|
| 05 | Refactoring | Find refactoring opportunities |
| 07 | Test Coverage | Analyze test coverage and suggest tests |
| 08 | Compliance | Check coding standards compliance |
| 09 | Code Review | Assist with code review process |

### Architecture Group

| # | Name | Description |
|---|------|-------------|
| 04 | Feature Development | Understand code for adding features |
| 10 | Cross-Repo Impact | Analyze cross-repository dependencies |
| 11 | Architecture Violations | Find architecture pattern violations |

### Performance Group

| # | Name | Description |
|---|------|-------------|
| 06 | Performance | Identify performance bottlenecks |

### Maintenance Group

| # | Name | Description |
|---|------|-------------|
| 12 | Tech Debt | Identify technical debt areas |
| 13 | Mass Refactoring | Plan large-scale code changes |

### Example Queries by Scenario

**Security Audit (02):**
```
Find SQL injection vulnerabilities
Check for command injection risks
Find functions that don't validate input
```

**Performance (06):**
```
Find functions with high cyclomatic complexity
What functions allocate the most memory?
Find recursive functions
```

**Debugging (15):**
```
Trace the call path to function X
What error handlers exist in module Y?
Find all places where exception Z is caught
```

---

## Project Management

### Project Configuration

Projects are stored in `projects.yaml`:

```yaml
projects:
  fsin_module:
    db_path: ./workspace/fsin_module/cpg.duckdb
    language: c
    description: PostgreSQL FSIN module

  django_app:
    db_path: ./workspace/django_app/cpg.duckdb
    language: python
    description: Django web application

active_project: fsin_module
```

### Adding Projects

```bash
# Via TUI
/project add myproject ./path/to/cpg.duckdb python "My Python Project"

# Via CLI (import full project)
python -m src.cli.import_commands full --path ./mycode --language python
```

### Switching Projects

```bash
/project switch django_app
```

When switching projects:
1. Database path is updated
2. Appropriate domain plugin is activated
3. ChromaDB collections are reloaded

---

## Code Review Mode

### Interactive Review

```bash
/review
```

This shows a menu:
```
Select review source:
  1. GitHub PR
  2. GitLab MR
  3. Local Git diff
  4. Patch file
  5. Paste diff
```

### GitHub Integration

```bash
/review github 123
```

Requires `GITHUB_TOKEN` environment variable.

### GitLab Integration

```bash
/review gitlab 456
```

Requires `GITLAB_TOKEN` and optionally `GITLAB_URL` environment variables.

### Review Output Formats

```bash
/review --format md      # Markdown (default)
/review --format json    # JSON structure
/review --format sarif   # SARIF for IDE integration
```

### Review Verdict

The review system analyzes:
- Security vulnerabilities
- Code quality issues
- Performance concerns
- Best practice violations

Output includes:
- Overall verdict (APPROVE / REQUEST_CHANGES / COMMENT)
- Confidence score
- Line-by-line comments
- Suggested improvements

---

## Configuration

### Viewing Configuration

```bash
/config            # List all sections
/config llm        # View LLM settings
```

### Editing Configuration

```bash
/config llm temperature 0.7
/config llm model gpt-4o-mini
```

### Key Configuration Options

**LLM Settings:**
```yaml
llm:
  provider: gigachat  # or openai, local
  temperature: 0.7
  max_tokens: 4096
```

**Retrieval Settings:**
```yaml
retrieval:
  top_k: 20
  hybrid_alpha: 0.7
  rerank: true
```

**Security Settings:**
```yaml
security:
  enabled: true
  dlp:
    enabled: true
    patterns: [PII, API_KEY, PASSWORD]
```

---

## Themes

### Available Themes

| Theme | Description |
|-------|-------------|
| `default` | Cyan accents, balanced contrast |
| `dark` | Magenta accents, dark-friendly |
| `light` | Blue accents, light terminal friendly |

### Using Themes

```bash
# Command line
python -m src.tui.app --theme dark

# In config.yaml
tui:
  theme: dark
```

### Theme Elements

Themes customize:
- Title and subtitle colors
- Message colors (user, assistant, system, error)
- Border colors
- Scenario indicators
- Code highlighting
- Progress indicators

---

## Sessions

### Automatic Session Management

Sessions are automatically:
- Created on TUI start
- Saved periodically during use
- Saved on exit

### Manual Session Control

```bash
/save              # Save current session
/save analysis_v2  # Save with custom name
/load              # List sessions
/load analysis_v2  # Load specific session
```

### Session Contents

Sessions store:
- Conversation history
- Current scenario
- Configuration state
- Project context
- Metadata (timestamps, message counts)

### Session Storage Location

Default: `./sessions/`

Custom: `python -m src.tui.app --session-dir /path/to/sessions`

---

## Tips & Tricks

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current input |
| `Ctrl+D` | Exit (with confirmation) |
| `Up Arrow` | Previous command (readline) |
| `Down Arrow` | Next command (readline) |

### Command Aliases

| Alias | Command |
|-------|---------|
| `/h` | `/help` |
| `/q` | `/exit` |
| `/quit` | `/exit` |
| `/stats` | `/stat` |
| `/sql` | `/query` |
| `/proj` | `/project` |
| `/grp` | `/group` |
| `/sess` | `/session` |
| `/whoami` | `/auth me` |

### Efficient Workflows

**Quick Security Audit:**
```bash
/select 2
Find SQL injection vulnerabilities
Find command injection risks
Find XSS vulnerabilities
```

**Code Exploration:**
```bash
/select 1
What does the main function do?
Show me the call graph for function X
```

**Review Workflow:**
```bash
/review git
# Review results
/save security_review_dec9
```

### Query Tips

1. **Be specific**: "Find SQL injection in authentication module" > "Find SQL injection"

2. **Use scenario context**: Select appropriate scenario before querying

3. **Check statistics first**: Use `/stat` to understand database size

4. **Use SQL for precision**: `/query SELECT * FROM nodes_method WHERE name LIKE '%auth%'`

---

## Troubleshooting

### Common Issues

#### "Copilot not available"

**Cause**: ChromaDB not installed or initialization failed.

**Solutions:**
```bash
pip install chromadb
# or
pip install -r requirements.txt
```

#### "Database not found"

**Cause**: No CPG database available.

**Solutions:**
1. Import a project:
   ```bash
   python -m src.cli.import_commands full --path ./mycode
   ```
2. Check project configuration:
   ```bash
   /project list
   ```

#### "LLM Provider Error"

**Cause**: Missing API credentials.

**Solutions:**
1. Check environment variables:
   ```bash
   echo $GIGACHAT_CREDENTIALS
   echo $OPENAI_API_KEY
   ```
2. Verify config.yaml:
   ```bash
   /config llm
   ```

#### Slow Responses

**Cause**: Large database or network latency.

**Solutions:**
1. Check database statistics: `/stat`
2. Use more specific queries
3. Consider local LLM provider

#### Character Encoding Issues (Windows)

**Cause**: Terminal encoding mismatch.

**Solutions:**
```bash
# Set UTF-8 in PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Or use Windows Terminal (recommended)
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
python -m src.tui.app --debug
```

This shows:
- LLM API calls
- Database queries
- Retrieval operations
- Error stack traces

### Log Files

Logs are written to `logs/tui.log` (if configured).

---

## See Also

- [CLI Tools Reference](./CLI_TOOLS.md)
- [REST API Documentation](../api/REST_API.md)
- [TUI User Guide](./TUI_USER_GUIDE.md)
- [Security Documentation](../reference/SECURITY.md)
