# Services Module

Core service layer providing CPG database queries, codebase statistics, and business logic for the RAG-CPGQL system.

## Overview

```
src/services/
├── cpg_query_service.py  # Main CPG query service
└── __init__.py           # Module exports
```

## CPGQueryService

The main service for querying the Code Property Graph database (DuckDB).

### Usage

```python
from src.services.cpg_query_service import CPGQueryService

# Context manager pattern
with CPGQueryService() as cpg:
    # Get method by name
    method = cpg.get_method('heap_insert')

    # Get method callers
    callers = cpg.get_callers('heap_insert')

    # Get method callees
    callees = cpg.get_callees('heap_insert')

    # Get codebase statistics
    stats = cpg.get_codebase_statistics()
```

### Key Methods

| Method | Description |
|--------|-------------|
| `get_method(name)` | Get method by name |
| `get_methods_by_pattern(pattern)` | Find methods matching regex |
| `get_callers(method)` | Get methods that call target |
| `get_callees(method)` | Get methods called by target |
| `get_dataflow(source, sink)` | Trace dataflow between points |
| `get_subsystems()` | Get codebase subsystems |
| `get_codebase_statistics()` | Get comprehensive stats |
| `execute_query(cpgql)` | Execute raw CPGQL query |

### Statistics

```python
stats = cpg.get_codebase_statistics()

# Returns:
{
    'total_methods': 52303,
    'total_calls': 111208,
    'total_files': 1234,
    'total_lines': 1500000,
    'todo_count': 150,
    'fixme_count': 45,
    'tech_debt_by_file': [...],
    'top_commented_files': [...],
}
```

### Subsystem Analysis

```python
subsystems = cpg.get_subsystems()

# Returns list of subsystems with method counts
[
    {'name': 'access', 'method_count': 500},
    {'name': 'executor', 'method_count': 800},
    {'name': 'storage', 'method_count': 1200},
]
```

### Call Graph Analysis

```python
# Get call chain
chain = cpg.get_call_chain('main', 'heap_insert', max_depth=5)

# Get all callers (transitive)
all_callers = cpg.get_transitive_callers('critical_function')
```

### Dataflow Queries

```python
# Find dataflow from user input to SQL execution
flows = cpg.get_dataflow(
    source='user_input',
    sink='ExecutorRun',
    include_paths=True
)
```

## Configuration

```yaml
services:
  cpg:
    db_path: ./cpg.duckdb
    cache_enabled: true
    cache_ttl: 3600
    max_results: 1000
```

## Database Schema

The CPG database contains these main tables:

| Table | Description |
|-------|-------------|
| `nodes_method` | Method definitions |
| `nodes_call` | Call site nodes |
| `nodes_identifier` | Identifiers |
| `nodes_literal` | Literal values |
| `nodes_comment` | Code comments |
| `edges_call` | Call relationships |
| `edges_cfg` | Control flow edges |
| `edges_ddg` | Data dependency edges |

## Error Handling

```python
from src.services.cpg_query_service import CPGQueryService, CPGError

try:
    with CPGQueryService() as cpg:
        result = cpg.execute_query("invalid query")
except CPGError as e:
    print(f"CPG query failed: {e}")
```

## Performance

- Query caching with configurable TTL
- Connection pooling for concurrent access
- Lazy loading of large result sets
- Index-optimized queries

## See Also

- `/src/execution/` - Joern CPG server queries
- `/src/retrieval/` - Vector store retrieval
- `/src/analysis/` - Advanced code analysis
