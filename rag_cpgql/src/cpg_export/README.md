# CPG Export Module

Tools for exporting Code Property Graphs (CPG) from Joern to DuckDB with full CPG Spec v1.1 compliance.

## Overview

This module provides a complete pipeline for:
1. Exporting CPG from Joern server to DuckDB
2. Querying CPG via SQL and SQL/PGQ
3. Adding semantic embeddings for hybrid search
4. Incremental updates via git diff
5. **Validation of export completeness**

## Module Architecture

```
src/cpg_export/
├── __init__.py              # Public API
├── exporter.py              # Main JoernToDuckDBExporter class (recommended)
├── schema.py                # Table and index definitions
├── progress.py              # Checkpoint/resume functionality
├── validation.py            # Export validation (Joern vs DuckDB)
├── nodes/                   # Node exporters
│   ├── __init__.py
│   ├── base.py              # NodeExporter base class
│   ├── core.py              # METHOD, CALL, IDENTIFIER, LITERAL, etc.
│   ├── structure.py         # FILE, NAMESPACE, TYPE_DECL, MEMBER
│   └── supplementary.py     # MODIFIER, ANNOTATION, BINDING, etc.
├── edges/                   # Edge exporters
│   ├── __init__.py
│   ├── base.py              # EdgeExporter base class
│   ├── core.py              # AST, CFG, CALL, REF, ARGUMENT
│   └── analysis.py          # CDG, REACHING_DEF, DOMINATE, EVAL_TYPE
├── duckdb_cpg_client_v2.py  # Query client for DuckDB
├── duckdb_cpg_schema.md     # CPG Spec v1.1 schema documentation
├── add_vector_embeddings.py # Vector embeddings for semantic search
├── export_tags.py           # Tag export for CPG enrichment
├── incremental_exporter.py  # Incremental export via git diff
├── migrations/              # SQL migrations
└── joern_to_duckdb_v2.py    # Legacy monolithic exporter (backward compat)
```

---

## Quick Start

### Python API (Recommended)

```python
from src.cpg_export import JoernToDuckDBExporter

# Create exporter
exporter = JoernToDuckDBExporter(
    server_endpoint="localhost:8080",
    workspace="myproject.cpg",
    db_path="cpg.duckdb",
    batch_size=10000
)

# Full export with automatic validation
results = exporter.export_full_cpg()

# Results contain:
# - node_stats: Dict[entity_type, count]
# - edge_stats: Dict[entity_type, count]
# - validation: Dict of ValidationResult objects

# Check if export was complete
if results['validation']:
    from src.cpg_export import ExportValidator
    validator = ExportValidator(exporter.joern_client, exporter.conn)
    summary = validator.get_summary(results['validation'])
    print(f"Export complete: {summary['all_valid']}")
    print(f"Total nodes: {summary['total_duckdb']}")
```

### CLI Usage

```bash
# Full export with validation
python -m src.cpg_export.exporter \
    --endpoint localhost:8080 \
    --workspace myproject.cpg \
    --db cpg.duckdb

# Resume interrupted export (default behavior)
python -m src.cpg_export.exporter --db cpg.duckdb

# Force recreate all tables
python -m src.cpg_export.exporter --db cpg.duckdb --force

# Disable resume (start fresh)
python -m src.cpg_export.exporter --db cpg.duckdb --no-resume

# Skip validation at the end
python -m src.cpg_export.exporter --db cpg.duckdb --skip-validation

# Show export status only
python -m src.cpg_export.exporter --db cpg.duckdb --status

# Run validation only
python -m src.cpg_export.exporter --db cpg.duckdb --validate-only

# Limit nodes per type (for testing)
python -m src.cpg_export.exporter --db cpg.duckdb --limit 1000

# Custom batch size
python -m src.cpg_export.exporter --db cpg.duckdb --batch-size 5000
```

### CLI Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--endpoint` | localhost:8080 | Joern server endpoint |
| `--workspace` | pg17_full.cpg | Workspace/CPG name |
| `--db` | cpg.duckdb | DuckDB database path |
| `--batch-size` | 10000 | Batch size for export |
| `--limit` | None | Limit nodes per type (testing) |
| `--force` | False | Force recreate all tables |
| `--no-resume` | False | Disable checkpoint resume |
| `--skip-validation` | False | Skip validation at end |
| `--status` | False | Show status only |
| `--validate-only` | False | Run validation only |

---

## Export Features

### Checkpoint/Resume

The exporter automatically saves progress after each batch. If interrupted, it resumes from the last checkpoint:

```python
# Progress is tracked in the export_progress table
exporter.progress_tracker.print_status()
```

```sql
-- Check export progress
SELECT entity_type, status, exported_count, last_offset
FROM export_progress
ORDER BY entity_type;
```

### Export Validation

After export completes, validation compares Joern counts with DuckDB counts:

```
======================================================================
CPG EXPORT VALIDATION REPORT
======================================================================
[OK]       nodes_method                      1234 /     1234 (100.0%)
[OK]       nodes_call                       45678 /    45678 (100.0%)
[MISSING]  nodes_identifier                 89000 /    89012 ( 99.9%)
----------------------------------------------------------------------
TOTAL                                      134912 /   134924 ( 99.9%)
======================================================================
[WARNING] 12 RECORDS MISSING - CHECK LOGS
======================================================================
```

### Supported Node Types (22 types)

**Core Nodes:**
- METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE

**Structure Nodes:**
- FILE, NAMESPACE, NAMESPACE_BLOCK, MEMBER, TYPE, TYPE_DECL, COMMENT

**Supplementary Nodes (P1-P3):**
- METHOD_PARAMETER_OUT, METHOD_RETURN, FIELD_IDENTIFIER
- TYPE_ARGUMENT, TYPE_PARAMETER, JUMP_LABEL, JUMP_TARGET
- METHOD_REF, MODIFIER, TYPE_REF, UNKNOWN, BINDING, ANNOTATION

### Supported Edge Types (20 types)

**Core Edges:**
- AST, CFG, CALL, REF, ARGUMENT, RECEIVER, CONDITION, SOURCE_FILE

**Analysis Edges:**
- REACHING_DEF, DOMINATE, POST_DOMINATE, CDG, CONTAINS, EVAL_TYPE
- INHERITS_FROM, ALIAS_OF, BINDS_TO, PARAMETER_LINK, TAGGED_BY, BINDS

---

## Programmatic Usage

### Export Only Nodes

```python
from src.cpg_export import JoernToDuckDBExporter

exporter = JoernToDuckDBExporter(...)
exporter.connect_db()

# Export only nodes (no edges)
node_stats = exporter.export_nodes_only(limit=10000)
print(f"Exported nodes: {node_stats}")
```

### Export Only Edges

```python
# Export only edges (assumes nodes exist)
edge_stats = exporter.export_edges_only()
print(f"Exported edges: {edge_stats}")
```

### Validate Existing Database

```python
from src.cpg_export import validate_export
from src.execution.joern_client import JoernClient
import duckdb

joern_client = JoernClient("localhost:8080", "myproject.cpg")
conn = duckdb.connect("cpg.duckdb")

results = validate_export(joern_client, conn, print_report=True)
```

### Custom Node Exporters

```python
from src.cpg_export.nodes import MethodExporter, CallExporter

# Create individual exporters
method_exporter = MethodExporter(joern_client, conn, batch_size=5000)
call_exporter = CallExporter(joern_client, conn, batch_size=5000)

# Export specific node types
method_count = method_exporter.export(limit=10000)
call_count = call_exporter.export()
```

### Initialize Schema Only

```python
from src.cpg_export import initialize_schema
import duckdb

conn = duckdb.connect("cpg.duckdb")
initialize_schema(conn, force_recreate=True)
```

---

## DuckDB Client

Query the exported CPG using the client:

```python
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient("cpg.duckdb")

# Find methods by name
methods = client.find_methods_by_name("exec%")

# Get call graph
callgraph = client.get_callgraph("MyClass::process")

# SQL/PGQ query
result = client.execute_pgq("""
    FROM GRAPH_TABLE(cpg
        MATCH (m:METHOD)-[c:CALLS]->(callee:METHOD)
        WHERE m.name = 'main'
        COLUMNS (m.name, callee.full_name)
    )
""")

# Get statistics
stats = client.get_stats()
print(stats)
```

---

## Vector Embeddings

Add semantic embeddings for code search:

```python
from src.cpg_export.add_vector_embeddings import add_embeddings_to_methods

# Add embeddings to methods
add_embeddings_to_methods("cpg.duckdb", model_name="all-MiniLM-L6-v2")

# Semantic search
similar = find_similar_methods("cpg.duckdb", "parse user input safely")
```

---

## Incremental Export

Update CPG incrementally based on git changes:

```python
from src.cpg_export.incremental_exporter import IncrementalExporter

exporter = IncrementalExporter(
    repo_path="/path/to/repo",
    db_path="cpg.duckdb",
    joern_path="/path/to/joern"
)

# Update CPG from last commit changes
exporter.update_from_last_commit()
```

---

## Schema Documentation

Full schema documentation is in `duckdb_cpg_schema.md`.

### Node Tables

| Table | Description |
|-------|-------------|
| `nodes_method` | Function/method declarations |
| `nodes_call` | Function call sites |
| `nodes_identifier` | Variable references |
| `nodes_literal` | Literal values |
| `nodes_local` | Local variables |
| `nodes_param` | Function parameters |
| `nodes_return` | Return statements |
| `nodes_block` | Code blocks |
| `nodes_control_structure` | if/for/while |
| `nodes_type_decl` | Type declarations |
| `nodes_file` | Source files |
| `nodes_type` | Type instances |

### Edge Tables

| Table | Description |
|-------|-------------|
| `edges_ast` | AST structure |
| `edges_cfg` | Control Flow Graph |
| `edges_call` | Method calls |
| `edges_ref` | Variable references |
| `edges_cdg` | Control Dependence Graph |
| `edges_reaching_def` | Data flow |
| `edges_dominate` | Dominance analysis |

---

## Testing

Run the test suite:

```bash
# Run all CPG export tests
pytest tests/unit/test_cpg_export/ -v

# Run specific test modules
pytest tests/unit/test_cpg_export/test_schema.py -v
pytest tests/unit/test_cpg_export/test_validation.py -v
pytest tests/unit/test_cpg_export/test_nodes.py -v
pytest tests/unit/test_cpg_export/test_edges.py -v
pytest tests/unit/test_cpg_export/test_progress.py -v
```

---

## Dependencies

```
duckdb>=0.9.0
cpgqls-client
sentence-transformers  # for embeddings
```

---

## See Also

- [Joern Documentation](https://docs.joern.io/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [CPG Spec v1.1](https://cpg.joern.io/)
- [DuckPGQ Extension](https://duckdb.org/docs/extensions/duckpgq)
