# Scenario 15: Debugging Assistance

> Developer debugging issues with code navigation and analysis.

## Table of Contents

- [Quick Start](#quick-start)
- [Call Path Tracing](#call-path-tracing)
  - [Trace Function Execution](#trace-function-execution)
  - [Reverse Trace (Callees)](#reverse-trace-callees)
- [Error Path Analysis](#error-path-analysis)
  - [Find Error Handlers](#find-error-handlers)
  - [Exception Flow](#exception-flow)
- [State Analysis](#state-analysis)
  - [Variable Tracking](#variable-tracking)
- [Debugging Workflows](#debugging-workflows)
  - [Quick Debug Checklist](#quick-debug-checklist)
- [Example Questions](#example-questions)
- [Related Scenarios](#related-scenarios)

## Quick Start

```bash
# Select Debugging Scenario
/select 15
```

## Call Path Tracing

### Trace Function Execution

```
> Trace the call path to heap_insert

╭─────────────── Call Path ───────────────────────────────────╮
│                                                              │
│  Target: heap_insert()                                       │
│  Location: src/backend/access/heap/heapam.c:2156             │
│                                                              │
│  Call Paths (top 3 by frequency):                            │
│                                                              │
│  Path 1 (INSERT statement):                                  │
│    exec_simple_query()                                       │
│      └── PortalRun()                                         │
│            └── ExecutorRun()                                 │
│                  └── ExecModifyTable()                       │
│                        └── ExecInsert()                      │
│                              └── table_tuple_insert()        │
│                                    └── heap_insert() ←       │
│                                                              │
│  Path 2 (COPY command):                                      │
│    DoCopy()                                                  │
│      └── CopyFrom()                                          │
│            └── CopyMultiInsertBufferFlush()                  │
│                  └── heap_insert() ←                         │
│                                                              │
│  Path 3 (Trigger execution):                                 │
│    ExecCallTriggerFunc()                                     │
│      └── heap_insert() ←                                     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Reverse Trace (Callees)

```
> What functions does heap_insert call?

╭─────────────── Callees ─────────────────────────────────────╮
│                                                              │
│  heap_insert() calls:                                        │
│                                                              │
│  Memory/Buffer:                                              │
│    RelationGetBufferForTuple()  - Get target buffer          │
│    BufferGetPage()              - Get page from buffer       │
│    PageAddItem()                - Add item to page           │
│    MarkBufferDirty()            - Mark for write             │
│                                                              │
│  Transaction:                                                │
│    GetCurrentTransactionId()    - Get XID                    │
│    TransactionIdStore()         - Store XID in tuple         │
│                                                              │
│  Locking:                                                    │
│    LockBuffer()                 - Lock buffer                │
│    UnlockReleaseBuffer()        - Unlock and release         │
│                                                              │
│  Logging:                                                    │
│    XLogInsert()                 - WAL logging                │
│    log_heap_insert()            - Heap-specific WAL          │
│                                                              │
│  Total direct callees: 23                                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Error Path Analysis

### Find Error Handlers

```
> What error handlers exist for heap operations?

╭─────────────── Error Handlers ──────────────────────────────╮
│                                                              │
│  Error Handling in Heap Module:                              │
│                                                              │
│  ereport(ERROR) locations:                                   │
│                                                              │
│  heap_insert():                                              │
│    Line 2178: "tuple too big"                                │
│    Line 2189: "no free space on page"                        │
│                                                              │
│  heap_update():                                              │
│    Line 3456: "concurrent update detected"                   │
│    Line 3478: "tuple updated by different transaction"       │
│                                                              │
│  heap_delete():                                              │
│    Line 2890: "tuple already deleted"                        │
│                                                              │
│  PG_TRY/PG_CATCH blocks:                                     │
│    heap_vacuum_rel(): 2 exception handlers                   │
│    heap_prepare_insert(): 1 exception handler                │
│                                                              │
│  Total error paths: 15                                       │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Exception Flow

```
> Trace what happens when heap_insert fails

╭─────────────── Exception Flow ──────────────────────────────╮
│                                                              │
│  Exception: "tuple too big" in heap_insert()                 │
│                                                              │
│  Exception Path:                                             │
│    heap_insert() raises ERROR                                │
│      ↓                                                       │
│    PG_CATCH in ExecModifyTable()                             │
│      ↓ (no specific handler, re-raise)                       │
│    PG_CATCH in ExecutorRun()                                 │
│      ↓ (cleanup, re-raise)                                   │
│    PG_CATCH in PortalRun()                                   │
│      ↓ (abort transaction)                                   │
│    PG_CATCH in PostgresMain()                                │
│      → Send error to client                                  │
│      → Rollback transaction                                  │
│      → Continue main loop                                    │
│                                                              │
│  Resources Cleaned Up:                                       │
│    - Buffers released                                        │
│    - Locks released                                          │
│    - Memory contexts reset                                   │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## State Analysis

### Variable Tracking

```
> Track the state of 'tuple' variable through heap_insert

╭─────────────── Variable State ──────────────────────────────╮
│                                                              │
│  Variable: tuple (HeapTuple)                                 │
│  Function: heap_insert()                                     │
│                                                              │
│  State Transitions:                                          │
│                                                              │
│  Line 2160: [INPUT] Received from caller                     │
│             State: Initialized, no OID                       │
│                                                              │
│  Line 2165: [MODIFIED] HeapTupleSetOid()                     │
│             State: OID assigned                              │
│                                                              │
│  Line 2170: [MODIFIED] HeapTupleHeaderSetXmin()              │
│             State: Xmin set to current XID                   │
│                                                              │
│  Line 2178: [CHECKED] tuple size validation                  │
│             State: Validated or ERROR                        │
│                                                              │
│  Line 2190: [MODIFIED] PageAddItem()                         │
│             State: Stored in buffer page                     │
│                                                              │
│  Line 2210: [OUTPUT] Return to caller                        │
│             State: Fully inserted, WAL logged                │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Debugging Workflows

### Quick Debug Checklist

```
> Generate debug checklist for heap_insert issues

╭─────────────── Debug Checklist ─────────────────────────────╮
│                                                              │
│  Debugging heap_insert() Issues:                             │
│                                                              │
│  1. Check Input Validity                                     │
│     □ Is relation valid and open?                            │
│     □ Is tuple properly formed?                              │
│     □ Is tuple size within limits?                           │
│                                                              │
│  2. Check Transaction State                                  │
│     □ Is there an active transaction?                        │
│     □ Is the transaction ID valid?                           │
│     □ Check for transaction wraparound                       │
│                                                              │
│  3. Check Buffer State                                       │
│     □ Is buffer properly locked?                             │
│     □ Is there free space on page?                           │
│     □ Is buffer dirty flag set?                              │
│                                                              │
│  4. Check WAL State                                          │
│     □ Is WAL logging enabled?                                │
│     □ Is the WAL insert successful?                          │
│     □ Check WAL buffer space                                 │
│                                                              │
│  5. Common Errors                                            │
│     □ "tuple too big" → Check tuple size                     │
│     □ "no free space" → Check autovacuum                     │
│     □ "deadlock" → Check lock ordering                       │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Trace the call path to [function]"
- "What functions does [function] call?"
- "Find error handlers in [module]"
- "What happens when [function] fails?"
- "Track variable [name] through [function]"
- "Generate debug checklist for [issue]"

## Related Scenarios

- [Onboarding](./01-onboarding.md) - Understanding code structure
- [Performance](./06-performance.md) - Performance debugging
- [Feature Development](./04-feature-development.md) - Understanding call chains
