# CodeGraph User Guide

> Comprehensive documentation for code analysis using Code Property Graphs

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Developer Scenarios](#developer-scenarios)
3. [QA/Tester Scenarios](#qatester-scenarios)
4. [Security Specialist Scenarios](#security-specialist-scenarios)
   - [D3FEND Source Code Hardening](#d3fend-source-code-hardening)
5. [Technical Writer Scenarios](#technical-writer-scenarios)
6. [TUI Command Reference](#tui-command-reference)
7. [Configuration Guide](#configuration-guide)
8. [Appendix: All 16 Scenarios](#appendix-all-16-scenarios)
9. [Security Audit Reports (CLI)](#security-audit-reports-cli)
10. [Common Workflows](#common-workflows)
11. [Themes](#themes)
12. [Sessions](#sessions)
13. [Tips & Tricks](#tips--tricks)
14. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# Clone and install dependencies
cd codegraph
pip install -r requirements.txt

# Set up API credentials (choose one)
export GIGACHAT_AUTH_KEY="your-key-here"    # GigaChat (Sber)
# OR
export OPENAI_API_KEY="your-key-here"        # OpenAI
```

### Launch the TUI

```bash
python -m src.tui.app
```

### Your First Query

```
╭─────────────────────────────────────────────────────────╮
│  CodeGraph Interactive Console                          │
│  Type /help for commands, /exit to quit                 │
╰─────────────────────────────────────────────────────────╯

> Where is the function heap_insert defined?

╭─────────────── Answer ────────────────╮
│ heap_insert is defined in:            │
│   src/backend/access/heap/heapam.c    │
│   Line: 2156                          │
│                                       │
│ Signature:                            │
│   void heap_insert(Relation relation, │
│                    HeapTuple tup,     │
│                    CommandId cid,     │
│                    ...)               │
╰───────────────────────────────────────╯
```

### Essential Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/scenarios` | List 16 analysis scenarios |
| `/select 02` | Switch to Security Audit mode |
| `/project` | Switch between CPG projects |
| `/review git` | Review current code changes |
| `/stat` | Show database statistics |
| `/exit` | Save session and exit |

---

## Developer Scenarios

### Day 1: Codebase Onboarding

**Scenario:** New developer joins the team, needs to understand codebase structure quickly.

#### Step 1: Select Onboarding Scenario

```
/select 01
```

#### Step 2: Ask Overview Questions

```
> What is the executor subsystem?

╭─────────────── Answer ────────────────╮
│ The executor subsystem is responsible │
│ for executing query plans generated   │
│ by the planner.                       │
│                                       │
│ Key components:                       │
│   - ExecutorStart: Initialize state   │
│   - ExecutorRun: Main execution loop  │
│   - ExecutorEnd: Cleanup resources    │
│                                       │
│ Entry point: src/backend/executor/    │
│              execMain.c               │
╰───────────────────────────────────────╯

> What are the main entry points in the executor?

> Show me the architecture of query execution
```

#### Step 3: Dive into Specifics

```
> What does ExecProcNode do?
> Who calls ExecutorRun?
> Explain the relationship between Plan and PlanState
```

#### Real-World Example: Understanding Memory Management

```
> How does memory allocation work in PostgreSQL?

╭─────────────── Answer ────────────────╮
│ PostgreSQL uses memory contexts for   │
│ hierarchical memory management:       │
│                                       │
│ Key functions:                        │
│   palloc()  - Allocate memory         │
│   pfree()   - Free memory             │
│   MemoryContextCreate() - New context │
│   MemoryContextReset()  - Bulk free   │
│                                       │
│ Main contexts:                        │
│   TopMemoryContext - Root context     │
│   CurrentMemoryContext - Active ctx   │
│   MessageContext - Per-message        │
╰───────────────────────────────────────╯
```

---

### Finding Function Definitions

**Scenario:** Developer needs to locate function implementations.

#### Quick Definition Search

```
> Where is palloc defined?

╭─────────────── Answer ────────────────╮
│ palloc is defined in:                 │
│   src/backend/utils/mmgr/mcxt.c:1089  │
│                                       │
│ Signature:                            │
│   void *palloc(Size size)             │
│                                       │
│ Related functions:                    │
│   palloc0(), palloc_extended(),       │
│   repalloc(), pfree()                 │
╰───────────────────────────────────────╯
```

#### With Call Graph

```
> Show me all callers of palloc

╭─────────────── Callers ───────────────╮
│ 1. heap_form_tuple()                  │
│ 2. ExecStoreTuple()                   │
│ 3. construct_array()                  │
│ 4. pnstrdup()                         │
│ 5. SPI_connect()                      │
│ ... (showing top 5 of 2,847 callers)  │
╰───────────────────────────────────────╯

> What functions does LWLockAcquire call?
```

#### Trace Data Flow

```
> How does data flow from pg_parse_query to executor?

╭─────────────── Data Flow ─────────────╮
│ pg_parse_query()                      │
│     ↓                                 │
│ pg_analyze_and_rewrite()              │
│     ↓                                 │
│ pg_plan_queries()                     │
│     ↓                                 │
│ PortalRun()                           │
│     ↓                                 │
│ ExecutorRun()                         │
│     ↓                                 │
│ ExecProcNode()                        │
╰───────────────────────────────────────╯
```

---

### Adding New Features

**Scenario:** Developer needs to add a new join algorithm.

#### Step 1: Select Feature Development Scenario

```
/select 04
```

#### Step 2: Find Integration Points

```
> Where should I add a new join algorithm?

╭─────────────── Answer ────────────────╮
│ To add a new join algorithm:          │
│                                       │
│ 1. Define node type:                  │
│    src/include/nodes/plannodes.h      │
│                                       │
│ 2. Add planner support:               │
│    src/backend/optimizer/path/        │
│    joinpath.c - add_xxx_path()        │
│                                       │
│ 3. Add executor support:              │
│    src/backend/executor/              │
│    nodeXxxjoin.c - ExecXxxJoin()      │
│                                       │
│ 4. Register in execProcnode.c         │
╰───────────────────────────────────────╯

> What hooks exist in the executor for custom plan nodes?

> Show me how hashjoin integrates with the planner
```

#### Step 3: Understand Impact

```
> What would break if I modify add_path?

╭─────────────── Impact Analysis ───────╮
│ Modifying add_path() affects:         │
│                                       │
│ Direct callers (47):                  │
│   - add_partial_path()                │
│   - add_partial_path_precheck()       │
│   - create_seqscan_path()             │
│   - create_index_path()               │
│   ...                                 │
│                                       │
│ Risk: HIGH - Core path selection      │
│ Recommendation: Add new function      │
│ instead of modifying existing         │
╰───────────────────────────────────────╯

> Show dependencies of create_hashjoin_path
```

---

### Debugging Assistance

**Scenario:** Developer debugging a crash or unexpected behavior.

#### Step 1: Select Debugging Scenario

```
/select 15
```

#### Step 2: Find Debug Points

```
> Where are assertion macros in the executor?

╭─────────────── Answer ────────────────╮
│ Assertion macros in executor:         │
│                                       │
│ Assert() - src/include/c.h:846        │
│ AssertArg() - Argument validation     │
│ AssertState() - State validation      │
│                                       │
│ Usage in executor:                    │
│   execMain.c: 89 assertions           │
│   execProcnode.c: 34 assertions       │
│   execScan.c: 23 assertions           │
╰───────────────────────────────────────╯

> Find elog calls in heap_insert

> What functions log to WAL?
```

#### Step 3: Trace Execution

```
> Trace execution from INSERT to heap_insert

╭─────────────── Execution Trace ───────╮
│ ProcessQuery()                        │
│   ↓                                   │
│ PortalRunMulti()                      │
│   ↓                                   │
│ ExecutorRun()                         │
│   ↓                                   │
│ ExecModifyTable()                     │
│   ↓                                   │
│ ExecInsert()                          │
│   ↓                                   │
│ table_tuple_insert()                  │
│   ↓                                   │
│ heap_insert()                         │
╰───────────────────────────────────────╯

> Where to set breakpoints for transaction commit?
```

---

### Refactoring Code

**Scenario:** Developer cleaning up technical debt during refactoring sprint.

#### Step 1: Select Refactoring Scenario

```
/select 05
```

#### Step 2: Find Dead Code

```
> Find unused static functions in executor

╭─────────────── Dead Code ─────────────╮
│ Potentially unused static functions:  │
│                                       │
│ 1. execUtils.c:                       │
│    - old_get_typlenbyval() :234       │
│                                       │
│ 2. execTuples.c:                      │
│    - legacy_slot_init() :456          │
│                                       │
│ Total: 12 candidates                  │
│ Verified unused: 8                    │
╰───────────────────────────────────────╯

> Show deprecated functions still in use

> Find duplicate error handling patterns
```

#### Step 3: Plan Refactoring

```
> What depends on ExecProcNode?

╭─────────────── Dependencies ──────────╮
│ Direct dependents: 47                 │
│ Transitive dependents: 312            │
│                                       │
│ Key callers:                          │
│   - ExecutorRun()                     │
│   - ExecSubPlan()                     │
│   - ExecMaterial()                    │
│   - ExecSort()                        │
│                                       │
│ Refactoring risk: CRITICAL            │
│ Recommendation: Staged migration      │
╰───────────────────────────────────────╯

> Impact of renaming heap_open to table_open
```

---

## QA/Tester Scenarios

### Test Coverage Analysis

**Scenario:** QA engineer needs to identify untested code paths.

#### Step 1: Select Test Coverage Scenario

```
/select 07
```

#### Step 2: Find Coverage Gaps

```
> What functions lack test coverage?

╭─────────────── Coverage Gaps ─────────╮
│ Functions without direct tests:       │
│                                       │
│ Critical (executor):                  │
│   - ExecParallelHashJoinNewBatch()    │
│   - ExecReScanGather()                │
│                                       │
│ High priority (storage):              │
│   - heap_lock_updated_tuple()         │
│   - heap_abort_speculative()          │
│                                       │
│ Total untested: 234 functions         │
│ Coverage estimate: 78%                │
╰───────────────────────────────────────╯

> Which critical functions need tests first?

> Find untested error handling paths
```

#### Step 3: Prioritize Testing

```
> Which untested functions have highest impact?

╭─────────────── Priority List ─────────╮
│ High Impact + No Tests:               │
│                                       │
│ 1. heap_lock_updated_tuple()          │
│    Impact: Transaction integrity      │
│    Callers: 23                        │
│                                       │
│ 2. ExecParallelHashJoinNewBatch()     │
│    Impact: Parallel query correctness │
│    Callers: 8                         │
│                                       │
│ 3. AtEOXact_RelationCache()           │
│    Impact: Cache consistency          │
│    Callers: 4                         │
╰───────────────────────────────────────╯

> Show entry points without tests
```

---

### Code Review Assistance

**Scenario:** Reviewer needs to analyze a pull request for quality and security issues.

#### Option A: GitHub PR

```
/review github 123
```

#### Option B: GitLab MR

```
/review gitlab 456
```

#### Option C: Local Git Changes

```
/review git
```

#### Option D: Patch File

```
/review file path/to/changes.patch
```

#### Understanding Output

```
╭─────────────── Review Results ────────────────────────────╮
│                                                           │
│  Score: 72/100         Recommendation: REQUEST_CHANGES    │
│                                                           │
│  ══════════════════════════════════════════════════════   │
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

#### Review with Inline Comments

```
/review git --format md --inline

╭─────────────── Inline Comments ───────────────────────────╮
│                                                           │
│  src/api/user_query.c                                     │
│  ─────────────────────                                    │
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

---

### Generating Test Cases

**Scenario:** QA needs to create comprehensive tests for a function.

```
> Generate test cases for heap_insert

╭─────────────── Test Cases ────────────────────────────────╮
│                                                           │
│ Function: heap_insert()                                   │
│ File: src/backend/access/heap/heapam.c:2156               │
│                                                           │
│ ═══════════════════════════════════════════════════════   │
│                                                           │
│ 1. Normal Insertion                                       │
│    Input: Valid relation, valid tuple, valid CommandId    │
│    Expected: OID returned, tuple visible                  │
│                                                           │
│ 2. NULL Relation                                          │
│    Input: NULL relation pointer                           │
│    Expected: Assert failure or graceful error             │
│                                                           │
│ 3. Oversized Tuple                                        │
│    Input: Tuple larger than BLCKSZ                        │
│    Expected: ERROR with clear message                     │
│                                                           │
│ 4. Concurrent Insert                                      │
│    Input: Multiple threads inserting                      │
│    Expected: All inserts succeed, no corruption           │
│                                                           │
│ 5. Transaction Rollback                                   │
│    Input: Insert followed by ROLLBACK                     │
│    Expected: Tuple not visible after rollback             │
│                                                           │
│ 6. TOAST Required                                         │
│    Input: Tuple with large varlena field                  │
│    Expected: TOAST table populated correctly              │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> What edge cases should I test in LWLockAcquire?

> Create test data for transaction commit scenarios
```

---

## Security Specialist Scenarios

### Vulnerability Scanning

**Scenario:** Security engineer performing audit sprint.

#### Step 1: Select Security Scenario

```
/select 02
```

#### Step 2: Scan for Vulnerabilities

```
> Find SQL injection vulnerabilities

╭─────────────── Security Findings ─────────────────────────╮
│                                                           │
│  🔴 CRITICAL: SQL Injection                               │
│     ────────────────────────                              │
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
│  ────────────────────────────────────────────────────     │
│                                                           │
│     Location: src/backend/utils/adt/ruleutils.c:2341      │
│     Pattern: Format string with external input            │
│     Risk: Potential format string injection               │
│     Fix: Validate format specifiers                       │
│                                                           │
│  Total findings: 7 critical, 12 high, 34 medium           │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Find buffer overflow risks in string functions

> Show functions using sprintf without bounds
```

---

### Taint Flow Analysis

**Scenario:** Security engineer tracing untrusted data through the system.

#### Step 1: Identify Entry Points

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

> Show network input handlers

> List user input functions
```

#### Step 2: Trace Data Flow

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
│  ════════════════════════════════════════════════════     │
│                                                           │
│  Sanitization found: YES                                  │
│  Location: pg_parse_query() validates syntax              │
│  BUT: Does not prevent semantic injection                 │
│                                                           │
│  Risk Level: HIGH                                         │
│  Recommendation: Add input validation at entry point      │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Does user input reach strcpy without validation?

> Show path from socket read to memory allocation
```

#### Step 3: Find Sanitization

```
> Where is input sanitized before query execution?

╭─────────────── Sanitization Points ───────────────────────╮
│                                                           │
│  Identified sanitizers:                                   │
│                                                           │
│  1. quote_identifier()                                    │
│     Location: src/backend/utils/adt/ruleutils.c:10234     │
│     Purpose: Escape SQL identifiers                       │
│     Coverage: Partial - not always used                   │
│                                                           │
│  2. quote_literal()                                       │
│     Location: src/backend/utils/adt/quote.c:45            │
│     Purpose: Escape SQL literals                          │
│     Coverage: Good - widely used                          │
│                                                           │
│  3. pg_parse_query()                                      │
│     Location: src/backend/tcop/postgres.c:645             │
│     Purpose: Syntax validation                            │
│     Coverage: All queries                                 │
│                                                           │
│  Missing sanitization at:                                 │
│    - Dynamic table name construction (12 locations)       │
│    - Format string building (5 locations)                 │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Find all validation functions in authentication
```

---

### D3FEND Source Code Hardening

**Scenario:** Security engineer checking defensive coding practices using MITRE D3FEND framework.

The D3FEND module analyzes code for 11 Source Code Hardening techniques defined by MITRE:

| ID | Technique | Description | CWE |
|----|-----------|-------------|-----|
| D3-VI | Variable Initialization | Uninitialized variables | CWE-457 |
| D3-CS | Credential Scrubbing | Hardcoded credentials | CWE-798 |
| D3-IRV | Integer Range Validation | Integer overflow risks | CWE-190 |
| D3-PV | Pointer Validation | Pointer dereference without check | CWE-476 |
| D3-RN | Reference Nullification | Use-after-free risks | CWE-416 |
| D3-TL | Trusted Library | Unsafe function usage | CWE-676 |
| D3-VTV | Variable Type Validation | Type confusion | CWE-704 |
| D3-MBSV | Memory Block Start Validation | Buffer bounds | CWE-119 |
| D3-NPC | Null Pointer Checking | Missing NULL checks | CWE-476 |
| D3-DLV | Domain Logic Validation | Business logic errors | CWE-20 |
| D3-OLV | Operational Logic Validation | State management | CWE-754 |

#### Use Case 1: Full Hardening Audit

```
/select 02

> Run D3FEND hardening compliance check

╭─────────────── D3FEND Compliance Report ─────────────────────╮
│                                                               │
│  Overall Compliance Score: 72.5%                              │
│                                                               │
│  ═══════════════════════════════════════════════════════════  │
│                                                               │
│  Findings by Technique:                                       │
│                                                               │
│  D3-VI (Variable Initialization): 23 issues                   │
│  ───────────────────────────────────────                      │
│    - palloc without palloc0: 15 locations                     │
│    - Uninitialized struct members: 8 locations                │
│                                                               │
│  D3-TL (Trusted Library): 12 issues                           │
│  ────────────────────────────────────                         │
│    🔴 strcpy usage: src/backend/utils/adt/varlena.c:234       │
│    🔴 sprintf usage: src/backend/libpq/auth.c:567             │
│    🟡 strtok usage: src/backend/parser/gram.c:1234            │
│                                                               │
│  D3-NPC (Null Pointer Checking): 8 issues                     │
│  ─────────────────────────────────────────                    │
│    - malloc without NULL check: 5 locations                   │
│    - palloc without assertion: 3 locations                    │
│                                                               │
│  D3-RN (Reference Nullification): 6 issues                    │
│  ──────────────────────────────────────────                   │
│    - pfree without ptr = NULL: 6 locations                    │
│                                                               │
│  Category Scores:                                             │
│    Initialization: 65%                                        │
│    Memory Safety: 78%                                         │
│    Pointer Safety: 82%                                        │
│    Library Safety: 58%                                        │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 2: Check Specific D3FEND Techniques

```
> Check for unsafe function usage (D3-TL Trusted Library)

╭─────────────── D3-TL: Trusted Library ───────────────────────╮
│                                                               │
│  Unsafe Functions Found: 47                                   │
│                                                               │
│  🔴 CRITICAL - strcpy (buffer overflow risk):                 │
│  ─────────────────────────────────────────────                │
│    src/backend/utils/adt/varlena.c:234                        │
│    src/backend/libpq/pqformat.c:567                           │
│    src/pl/plpgsql/src/pl_exec.c:1234                          │
│                                                               │
│  🔴 CRITICAL - sprintf (format string risk):                  │
│  ─────────────────────────────────────────────                │
│    src/backend/libpq/auth.c:567                               │
│    src/backend/utils/error/elog.c:890                         │
│                                                               │
│  🟡 HIGH - gets (deprecated, always unsafe):                  │
│  ─────────────────────────────────────────────                │
│    None found ✓                                               │
│                                                               │
│  🟡 HIGH - rand (weak random number generator):               │
│  ─────────────────────────────────────────────                │
│    src/backend/utils/misc/pg_random.c:45                      │
│                                                               │
│  Remediation:                                                 │
│  ────────────                                                 │
│    - strcpy → strncpy/strlcpy                                 │
│    - sprintf → snprintf                                       │
│    - gets → fgets                                             │
│    - rand → pg_prng_* or arc4random                           │
│                                                               │
╰───────────────────────────────────────────────────────────────╯

> Find null pointer vulnerabilities (D3-NPC)

╭─────────────── D3-NPC: Null Pointer Checking ────────────────╮
│                                                               │
│  Missing NULL Checks After Allocation: 23                     │
│                                                               │
│  malloc without check:                                        │
│  ─────────────────────                                        │
│    src/backend/utils/mmgr/aset.c:345                          │
│      char *buf = malloc(size);                                │
│      use(buf);  // ← No NULL check!                           │
│                                                               │
│  palloc without assertion:                                    │
│  ──────────────────────────                                   │
│    src/backend/executor/execUtils.c:234                       │
│      TupleTableSlot *slot = palloc(sizeof(...));              │
│      slot->tts_values = palloc(...);  // ← No check           │
│                                                               │
│  PostgreSQL Note: palloc() raises ERROR on OOM,               │
│  but explicit checks improve code clarity.                    │
│                                                               │
│  Example Fix:                                                 │
│  ────────────                                                 │
│    char *buf = malloc(size);                                  │
│    if (buf == NULL) {                                         │
│        ereport(ERROR, (errcode(ERRCODE_OUT_OF_MEMORY)));      │
│    }                                                          │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 3: Check Memory Safety (D3-RN Reference Nullification)

```
> Check for use-after-free risks

╭─────────────── D3-RN: Reference Nullification ───────────────╮
│                                                               │
│  Free Without Nullification: 34 locations                     │
│                                                               │
│  pfree without NULL assignment:                               │
│  ──────────────────────────────                               │
│                                                               │
│    src/backend/utils/cache/relcache.c:567                     │
│    ─────────────────────────────────────                      │
│      pfree(rel->rd_options);                                  │
│      // rel->rd_options still points to freed memory!         │
│                                                               │
│      ✓ FIX:                                                   │
│      pfree(rel->rd_options);                                  │
│      rel->rd_options = NULL;                                  │
│                                                               │
│    src/backend/executor/nodeHash.c:234                        │
│    ─────────────────────────────────                          │
│      pfree(hashtable->buckets);                               │
│      // Dangling pointer risk in error paths                  │
│                                                               │
│  MemoryContextDelete without nullification:                   │
│  ──────────────────────────────────────────                   │
│                                                               │
│    src/backend/utils/mmgr/mcxt.c:890                          │
│      MemoryContextDelete(ctx);                                │
│      // ctx may be accessed later!                            │
│                                                               │
│  CWE Reference: CWE-416 (Use After Free)                      │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 4: Check Variable Initialization (D3-VI)

```
> Find uninitialized variables

╭─────────────── D3-VI: Variable Initialization ───────────────╮
│                                                               │
│  Uninitialized Variables Found: 56                            │
│                                                               │
│  Stack variables without initialization:                      │
│  ─────────────────────────────────────────                    │
│                                                               │
│    src/backend/executor/execMain.c:456                        │
│    ─────────────────────────────────────                      │
│      EState *estate;        // ← Uninitialized                │
│      QueryDesc *queryDesc;  // ← Uninitialized                │
│                                                               │
│      ✓ FIX:                                                   │
│      EState *estate = NULL;                                   │
│      QueryDesc *queryDesc = NULL;                             │
│                                                               │
│  palloc without palloc0:                                      │
│  ───────────────────────                                      │
│                                                               │
│    src/backend/nodes/copyfuncs.c:234                          │
│    ─────────────────────────────────                          │
│      Node *newnode = palloc(sizeof(Node));                    │
│      // Fields may contain garbage!                           │
│                                                               │
│      ✓ FIX:                                                   │
│      Node *newnode = palloc0(sizeof(Node));                   │
│                                                               │
│  Struct without memset:                                       │
│  ──────────────────────                                       │
│                                                               │
│    struct MyStruct s;       // ← Uninitialized fields         │
│    ✓ FIX:                                                     │
│    struct MyStruct s = {0}; // Zero-initialize                │
│                                                               │
│  CWE Reference: CWE-457 (Use of Uninitialized Variable)       │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 5: Credential Scrubbing (D3-CS)

```
> Find hardcoded credentials

╭─────────────── D3-CS: Credential Scrubbing ──────────────────╮
│                                                               │
│  🔴 CRITICAL: Hardcoded Credentials Found                     │
│                                                               │
│  Password literals:                                           │
│  ─────────────────                                            │
│                                                               │
│    src/backend/libpq/auth.c:123                               │
│    ─────────────────────────────                              │
│      char *default_password = "postgres123";                  │
│      //    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                  │
│      // NEVER hardcode passwords!                             │
│                                                               │
│  API Key patterns:                                            │
│  ────────────────                                             │
│                                                               │
│    src/contrib/postgres_fdw/connection.c:456                  │
│    ──────────────────────────────────────────                 │
│      #define AWS_SECRET_KEY "AKIAIOSFODNN7EXAMPLE"            │
│      // Exposed credential in source code!                    │
│                                                               │
│  Token patterns:                                              │
│  ───────────────                                              │
│    None found ✓                                               │
│                                                               │
│  Remediation:                                                 │
│  ────────────                                                 │
│    - Use environment variables: getenv("DB_PASSWORD")         │
│    - Use secure credential stores                             │
│    - Use .pgpass file for PostgreSQL                          │
│    - Implement credential rotation                            │
│                                                               │
│  CWE Reference: CWE-798 (Use of Hard-coded Credentials)       │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 6: Integer Range Validation (D3-IRV)

```
> Check for integer overflow risks

╭─────────────── D3-IRV: Integer Range Validation ─────────────╮
│                                                               │
│  Integer Overflow Risks: 18                                   │
│                                                               │
│  Allocation size calculation without check:                   │
│  ──────────────────────────────────────────                   │
│                                                               │
│    src/backend/utils/palloc.c:234                             │
│    ───────────────────────────────                            │
│      size_t size = count * sizeof(int);  // May overflow!     │
│      ptr = palloc(size);                                      │
│                                                               │
│      ✓ FIX (PostgreSQL style):                                │
│      if (count > SIZE_MAX / sizeof(int))                      │
│          ereport(ERROR, ...);                                 │
│      ptr = palloc(count * sizeof(int));                       │
│                                                               │
│      ✓ FIX (with overflow check macro):                       │
│      if (pg_mul_s64_overflow(count, sizeof(int), &size))      │
│          ereport(ERROR, ...);                                 │
│      ptr = palloc(size);                                      │
│                                                               │
│  Array index calculation:                                     │
│  ────────────────────────                                     │
│                                                               │
│    src/backend/access/heap/heapam.c:567                       │
│    ────────────────────────────────────                       │
│      int offset = base + delta;  // May wrap around!          │
│      array[offset] = value;                                   │
│                                                               │
│  CWE Reference: CWE-190 (Integer Overflow)                    │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 7: Domain-Specific Checks (PostgreSQL)

```
> Run PostgreSQL-specific hardening checks

╭─────────────── PostgreSQL Hardening Report ──────────────────╮
│                                                               │
│  PostgreSQL-Specific D3FEND Findings                          │
│                                                               │
│  D3-VI-PG: palloc vs palloc0                                  │
│  ─────────────────────────────                                │
│    palloc without initialization: 45 locations                │
│    Recommendation: Use palloc0() for structs                  │
│                                                               │
│  D3-TL-PG: Standard C vs PostgreSQL functions                 │
│  ─────────────────────────────────────────────                │
│    malloc usage (should use palloc): 12 locations             │
│    free usage (should use pfree): 8 locations                 │
│    strdup usage (should use pstrdup): 5 locations             │
│                                                               │
│  D3-DLV-PG: OID Validation                                    │
│  ─────────────────────────────                                │
│    SearchSysCache without OidIsValid: 7 locations             │
│    GetSysCacheOid without check: 3 locations                  │
│                                                               │
│  D3-OLV-PG: SPI State Management                              │
│  ───────────────────────────────                              │
│    SPI_execute without SPI_connect: 2 locations               │
│    Missing SPI_finish in error paths: 4 locations             │
│                                                               │
│  PostgreSQL Best Practices:                                   │
│  ──────────────────────────                                   │
│    ✓ Use palloc/pfree instead of malloc/free                  │
│    ✓ Use palloc0 for struct initialization                    │
│    ✓ Always check OidIsValid() before cache lookups           │
│    ✓ Use HeapTupleIsValid() after SearchSysCache              │
│    ✓ Balance SPI_connect/SPI_finish in all paths              │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Use Case 8: Generate Compliance Report

```
> Generate D3FEND compliance report for audit

╭─────────────── D3FEND Compliance Audit Report ───────────────╮
│                                                               │
│  MITRE D3FEND Source Code Hardening Compliance                │
│  ═══════════════════════════════════════════                  │
│                                                               │
│  Audit Date: 2024-12-09                                       │
│  Target: PostgreSQL 16.1 (src/backend/*)                      │
│  Language: C                                                  │
│                                                               │
│  EXECUTIVE SUMMARY                                            │
│  ─────────────────                                            │
│  Overall Compliance Score: 72.5%                              │
│  Total Findings: 156                                          │
│    - Critical: 12                                             │
│    - High: 34                                                 │
│    - Medium: 67                                               │
│    - Low: 43                                                  │
│                                                               │
│  TECHNIQUE COMPLIANCE                                         │
│  ─────────────────────                                        │
│                                                               │
│  D3-VI  Variable Initialization     ████████░░  78%           │
│  D3-CS  Credential Scrubbing        ██████████  95%           │
│  D3-IRV Integer Range Validation    ███████░░░  68%           │
│  D3-PV  Pointer Validation          ████████░░  82%           │
│  D3-RN  Reference Nullification     ██████░░░░  62%           │
│  D3-TL  Trusted Library             █████░░░░░  58%           │
│  D3-VTV Variable Type Validation    ████████░░  85%           │
│  D3-MBSV Memory Block Validation    ███████░░░  72%           │
│  D3-NPC Null Pointer Checking       ████████░░  80%           │
│  D3-DLV Domain Logic Validation     ███████░░░  75%           │
│  D3-OLV Operational Logic Valid.    ██████░░░░  65%           │
│                                                               │
│  TOP PRIORITY REMEDIATION                                     │
│  ────────────────────────                                     │
│  1. Replace unsafe string functions (D3-TL)                   │
│  2. Add NULL checks after allocations (D3-NPC)                │
│  3. Nullify pointers after free (D3-RN)                       │
│  4. Add overflow checks in size calculations (D3-IRV)         │
│                                                               │
│  Full report saved to: d3fend_audit_2024-12-09.md             │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

#### Programmatic API Usage

For automation and CI/CD integration:

```python
from src.security.hardening import HardeningScanner, HardeningCategory
from src.services.cpg_query_service import CPGQueryService

# Initialize scanner
with CPGQueryService() as cpg:
    scanner = HardeningScanner(cpg, language="c")

    # Run all checks
    findings = scanner.scan_all(limit_per_check=50)

    # Or run specific D3FEND techniques
    findings = scanner.scan_by_d3fend_id(
        ["D3-VI", "D3-NPC", "D3-TL"],
        limit=30
    )

    # Or run by category
    findings = scanner.scan_by_category(
        HardeningCategory.MEMORY_SAFETY,
        limit=20
    )

    # Get compliance scores
    scores = scanner.get_compliance_score(findings)
    print(f"Overall Score: {scores['overall_score']}%")
    print(f"By D3FEND: {scores['d3fend_scores']}")

    # Generate remediation report
    report = scanner.get_remediation_report(findings)
    with open("hardening_report.md", "w") as f:
        f.write(report)
```

---

### Compliance Checking

**Scenario:** Auditor checking codebase for regulatory compliance.

#### Step 1: Select Compliance Scenario

```
/select 08
```

#### Step 2: Check Standards

```
> Check for OWASP Top 10 vulnerabilities

╭─────────────── OWASP Top 10 Audit ────────────────────────╮
│                                                           │
│  A01:2021 - Broken Access Control                         │
│  ─────────────────────────────────                        │
│  Status: 3 findings                                       │
│    - Missing ACL check in pg_ls_dir()                     │
│    - Privilege escalation in ALTER ROLE                   │
│                                                           │
│  A02:2021 - Cryptographic Failures                        │
│  ─────────────────────────────────                        │
│  Status: PASS                                             │
│    - Using OpenSSL for encryption                         │
│    - scram-sha-256 for authentication                     │
│                                                           │
│  A03:2021 - Injection                                     │
│  ────────────────────────                                 │
│  Status: 7 findings                                       │
│    - See SQL injection report above                       │
│                                                           │
│  A04:2021 - Insecure Design                               │
│  ──────────────────────────                               │
│  Status: 2 findings                                       │
│    - Default superuser without password                   │
│                                                           │
│  Overall Score: 72/100                                    │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Find hardcoded credentials

> Generate compliance report for CWE-89
```

---

### Python/Django Security Audit

**Scenario:** Security engineer auditing a Django web application.

When analyzing Python/Django projects, the copilot uses specialized security patterns for web vulnerabilities:

#### Supported Vulnerabilities

| ID | Vulnerability | CWE | Indicators |
|----|--------------|-----|------------|
| DJANGO_SQL_INJECTION | SQL Injection via Raw Query | CWE-89 | `raw()`, `extra()`, `RawSQL()`, `cursor.execute()` |
| DJANGO_XSS | Cross-Site Scripting | CWE-79 | `mark_safe()`, `\|safe`, `autoescape off` |
| DJANGO_CSRF | CSRF Vulnerability | CWE-352 | `@csrf_exempt` |
| DJANGO_AUTH_BYPASS | Authentication Bypass | CWE-287 | `@permission_classes([])`, `AllowAny` |
| DJANGO_INSECURE_DESERIALIZE | Insecure Deserialization | CWE-502 | `pickle.loads`, `yaml.load`, `eval()` |
| DJANGO_PATH_TRAVERSAL | Path Traversal | CWE-22 | `open()`, `os.path.join()` with user input |
| DJANGO_CMD_INJECTION | Command Injection | CWE-78 | `subprocess.*`, `os.system()`, `shell=True` |
| DJANGO_MASS_ASSIGNMENT | Mass Assignment | CWE-915 | `**request.data`, `update(**kwargs)` |

#### Example Queries

```
# Switch to Django project first
/project switch fsin_module

# Then select Security Audit scenario
/select 02

# Ask security questions
> Find SQL injection vulnerabilities in views
> Check for XSS in templates
> Find endpoints without CSRF protection
> Show functions using eval() or exec()
```

#### Taint Sources (User Input)

The system tracks data flow from these Django sources:
- `request.GET.get()`, `request.POST.get()`, `request.data.get()`
- `request.body`, `request.path`, `request.FILES`
- `form.cleaned_data`, `serializer.validated_data`
- URL parameters (`kwargs.get()`)

#### Taint Sinks (Dangerous Functions)

Data reaching these sinks is flagged:
- **SQL**: `raw()`, `extra()`, `execute()`, `RawSQL()`
- **XSS**: `mark_safe()`, `HttpResponse()`
- **Command**: `subprocess.*`, `os.system()`, `os.popen()`
- **File**: `open()`, `FileResponse()`
- **Deserialize**: `pickle.loads()`, `yaml.load()`, `eval()`, `exec()`

---

### Incident Response

**Scenario:** Security team investigating a breach.

#### Step 1: Select Incident Scenario

```
/select 14
```

#### Step 2: Trace Attack Path

```
> Trace attack vector from login to admin access

╭─────────────── Attack Path Analysis ──────────────────────╮
│                                                           │
│  Potential privilege escalation paths:                    │
│                                                           │
│  Path 1: SQL Injection → Superuser                        │
│  ─────────────────────────────────────                    │
│  1. login() accepts user input                            │
│  2. Input passed to authenticate()                        │
│  3. Query built with string concatenation                 │
│  4. Injection bypasses authentication                     │
│  5. Session granted superuser privileges                  │
│                                                           │
│  Path 2: Function Overloading                             │
│  ────────────────────────────                             │
│  1. User creates function with same signature             │
│  2. Search path manipulation                              │
│  3. Malicious function called by superuser                │
│                                                           │
│  Mitigation:                                              │
│    - Parameterized queries                                │
│    - Explicit schema qualification                        │
│    - SECURITY DEFINER audit                               │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Find privilege escalation paths

> Show data access from compromised function
```

#### Step 3: Assess Impact

```
> What data could be accessed from auth_check function?

╭─────────────── Impact Assessment ─────────────────────────╮
│                                                           │
│  Function: auth_check()                                   │
│  Access Level: Superuser context                          │
│                                                           │
│  Reachable Data:                                          │
│  ────────────────                                         │
│                                                           │
│  Direct Access:                                           │
│    - pg_authid (passwords, roles)                         │
│    - pg_auth_members (role membership)                    │
│    - All user tables                                      │
│                                                           │
│  Via Function Calls:                                      │
│    - pg_read_file() - Filesystem access                   │
│    - pg_ls_dir() - Directory listing                      │
│    - COPY TO PROGRAM - Command execution                  │
│                                                           │
│  Blast Radius: CRITICAL                                   │
│    - Full database compromise                             │
│    - Potential OS-level access                            │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Find all callers of compromised component
```

---

## Technical Writer Scenarios

### Generating API Documentation

**Scenario:** Technical writer documenting public API.

#### Step 1: Select Documentation Scenario

```
/select 03
```

#### Step 2: Generate Function Docs

```
> Generate documentation for heap_insert

╭─────────────── API Documentation ─────────────────────────╮
│                                                           │
│  ## heap_insert                                           │
│                                                           │
│  Inserts a tuple into a heap relation.                    │
│                                                           │
│  ### Signature                                            │
│                                                           │
│  ```c                                                     │
│  void heap_insert(Relation relation,                      │
│                   HeapTuple tup,                          │
│                   CommandId cid,                          │
│                   int options,                            │
│                   BulkInsertState bistate)                │
│  ```                                                      │
│                                                           │
│  ### Parameters                                           │
│                                                           │
│  | Parameter | Type | Description |                      │
│  |-----------|------|-------------|                      │
│  | relation | Relation | Target heap relation |          │
│  | tup | HeapTuple | Tuple to insert |                   │
│  | cid | CommandId | Command ID for MVCC |               │
│  | options | int | Insert options flags |                │
│  | bistate | BulkInsertState | Bulk insert state |       │
│                                                           │
│  ### Returns                                              │
│                                                           │
│  void (tuple modified in place with OID if applicable)    │
│                                                           │
│  ### Example                                              │
│                                                           │
│  ```c                                                     │
│  HeapTuple tuple = heap_form_tuple(desc, values, nulls);  │
│  heap_insert(rel, tuple, GetCurrentCommandId(true),       │
│              0, NULL);                                    │
│  ```                                                      │
│                                                           │
│  ### See Also                                             │
│                                                           │
│  - heap_update() - Update existing tuple                  │
│  - heap_delete() - Delete tuple                           │
│  - simple_heap_insert() - Simplified wrapper              │
│                                                           │
│  ### Source                                               │
│                                                           │
│  src/backend/access/heap/heapam.c:2156                    │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Document the SPI interface functions

> Create API reference for lock management
```

---

### Understanding Module Architecture

**Scenario:** Technical writer documenting system architecture.

```
> Explain the executor module architecture

╭─────────────── Architecture ──────────────────────────────╮
│                                                           │
│  Executor Module Architecture                             │
│  ═══════════════════════════                              │
│                                                           │
│  Purpose: Execute query plans generated by the planner    │
│                                                           │
│  Directory: src/backend/executor/                         │
│                                                           │
│  Core Components:                                         │
│  ────────────────                                         │
│                                                           │
│  1. execMain.c - Main executor entry points               │
│     - ExecutorStart(): Initialize execution state         │
│     - ExecutorRun(): Main execution loop                  │
│     - ExecutorEnd(): Cleanup and shutdown                 │
│                                                           │
│  2. execProcnode.c - Node dispatcher                      │
│     - ExecProcNode(): Route to specific node types        │
│     - ExecInitNode(): Initialize plan nodes               │
│     - ExecEndNode(): Cleanup plan nodes                   │
│                                                           │
│  3. Node-specific executors:                              │
│     - nodeSeqscan.c    - Sequential scan                  │
│     - nodeIndexscan.c  - Index scan                       │
│     - nodeHashjoin.c   - Hash join                        │
│     - nodeMergejoin.c  - Merge join                       │
│     - nodeAgg.c        - Aggregation                      │
│     - nodeSort.c       - Sorting                          │
│                                                           │
│  Data Flow:                                               │
│  ──────────                                               │
│                                                           │
│  Plan Tree → PlanState Tree → Tuple Output                │
│                                                           │
│  Dependencies:                                            │
│  ─────────────                                            │
│    → access/    (storage layer)                           │
│    → utils/     (memory, cache)                           │
│    → nodes/     (node definitions)                        │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> What are the main components of WAL?

> How does MVCC work in PostgreSQL?
```

---

### Creating Function References

**Scenario:** Technical writer building function index.

```
> List all public functions in executor module

╭─────────────── Function Reference ────────────────────────╮
│                                                           │
│  Executor Public Functions                                │
│  ═════════════════════════                                │
│                                                           │
│  Entry Points:                                            │
│  ─────────────                                            │
│  ExecutorStart()      Initialize execution                │
│  ExecutorRun()        Execute plan                        │
│  ExecutorFinish()     Post-execution processing           │
│  ExecutorEnd()        Cleanup                             │
│                                                           │
│  Node Operations:                                         │
│  ────────────────                                         │
│  ExecProcNode()       Execute single node                 │
│  ExecInitNode()       Initialize node                     │
│  ExecEndNode()        Cleanup node                        │
│  ExecReScan()         Reset for rescan                    │
│                                                           │
│  Tuple Operations:                                        │
│  ─────────────────                                        │
│  ExecStoreTuple()     Store tuple in slot                 │
│  ExecClearTuple()     Clear slot                          │
│  ExecCopySlot()       Copy slot contents                  │
│                                                           │
│  Total: 156 public functions                              │
│                                                           │
╰───────────────────────────────────────────────────────────╯

> Show all entry points with their signatures
```

#### Using Direct SQL Query

```
/query SELECT name, signature, filename FROM nodes_method
       WHERE filename LIKE '%executor%'
       ORDER BY name
       LIMIT 20

╭─────────────── Query Results ─────────────────────────────╮
│                                                           │
│  name              | signature              | filename    │
│  ──────────────────┼────────────────────────┼──────────   │
│  ExecAgg           | ExecAgg(PlanState*)    | nodeAgg.c   │
│  ExecAppend        | ExecAppend(...)        | nodeAppend  │
│  ExecBitmapAnd     | ExecBitmapAnd(...)     | nodeBitma   │
│  ...               | ...                    | ...         │
│                                                           │
│  20 rows returned                                         │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

---

## TUI Command Reference

### All Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/help` | `[command]` | Show help for all commands or specific command |
| `/scenarios` | `[group]` | List available scenarios, optionally filtered |
| `/select` | `<number>` | Select scenario by number (01-16) |
| `/history` | `[count]` | Show conversation history |
| `/save` | `[filename]` | Save current session |
| `/load` | `<filename>` | Load saved session |
| `/config` | `[section] [key] [value]` | View or edit configuration |
| `/stat` | | Show CPG and ChromaDB statistics |
| `/query` | `<SQL>` | Execute SQL on CPG database |
| `/review` | `[source] [id] [--format] [--inline]` | Launch code review |
| `/demo` | `[--scenarios N,N] [--lang en\|ru]` | Run quick benchmark |
| `/clear` | | Clear the screen |
| `/exit` | | Exit the application |
| `/project` | `[list\|switch\|add]` | Manage CPG projects |

### Command Details

#### /project

Manage multiple CPG projects (switch between different codebases).

```bash
# Show current project info
/project

# List all available projects
/project list

# Switch to a different project
/project switch fsin_module
/project switch postgresql

# Add a new project
/project add myproject path/to/project.duckdb python "My Python Project"
```

**Project Configuration (projects.yaml):**

```yaml
projects:
  postgresql:
    db_path: "cpg.duckdb"
    language: c
    description: "PostgreSQL 17 source code"
  fsin_module:
    db_path: "workspace/fsin_module_v2.duckdb"
    language: python
    description: "Django FSIN Module"

active_project: postgresql
```

**Domain Auto-Switching:**

When switching projects, the system automatically activates the appropriate domain plugin:

| Language | Domain Plugin | Security Patterns |
|----------|--------------|-------------------|
| c, cpp | postgresql / generic_cpp | Memory safety, buffer overflow |
| python | python_django | SQL injection, XSS, CSRF |

```bash
# Example: switch to Python/Django project
/project switch fsin_module
# Output: Domain activated: python_django

# Example: switch back to C project
/project switch postgresql
# Output: Domain activated: postgresql
```

#### /scenarios

```bash
# List all scenarios
/scenarios

# Filter by group
/scenarios security    # Security-related scenarios
/scenarios dev         # Development scenarios
/scenarios qa          # Quality assurance scenarios
```

#### /select

```bash
# Select by number
/select 1     # Onboarding
/select 02    # Security Audit
/select 15    # Debugging
```

#### /config

```bash
# View all configuration sections
/config

# View specific section
/config llm

# Set a value
/config llm temperature 0.7
/config llm provider gigachat
```

#### /query

```bash
# Basic queries
/query SELECT COUNT(*) FROM nodes_method
/query SELECT name, filename FROM nodes_method WHERE name LIKE 'heap%'

# Describe tables
/query DESCRIBE nodes_method
/query SHOW TABLES

# Complex queries
/query SELECT caller.name, callee.name
       FROM edges_call e
       JOIN nodes_method caller ON e.src = caller.id
       JOIN nodes_method callee ON e.dst = callee.id
       WHERE callee.name = 'palloc'
       LIMIT 10
```

#### /review

```bash
# Interactive mode (choose source)
/review

# GitHub PR
/review github 123
/review github 123 --format json

# GitLab MR
/review gitlab 456 --inline

# Local git changes
/review git
/review git --format yaml

# Patch file
/review file changes.patch --format md --inline
```

---

## Configuration Guide

### LLM Provider Setup

#### GigaChat (Sber)

```yaml
# config.yaml
llm:
  provider: "gigachat"
  gigachat:
    credentials: ${GIGACHAT_AUTH_KEY}
    model: "GigaChat-2"  # or GigaChat-2-Pro, GigaChat-2-Max
    temperature: 0.7
```

```bash
# Environment variable
export GIGACHAT_AUTH_KEY="your-base64-encoded-key"
```

#### OpenAI

```yaml
# config.yaml
llm:
  provider: "openai"
  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4"
    temperature: 0.7
```

```bash
# Environment variable
export OPENAI_API_KEY="sk-..."
```

#### Local Model (llama.cpp)

```yaml
# config.yaml
llm:
  provider: "local"
  local:
    model_path: ${LLMXCPG_MODEL_PATH}
    n_gpu_layers: -1  # All layers on GPU
    n_ctx: 8192
```

### Retrieval Settings

```yaml
retrieval:
  embedding_model: "all-MiniLM-L6-v2"
  top_k_qa: 3       # QA examples to retrieve
  top_k_cpgql: 5    # CPGQL examples to retrieve
  max_results: 50   # Maximum search results
```

### Query Limits

```yaml
query:
  default_limit: 100  # Default LIMIT for SQL
  max_limit: 1000     # Maximum allowed LIMIT
```

---

## Appendix: All 16 Scenarios

| # | Name | Best For | Example Query |
|---|------|----------|---------------|
| 01 | Onboarding | New developers | "Where is function X defined?" |
| 02 | Security Audit | Security team | "Find SQL injection vulnerabilities" |
| 03 | Documentation | Tech writers | "Generate docs for function X" |
| 04 | Feature Development | Adding features | "Where to add a new hook?" |
| 05 | Refactoring | Code cleanup | "Find dead code in module X" |
| 06 | Performance | Optimization | "Find performance hotspots" |
| 07 | Test Coverage | QA team | "What functions lack tests?" |
| 08 | Compliance | Auditors | "Check OWASP Top 10" |
| 09 | Code Review | Reviewers | "Review this patch" |
| 10 | Cross-Repo | Architects | "Find cross-repo dependencies" |
| 11 | Architecture | Architects | "Find layering violations" |
| 12 | Tech Debt | Managers | "Quantify technical debt" |
| 13 | Mass Refactoring | Large changes | "Rename all X to Y" |
| 14 | Incident Response | Security | "Trace attack vector" |
| 15 | Debugging | Developers | "Find debug points" |
| 16 | Entry Points | Security | "List all API endpoints" |

### Scenario Selection Guide

**For Developers:**
- Day 1: Scenario 01 (Onboarding)
- Feature work: Scenario 04 (Feature Development)
- Bug fixing: Scenario 15 (Debugging)
- Cleanup: Scenario 05 (Refactoring)

**For QA/Testers:**
- Coverage gaps: Scenario 07 (Test Coverage)
- Code review: Scenario 09 (Code Review)
- Quality metrics: Scenario 12 (Tech Debt)

**For Security:**
- Vulnerability scan: Scenario 02 (Security Audit)
- Compliance: Scenario 08 (Compliance)
- Incident: Scenario 14 (Incident Response)
- Attack surface: Scenario 16 (Entry Points)

**For Technical Writers:**
- API docs: Scenario 03 (Documentation)
- Architecture: Scenario 11 (Architecture)
- Dependencies: Scenario 10 (Cross-Repo)

---

## Security Audit Reports (CLI)

### Overview

CodeGraph provides a CLI tool for generating comprehensive security audit reports.
Reports can be generated in multiple formats (Markdown, JSON, SARIF) with full
localization support (English, Russian).

### Scenario: Django Project Security Audit

**Situation:** Security engineer needs to audit a Django project before production deployment.

#### Step 1: Run Full Security Scan

```bash
python -m src.cli.security_audit full \
  --path /path/to/django/project \
  --output-dir ./security_reports \
  --language ru
```

#### Step 2: Review Generated Report

The tool generates three files:

- `security_report.md` - Human-readable Markdown report
- `security_report.json` - Machine-readable JSON for CI/CD
- `security_report.sarif` - GitHub Security Alerts format

#### Example Output (Markdown)

```markdown
# Отчёт по безопасности: My Django Project

**Путь к проекту:** `/path/to/django/project`
**Время аудита:** 2025-12-09 20:43:19
**Проанализировано файлов:** 88

## Краткое резюме

| Серьёзность | Количество |
|----------|-------|
| 🔴 КРИТИЧЕСКИЙ | 2 |
| 🟠 ВЫСОКИЙ | 6 |
| 🟡 СРЕДНИЙ | 2 |

## 🔴 КРИТИЧЕСКИЙ Уязвимости уровня (2)

### 1. SECRET_KEY with Fallback (File Scan)

**Файл:** `backend/settings.py:25`
**CWE:** CWE-798

**Описание:** SECRET_KEY с небезопасным fallback-значением

**Уязвимый код:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'insecure-fallback')
```

**Рекомендация:**
Удалите fallback-значение: SECRET_KEY = os.environ["SECRET_KEY"]
```

### Scenario: Quick Security Check

**Situation:** Developer wants a quick vulnerability scan before commit.

```bash
python -m src.cli.security_audit quick --path .

╭─────────────────── Quick Scan Results ───────────────────╮
│                                                           │
│  Files scanned: 45                                        │
│  Time: 0.3s                                               │
│                                                           │
│  Findings:                                                │
│    🔴 Critical: 0                                         │
│    🟠 High: 2                                             │
│    🟡 Medium: 1                                           │
│                                                           │
│  Run 'security-audit full' for detailed report            │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

### Scenario: CI/CD Integration

**Situation:** Add security checks to GitLab CI pipeline.

#### `.gitlab-ci.yml`

```yaml
security-audit:
  stage: test
  script:
    - pip install -r requirements.txt
    - python -m src.cli.security_audit full \
        --path . \
        --output-dir ./security_reports \
        --format json,sarif
    - |
      CRITICAL=$(jq '.summary.critical_issues' security_reports/security_report.json)
      if [ "$CRITICAL" -gt 0 ]; then
        echo "❌ Critical vulnerabilities found!"
        exit 1
      fi
  artifacts:
    paths:
      - security_reports/
    reports:
      sast: security_reports/security_report.sarif
```

### Programmatic Usage

**Situation:** Generate reports from Python code.

```python
from src.security.file_scanner import FileSecurityScanner
from src.security.report_generator import ReportGenerator

# Initialize scanner
scanner = FileSecurityScanner()

# Run scan
result = scanner.scan_project('/path/to/project')

# Generate report
generator = ReportGenerator()
report = generator.create_report(
    project_name='My Project',
    project_path=result.project_path,
    scan_result=result
)

# Save in multiple formats
output_files = generator.save_report(
    output_dir='./reports',
    formats=['markdown', 'json', 'sarif'],
    language='ru'  # Russian localization
)

print(f"Report saved to: {output_files['markdown']}")
```

### Detected Vulnerability Patterns

The security scanner detects Django/Python specific patterns:

| Pattern ID | Severity | Description |
|------------|----------|-------------|
| `FILE_SECRET_FALLBACK_001` | Critical | SECRET_KEY with insecure fallback |
| `FILE_DJANGO_DEBUG_001` | Critical | DEBUG=True in production |
| `FILE_CORS_001` | High | CORS_ALLOW_ALL_ORIGINS=True |
| `FILE_HOSTS_001` | High | ALLOWED_HOSTS=['*'] |
| `FILE_DB_001` | High | Default database password |
| `FILE_JWT_001` | High | JWT access token > 24h |
| `FILE_PATH_001` | High | Path traversal risk |
| `FILE_DEBUG_PERM_001` | High | Permission based on DEBUG |
| `FILE_TOOLBAR_001` | Medium | Debug toolbar unconditionally enabled |
| `FILE_PAGESIZE_001` | Medium | PAGE_SIZE > 1000 (DoS risk) |

### D3FEND Compliance Section

Reports include MITRE D3FEND Source Code Hardening compliance:

```markdown
## Соответствие D3FEND Source Code Hardening

| Техника | Название | Статус | Применимость |
|---------|----------|--------|--------------|
| D3-CS | Очистка учётных данных | ✅ | Применимо для Python |
| D3-DLV | Валидация доменной логики | ✅ | Применимо для Python |
| D3-OLV | Валидация операционной логики | ✅ | Применимо для Python |
| D3-VI | Инициализация переменных | N/A | Только C/C++ |

**Общий показатель соответствия:** 100% (3/3 применимых техник)
```

---

## Common Workflows

### Daily Security Check

```bash
# Morning security review
/select 02
> Find new vulnerabilities in recently modified files
/review git
/exit
```

### Weekly Code Quality

```bash
# Weekly quality review
/select 05
> Find dead code introduced this week

/select 12
> Show technical debt summary

/select 07
> What new functions lack test coverage?
```

### Pre-Release Audit

```bash
# Before major release
/select 08
> Generate OWASP Top 10 compliance report

/select 02
> Find all critical vulnerabilities

/review git --format json > audit_report.json
```

### New Developer Onboarding

```bash
# First day setup
/select 01
> Explain the overall architecture
> What are the main subsystems?
> Where should I start reading code?

/save onboarding_session
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
4. Reduce context size in config.yaml:
   ```yaml
   llm:
     local:
       n_ctx: 4096  # Reduce from 8192
   ```

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

### Getting Help

- Type `/help` for command reference
- Type `/help <command>` for specific command help
- Check logs in `logs/` directory
- Report issues: https://github.com/anthropics/claude-code/issues

---

## See Also

- [CLI Guide](./CLI_GUIDE.md) - Command-line interface
- [Scenarios](./SCENARIOS.md) - Programmatic scenario usage
- [REST API](../api/REST_API.md) - HTTP API reference
- [Security](../reference/SECURITY.md) - Security features

---

*Generated for CodeGraph v1.0*
