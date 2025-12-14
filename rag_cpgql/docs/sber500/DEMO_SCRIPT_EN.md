# CodeGraph: Demo Script for Sber500

## Format and Timing

| Parameter | Value |
|-----------|-------|
| **Total time** | 5 minutes |
| **Format** | Live demo with TUI interface |
| **Codebase** | PostgreSQL 17 (52K methods) |
| **LLM** | GigaChat-2-Pro |

---

## Demo Preparation

### Checklist Before Launch

```bash
# 1. Check environment variables
echo $GIGACHAT_AUTH_KEY

# 2. Check DuckDB CPG access
ls -la cpg.duckdb

# 3. Launch TUI
python -m src.tui.app
```

### Expected Launch Screen

```
+====================================================================+
|                      CodeGraph v1.0                                 |
|              AI Copilot for Source Code Analysis                    |
+====================================================================+
|  LLM: GigaChat-2-Pro                                                |
|  CPG: PostgreSQL 17 (52,482 methods)                                |
|  Vector DB: 250,000+ documents                                      |
|  Status: Ready                                                      |
+====================================================================+
```

---

## PART 1: Introduction (0:00 - 0:45)

### What to Say

> "Hello! I'll show you CodeGraph - an AI assistant for code analysis powered by GigaChat.
> Currently it's connected to the PostgreSQL 17 codebase - that's 52 thousand functions and over a million lines of C code.
> Let's see how GigaChat helps us understand and analyze this volume of code."

### Actions

1. Show TUI main screen
2. Point out connection statistics
3. Show scenario list with `/scenarios` command

```
> /scenarios

Available scenarios:
+----+------------------------+-------------------------------------+
| ID | Name                   | Description                         |
+----+------------------------+-------------------------------------+
| 01 | Onboarding            | Help for new developers             |
| 02 | Security Audit        | Vulnerability search                |
| 03 | Documentation         | Documentation generation            |
| 04 | Feature Development   | Help adding features                |
| 05 | Dead Code Detection   | Unused code search                  |
| ...| ...                   | (16 scenarios total)                |
+----+------------------------+-------------------------------------+
```

---

## PART 2: Security Audit (0:45 - 2:00)

### What to Say

> "The main use case for enterprise is vulnerability search.
> Let's select the Security Audit scenario and ask to find SQL injection."

### Actions

**Step 1: Select scenario**
```
> /select 02

OK Selected scenario: Security Audit
  Domain: postgresql
  Tags: SECURITY, VULNERABILITY, SQL_INJECTION
```

**Step 2: Ask question**
```
> Find SQL injection vulnerabilities

[GigaChat: Analyzing request...]
  +-- Intent: security-vulnerability-search
  +-- Entity: SQL injection
  +-- Scenario: CWE-89 detection

[Retrieval: Hybrid search...]
  +-- Vector: found 127 relevant fragments
  +-- Graph: found 43 potential points
  +-- RRF merge: 15 candidates

[GigaChat: Generating CPGQL query...]
  +-- Query: SELECT m.name, m.filename, m.line_number
            FROM nodes_method m
            WHERE m.id IN (SELECT src FROM edges_reaching_def...)

[Result]
+====================================================================+
|           REPORT: SQL Injection Vulnerabilities                     |
+====================================================================+
| CRITICAL (7):                                                       |
| +-- src/backend/parser/analyze.c:234                                |
| |   +-- Dynamic query construction without parameterization         |
| +-- src/pl/plpgsql/src/pl_exec.c:4567                              |
| |   +-- String interpolation in EXECUTE                            |
| +-- ... (5 more)                                                    |
|                                                                     |
| HIGH (12):                                                          |
| +-- contrib/dblink/dblink.c:891                                     |
| |   +-- External input passed to query builder                     |
| +-- ... (11 more)                                                   |
+====================================================================+
```

### Key Point

> "Notice: GigaChat does 4 things:
> 1. Understands we're looking for CWE-89 type vulnerabilities
> 2. Generates the correct query for the code graph
> 3. Finds specific files and lines
> 4. Groups by severity and explains the problem"

---

## PART 3: Data Flow Analysis (2:00 - 3:00)

### What to Say

> "Now let's trace how data reaches the vulnerable function.
> This is called taint analysis - tracking unsafe data flow."

### Actions

```
> Show data flow from user input to SQL execution in pl_exec.c

[GigaChat: Analyzing dataflow request...]
  +-- Source: user_input (tag: TAINT_SOURCE)
  +-- Sink: SQL execution (tag: QUERY_EXECUTION)
  +-- Target: pl_exec.c

[Graph Traversal: Taint propagation...]
  +-- Found 3 paths from source to sink

+====================================================================+
|                    DATA FLOW: Taint Analysis                        |
+====================================================================+
|                                                                     |
|  [SOURCE]                                                           |
|     |  PG_GETARG_TEXT_PP(0)  @ pl_exec.c:1234                      |
|     |  tag: TAINT_SOURCE, USER_INPUT                               |
|     v                                                               |
|  [TRANSFORMATION]                                                   |
|     |  text_to_cstring()  @ pl_exec.c:1240                         |
|     |  tag: STRING_CONVERSION                                      |
|     v                                                               |
|  [CONCATENATION]  WARNING: NO SANITIZATION                          |
|     |  sprintf(query, "SELECT * FROM %s", user_table)              |
|     |  @ pl_exec.c:1256                                            |
|     v                                                               |
|  [SINK]  CRITICAL VULNERABILITY                                     |
|     |  SPI_execute(query, ...)  @ pl_exec.c:1267                   |
|     |  tag: QUERY_EXECUTION, SQL_SINK                              |
|                                                                     |
|  RECOMMENDATION: Use SPI_execute_with_args()                        |
|                  with parameterized queries                         |
+====================================================================+
```

### Key Point

> "GigaChat + code graph = complete understanding of HOW data reaches the vulnerable spot.
> This is what usually takes hours of manual analysis, but here - seconds."

---

## PART 4: Code Review (3:00 - 4:00)

### What to Say

> "Now I'll show automatic code review.
> This can be integrated with GitHub/GitLab to check every PR."

### Actions

```
> /review git

[Analyzing changes in current commit...]

+====================================================================+
|                    CODE REVIEW REPORT                               |
+====================================================================+
|  Commit: a1b2c3d "Add user search functionality"                    |
|  Files changed: 3                                                   |
|  Lines: +127 / -12                                                  |
+====================================================================+
|                                                                     |
|  SECURITY SCORE: 72/100                                             |
|  ████████████████████░░░░░░░░                                       |
|                                                                     |
|  FINDINGS:                                                          |
|                                                                     |
|  CRITICAL (1):                                                      |
|     src/search.c:45 - Potential buffer overflow                     |
|     strcpy(dest, user_input) without bounds check                   |
|     FIX: Use strncpy or strlcpy                                     |
|                                                                     |
|  MEDIUM (2):                                                        |
|     src/search.c:67 - Missing NULL check                            |
|     src/utils.c:23 - Integer overflow possible                      |
|                                                                     |
|  RECOMMENDATION: REQUEST_CHANGES                                    |
|  "Fix critical buffer overflow before merge"                        |
+====================================================================+
```

### Key Point

> "72 out of 100 - this is below the threshold for automatic merge.
> GigaChat not only finds problems but also suggests specific fixes."

---

## PART 5: Onboarding (4:00 - 4:45)

### What to Say

> "Last scenario - onboarding. Imagine a new developer
> wants to understand how MVCC works in PostgreSQL."

### Actions

```
> /select 01
> How does MVCC work in PostgreSQL?

[GigaChat: Analyzing architectural question...]
  +-- Intent: architecture-explanation
  +-- Domain: PostgreSQL internals
  +-- Topic: MVCC (Multi-Version Concurrency Control)

+====================================================================+
|             MVCC in PostgreSQL: Architecture Overview               |
+====================================================================+
|                                                                     |
|  MVCC (Multi-Version Concurrency Control) - a mechanism             |
|  allowing multiple transactions to simultaneously read              |
|  and modify data without read locks.                                |
|                                                                     |
|  KEY COMPONENTS:                                                    |
|                                                                     |
|  1. Tuple Headers (src/include/access/htup_details.h)              |
|     +-- t_xmin: creating transaction ID                            |
|     +-- t_xmax: deleting transaction ID                            |
|     +-- t_ctid: physical location                                  |
|                                                                     |
|  2. Visibility Check (src/backend/access/heap/heapam.c)            |
|     +-- HeapTupleSatisfiesMVCC(): visibility check                 |
|     +-- XidInMVCCSnapshot(): snapshot check                        |
|                                                                     |
|  3. Snapshot (src/backend/utils/time/snapmgr.c)                    |
|     +-- GetTransactionSnapshot(): snapshot creation                |
|     +-- xmin/xmax: visible transaction boundaries                  |
|                                                                     |
|  CODE EXAMPLE:                                                      |
|  ```c                                                               |
|  // heapam.c:1847                                                   |
|  bool HeapTupleSatisfiesMVCC(HeapTuple htup, Snapshot snap) {      |
|      if (XidInMVCCSnapshot(HeapTupleHeaderGetXmin(tuple), snap))   |
|          return false;  // Transaction still active                 |
|      return true;                                                   |
|  }                                                                  |
|  ```                                                                |
|                                                                     |
|  RELATED FUNCTIONS:                                                 |
|  +-- heap_insert() - insertion with MVCC                           |
|  +-- heap_update() - update creates new version                    |
|  +-- heap_delete() - deletion marks t_xmax                         |
+====================================================================+

Would you like to learn more about any component?
```

### Key Point

> "Instead of reading documentation or asking colleagues,
> a new developer gets a structured answer with specific files and functions."

---

## PART 6: Conclusion (4:45 - 5:00)

### What to Say

> "So, in 5 minutes we saw:
> 1. Finding vulnerabilities in seconds instead of hours
> 2. Data flow analysis to understand vulnerability causes
> 3. Automatic code review with specific recommendations
> 4. Instant architecture immersion for new developers
>
> All of this runs on GigaChat, which understands context and generates
> meaningful answers in Russian language.
>
> Thank you! Ready to answer questions."

---

## Backup Scenarios

### If Time Remains - Show /query

```
> /query SELECT COUNT(*) as total_functions,
         AVG(cyclomatic_complexity) as avg_complexity
         FROM nodes_method WHERE cyclomatic_complexity > 10

+-----------------+----------------+
| total_functions | avg_complexity |
+-----------------+----------------+
|            2,847|           15.3 |
+-----------------+----------------+

> 2,847 functions with high complexity - this is technical debt
> worth prioritizing for refactoring.
```

### If Asked About Performance

```
> /stat

+====================================================================+
|                     SYSTEM STATISTICS                               |
+====================================================================+
|  CPG Database:                                                      |
|  +-- Methods: 52,482                                                |
|  +-- Calls: 111,847                                                 |
|  +-- Data flows: 89,234                                             |
|  +-- Semantic tags: 15,680,000                                      |
|                                                                     |
|  Vector Database:                                                   |
|  +-- Documents: 250,000+                                            |
|                                                                     |
|  Performance:                                                       |
|  +-- Avg query time: 2.3ms                                          |
|  +-- E2E response: < 5 sec                                          |
|  +-- GigaChat calls per query: 4-5                                  |
+====================================================================+
```

---

## FAQ for Demo

### Q: What languages are supported?
> A: Currently C/C++ (PostgreSQL, Linux Kernel, LLVM). Java and Python in roadmap for Q2 2025.

### Q: Can it be used locally?
> A: Yes, via Docker. Data doesn't leave company perimeter.

### Q: How long does codebase indexing take?
> A: PostgreSQL 17 (~1M lines) - about 30 minutes on standard hardware.

### Q: What is vulnerability detection accuracy?
> A: F1@10 = 0.383, which is 33% better than vector-only approaches.

### Q: How much does one query cost?
> A: ~1-2 RUB (4-5 GigaChat calls + infrastructure).

---

## Technical Requirements

### For Live Demo

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Storage | 10 GB | 50 GB |
| Network | Stable | Stable |
| GigaChat API | Active | Active |

### Backup Plan

If API is unavailable:
1. Show pre-recorded video (5 minutes)
2. Show result screenshots
3. Launch in offline mode with local model

---

## Checklist

- [ ] GigaChat API working
- [ ] DuckDB CPG loaded
- [ ] ChromaDB available
- [ ] TUI launches correctly
- [ ] Terminal in fullscreen mode
- [ ] Font readable (14-16pt)
- [ ] Colors contrasting
- [ ] Backup video ready
