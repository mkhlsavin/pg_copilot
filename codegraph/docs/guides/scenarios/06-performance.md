# Scenario 06: Performance Analysis

> Performance engineer identifying bottlenecks and optimization opportunities.

## Quick Start

```bash
# Select Performance Scenario
/select 06
```

## Complexity Analysis

### Finding Hot Functions

```
> Find functions with highest cyclomatic complexity

╭─────────────── Complexity Report ───────────────────────────╮
│                                                              │
│  Top 10 Most Complex Functions:                              │
│                                                              │
│  #  Function                    Complexity  Lines  File      │
│  ─────────────────────────────────────────────────────────── │
│  1  exec_simple_query           47          234    postgres.c│
│  2  ExecInitNode                32          189    execProc..│
│  3  parse_analyze               28          156    analyze.c │
│  4  standard_ProcessUtility     26          312    utility.c │
│  5  heap_insert                 24          178    heapam.c  │
│                                                              │
│  Average complexity: 8.4                                     │
│  Functions > 20: 23                                          │
│  Functions > 30: 5                                           │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Deep Nesting Detection

```
> Find functions with deep loop nesting

╭─────────────── Nesting Analysis ────────────────────────────╮
│                                                              │
│  Functions with Nesting Depth > 4:                           │
│                                                              │
│  🔴 join_search_one_level()     depth: 6                     │
│     Location: src/backend/optimizer/path/joinrels.c:89       │
│     Pattern: Triple-nested loops with conditions             │
│     Impact: O(n³) complexity in worst case                   │
│                                                              │
│  🟡 ExecHashJoinImpl()          depth: 5                     │
│     Location: src/backend/executor/nodeHashjoin.c:234        │
│     Pattern: Nested loop with retry logic                    │
│                                                              │
│  Optimization suggestions available for 12 functions         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Memory Analysis

### Allocation Patterns

```
> Find functions that allocate large amounts of memory

╭─────────────── Memory Allocation Analysis ──────────────────╮
│                                                              │
│  High Allocation Functions:                                  │
│                                                              │
│  Function                   Allocations  Context              │
│  ────────────────────────────────────────────────────────────│
│  ExecHashTableCreate        palloc x 15  HashMemoryContext   │
│  MakeTupleTableSlot         palloc x 8   Per-tuple           │
│  BuildTupleHashTable        palloc x 12  HashMemoryContext   │
│                                                              │
│  Memory Context Hotspots:                                    │
│    - HashMemoryContext: 45% of allocations                   │
│    - MessageContext: 23% of allocations                      │
│    - PortalContext: 18% of allocations                       │
│                                                              │
│  Recommendation: Review HashMemoryContext usage              │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Call Frequency Analysis

### Hot Paths

```
> Find frequently called functions in query execution

╭─────────────── Call Frequency Analysis ─────────────────────╮
│                                                              │
│  Hot Functions (by call count in typical query):             │
│                                                              │
│  Function                 Calls/Query   Cumulative           │
│  ────────────────────────────────────────────────────────────│
│  slot_getattr             ~10,000       Inner loop           │
│  ExecQual                 ~5,000        Row filtering        │
│  ExecProject              ~2,500        Projection           │
│  ExecProcNode             ~1,000        Node dispatch        │
│                                                              │
│  Critical Path:                                              │
│  ExecutorRun → ExecProcNode → ExecScan → slot_getattr        │
│                                                              │
│  Optimization Focus: Inner loop functions                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Algorithmic Patterns

### O(n²) and Worse

```
> Find potential O(n²) patterns

╭─────────────── Algorithmic Complexity ──────────────────────╮
│                                                              │
│  Potentially Quadratic Patterns:                             │
│                                                              │
│  🔴 list_member() in loop                                    │
│     Location: src/backend/catalog/dependency.c:456           │
│     Pattern: Linear search in loop                           │
│     Fix: Use hash table for membership testing               │
│                                                              │
│  🟡 bsearch in nested loop                                   │
│     Location: src/backend/optimizer/path/costsize.c:789      │
│     Pattern: O(n log n) per iteration                        │
│     Current complexity: O(n² log n)                          │
│                                                              │
│  Total patterns found: 8                                     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Find functions with high complexity"
- "Show memory allocation hotspots"
- "Find O(n²) patterns"
- "What are the most frequently called functions?"
- "Find functions with deep nesting"
- "Show critical execution paths"

## Metrics Reference

| Metric | Threshold | Action |
|--------|-----------|--------|
| Cyclomatic complexity | > 20 | Consider splitting |
| Nesting depth | > 4 | Refactor loops |
| Function length | > 200 lines | Extract methods |
| Allocations per call | > 10 | Review memory usage |

## Related Scenarios

- [Refactoring](./05-refactoring.md) - Code improvement
- [Tech Debt](./12-tech-debt.md) - Debt indicators
- [Debugging](./15-debugging.md) - Performance debugging
