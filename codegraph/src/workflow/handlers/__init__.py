"""
Workflow Node Handlers.

Contains reusable handler classes for common workflow operations
that can be shared across different scenario workflows.

Handler Types:
- RetrievalHandler: CPG query and retrieval operations
- AnalysisHandler: Code analysis (call graph, dataflow)
- GenerationHandler: LLM response generation
- EvaluationHandler: Result validation and quality scoring

Example usage:
    from src.workflow.handlers import RetrievalHandler, AnalysisHandler

    # Initialize handlers with dependencies
    retrieval = RetrievalHandler(cpg_client=client)
    analysis = AnalysisHandler(cpg_client=client)

    # Execute operations
    result = retrieval.find_methods("malloc")
    if result.success:
        print(f"Found {len(result.data)} methods")

    impact = analysis.analyze_change_impact("heap_insert")
    if impact.success:
        print(f"Impact level: {impact.data['impact_level']}")
"""

from .base import BaseHandler, HandlerResult
from .retrieval import RetrievalHandler
from .analysis import AnalysisHandler
from .generation import GenerationHandler
from .evaluation import EvaluationHandler, EvaluationScore

__all__ = [
    # Base classes
    "BaseHandler",
    "HandlerResult",

    # Handler implementations
    "RetrievalHandler",
    "AnalysisHandler",
    "GenerationHandler",
    "EvaluationHandler",

    # Data classes
    "EvaluationScore",
]
