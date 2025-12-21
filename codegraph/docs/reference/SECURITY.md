# Enterprise Security Module

## Overview

CodeGraph includes an enterprise-level security module for protecting sensitive data when using external LLM providers (GigaChat, OpenAI). This module ensures compliance with data protection requirements and provides comprehensive audit capabilities.

## Features

### 1. LLM Request/Response Logging
- Complete audit trail of all LLM interactions
- Configurable prompt redaction before logging
- Token usage and latency metrics
- Database storage with retention policies

### 2. SIEM Integration
Real-time log streaming to enterprise SIEM systems:
- **SysLog (RFC 5424)** - Standard syslog with structured data
- **CEF (Common Event Format)** - For ArcSight integration
- **LEEF (Log Event Extended Format)** - For IBM QRadar integration

### 3. DLP (Data Loss Prevention)
Pattern-based scanning to prevent data leaks:
- **Credentials Detection** - API keys, passwords, private keys
- **PII Detection** - Email, phone, credit cards, INN/SNILS
- **Source Code Paths** - Internal paths, connection strings
- **Custom Keywords** - Organization-specific blacklists

Configurable actions per category:
- `BLOCK` - Reject the request entirely
- `MASK` - Replace sensitive data with `[REDACTED]`
- `WARN` - Log warning but allow
- `LOG_ONLY` - Log for audit only

### 4. HashiCorp Vault Integration
Secure secrets management:
- Dynamic credential retrieval
- Multiple auth methods (Token, AppRole, Kubernetes)
- Automatic secret rotation
- Caching with TTL

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SecureLLMProvider                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  DLP Scanner │  │ Content      │  │  LLM Audit Logger    │  │
│  │  (Pre/Post)  │  │ Filter       │  │  (DB + SIEM)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  DLP Actions │     │ BaseLLMProv. │     │   SIEM Dispatcher    │
│  BLOCK/MASK  │     │ (GigaChat)   │     │  ┌────┐┌────┐┌────┐ │
│  /WARN/LOG   │     │              │     │  │Sys ││CEF ││LEEF│ │
└──────────────┘     └──────────────┘     │  │Log ││    ││    │ │
         │                                 │  └────┘└────┘└────┘ │
         ▼                                 └──────────────────────┘
┌──────────────┐                                    │
│ DLP Webhook  │                                    ▼
│ (External)   │                           ┌──────────────┐
└──────────────┘                           │    SIEM      │
                                           │  (Splunk/    │
┌──────────────┐                           │   QRadar)    │
│ HashiCorp    │◄── Secret Rotation        └──────────────┘
│ Vault        │
└──────────────┘
```

## Configuration

### Enable Security Module

Set environment variable or update `config.yaml`:

```bash
export SECURITY_ENABLED=true
export SIEM_ENABLED=true
export DLP_ENABLED=true
```

### Full Configuration (config.yaml)

```yaml
security:
  # Master switch
  enabled: true

  # LLM Logging
  llm_logging:
    enabled: true
    log_prompts: true
    redact_prompts: true
    max_prompt_length: 2000
    log_responses: true
    log_token_usage: true
    log_latency: true
    log_to_database: true

  # SIEM
  siem:
    enabled: true
    syslog:
      enabled: true
      protocol: "tls"  # udp, tcp, tls
      host: "siem.company.com"
      port: 6514
      facility: 16  # local0
      app_name: "codegraph"
    cef:
      enabled: true
      host: "arcsight.company.com"
      port: 514
    leef:
      enabled: false

  # DLP
  dlp:
    enabled: true
    pre_request:
      enabled: true
      default_action: "WARN"
    post_response:
      enabled: true
      default_action: "MASK"
    categories:
      credentials:
        enabled: true
        action: "BLOCK"
        severity: "critical"
      pii:
        enabled: true
        action: "MASK"
        severity: "high"
    webhook:
      enabled: true
      endpoint: "https://dlp.company.com/api/alerts"
      notify_on: ["BLOCK", "WARN"]

  # Vault
  vault:
    enabled: true
    url: "https://vault.company.com:8200"
    auth_method: "approle"
    secrets_mount_point: "secret"
    llm_secrets_path: "codegraph/llm"
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECURITY_ENABLED` | Enable security module | `false` |
| `SIEM_ENABLED` | Enable SIEM integration | `false` |
| `SIEM_SYSLOG_HOST` | SysLog server host | `localhost` |
| `SIEM_SYSLOG_PORT` | SysLog server port | `514` |
| `SIEM_CEF_HOST` | CEF server host | `localhost` |
| `SIEM_LEEF_HOST` | LEEF server host | `localhost` |
| `DLP_ENABLED` | Enable DLP scanning | `true` |
| `DLP_WEBHOOK_URL` | DLP webhook endpoint | - |
| `DLP_WEBHOOK_AUTH` | DLP webhook auth header | - |
| `VAULT_ENABLED` | Enable Vault integration | `false` |
| `VAULT_ADDR` | Vault server URL | `http://localhost:8200` |
| `VAULT_TOKEN` | Vault token | - |
| `VAULT_ROLE_ID` | AppRole role ID | - |
| `VAULT_SECRET_ID` | AppRole secret ID | - |

## Usage Examples

### Basic Usage (Automatic)

Security wrapping is automatic when enabled:

```python
from src.llm import create_llm_provider

# Provider is automatically wrapped with security layer
provider = create_llm_provider()

# All requests are now filtered and logged
response = provider.generate(
    system_prompt="You are a code analyst",
    user_prompt="Analyze this function",
)
```

### Manual Security Wrapper

```python
from src.llm import GigaChatProvider
from src.security import get_security_config, SecureLLMProvider

# Create base provider
base_provider = GigaChatProvider(config)

# Wrap with security
secure_provider = SecureLLMProvider(
    wrapped_provider=base_provider,
    config=get_security_config()
)

# Use secure provider
response = secure_provider.generate(
    system_prompt="Analyze code",
    user_prompt="def process_payment(card_number='4111111111111111')...",
    _user_id="user-123",  # Optional: user context
    _ip_address="192.168.1.100",  # Optional: IP for audit
)
```

### DLP Scanning Only

```python
from src.security.dlp import ContentScanner
from src.security.config import get_security_config

config = get_security_config()
scanner = ContentScanner(config.dlp)

# Scan content
result = scanner.scan_request("API_KEY=sk-1234567890abcdef")

if result.blocked:
    print(f"Content blocked! Matches: {result.matches}")
elif result.has_matches:
    print(f"Sensitive data found: {result.matches}")
    # Use masked content
    safe_content = result.modified_content
```

### SIEM Event Dispatch

```python
from src.security.siem import (
    SecurityEvent, SecurityEventType,
    init_siem_dispatcher
)
from src.security.config import get_security_config

# Initialize dispatcher
dispatcher = init_siem_dispatcher(get_security_config().siem)

# Create and dispatch event
event = SecurityEvent.create(
    event_type=SecurityEventType.DLP_BLOCK,
    message="Credentials detected in LLM request",
    severity=3,  # Error
    user_id="user-123",
    request_id="req-456",
    details={"pattern": "aws_key", "category": "credentials"}
)

dispatcher.dispatch(event)
```

## DLP Patterns

### Built-in Patterns

#### Credentials
- `api_key` - Generic API keys
- `aws_key` - AWS Access Key IDs (AKIA...)
- `aws_secret` - AWS Secret Keys
- `private_key` - PEM private keys
- `password` - Password patterns
- `jwt_token` - JSON Web Tokens
- `bearer_token` - Bearer auth tokens
- `basic_auth` - Base64 Basic auth

#### PII (Russian locale)
- `email` - Email addresses
- `phone_ru` - Russian phone numbers
- `credit_card` - Credit card numbers
- `inn` - Russian INN (tax ID)
- `snils` - Russian SNILS
- `passport_ru` - Russian passport numbers

#### Source Code
- `connection_string` - Database connection strings
- `internal_path` - Internal file paths
- `ip_address` - IP addresses

### Custom Patterns

Add custom patterns via config:

```yaml
dlp:
  categories:
    custom:
      enabled: true
      action: "WARN"
      severity: "medium"
      patterns:
        - name: "project_code"
          regex: "PROJECT-[A-Z]{2,4}-\d{4,6}"
          mask_with: "[PROJECT-ID]"
```

## Database Tables

### llm_audit_log

Stores all LLM interactions:

| Column | Type | Description |
|--------|------|-------------|
| request_id | UUID | Unique request identifier |
| user_id | UUID | User who made request |
| provider | VARCHAR | LLM provider name |
| model | VARCHAR | Model name |
| system_prompt_hash | VARCHAR | SHA256 of system prompt |
| user_prompt_preview | TEXT | Redacted prompt preview |
| response_preview | TEXT | Response preview |
| prompt_tokens | INT | Prompt token count |
| completion_tokens | INT | Completion token count |
| latency_ms | FLOAT | Request latency |
| dlp_action | VARCHAR | DLP action taken |
| dlp_categories | ARRAY | Matched DLP categories |
| timestamp | TIMESTAMP | Request time |

### dlp_events

Detailed DLP match events:

| Column | Type | Description |
|--------|------|-------------|
| request_id | UUID | Request identifier |
| action | VARCHAR | Action taken |
| category | VARCHAR | DLP category |
| pattern_name | VARCHAR | Matched pattern |
| severity | VARCHAR | Match severity |
| timestamp | TIMESTAMP | Event time |

## SIEM Event Formats

### SysLog (RFC 5424)

```
<134>1 2024-12-09T10:30:00.000Z codegraph.company.com codegraph - llm.dlp.block [llm@12345 requestId="req-123" userId="user-456" provider="GigaChat" action="BLOCK" category="credentials"] DLP BLOCK: 2 patterns in request
```

### CEF

```
CEF:0|CodeGraph|CodeAnalysis|1.0|llm.dlp.block|DLP Block|7|rt=Dec 09 2024 10:30:00 src=192.168.1.100 suser=user-456 cs1=req-123 cs1Label=RequestID cs2=GigaChat cs2Label=Provider act=BLOCK cat=credentials
```

### LEEF

```
LEEF:2.0|CodeGraph|CodeAnalysis|1.0|llm.dlp.block|	devTime=Dec 09 2024 10:30:00	src=192.168.1.100	usrName=user-456	requestId=req-123	provider=GigaChat	action=BLOCK	category=credentials
```

## Webhook Integration

DLP webhook payload format:

```json
{
  "alert_id": "a1b2c3d4e5f6",
  "timestamp": "2024-12-09T10:30:00.000Z",
  "action": "BLOCK",
  "match_count": 2,
  "categories": ["credentials"],
  "patterns": ["api_key", "aws_key"],
  "request_id": "req-123",
  "user_id": "user-456",
  "ip_address": "192.168.1.100",
  "severity": "critical",
  "context": {}
}
```

## Security Best Practices

1. **Enable TLS** for SIEM connections in production
2. **Use AppRole** or Kubernetes auth for Vault (not plain tokens)
3. **Set appropriate DLP actions** - BLOCK for credentials, MASK for PII
4. **Configure log retention** in your SIEM for compliance
5. **Monitor DLP_BLOCK events** for potential data exfiltration attempts
6. **Regular pattern updates** for new credential formats
7. **Test DLP patterns** before production deployment

## Compliance

The security module helps meet requirements for:
- **GDPR** - PII detection and masking
- **PCI DSS** - Credit card number detection
- **SOX** - Complete audit trail
- **HIPAA** - PHI protection (with custom patterns)
- **152-ФЗ** - Russian personal data law (PII patterns)

---

## Advanced Security Features

### 5. File-Based Security Scanner

Fast file-based scanning for quick security assessments without CPG generation.

#### Usage

```python
from src.security.file_scanner import FileSecurityScanner

scanner = FileSecurityScanner()
result = scanner.scan("/path/to/project")

print(f"Critical: {result.critical_count}")
print(f"High: {result.high_count}")

for finding in result.findings:
    print(f"{finding.severity}: {finding.description}")
    print(f"  File: {finding.file_path}:{finding.line_number}")
```

#### CLI Usage

```bash
# Quick scan
python -m src.cli.security_audit quick --path ./myproject

# Full scan with report
python -m src.cli.security_audit full --path ./myproject --format all
```

### 6. Taint-Verified Scanner

Reduces false positives by verifying data flow from sources to sinks using CPG analysis.

#### Concept

Traditional pattern matching produces many false positives. The taint-verified scanner:
1. Identifies potential vulnerabilities via patterns
2. Traces data flow from taint sources (user input) to sinks (dangerous functions)
3. Only reports issues with confirmed taint paths

#### Taint Sources (Python/Django)

```python
# Django request data
request.GET, request.POST, request.data
request.body, request.FILES, request.META

# Flask request data
request.args, request.form, request.json

# Generic input
input(), raw_input(), sys.stdin, os.getenv()

# File/Network input
open(), read(), recv(), urlopen()
```

#### Dangerous Sinks by Category

| Category | Sinks |
|----------|-------|
| SQL Injection | `execute`, `raw`, `cursor.execute`, `RawSQL` |
| Command Injection | `os.system`, `subprocess.run`, `eval`, `exec` |
| Path Traversal | `open`, `os.path.join`, `send_file` |
| XSS | `mark_safe`, `HttpResponse` |
| Deserialization | `pickle.loads`, `yaml.load`, `marshal.loads` |

#### Usage

```python
from src.security.taint_verified_scanner import TaintVerifiedScanner

scanner = TaintVerifiedScanner(duckdb_path="cpg.duckdb")

# Verify SQL injection findings
verified = scanner.verify_sql_injection_findings(raw_findings)

for finding in verified:
    print(f"Confirmed: {finding['description']}")
    print(f"Taint path: {finding['taint_path']}")
```

### 7. MITRE D3FEND Hardening Checks

Implements all MITRE D3FEND Source Code Hardening techniques.

#### Supported Checks

| D3FEND ID | Name | Description |
|-----------|------|-------------|
| D3-VI | Variable Initialization | Detect uninitialized variables |
| D3-CS | Credential Scrubbing | Ensure credentials are cleared from memory |
| D3-IRV | Integer Range Validation | Check for integer overflow risks |
| D3-RN | Reference Nullification | Check pointer cleanup after free |
| D3-TL | Trusted Library | Verify use of safe library functions |
| D3-VTV | Variable Type Validation | Check type safety |
| D3-MBSV | Memory Block Start Validation | Validate memory block boundaries |
| D3-NPC | Null Pointer Checking | Detect missing null checks |
| D3-DLV | Domain Logic Validation | Check business logic validation |
| D3-OLV | Operational Logic Validation | Verify operational constraints |

#### Usage

```python
from src.security.hardening import HardeningScanner

scanner = HardeningScanner(duckdb_path="cpg.duckdb")
results = scanner.run_all_checks()

for result in results:
    print(f"[{result.check.d3fend_id}] {result.check.d3fend_name}")
    print(f"  Violations: {len(result.violations)}")
    print(f"  Remediation: {result.check.remediation}")
```

#### Configuration

```yaml
security:
  hardening:
    enabled: true
    checks:
      D3-VI: true    # Variable Initialization
      D3-CS: true    # Credential Scrubbing
      D3-NPC: true   # Null Pointer Checking
    severity_threshold: "medium"  # Skip low severity
```

### 8. SAST Comparison

Compare CodeGraph findings with external SAST tools to validate accuracy.

#### Supported Tools

- **Bandit** - Python security linter
- **Semgrep** - Multi-language static analysis

#### Usage

```python
from src.security.sast_comparison import SASTComparison

comparison = SASTComparison(project_path="./myproject")

# Compare with Bandit
result = comparison.compare_with_bandit(our_findings)

print(f"Precision: {result.precision:.2%}")
print(f"Recall: {result.recall:.2%}")
print(f"F1 Score: {result.f1_score:.2%}")
print(f"Unique to us: {len(result.only_ours)}")
print(f"Missed by us: {len(result.only_theirs)}")
```

#### CLI Usage

```bash
# Compare with Bandit
python -m src.cli.security_audit full --path ./myproject --compare bandit

# Compare with Semgrep
python -m src.cli.security_audit full --path ./myproject --compare semgrep
```

### 9. Security Report Generator

Generate comprehensive security reports in multiple formats.

#### Supported Formats

| Format | Use Case |
|--------|----------|
| JSON | CI/CD integration, programmatic access |
| Markdown | Documentation, manual review |
| SARIF | GitHub Security Alerts, IDE integration |

#### Languages

Reports support localization:
- English (`en`)
- Russian (`ru`)

#### Usage

```python
from src.security.report_generator import SecurityReportGenerator

generator = SecurityReportGenerator(language="en")

# Generate report from scan results
report = generator.generate(
    project_name="MyProject",
    project_path="./myproject",
    file_findings=file_scan.findings,
    cpg_findings=cpg_scan.findings,
    hardening_findings=hardening_results,
)

# Export to different formats
generator.export_json(report, "report.json")
generator.export_markdown(report, "report.md")
generator.export_sarif(report, "report.sarif")
```

#### Report Sections

1. **Executive Summary** - High-level finding counts
2. **Critical Findings** - Immediate action required
3. **High Severity** - Address before deployment
4. **D3FEND Compliance** - Hardening check results
5. **Detailed Findings** - Full list with remediation
6. **Metrics** - Coverage, precision, recall

### 10. CPG Context Resolver

Enriches security findings with CPG context for better understanding.

#### Features

- Call graph context (callers/callees)
- Data flow paths
- Control flow analysis
- Module boundaries

#### Usage

```python
from src.security.cpg_context_resolver import CPGContextResolver

resolver = CPGContextResolver(duckdb_path="cpg.duckdb")

# Enrich finding with context
enriched = resolver.enrich_finding(finding)

print(f"Callers: {enriched['callers']}")
print(f"Data flow: {enriched['data_flow_path']}")
print(f"Module: {enriched['module']}")
```

---

## Security Module Structure

```
src/security/
├── __init__.py          # Module exports
├── _base.py             # Base classes (Severity, Category)
├── config.py            # Security configuration
│
├── dlp/                 # Data Loss Prevention
│   ├── patterns.py      # DLP patterns (credentials, PII)
│   ├── scanner.py       # Content scanner
│   ├── actions.py       # DLP actions (BLOCK, MASK, WARN)
│   └── webhook.py       # Alert webhooks
│
├── siem/                # SIEM Integration
│   ├── base_handler.py  # Base handler class
│   ├── syslog_handler.py
│   ├── cef_handler.py
│   ├── leef_handler.py
│   ├── buffer.py        # Event buffering
│   └── dispatcher.py    # Multi-handler dispatch
│
├── vault/               # HashiCorp Vault
│   ├── client.py        # Vault API client
│   └── secret_manager.py
│
├── llm/                 # LLM Security
│   ├── secure_provider.py  # SecureLLMProvider wrapper
│   └── request_logger.py   # Audit logging
│
├── hardening/           # D3FEND Hardening
│   ├── base.py          # Check definitions
│   ├── d3fend_checks.py # All D3FEND checks
│   └── hardening_scanner.py
│
├── patterns/            # Vulnerability Patterns
│   ├── injection.py     # SQL/Command injection
│   ├── memory.py        # Memory safety
│   ├── crypto.py        # Cryptographic issues
│   ├── auth.py          # Authentication flaws
│   ├── concurrency.py   # Race conditions
│   └── python_django.py # Python/Django specific
│
├── file_scanner.py      # File-based scanning
├── taint_verified_scanner.py  # Taint analysis
├── cpg_context_resolver.py    # CPG enrichment
├── sast_comparison.py   # SAST tool comparison
├── report_generator.py  # Report generation
└── report_localizer.py  # i18n support
```

---

## Quick Start Guide

### 1. Enable Security Features

```bash
# Environment variables
export SECURITY_ENABLED=true
export DLP_ENABLED=true
export SIEM_ENABLED=true
```

### 2. Run Security Audit

```bash
# Full audit with all checks
python -m src.cli.security_audit full \
    --path ./myproject \
    --format all \
    --verbose
```

### 3. Review Reports

```bash
# Reports are saved to ./security_reports/
ls security_reports/
# security_audit_20241209_103000.json
# security_audit_20241209_103000.md
# security_audit_20241209_103000.sarif
```

### 4. Integrate with CI/CD

```yaml
# .github/workflows/security.yml
- name: Security Audit
  run: |
    python -m src.cli.security_audit full \
      --path . \
      --format sarif \
      --output security.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: security.sarif
```

---

## See Also

- [CLI Tools Reference](../guides/CLI_TOOLS.md) - Security audit CLI usage
- [TUI Guide](../guides/TUI_GUIDE.md) - Interactive security scenario
- [API Documentation](../api/REST_API.md) - Security endpoints
