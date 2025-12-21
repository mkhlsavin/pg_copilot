# Scenario 01: Developer Onboarding

> New developer joins the team and needs to understand codebase structure quickly.

## Quick Start

```bash
# Select Onboarding Scenario
/select 01
```

## Use Cases

### Day 1: Codebase Overview

Ask high-level questions about the system:

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

### Finding Function Definitions

Locate function implementations quickly:

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

### Understanding Call Graphs

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

### Tracing Data Flow

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

### Understanding Memory Management

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

## Example Questions for Day 1

1. "What is the main architecture?"
2. "Where is [function_name] defined?"
3. "Who calls [function_name]?"
4. "What does [module_name] do?"
5. "Show me the relationship between X and Y"

## Tips

- Start with high-level questions, then dive deeper
- Use the call graph to understand dependencies
- Ask about data flow to understand how components interact
- Save your session with `/save` for future reference

## Related Scenarios

- [Feature Development](./04-feature-development.md) - Once you understand the codebase
- [Debugging](./15-debugging.md) - For troubleshooting issues
- [Architecture](./11-architecture.md) - For deeper architectural understanding
