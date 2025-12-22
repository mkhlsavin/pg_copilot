"""Data Flow Tracer - Backward Compatibility Facade.

This module re-exports from src.analysis.dataflow for backward compatibility.
New code should import directly from src.analysis.dataflow.

Example:
    # Old import (still works)
    from src.analysis.dataflow_tracer import DataFlowTracer

    # New import (preferred)
    from src.analysis.dataflow import DataFlowTracer
"""

from src.analysis.dataflow import (
    DataFlowTracer,
    DataFlowPath,
    VariableFlow,
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
