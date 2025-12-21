# Scenario 10: Cross-Repository Analysis

> Architect analyzing dependencies and impacts across multiple repositories.

## Quick Start

```bash
# Select Cross-Repository Scenario
/select 10
```

## Multi-Project Setup

### Configure Cross-Repo Analysis

```bash
# Add multiple projects
/project add postgres ./pg_cpg.duckdb c "PostgreSQL core"
/project add extension1 ./ext1_cpg.duckdb c "Extension module 1"
/project add extension2 ./ext2_cpg.duckdb c "Extension module 2"

# Enable cross-repo mode
/config cross_repo enabled true
```

## Dependency Analysis

### Cross-Repository Function Calls

```
> Find functions in extension1 that call PostgreSQL core

╭─────────────── Cross-Repo Dependencies ─────────────────────╮
│                                                              │
│  Extension1 → PostgreSQL Core Dependencies:                  │
│                                                              │
│  API Calls:                                                  │
│    palloc()           12 calls   Memory allocation           │
│    ereport()          8 calls    Error reporting             │
│    SPI_connect()      5 calls    SQL interface               │
│    GetCurrentTransactionId() 3 calls  Transaction access     │
│                                                              │
│  Direct Function Calls:                                      │
│    heap_insert()      4 calls    Tuple insertion             │
│    index_insert()     2 calls    Index maintenance           │
│                                                              │
│  Total dependencies: 34 function calls                       │
│  Risk level: MEDIUM (uses internal APIs)                     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### API Boundary Mapping

```
> Show API boundaries between projects

╭─────────────── API Boundaries ──────────────────────────────╮
│                                                              │
│  PostgreSQL Core Exports:                                    │
│                                                              │
│  Stable APIs (safe to use):                                  │
│    ├── SPI_* (12 functions)                                  │
│    ├── PG_FUNCTION_* macros                                  │
│    └── Standard extension hooks                              │
│                                                              │
│  Internal APIs (use with caution):                           │
│    ├── heap_* (23 functions)                                 │
│    ├── index_* (18 functions)                                │
│    └── buffer_* (15 functions)                               │
│                                                              │
│  Extension1 Usage:                                           │
│    Stable APIs: 67%                                          │
│    Internal APIs: 33%  ⚠️                                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Impact Analysis

### Breaking Change Detection

```
> What extensions would break if heap_insert signature changes?

╭─────────────── Breaking Change Impact ──────────────────────╮
│                                                              │
│  Target: heap_insert()                                       │
│  Signature: void heap_insert(Relation, HeapTuple, ...)       │
│                                                              │
│  Affected Extensions:                                        │
│                                                              │
│  🔴 extension1 (4 direct calls)                              │
│     Files: src/insert_handler.c, src/bulk_loader.c           │
│     Risk: HIGH - Core functionality                          │
│                                                              │
│  🔴 extension2 (2 direct calls)                              │
│     Files: src/custom_insert.c                               │
│     Risk: MEDIUM - Optional feature                          │
│                                                              │
│  Recommended Actions:                                        │
│    1. Provide wrapper function                               │
│    2. Deprecation period: 2 major versions                   │
│    3. Update extension documentation                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Version Compatibility Matrix

```
> Show compatibility matrix for extensions

╭─────────────── Compatibility Matrix ────────────────────────╮
│                                                              │
│  Extension Compatibility with PostgreSQL Versions:           │
│                                                              │
│  Extension      PG 14    PG 15    PG 16    Issues           │
│  ─────────────────────────────────────────────────────────── │
│  extension1     ✅       ✅       ⚠️       heap_insert       │
│  extension2     ✅       ✅       ✅       -                 │
│  extension3     ❌       ✅       ✅       Removed API       │
│                                                              │
│  Legend:                                                     │
│    ✅ Compatible  ⚠️ Needs update  ❌ Incompatible           │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Migration Planning

### Upgrade Path Analysis

```
> Plan migration from PG 15 to PG 16 for all extensions

╭─────────────── Migration Plan ──────────────────────────────╮
│                                                              │
│  Migration: PostgreSQL 15 → 16                               │
│                                                              │
│  Phase 1: API Updates Required                               │
│    extension1:                                               │
│      - Update heap_insert() calls (4 locations)              │
│      - Update buffer management (2 locations)                │
│                                                              │
│  Phase 2: Deprecated API Replacement                         │
│    extension3:                                               │
│      - Replace removed_api() with new_api()                  │
│                                                              │
│  Phase 3: Testing                                            │
│    - Run regression tests for all extensions                 │
│    - Verify cross-extension interactions                     │
│                                                              │
│  Estimated changes: 12 files, ~150 lines                     │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Find cross-repository dependencies"
- "What extensions use [function_name]?"
- "Show API boundaries between projects"
- "What would break if [function] changes?"
- "Plan migration for version upgrade"
- "Show compatibility matrix"

## CLI Commands

```bash
# Cross-repo analysis commands
python -m src.cli.cross_repo dependencies --from extension1 --to postgres
python -m src.cli.cross_repo impact --function heap_insert
python -m src.cli.cross_repo compatibility --versions "14,15,16"
```

## Related Scenarios

- [Architecture](./11-architecture.md) - Architectural analysis
- [Feature Development](./04-feature-development.md) - Understanding dependencies
- [Mass Refactoring](./13-mass-refactoring.md) - Large-scale changes
