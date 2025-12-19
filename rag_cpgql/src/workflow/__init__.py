"""
CodeGraph Workflow Package.

This package contains the LangGraph-based workflow implementation for
the multi-scenario copilot, supporting 14 different code analysis scenarios.

Main Components:
- MultiScenarioCopilot: Main entry point for running queries
- MultiScenarioState: Shared state across all workflows
- Scenario-specific workflows in the scenarios subpackage

Usage:
    from src.workflow import MultiScenarioCopilot

    copilot = MultiScenarioCopilot()
    result = copilot.run("Find SQL injection vulnerabilities")
    print(result['answer'])
"""

# Import from legacy location for backward compatibility
from .multi_scenario_workflow import (
    MultiScenarioCopilot,
    MultiScenarioState,
    classify_intent_node,
    route_by_intent,
)

# Import from new modular structure
from .state import (
    MultiScenarioState as MultiScenarioStateNew,
    SecurityWorkflowState,
    PerformanceWorkflowState,
    ArchitectureWorkflowState,
    create_initial_state,
)

# Import LangGraph state and components
from ._state import RAGCPGQLState
from ._components import (
    get_analyzer,
    get_retriever,
    get_generator_agent,
    get_interpreter_agent,
    get_joern_client,
    get_adaptive_refiner,
)

__all__ = [
    # Main classes
    'MultiScenarioCopilot',
    'MultiScenarioState',

    # State management
    'create_initial_state',
    'SecurityWorkflowState',
    'PerformanceWorkflowState',
    'ArchitectureWorkflowState',

    # LangGraph state and components
    'RAGCPGQLState',
    'get_analyzer',
    'get_retriever',
    'get_generator_agent',
    'get_interpreter_agent',
    'get_joern_client',
    'get_adaptive_refiner',

    # Node functions (for custom workflow building)
    'classify_intent_node',
    'route_by_intent',
]
