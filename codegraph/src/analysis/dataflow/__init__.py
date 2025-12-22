"""Data Flow Analysis Package.

Data flow tracing using REACHING_DEF edges from CPG.

Main components:
- DataFlowTracer: Main tracer class
- DataFlowPath: Represents a data flow path
- VariableFlow: Tracks flow of a single variable
- Sanitization patterns and confidence scoring

Example usage:
    from src.analysis.dataflow import DataFlowTracer

    tracer = DataFlowTracer(cpg_service)
    flow = tracer.trace_variable('user_input')
    paths = tracer.find_taint_paths(['readLine'], ['system'])
"""

from .models import DataFlowPath, VariableFlow
from .tracer import DataFlowTracer
from .sanitization import (
    SANITIZATION_CONFIDENCE,
    SANITIZATION_CONFIDENCE_THRESHOLD,
    get_sanitization_patterns,
)

__all__ = [
    "DataFlowTracer",
    "DataFlowPath",
    "VariableFlow",
    "SANITIZATION_CONFIDENCE",
    "SANITIZATION_CONFIDENCE_THRESHOLD",
    "get_sanitization_patterns",
]
