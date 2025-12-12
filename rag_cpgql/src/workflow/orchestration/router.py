"""
Intent-Based Router for Multi-Scenario Workflow.

Routes classified queries to scenario-specific workflow nodes.
"""

import logging

from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)


def route_by_intent(state: MultiScenarioState) -> str:
    """
    Conditional edge function that routes to scenario-specific workflows.

    Routes based on classified intent from IntentClassifier.
    Supports 16 enterprise scenarios via INTENT_TAXONOMY.

    Returns:
        Next node name based on intent
    """
    intent = state.get('intent', 'onboarding')

    # Map intents to workflow nodes (16 scenarios)
    routing_map = {
        'onboarding': 'onboarding_workflow',
        'security_audit': 'security_workflow',
        'documentation': 'documentation_workflow',
        'feature_development': 'feature_dev_workflow',
        'refactoring': 'refactoring_workflow',
        'performance': 'performance_workflow',
        'test_coverage': 'test_coverage_workflow',
        'compliance': 'compliance_workflow',
        'code_review': 'code_review_workflow',
        'cross_repo_impact': 'cross_repo_workflow',
        'architecture_violations': 'architecture_workflow',
        'tech_debt': 'tech_debt_workflow',
        'mass_refactoring': 'mass_refactoring_workflow',
        'security_incident': 'security_incident_workflow',
        'debugging': 'debugging_workflow',
        'entry_points': 'entry_points_workflow',
    }

    next_node = routing_map.get(intent, 'onboarding_workflow')
    logger.info(f"Routing to: {next_node}")

    return next_node
