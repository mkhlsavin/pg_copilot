# Analysis Modules Reference

Comprehensive documentation for the code analysis modules in `src/analysis/`.

## Table of Contents

- [Overview](#overview)
- [CFGAnalyzer](#cfganalyzer)
  - [Features](#features)
  - [Key Classes](#key-classes)
  - [API Reference](#api-reference)
  - [Database Tables Used](#database-tables-used)
- [FieldSensitiveTracer](#fieldsensitivetracer)
  - [Features](#features)
  - [Key Classes](#key-classes)
  - [API Reference](#api-reference)
  - [Sensitive Field Categories](#sensitive-field-categories)
  - [Database Tables Used](#database-tables-used)
- [DataFlowTracer](#dataflowtracer)
  - [Integration Methods](#integration-methods)
- [ControlFlowAnalyzer (Patch Review)](#controlflowanalyzer-patch-review)
  - [Features](#features)
  - [Integration with CFGAnalyzer](#integration-with-cfganalyzer)
  - [Loop Severity Classification](#loop-severity-classification)
- [Usage Examples](#usage-examples)
  - [Security Audit (Scenario 2)](#security-audit-scenario-2)
  - [Complexity Analysis (Scenario 5/6)](#complexity-analysis-scenario-56)
  - [Patch Review (Scenario 9)](#patch-review-scenario-9)
- [Database Schema Reference](#database-schema-reference)
  - [Key Tables for Analysis](#key-tables-for-analysis)
  - [Edge Types for Dataflow](#edge-types-for-dataflow)
- [Troubleshooting](#troubleshooting)
  - ["Method not found"](#method-not-found)
  - ["No CFG data found"](#no-cfg-data-found)
  - ["No field accesses found"](#no-field-accesses-found)
  - [Performance Considerations](#performance-considerations)
- [See Also](#see-also)

## Overview

The analysis modules provide advanced static analysis capabilities on top of the CPG (Code Property Graph) stored in DuckDB:

| Module | Purpose | Key Scenarios |
|--------|---------|---------------|
| **CFGAnalyzer** | Control flow graph analysis, complexity metrics | 5, 6, 13 (refactoring, performance) |
| **FieldSensitiveTracer** | Field-path taint tracking | 2, 8, 14 (security, compliance, incident) |
| **DataFlowTracer** | General dataflow analysis facade | 2, 14 (security, incident response) |
| **CallGraphAnalyzer** | Call graph traversal | 1, 12 (onboarding, cross-repo) |
| **ConcurrencyAnalyzer** | Lock/mutex pattern detection | 16 (concurrency) |
| **CloneDetector** | Code duplicate detection | 7, 13 (refactoring) |

---

## CFGAnalyzer

**File:** `src/analysis/cfg_analyzer.py`

CFG-based analysis using the `edges_cfg` table for accurate control flow analysis.

### Features

- **Cyclomatic Complexity**: McCabe complexity via `M = E - N + 2`
- **Path Enumeration**: DFS-based execution path discovery with cycle detection
- **Dominator Analysis**: Compute dominator and post-dominator trees
- **CFG Structure Extraction**: Get nodes, edges, entry/exit points

### Key Classes

```python
@dataclass
class CFGStructure:
    """Represents the CFG structure of a method"""
    method_name: str
    method_full_name: str
    nodes: List[int]
    edges: List[Tuple[int, int]]  # (src, dst) pairs
    entry_nodes: List[int]
    exit_nodes: List[int]
    node_count: int
    edge_count: int

@dataclass
class CFGPath:
    """Represents an execution path through the CFG"""
    path_id: str
    nodes: List[int]
    length: int
    has_loop: bool = False
```

### API Reference

#### `CFGAnalyzer(cpg_service)`
Initialize with CPGQueryService or DuckDB connection.

#### `get_method_cfg(method_name: str) -> Optional[CFGStructure]`
Get the CFG structure for a method.

```python
from src.analysis.cfg_analyzer import CFGAnalyzer

analyzer = CFGAnalyzer(cpg_service)
cfg = analyzer.get_method_cfg("heap_insert")
print(f"Nodes: {cfg.node_count}, Edges: {cfg.edge_count}")
```

#### `compute_cyclomatic_complexity(method_name: str) -> int`
Calculate McCabe cyclomatic complexity: `M = E - N + 2`

```python
complexity = analyzer.compute_cyclomatic_complexity("heap_insert")
print(f"Complexity: {complexity}")  # e.g., 15
```

#### `enumerate_paths(method_name: str, max_paths: int = 100) -> List[CFGPath]`
Find execution paths through the CFG with cycle detection.

```python
paths = analyzer.enumerate_paths("process_query", max_paths=50)
for path in paths:
    print(f"Path {path.path_id}: {path.length} nodes, loop={path.has_loop}")
```

#### `find_dominators(method_name: str) -> Dict[int, Set[int]]`
Compute dominator tree using `edges_dominate` table.

#### `find_post_dominators(method_name: str) -> Dict[int, Set[int]]`
Compute post-dominator tree using `edges_post_dominate` table.

#### `analyze_complexity_distribution() -> Dict[str, Any]`
Analyze complexity across all methods in the codebase.

```python
dist = analyzer.analyze_complexity_distribution()
print(f"Average complexity: {dist['average']}")
print(f"High complexity methods: {dist['high_complexity_methods']}")
```

### Database Tables Used

- `nodes_method` - Method metadata
- `edges_contains` - Method-to-node containment
- `edges_cfg` - CFG edges between nodes
- `edges_dominate` - Dominator relationships
- `edges_post_dominate` - Post-dominator relationships

---

## FieldSensitiveTracer

**File:** `src/analysis/field_sensitive_tracer.py`

Field-path tracking for precise taint analysis, distinguishing between different fields of the same object.

### Features

- **Field Path Parsing**: Parse `obj.field1.field2` and `obj->field->data` access chains
- **Field Access Tracking**: Find all reads/writes to specific fields
- **Taint Propagation**: Track taint through field accesses
- **Sensitive Field Detection**: Identify flows from sensitive fields (password, token, etc.)

### Key Classes

```python
@dataclass
class FieldPath:
    """Represents a field access path like obj.field1.field2"""
    base_variable: str
    field_chain: List[str]
    full_path: str
    node_ids: List[int]
    type_full_name: Optional[str]

@dataclass
class FieldAccess:
    """Represents a single field access in code"""
    node_id: int
    base_variable: str
    field_name: str
    access_code: str
    line_number: int
    filename: str
    access_type: str  # 'read', 'write', 'call'
    containing_method: Optional[str]

@dataclass
class FieldSensitiveFlow:
    """A dataflow path with field sensitivity"""
    source_path: FieldPath
    sink_path: FieldPath
    intermediate_fields: List[FieldPath]
    is_tainted: bool
    relationship: str  # 'exact', 'prefix', 'suffix', 'propagated'
    confidence: float
```

### API Reference

#### `FieldSensitiveTracer(cpg_service)`
Initialize with CPGQueryService or DuckDB connection.

#### `parse_field_path(code: str) -> FieldPath`
Parse field access string into structured FieldPath.

```python
from src.analysis.field_sensitive_tracer import FieldSensitiveTracer

tracer = FieldSensitiveTracer(cpg_service)

# Parse pointer notation
path = tracer.parse_field_path("user->password")
print(path.base_variable)  # "user"
print(path.field_chain)    # ["password"]

# Parse dot notation
path = tracer.parse_field_path("request.data.buffer")
print(path.full_path)  # "request.data.buffer"
```

#### `get_struct_fields(struct_name: str) -> List[Dict]`
Get fields defined in a struct with type information.

```python
fields = tracer.get_struct_fields("UserData")
for field in fields:
    print(f"{field['name']}: {field['type']}")
```

#### `find_field_accesses(base_var: str, field_name: str) -> List[FieldAccess]`
Find all accesses to a specific field.

```python
accesses = tracer.find_field_accesses("user", "password")
for access in accesses:
    print(f"{access.filename}:{access.line_number} - {access.access_type}")
```

#### `trace_field_taint(source_field: str, sink_functions: List[str]) -> List[FieldSensitiveFlow]`
Trace taint from a source field to sink functions.

```python
flows = tracer.trace_field_taint(
    source_field="credentials->password",
    sink_functions=["printf", "log", "send"]
)
for flow in flows:
    print(f"Tainted flow: {flow.source_path} -> {flow.sink_path}")
```

#### `find_sensitive_field_flows(sensitive_fields: List[str] = None, sink_functions: List[str] = None) -> List[FieldSensitiveFlow]`
Find flows from sensitive fields to dangerous sinks.

```python
# Default sensitive fields: password, token, secret, private_key, credential, auth
flows = tracer.find_sensitive_field_flows()
print(f"Found {len(flows)} potential sensitive data exposures")
```

### Sensitive Field Categories

Default sensitive fields tracked:
- `password`, `passwd`, `pwd`
- `token`, `auth_token`, `access_token`
- `secret`, `api_secret`, `client_secret`
- `private_key`, `secret_key`
- `credential`, `credentials`
- `auth`, `authorization`

### Database Tables Used

- `nodes_field_identifier` - Field access nodes
- `nodes_identifier` - Variable identifiers
- `nodes_member` - Struct member definitions
- `edges_reaching_def` - Reaching definition edges
- `edges_argument` - Function argument edges

---

## DataFlowTracer

**File:** `src/analysis/dataflow_tracer.py`

Facade module that provides unified access to dataflow analysis capabilities.

### Integration Methods

The DataFlowTracer provides integration between base dataflow analysis and field-sensitive analysis:

#### `find_taint_paths_field_sensitive(source_functions, sink_functions, track_fields=True, max_depth=10) -> List[DataFlowPath]`
Enhanced taint analysis with optional field tracking.

```python
from src.analysis.dataflow_tracer import DataFlowTracer

tracer = DataFlowTracer(cpg_service)

# Find taint paths with field sensitivity
paths = tracer.find_taint_paths_field_sensitive(
    source_functions=["getenv", "fgets", "read"],
    sink_functions=["system", "exec", "popen"],
    track_fields=True,
    max_depth=10
)

for path in paths:
    print(f"Source: {path.source} -> Sink: {path.sink}")
    print(f"Fields accessed: {path.field_accesses}")
```

#### `find_sensitive_data_flows(sensitive_fields=None, sink_functions=None) -> List[Dict]`
Wrapper around FieldSensitiveTracer for common security analysis.

```python
# Use defaults for common patterns
flows = tracer.find_sensitive_data_flows()

# Or customize
flows = tracer.find_sensitive_data_flows(
    sensitive_fields=["api_key", "bearer_token"],
    sink_functions=["http_request", "socket_send"]
)
```

---

## ControlFlowAnalyzer (Patch Review)

**File:** `src/patch_review/analyzers/control_flow_analyzer.py`

Analyzes control flow impact of patches, now using CFGAnalyzer for accurate metrics.

### Features

- Complexity delta calculation (before/after patch)
- New loop detection with risk classification
- Error handling change tracking
- Branch coverage impact estimation

### Integration with CFGAnalyzer

```python
from src.patch_review.analyzers.control_flow_analyzer import PatchControlFlowAnalyzer

analyzer = PatchControlFlowAnalyzer(cpg_service)

# Analyze patch impact
result = analyzer.analyze_control_flow_changes(patch_data)

print(f"Complexity delta: {result.complexity_delta}")
print(f"New loops: {len(result.new_loops)}")
print(f"Error handling changes: {len(result.error_handling_changes)}")
```

### Loop Severity Classification

New loops are classified by risk:
- **HIGH**: Nested loops, loops with I/O, unbounded loops
- **MEDIUM**: Loops with external calls
- **LOW**: Simple bounded loops

---

## Usage Examples

### Security Audit (Scenario 2)

```python
from src.analysis.field_sensitive_tracer import FieldSensitiveTracer

tracer = FieldSensitiveTracer(cpg_service)

# Find password leaks
flows = tracer.find_sensitive_field_flows(
    sensitive_fields=["password", "credentials"],
    sink_functions=["printf", "fprintf", "syslog", "elog"]
)

for flow in flows:
    print(f"ALERT: {flow.source_path} flows to {flow.sink_path}")
```

### Complexity Analysis (Scenario 5/6)

```python
from src.analysis.cfg_analyzer import CFGAnalyzer

analyzer = CFGAnalyzer(cpg_service)

# Analyze all methods
dist = analyzer.analyze_complexity_distribution()

# Find refactoring candidates
for method in dist['high_complexity_methods']:
    print(f"Refactor candidate: {method['name']} (complexity={method['complexity']})")
```

### Patch Review (Scenario 9)

```python
from src.patch_review.analyzers.control_flow_analyzer import PatchControlFlowAnalyzer

analyzer = PatchControlFlowAnalyzer(cpg_service)
result = analyzer.analyze_control_flow_changes(patch)

if result.complexity_delta > 10:
    print("WARNING: Significant complexity increase")

for loop in result.new_loops:
    if loop.severity == 'HIGH':
        print(f"ALERT: High-risk loop in {loop.method_name}")
```

---

## Database Schema Reference

### Key Tables for Analysis

| Table | Purpose |
|-------|---------|
| `nodes_method` | Method definitions |
| `nodes_control_structure` | Control flow structures (if, for, while) |
| `nodes_field_identifier` | Field access expressions |
| `nodes_identifier` | Variable references |
| `edges_cfg` | Control flow graph edges |
| `edges_contains` | Containment relationships |
| `edges_dominate` | Dominator relationships |
| `edges_reaching_def` | Reaching definition edges |
| `edges_argument` | Function argument edges |

### Edge Types for Dataflow

| Edge Type | Table | Purpose |
|-----------|-------|---------|
| CFG | `edges_cfg` | Control flow between statements |
| REACHING_DEF | `edges_reaching_def` | Definition-use chains |
| ARGUMENT | `edges_argument` | Function call arguments |
| CONTAINS | `edges_contains` | Scope containment |

---

## Troubleshooting

### "Method not found"
The method name must match exactly (case-sensitive). Use the simple name, not the full qualified name.

```python
# Correct
cfg = analyzer.get_method_cfg("heap_insert")

# Incorrect
cfg = analyzer.get_method_cfg("heap_insert(Relation, HeapTuple)")
```

### "No CFG data found"
Ensure the CPG export included CFG edges. Check if `edges_cfg` table has data:

```sql
SELECT COUNT(*) FROM edges_cfg;
```

### "No field accesses found"
Field access tracking requires `nodes_field_identifier` data:

```sql
SELECT COUNT(*) FROM nodes_field_identifier;
```

### Performance Considerations

- Path enumeration is bounded by `max_paths` to prevent explosion
- Use `max_depth` to limit taint tracking depth
- Large methods may have many paths; consider sampling

---

## See Also

- [Schema Reference](SCHEMA.md) - Complete database schema
- [SQL Query Cookbook](SQL_QUERY_COOKBOOK.md) - Query examples
- [Agents Reference](AGENTS.md) - Agent pipeline
- [Scenarios Guide](../guides/SCENARIOS.md) - Usage scenarios
