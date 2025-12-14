# SQL Query Cookbook for DuckDB CPG

A practical collection of SQL queries for common code analysis tasks on DuckDB CPG.

## Table of Contents

1. [Method Queries](#method-queries)
2. [Call Analysis](#call-analysis)
3. [Control Flow](#control-flow)
4. [Data Flow](#data-flow)
5. [File Analysis](#file-analysis)
6. [Security Patterns](#security-patterns)
7. [Code Quality](#code-quality)
8. [Statistics](#statistics)
9. [Advanced Patterns](#advanced-patterns)
10. [SQL/PGQ Graph Queries](#sqlpgq-graph-queries)
11. [See Also](#see-also)

## Method Queries

### Find Method by Exact Name

```sql
SELECT id, name, full_name, filename, line_number, signature
FROM nodes_method
WHERE name = 'authenticate'
LIMIT 10;
```

### Find Methods by Pattern

```sql
SELECT id, name, full_name, filename, line_number
FROM nodes_method
WHERE name LIKE '%process%'
ORDER BY name
LIMIT 50;
```

### Methods by Signature Pattern

```sql
SELECT name, full_name, signature, filename
FROM nodes_method
WHERE signature LIKE '%char*%'  -- Methods taking char* parameter
ORDER BY name
LIMIT 100;
```

### External vs Internal Methods

```sql
-- External methods (from libraries)
SELECT name, full_name, COUNT(*) as count
FROM nodes_method
WHERE is_external = true
GROUP BY name, full_name
ORDER BY count DESC
LIMIT 20;

-- Internal methods (your code)
SELECT filename, COUNT(*) as method_count
FROM nodes_method
WHERE is_external = false
GROUP BY filename
ORDER BY method_count DESC
LIMIT 20;
```

### Methods by Line Count

```sql
SELECT
    name,
    filename,
    line_number,
    line_number_end,
    (line_number_end - line_number) as lines_of_code
FROM nodes_method
WHERE line_number_end IS NOT NULL
  AND (line_number_end - line_number) > 50  -- Long methods
ORDER BY lines_of_code DESC
LIMIT 20;
```

## Call Analysis

### Direct Callees (What does X call?)

```sql
SELECT DISTINCT
    callee.name,
    callee.full_name,
    callee.filename,
    callee.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.name = 'main'
ORDER BY callee.name
LIMIT 100;
```

### Direct Callers (Who calls X?)

```sql
SELECT DISTINCT
    caller.name,
    caller.full_name,
    caller.filename,
    caller.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method callee ON ec.dst = callee.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
WHERE callee.name = 'malloc'
ORDER BY caller.name
LIMIT 100;
```

### Call Chain (Transitive Callees)

```sql
WITH RECURSIVE call_chain AS (
    -- Base: direct calls from starting method
    SELECT
        ec.dst as method_id,
        1 as depth,
        m_start.name as start_method
    FROM edges_call ec
    JOIN nodes_call c ON ec.src = c.id
    JOIN nodes_method m_start ON c.method_full_name LIKE '%' || m_start.name || '%'
    WHERE m_start.name = 'main'

    UNION ALL

    -- Recursive: follow the chain
    SELECT
        ec2.dst,
        cc.depth + 1,
        cc.start_method
    FROM edges_call ec2
    JOIN nodes_call c2 ON ec2.src = c2.id
    JOIN nodes_method m2 ON c2.method_full_name LIKE '%' || m2.name || '%'
    JOIN call_chain cc ON m2.id = cc.method_id
    WHERE cc.depth < 5
)
SELECT DISTINCT
    m.name,
    m.full_name,
    MIN(cc.depth) as min_depth
FROM call_chain cc
JOIN nodes_method m ON cc.method_id = m.id
GROUP BY m.id, m.name, m.full_name
ORDER BY min_depth, m.name
LIMIT 100;
```

### Top Callers (Methods Making Most Calls)

```sql
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT c.id) as outgoing_calls
FROM nodes_method m
LEFT JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY outgoing_calls DESC
LIMIT 20;
```

### Top Callees (Most Called Methods)

```sql
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(ec.src) as incoming_calls
FROM nodes_method m
LEFT JOIN edges_call ec ON m.id = ec.dst
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY incoming_calls DESC
LIMIT 20;
```

### Call Pairs (Frequent Caller-Callee Patterns)

```sql
SELECT
    caller.name as caller,
    callee.name as callee,
    COUNT(*) as frequency
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
GROUP BY caller.name, callee.name
ORDER BY frequency DESC
LIMIT 50;
```

### Leaf Methods (No Outgoing Calls)

```sql
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE NOT EXISTS (
    SELECT 1
    FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
)
AND m.is_external = false
ORDER BY m.name
LIMIT 100;
```

### Root Methods (Not Called by Anyone)

```sql
SELECT
    m.name,
    m.full_name,
    m.filename,
    m.line_number
FROM nodes_method m
WHERE NOT EXISTS (
    SELECT 1
    FROM edges_call ec
    WHERE ec.dst = m.id
)
AND m.is_external = false
ORDER BY m.filename, m.line_number
LIMIT 100;
```

## Control Flow

### Methods with Branches

```sql
-- Find methods containing IF/SWITCH structures via AST
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT cs.id) as branch_count
FROM nodes_method m
JOIN edges_ast ast ON m.id = ast.src
JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE cs.control_structure_type IN ('IF', 'SWITCH')
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY branch_count DESC
LIMIT 20;
```

### Methods with Loops

```sql
-- Find methods containing loop structures via AST
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT cs.id) as loop_count
FROM nodes_method m
JOIN edges_ast ast ON m.id = ast.src
JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE cs.control_structure_type IN ('WHILE', 'FOR', 'DO')
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY loop_count DESC
LIMIT 20;
```

### Cyclomatic Complexity Approximation

```sql
-- Approximate complexity by counting control structures
SELECT
    m.name,
    m.filename,
    1 + COUNT(DISTINCT cs.id) as approx_complexity
FROM nodes_method m
LEFT JOIN edges_ast ast ON m.id = ast.src
LEFT JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE m.is_external = false
GROUP BY m.id, m.name, m.filename
ORDER BY approx_complexity DESC
LIMIT 30;
```

### Control Flow Graph Traversal (SQL/PGQ)

```sql
-- Follow CFG edges using property graph
FROM GRAPH_TABLE(cpg
    MATCH (start:METHOD)-[:CFG*1..10]->(node:CPG_NODE)
    WHERE start.name = 'process_request'
    COLUMNS (
        start.name AS method_name,
        node.id AS node_id,
        node.node_type
    )
)
LIMIT 100;
```

## Data Flow

### Variable Flow Paths

```sql
WITH RECURSIVE var_flow AS (
    -- Base: initial definitions
    SELECT src, dst, variable, 1 as depth
    FROM edges_reaching_def
    WHERE variable = 'password'

    UNION ALL

    -- Recursive: follow the flow
    SELECT erd.src, erd.dst, erd.variable, vf.depth + 1
    FROM edges_reaching_def erd
    JOIN var_flow vf ON erd.src = vf.dst
    WHERE vf.depth < 10
)
SELECT
    variable,
    COUNT(DISTINCT src) as definition_points,
    COUNT(DISTINCT dst) as use_points,
    MAX(depth) as max_depth
FROM var_flow
GROUP BY variable;
```

### Tainted Parameters

```sql
-- Methods receiving tainted input
SELECT DISTINCT
    m.name,
    m.full_name,
    p.name as parameter_name,
    p.type_full_name as parameter_type
FROM nodes_method m
JOIN nodes_param p ON p.method_full_name = m.full_name
WHERE p.name IN ('userInput', 'request', 'input', 'data')
ORDER BY m.name
LIMIT 50;
```

## File Analysis

### Methods Per File

```sql
SELECT
    filename,
    COUNT(*) as method_count,
    SUM(CASE WHEN is_external THEN 1 ELSE 0 END) as external_methods,
    SUM(CASE WHEN is_external THEN 0 ELSE 1 END) as internal_methods
FROM nodes_method
GROUP BY filename
ORDER BY method_count DESC
LIMIT 30;
```

### Files by Call Activity

```sql
SELECT
    m.filename,
    COUNT(DISTINCT c.id) as total_calls,
    COUNT(DISTINCT c.name) as unique_calls
FROM nodes_method m
JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.filename
ORDER BY total_calls DESC
LIMIT 20;
```

### Cross-File Calls

```sql
SELECT
    caller.filename as from_file,
    callee.filename as to_file,
    COUNT(*) as call_count
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.filename != callee.filename
GROUP BY caller.filename, callee.filename
ORDER BY call_count DESC
LIMIT 50;
```

## Security Patterns

### Memory Management Issues

```sql
-- Methods that malloc but don't free
SELECT DISTINCT m.name, m.full_name
FROM nodes_method m
WHERE EXISTS (
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'malloc'
)
AND NOT EXISTS (
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'free'
)
LIMIT 50;
```

### Dangerous Function Calls

```sql
SELECT
    m.name as caller,
    m.filename,
    c.name as dangerous_function,
    m.line_number
FROM nodes_call c
JOIN nodes_method m ON c.method_full_name LIKE '%' || m.name || '%'
WHERE c.name IN ('strcpy', 'sprintf', 'gets', 'system', 'eval')
ORDER BY m.filename, m.line_number
LIMIT 100;
```

### SQL Injection Candidates

```sql
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE EXISTS (
    -- Has SQL-related calls
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND (c.name LIKE '%query%' OR c.name LIKE '%execute%')
)
AND EXISTS (
    -- Receives user input
    SELECT 1 FROM nodes_param p
    WHERE p.method_full_name = m.full_name
      AND (p.name LIKE '%input%' OR p.name LIKE '%request%')
)
LIMIT 50;
```

### Authentication Bypass Candidates

```sql
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE m.name LIKE '%auth%'
  OR m.name LIKE '%login%'
  OR m.name LIKE '%verify%'
ORDER BY m.name
LIMIT 100;
```

## Code Quality

### God Methods (Too Long)

```sql
SELECT
    name,
    filename,
    line_number,
    line_number_end,
    (line_number_end - line_number) as loc
FROM nodes_method
WHERE line_number_end IS NOT NULL
  AND (line_number_end - line_number) > 100
ORDER BY loc DESC
LIMIT 20;
```

### High Fan-Out (Too Many Calls)

```sql
SELECT
    m.name,
    m.filename,
    COUNT(DISTINCT c.id) as fan_out
FROM nodes_method m
JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.id, m.name, m.filename
HAVING COUNT(DISTINCT c.id) > 10
ORDER BY fan_out DESC
LIMIT 20;
```

### High Fan-In (Too Many Callers)

```sql
SELECT
    m.name,
    m.filename,
    COUNT(DISTINCT ec.src) as fan_in
FROM nodes_method m
JOIN edges_call ec ON m.id = ec.dst
GROUP BY m.id, m.name, m.filename
HAVING COUNT(DISTINCT ec.src) > 10
ORDER BY fan_in DESC
LIMIT 20;
```

### Unused Methods (Potential Dead Code)

```sql
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE m.is_external = false
  AND NOT EXISTS (
      SELECT 1 FROM edges_call ec WHERE ec.dst = m.id
  )
  AND m.name NOT IN ('main', 'test%')  -- Exclude entry points
ORDER BY m.filename, m.name
LIMIT 100;
```

## Statistics

### CPG Overview

```sql
SELECT
    (SELECT COUNT(*) FROM nodes_method) as total_methods,
    (SELECT COUNT(*) FROM nodes_method WHERE is_external = false) as internal_methods,
    (SELECT COUNT(*) FROM nodes_call) as total_calls,
    (SELECT COUNT(*) FROM edges_call) as call_edges,
    (SELECT COUNT(DISTINCT filename) FROM nodes_method) as file_count;
```

### Call Distribution

```sql
SELECT
    call_count_bucket,
    COUNT(*) as methods_in_bucket
FROM (
    SELECT
        m.id,
        CASE
            WHEN call_count = 0 THEN '0 calls'
            WHEN call_count <= 5 THEN '1-5 calls'
            WHEN call_count <= 10 THEN '6-10 calls'
            WHEN call_count <= 20 THEN '11-20 calls'
            ELSE '20+ calls'
        END as call_count_bucket
    FROM nodes_method m
    LEFT JOIN (
        SELECT
            m2.id,
            COUNT(c.id) as call_count
        FROM nodes_method m2
        LEFT JOIN nodes_call c ON c.method_full_name LIKE '%' || m2.name || '%'
        GROUP BY m2.id
    ) counts ON m.id = counts.id
)
GROUP BY call_count_bucket
ORDER BY
    CASE call_count_bucket
        WHEN '0 calls' THEN 1
        WHEN '1-5 calls' THEN 2
        WHEN '6-10 calls' THEN 3
        WHEN '11-20 calls' THEN 4
        ELSE 5
    END;
```

### Language Distribution (by filename extension)

```sql
SELECT
    CASE
        WHEN filename LIKE '%.c' THEN 'C'
        WHEN filename LIKE '%.cpp' OR filename LIKE '%.cc' THEN 'C++'
        WHEN filename LIKE '%.java' THEN 'Java'
        WHEN filename LIKE '%.py' THEN 'Python'
        WHEN filename LIKE '%.js' THEN 'JavaScript'
        ELSE 'Other'
    END as language,
    COUNT(*) as method_count
FROM nodes_method
WHERE is_external = false
GROUP BY language
ORDER BY method_count DESC;
```

### Method Signature Complexity

```sql
SELECT
    m.name,
    m.signature,
    LENGTH(m.signature) as sig_length,
    (LENGTH(m.signature) - LENGTH(REPLACE(m.signature, ',', ''))) + 1 as param_count
FROM nodes_method m
WHERE m.signature IS NOT NULL
  AND m.is_external = false
ORDER BY param_count DESC, sig_length DESC
LIMIT 30;
```

## Advanced Patterns

### Find Method Chains (A → B → C)

```sql
WITH chain AS (
    SELECT
        caller.name as method_a,
        intermediate.name as method_b,
        callee.name as method_c
    FROM edges_call ec1
    JOIN nodes_call c1 ON ec1.src = c1.id
    JOIN nodes_method caller ON c1.method_full_name LIKE '%' || caller.name || '%'
    JOIN nodes_method intermediate ON ec1.dst = intermediate.id
    JOIN nodes_call c2 ON c2.method_full_name LIKE '%' || intermediate.name || '%'
    JOIN edges_call ec2 ON c2.id = ec2.src
    JOIN nodes_method callee ON ec2.dst = callee.id
    WHERE caller.name = 'main'
)
SELECT DISTINCT method_a, method_b, method_c
FROM chain
LIMIT 100;
```

### Connected Components (Method Clusters)

```sql
-- Find methods in same call graph
WITH RECURSIVE component AS (
    SELECT id, name, id as root
    FROM nodes_method
    WHERE name = 'main'

    UNION

    SELECT m.id, m.name, c.root
    FROM nodes_method m
    JOIN edges_call ec ON m.id = ec.dst OR m.id IN (
        SELECT m2.id FROM nodes_method m2
        JOIN nodes_call nc ON nc.method_full_name LIKE '%' || m2.name || '%'
        WHERE nc.id = ec.src
    )
    JOIN component c ON ec.dst = c.id OR ec.src = c.id
)
SELECT
    root,
    COUNT(DISTINCT id) as component_size,
    STRING_AGG(DISTINCT name, ', ') as methods
FROM component
GROUP BY root
ORDER BY component_size DESC
LIMIT 10;
```

## Usage Tips

1. **Always add LIMIT** to prevent returning millions of rows
2. **Use specific columns** instead of SELECT *
3. **Test on small datasets** first
4. **Add WHERE clauses** to filter irrelevant results
5. **Use EXPLAIN** to check query plans
6. **Monitor execution time** (should be < 100ms for most queries)

## Performance Notes

- Simple lookups: 1-3 ms
- JOINs (1-2 tables): 2-5 ms
- Aggregations: 4-8 ms
- Recursive CTEs: 10-50 ms (depends on depth)

All queries tested on sample database with 5 methods, 4 calls.
Performance scales sub-linearly with data size due to indexes.

## SQL/PGQ Graph Queries

DuckDB's SQL/PGQ extension enables intuitive graph traversal queries.

### Call Graph Traversal

```sql
-- Find all methods called by main (direct and indirect)
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[:CALLS*1..3]->(callee:METHOD)
    WHERE caller.name = 'main'
    COLUMNS (
        caller.name AS caller,
        callee.name AS callee,
        callee.filename
    )
)
LIMIT 100;
```

### Data Flow Analysis

```sql
-- Track data flow through reaching definitions
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL_NODE)
    WHERE src.name = 'user_input'
    COLUMNS (
        src.name AS source_var,
        sink.name AS sink_function,
        sink.line_number
    )
)
LIMIT 100;
```

### AST Traversal

```sql
-- Find all nodes under a method in AST
FROM GRAPH_TABLE(cpg
    MATCH (method:METHOD)-[:AST*1..5]->(child:CPG_NODE)
    WHERE method.name = 'authenticate'
    COLUMNS (
        method.name AS method_name,
        child.id AS child_id,
        child.node_type
    )
)
LIMIT 100;
```

### Type Hierarchy

```sql
-- Find inheritance relationships
FROM GRAPH_TABLE(cpg
    MATCH (derived:TYPE_DECL)-[:INHERITS_FROM]->(base:TYPE_NODE)
    COLUMNS (
        derived.name AS derived_type,
        base.full_name AS base_type
    )
)
```

---

## Next Steps

- Try these queries on your CPG database
- Modify parameters to match your needs
- Combine patterns for complex analysis
- Monitor performance and optimize as needed
- Add your own patterns to this cookbook!

---

## See Also

- [CPGQL to SQL Migration](./CPGQL_TO_SQL.md) - Translate Joern queries to SQL
- [CPG Export Guide](../guides/CPG_EXPORT.md) - Export CPG from Joern to DuckDB
- [Hypothesis System](./HYPOTHESIS_SYSTEM.md) - Security hypothesis generation
- [DuckDB SQL/PGQ Documentation](https://duckdb.org/docs/extensions/duckpgq)
- [CPG Specification v1.1](https://cpg.joern.io/)
