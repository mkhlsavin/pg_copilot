# Scenario 09: Code Review

> Automated code review for pull requests, patches, and local changes.

## Quick Start

```bash
# Select Code Review Scenario
/select 09
```

## Review Sources

### GitHub Pull Request

```bash
/review github 123
```

### GitLab Merge Request

```bash
/review gitlab 456
```

### Local Git Changes

```bash
/review git
```

### Patch File

```bash
/review file path/to/changes.patch
```

## Understanding Review Output

```
╭─────────────── Review Results ────────────────────────────╮
│                                                           │
│  Score: 72/100         Recommendation: REQUEST_CHANGES    │
│                                                           │
│  Findings:                                                │
│                                                           │
│  🔴 CRITICAL  SQL Injection Risk                          │
│     Location: src/api/user_query.c:45                     │
│     Pattern: User input concatenated in query             │
│     Fix: Use parameterized queries                        │
│                                                           │
│  🟡 MEDIUM    Cyclomatic Complexity                       │
│     Location: src/parser/gram.y:1234                      │
│     Value: 47 (threshold: 10)                             │
│     Fix: Extract helper functions                         │
│                                                           │
│  🟢 LOW       Missing NULL check                          │
│     Location: src/utils/string.c:89                       │
│     Fix: Add NULL pointer validation                      │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

## Review with Inline Comments

```bash
/review git --format md --inline

╭─────────────── Inline Comments ───────────────────────────╮
│                                                           │
│  src/api/user_query.c                                     │
│                                                           │
│  Line 45:                                                 │
│    sprintf(query, "SELECT * FROM users WHERE id=%s", id); │
│    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^│
│    🔴 SQL Injection: Use snprintf with proper escaping    │
│                                                           │
│  Line 67:                                                 │
│    char *result = malloc(len);                            │
│    ^^^^^^^^^^^^^^^^^^^^^^^^^^^                            │
│    🟡 Memory: Check malloc return value for NULL          │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

## Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `--format md` | Markdown | Documentation, GitHub |
| `--format json` | JSON | CI/CD integration |
| `--format yaml` | YAML | Configuration |

## Review Options

```bash
# Basic review
/review git

# With format
/review git --format json

# With inline comments
/review git --inline

# Combined
/review github 123 --format md --inline
```

## Related Scenarios

- [Security Audit](./02-security-audit.md) - Deeper security analysis
- [Test Coverage](./07-test-coverage.md) - Coverage analysis
- [Refactoring](./05-refactoring.md) - Code quality
