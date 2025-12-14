# DLP: Data Loss Prevention

> Technical Documentation for Security and Compliance Teams

---

## Overview

The DLP (Data Loss Prevention) module in CodeGraph protects against sensitive data leakage when working with LLMs. The system scans both incoming user requests and outgoing LLM responses.

### Key Capabilities

- **25+ patterns** for sensitive data detection
- **Pre-request scanning** — blocking before sending to LLM
- **Post-response scanning** — masking in LLM responses
- **4 action modes**: BLOCK, MASK, WARN, LOG_ONLY
- **SIEM integration** — real-time event dispatch
- **Webhook notifications** — integration with external DLP systems

---

## Architecture

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER                                        │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    PRE-REQUEST SCANNER                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Credentials │  │    PII      │  │ Source Code │               │ │
│  │  │   (HIGH)    │  │  (MEDIUM)   │  │    (LOW)    │               │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │ │
│  │         │                │                │                       │ │
│  │         └────────────────┴────────────────┘                       │ │
│  │                          │                                        │ │
│  │              ┌───────────┴───────────┐                           │ │
│  │              ▼           ▼           ▼                           │ │
│  │          [BLOCK]     [MASK]     [WARN/LOG]                       │ │
│  │              │           │           │                           │ │
│  │              │     ┌─────┴─────┐     │                           │ │
│  │              │     │Replace w/ │     │                           │ │
│  │              │     │[REDACTED] │     │                           │ │
│  │              │     └─────┬─────┘     │                           │ │
│  └──────────────┼───────────┼───────────┼────────────────────────────┘ │
│                 │           │           │                              │
│                 │      ┌────┴────┐      │                              │
│                 │      ▼         ▼      │                              │
│            SIEM Event     GigaChat API  │                              │
│                               │         │                              │
│                               ▼         │                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                   POST-RESPONSE SCANNER                           │ │
│  │                          │                                        │ │
│  │              Mask sensitive data in                               │ │
│  │              LLM response                                         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│                       USER RESPONSE                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detection Categories

### 1. Credentials — HIGH Severity

| Pattern | Regex | Description |
|---------|-------|-------------|
| `api_key_generic` | `(?i)(api[_-]?key\|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?` | Generic API key |
| `aws_access_key` | `AKIA[0-9A-Z]{16}` | AWS Access Key ID |
| `aws_secret_key` | `(?i)aws[_\s]*secret[_\s]*access[_\s]*key["\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?` | AWS Secret Access Key |
| `private_key` | `-----BEGIN (RSA \|EC \|OPENSSH \|DSA )?PRIVATE KEY-----` | Private key (RSA, EC, DSA) |
| `password_pattern` | `(?i)(password\|passwd\|pwd)["\s:=]+["\']?([^\s"\']{8,})["\']?` | Password in config/code |
| `bearer_token` | `(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+` | JWT Bearer token |
| `github_token` | `gh[pousr]_[A-Za-z0-9_]{36,}` | GitHub Personal Access Token |

**Default Action**: `BLOCK`

### 2. PII (Personal Identifiable Information) — MEDIUM Severity

| Pattern | Regex | Mask | Description |
|---------|-------|------|-------------|
| `email` | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `[EMAIL]` | Email address |
| `phone_ru` | `(\+7\|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}` | `[PHONE]` | Russian phone |
| `phone_us` | `(\+1)?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}` | `[PHONE]` | US phone |
| `ssn` | `\b\d{3}-\d{2}-\d{4}\b` | `[SSN]` | US SSN |
| `credit_card` | `\b(?:\d{4}[\s-]?){3}\d{4}\b` | `[CARD]` | Credit card |
| `ip_address` | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `[IP]` | IPv4 address |
| `passport_ru` | `\b\d{2}\s?\d{2}\s?\d{6}\b` | `[PASSPORT]` | Russian passport |

**Default Action**: `MASK`

### 3. Source Code — LOW Severity

| Pattern | Regex | Mask | Description |
|---------|-------|------|-------------|
| `connection_string` | `(?i)(jdbc\|mysql\|postgresql\|mongodb\|redis)://[^\s"\'<>]+` | `[CONN_STRING]` | DB connection string |
| `internal_path_unix` | `(/home/\|/var/\|/etc/\|/opt/)[^\s"\'<>\|]+` | `[PATH]` | Unix path |
| `internal_path_windows` | `[A-Z]:\\(Users\|Windows\|Program)[^\s"\'<>\|]*` | `[PATH]` | Windows path |

**Default Action**: `WARN`

---

## DLP Actions

### Priority Hierarchy

| Priority | Action | Description | Result |
|:--------:|--------|-------------|--------|
| 4 (max) | `BLOCK` | Complete blocking | Request rejected, error to client |
| 3 | `MASK` | Masking | Data replaced with `[REDACTED]` |
| 2 | `WARN` | Warning | Request allowed, SIEM event |
| 1 | `LOG_ONLY` | Logging only | Audit log entry |

### Action Selection Logic

```python
# With multiple matches, highest priority is selected
action_priority = {
    DLPAction.BLOCK: 4,
    DLPAction.MASK: 3,
    DLPAction.WARN: 2,
    DLPAction.LOG_ONLY: 1,
}

# Example: found API key (BLOCK) and email (MASK)
# Result: BLOCK (priority 4 > 3)
```

---

## Configuration

### Basic Configuration (config.yaml)

```yaml
security:
  enabled: true

  dlp:
    enabled: true

    # Pre-request scanning (before sending to LLM)
    pre_request:
      enabled: true
      default_action: WARN

    # Post-response scanning (after receiving from LLM)
    post_response:
      enabled: true
      default_action: MASK

    # Categories and patterns
    categories:
      credentials:
        enabled: true
        action: BLOCK
        patterns: []  # Uses default patterns

      pii:
        enabled: true
        action: MASK
        patterns:
          - name: custom_ssn_pattern
            regex: '\b\d{3}-\d{2}-\d{4}\b'
            mask_with: '[SSN]'
            description: 'Social Security Number'

      source_code:
        enabled: true
        action: WARN
        patterns: []

    # Custom keywords
    keywords:
      sensitive_terms:
        words:
          - "confidential"
          - "top secret"
          - "internal use only"
        case_sensitive: false

    keywords_action: LOG_ONLY

    # Webhook for external DLP system
    webhook:
      enabled: false
      endpoint: "https://dlp.company.com/api/scan"
      auth_header: "Bearer ${DLP_WEBHOOK_TOKEN}"
      timeout_seconds: 10
      notify_on:
        - BLOCK
        - WARN
```

### Adding Custom Patterns

```python
from src.security.dlp.patterns import PatternRegistry
from src.security.config import DLPAction

registry = PatternRegistry(config)

# Add custom pattern
registry.add_pattern(
    category="pii",
    name="employee_id",
    regex=r'EMP-\d{6}',
    action=DLPAction.MASK,
    mask_with="[EMPLOYEE_ID]"
)

# Add keywords
registry.add_keywords(
    list_name="internal_projects",
    keywords=["Project Alpha", "Codename Beta"],
    case_sensitive=False
)
```

---

## API Reference

### ContentScanner

```python
from src.security.dlp.scanner import ContentScanner, DLPBlockedException
from src.security.config import get_security_config

# Initialize scanner
config = get_security_config()
scanner = ContentScanner(config.dlp)

# Pre-request scanning
result = scanner.scan_request(user_prompt)

if result.blocked:
    # Request blocked
    raise DLPBlockedException(result.matches)
elif result.action == DLPAction.MASK:
    # Use masked content
    user_prompt = result.modified_content

# Send to LLM...
llm_response = await llm_client.complete(user_prompt)

# Post-response scanning
result = scanner.scan_response(llm_response)
if result.has_matches:
    # Mask response
    llm_response = result.modified_content

return llm_response
```

### ScanResult

```python
@dataclass
class ScanResult:
    has_matches: bool           # Whether matches were found
    matches: List[DLPMatch]     # List of matches
    action: DLPAction           # Recommended action
    modified_content: str       # Masked content
    blocked: bool               # Whether to block request
```

### DLPMatch

```python
@dataclass
class DLPMatch:
    category: str          # Category (credentials, pii, source_code)
    pattern_name: str      # Pattern name
    match_type: MatchType  # REGEX or KEYWORD
    matched_text: str      # Found text
    start: int             # Start position
    end: int               # End position
    action: DLPAction      # Action for this match
    mask_with: str         # Replacement text
    severity: str          # Severity (critical, high, medium, low)
```

---

## SIEM Integration

### DLP Events

Each DLP trigger sends an event to SIEM:

```json
{
  "event_type": "DLP_BLOCK",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "severity": "CRITICAL",
  "user_id": "user_123",
  "session_id": "sess_456",
  "category": "credentials",
  "pattern_name": "aws_access_key",
  "action_taken": "BLOCK",
  "match_count": 1,
  "masked_preview": "Found AWS key: AKIA...",
  "request_path": "/api/v1/scenarios/execute",
  "ip_address": "10.0.0.50"
}
```

### Event Types

| Event | Severity | Description |
|-------|----------|-------------|
| `DLP_BLOCK` | CRITICAL | Request blocked |
| `DLP_MASK` | WARNING | Data masked |
| `DLP_WARN` | WARNING | Warning issued |
| `DLP_LOG` | INFO | Logging only |

---

## Webhook Integration

### External DLP Request Format

```json
POST /api/scan HTTP/1.1
Host: dlp.company.com
Authorization: Bearer xxx
Content-Type: application/json

{
  "scan_id": "scan_789",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "content_type": "request",
  "user_id": "user_123",
  "matches": [
    {
      "category": "credentials",
      "pattern_name": "aws_access_key",
      "severity": "high",
      "action": "BLOCK"
    }
  ],
  "action_taken": "BLOCK"
}
```

---

## Best Practices

### For Configuration

1. **Start with WARN** — set all categories to WARN to assess false positives
2. **Gradually tighten** — move critical categories to BLOCK after testing
3. **Configure exceptions** — add whitelist for known safe patterns
4. **Monitor SIEM** — track trigger statistics

### For Developers

1. **Don't log matched_text** in production without masking
2. **Handle DLPBlockedException** in API — return clear error message
3. **Test patterns** — use regex101.com for validation

### For Compliance

1. **Document patterns** — maintain registry of patterns in use
2. **Regular audit** — verify detection effectiveness
3. **GDPR compliance** — ensure PII patterns cover required data types

---

## Metrics and Monitoring

### Prometheus Metrics

```promql
# Block count
rate(dlp_blocks_total[5m])

# Mask count
rate(dlp_masks_total[5m])

# Distribution by category
dlp_matches_total{category="credentials"}
dlp_matches_total{category="pii"}

# Average scan time
histogram_quantile(0.95, rate(dlp_scan_duration_seconds_bucket[5m]))
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "DLP Blocks per Minute",
      "query": "rate(dlp_blocks_total[1m])"
    },
    {
      "title": "Top Triggered Patterns",
      "query": "topk(10, dlp_matches_total)"
    }
  ]
}
```

---

## Related Documents

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF_EN.md) — Security overview
- [SIEM Integration](./SIEM_INTEGRATION_EN.md) — SIEM integration
- [LLM Security](./LLM_SECURITY_EN.md) — LLM security

---

*Version: 1.0 | December 2025*
