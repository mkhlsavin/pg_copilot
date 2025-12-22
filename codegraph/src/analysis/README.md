# Analysis Module

Code analysis utilities including CFG analysis, dataflow tracing, field-sensitive tracking, and complexity metrics.

## Overview

```
src/analysis/
├── cfg_analyzer.py           # CFG-based analysis, cyclomatic complexity
├── field_sensitive_tracer.py # Field-path taint tracking
├── dataflow_tracer.py        # Dataflow analysis facade
├── call_graph_analyzer.py    # Call graph traversal
├── concurrency_analyzer.py   # Concurrency pattern detection
├── clone_detector.py         # Code clone detection
├── dataflow/                 # Dataflow analysis implementations
├── callgraph/                # Call graph implementations
├── _call_graph_types.py      # Type definitions
└── __init__.py
```

## Key Modules

### CFGAnalyzer (NEW)

Proper CFG-based analysis using `edges_cfg` table:

```python
from src.analysis.cfg_analyzer import CFGAnalyzer

analyzer = CFGAnalyzer(cpg_service)

# Get cyclomatic complexity (M = E - N + 2)
complexity = analyzer.compute_cyclomatic_complexity("heap_insert")

# Enumerate execution paths
paths = analyzer.enumerate_paths("process_query", max_paths=50)

# Get CFG structure
cfg = analyzer.get_method_cfg("main")
print(f"Nodes: {cfg.node_count}, Edges: {cfg.edge_count}")
```

### FieldSensitiveTracer (NEW)

Field-path tracking for precise taint analysis:

```python
from src.analysis.field_sensitive_tracer import FieldSensitiveTracer

tracer = FieldSensitiveTracer(cpg_service)

# Parse field access
path = tracer.parse_field_path("user->password")

# Find sensitive data flows
flows = tracer.find_sensitive_field_flows()
```

### DataFlowTracer

Facade providing unified dataflow analysis:

```python
from src.analysis.dataflow_tracer import DataFlowTracer

tracer = DataFlowTracer(cpg_service)

# Field-sensitive taint analysis
paths = tracer.find_taint_paths_field_sensitive(
    source_functions=["getenv", "fgets"],
    sink_functions=["system", "exec"]
)

# Find sensitive data exposures
flows = tracer.find_sensitive_data_flows()
```

### CallGraphAnalyzer

Call graph traversal and analysis:

```python
from src.analysis.call_graph_analyzer import CallGraphAnalyzer

analyzer = CallGraphAnalyzer(cpg_service)
callers = analyzer.get_transitive_callers("critical_func")
callees = analyzer.get_transitive_callees("main")
```

### ConcurrencyAnalyzer

Lock pattern and race condition detection:

```python
from src.analysis.concurrency_analyzer import ConcurrencyAnalyzer

analyzer = ConcurrencyAnalyzer(cpg_service)
patterns = analyzer.find_lock_patterns()
races = analyzer.detect_potential_races()
```

### CloneDetector

Code duplicate detection:

```python
from src.analysis.clone_detector import CloneDetector

detector = CloneDetector(cpg_service)
clones = detector.find_clones(min_lines=10)
```

## Use Cases

| Scenario | Modules Used |
|----------|--------------|
| Security Audit | FieldSensitiveTracer, DataFlowTracer |
| Refactoring | CFGAnalyzer, CloneDetector |
| Performance | CFGAnalyzer (complexity) |
| Compliance | FieldSensitiveTracer |
| Concurrency | ConcurrencyAnalyzer |
| Incident Response | FieldSensitiveTracer, DataFlowTracer |

## See Also

- [Analysis Modules Reference](/docs/reference/ANALYSIS_MODULES.md) - Full API documentation
- [Patch Review](/src/patch_review/README.md) - Control flow analyzer integration
- [Workflow Scenarios](/src/workflow/README.md) - Usage in scenarios
