"""
Intent Classification Node for Multi-Scenario Workflow.

Entry point for classifying user queries into scenario-specific workflows.
"""

import logging
from typing import Dict, Any

from src.intent.intent_classifier import IntentClassifier
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)


def classify_intent_node(state: MultiScenarioState) -> MultiScenarioState:
    """
    Entry point: Classify user query into one of 14 scenarios.

    Updates state with:
    - intent: Intent key
    - scenario_id: Scenario ID
    - confidence: Classification confidence
    - classification_method: How it was classified
    """
    logger.info(f"Classifying query: {state['query'][:100]}...")

    try:
        # Initialize classifier (with LLM client if available)
        llm_client = LLMInterface()  # Use LLMxCPG-Q model (default)
        classifier = IntentClassifier(llm_client=llm_client)

        # Classify
        result = classifier.classify(
            query=state['query'],
            context=state.get('context')
        )

        # Update state
        state['intent'] = result['intent']
        state['scenario_id'] = result['scenario_id']
        state['confidence'] = result['confidence']
        state['classification_method'] = result['method']

        logger.info(
            f"Intent: {result['intent']} "
            f"(confidence: {result['confidence']:.2f}, "
            f"method: {result['method']})"
        )

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        # Fallback to onboarding
        state['intent'] = 'onboarding'
        state['scenario_id'] = 'scenario_1'
        state['confidence'] = 0.3
        state['classification_method'] = 'error_fallback'
        state['error'] = str(e)

    return state
