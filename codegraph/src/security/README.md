# Security Module

Security scanning and analysis system including vulnerability detection, DLP (Data Loss Prevention), and SIEM integration.

## Overview

```
src/security/
├── scanner.py           # Vulnerability scanner
├── dlp.py               # Data Loss Prevention
├── siem.py              # SIEM integration
├── patterns/            # Vulnerability patterns
│   ├── sql_injection.py
│   ├── buffer_overflow.py
│   └── input_validation.py
└── __init__.py
```

## Features

### Vulnerability Detection
- SQL injection
- Buffer overflow
- Use-after-free
- Format string vulnerabilities
- Integer overflow
- Path traversal

### DLP Integration
- Sensitive data detection
- PII filtering in LLM responses
- Audit logging

### SIEM Integration
- Security event logging
- Alert generation
- Compliance reporting

## Usage

```python
from src.security.scanner import SecurityScanner

scanner = SecurityScanner()
vulnerabilities = scanner.scan_codebase()

for vuln in vulnerabilities:
    print(f"{vuln.severity}: {vuln.description}")
```

## Configuration

```yaml
security:
  enabled: true
  dlp:
    enabled: true
    patterns: ['ssn', 'credit_card', 'api_key']
  siem:
    enabled: true
    endpoint: https://siem.example.com
```

## See Also

- `/src/workflow/scenarios/security.py` - Security workflow
- `/docs/guides/SECURITY.md` - Security guide
