# Scenario 02: Security Audit

> Security engineer performing vulnerability assessment and code hardening checks.

## Quick Start

```bash
# Select Security Audit Scenario
/select 02
```

## Vulnerability Scanning

### SQL Injection Detection

```
> Find SQL injection vulnerabilities

╭─────────────── Security Findings ─────────────────────────╮
│                                                           │
│  🔴 CRITICAL: SQL Injection                               │
│                                                           │
│     Location: src/pl/plpgsql/src/pl_exec.c:4567           │
│     Pattern: Dynamic query with string concatenation      │
│     Code:                                                 │
│       snprintf(query, "SELECT * FROM %s", table_name);    │
│                                                           │
│     Risk: User-controlled table_name can inject SQL       │
│     Fix: Use quote_identifier() for table names           │
│     CWE: CWE-89                                           │
│                                                           │
│  Total findings: 7 critical, 12 high, 34 medium           │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

### Buffer Overflow Detection

```
> Find buffer overflow risks in string functions
> Show functions using sprintf without bounds
```

## Taint Flow Analysis

### Identify Entry Points

```
> Find all external entry points

╭─────────────── Entry Points ──────────────────────────────╮
│                                                           │
│  Network Entry Points:                                    │
│    - pq_getmsgstring()     - Read string from client      │
│    - pq_getmsgint()        - Read int from client         │
│    - ProcessClientRead()   - Raw socket read              │
│                                                           │
│  SQL Entry Points:                                        │
│    - exec_simple_query()   - Direct SQL execution         │
│    - exec_parse_message()  - Prepared statement           │
│    - exec_bind_message()   - Parameter binding            │
│                                                           │
│  File Entry Points:                                       │
│    - pg_read_file()        - Read arbitrary file          │
│    - pg_ls_dir()           - List directory               │
│                                                           │
│  Total: 47 entry points identified                        │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

### Trace Data Flow

```
> Trace data flow from PQgetvalue to SQL execution

╭─────────────── Taint Flow ────────────────────────────────╮
│                                                           │
│  SOURCE: PQgetvalue() [Client Input]                      │
│      ↓                                                    │
│  pq_getmsgstring()                                        │
│      ↓                                                    │
│  exec_simple_query()                                      │
│      ↓                                                    │
│  pg_parse_query()                                         │
│      ↓                                                    │
│  SINK: SPI_execute() [SQL Execution]                      │
│                                                           │
│  Risk Level: HIGH                                         │
│  Recommendation: Add input validation at entry point      │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

## D3FEND Source Code Hardening

The D3FEND module analyzes code for 11 MITRE D3FEND Source Code Hardening techniques:

| ID | Technique | Description | CWE |
|----|-----------|-------------|-----|
| D3-VI | Variable Initialization | Uninitialized variables | CWE-457 |
| D3-CS | Credential Scrubbing | Hardcoded credentials | CWE-798 |
| D3-IRV | Integer Range Validation | Integer overflow risks | CWE-190 |
| D3-PV | Pointer Validation | Pointer dereference without check | CWE-476 |
| D3-RN | Reference Nullification | Use-after-free risks | CWE-416 |
| D3-TL | Trusted Library | Unsafe function usage | CWE-676 |
| D3-NPC | Null Pointer Checking | Missing NULL checks | CWE-476 |

### Full Hardening Audit

```
> Run D3FEND hardening compliance check

╭─────────────── D3FEND Compliance Report ─────────────────────╮
│                                                               │
│  Overall Compliance Score: 72.5%                              │
│                                                               │
│  Findings by Technique:                                       │
│                                                               │
│  D3-VI (Variable Initialization): 23 issues                   │
│  D3-TL (Trusted Library): 12 issues                           │
│  D3-NPC (Null Pointer Checking): 8 issues                     │
│  D3-RN (Reference Nullification): 6 issues                    │
│                                                               │
│  Category Scores:                                             │
│    Initialization: 65%                                        │
│    Memory Safety: 78%                                         │
│    Pointer Safety: 82%                                        │
│    Library Safety: 58%                                        │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

### Check Unsafe Functions (D3-TL)

```
> Check for unsafe function usage (D3-TL Trusted Library)

╭─────────────── D3-TL: Trusted Library ───────────────────────╮
│                                                               │
│  🔴 CRITICAL - strcpy (buffer overflow risk):                 │
│    src/backend/utils/adt/varlena.c:234                        │
│    src/backend/libpq/pqformat.c:567                           │
│                                                               │
│  🔴 CRITICAL - sprintf (format string risk):                  │
│    src/backend/libpq/auth.c:567                               │
│                                                               │
│  Remediation:                                                 │
│    - strcpy → strncpy/strlcpy                                 │
│    - sprintf → snprintf                                       │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

### Check Null Pointer Safety (D3-NPC)

```
> Find null pointer vulnerabilities (D3-NPC)

╭─────────────── D3-NPC: Null Pointer Checking ────────────────╮
│                                                               │
│  Missing NULL Checks After Allocation: 23                     │
│                                                               │
│  malloc without check:                                        │
│    src/backend/utils/mmgr/aset.c:345                          │
│      char *buf = malloc(size);                                │
│      use(buf);  // ← No NULL check!                           │
│                                                               │
│  Example Fix:                                                 │
│    char *buf = malloc(size);                                  │
│    if (buf == NULL) {                                         │
│        ereport(ERROR, (errcode(ERRCODE_OUT_OF_MEMORY)));      │
│    }                                                          │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

## Language-Specific Security Patterns

CodeGraph supports security analysis for multiple programming languages with CWE/CAPEC mappings.

### Supported Languages and Vulnerability Patterns

| Language | Patterns | Key CWEs |
|----------|----------|----------|
| **C/C++** | Buffer overflow, format string, UAF, command injection | CWE-120, CWE-134, CWE-416, CWE-78 |
| **Python/Django** | SQL injection, XSS, CSRF, deserialization | CWE-89, CWE-79, CWE-352, CWE-502 |
| **JavaScript/TypeScript** | XSS, prototype pollution, eval injection, SSRF | CWE-79, CWE-1321, CWE-94, CWE-918 |
| **Go** | Race conditions, SQL injection, path traversal, insecure TLS | CWE-362, CWE-89, CWE-22, CWE-295 |
| **Ruby/Rails** | Eval injection, YAML deserialization, mass assignment | CWE-94, CWE-502, CWE-915 |
| **C#/.NET** | SQL injection, XSS, insecure deserialization, XXE | CWE-89, CWE-79, CWE-502, CWE-611 |
| **Kotlin/Android** | WebView XSS, intent redirection, insecure storage | CWE-79, CWE-927, CWE-312 |
| **Swift/iOS** | Keychain misuse, URL scheme hijacking, TLS bypass | CWE-312, CWE-939, CWE-295 |
| **Java** | SQL injection, deserialization, XXE, LDAP injection | CWE-89, CWE-502, CWE-611, CWE-90 |
| **PHP** | SQL injection, XSS, command injection, path traversal | CWE-89, CWE-79, CWE-78, CWE-22 |

### CWE Database Coverage (30+ CWEs)

**Injection Vulnerabilities:**
- CWE-78: OS Command Injection
- CWE-89: SQL Injection
- CWE-94: Code Injection
- CWE-134: Format String

**Web Vulnerabilities:**
- CWE-79: Cross-Site Scripting (XSS)
- CWE-352: Cross-Site Request Forgery (CSRF)
- CWE-502: Insecure Deserialization
- CWE-611: XML External Entity (XXE)
- CWE-918: Server-Side Request Forgery (SSRF)
- CWE-1321: Prototype Pollution

**Memory Safety (C/C++):**
- CWE-120: Buffer Overflow
- CWE-416: Use After Free
- CWE-476: NULL Pointer Dereference
- CWE-190: Integer Overflow

**Authentication/Authorization:**
- CWE-798: Hardcoded Credentials
- CWE-284: Improper Access Control
- CWE-862: Missing Authorization

### CAPEC Attack Patterns (15+ patterns)

- CAPEC-66: SQL Injection
- CAPEC-86: XSS Through HTTP Headers
- CAPEC-88: OS Command Injection
- CAPEC-100: Buffer Overflow
- CAPEC-126: Path Traversal
- CAPEC-586: Object Injection (Deserialization)
- CAPEC-664: Server-Side Request Forgery

### Python/Django Example

```bash
# Switch to Django project
/project switch my_django_app

# Run security queries
> Find SQL injection vulnerabilities in views
> Check for XSS in templates
> Find endpoints without CSRF protection
```

### JavaScript/TypeScript Example

```
> Find prototype pollution vulnerabilities
> Check for XSS via innerHTML
> Find eval() usage with user input
```

### Go Example

```
> Find race conditions in goroutines
> Check for SQL injection in database queries
> Find insecure TLS configurations
```

## CLI Security Reports

Generate comprehensive security reports:

```bash
# Auto-detect language
python -m src.cli.security_audit full \
  --path /path/to/project \
  --output ./security_reports

# Specify language explicitly
python -m src.cli.security_audit full \
  --path /path/to/project \
  --language python \
  --output ./security_reports

# Available languages: auto, c, cpp, python, javascript, typescript,
#                      go, ruby, csharp, kotlin, swift, java, php
```

Generates:
- `security_report.md` - Human-readable report
- `security_report.json` - Machine-readable for CI/CD
- `security_report.sarif` - GitHub Security Alerts format

## Related Scenarios

- [Compliance](./08-compliance.md) - Regulatory compliance checks
- [Incident Response](./14-incident-response.md) - Post-breach investigation
- [Entry Points](./16-entry-points.md) - Attack surface mapping
