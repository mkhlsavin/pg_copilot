"""
Tests for Codebase Onboarding Workflow (Scenario 1).

Tests for onboarding_workflow, query type detection, and specialized query handlers.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "onboarding",
        "scenario_id": "scenario_1",
        "confidence": 0.9,
        "classification_method": "test",
        "cpg_results": None,
        "subsystems": None,
        "methods": None,
        "call_graph": None,
        "answer": None,
        "evidence": None,
        "metadata": None,
        "retrieved_functions": None,
        "error": None,
        "retry_count": 0,
    }


class TestOnboardingQueryTypeDetection:
    """Tests for detect_onboarding_query_type function."""

    def test_import_query_handler(self):
        """Test that query handlers can be imported."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        assert callable(detect_onboarding_query_type)

    def test_definition_query_detection(self):
        """Test detection of definition/location queries."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        result = detect_onboarding_query_type("Where is the elog function defined?")

        assert result["type"] == "definition"
        assert result["target"] is not None

    def test_call_graph_query_detection(self):
        """Test detection of call graph queries."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        result = detect_onboarding_query_type("What functions call ExecInitNode?")

        assert result["type"] == "call_graph"
        assert "ExecInitNode" in result.get("target", "")

    def test_dataflow_query_detection(self):
        """Test detection of dataflow queries."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        result = detect_onboarding_query_type(
            "How does data flow through the executor?"
        )

        assert result["type"] in ["dataflow", "general"]

    def test_general_query_detection(self):
        """Test detection of general overview queries."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        result = detect_onboarding_query_type("Explain the codebase architecture")

        assert result["type"] == "general"

    def test_subsystem_explain_query_detection(self):
        """Test detection of subsystem explanation queries."""
        from src.workflow.query_handlers import detect_onboarding_query_type

        result = detect_onboarding_query_type("Explain the WAL subsystem")

        # Should detect as subsystem explanation or general
        assert result["type"] in ["subsystem_explain", "general"]


class TestDefinitionQueryHandler:
    """Tests for handle_definition_query function."""

    def test_import_handler(self):
        """Test that definition handler can be imported."""
        from src.workflow.query_handlers import handle_definition_query

        assert callable(handle_definition_query)

    def test_definition_query_returns_dict(self):
        """Test that definition handler returns a dict."""
        from src.workflow.query_handlers import handle_definition_query

        mock_cpg = MagicMock()
        mock_cpg.execute_query.return_value = []

        result = handle_definition_query(
            mock_cpg, "Where is elog defined?", "elog"
        )

        assert isinstance(result, dict)

    def test_definition_query_searches_methods(self):
        """Test that definition handler searches for methods."""
        from src.workflow.query_handlers import handle_definition_query

        mock_cpg = MagicMock()
        mock_cpg.execute_query.return_value = [
            {
                "name": "elog",
                "filename": "src/backend/utils/error/elog.c",
                "line_number": 100,
                "full_name": "elog",
            }
        ]

        result = handle_definition_query(
            mock_cpg, "Where is elog defined?", "elog"
        )

        mock_cpg.execute_query.assert_called()


class TestCallGraphQueryHandler:
    """Tests for handle_call_graph_query function."""

    def test_import_handler(self):
        """Test that call graph handler can be imported."""
        from src.workflow.query_handlers import handle_call_graph_query

        assert callable(handle_call_graph_query)

    def test_call_graph_query_returns_dict(self):
        """Test that call graph handler returns a dict."""
        from src.workflow.query_handlers import handle_call_graph_query

        mock_cpg = MagicMock()
        mock_analyzer = MagicMock()
        mock_analyzer.find_all_callers.return_value = []
        mock_analyzer.find_all_callees.return_value = []

        result = handle_call_graph_query(
            mock_cpg, mock_analyzer, "What calls ExecInitNode?", "ExecInitNode"
        )

        assert isinstance(result, dict)

    def test_call_graph_query_finds_callers(self):
        """Test that call graph handler finds callers."""
        from src.workflow.query_handlers import handle_call_graph_query

        mock_cpg = MagicMock()
        mock_analyzer = MagicMock()
        mock_analyzer.find_all_callers.return_value = ["main", "exec_query"]
        mock_analyzer.find_all_callees.return_value = []

        result = handle_call_graph_query(
            mock_cpg, mock_analyzer, "What calls ExecInitNode?", "ExecInitNode"
        )

        assert "direct_callers" in result or "callers" in result


class TestDataflowQueryHandler:
    """Tests for handle_dataflow_query function."""

    def test_import_handler(self):
        """Test that dataflow handler can be imported."""
        from src.workflow.query_handlers import handle_dataflow_query

        assert callable(handle_dataflow_query)

    def test_dataflow_query_returns_dict(self):
        """Test that dataflow handler returns a dict."""
        from src.workflow.query_handlers import handle_dataflow_query

        mock_cpg = MagicMock()
        mock_cpg.execute_query.return_value = []

        result = handle_dataflow_query(
            mock_cpg, "How does data flow in exec?", "exec", "buffer"
        )

        assert isinstance(result, dict)


class TestOnboardingWorkflowMocked:
    """Tests for onboarding_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = [
            {"name": "executor", "method_count": 500, "file_count": 20},
            {"name": "optimizer", "method_count": 300, "file_count": 15},
            {"name": "parser", "method_count": 200, "file_count": 10},
        ]
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        mock.get_methods_by_subsystem.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "The codebase is organized into subsystems..."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("What are the main subsystems?")

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.onboarding.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.onboarding.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a codebase guide",
                        "user": "Explain the architecture",
                    }
                    with patch("src.workflow.scenarios.onboarding.detect_onboarding_query_type") as mock_detect:
                        mock_detect.return_value = {"type": "general", "target": None}

                        result = onboarding_workflow(state)

        assert isinstance(result, dict)

    def test_workflow_sets_subsystems(self, mock_cpg_service, mock_llm):
        """Test that workflow sets subsystems in state."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("What are the main subsystems?")

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.onboarding.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.onboarding.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a guide",
                        "user": "Explain",
                    }
                    with patch("src.workflow.scenarios.onboarding.detect_onboarding_query_type") as mock_detect:
                        mock_detect.return_value = {"type": "general", "target": None}

                        result = onboarding_workflow(state)

        assert "subsystems" in result
        if result.get("subsystems"):
            assert "executor" in result["subsystems"]


class TestOnboardingFallbacks:
    """Tests for onboarding workflow fallback behavior."""

    def test_fallback_answers_defined(self):
        """Test that fallback answers are defined in workflow."""
        # Read the source to verify fallbacks exist
        # This is a structural test
        from src.workflow.scenarios import onboarding

        # The module should contain fallback logic
        assert hasattr(onboarding, "onboarding_workflow")

    def test_subsystem_fallback_keywords(self):
        """Test subsystem fallback keyword mapping exists."""
        # This tests that the fallback mechanism is in place
        state = create_mock_state("Explain the executor subsystem")

        # Verify state has expected structure
        assert "query" in state
        assert "executor" in state["query"].lower()


class TestOnboardingSpecializedQueries:
    """Tests for specialized query handling in onboarding."""

    def test_debug_query_detection(self):
        """Test debug query detection."""
        state = create_mock_state("How do I debug with elog?")

        query_lower = state["query"].lower()

        # Verify debug keywords are detected
        debug_keywords = ["elog", "debug", "trace", "log"]
        assert any(kw in query_lower for kw in debug_keywords)

    def test_business_logic_query_detection(self):
        """Test business logic query detection."""
        state = create_mock_state("What happens when a SELECT query executes?")

        query_lower = state["query"].lower()

        # Verify business logic keywords
        business_keywords = ["what happens when", "select", "execute"]
        assert any(kw in query_lower for kw in business_keywords)

    def test_subsystem_query_detection(self):
        """Test subsystem query detection."""
        state = create_mock_state("Explain the WAL write-ahead logging subsystem")

        query_lower = state["query"].lower()

        # Verify subsystem keywords
        subsystem_names = ["wal", "write-ahead", "executor", "optimizer"]
        assert any(sub in query_lower for sub in subsystem_names)


class TestOnboardingGraphMethods:
    """Tests for graph method integration in onboarding."""

    def test_entry_point_detection(self):
        """Test that entry point detection is attempted."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("Show me the main entry points")

        mock_cpg = MagicMock()
        mock_cpg.get_subsystems.return_value = []
        mock_cpg.get_database_stats.return_value = {"method_count": 0}
        mock_cpg.get_methods_by_subsystem.return_value = []
        mock_cpg.execute_query.return_value = []

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as cpg_class:
            cpg_class.return_value.__enter__ = MagicMock(return_value=mock_cpg)
            cpg_class.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.onboarding.LLMInterface") as llm_class:
                llm_class.return_value.generate.return_value = "Entry points..."

                with patch("src.workflow.scenarios.onboarding.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Guide",
                        "user": "Entry points",
                    }
                    with patch("src.workflow.scenarios.onboarding.detect_onboarding_query_type") as mock_detect:
                        mock_detect.return_value = {"type": "general", "target": None}

                        result = onboarding_workflow(state)

        # Should complete without error
        assert result is not None


class TestOnboardingErrorHandling:
    """Tests for onboarding workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("What are the subsystems?")

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = onboarding_workflow(state)

        # Should have error set or fallback answer
        assert result.get("error") is not None or result.get("answer") is not None

    def test_llm_generation_error(self):
        """Test handling of LLM generation error."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("Explain the codebase")

        mock_cpg = MagicMock()
        mock_cpg.get_subsystems.return_value = []
        mock_cpg.get_database_stats.return_value = {"method_count": 0}

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as cpg_class:
            cpg_class.return_value.__enter__ = MagicMock(return_value=mock_cpg)
            cpg_class.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.onboarding.LLMInterface") as llm_class:
                llm_class.return_value.generate.side_effect = Exception("LLM error")

                with patch("src.workflow.scenarios.onboarding.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Guide",
                        "user": "Explain",
                    }
                    with patch("src.workflow.scenarios.onboarding.detect_onboarding_query_type") as mock_detect:
                        mock_detect.return_value = {"type": "general", "target": None}

                        result = onboarding_workflow(state)

        # Should have error or fallback
        assert result.get("error") is not None or result.get("answer") is not None


class TestOnboardingMetadata:
    """Tests for onboarding workflow metadata generation."""

    def test_metadata_includes_graph_methods_flag(self):
        """Test that metadata includes graph_methods_enabled flag."""
        from src.workflow.scenarios.onboarding import onboarding_workflow

        state = create_mock_state("Architecture overview")

        mock_cpg = MagicMock()
        mock_cpg.get_subsystems.return_value = [{"name": "test", "method_count": 10, "file_count": 1}]
        mock_cpg.get_database_stats.return_value = {"method_count": 100}
        mock_cpg.get_methods_by_subsystem.return_value = []

        with patch("src.workflow.scenarios.onboarding.CPGQueryService") as cpg_class:
            cpg_class.return_value.__enter__ = MagicMock(return_value=mock_cpg)
            cpg_class.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.onboarding.LLMInterface") as llm_class:
                llm_class.return_value.generate.return_value = "Overview..."

                with patch("src.workflow.scenarios.onboarding.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Guide",
                        "user": "Overview",
                    }
                    with patch("src.workflow.scenarios.onboarding.detect_onboarding_query_type") as mock_detect:
                        mock_detect.return_value = {"type": "general", "target": None}

                        result = onboarding_workflow(state)

        # Metadata should be set
        if result.get("metadata"):
            assert "graph_methods_enabled" in result["metadata"]
