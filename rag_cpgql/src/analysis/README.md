# Analysis Module

Code analysis utilities including call graph analysis, dataflow tracing, and complexity metrics.

## Overview

```
src/analysis/
├── call_graph.py        # Call graph analyzer
├── dataflow.py          # Dataflow tracer
├── complexity.py        # Complexity metrics
├── concurrency.py       # Concurrency analyzer
├── clone_detector.py    # Code clone detection
└── __init__.py
```

## Features

### Call Graph Analysis
```python
from src.analysis import CallGraphAnalyzer

analyzer = CallGraphAnalyzer(cpg)
callers = analyzer.get_transitive_callers('critical_func')
callees = analyzer.get_transitive_callees('main')
```

### Dataflow Tracing
```python
from src.analysis import DataflowTracer

tracer = DataflowTracer(cpg)
flows = tracer.trace('user_input', 'database_query')
```

### Complexity Metrics
```python
from src.analysis import ComplexityAnalyzer

analyzer = ComplexityAnalyzer(cpg)
metrics = analyzer.analyze_function('complex_func')
# cyclomatic_complexity, lines_of_code, etc.
```

## See Also

- `/src/services/cpg_query_service.py`
- `/src/workflow/scenarios/`
