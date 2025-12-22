"""SQL Semantic Prompts for DuckDB CPG queries.

Replaces CPGQL semantic prompts with SQL equivalents for DuckDB CPG.
Used by generator_agent.py for semantic (comment-based) queries.
"""

SQL_SEMANTIC_SYSTEM_PROMPT = """Generate SQL queries for DuckDB CPG that answer questions using code COMMENTS.

====================================================================================
DATABASE SCHEMA:
====================================================================================

Tables available:
- nodes_method: id, name, full_name, filename, line_number, line_number_end, signature
- nodes_comment: id, code, filename, line_number, containing_method_id
- nodes_call: id, name, code, filename, line_number, containing_method_id
- edges_call: src (nodes_call.id), dst (nodes_method.id)

====================================================================================
CRITICAL RULES - READ CAREFULLY:
====================================================================================

DO:
1. ALWAYS query nodes_comment to get explanations
2. Use ILIKE with % wildcards for fuzzy pattern matching
3. Study the RETRIEVED EXAMPLES - they show REAL methods that exist in the codebase
4. If question mentions a specific method name, use a FUZZY pattern to find similar methods
5. Return structured JSON results with method, file, line, and explanation fields

DON'T:
1. DON'T invent method names from the question text
2. DON'T use exact method names unless you see them in retrieved examples
3. DON'T use literal strings from questions as method names (e.g., "Cache Key: ...")
4. DON'T assume a method exists just because the question mentions it

====================================================================================
REQUIRED QUERY STRUCTURE:
====================================================================================

```sql
SELECT
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    COALESCE(
        (SELECT STRING_AGG(c.code, ' | ')
         FROM nodes_comment c
         WHERE c.filename = m.filename
           AND ABS(c.line_number - m.line_number) < 10),
        'No comments found'
    ) AS explanation
FROM nodes_method m
WHERE m.name ILIKE '%FUZZY_PATTERN%'
LIMIT 5;
```

====================================================================================
CORRECT EXAMPLES:
====================================================================================

Q: "What does timestamp2time_t do?"  <- May not exist exactly!
CORRECT:
```sql
SELECT
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    (SELECT STRING_AGG(c.code, ' | ')
     FROM nodes_comment c
     WHERE c.filename = m.filename
       AND ABS(c.line_number - m.line_number) < 10) AS explanation
FROM nodes_method m
WHERE m.name ILIKE '%timestamp%time%'
LIMIT 5;
```
WRONG: WHERE m.name = 'timestamp2time_t'  <- Too specific, may not exist!

Q: "What does replication worker do?"
CORRECT:
```sql
SELECT
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    (SELECT STRING_AGG(c.code, ' | ')
     FROM nodes_comment c
     WHERE c.filename = m.filename
       AND ABS(c.line_number - m.line_number) < 10) AS explanation
FROM nodes_method m
WHERE m.name ILIKE '%replicat%'
   OR m.name ILIKE '%worker%replicat%'
LIMIT 5;
```
WRONG: WHERE m.name ILIKE '%replication_worker%'  <- Too specific!

Q: "Find methods related to memory allocation"
CORRECT:
```sql
SELECT
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    (SELECT STRING_AGG(c.code, ' | ')
     FROM nodes_comment c
     WHERE c.filename = m.filename
       AND ABS(c.line_number - m.line_number) < 10) AS explanation
FROM nodes_method m
WHERE m.name ILIKE '%alloc%'
   OR m.name ILIKE '%memory%'
LIMIT 10;
```

====================================================================================
PATTERN MATCHING TIPS:
====================================================================================

- Break compound words: "timestamp2time" -> '%timestamp%time%'
- Use broader patterns: "replication_worker" -> '%replicat%' or '%worker%'
- For acronyms: "XLog" -> '%xlog%' or '%log%' (ILIKE is case-insensitive)
- When uncertain: use the most general part (e.g., '%alloc%' for allocation)
- Use OR patterns: WHERE m.name ILIKE '%read%buffer%' OR m.name ILIKE '%buffer%read%'
- Combine with filename: AND m.filename ILIKE '%specific_dir%'

====================================================================================
"""

SQL_SEMANTIC_USER_PROMPT = """Question: {question}

{retrieved_examples}

Generate SQL query following the template above. Include comment retrieval.
REMEMBER: Use ILIKE with % wildcards, DON'T invent exact method names!

Query:
```sql
"""


# Alternative prompt for simpler queries (just method lookup)
SQL_SIMPLE_SYSTEM_PROMPT = """Generate SQL queries for DuckDB CPG to find methods and their details.

Tables:
- nodes_method: id, name, full_name, filename, line_number, signature
- nodes_call: id, name, code, filename, line_number, containing_method_id
- edges_call: src (nodes_call.id), dst (nodes_method.id)

Rules:
- Use ILIKE with % for fuzzy matching (case-insensitive)
- Return name, filename, line_number at minimum
- Limit results to avoid overwhelming output

Example:
Q: "Find the main entry point"
```sql
SELECT name, full_name, filename, line_number
FROM nodes_method
WHERE name ILIKE '%main%'
   OR name ILIKE '%entry%'
LIMIT 10;
```
"""

SQL_SIMPLE_USER_PROMPT = """Question: {question}

Generate SQL query:
```sql
"""
