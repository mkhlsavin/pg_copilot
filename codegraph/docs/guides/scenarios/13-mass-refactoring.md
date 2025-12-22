# Scenario 13: Mass Refactoring

> Tech lead planning and coordinating large-scale code changes.

## Table of Contents

- [Quick Start](#quick-start)
- [Scope Analysis](#scope-analysis)
  - [Identify Refactoring Scope](#identify-refactoring-scope)
  - [Dependency Analysis](#dependency-analysis)
- [Change Planning](#change-planning)
  - [Generate Refactoring Plan](#generate-refactoring-plan)
  - [Generate Change Script](#generate-change-script)
- [Risk Management](#risk-management)
  - [Impact Assessment](#impact-assessment)
  - [Rollback Planning](#rollback-planning)
- [Example Questions](#example-questions)
- [Related Scenarios](#related-scenarios)

## Quick Start

```bash
# Select Mass Refactoring Scenario
/select 13
```

## Scope Analysis

### Identify Refactoring Scope

```
> Plan mass refactoring of memory allocation functions

╭─────────────── Scope Analysis ──────────────────────────────╮
│                                                              │
│  Refactoring Target: Memory Allocation API                   │
│                                                              │
│  Affected Functions:                                         │
│    palloc()          89 usages across 45 files               │
│    palloc0()         67 usages across 38 files               │
│    repalloc()        34 usages across 22 files               │
│    pfree()           112 usages across 52 files              │
│                                                              │
│  Total Impact:                                               │
│    Files affected: 78                                        │
│    Lines to modify: ~450                                     │
│    Subsystems: 12                                            │
│                                                              │
│  Risk Assessment: HIGH                                       │
│    - Core functionality                                      │
│    - Wide usage                                              │
│    - Performance critical                                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Dependency Analysis

```
> Show dependencies for mass refactoring

╭─────────────── Dependency Graph ────────────────────────────╮
│                                                              │
│  Refactoring Order (by dependency):                          │
│                                                              │
│  Phase 1: Core (no dependencies)                             │
│    └── mcxt.c (memory context core)                          │
│                                                              │
│  Phase 2: Low-level (depends on Phase 1)                     │
│    ├── aset.c (allocation set)                               │
│    ├── generation.c (generation context)                     │
│    └── slab.c (slab allocator)                               │
│                                                              │
│  Phase 3: Utilities (depends on Phase 2)                     │
│    ├── stringinfo.c                                          │
│    ├── psprintf.c                                            │
│    └── palloc_extended.c                                     │
│                                                              │
│  Phase 4: Consumers (depends on all above)                   │
│    └── [78 consumer files]                                   │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Change Planning

### Generate Refactoring Plan

```
> Create refactoring plan with tasks

╭─────────────── Refactoring Plan ────────────────────────────╮
│                                                              │
│  Mass Refactoring: Memory API Modernization                  │
│                                                              │
│  Task 1: Update Core Interface                               │
│    Files: src/backend/utils/mmgr/mcxt.c                      │
│    Changes: Add new API functions                            │
│    Tests: Unit tests for new functions                       │
│                                                              │
│  Task 2: Create Compatibility Layer                          │
│    Files: src/include/utils/palloc.h                         │
│    Changes: Macro wrappers for old API                       │
│    Tests: Verify backward compatibility                      │
│                                                              │
│  Task 3: Update Executor Module                              │
│    Files: 12 files in executor/                              │
│    Changes: Switch to new API                                │
│    Tests: Regression tests                                   │
│                                                              │
│  Task 4: Update Storage Module                               │
│    Files: 8 files in storage/                                │
│    Changes: Switch to new API                                │
│    Tests: Regression tests                                   │
│                                                              │
│  [... 6 more phases ...]                                     │
│                                                              │
│  Total Tasks: 10                                             │
│  Parallel Tracks: 3 (after Phase 2)                          │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Generate Change Script

```
> Generate sed commands for API migration

╭─────────────── Change Script ───────────────────────────────╮
│                                                              │
│  Automated Refactoring Commands:                             │
│                                                              │
│  # Step 1: Simple replacements                               │
│  find . -name "*.c" -exec sed -i \                           │
│    's/palloc(\([^)]*\))/palloc_new(\1)/g' {} \;              │
│                                                              │
│  # Step 2: Pattern with error handling                       │
│  # Requires manual review                                    │
│  grep -rn "palloc.*;" | grep -v "if.*palloc"                 │
│                                                              │
│  # Step 3: Verify changes                                    │
│  git diff --stat                                             │
│                                                              │
│  Warning: Some patterns require manual review:               │
│    - Conditional allocations                                 │
│    - Macro expansions                                        │
│    - Error handling patterns                                 │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Risk Management

### Impact Assessment

```
> Assess risk of mass refactoring

╭─────────────── Risk Assessment ─────────────────────────────╮
│                                                              │
│  Risk Matrix:                                                │
│                                                              │
│  🔴 High Risk Areas:                                         │
│    - Transaction commit path (performance critical)          │
│    - Buffer management (data integrity)                      │
│    - Lock manager (deadlock potential)                       │
│                                                              │
│  🟡 Medium Risk Areas:                                       │
│    - Executor nodes (covered by tests)                       │
│    - Catalog operations (reversible)                         │
│                                                              │
│  🟢 Low Risk Areas:                                          │
│    - Utility functions (isolated)                            │
│    - Contrib modules (optional)                              │
│                                                              │
│  Mitigation Strategies:                                      │
│    1. Feature flags for gradual rollout                      │
│    2. Comprehensive test coverage before change              │
│    3. Rollback plan for each phase                           │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Rollback Planning

```
> Generate rollback plan

╭─────────────── Rollback Plan ───────────────────────────────╮
│                                                              │
│  Rollback Procedures by Phase:                               │
│                                                              │
│  Phase 1 Rollback:                                           │
│    git revert <commit-hash>                                  │
│    Risk: None (core changes only)                            │
│                                                              │
│  Phase 2 Rollback:                                           │
│    git revert <commit-range>                                 │
│    Additional: Rebuild compatibility layer                   │
│                                                              │
│  Phase 3+ Rollback:                                          │
│    git revert <commit-range>                                 │
│    Additional: Run regression suite                          │
│    Warning: May require data migration                       │
│                                                              │
│  Point of No Return: After Phase 7                           │
│    (Compatibility layer removed)                             │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Plan mass refactoring of [API/pattern]"
- "Show dependencies for refactoring"
- "Generate change script for [pattern]"
- "Assess risk of mass refactoring"
- "Create rollback plan"
- "Split refactoring into phases"

## Related Scenarios

- [Refactoring](./05-refactoring.md) - Single-function refactoring
- [Cross-Repo](./10-cross-repo.md) - Multi-repository changes
- [Tech Debt](./12-tech-debt.md) - Debt-driven refactoring
- [Code Review](./09-code-review.md) - Review mass changes
