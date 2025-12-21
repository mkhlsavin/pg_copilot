# Scenario 11: Architecture Analysis

> Software architect understanding and documenting system architecture.

## Quick Start

```bash
# Select Architecture Scenario
/select 11
```

## Subsystem Mapping

### Module Overview

```
> Map the PostgreSQL architecture

╭─────────────── Architecture Overview ───────────────────────╮
│                                                              │
│  PostgreSQL Subsystem Architecture:                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Client Layer                          │ │
│  │  libpq, JDBC, ODBC, psql                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   Protocol Layer                         │ │
│  │  PostgresMain, pqcomm, auth                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Query Processing Layer                      │ │
│  │  Parser → Analyzer → Planner → Executor                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Storage Layer                           │ │
│  │  Buffer Manager → Heap/Index Access → File Manager       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Layer Dependencies

```
> Show dependencies between architectural layers

╭─────────────── Layer Dependencies ──────────────────────────╮
│                                                              │
│  Dependency Flow (top-down):                                 │
│                                                              │
│  Protocol                                                    │
│    └── Query Processing                                      │
│          ├── Storage                                         │
│          │     ├── Buffer Manager                            │
│          │     ├── Lock Manager                              │
│          │     └── Transaction Manager                       │
│          └── Catalog                                         │
│                └── Storage                                   │
│                                                              │
│  Cross-cutting Concerns:                                     │
│    - Memory Management (all layers)                          │
│    - Error Handling (all layers)                             │
│    - Logging (all layers)                                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Pattern Detection

### Design Patterns Used

```
> Find design patterns in the codebase

╭─────────────── Design Patterns ─────────────────────────────╮
│                                                              │
│  Detected Design Patterns:                                   │
│                                                              │
│  Strategy Pattern:                                           │
│    - Access Methods (heap, btree, hash, gin, gist)           │
│    - Scan Types (sequential, index, bitmap)                  │
│                                                              │
│  Observer Pattern:                                           │
│    - Event trigger system                                    │
│    - Hook mechanism (executor hooks, planner hooks)          │
│                                                              │
│  Factory Pattern:                                            │
│    - Node creation (makeNode, copyObject)                    │
│    - Memory context creation                                 │
│                                                              │
│  Singleton Pattern:                                          │
│    - Shared memory segments                                  │
│    - System catalogs cache                                   │
│                                                              │
│  Iterator Pattern:                                           │
│    - Executor node iteration (ExecProcNode)                  │
│    - Heap scan iteration                                     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Architecture Violations

```
> Find architecture pattern violations

╭─────────────── Architecture Violations ─────────────────────╮
│                                                              │
│  Layer Boundary Violations:                                  │
│                                                              │
│  🔴 Direct file access from executor                         │
│     Location: src/backend/executor/nodeCustom.c:234          │
│     Issue: Bypasses buffer manager                           │
│     Fix: Use ReadBuffer() instead of direct read             │
│                                                              │
│  🟡 Catalog access without proper locks                      │
│     Location: src/backend/utils/cache/relcache.c:567         │
│     Issue: Potential race condition                          │
│     Fix: Add LockRelationOid() before access                 │
│                                                              │
│  Circular Dependencies:                                      │
│    optimizer ↔ executor (3 locations)                        │
│                                                              │
│  Total violations: 5                                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Component Analysis

### Module Cohesion

```
> Analyze cohesion of the executor module

╭─────────────── Cohesion Analysis ───────────────────────────╮
│                                                              │
│  Module: src/backend/executor/                               │
│                                                              │
│  Cohesion Score: 78% (Good)                                  │
│                                                              │
│  Sub-components:                                             │
│    execMain.c     - Entry points (High cohesion)             │
│    execProcnode.c - Node dispatch (High cohesion)            │
│    execQual.c     - Qualification eval (High cohesion)       │
│    execUtils.c    - Utilities (Medium cohesion)              │
│                                                              │
│  Improvement Opportunities:                                  │
│    - Split execUtils.c into focused modules                  │
│    - Extract parallel execution to separate module           │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Interface Analysis

```
> Show public interfaces of storage layer

╭─────────────── Public Interfaces ───────────────────────────╮
│                                                              │
│  Storage Layer Public API:                                   │
│                                                              │
│  Buffer Manager (bufmgr.h):                                  │
│    ReadBuffer()           - Read page into buffer            │
│    ReleaseBuffer()        - Release buffer pin               │
│    MarkBufferDirty()      - Mark for write                   │
│    FlushBuffer()          - Write to disk                    │
│                                                              │
│  Heap Access (heapam.h):                                     │
│    heap_insert()          - Insert tuple                     │
│    heap_delete()          - Delete tuple                     │
│    heap_update()          - Update tuple                     │
│    heap_fetch()           - Fetch tuple by TID               │
│                                                              │
│  Lock Manager (lmgr.h):                                      │
│    LockRelation()         - Lock relation                    │
│    UnlockRelation()       - Unlock relation                  │
│    LockTuple()            - Lock tuple                       │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Map the system architecture"
- "Show dependencies between layers"
- "Find design patterns used"
- "Detect architecture violations"
- "Analyze module cohesion"
- "Show public interfaces of [module]"

## Related Scenarios

- [Onboarding](./01-onboarding.md) - Initial exploration
- [Documentation](./03-documentation.md) - Generate architecture docs
- [Cross-Repo](./10-cross-repo.md) - Multi-repository analysis
- [Feature Development](./04-feature-development.md) - Understanding for development
