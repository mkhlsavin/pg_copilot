# Scenario 12: Tech Debt Assessment

> Tech lead identifying and prioritizing technical debt.

## Quick Start

```bash
# Select Tech Debt Scenario
/select 12
```

## Debt Identification

### Overall Debt Score

```
> Calculate technical debt score

╭─────────────── Tech Debt Summary ───────────────────────────╮
│                                                              │
│  Overall Technical Debt Score: 34/100 (Moderate)             │
│                                                              │
│  Category Breakdown:                                         │
│                                                              │
│  Complexity Debt:      42%  ████████░░                       │
│    - 23 functions over complexity threshold                  │
│    - 5 functions over 300 lines                              │
│                                                              │
│  Duplication Debt:     28%  █████░░░░░                       │
│    - 15 clone clusters detected                              │
│    - ~450 duplicated lines                                   │
│                                                              │
│  Coupling Debt:        35%  ███████░░░                       │
│    - 8 circular dependencies                                 │
│    - 12 high-coupling modules                                │
│                                                              │
│  Documentation Debt:   31%  ██████░░░░                       │
│    - 67% comment coverage (target: 80%)                      │
│    - 23 undocumented public functions                        │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Debt Hotspots

```
> Find technical debt hotspots

╭─────────────── Debt Hotspots ───────────────────────────────╮
│                                                              │
│  Top 10 Files by Debt Density:                               │
│                                                              │
│  #  File                          Score  Issues              │
│  ─────────────────────────────────────────────────────────── │
│  1  src/backend/tcop/postgres.c   78     Complexity, size    │
│  2  src/backend/parser/gram.y     72     Generated, complex  │
│  3  src/backend/executor/execMain 65     Complexity          │
│  4  src/backend/optimizer/plan.c  61     Coupling            │
│  5  src/backend/catalog/pg_type.c 58     Duplication         │
│                                                              │
│  Recommendation: Focus on top 5 files for maximum impact     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Debt Categories

### Complexity Debt

```
> Find complexity debt items

╭─────────────── Complexity Debt ─────────────────────────────╮
│                                                              │
│  High Complexity Functions:                                  │
│                                                              │
│  🔴 exec_simple_query()           CC: 47                     │
│     Estimated refactoring: 4-8 hours                         │
│     Impact: High (core query path)                           │
│                                                              │
│  🔴 ExecInitNode()                CC: 32                     │
│     Estimated refactoring: 2-4 hours                         │
│     Impact: Medium (dispatch function)                       │
│                                                              │
│  Deeply Nested Code:                                         │
│    - 5 functions with nesting depth > 5                      │
│    - 12 functions with nesting depth > 4                     │
│                                                              │
│  Total complexity debt: ~40 hours                            │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Coupling Debt

```
> Find coupling issues

╭─────────────── Coupling Debt ───────────────────────────────╮
│                                                              │
│  Circular Dependencies:                                      │
│                                                              │
│  🔴 executor ↔ optimizer                                     │
│     Files: execMain.c, createplan.c                          │
│     Impact: Compilation order, testing difficulty            │
│                                                              │
│  🔴 catalog ↔ utils                                          │
│     Files: pg_class.c, relcache.c                            │
│     Impact: Initialization complexity                        │
│                                                              │
│  High Fan-out Functions (> 20 dependencies):                 │
│    ProcessQuery()        depends on 34 modules               │
│    PostgresMain()        depends on 28 modules               │
│                                                              │
│  High Fan-in Functions (> 50 callers):                       │
│    palloc()              89 callers                          │
│    ereport()             156 callers                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Legacy Code Debt

```
> Find legacy code patterns

╭─────────────── Legacy Code ─────────────────────────────────╮
│                                                              │
│  Deprecated Patterns Found:                                  │
│                                                              │
│  🟡 Old-style function declarations: 12                      │
│     Example: void func() instead of void func(void)          │
│                                                              │
│  🟡 Implicit type conversions: 45                            │
│     Risk: Potential data loss or undefined behavior          │
│                                                              │
│  🔴 Commented-out code blocks: 23                            │
│     Total lines: ~340                                        │
│     Recommendation: Remove or document                       │
│                                                              │
│  🟡 TODO/FIXME comments: 156                                 │
│     FIXME: 34                                                │
│     TODO: 89                                                 │
│     HACK: 12                                                 │
│     XXX: 21                                                  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Prioritization

### Debt Prioritization Matrix

```
> Prioritize debt items by impact and effort

╭─────────────── Prioritization Matrix ───────────────────────╮
│                                                              │
│                    Low Effort    High Effort                 │
│                 ┌─────────────┬─────────────┐                │
│   High Impact  │  QUICK WINS │  MAJOR      │                │
│                │  ───────────│  PROJECTS   │                │
│                │  • Remove   │  • Refactor │                │
│                │    dead code│    postgres │                │
│                │  • Fix docs │    .c       │                │
│                │             │  • Split    │                │
│                │             │    large    │                │
│                │             │    modules  │                │
│                ├─────────────┼─────────────┤                │
│   Low Impact   │  FILL-INS   │  AVOID      │                │
│                │  ───────────│  ───────────│                │
│                │  • Style    │  • Deep     │                │
│                │    cleanup  │    refactor │                │
│                │  • Comment  │    of       │                │
│                │    updates  │    working  │                │
│                │             │    code     │                │
│                └─────────────┴─────────────┘                │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Calculate technical debt score"
- "Find debt hotspots"
- "Show complexity debt items"
- "Find coupling issues"
- "Prioritize debt by impact"
- "Find TODO/FIXME comments"

## Related Scenarios

- [Refactoring](./05-refactoring.md) - Address debt through refactoring
- [Performance](./06-performance.md) - Performance-related debt
- [Compliance](./08-compliance.md) - Standards compliance debt
- [Mass Refactoring](./13-mass-refactoring.md) - Large-scale debt reduction
