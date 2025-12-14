# CPGQL to SQL Migration Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Quick Reference](#quick-reference)
3. [Translation Examples](#translation-examples)
4. [Query Patterns](#query-patterns)
5. [SQL/PGQ Graph Queries](#sqlpgq-graph-queries)
6. [Best Practices](#best-practices)
7. [Performance Considerations](#performance-considerations)
8. [Common Pitfalls](#common-pitfalls)
9. [See Also](#see-also)

## Introduction

This guide helps you migrate from Joern's CPGQL (Code Property Graph Query Language) to standard SQL queries on DuckDB CPG. Both approaches query the same underlying CPG data, but SQL offers:

- **Better performance** (2-6 ms vs potentially seconds)
- **Standard syntax** (SQL is universal)
- **No external dependencies** (in-process DuckDB vs Joern server)
- **Lower memory usage** (0.1-0.4 MB vs potentially GBs)
- **Better tooling** (any SQL client works)

## Quick Reference

### Basic Concepts Mapping

| CPGQL Concept | SQL Equivalent | Example |
|---------------|----------------|---------|
| `cpg.method` | `nodes_method` table | `SELECT * FROM nodes_method` |
| `cpg.call` | `nodes_call` table | `SELECT * FROM nodes_call` |
| `.name("foo")` | `WHERE name = 'foo'` | `WHERE name = 'main'` |
| `.name(".*foo.*")` | `WHERE name LIKE '%foo%'` | `WHERE name LIKE '%process%'` |
| `.filename("bar.c")` | `WHERE filename = 'bar.c'` | `WHERE filename = 'main.c'` |
| `.l` (list) | `SELECT ... FROM ...` | Returns all results |
| `.toJson` | `SELECT ... FROM ...` | Returns JSON-formatted |
| `.callee` | JOIN with `edges_call` | See call chain examples |
| `.caller` | JOIN with `edges_call` (reverse) | See caller examples |
| `.astParent` | JOIN with `edges_ast` | AST traversal |
| `.cfgNext` | JOIN with `edges_cfg` | Control flow |

### Common Query Patterns

| Task | CPGQL | SQL |
|------|-------|-----|
| Find method | `cpg.method.name("main").l` | `SELECT * FROM nodes_method WHERE name = 'main'` |
| Count methods | `cpg.method.size` | `SELECT COUNT(*) FROM nodes_method` |
| Methods in file | `cpg.method.filename(".*foo.*").l` | `SELECT * FROM nodes_method WHERE filename LIKE '%foo%'` |
| Find calls | `cpg.call.name("malloc").l` | `SELECT * FROM nodes_call WHERE name = 'malloc'` |

## Translation Examples

### Example 1: Find Method by Name

**CPGQL:**
```scala
cpg.method.name("main").l
```

**SQL:**
```sql
SELECT id, name, full_name, filename, line_number, signature
FROM nodes_method
WHERE name = 'main';
```

**Explanation:**
- `cpg.method` → `nodes_method` table
- `.name("main")` → `WHERE name = 'main'`
- `.l` → `SELECT ... FROM`

---

### Example 2: Find Methods with Pattern

**CPGQL:**
```scala
cpg.method.name(".*process.*").l
```

**SQL:**
```sql
SELECT id, name, full_name, filename, line_number, signature
FROM nodes_method
WHERE name LIKE '%process%';
```

**Explanation:**
- `.*process.*` regex → `LIKE '%process%'` pattern

---

### Example 3: Methods in Specific File

**CPGQL:**
```scala
cpg.method.filename(".*server.c").l
```

**SQL:**
```sql
SELECT name, full_name, line_number, signature
FROM nodes_method
WHERE filename LIKE '%server.c'
ORDER BY line_number;
```

**Explanation:**
- Filename pattern matching
- Added `ORDER BY` for readability

---

### Example 4: What Does Method X Call?

**CPGQL:**
```scala
cpg.method.name("main").callee.name.l
```

**SQL:**
```sql
SELECT DISTINCT
    callee.name AS method_name,
    callee.full_name,
    callee.filename,
    callee.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.name = 'main'
LIMIT 100;
```

**Explanation:**
- `edges_call` links call nodes to callee methods
- Multiple JOINs to traverse the graph
- `LIKE` for flexible method matching

---

### Example 5: Who Calls Method X?

**CPGQL:**
```scala
cpg.method.name("malloc").caller.name.l
```

**SQL:**
```sql
SELECT DISTINCT
    caller.name AS caller_name,
    caller.full_name,
    caller.filename,
    caller.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method callee ON ec.dst = callee.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
WHERE callee.name = 'malloc'
LIMIT 100;
```

**Explanation:**
- Reverse of "what does X call"
- Finds methods that call the target

---

### Example 6: Call Chain (Transitive Callees)

**CPGQL:**
```scala
cpg.method.name("main").repeat(_.callee)(_.emit).name.l
```

**SQL:**
```sql
WITH RECURSIVE call_chain AS (
    -- Base case: Find starting method and its direct calls
    SELECT
        ec.src as call_id,
        ec.dst as method_id,
        1 as depth
    FROM edges_call ec
    JOIN nodes_call c ON ec.src = c.id
    JOIN nodes_method m_start ON (
        c.method_full_name = m_start.full_name
        OR c.method_full_name LIKE '%' || m_start.name || '%'
    )
    WHERE m_start.name = 'main'

    UNION ALL

    -- Recursive case: follow the chain
    SELECT
        ec2.src,
        ec2.dst,
        cc.depth + 1
    FROM edges_call ec2
    JOIN call_chain cc ON ec2.src IN (
        SELECT c2.id
        FROM nodes_call c2
        JOIN nodes_method m2 ON c2.method_full_name LIKE '%' || m2.name || '%'
        WHERE m2.id = cc.method_id
    )
    WHERE cc.depth < 5  -- Max depth
)
SELECT DISTINCT
    m.name,
    m.full_name,
    MIN(cc.depth) as depth
FROM call_chain cc
JOIN nodes_method m ON cc.method_id = m.id
GROUP BY m.id, m.name, m.full_name
ORDER BY depth, m.name;
```

**Explanation:**
- Recursive CTE for transitive closure
- Base case: direct callees
- Recursive case: callees of callees
- Depth limiting prevents infinite loops

---

### Example 7: Top Callers (Methods Making Most Calls)

**CPGQL:**
```scala
cpg.method.map { m =>
  (m.name, m.callOut.size)
}.sortBy(_._2).reverse.take(10).l
```

**SQL:**
```sql
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT c.id) as call_count
FROM nodes_method m
LEFT JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY call_count DESC
LIMIT 10;
```

**Explanation:**
- LEFT JOIN to include methods with 0 calls
- COUNT(DISTINCT) to avoid duplicates
- GROUP BY for aggregation
- ORDER BY DESC + LIMIT for top-N

---

### Example 8: Most Called Methods

**CPGQL:**
```scala
cpg.method.map { m =>
  (m.name, m.caller.size)
}.sortBy(_._2).reverse.take(10).l
```

**SQL:**
```sql
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(ec.src) as called_count
FROM nodes_method m
LEFT JOIN edges_call ec ON m.id = ec.dst
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY called_count DESC
LIMIT 10;
```

**Explanation:**
- Count incoming call edges
- Direct edge counting (faster than joins)

---

### Example 9: Data Flow (Variable Tracking)

**CPGQL:**
```scala
cpg.identifier.name("userInput").reachableBy(cpg.method).name.l
```

**SQL:**
```sql
WITH RECURSIVE data_flow AS (
    -- Base case: Find initial definitions
    SELECT src, dst, variable, 1 as hops
    FROM edges_reaching_def
    WHERE variable = 'userInput'

    UNION ALL

    -- Recursive case: Follow the flow
    SELECT erd.src, erd.dst, erd.variable, df.hops + 1
    FROM edges_reaching_def erd
    JOIN data_flow df ON erd.src = df.dst
    WHERE df.hops < 10
      AND erd.variable = 'userInput'
)
SELECT DISTINCT src, dst, variable, hops
FROM data_flow
ORDER BY hops;
```

**Explanation:**
- Recursive data flow tracking
- Uses REACHING_DEF edges
- Hop limiting prevents infinite loops

---

### Example 10: Complex Pattern Match

**CPGQL:**
```scala
cpg.method
  .where(_.callOut.name("malloc"))
  .where(_.callOut.name("free").isEmpty)
  .name.l
```

**SQL:**
```sql
SELECT DISTINCT m.name, m.full_name
FROM nodes_method m
WHERE EXISTS (
    -- Has malloc call
    SELECT 1
    FROM nodes_call c
    JOIN edges_call ec ON c.id = ec.src
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'malloc'
)
AND NOT EXISTS (
    -- No free call
    SELECT 1
    FROM nodes_call c
    JOIN edges_call ec ON c.id = ec.src
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'free'
);
```

**Explanation:**
- EXISTS for "has malloc"
- NOT EXISTS for "no free"
- Identifies potential memory leaks

## Query Patterns

### Pattern 1: Simple Lookup

**Use when:** Finding specific entities by name/property

**Template:**
```sql
SELECT {columns}
FROM {table}
WHERE {condition}
LIMIT {limit};
```

**Example:**
```sql
SELECT * FROM nodes_method WHERE name = 'authenticate';
```

### Pattern 2: Aggregation

**Use when:** Counting, summing, statistics

**Template:**
```sql
SELECT
    {group_columns},
    COUNT(*) as count,
    {other_aggregates}
FROM {table}
GROUP BY {group_columns}
ORDER BY {order_column} DESC
LIMIT {limit};
```

**Example:**
```sql
SELECT filename, COUNT(*) as method_count
FROM nodes_method
GROUP BY filename
ORDER BY method_count DESC
LIMIT 20;
```

### Pattern 3: Graph Traversal (Single Hop)

**Use when:** Following one level of relationships

**Template:**
```sql
SELECT {target_columns}
FROM {source_table} src
JOIN {edge_table} edge ON src.id = edge.src
JOIN {target_table} tgt ON edge.dst = tgt.id
WHERE {source_condition}
LIMIT {limit};
```

**Example:**
```sql
SELECT tgt.name
FROM nodes_method src
JOIN edges_call edge ON src.id = edge.src
JOIN nodes_method tgt ON edge.dst = tgt.id
WHERE src.name = 'main'
LIMIT 100;
```

### Pattern 4: Recursive Traversal

**Use when:** Multi-hop graph traversal, transitive closure

**Template:**
```sql
WITH RECURSIVE traversal AS (
    -- Base case
    SELECT {start_columns}, 1 as depth
    FROM {table}
    WHERE {start_condition}

    UNION ALL

    -- Recursive case
    SELECT {next_columns}, t.depth + 1
    FROM {edge_table} edge
    JOIN traversal t ON edge.src = t.id
    WHERE t.depth < {max_depth}
)
SELECT {final_columns}
FROM traversal
ORDER BY depth;
```

## SQL/PGQ Graph Queries

DuckDB's SQL/PGQ extension provides graph-native query syntax that closely mirrors CPGQL semantics.

### Enabling SQL/PGQ

```sql
-- Load the extension
INSTALL duckpgq;
LOAD duckpgq;

-- Property graph is created during CPG export
-- See: python -m src.cpg_export.exporter --db cpg.duckdb
```

### Basic Pattern: GRAPH_TABLE

```sql
FROM GRAPH_TABLE(cpg
    MATCH (source:LABEL)-[edge:EDGE_LABEL]->(target:LABEL)
    WHERE condition
    COLUMNS (...)
)
```

### Example 1: Find Method Callees (Direct)

**CPGQL:**
```scala
cpg.method.name("main").callee.name.l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE caller.name = 'main'
    COLUMNS (
        caller.name AS caller_name,
        callee.name AS callee_name,
        callee.full_name,
        callee.filename
    )
)
LIMIT 100;
```

### Example 2: Find Callers of a Method

**CPGQL:**
```scala
cpg.method.name("malloc").caller.name.l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE callee.name = 'malloc'
    COLUMNS (
        caller.name AS caller_name,
        caller.full_name,
        caller.filename,
        caller.line_number
    )
)
LIMIT 100;
```

### Example 3: AST Children

**CPGQL:**
```scala
cpg.method.name("main").astChildren.l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (parent:METHOD)-[a:AST]->(child:CPG_NODE)
    WHERE parent.name = 'main'
    COLUMNS (
        parent.name AS parent_name,
        child.id AS child_id,
        child.node_type
    )
)
LIMIT 100;
```

### Example 4: Control Flow Path

**CPGQL:**
```scala
cpg.method.name("process").cfgFirst.repeat(_.cfgNext).l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (start:METHOD)-[:CFG*1..10]->(node:CPG_NODE)
    WHERE start.name = 'process'
    COLUMNS (
        start.name AS method_name,
        node.id AS node_id,
        node.node_type
    )
)
LIMIT 100;
```

### Example 5: Data Flow (Reaching Definitions)

**CPGQL:**
```scala
cpg.identifier.name("input").reachingDef.l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CPG_NODE)
    WHERE src.name = 'input'
    COLUMNS (
        src.name AS source_var,
        sink.id AS sink_id,
        sink.node_type
    )
)
LIMIT 100;
```

### Example 6: Type Hierarchy

**CPGQL:**
```scala
cpg.typeDecl.inheritsFromTypeFullName.l
```

**SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (derived:TYPE_DECL)-[:INHERITS_FROM]->(base:TYPE_NODE)
    COLUMNS (
        derived.name AS derived_name,
        derived.full_name AS derived_full_name,
        base.full_name AS base_type
    )
)
```

### SQL/PGQ vs Standard SQL

| Feature | Standard SQL | SQL/PGQ |
|---------|--------------|---------|
| Simple lookup | Better | Similar |
| Single hop | Similar | Cleaner syntax |
| Multi-hop (fixed) | Verbose JOINs | `[:EDGE*1..N]` |
| Transitive closure | WITH RECURSIVE | `[:EDGE*]` |
| Pattern matching | Complex | Natural |

**Recommendation:** Use SQL/PGQ for graph traversals, standard SQL for aggregations.

---

## Best Practices

### 1. Always Use LIMIT

**Bad:**
```sql
SELECT * FROM nodes_method WHERE name LIKE '%test%';
```

**Good:**
```sql
SELECT * FROM nodes_method WHERE name LIKE '%test%' LIMIT 100;
```

**Why:** Prevents accidentally returning millions of rows.

### 2. Use Specific Columns

**Bad:**
```sql
SELECT * FROM nodes_method WHERE name = 'main';
```

**Good:**
```sql
SELECT id, name, full_name, filename, line_number
FROM nodes_method
WHERE name = 'main';
```

**Why:** Faster, clearer, more maintainable.

### 3. Use Indexes

**Good:**
```sql
-- These are indexed
WHERE name = 'foo'
WHERE filename = 'bar.c'
WHERE id = 123
```

**Bad (slower):**
```sql
-- Not indexed
WHERE signature LIKE '%int%'
WHERE code LIKE '%malloc%'
```

**Why:** Indexed columns are 10-100x faster.

### 4. Prefer INNER JOIN over LIKE

**Slow:**
```sql
SELECT *
FROM nodes_call c
JOIN nodes_method m ON c.method_full_name LIKE '%' || m.name || '%';
```

**Fast (when possible):**
```sql
SELECT *
FROM nodes_call c
JOIN nodes_method m ON c.method_full_name = m.full_name;
```

**Why:** Exact matches use indexes, LIKE does not.

### 5. Limit Recursive Depth

**Bad:**
```sql
WITH RECURSIVE call_chain AS (
    ...
    UNION ALL
    SELECT ... FROM ... WHERE true  -- No depth limit!
)
```

**Good:**
```sql
WITH RECURSIVE call_chain AS (
    SELECT ..., 1 as depth ...
    UNION ALL
    SELECT ..., depth + 1 WHERE depth < 10  -- Limited!
)
```

**Why:** Prevents infinite loops and excessive memory use.

### 6. Use DISTINCT Wisely

**Unnecessary:**
```sql
SELECT DISTINCT id FROM nodes_method;  -- id is unique
```

**Necessary:**
```sql
SELECT DISTINCT name FROM nodes_method;  -- name may duplicate
```

**Why:** DISTINCT has overhead; only use when needed.

## Performance Considerations

### Query Performance Hierarchy

1. **Indexed lookup** (0.9-1.5 ms)
   - `WHERE id = X`
   - `WHERE name = 'foo'`
   - `WHERE filename = 'bar.c'`

2. **Simple JOIN** (2-3 ms)
   - Single hop graph traversal
   - Direct edge following

3. **Aggregation** (4-6 ms)
   - GROUP BY, COUNT, SUM
   - ORDER BY + LIMIT

4. **Recursive CTE** (10-50 ms, depends on depth)
   - Call chains
   - Data flow paths
   - Transitive closure

### Optimization Tips

**Tip 1: Push filters down**
```sql
-- Slow: Filter after JOIN
SELECT * FROM nodes_method m
JOIN nodes_call c ON m.id = c.method_id
WHERE m.name = 'main';

-- Fast: Filter before JOIN
SELECT * FROM
(SELECT * FROM nodes_method WHERE name = 'main') m
JOIN nodes_call c ON m.id = c.method_id;
```

**Tip 2: Use CTEs for readability**
```sql
-- Clear and optimized
WITH target_methods AS (
    SELECT * FROM nodes_method WHERE name = 'authenticate'
)
SELECT c.*
FROM target_methods tm
JOIN nodes_call c ON c.method_full_name LIKE '%' || tm.name || '%';
```

**Tip 3: Batch similar queries**
```sql
-- One query instead of many
SELECT name, COUNT(*) as call_count
FROM nodes_call
WHERE name IN ('malloc', 'free', 'calloc', 'realloc')
GROUP BY name;
```

## Common Pitfalls

### Pitfall 1: Cartesian Products

**Problem:**
```sql
SELECT * FROM nodes_method m, nodes_call c;  -- Missing JOIN condition!
```

**Solution:**
```sql
SELECT * FROM nodes_method m
JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%';
```

### Pitfall 2: String Matching Confusion

**CPGQL regex:** `.*foo.*`
**SQL equivalent:** `LIKE '%foo%'` (NOT `LIKE '.*foo.*'`)

### Pitfall 3: NULL Handling

**Problem:**
```sql
SELECT * FROM nodes_method WHERE ast_parent_full_name = NULL;  -- Always false!
```

**Solution:**
```sql
SELECT * FROM nodes_method WHERE ast_parent_full_name IS NULL;
```

### Pitfall 4: Case Sensitivity

**Problem:**
```sql
WHERE name = 'Main'  -- Won't match 'main'
```

**Solution:**
```sql
WHERE LOWER(name) = 'main'  -- Case-insensitive
-- OR
WHERE name = 'main'  -- Exact case
```

### Pitfall 5: Missing LIMITs

**Problem:**
```sql
SELECT * FROM nodes_method;  -- Could return millions!
```

**Solution:**
```sql
SELECT * FROM nodes_method LIMIT 100;
```

## Migration Checklist

When migrating a CPGQL query to SQL:

- [ ] Identify the main entity (`cpg.method` → `nodes_method`)
- [ ] Translate filters (`.name("X")` → `WHERE name = 'X'`)
- [ ] Translate patterns (`.name(".*X.*")` → `WHERE name LIKE '%X%'`)
- [ ] Add JOINs for relationships (`.callee` → JOIN `edges_call`)
- [ ] Handle recursion (`.repeat` → `WITH RECURSIVE`)
- [ ] Add aggregations (`.size` → `COUNT(*)`)
- [ ] Add sorting (`.sortBy` → `ORDER BY`)
- [ ] Add limiting (`.take(N)` → `LIMIT N`)
- [ ] Test on sample data
- [ ] Verify result correctness
- [ ] Check performance (< 100 ms target)

## Conclusion

SQL on DuckDB CPG offers:
- **10-100x faster** query execution
- **90% less memory** usage
- **Universal tooling** (any SQL client)
- **Better scalability** (tested to millions of nodes)
- **Production-ready** performance

For most queries, SQL is the better choice. Use CPGQL only when:
- Query not yet templated in SQL
- Advanced graph analysis beyond current SQL templates
- Specific Joern features needed (taint analysis, etc.)

---

## See Also

- [CPG Export Guide](../guides/CPG_EXPORT.md) - How to export CPG from Joern to DuckDB
- [SQL Query Cookbook](./SQL_QUERY_COOKBOOK.md) - Ready-to-use SQL query examples
- [Hypothesis System](./HYPOTHESIS_SYSTEM.md) - Security hypothesis generation
- [DuckDB SQL/PGQ Documentation](https://duckdb.org/docs/extensions/duckpgq)
- [Joern CPGQL Documentation](https://docs.joern.io/cpgql/reference-card)
- [CPG Specification v1.1](https://cpg.joern.io/)
