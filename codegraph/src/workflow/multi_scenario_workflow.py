"""
Multi-Scenario LangGraph Workflow for 16+ Enterprise Scenarios.

This module provides backward compatibility by re-exporting from the orchestration package.

The orchestration package contains:
- intent_classifier.py - Intent classification node
- router.py - Intent-based routing
- graph_builder.py - LangGraph workflow builder
- copilot.py - MultiScenarioCopilot interface

For new code, import directly from src.workflow.orchestration.
"""

# Re-export from orchestration package for backward compatibility
from src.workflow.orchestration import (
    classify_intent_node,
    route_by_intent,
    build_multi_scenario_graph,
    MultiScenarioCopilot,
)

# Re-export state for backward compatibility
from src.workflow.state import MultiScenarioState

# Re-export all scenario workflows for backward compatibility
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

__all__ = [
    # Core orchestration
    'classify_intent_node',
    'route_by_intent',
    'build_multi_scenario_graph',
    'MultiScenarioCopilot',
    'MultiScenarioState',
    # Scenario workflows
    'security_workflow',
    'performance_workflow',
    'refactoring_workflow',
    'onboarding_workflow',
    'documentation_workflow',
    'feature_dev_workflow',
    'test_coverage_workflow',
    'code_review_workflow',
    'compliance_workflow',
    'security_incident_workflow',
    'cross_repo_workflow',
    'large_scale_refactoring_workflow',
    'architecture_workflow',
    'tech_debt_workflow',
    'mass_refactoring_workflow',
    'debugging_workflow',
]


if __name__ == "__main__":
    # Demo execution
    copilot = MultiScenarioCopilot()

    # Test queries for different scenarios
    test_queries = [
        "Give me an overview of the PostgreSQL executor",  # Onboarding
        "Generate documentation for the planner module",   # Documentation
        "Where should I add a new join algorithm?",        # Feature Dev
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")

        result = copilot.run(query)

        print(f"Intent: {result.get('intent')}")
        print(f"Confidence: {result.get('confidence'):.2f}")
        print(f"Method: {result.get('classification_method')}\n")
        print(f"Answer:\n{result.get('answer')}\n")

        if result.get('evidence'):
            print(f"Evidence:")
            for evidence in result['evidence']:
                print(f"  - {evidence}")
