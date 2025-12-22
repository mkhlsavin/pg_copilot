"""
Tests for Multi-Scenario Workflow.

Tests for MultiScenarioCopilot, intent classification, and scenario routing.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any


class MockLLMInterface:
    """Mock LLM interface for testing."""

    def __init__(self, response: str = "Test response"):
        self.response = response

    def generate(self, prompt: str, **kwargs) -> str:
        return self.response


class MockIntentClassifier:
    """Mock intent classifier for testing."""

    def __init__(self, intent: str = "onboarding", confidence: float = 0.9):
        self._intent = intent
        self._confidence = confidence

    def classify(self, query: str, context: Dict = None) -> Dict[str, Any]:
        return {
            "intent": self._intent,
            "scenario_id": f"scenario_{self._intent}",
            "confidence": self._confidence,
            "method": "mock",
        }


class TestClassifyIntentNode:
    """Tests for classify_intent_node function."""

    def test_classify_intent_success(self):
        """Test successful intent classification."""
        from src.workflow.multi_scenario_workflow import classify_intent_node

        state = {
            "query": "What are the main subsystems in the codebase?",
            "context": None,
            "intent": None,
            "scenario_id": None,
            "confidence": None,
            "classification_method": None,
        }

        with patch(
            "src.workflow.orchestration.intent_classifier.IntentClassifier"
        ) as mock_classifier_class:
            mock_classifier = MockIntentClassifier(
                intent="onboarding",
                confidence=0.85
            )
            mock_classifier_class.return_value = mock_classifier

            with patch(
                "src.workflow.orchestration.intent_classifier.LLMInterface"
            ) as mock_llm:
                mock_llm.return_value = MockLLMInterface()

                result = classify_intent_node(state)

        assert result["intent"] == "onboarding"
        assert result["confidence"] == 0.85
        assert result["classification_method"] == "mock"

    def test_classify_intent_error_fallback(self):
        """Test fallback behavior on classification error."""
        from src.workflow.multi_scenario_workflow import classify_intent_node

        state = {
            "query": "Some query",
            "context": None,
            "intent": None,
            "scenario_id": None,
            "confidence": None,
            "classification_method": None,
        }

        with patch(
            "src.workflow.orchestration.intent_classifier.IntentClassifier"
        ) as mock_classifier_class:
            mock_classifier_class.side_effect = Exception("Classification failed")

            with patch(
                "src.workflow.orchestration.intent_classifier.LLMInterface"
            ):
                result = classify_intent_node(state)

        # Should fallback to onboarding
        assert result["intent"] == "onboarding"
        assert result["scenario_id"] == "scenario_1"
        assert result["confidence"] == 0.3
        assert result["classification_method"] == "error_fallback"
        assert "error" in result


class TestRouteByIntent:
    """Tests for route_by_intent function."""

    def test_route_onboarding(self):
        """Test routing to onboarding workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "onboarding"}
        result = route_by_intent(state)

        assert result == "onboarding_workflow"

    def test_route_security(self):
        """Test routing to security workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "security_audit"}
        result = route_by_intent(state)

        assert result == "security_workflow"

    def test_route_documentation(self):
        """Test routing to documentation workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "documentation"}
        result = route_by_intent(state)

        assert result == "documentation_workflow"

    def test_route_feature_dev(self):
        """Test routing to feature development workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "feature_development"}
        result = route_by_intent(state)

        assert result == "feature_dev_workflow"

    def test_route_refactoring(self):
        """Test routing to refactoring workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "refactoring"}
        result = route_by_intent(state)

        assert result == "refactoring_workflow"

    def test_route_performance(self):
        """Test routing to performance workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "performance"}
        result = route_by_intent(state)

        assert result == "performance_workflow"

    def test_route_test_coverage(self):
        """Test routing to test coverage workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "test_coverage"}
        result = route_by_intent(state)

        assert result == "test_coverage_workflow"

    def test_route_compliance(self):
        """Test routing to compliance workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "compliance"}
        result = route_by_intent(state)

        assert result == "compliance_workflow"

    def test_route_code_review(self):
        """Test routing to code review workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "code_review"}
        result = route_by_intent(state)

        assert result == "code_review_workflow"

    def test_route_cross_repo(self):
        """Test routing to cross-repo workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "cross_repo_impact"}
        result = route_by_intent(state)

        assert result == "cross_repo_workflow"

    def test_route_architecture(self):
        """Test routing to architecture workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "architecture_violations"}
        result = route_by_intent(state)

        assert result == "architecture_workflow"

    def test_route_tech_debt(self):
        """Test routing to tech debt workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "tech_debt"}
        result = route_by_intent(state)

        assert result == "tech_debt_workflow"

    def test_route_mass_refactoring(self):
        """Test routing to mass refactoring workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "mass_refactoring"}
        result = route_by_intent(state)

        assert result == "mass_refactoring_workflow"

    def test_route_security_incident(self):
        """Test routing to security incident workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "security_incident"}
        result = route_by_intent(state)

        assert result == "security_incident_workflow"

    def test_route_debugging(self):
        """Test routing to debugging workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "debugging"}
        result = route_by_intent(state)

        assert result == "debugging_workflow"

    def test_route_entry_points(self):
        """Test routing to entry points workflow."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "entry_points"}
        result = route_by_intent(state)

        assert result == "entry_points_workflow"

    def test_route_unknown_defaults_to_onboarding(self):
        """Test unknown intent defaults to onboarding."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {"intent": "unknown_intent"}
        result = route_by_intent(state)

        assert result == "onboarding_workflow"

    def test_route_missing_intent_defaults_to_onboarding(self):
        """Test missing intent defaults to onboarding."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        state = {}
        result = route_by_intent(state)

        assert result == "onboarding_workflow"


class TestBuildMultiScenarioGraph:
    """Tests for build_multi_scenario_graph function."""

    def test_graph_builds_successfully(self):
        """Test that graph builds without error."""
        from src.workflow.multi_scenario_workflow import build_multi_scenario_graph

        graph = build_multi_scenario_graph()

        assert graph is not None

    def test_graph_has_entry_point(self):
        """Test that graph has entry point."""
        from src.workflow.multi_scenario_workflow import build_multi_scenario_graph

        graph = build_multi_scenario_graph()

        # Graph should be compiled and runnable
        assert hasattr(graph, "invoke")


class TestMultiScenarioCopilot:
    """Tests for MultiScenarioCopilot class."""

    def test_copilot_initialization(self):
        """Test copilot initialization."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        copilot = MultiScenarioCopilot()

        assert copilot.graph is not None

    def test_run_returns_state(self):
        """Test run method returns state dict."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch.object(
            MultiScenarioCopilot,
            "__init__",
            lambda self: None
        ):
            copilot = MultiScenarioCopilot()
            copilot.graph = MagicMock()
            copilot.graph.invoke.return_value = {
                "query": "Test query",
                "intent": "onboarding",
                "answer": "Test answer",
                "retrieved_functions": ["func1", "func2"],
            }

            with patch.object(
                copilot,
                "_extract_retrieved_functions",
                lambda state: state
            ):
                result = copilot.run("Test query")

        assert "query" in result
        assert "intent" in result
        assert "answer" in result

    def test_run_with_context(self):
        """Test run method with context parameter."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch.object(
            MultiScenarioCopilot,
            "__init__",
            lambda self: None
        ):
            copilot = MultiScenarioCopilot()
            copilot.graph = MagicMock()
            copilot.graph.invoke.return_value = {
                "query": "Test",
                "context": {"subsystem": "executor"},
            }

            with patch.object(
                copilot,
                "_extract_retrieved_functions",
                lambda state: state
            ):
                result = copilot.run("Test", context={"subsystem": "executor"})

        # Context should be passed through
        call_args = copilot.graph.invoke.call_args[0][0]
        assert call_args["context"] == {"subsystem": "executor"}


class TestExtractRetrievedFunctions:
    """Tests for function extraction from state."""

    def test_extract_from_methods(self):
        """Test extracting function names from methods."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch.object(
            MultiScenarioCopilot,
            "__init__",
            lambda self: None
        ):
            copilot = MultiScenarioCopilot()
            copilot.graph = MagicMock()

            state = {
                "methods": [
                    {"name": "method1"},
                    {"name": "method2"},
                ],
                "retrieved_functions": None,
            }

            result = copilot._extract_retrieved_functions(state)

            assert "retrieved_functions" in result
            assert "method1" in result["retrieved_functions"]

    def test_extract_from_cpg_results(self):
        """Test extracting function names from CPG results."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch.object(
            MultiScenarioCopilot,
            "__init__",
            lambda self: None
        ):
            copilot = MultiScenarioCopilot()
            copilot.graph = MagicMock()

            state = {
                "cpg_results": [
                    {"name": "func1", "filename": "test.c"},
                    {"name": "func2", "filename": "test.c"},
                ],
                "methods": None,
                "retrieved_functions": None,
            }

            result = copilot._extract_retrieved_functions(state)

            assert result is not None


class TestRoutingMap:
    """Tests for routing map completeness."""

    def test_all_scenarios_mapped(self):
        """Test that all 16 scenarios are in routing map."""
        from src.workflow.multi_scenario_workflow import route_by_intent

        # Test all known intents
        expected_intents = [
            "onboarding",
            "security_audit",
            "documentation",
            "feature_development",
            "refactoring",
            "performance",
            "test_coverage",
            "compliance",
            "code_review",
            "cross_repo_impact",
            "architecture_violations",
            "tech_debt",
            "mass_refactoring",
            "security_incident",
            "debugging",
            "entry_points",
        ]

        for intent in expected_intents:
            state = {"intent": intent}
            result = route_by_intent(state)
            assert result != "onboarding_workflow" or intent == "onboarding", \
                f"Intent '{intent}' not properly mapped"


class TestStateInitialization:
    """Tests for state initialization."""

    def test_initial_state_structure(self):
        """Test that initial state has all required fields."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch.object(
            MultiScenarioCopilot,
            "__init__",
            lambda self: None
        ):
            copilot = MultiScenarioCopilot()
            copilot.graph = MagicMock()
            copilot.graph.invoke.return_value = {}

            with patch.object(
                copilot,
                "_extract_retrieved_functions",
                lambda state: state
            ):
                # Capture the initial state passed to invoke
                copilot.run("Test query")

        call_args = copilot.graph.invoke.call_args[0][0]

        # Check required state fields
        assert "query" in call_args
        assert "context" in call_args
        assert "intent" in call_args
        assert "scenario_id" in call_args
        assert "confidence" in call_args
        assert "classification_method" in call_args
        assert "cpg_results" in call_args
        assert "subsystems" in call_args
        assert "methods" in call_args
        assert "call_graph" in call_args
        assert "answer" in call_args
        assert "evidence" in call_args
        assert "metadata" in call_args
        assert "retrieved_functions" in call_args
        assert "error" in call_args
        assert "retry_count" in call_args


class TestIntegration:
    """Integration tests for multi-scenario workflow."""

    def test_full_workflow_mock(self):
        """Test full workflow with mocked components."""
        from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

        with patch(
            "src.workflow.orchestration.intent_classifier.IntentClassifier"
        ) as mock_classifier_class:
            mock_classifier = MockIntentClassifier()
            mock_classifier_class.return_value = mock_classifier

            with patch(
                "src.workflow.orchestration.intent_classifier.LLMInterface"
            ):
                with patch(
                    "src.workflow.orchestration.copilot.CPGQueryService"
                ):
                    # Create copilot
                    copilot = MultiScenarioCopilot()

                    # This tests that the graph compiles correctly
                    assert copilot.graph is not None
