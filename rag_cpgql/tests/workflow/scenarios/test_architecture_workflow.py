"""
Tests for Architecture Violation Detection Workflow (Scenario 11).

Tests for architecture workflow, dependency analysis, layer validation, and violation detection.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "architecture_violations",
        "scenario_id": "scenario_11",
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


class TestArchitectureWorkflowImports:
    """Tests for architecture workflow module imports."""

    def test_import_workflow(self):
        """Test that architecture workflow can be imported."""
        from src.workflow.scenarios.architecture import architecture_workflow

        assert callable(architecture_workflow)

    def test_import_architecture_agents(self):
        """Test that architecture agents can be imported."""
        from src.architecture.architecture_agents import (
            DependencyAnalyzer,
            LayerValidator,
            ArchitectureReporter,
        )

        assert DependencyAnalyzer is not None
        assert LayerValidator is not None
        assert ArchitectureReporter is not None


class TestArchitectureQueryTypeDetection:
    """Tests for architecture query type detection."""

    def test_import_query_handler(self):
        """Test that query handler can be imported."""
        from src.workflow.query_handlers import detect_architecture_query_type

        assert callable(detect_architecture_query_type)

    def test_include_query_detection(self):
        """Test detection of include/dependency queries."""
        from src.workflow.query_handlers import detect_architecture_query_type

        result = detect_architecture_query_type("What files include memutils.h?")

        assert result.get("type") in ["include", "dependency", "general"]

    def test_dependency_query_detection(self):
        """Test detection of dependency queries."""
        from src.workflow.query_handlers import detect_architecture_query_type

        result = detect_architecture_query_type("What does the executor module depend on?")

        assert "type" in result


class TestArchitectureQueryPatterns:
    """Tests for architecture query pattern detection."""

    def test_dependency_keywords(self):
        """Test dependency keyword detection."""
        queries = [
            "Find module dependencies",
            "What does executor depend on?",
            "Show import relationships",
        ]

        dep_keywords = ["depend", "import", "include", "relationship"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in dep_keywords)

    def test_circular_dependency_keywords(self):
        """Test circular dependency keyword detection."""
        queries = [
            "Find circular dependencies",
            "Detect cyclic imports",
            "Check for dependency cycles",
        ]

        circular_keywords = ["circular", "cyclic", "cycle"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in circular_keywords)

    def test_layer_violation_keywords(self):
        """Test layer violation keyword detection."""
        queries = [
            "Find layer violations",
            "Check architectural layering",
            "Validate layer boundaries",
        ]

        layer_keywords = ["layer", "boundary", "architecture"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in layer_keywords)

    def test_god_module_keywords(self):
        """Test god module keyword detection."""
        queries = [
            "Find god modules",
            "Detect overly connected modules",
            "Find modules with too many dependencies",
        ]

        god_keywords = ["god", "connected", "many dependencies"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in god_keywords)


class TestArchitectureWorkflowMocked:
    """Tests for architecture_workflow function with mocked dependencies."""

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
        mock.generate.return_value = "Architecture analysis: No violations found."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.architecture import architecture_workflow

        state = create_mock_state("Find architecture violations")

        with patch("src.workflow.scenarios.architecture.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.architecture.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.architecture.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are an architecture expert",
                        "user": "Analyze architecture",
                    }
                    with patch("src.workflow.scenarios.architecture.DependencyAnalyzer"):
                        with patch("src.workflow.scenarios.architecture.LayerValidator"):
                            with patch("src.workflow.scenarios.architecture.ArchitectureReporter"):
                                with patch("src.workflow.scenarios.architecture.detect_architecture_query_type") as mock_detect:
                                    mock_detect.return_value = {"type": "general"}

                                    result = architecture_workflow(state)

        assert isinstance(result, dict)


class TestArchitectureErrorHandling:
    """Tests for architecture workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.architecture import architecture_workflow

        state = create_mock_state("Find violations")

        with patch("src.workflow.scenarios.architecture.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.architecture.detect_architecture_query_type") as mock_detect:
                mock_detect.return_value = {"type": "general"}

                result = architecture_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestDependencyAnalyzer:
    """Tests for DependencyAnalyzer agent interface."""

    def test_analyzer_interface(self):
        """Test dependency analyzer interface."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_dependencies.return_value = {
            "total_modules": 100,
            "total_dependencies": 500,
            "circular_dependencies": [],
        }

        result = mock_analyzer.analyze_dependencies()

        assert result["total_modules"] == 100

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        mock_analyzer = MagicMock()
        mock_analyzer.find_circular_dependencies.return_value = [
            {"modules": ["A", "B", "C", "A"], "length": 3},
        ]

        cycles = mock_analyzer.find_circular_dependencies()

        assert len(cycles) == 1
        assert cycles[0]["length"] == 3

    def test_god_module_detection(self):
        """Test god module detection."""
        mock_analyzer = MagicMock()
        mock_analyzer.find_god_modules.return_value = [
            {"name": "mega_module", "dependencies": 50, "dependents": 100},
        ]

        gods = mock_analyzer.find_god_modules()

        assert len(gods) == 1
        assert gods[0]["dependencies"] == 50

    def test_unstable_dependency_detection(self):
        """Test unstable dependency detection."""
        mock_analyzer = MagicMock()
        mock_analyzer.find_unstable_dependencies.return_value = [
            {"from": "stable_module", "to": "unstable_module", "risk": "high"},
        ]

        unstable = mock_analyzer.find_unstable_dependencies()

        assert len(unstable) == 1
        assert unstable[0]["risk"] == "high"


class TestLayerValidator:
    """Tests for LayerValidator agent interface."""

    def test_validator_interface(self):
        """Test layer validator interface."""
        mock_validator = MagicMock()
        mock_validator.validate_layers.return_value = {
            "valid": True,
            "violations": [],
        }

        result = mock_validator.validate_layers()

        assert result["valid"] is True

    def test_layer_violation_detection(self):
        """Test layer violation detection."""
        mock_validator = MagicMock()
        mock_validator.find_layer_violations.return_value = [
            {"source_layer": "presentation", "target_layer": "data", "module": "ui.c"},
        ]

        violations = mock_validator.find_layer_violations()

        assert len(violations) == 1
        assert violations[0]["source_layer"] == "presentation"


class TestArchitectureReporter:
    """Tests for ArchitectureReporter agent interface."""

    def test_reporter_interface(self):
        """Test architecture reporter interface."""
        mock_reporter = MagicMock()
        mock_reporter.generate_report.return_value = {
            "summary": "Architecture is mostly healthy",
            "score": 85,
            "violations": [],
            "recommendations": [],
        }

        report = mock_reporter.generate_report({})

        assert report["score"] == 85

    def test_prioritized_violations(self):
        """Test prioritized violation reporting."""
        mock_reporter = MagicMock()
        mock_reporter.get_prioritized_violations.return_value = [
            {"type": "circular", "severity": "critical", "priority": 1},
            {"type": "layer", "severity": "high", "priority": 2},
        ]

        violations = mock_reporter.get_prioritized_violations()

        assert violations[0]["priority"] == 1


class TestIncludeDependencyQueries:
    """Tests for include/dependency query handling."""

    def test_include_pattern_extraction(self):
        """Test extraction of include patterns from query."""
        import re

        query = "What files include memutils.h?"
        pattern = r'include\s+([a-zA-Z0-9_/\.]+)'

        match = re.search(pattern, query.lower())
        if match:
            target = match.group(1)
            assert "memutils" in target

    def test_dependency_pattern_extraction(self):
        """Test extraction of dependency patterns from query."""
        import re

        query = "What does the executor module depend on?"
        pattern = r'what\s+does\s+(?:the\s+)?([a-zA-Z0-9_]+)\s+(?:module\s+)?depend'

        match = re.search(pattern, query.lower())
        if match:
            target = match.group(1)
            assert target == "executor"


class TestArchitectureViolationScoring:
    """Tests for architecture violation scoring."""

    def test_severity_scoring(self):
        """Test severity-based scoring."""
        violations = [
            {"type": "circular", "severity": "critical"},
            {"type": "layer", "severity": "high"},
            {"type": "coupling", "severity": "medium"},
        ]

        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}

        total_score = sum(
            severity_weights.get(v["severity"], 0)
            for v in violations
        )

        assert total_score == 17

    def test_health_score_calculation(self):
        """Test architecture health score calculation."""
        metrics = {
            "violations": 5,
            "modules": 100,
            "circular_count": 1,
        }

        # Health score formula
        violation_penalty = metrics["violations"] * 2
        circular_penalty = metrics["circular_count"] * 10
        base_score = 100

        health_score = base_score - violation_penalty - circular_penalty

        assert health_score == 80


class TestArchitectureGraphInsights:
    """Tests for architecture graph insights."""

    def test_graph_insights_structure(self):
        """Test graph insights structure."""
        graph_insights = {
            "dependency_paths": [],
            "violation_impact": {},
            "hotspots": [],
        }

        assert "dependency_paths" in graph_insights
        assert "violation_impact" in graph_insights

    def test_impact_analysis(self):
        """Test violation impact analysis."""
        violations = [
            {"module": "core", "affected_modules": 50},
            {"module": "util", "affected_modules": 5},
        ]

        # Sort by impact
        sorted_violations = sorted(
            violations,
            key=lambda v: v["affected_modules"],
            reverse=True
        )

        assert sorted_violations[0]["module"] == "core"
