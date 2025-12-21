"""
Graph Analysis Module for CPG

Implements 14 graph methods from "Graph methods for RAG copilot.md":
1. Definition and reference finding
2. Call graph navigation ✅ (CallGraphAnalyzer)
3. Data flow tracing ✅ (DataFlowTracer)
4. Vulnerability detection (taint analysis) - uses DataFlowTracer
5. Dead code detection
6. Complexity metrics and hotspots
7. Code clone detection
8. Entry points and attack surface
9. Concurrency error analysis ✅ (ConcurrencyAnalyzer)
10. Memory analysis
11. Module structure and dependencies
12. Auto-documentation
13. Concept explanation
14. Debugging and tracing
"""

from .call_graph_analyzer import CallGraphAnalyzer
from .dataflow_tracer import DataFlowTracer
from .concurrency_analyzer import ConcurrencyAnalyzer
from .clone_detector import ASTCloneDetector, CloneResult, detect_duplicate_category
from .cfg_analyzer import CFGAnalyzer, CFGStructure, CFGPath
from .field_sensitive_tracer import (
    FieldSensitiveTracer,
    FieldPath,
    FieldAccess,
    FieldSensitiveFlow,
)

__all__ = [
    'CallGraphAnalyzer',
    'DataFlowTracer',
    'ConcurrencyAnalyzer',
    'ASTCloneDetector',
    'CloneResult',
    'detect_duplicate_category',
    'CFGAnalyzer',
    'CFGStructure',
    'CFGPath',
    'FieldSensitiveTracer',
    'FieldPath',
    'FieldAccess',
    'FieldSensitiveFlow',
]
