"""
Routing functions for LangGraph CodeGraph Workflow.

This module contains conditional routing functions that determine
workflow execution paths based on state.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.workflow._state import RAGCPGQLState

logger = logging.getLogger(__name__)


def route_by_mode(state: "RAGCPGQLState") -> str:
    """Route to semantic or control flow mode based on query_mode.

    Returns:
        "control_flow_generate" for explain-logic mode
        "retrieve" for find-method mode (semantic)
    """
    query_mode = state.get("query_mode", "find-method")
    logger.info(f"Routing: query_mode={query_mode}")

    if query_mode == "explain-logic":
        return "control_flow_generate"
    else:
        return "retrieve"


def should_refine(state: "RAGCPGQLState") -> str:
    """Determine if query needs refinement or can proceed to execution."""
    if state.get("query_valid", False):
        return "execute"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count >= 2:
            return "execute"  # Give up, try to execute anyway
        return "refine"


__all__ = [
    'route_by_mode',
    'should_refine',
]
