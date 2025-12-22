"""
LangGraph CodeGraph Workflow Core Package.

This package contains shared components for workflow scenarios:
- helpers.py - Utility functions (RAGAS, query processing)
- routing.py - Conditional routing functions

Main entry point: src.workflow.multi_scenario_workflow.MultiScenarioCopilot
Scenario workflows: src.workflow.scenarios.*
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
