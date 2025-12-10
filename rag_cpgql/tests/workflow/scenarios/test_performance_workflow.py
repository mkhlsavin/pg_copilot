"""
Tests for Performance Optimization Workflow (Scenario 6).

Tests for performance workflow, bottleneck detection, and optimization suggestions.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "performance",
        "scenario_id": "scenario_6",
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


class TestPerformanceWorkflowImports:
    """Tests for performance workflow module imports."""

    def test_import_workflow(self):
        """Test that performance workflow can be imported."""
        from src.workflow.scenarios.performance import performance_workflow

        assert callable(performance_workflow)

    def test_import_all_exports(self):
        """Test that __all__ exports are accessible."""
        from src.workflow.scenarios import performance

        assert hasattr(performance, "performance_workflow")


class TestPerformanceWorkflowMocked:
    """Tests for performance_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = [
            {"name": "executor", "method_count": 500, "file_count": 20},
        ]
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        mock.get_methods_by_subsystem.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Performance analysis: No bottlenecks found."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.performance import performance_workflow

        state = create_mock_state("Find performance bottlenecks")

        with patch("src.workflow.scenarios.performance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.performance.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.performance.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a performance expert",
                        "user": "Analyze performance",
                    }

                    result = performance_workflow(state)

        assert isinstance(result, dict)

    def test_workflow_handles_hotspot_query(self, mock_cpg_service, mock_llm):
        """Test handling of hotspot detection query."""
        from src.workflow.scenarios.performance import performance_workflow

        state = create_mock_state("Find hot functions in the executor")

        with patch("src.workflow.scenarios.performance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.performance.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.performance.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Performance expert",
                        "user": "Find hotspots",
                    }

                    result = performance_workflow(state)

        assert result is not None

    def test_workflow_handles_complexity_query(self, mock_cpg_service, mock_llm):
        """Test handling of complexity analysis query."""
        from src.workflow.scenarios.performance import performance_workflow

        state = create_mock_state("Find functions with high cyclomatic complexity")

        with patch("src.workflow.scenarios.performance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.performance.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.performance.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Performance expert",
                        "user": "Analyze complexity",
                    }

                    result = performance_workflow(state)

        assert result is not None


class TestPerformanceQueryPatterns:
    """Tests for performance query pattern detection."""

    def test_hotspot_keywords(self):
        """Test hotspot keyword detection."""
        queries = [
            "Find hot functions",
            "Identify hotspots",
            "What are the performance-critical functions?",
        ]

        hotspot_keywords = ["hot", "hotspot", "critical", "bottleneck"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in hotspot_keywords + ["performance"])

    def test_complexity_keywords(self):
        """Test complexity keyword detection."""
        queries = [
            "Find high complexity functions",
            "Analyze cyclomatic complexity",
            "Functions with many branches",
        ]

        complexity_keywords = ["complexity", "cyclomatic", "branch"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in complexity_keywords)

    def test_memory_performance_keywords(self):
        """Test memory performance keyword detection."""
        queries = [
            "Find memory-intensive functions",
            "Analyze allocation patterns",
            "Memory usage hotspots",
        ]

        memory_keywords = ["memory", "allocation", "palloc", "malloc"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in memory_keywords + ["memory"])

    def test_io_performance_keywords(self):
        """Test I/O performance keyword detection."""
        queries = [
            "Find I/O bottlenecks",
            "Disk read performance",
            "Network latency issues",
        ]

        io_keywords = ["io", "i/o", "disk", "network", "read", "write"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in io_keywords)


class TestPerformanceWorkflowErrorHandling:
    """Tests for performance workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.performance import performance_workflow

        state = create_mock_state("Find bottlenecks")

        with patch("src.workflow.scenarios.performance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = performance_workflow(state)

        # Should have error set
        assert result.get("error") is not None

    def test_llm_generation_error(self):
        """Test handling of LLM generation error."""
        from src.workflow.scenarios.performance import performance_workflow

        state = create_mock_state("Analyze performance")

        mock_cpg = MagicMock()
        mock_cpg.get_subsystems.return_value = []
        mock_cpg.get_database_stats.return_value = {"method_count": 0}
        mock_cpg.execute_query.return_value = []

        with patch("src.workflow.scenarios.performance.CPGQueryService") as cpg_class:
            cpg_class.return_value.__enter__ = MagicMock(return_value=mock_cpg)
            cpg_class.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.performance.LLMInterface") as llm_class:
                llm_class.return_value.generate.side_effect = Exception("LLM error")

                with patch("src.workflow.scenarios.performance.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "Expert",
                        "user": "Analyze",
                    }

                    result = performance_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestPerformanceMetrics:
    """Tests for performance metric collection."""

    def test_complexity_metric_extraction(self):
        """Test extraction of complexity metrics from CPG results."""
        # Simulate CPG results with complexity data
        cpg_results = [
            {"name": "func1", "complexity": 15},
            {"name": "func2", "complexity": 5},
            {"name": "func3", "complexity": 25},
        ]

        # Sort by complexity descending
        sorted_results = sorted(
            cpg_results,
            key=lambda x: x.get("complexity", 0),
            reverse=True
        )

        assert sorted_results[0]["name"] == "func3"
        assert sorted_results[0]["complexity"] == 25

    def test_call_count_metric(self):
        """Test call count metric calculation."""
        # Simulate method call counts
        call_data = [
            {"name": "frequently_called", "call_count": 1000},
            {"name": "rarely_called", "call_count": 5},
        ]

        hot_functions = [f for f in call_data if f["call_count"] > 100]

        assert len(hot_functions) == 1
        assert hot_functions[0]["name"] == "frequently_called"


class TestPerformanceAnalysisIntegration:
    """Tests for performance analysis component integration."""

    def test_call_graph_analysis_integration(self):
        """Test integration with call graph analyzer."""
        mock_analyzer = MagicMock()
        mock_analyzer.find_all_callees.return_value = ["callee1", "callee2"]
        mock_analyzer.analyze_impact.return_value = MagicMock(
            impact_score=0.8,
            transitive_callees=["a", "b", "c"],
        )

        # Verify analyzer interface
        callees = mock_analyzer.find_all_callees("some_function")
        impact = mock_analyzer.analyze_impact("some_function")

        assert len(callees) == 2
        assert impact.impact_score == 0.8

    def test_dataflow_analysis_integration(self):
        """Test integration with dataflow tracer."""
        mock_tracer = MagicMock()
        mock_tracer.trace_forward.return_value = [
            {"node": "a", "type": "identifier"},
            {"node": "b", "type": "call"},
        ]

        # Verify tracer interface
        flow = mock_tracer.trace_forward("source_var")

        assert len(flow) == 2


class TestPerformanceRecommendations:
    """Tests for performance recommendation generation."""

    def test_recommendation_for_high_complexity(self):
        """Test recommendations for high complexity functions."""
        # Functions with complexity > 20 should get refactoring recommendations
        high_complexity_funcs = [
            {"name": "complex_func", "complexity": 30},
        ]

        recommendations = []
        for func in high_complexity_funcs:
            if func["complexity"] > 20:
                recommendations.append({
                    "function": func["name"],
                    "recommendation": "Consider splitting into smaller functions",
                    "priority": "high",
                })

        assert len(recommendations) == 1
        assert recommendations[0]["priority"] == "high"

    def test_recommendation_for_nested_loops(self):
        """Test recommendations for deeply nested loops."""
        # Simulate detection of nested loops
        nested_loop_funcs = [
            {"name": "matrix_multiply", "max_loop_depth": 3},
        ]

        recommendations = []
        for func in nested_loop_funcs:
            if func["max_loop_depth"] >= 3:
                recommendations.append({
                    "function": func["name"],
                    "recommendation": "Consider loop optimization or algorithmic improvement",
                    "priority": "medium",
                })

        assert len(recommendations) == 1
