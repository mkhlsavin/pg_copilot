# Scenario 14: Security Incident Response

> Security team investigating potential security incidents and vulnerabilities.

## Table of Contents

- [Quick Start](#quick-start)
- [Incident Investigation](#incident-investigation)
  - [CVE Impact Analysis](#cve-impact-analysis)
  - [Trace Exploitation Paths](#trace-exploitation-paths)
- [Remediation Analysis](#remediation-analysis)
  - [Find Similar Vulnerabilities](#find-similar-vulnerabilities)
  - [Patch Impact Assessment](#patch-impact-assessment)
- [Forensic Analysis](#forensic-analysis)
  - [Trace Affected Data](#trace-affected-data)
- [Incident Timeline](#incident-timeline)
  - [Generate Incident Report](#generate-incident-report)
- [Example Questions](#example-questions)
- [Related Scenarios](#related-scenarios)

## Quick Start

```bash
# Select Incident Response Scenario
/select 14
```

## Incident Investigation

### CVE Impact Analysis

```
> Trace the impact of CVE-2023-XXXX in parse_query

╭─────────────── CVE Impact Analysis ─────────────────────────╮
│                                                              │
│  CVE: CVE-2023-XXXX                                          │
│  Vulnerability: Buffer overflow in parse_query()             │
│  Severity: CRITICAL (CVSS 9.8)                               │
│                                                              │
│  Affected Function:                                          │
│    parse_query()                                             │
│    Location: src/backend/parser/parser.c:234                 │
│                                                              │
│  Attack Surface:                                             │
│    Entry Points: 3                                           │
│      - exec_simple_query() [Network accessible]              │
│      - exec_parse_message() [Prepared statements]            │
│      - SPI_execute() [Internal API]                          │
│                                                              │
│  Exploitation Path:                                          │
│    Client → pq_getmsgstring() → exec_simple_query()          │
│           → parse_query() [VULNERABLE]                       │
│                                                              │
│  Blast Radius:                                               │
│    Direct callers: 5                                         │
│    Transitive impact: 156 functions                          │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Trace Exploitation Paths

```
> Find all paths from network input to vulnerable function

╭─────────────── Exploitation Paths ──────────────────────────╮
│                                                              │
│  Paths from Network to Vulnerable Code:                      │
│                                                              │
│  Path 1 (Direct, 3 hops):                                    │
│    ProcessClientRead() → exec_simple_query()                 │
│                        → parse_query() ⚠️                    │
│                                                              │
│  Path 2 (Prepared statement, 4 hops):                        │
│    ProcessClientRead() → exec_parse_message()                │
│                        → pg_parse_query()                    │
│                        → parse_query() ⚠️                    │
│                                                              │
│  Path 3 (Extended protocol, 5 hops):                         │
│    ProcessClientRead() → exec_bind_message()                 │
│                        → PortalRun()                         │
│                        → pg_parse_query()                    │
│                        → parse_query() ⚠️                    │
│                                                              │
│  Total exploitable paths: 3                                  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Remediation Analysis

### Find Similar Vulnerabilities

```
> Find similar patterns that might have same vulnerability

╭─────────────── Pattern Analysis ────────────────────────────╮
│                                                              │
│  Searching for similar vulnerability patterns...             │
│                                                              │
│  Pattern: Unbounded string copy from network input           │
│                                                              │
│  Similar Locations Found:                                    │
│                                                              │
│  🔴 HIGH RISK (same pattern):                                │
│    src/backend/parser/gram.y:567                             │
│    src/backend/tcop/postgres.c:890                           │
│    src/backend/commands/copy.c:234                           │
│                                                              │
│  🟡 MEDIUM RISK (similar pattern):                           │
│    src/backend/replication/walsender.c:456                   │
│    src/backend/libpq/auth.c:789                              │
│                                                              │
│  Recommendation: Review all 5 locations for same fix         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Patch Impact Assessment

```
> Assess impact of proposed patch

╭─────────────── Patch Impact ────────────────────────────────╮
│                                                              │
│  Proposed Fix: Add bounds checking to parse_query()          │
│                                                              │
│  Patch Location:                                             │
│    File: src/backend/parser/parser.c                         │
│    Lines: 234-240                                            │
│                                                              │
│  Functional Impact:                                          │
│    - Query length now limited to MAX_QUERY_SIZE              │
│    - Error raised for oversized queries                      │
│                                                              │
│  Performance Impact:                                         │
│    - Additional strlen() call: ~0.1% overhead                │
│    - Memory savings: Prevents unbounded allocation           │
│                                                              │
│  Compatibility Impact:                                       │
│    - Queries > 1GB will now fail (was undefined behavior)    │
│    - No API changes                                          │
│                                                              │
│  Risk Level: LOW                                             │
│    - Defensive check only                                    │
│    - No behavioral change for valid inputs                   │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Forensic Analysis

### Trace Affected Data

```
> What data could have been accessed through this vulnerability?

╭─────────────── Data Access Analysis ────────────────────────╮
│                                                              │
│  Potential Data Exposure from Vulnerability:                 │
│                                                              │
│  Memory Regions Accessible:                                  │
│    ├── Query text buffer (direct access)                     │
│    ├── Connection state (adjacent memory)                    │
│    ├── Authentication tokens (same context)                  │
│    └── Other session data (stack frames)                     │
│                                                              │
│  Privilege Level:                                            │
│    - Runs as: postgres backend process                       │
│    - Can access: All database files                          │
│    - Cannot access: OS-level without escalation              │
│                                                              │
│  Worst Case Scenario:                                        │
│    - Full database read access                               │
│    - Potential code execution as postgres user               │
│                                                              │
│  Indicators of Compromise:                                   │
│    - Queries with unusual binary content                     │
│    - Unexpected memory allocation errors                     │
│    - Crash logs with parse_query in stack trace              │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Incident Timeline

### Generate Incident Report

```
> Generate incident response report

╭─────────────── Incident Report ─────────────────────────────╮
│                                                              │
│  SECURITY INCIDENT REPORT                                    │
│  Generated: 2024-12-20 14:30 UTC                             │
│                                                              │
│  Vulnerability Summary:                                      │
│    Type: Buffer Overflow (CWE-120)                           │
│    Severity: CRITICAL                                        │
│    Affected: parse_query() in parser.c                       │
│                                                              │
│  Timeline:                                                   │
│    Discovery: 2024-12-19 10:00 UTC                           │
│    Analysis: 2024-12-19 14:00 UTC                            │
│    Patch Ready: 2024-12-20 08:00 UTC                         │
│    Deployment: TBD                                           │
│                                                              │
│  Affected Systems:                                           │
│    - All PostgreSQL versions 14.x, 15.x, 16.x                │
│    - Extensions using SPI_execute                            │
│                                                              │
│  Remediation:                                                │
│    1. Apply patch to parse_query()                           │
│    2. Review similar patterns (5 locations)                  │
│    3. Update security documentation                          │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Trace the impact of [CVE] in [function]"
- "Find exploitation paths to [function]"
- "Find similar vulnerability patterns"
- "What data could be accessed through [vulnerability]?"
- "Assess impact of patch to [function]"
- "Generate incident report"

## Related Scenarios

- [Security Audit](./02-security-audit.md) - Proactive security analysis
- [Entry Points](./16-entry-points.md) - Attack surface mapping
- [Code Review](./09-code-review.md) - Review security patches
