"""
Multi-Scenario Workflow Orchestration Package.

Provides the orchestration layer for the LangGraph-based multi-scenario copilot:
- Intent classification
- Scenario routing
- Graph building
- Copilot interface

This package coordinates 16+ enterprise scenarios through a unified workflow.
"""

from src.workflow.orchestration.intent_classifier import classify_intent_node
from src.workflow.orchestration.router import route_by_intent
from src.workflow.orchestration.graph_builder import build_multi_scenario_graph
from src.workflow.orchestration.copilot import MultiScenarioCopilot


__all__ = [
    # Core workflow functions
    'classify_intent_node',
    'route_by_intent',
    'build_multi_scenario_graph',
    # Main interface
    'MultiScenarioCopilot',
]
