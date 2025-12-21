# Scenario 08: Compliance Checking

> Compliance officer verifying coding standards and regulatory requirements.

## Quick Start

```bash
# Select Compliance Scenario
/select 08
```

## Coding Standards Compliance

### Style Violations

```
> Check for coding standard violations

╭─────────────── Style Compliance ────────────────────────────╮
│                                                              │
│  Violations Found: 47                                        │
│                                                              │
│  By Category:                                                │
│    Naming conventions:     18                                │
│    Indentation:            12                                │
│    Comment style:          9                                 │
│    Function length:        8                                 │
│                                                              │
│  Sample Violations:                                          │
│                                                              │
│  🟡 src/backend/utils/cache.c:234                            │
│     Variable 'TempVar' should use snake_case                 │
│                                                              │
│  🟡 src/backend/executor/nodeHash.c:567                      │
│     Function exceeds 200 line limit (234 lines)              │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### API Compatibility

```
> Check for deprecated API usage

╭─────────────── API Compliance ──────────────────────────────╮
│                                                              │
│  Deprecated API Usage:                                       │
│                                                              │
│  🔴 strcpy() - Use strlcpy instead                           │
│     Locations: 23 occurrences                                │
│     Files: utils/string.c, libpq/pqformat.c                  │
│                                                              │
│  🔴 sprintf() - Use snprintf instead                         │
│     Locations: 45 occurrences                                │
│     Files: various                                           │
│                                                              │
│  🟡 gets() - Use fgets instead                               │
│     Locations: 2 occurrences                                 │
│     Files: contrib/pg_test.c                                 │
│                                                              │
│  Remediation: Use safe string functions                      │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Security Compliance

### OWASP Top 10

```
> Check for OWASP Top 10 violations

╭─────────────── OWASP Compliance ────────────────────────────╮
│                                                              │
│  OWASP Top 10 Analysis:                                      │
│                                                              │
│  A1 - Injection:                    3 potential issues       │
│  A2 - Broken Authentication:        0 issues                 │
│  A3 - Sensitive Data Exposure:      2 potential issues       │
│  A4 - XXE:                          0 issues                 │
│  A5 - Broken Access Control:        1 potential issue        │
│  A6 - Security Misconfiguration:    N/A (runtime)            │
│  A7 - XSS:                          0 issues                 │
│  A8 - Insecure Deserialization:     0 issues                 │
│  A9 - Using Known Vulnerabilities:  Check dependencies       │
│  A10 - Insufficient Logging:        4 areas lacking          │
│                                                              │
│  Total: 10 potential compliance gaps                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### CWE Mapping

```
> Map findings to CWE identifiers

╭─────────────── CWE Mapping ─────────────────────────────────╮
│                                                              │
│  Common Weakness Enumeration Findings:                       │
│                                                              │
│  CWE-89 (SQL Injection):           3 occurrences             │
│    src/pl/plpgsql/src/pl_exec.c:4567                         │
│    src/backend/commands/copy.c:234                           │
│    src/backend/replication/slot.c:789                        │
│                                                              │
│  CWE-120 (Buffer Overflow):        5 occurrences             │
│    Various string handling locations                         │
│                                                              │
│  CWE-476 (NULL Pointer Deref):     12 occurrences            │
│    Missing NULL checks after allocation                      │
│                                                              │
│  Full report available in SARIF format                       │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Documentation Compliance

### Comment Coverage

```
> Check documentation coverage

╭─────────────── Documentation Compliance ────────────────────╮
│                                                              │
│  Comment Coverage Analysis:                                  │
│                                                              │
│  Overall coverage: 67%                                       │
│                                                              │
│  By Module:                                                  │
│    executor/:     78%  ✅                                    │
│    parser/:       72%  ✅                                    │
│    optimizer/:    65%  🟡                                    │
│    storage/:      54%  🔴                                    │
│    utils/:        48%  🔴                                    │
│                                                              │
│  Missing Documentation:                                      │
│    - 23 public functions without comments                    │
│    - 8 complex functions without algorithm explanation       │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Compliance Reports

### Generate Full Report

```bash
# Generate compliance report
python -m src.cli.compliance_report full \
  --path /path/to/project \
  --standards owasp,cwe,style \
  --output-dir ./compliance_reports \
  --format sarif
```

Output formats:
- `sarif` - For IDE/CI integration
- `json` - Machine-readable
- `md` - Human-readable Markdown
- `html` - Web report

## Example Questions

- "Check for coding standard violations"
- "Find deprecated API usage"
- "Map findings to CWE identifiers"
- "Check OWASP Top 10 compliance"
- "Verify documentation coverage"
- "Generate compliance report for [standard]"

## Related Scenarios

- [Security Audit](./02-security-audit.md) - Deep security analysis
- [Code Review](./09-code-review.md) - Review compliance
- [Tech Debt](./12-tech-debt.md) - Technical debt assessment
