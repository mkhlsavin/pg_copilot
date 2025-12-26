# Scenario 04: Feature Development

> Developer understanding existing code to add new features.

## Quick Start

```bash
# Select Feature Development Scenario
/select 04
```

## Understanding Existing Code

### Finding Related Functions

```
> Find functions related to transaction handling

╭─────────────── Related Code ────────────────────────────────╮
│                                                              │
│  Transaction Functions:                                      │
│                                                              │
│  Entry Points:                                               │
│    StartTransaction()      src/backend/access/transam/xact.c │
│    CommitTransaction()     src/backend/access/transam/xact.c │
│    AbortTransaction()      src/backend/access/transam/xact.c │
│                                                              │
│  Support Functions:                                          │
│    AssignTransactionId()   src/backend/access/transam/xact.c │
│    GetCurrentTransactionId() src/backend/access/transam/xact.c │
│                                                              │
│  Related Modules:                                            │
│    src/backend/access/heap/  - Heap operations               │
│    src/backend/storage/lmgr/ - Lock manager                  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Understanding Call Chains

```
> Show the call path from parser to executor

╭─────────────── Call Chain ──────────────────────────────────╮
│                                                              │
│  Parser → Executor Flow:                                     │
│                                                              │
│  1. pg_parse_query()                                         │
│       ↓                                                      │
│  2. pg_analyze_and_rewrite()                                 │
│       ↓                                                      │
│  3. pg_plan_queries()                                        │
│       ↓                                                      │
│  4. PortalRun()                                              │
│       ↓                                                      │
│  5. ExecutorStart() → ExecutorRun() → ExecutorFinish()       │
│       ↓                                                      │
│  6. ExecProcNode() [dispatches to specific nodes]            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Integration Points

### Finding Extension Points

```
> Where can I add a new node type?

╭─────────────── Extension Points ────────────────────────────╮
│                                                              │
│  Adding New Executor Node Type:                              │
│                                                              │
│  1. Define node structure in:                                │
│     src/include/nodes/execnodes.h                            │
│                                                              │
│  2. Implement node operations:                               │
│     src/backend/executor/nodeXXX.c                           │
│     - ExecInitXXX()                                          │
│     - ExecXXX()                                              │
│     - ExecEndXXX()                                           │
│                                                              │
│  3. Register in dispatcher:                                  │
│     src/backend/executor/execProcnode.c                      │
│     - ExecInitNode()                                         │
│     - ExecProcNode()                                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Understanding Dependencies

```
> What modules does the buffer manager depend on?

╭─────────────── Dependencies ────────────────────────────────╮
│                                                              │
│  Buffer Manager Dependencies:                                │
│                                                              │
│  Upstream (uses):                                            │
│    - storage/smgr     (Storage manager interface)            │
│    - storage/lmgr     (Lock manager)                         │
│    - utils/memutils   (Memory contexts)                      │
│                                                              │
│  Downstream (used by):                                       │
│    - access/heap      (Heap access methods)                  │
│    - access/index     (Index access methods)                 │
│    - executor/*       (Query execution)                      │
│                                                              │
│  Interfaces:                                                 │
│    - ReadBuffer()     (Main read interface)                  │
│    - ReleaseBuffer()  (Release interface)                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Code Patterns

### Finding Similar Implementations

```
> Show examples of error handling in executor

╭─────────────── Error Handling Patterns ─────────────────────╮
│                                                              │
│  Common Patterns in Executor:                                │
│                                                              │
│  1. ereport with ERROR level:                                │
│     ereport(ERROR,                                           │
│         (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),             │
│          errmsg("feature X not supported")));                │
│                                                              │
│  2. Exception handling with PG_TRY:                          │
│     PG_TRY();                                                │
│     {                                                        │
│         /* risky operation */                                │
│     }                                                        │
│     PG_CATCH();                                              │
│     {                                                        │
│         /* cleanup */                                        │
│         PG_RE_THROW();                                       │
│     }                                                        │
│     PG_END_TRY();                                            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "How does [feature_name] work?"
- "What functions are involved in [subsystem]?"
- "Where should I add code for [new_feature]?"
- "Show similar implementations to [existing_feature]"
- "What's the data flow for [operation]?"
- "Find integration points for [component]"

## Related Scenarios

- [Onboarding](./01-onboarding.md) - Codebase exploration basics
- [Architecture](./11-architecture.md) - Architectural understanding
- [Refactoring](./05-refactoring.md) - Code improvement
