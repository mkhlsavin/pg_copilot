# Generation Module

This module handles SQL query generation for the DuckDB CPG using Large Language Models.

## Overview

The generation pipeline converts user questions into valid SQL queries:

```
User Question -> Context Retrieval -> Prompt Builder -> LLM Inference -> SQL Query
```

## Components

### 1. SQL Query Generator (`sql_query_generator.py`)

**Purpose**: Generates SQL queries for the DuckDB Code Property Graph.

**Supported Query Types**:
- `find_method` - Find methods by name pattern
- `find_callees` - Find functions called by a method
- `find_callers` - Find functions that call a method
- `call_chain` - Analyze call chains (recursive)
- `top_callers` - Find most frequently called functions
- `top_callees` - Find functions with most calls
- `data_flow` - Trace data flow paths
- `pattern_match` - Complex pattern matching

**Usage**:
```python
from src.generation.sql_query_generator import SQLQueryGenerator
from src.llm.llm_interface_compat import LLMInterface

llm = LLMInterface()
generator = SQLQueryGenerator(llm=llm)

result = generator.generate(
    question="What functions does heap_insert call?",
    context=retrieved_examples
)

print(result['sql'])
print(result['query_type'])
```

**Example Output**:
```sql
SELECT DISTINCT callee.name, callee.full_name, callee.file_name
FROM nodes caller
JOIN call_graph cg ON caller.id = cg.caller_id
JOIN nodes callee ON cg.callee_id = callee.id
WHERE caller.name = 'heap_insert'
ORDER BY callee.name;
```

### 2. Prompt Templates (`prompts.py`)

**Purpose**: Manages prompt templates for SQL query generation.

**Template Components**:

1. **System Prompt**: Defines LLM role as SQL/CPG expert
2. **Schema Context**: DuckDB table definitions
3. **SQL Examples**: Few-shot examples from ChromaDB
4. **User Question**: The query to answer

**Prompt Structure**:
```
[System Prompt]
You are an expert at generating SQL queries for Code Property Graphs...

[Schema Section]
Available tables: nodes, edges, call_graph, ...

[Examples Section]
Similar queries:
Q: Find all methods with "lock" in name
SQL: SELECT DISTINCT n.name FROM nodes n WHERE n.label = 'METHOD' AND n.name LIKE '%lock%'

[User Question]
Question: {user_question}

[Instructions]
Generate a valid SQL query...
```

## DuckDB CPG Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `nodes` | CPG nodes (methods, calls, identifiers) |
| `edges` | CPG edges (AST, CFG, call relationships) |
| `call_graph` | Pre-computed caller/callee relationships |
| `tags` | Semantic tags for methods |

### Key Columns

**nodes**:
- `id` - Unique identifier
- `label` - Node type (METHOD, CALL, IDENTIFIER, etc.)
- `name` - Short name
- `full_name` - Fully qualified name
- `file_name` - Source file
- `line_number` - Line in source

**call_graph**:
- `caller_id` - Calling function ID
- `callee_id` - Called function ID
- `call_site_id` - Call location

## Query Templates

### Find Method
```sql
SELECT DISTINCT n.name, n.full_name, n.file_name, n.line_number
FROM nodes n
WHERE n.label = 'METHOD'
  AND n.name LIKE '%{pattern}%'
ORDER BY n.name;
```

### Find Callees
```sql
SELECT DISTINCT callee.name, callee.full_name
FROM nodes caller
JOIN call_graph cg ON caller.id = cg.caller_id
JOIN nodes callee ON cg.callee_id = callee.id
WHERE caller.name = '{method_name}'
ORDER BY callee.name;
```

### Find Callers
```sql
SELECT DISTINCT caller.name, caller.full_name
FROM nodes callee
JOIN call_graph cg ON callee.id = cg.callee_id
JOIN nodes caller ON cg.caller_id = caller.id
WHERE callee.name = '{method_name}'
ORDER BY caller.name;
```

### Call Chain (Recursive)
```sql
WITH RECURSIVE call_chain AS (
    SELECT caller_id, callee_id, 1 as depth,
           ARRAY[caller_id] as path
    FROM call_graph
    WHERE caller_id = (SELECT id FROM nodes WHERE name = '{start_method}' LIMIT 1)

    UNION ALL

    SELECT cg.caller_id, cg.callee_id, cc.depth + 1,
           cc.path || cg.callee_id
    FROM call_graph cg
    JOIN call_chain cc ON cg.caller_id = cc.callee_id
    WHERE cc.depth < {max_depth}
      AND NOT cg.callee_id = ANY(cc.path)
)
SELECT DISTINCT n.name, cc.depth
FROM call_chain cc
JOIN nodes n ON cc.callee_id = n.id
ORDER BY cc.depth, n.name;
```

## ChromaDB Integration

SQL examples are stored in ChromaDB for few-shot learning:

**Collection**: `sql_examples`

**Document Format**:
```json
{
  "question": "What functions does main call?",
  "query_type": "find_callees",
  "sql": "SELECT DISTINCT callee.name...",
  "category": "call_graph",
  "complexity": "simple"
}
```

**Retrieval**:
```python
from src.retrieval.vector_store_real import VectorStoreReal

store = VectorStoreReal()
examples = store.retrieve_sql(
    query="find callees of heap_insert",
    query_type="find_callees",
    top_k=5
)
```

## Performance Metrics

### Generation Latency
- **Prompt Building**: ~50ms
- **LLM Inference**: 2-5 seconds
- **Total**: ~2-6 seconds per query

### Generation Quality
- **Syntax Validity**: 98%+
- **Execution Success**: 95%+
- **First-Try Success**: 92%+

## Configuration

### Generation Settings (`config.yaml`)

```yaml
generation:
  model:
    provider: yandex
    temperature: 0.1
    max_tokens: 2048

  prompts:
    max_sql_examples: 5
    include_schema: true

  validation:
    check_syntax: true
    check_tables: true
```

## Dependencies

- `src.llm` - LLM interface (Yandex, OpenAI, local)
- `src.retrieval` - ChromaDB vector store
- `logging` - Generation logging

## See Also

- `/src/retrieval/vector_store_real.py` - SQL example retrieval
- `/src/workflow/` - LangGraph integration
- `/data/sql_examples.json` - SQL example dataset
