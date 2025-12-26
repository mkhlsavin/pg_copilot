# Scenario 07: Test Coverage

> QA engineer identifying untested code paths and prioritizing test development.

## Quick Start

```bash
# Select Test Coverage Scenario
/select 07
```

## Finding Coverage Gaps

### Identify Untested Functions

```
> What functions lack test coverage?

╭─────────────── Coverage Gaps ─────────────────╮
│ Functions without direct tests:               │
│                                               │
│ Critical (executor):                          │
│   - ExecParallelHashJoinNewBatch()            │
│   - ExecReScanGather()                        │
│                                               │
│ High priority (storage):                      │
│   - heap_lock_updated_tuple()                 │
│   - heap_abort_speculative()                  │
│                                               │
│ Total untested: 234 functions                 │
│ Coverage estimate: 78%                        │
╰───────────────────────────────────────────────╯
```

### Prioritize Testing

```
> Which untested functions have highest impact?

╭─────────────── Priority List ─────────────────╮
│ High Impact + No Tests:                       │
│                                               │
│ 1. heap_lock_updated_tuple()                  │
│    Impact: Transaction integrity              │
│    Callers: 23                                │
│                                               │
│ 2. ExecParallelHashJoinNewBatch()             │
│    Impact: Parallel query correctness         │
│    Callers: 8                                 │
│                                               │
│ 3. AtEOXact_RelationCache()                   │
│    Impact: Cache consistency                  │
│    Callers: 4                                 │
╰───────────────────────────────────────────────╯
```

### Find Untested Error Paths

```
> Find untested error handling paths
> Show entry points without tests
```

## Generating Test Cases

```
> Generate test cases for heap_insert

╭─────────────── Test Cases ────────────────────────────────╮
│                                                           │
│ Function: heap_insert()                                   │
│ File: src/backend/access/heap/heapam.c:2156               │
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
╰───────────────────────────────────────────────────────────╯
```

## Example Questions

- "What functions lack test coverage?"
- "Which critical functions need tests first?"
- "Find untested error handling paths"
- "Generate test cases for [function_name]"
- "What edge cases should I test in [function_name]?"

## Related Scenarios

- [Code Review](./09-code-review.md) - Review code changes
- [Refactoring](./05-refactoring.md) - Find dead code to remove
