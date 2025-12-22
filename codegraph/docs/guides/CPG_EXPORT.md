# CPG Export Guide

This guide covers creating and exporting Code Property Graphs (CPG) to DuckDB for analysis with CodeGraph.

> **Note:** For regular CodeGraph operation, Joern is **not required**. CPG data is typically pre-exported to DuckDB.
> This guide is for users who need to create new CPG exports from source code.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
  - [For New CPG Creation (Optional)](#for-new-cpg-creation-optional)
  - [For Using Existing CPG Data](#for-using-existing-cpg-data)
  - [Optional](#optional)
  - [Install Dependencies](#install-dependencies)
- [Quick Start](#quick-start)
  - [CLI Export (Recommended)](#cli-export-recommended)
  - [Python API](#python-api)
- [CLI Reference](#cli-reference)
  - [Parameters](#parameters)
  - [Common Commands](#common-commands)
- [Export Process](#export-process)
  - [Step 1: Schema Initialization](#step-1-schema-initialization)
  - [Step 2: Node Export](#step-2-node-export)
  - [Step 3: Edge Export](#step-3-edge-export)
  - [Step 4: Property Graph Creation](#step-4-property-graph-creation)
  - [Step 5: Validation](#step-5-validation)
- [Checkpoint/Resume](#checkpointresume)
  - [Check Progress](#check-progress)
  - [Progress States](#progress-states)
- [Validation](#validation)
  - [Automatic Validation](#automatic-validation)
  - [Manual Validation](#manual-validation)
  - [Handling Missing Data](#handling-missing-data)
- [Incremental Updates](#incremental-updates)
  - [Performance](#performance)
- [Vector Embeddings](#vector-embeddings)
- [Schema Reference](#schema-reference)
  - [Core Node Tables](#core-node-tables)
  - [Core Edge Tables](#core-edge-tables)
  - [Full Schema](#full-schema)
- [Querying the CPG](#querying-the-cpg)
  - [SQL Queries](#sql-queries)
  - [Property Graph Queries (DuckPGQ)](#property-graph-queries-duckpgq)
  - [Python Client](#python-client)
- [Troubleshooting](#troubleshooting)
  - [Connection Errors](#connection-errors)
  - [Out of Memory](#out-of-memory)
  - [Slow Export](#slow-export)
  - [Missing Nodes](#missing-nodes)
- [Performance Tips](#performance-tips)
- [See Also](#see-also)

## Overview

The CPG export system creates code analysis data in DuckDB format, enabling:

- **SQL queries** for graph traversal
- **Semantic search** with vector embeddings
- **Security analysis** with hypothesis generation
- **Incremental updates** via git integration

**Key Features:**
- Full CPG Spec v1.1 compliance (22 node types, 20 edge types)
- Checkpoint/resume for large codebases
- Automatic validation
- Property Graph creation for graph queries

---

## Prerequisites

### For New CPG Creation (Optional)
- **Joern** installation (only if creating new CPG from source code)
- **DuckDB** 0.9.0+
- **Python** 3.10+

### For Using Existing CPG Data
- **DuckDB** 0.9.0+
- **Python** 3.10+
- Pre-exported CPG database file (`.duckdb`)

### Optional
- **DuckPGQ extension** for property graph queries
- **sentence-transformers** for semantic embeddings

### Install Dependencies

```bash
pip install duckdb cpgqls-client sentence-transformers
```

---

## Quick Start

### CLI Export (Recommended)

```bash
# Full export with validation
python -m src.cpg_export.exporter \
    --endpoint localhost:8080 \
    --workspace myproject.cpg \
    --db cpg.duckdb

# Check export status
python -m src.cpg_export.exporter --db cpg.duckdb --status

# Validate existing database
python -m src.cpg_export.exporter --db cpg.duckdb --validate-only
```

### Python API

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

# Check results
print(f"Nodes exported: {sum(results['node_stats'].values())}")
print(f"Edges exported: {sum(results['edge_stats'].values())}")
```

---

## CLI Reference

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--endpoint` | `localhost:8080` | Joern server endpoint |
| `--workspace` | `pg17_full.cpg` | Workspace/CPG name in Joern |
| `--db` | `cpg.duckdb` | Output DuckDB file path |
| `--batch-size` | `10000` | Records per batch (memory vs speed) |
| `--limit` | None | Limit records per type (for testing) |
| `--force` | False | Drop and recreate all tables |
| `--no-resume` | False | Disable checkpoint resume |
| `--skip-validation` | False | Skip validation at end |
| `--status` | False | Show export progress only |
| `--validate-only` | False | Run validation only |

### Common Commands

```bash
# Resume interrupted export
python -m src.cpg_export.exporter --db cpg.duckdb

# Force fresh export (drops existing data)
python -m src.cpg_export.exporter --db cpg.duckdb --force

# Test with limited data
python -m src.cpg_export.exporter --db cpg.duckdb --limit 1000

# Large codebase with smaller batches
python -m src.cpg_export.exporter --db cpg.duckdb --batch-size 5000
```

---

## Export Process

The exporter runs a 5-step pipeline:

### Step 1: Schema Initialization

Creates tables for all CPG node and edge types. Tables are created with `IF NOT EXISTS` to preserve existing data unless `--force` is used.

### Step 2: Node Export

Exports all CPG nodes by type:

| Priority | Node Types |
|----------|------------|
| P0 (Core) | METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE |
| P0 (Structure) | FILE, NAMESPACE, NAMESPACE_BLOCK, MEMBER, TYPE, TYPE_DECL |
| P1 | METHOD_PARAMETER_OUT, METHOD_RETURN, FIELD_IDENTIFIER, TYPE_ARGUMENT, TYPE_PARAMETER |
| P2 | JUMP_LABEL, JUMP_TARGET, METHOD_REF, MODIFIER, TYPE_REF, UNKNOWN |
| P3 | BINDING, ANNOTATION |

### Step 3: Edge Export

Exports all CPG edges:

| Priority | Edge Types |
|----------|------------|
| P0 (Core) | AST, CFG, CALL, REF, ARGUMENT, RECEIVER, CONDITION |
| P0 (Analysis) | REACHING_DEF, DOMINATE, POST_DOMINATE, CDG, CONTAINS |
| P1 | EVAL_TYPE, INHERITS_FROM, ALIAS_OF |
| P2 | BINDS_TO, PARAMETER_LINK, SOURCE_FILE |
| P3 | TAGGED_BY, BINDS |

### Step 4: Property Graph Creation

Creates a DuckDB Property Graph named `cpg` for graph traversal queries:

```sql
-- Query using property graph
FROM GRAPH_TABLE(cpg
    MATCH (m:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE m.name = 'main'
    COLUMNS (m.name AS caller, callee.full_name AS callee)
)
```

### Step 5: Validation

Compares counts between Joern and DuckDB to ensure complete export:

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
```

---

## Checkpoint/Resume

The exporter automatically saves progress after each batch. If interrupted:

```bash
# Simply run again - will resume automatically
python -m src.cpg_export.exporter --db cpg.duckdb
```

### Check Progress

```bash
# CLI
python -m src.cpg_export.exporter --db cpg.duckdb --status
```

```sql
-- Direct SQL query
SELECT entity_type, status, exported_count, last_offset
FROM export_progress
ORDER BY entity_type;
```

### Progress States

| Status | Description |
|--------|-------------|
| `pending` | Not yet started |
| `in_progress` | Currently exporting |
| `completed` | Successfully finished |
| `failed` | Error occurred |

---

## Validation

### Automatic Validation

Validation runs automatically at the end of export. To skip:

```bash
python -m src.cpg_export.exporter --db cpg.duckdb --skip-validation
```

### Manual Validation

```bash
# CLI
python -m src.cpg_export.exporter --db cpg.duckdb --validate-only
```

```python
# Python API
from src.cpg_export import validate_export
from src.execution.joern_client import JoernClient
import duckdb

joern = JoernClient("localhost:8080", "myproject.cpg")
conn = duckdb.connect("cpg.duckdb")

results = validate_export(joern, conn, print_report=True)
```

### Handling Missing Data

If validation shows missing records:

1. **Check Joern logs** for parse errors
2. **Re-export specific types** if partial failure
3. **Force recreate** if data corruption suspected

```python
# Re-export only nodes
exporter = JoernToDuckDBExporter(...)
exporter.connect_db()
node_stats = exporter.export_nodes_only(limit=None)

# Re-export only edges
edge_stats = exporter.export_edges_only(limit=None)
```

---

## Incremental Updates

For repositories with active development, use incremental export:

```python
from src.cpg_export.incremental_exporter import IncrementalCPGExporter

exporter = IncrementalCPGExporter(
    repo_path="/path/to/repo",
    db_path="cpg.duckdb",
    joern_path="/path/to/joern"
)

# Update from git changes
result = exporter.update_from_git_diff(
    from_ref="HEAD~5",  # Last 5 commits
    to_ref="HEAD"
)

print(f"Status: {result.status}")
print(f"Files changed: {len(result.changed_files)}")
print(f"Nodes updated: {result.nodes_updated}")
print(f"Duration: {result.duration_seconds}s")
```

### Performance

| Operation | Full Export | Incremental |
|-----------|-------------|-------------|
| 100K LOC | ~20 min | ~2 min |
| 1M LOC | ~3 hours | ~10 min |

---

## Vector Embeddings

Add semantic embeddings for code search:

```python
from src.cpg_export.add_vector_embeddings import add_embeddings_to_methods

# Add embeddings to methods table
add_embeddings_to_methods(
    db_path="cpg.duckdb",
    model_name="all-MiniLM-L6-v2",
    batch_size=100
)

# Semantic search
from src.cpg_export.add_vector_embeddings import find_similar_methods

results = find_similar_methods(
    db_path="cpg.duckdb",
    query="parse user input safely",
    top_k=10
)
```

---

## Schema Reference

### Core Node Tables

| Table | Key Columns | Description |
|-------|-------------|-------------|
| `nodes_method` | id, name, full_name, filename, line_number | Functions/methods |
| `nodes_call` | id, name, method_full_name, filename, line_number | Call sites |
| `nodes_identifier` | id, name, type_full_name, line_number | Variable references |
| `nodes_literal` | id, code, type_full_name | Literal values |
| `nodes_local` | id, name, type_full_name | Local variables |
| `nodes_param` | id, name, type_full_name, index | Parameters |
| `nodes_return` | id, code, line_number | Return statements |
| `nodes_block` | id, type_full_name, line_number | Code blocks |
| `nodes_control_structure` | id, control_structure_type, line_number | if/for/while |
| `nodes_type_decl` | id, name, full_name, filename | Type declarations |
| `nodes_file` | id, name, hash | Source files |

### Core Edge Tables

| Table | Columns | Description |
|-------|---------|-------------|
| `edges_ast` | src, dst | AST parent-child |
| `edges_cfg` | src, dst | Control flow |
| `edges_call` | src, dst | Method calls |
| `edges_ref` | src, dst | Variable references |
| `edges_reaching_def` | src, dst, variable | Data flow |
| `edges_cdg` | src, dst | Control dependence |
| `edges_dominate` | src, dst | Dominance |

### Full Schema

See `src/cpg_export/duckdb_cpg_schema.md` for complete schema documentation.

---

## Querying the CPG

### SQL Queries

```sql
-- Find all methods in a file
SELECT name, full_name, line_number
FROM nodes_method
WHERE filename LIKE '%auth%'
ORDER BY line_number;

-- Find calls to dangerous functions
SELECT nc.code, nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('system', 'exec', 'eval');

-- Count nodes by type
SELECT 'METHOD' as type, COUNT(*) as cnt FROM nodes_method
UNION ALL
SELECT 'CALL', COUNT(*) FROM nodes_call
UNION ALL
SELECT 'IDENTIFIER', COUNT(*) FROM nodes_identifier;
```

### Property Graph Queries (DuckPGQ)

```sql
-- Find call chains
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE caller.name = 'process_input'
    COLUMNS (
        caller.full_name AS caller,
        callee.full_name AS callee
    )
)
LIMIT 100;

-- Find data flow paths
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL)
    WHERE sink.name = 'execute'
    COLUMNS (
        src.name AS source_var,
        sink.code AS sink_call,
        sink.line_number AS line
    )
)
```

### Python Client

```python
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient("cpg.duckdb")

# Find methods by pattern
methods = client.find_methods_by_name("parse%")

# Get call graph for a method
callgraph = client.get_callgraph("UserController::authenticate")

# Get statistics
stats = client.get_stats()
print(f"Total methods: {stats['nodes_method']}")
print(f"Total calls: {stats['nodes_call']}")
```

---

## Troubleshooting

### Connection Errors

```
Error: Could not connect to Joern server
```

**Solution:** Verify Joern is running and accessible:

```bash
# Test connection
curl http://localhost:8080/result
```

### Out of Memory

```
Error: Database out of memory
```

**Solutions:**
1. Reduce batch size: `--batch-size 5000`
2. Use `--limit` for testing
3. Close other applications

### Slow Export

For large codebases (>1M LOC):

1. Use incremental export for updates
2. Run overnight for initial export
3. Consider splitting by directory

### Missing Nodes

If validation shows missing nodes:

1. Check Joern parse logs for errors
2. Verify workspace is correctly opened
3. Try force recreate: `--force`

---

## Performance Tips

| Codebase Size | Batch Size | Estimated Time |
|---------------|------------|----------------|
| <50K LOC | 10000 | <5 min |
| 50K-200K LOC | 10000 | 5-30 min |
| 200K-1M LOC | 5000 | 30 min - 3 hours |
| >1M LOC | 2000 | 3+ hours |

**Optimizations:**
- SSD storage for database
- Adequate RAM (8GB+ for large codebases)
- Run validation separately if needed
- Use incremental exports for updates

---

## See Also

- [SQL Query Cookbook](../reference/SQL_QUERY_COOKBOOK.md) - Example queries
- [Schema Reference](../reference/SCHEMA.md) - Database schema reference
- [Joern Documentation](https://docs.joern.io/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [CPG Specification v1.1](https://cpg.joern.io/)
