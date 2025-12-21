# Scenario 05: Refactoring

> Senior developer identifying code improvement opportunities.

## Quick Start

```bash
# Select Refactoring Scenario
/select 05
```

## Finding Refactoring Opportunities

### High Complexity Functions

```
> Find functions with cyclomatic complexity over 20

╭─────────────── Complexity Analysis ─────────────────────────╮
│                                                              │
│  Functions Exceeding Threshold (complexity > 20):            │
│                                                              │
│  🔴 exec_simple_query()        complexity: 47                │
│     Location: src/backend/tcop/postgres.c:890                │
│     Suggestion: Extract authentication, parsing,             │
│                 and execution into separate functions        │
│                                                              │
│  🟡 ExecInitNode()             complexity: 32                │
│     Location: src/backend/executor/execProcnode.c:156        │
│     Suggestion: Use dispatch table instead of switch         │
│                                                              │
│  🟡 parse_analyze()            complexity: 28                │
│     Location: src/backend/parser/analyze.c:102               │
│     Suggestion: Extract statement-specific handlers          │
│                                                              │
│  Total: 23 functions above threshold                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Dead Code Detection

```
> Find unused static functions

╭─────────────── Dead Code Analysis ──────────────────────────╮
│                                                              │
│  Unused Static Functions (no callers found):                 │
│                                                              │
│  src/backend/utils/misc/help.c:                              │
│    - old_format_help()         Lines: 45-89                  │
│    - legacy_usage_message()    Lines: 123-156                │
│                                                              │
│  src/backend/catalog/pg_type.c:                              │
│    - deprecated_type_check()   Lines: 789-834                │
│                                                              │
│  Confidence: HIGH (static functions, no external refs)       │
│  Recommendation: Safe to remove after verification           │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Code Duplication

```
> Find duplicate code patterns

╭─────────────── Clone Detection ─────────────────────────────╮
│                                                              │
│  Duplicate Code Clusters:                                    │
│                                                              │
│  Cluster #1 (95% similarity, 34 lines):                      │
│    - src/backend/access/heap/heapam.c:1234-1267              │
│    - src/backend/access/heap/heapam.c:1890-1923              │
│    Suggestion: Extract common logic into helper function     │
│                                                              │
│  Cluster #2 (88% similarity, 22 lines):                      │
│    - src/backend/executor/nodeSeqscan.c:45-66                │
│    - src/backend/executor/nodeIndexscan.c:78-99              │
│    - src/backend/executor/nodeBitmapscan.c:89-110            │
│    Suggestion: Create shared scan initialization routine     │
│                                                              │
│  Total clones: 15 clusters                                   │
│  Lines duplicated: ~450                                      │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Refactoring Planning

### Extract Method Opportunities

```
> Find extract method opportunities in exec_simple_query

╭─────────────── Extract Method Analysis ─────────────────────╮
│                                                              │
│  Function: exec_simple_query()                               │
│  Current Lines: 234                                          │
│                                                              │
│  Suggested Extractions:                                      │
│                                                              │
│  1. Lines 45-78: Authentication handling                     │
│     Suggested name: check_query_authorization()              │
│     Parameters: query_string, session_state                  │
│                                                              │
│  2. Lines 89-134: Query parsing                              │
│     Suggested name: parse_and_analyze_query()                │
│     Parameters: query_string                                 │
│     Returns: ParsedQuery                                     │
│                                                              │
│  3. Lines 156-198: Plan generation                           │
│     Suggested name: generate_query_plan()                    │
│     Parameters: analyzed_query                               │
│     Returns: PlannedQuery                                    │
│                                                              │
│  Impact: Reduces complexity from 47 to ~12 per function      │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Impact Analysis

```
> What would be affected by refactoring heap_insert?

╭─────────────── Impact Analysis ─────────────────────────────╮
│                                                              │
│  Refactoring Target: heap_insert()                           │
│  Direct Callers: 23                                          │
│  Transitive Callers: 156                                     │
│                                                              │
│  Affected Subsystems:                                        │
│    - Executor (12 callers)                                   │
│    - COPY command (3 callers)                                │
│    - Trigger execution (4 callers)                           │
│    - Foreign data wrapper (4 callers)                        │
│                                                              │
│  Test Files to Update:                                       │
│    - regress/sql/insert.sql                                  │
│    - regress/sql/copy.sql                                    │
│    - regress/sql/triggers.sql                                │
│                                                              │
│  Risk Level: HIGH (core function)                            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Find functions with high complexity"
- "Show duplicate code patterns"
- "Find unused code in [module]"
- "What would be affected by changing [function]?"
- "Suggest refactoring for [function_name]"
- "Find long functions that should be split"

## Related Scenarios

- [Performance](./06-performance.md) - Performance-driven refactoring
- [Tech Debt](./12-tech-debt.md) - Debt assessment
- [Mass Refactoring](./13-mass-refactoring.md) - Large-scale changes
- [Code Review](./09-code-review.md) - Review refactoring changes
