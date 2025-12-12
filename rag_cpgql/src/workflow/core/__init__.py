"""
LangGraph RAG-CPGQL Workflow Core Package.

This package contains the modular components of the LangGraph workflow:
- helpers.py - Utility functions (RAGAS, query processing)
- routing.py - Conditional routing functions

Agent node functions remain in the main langgraph_workflow.py module
for now but may be migrated here in the future.

For backward compatibility, import from src.workflow.langgraph_workflow.
"""

from .helpers import (
    _build_context_strings,
    _compute_ragas_scores,
    _count_scala_results,
    post_process_query,
    is_empty_result,
    _RAGAS_AVAILABLE,
    _RAGAS_METRICS,
)

from .routing import (
    route_by_mode,
    should_refine,
)


__all__ = [
    # Helpers
    '_build_context_strings',
    '_compute_ragas_scores',
    '_count_scala_results',
    'post_process_query',
    'is_empty_result',
    '_RAGAS_AVAILABLE',
    '_RAGAS_METRICS',
    # Routing
    'route_by_mode',
    'should_refine',
]
