"""
LangGraph Builder for Multi-Scenario Workflow.

Constructs the workflow graph with conditional routing to scenarios.
"""

from langgraph.graph import StateGraph, END

from src.workflow.state import MultiScenarioState
from src.workflow.orchestration.intent_classifier import classify_intent_node
from src.workflow.orchestration.router import route_by_intent

# All scenario workflows
from src.workflow.scenarios import (
    security_workflow,
    performance_workflow,
    refactoring_workflow,
    onboarding_workflow,
    documentation_workflow,
    feature_dev_workflow,
    test_coverage_workflow,
    code_review_workflow,
    compliance_workflow,
    security_incident_workflow,
    cross_repo_workflow,
    large_scale_refactoring_workflow,
    architecture_workflow,
    tech_debt_workflow,
    mass_refactoring_workflow,
    debugging_workflow,
)
# Entry points workflow (Scenario 16)
from src.workflow.scenarios.security import entry_points_workflow


def build_multi_scenario_graph() -> StateGraph:
    """
    Build the multi-scenario LangGraph workflow.

    Graph Structure:
        START
          |
          v
        [classify_intent]
          |
          v
        <route_by_intent> (conditional)
          |
          +-- onboarding_workflow
          +-- security_workflow
          +-- documentation_workflow
          +-- feature_dev_workflow
          +-- ... (10 more workflows)
          |
          v
        END
    """
    # Create graph
    workflow = StateGraph(MultiScenarioState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)

    # Add scenario workflow nodes (Week 1 - implemented)
    workflow.add_node("onboarding_workflow", onboarding_workflow)
    workflow.add_node("documentation_workflow", documentation_workflow)
    workflow.add_node("feature_dev_workflow", feature_dev_workflow)

    # Add placeholder workflow nodes (Week 2-4)
    workflow.add_node("security_workflow", security_workflow)
    workflow.add_node("refactoring_workflow", refactoring_workflow)
    workflow.add_node("performance_workflow", performance_workflow)
    workflow.add_node("test_coverage_workflow", test_coverage_workflow)
    workflow.add_node("compliance_workflow", compliance_workflow)
    workflow.add_node("code_review_workflow", code_review_workflow)
    workflow.add_node("cross_repo_workflow", cross_repo_workflow)
    workflow.add_node("architecture_workflow", architecture_workflow)
    workflow.add_node("tech_debt_workflow", tech_debt_workflow)
    workflow.add_node("mass_refactoring_workflow", mass_refactoring_workflow)
    workflow.add_node("security_incident_workflow", security_incident_workflow)
    workflow.add_node("debugging_workflow", debugging_workflow)
    # S08 FIX: Add dedicated entry points workflow
    workflow.add_node("entry_points_workflow", entry_points_workflow)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Add conditional edges from intent classifier to scenario workflows
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "onboarding_workflow": "onboarding_workflow",
            "security_workflow": "security_workflow",
            "documentation_workflow": "documentation_workflow",
            "feature_dev_workflow": "feature_dev_workflow",
            "refactoring_workflow": "refactoring_workflow",
            "performance_workflow": "performance_workflow",
            "test_coverage_workflow": "test_coverage_workflow",
            "compliance_workflow": "compliance_workflow",
            "code_review_workflow": "code_review_workflow",
            "cross_repo_workflow": "cross_repo_workflow",
            "architecture_workflow": "architecture_workflow",
            "tech_debt_workflow": "tech_debt_workflow",
            "mass_refactoring_workflow": "mass_refactoring_workflow",
            "security_incident_workflow": "security_incident_workflow",
            "debugging_workflow": "debugging_workflow",
            # S08 FIX: Add entry_points_workflow routing
            "entry_points_workflow": "entry_points_workflow"
        }
    )

    # All workflows end at END
    for workflow_name in [
        "onboarding_workflow", "security_workflow", "documentation_workflow",
        "feature_dev_workflow", "refactoring_workflow", "performance_workflow",
        "test_coverage_workflow", "compliance_workflow", "code_review_workflow",
        "cross_repo_workflow", "architecture_workflow", "tech_debt_workflow",
        "mass_refactoring_workflow", "security_incident_workflow", "debugging_workflow",
        "entry_points_workflow"  # S08 FIX
    ]:
        workflow.add_edge(workflow_name, END)

    # Compile graph
    return workflow.compile()
