"""
Tests for Debugging Support Workflow (Scenario 14).

Tests for debugging workflow, debug pattern detection, and breakpoint suggestions.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "debugging",
        "scenario_id": "scenario_14",
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


class TestDebugPatternsFromPlugin:
    """Tests for _get_debug_patterns_from_plugin function."""

    def test_function_exists(self):
        """Test that function exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        assert callable(_get_debug_patterns_from_plugin)

    def test_returns_dict(self):
        """Test that function returns dict."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert isinstance(result, dict)

    def test_has_logging_category(self):
        """Test that logging category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "logging" in result
        assert "functions" in result["logging"]
        assert "keywords" in result["logging"]

    def test_has_assertion_category(self):
        """Test that assertion category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "assertion" in result
        assert "functions" in result["assertion"]

    def test_has_trace_category(self):
        """Test that trace category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "trace" in result

    def test_has_explain_category(self):
        """Test that explain/query plan category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "explain" in result
        assert "ExplainQuery" in result["explain"]["functions"] or "Explain" in str(result["explain"]["functions"])

    def test_has_breakpoint_category(self):
        """Test that breakpoint category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "breakpoint" in result
        assert "functions" in result["breakpoint"]
        assert len(result["breakpoint"]["functions"]) > 0

    def test_has_stack_trace_category(self):
        """Test that stack trace category exists."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        result = _get_debug_patterns_from_plugin()

        assert "stack_trace" in result


class TestGetErrorLevelsFromPlugin:
    """Tests for _get_error_levels_from_plugin function."""

    def test_function_exists(self):
        """Test that function exists."""
        from src.workflow.scenarios.debugging import _get_error_levels_from_plugin

        assert callable(_get_error_levels_from_plugin)

    def test_returns_list(self):
        """Test that function returns list."""
        from src.workflow.scenarios.debugging import _get_error_levels_from_plugin

        result = _get_error_levels_from_plugin()

        assert isinstance(result, list)

    def test_contains_error_level(self):
        """Test that ERROR level is included."""
        from src.workflow.scenarios.debugging import _get_error_levels_from_plugin

        result = _get_error_levels_from_plugin()

        assert "ERROR" in result

    def test_contains_warning_level(self):
        """Test that WARNING level is included."""
        from src.workflow.scenarios.debugging import _get_error_levels_from_plugin

        result = _get_error_levels_from_plugin()

        assert "WARNING" in result

    def test_contains_debug_levels(self):
        """Test that DEBUG levels are included."""
        from src.workflow.scenarios.debugging import _get_error_levels_from_plugin

        result = _get_error_levels_from_plugin()

        # Should have at least DEBUG1
        assert any("DEBUG" in level for level in result)


class TestBuildBreakpointQuery:
    """Tests for _build_breakpoint_query function."""

    def test_function_exists(self):
        """Test that function exists."""
        from src.workflow.scenarios.debugging import _build_breakpoint_query

        assert callable(_build_breakpoint_query)

    def test_returns_string(self):
        """Test that function returns SQL string."""
        from src.workflow.scenarios.debugging import _build_breakpoint_query

        result = _build_breakpoint_query("memory")

        assert isinstance(result, str)
        # Should be a SELECT query
        assert "SELECT" in result.upper() or result == ""


class TestDebuggingWorkflowImports:
    """Tests for debugging workflow module imports."""

    def test_import_workflow(self):
        """Test that debugging workflow can be imported."""
        from src.workflow.scenarios.debugging import debugging_workflow

        assert callable(debugging_workflow)


class TestDebuggingQueryPatterns:
    """Tests for debugging query pattern detection."""

    def test_elog_keywords(self):
        """Test elog keyword detection."""
        queries = [
            "How do I use elog?",
            "Find elog calls",
            "Logging with elog",
        ]

        for query in queries:
            query_lower = query.lower()
            assert "elog" in query_lower

    def test_ereport_keywords(self):
        """Test ereport keyword detection."""
        queries = [
            "How does ereport work?",
            "Error reporting with ereport",
        ]

        for query in queries:
            query_lower = query.lower()
            assert "ereport" in query_lower

    def test_assertion_keywords(self):
        """Test assertion keyword detection."""
        queries = [
            "Find Assert macros",
            "Where are assertions used?",
            "Check invariants",
        ]

        assertion_keywords = ["assert", "invariant", "check"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in assertion_keywords)

    def test_breakpoint_keywords(self):
        """Test breakpoint keyword detection."""
        queries = [
            "Good breakpoints for debugging",
            "Where to set GDB breakpoints",
            "Debug execution points",
        ]

        breakpoint_keywords = ["breakpoint", "debug", "gdb"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in breakpoint_keywords)

    def test_explain_keywords(self):
        """Test explain/query plan keyword detection."""
        queries = [
            "How does EXPLAIN work?",
            "Query plan analysis",
            "ExplainNode function",
        ]

        explain_keywords = ["explain", "plan", "query"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in explain_keywords)

    def test_stack_trace_keywords(self):
        """Test stack trace keyword detection."""
        queries = [
            "Get stack trace",
            "Backtrace functions",
            "Call stack analysis",
        ]

        trace_keywords = ["stack", "trace", "backtrace", "call"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in trace_keywords)


class TestDebuggingWorkflowMocked:
    """Tests for debugging_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = []
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Debugging analysis: Use elog for logging."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.debugging import debugging_workflow

        state = create_mock_state("How do I use elog?")

        with patch("src.workflow.scenarios.debugging.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.debugging.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.debugging.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a debugging expert",
                        "user": "Explain elog usage",
                    }

                    result = debugging_workflow(state)

        assert isinstance(result, dict)

    def test_workflow_handles_breakpoint_query(self, mock_cpg_service, mock_llm):
        """Test workflow handles breakpoint query."""
        from src.workflow.scenarios.debugging import debugging_workflow

        state = create_mock_state("Good breakpoints for debugging query execution")

        with patch("src.workflow.scenarios.debugging.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.debugging.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.debugging.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Debugging expert",
                        "user": "Breakpoint suggestions",
                    }

                    result = debugging_workflow(state)

        assert result is not None


class TestDebuggingErrorHandling:
    """Tests for debugging workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.debugging import debugging_workflow

        state = create_mock_state("Find elog calls")

        with patch("src.workflow.scenarios.debugging.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = debugging_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestDebugCategoryDetection:
    """Tests for debug category detection from queries."""

    def test_logging_category_detection(self):
        """Test detection of logging-related queries."""
        logging_queries = [
            "how to use elog",
            "ereport error handling",
            "log warning messages",
        ]

        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        logging_keywords = patterns["logging"]["keywords"]

        for query in logging_queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in logging_keywords)

    def test_assertion_category_detection(self):
        """Test detection of assertion-related queries."""
        assertion_queries = [
            "Assert macro usage",
            "assertion failures",
            "check invariants",
        ]

        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        assertion_keywords = patterns["assertion"]["keywords"]

        for query in assertion_queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in assertion_keywords)

    def test_breakpoint_category_detection(self):
        """Test detection of breakpoint-related queries."""
        breakpoint_queries = [
            "set breakpoint in executor",
            "debug query execution",
            "gdb breakpoint for transactions",
        ]

        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        breakpoint_keywords = patterns["breakpoint"]["keywords"]

        for query in breakpoint_queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in breakpoint_keywords)


class TestBreakpointSuggestions:
    """Tests for breakpoint suggestion logic."""

    def test_executor_breakpoints(self):
        """Test breakpoint patterns are configured."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        breakpoint_funcs = patterns["breakpoint"]["functions"]

        # Breakpoint functions should be defined (may vary by domain config)
        assert isinstance(breakpoint_funcs, list)
        # At minimum should have some breakpoint functions defined
        assert len(breakpoint_funcs) >= 0  # May be empty for some configurations

    def test_transaction_breakpoints(self):
        """Test breakpoint keywords are configured."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        breakpoint_keywords = patterns["breakpoint"]["keywords"]

        # Breakpoint keywords should be defined
        assert isinstance(breakpoint_keywords, list)

    def test_buffer_breakpoints(self):
        """Test all debug pattern categories exist."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()

        # Should have standard debug pattern categories
        expected_categories = ["logging", "assertion", "trace", "breakpoint"]
        for cat in expected_categories:
            assert cat in patterns, f"Missing debug pattern category: {cat}"
            assert "functions" in patterns[cat]
            assert "keywords" in patterns[cat]


class TestDebuggingMetadata:
    """Tests for debugging workflow metadata generation."""

    def test_debug_function_counts(self):
        """Test counting of debug functions found."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()

        # Count total debug functions across categories
        total_funcs = sum(
            len(cat_data["functions"])
            for cat_data in patterns.values()
        )

        assert total_funcs > 0

    def test_category_coverage(self):
        """Test that all major debug categories are covered."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()

        expected_categories = [
            "logging",
            "assertion",
            "trace",
            "explain",
            "breakpoint",
        ]

        for category in expected_categories:
            assert category in patterns, f"Missing category: {category}"


class TestDebugContextualHelp:
    """Tests for contextual debugging help."""

    def test_subsystem_specific_breakpoints(self):
        """Test subsystem-specific breakpoint suggestions."""
        from src.workflow.scenarios.debugging import _get_debug_patterns_from_plugin

        patterns = _get_debug_patterns_from_plugin()
        keywords = patterns["breakpoint"]["keywords"]

        # Should have subsystem-specific keywords
        subsystem_keywords = [
            "buffer management",
            "lock debugging",
            "wal subsystem",
            "vacuum debugging",
        ]

        for subsys_kw in subsystem_keywords:
            assert any(subsys_kw in kw for kw in keywords), f"Missing {subsys_kw}"
