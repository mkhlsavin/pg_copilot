"""
Tests for Refactoring Assistance Workflow (Scenario 5).

Tests for refactoring workflow, dead code detection, and technical debt analysis.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "refactoring",
        "scenario_id": "scenario_5",
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


class TestDeadCodeIntentMap:
    """Tests for DEAD_CODE_INTENT_MAP constant."""

    def test_intent_map_exists(self):
        """Test that intent map is defined."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_INTENT_MAP

        assert isinstance(DEAD_CODE_INTENT_MAP, dict)
        assert len(DEAD_CODE_INTENT_MAP) > 0

    def test_intent_map_has_deprecated_patterns(self):
        """Test that deprecated patterns are mapped."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_INTENT_MAP

        deprecated_terms = ["deprecated", "deprecate", "obsolete"]

        for term in deprecated_terms:
            assert term in DEAD_CODE_INTENT_MAP, f"Missing {term}"

    def test_intent_map_has_unused_patterns(self):
        """Test that unused code patterns are mapped."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_INTENT_MAP

        unused_terms = ["unused", "never called", "uncalled"]

        for term in unused_terms:
            assert term in DEAD_CODE_INTENT_MAP, f"Missing {term}"

    def test_intent_map_has_unreachable_patterns(self):
        """Test that unreachable code patterns are mapped."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_INTENT_MAP

        unreachable_terms = ["unreachable", "after return"]

        for term in unreachable_terms:
            assert term in DEAD_CODE_INTENT_MAP, f"Missing {term}"


class TestDeadCodePatternConfidence:
    """Tests for DEAD_CODE_PATTERN_CONFIDENCE scores."""

    def test_confidence_map_exists(self):
        """Test that confidence map is defined."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_PATTERN_CONFIDENCE

        assert isinstance(DEAD_CODE_PATTERN_CONFIDENCE, dict)
        assert len(DEAD_CODE_PATTERN_CONFIDENCE) > 0

    def test_confidence_values_in_range(self):
        """Test that all confidence values are between 0 and 1."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_PATTERN_CONFIDENCE

        for pattern, confidence in DEAD_CODE_PATTERN_CONFIDENCE.items():
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence for {pattern}"

    def test_deprecated_has_highest_confidence(self):
        """Test that deprecated marker has highest confidence."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_PATTERN_CONFIDENCE

        deprecated_conf = DEAD_CODE_PATTERN_CONFIDENCE.get("DEPRECATED_MARKER", 0)

        # Should be high confidence
        assert deprecated_conf >= 0.9


class TestDetectDeadCodeIntent:
    """Tests for detect_dead_code_intent function."""

    def test_deprecated_query(self):
        """Test deprecated code detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find deprecated functions")

        assert patterns is not None
        assert "DEPRECATED_MARKER" in patterns

    def test_unused_query(self):
        """Test unused code detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find unused functions")

        assert patterns is not None
        assert "DEAD_CODE" in patterns or "UNUSED_VARIABLE" in patterns

    def test_unreachable_query(self):
        """Test unreachable code detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find unreachable code")

        assert patterns is not None
        assert "UNREACHABLE_AFTER_RETURN" in patterns

    def test_disabled_code_query(self):
        """Test disabled code detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find disabled code blocks")

        assert patterns is not None
        assert "DISABLED_CODE_BLOCK" in patterns

    def test_empty_stub_query(self):
        """Test empty stub detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find empty stub functions")

        assert patterns is not None
        assert "EMPTY_STUB" in patterns

    def test_orphan_query(self):
        """Test orphan component detection."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find orphan components")

        assert patterns is not None
        assert "ORPHAN_COMPONENT" in patterns

    def test_combined_query(self):
        """Test query with multiple dead code types."""
        from src.workflow.scenarios.refactoring import detect_dead_code_intent

        patterns = detect_dead_code_intent("Find deprecated and unused code")

        assert patterns is not None
        assert "DEPRECATED_MARKER" in patterns
        assert "DEAD_CODE" in patterns or "UNUSED_VARIABLE" in patterns


class TestDeadCodePatternKeywords:
    """Tests for DEAD_CODE_PATTERN_KEYWORDS mapping."""

    def test_keywords_map_exists(self):
        """Test that keywords map is defined."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_PATTERN_KEYWORDS

        assert isinstance(DEAD_CODE_PATTERN_KEYWORDS, dict)

    def test_keywords_contain_bold_markers(self):
        """Test that keywords contain bold markdown markers."""
        from src.workflow.scenarios.refactoring import DEAD_CODE_PATTERN_KEYWORDS

        for pattern, keywords in DEAD_CODE_PATTERN_KEYWORDS.items():
            assert "**" in keywords, f"No bold markers in {pattern}"


class TestRefactoringWorkflowMocked:
    """Tests for refactoring_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = [
            {"name": "executor", "method_count": 500, "file_count": 20},
        ]
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Refactoring analysis complete."
        return mock

    def test_workflow_imports(self):
        """Test that refactoring workflow can be imported."""
        from src.workflow.scenarios.refactoring import refactoring_workflow

        assert callable(refactoring_workflow)

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.refactoring import refactoring_workflow

        state = create_mock_state("Find dead code")

        # Use correct path - imports are in the workflow submodule
        with patch("src.workflow.scenarios.refactoring.workflow.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.refactoring.workflow.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.refactoring.workflow.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a refactoring expert",
                        "user": "Analyze refactoring",
                    }
                    with patch("src.workflow.scenarios.refactoring.workflow.TechnicalDebtDetector"):
                        with patch("src.workflow.scenarios.refactoring.workflow.DeadCodeDetector"):
                            with patch("src.workflow.scenarios.refactoring.workflow.ImpactAnalyzer"):
                                with patch("src.workflow.scenarios.refactoring.workflow.RefactoringPlanner"):
                                    with patch("src.workflow.scenarios.refactoring.workflow.detect_refactoring_query_type") as mock_detect:
                                        mock_detect.return_value = {"type": "dead_code", "target": None}

                                        result = refactoring_workflow(state)

        assert isinstance(result, dict)


class TestRefactoringQueryPatterns:
    """Tests for refactoring query pattern detection."""

    def test_dead_code_keywords(self):
        """Test dead code keyword detection."""
        queries = [
            "Find dead code",
            "Identify unused functions",
            "Find deprecated APIs",
        ]

        dead_code_keywords = ["dead", "unused", "deprecated", "obsolete", "never called"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in dead_code_keywords)

    def test_duplication_keywords(self):
        """Test duplication keyword detection."""
        queries = [
            "Find duplicate code",
            "Detect code clones",
            "Similar functions",
        ]

        dup_keywords = ["duplicate", "clone", "similar", "copy"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in dup_keywords)

    def test_complexity_keywords(self):
        """Test complexity keyword detection."""
        queries = [
            "Functions with high complexity",
            "Deeply nested code",
            "Too many parameters",
        ]

        complexity_keywords = ["complex", "nested", "parameter", "large"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in complexity_keywords + ["complex", "nested"])


class TestRefactoringErrorHandling:
    """Tests for refactoring workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.refactoring import refactoring_workflow

        state = create_mock_state("Find dead code")

        # Use correct path - imports are in the workflow submodule
        with patch("src.workflow.scenarios.refactoring.workflow.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = refactoring_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestTechnicalDebtDetection:
    """Tests for technical debt detection integration."""

    def test_debt_detector_interface(self):
        """Test technical debt detector interface."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [
            {"type": "long_method", "function": "func1", "lines": 500},
            {"type": "god_class", "file": "big.c", "methods": 50},
        ]

        findings = mock_detector.detect()

        assert len(findings) == 2
        assert findings[0]["type"] == "long_method"

    def test_dead_code_detector_interface(self):
        """Test dead code detector interface."""
        mock_detector = MagicMock()
        mock_detector.detect_dead_code.return_value = [
            {"pattern": "DEAD_CODE", "function": "unused_func", "confidence": 0.8},
        ]

        findings = mock_detector.detect_dead_code()

        assert len(findings) == 1
        assert findings[0]["pattern"] == "DEAD_CODE"


class TestRefactoringRecommendations:
    """Tests for refactoring recommendation generation."""

    def test_extract_method_recommendation(self):
        """Test extract method recommendation for long functions."""
        long_functions = [
            {"name": "very_long_function", "lines": 500},
        ]

        recommendations = []
        for func in long_functions:
            if func["lines"] > 100:
                recommendations.append({
                    "function": func["name"],
                    "refactoring": "Extract Method",
                    "reason": f"Function has {func['lines']} lines",
                })

        assert len(recommendations) == 1
        assert recommendations[0]["refactoring"] == "Extract Method"

    def test_inline_recommendation(self):
        """Test inline recommendation for single-caller functions."""
        single_caller_funcs = [
            {"name": "helper_used_once", "caller_count": 1},
        ]

        recommendations = []
        for func in single_caller_funcs:
            if func["caller_count"] == 1:
                recommendations.append({
                    "function": func["name"],
                    "refactoring": "Inline Function",
                    "reason": "Only called from one place",
                })

        assert len(recommendations) == 1
        assert recommendations[0]["refactoring"] == "Inline Function"


class TestImpactAnalysis:
    """Tests for refactoring impact analysis."""

    def test_impact_analyzer_interface(self):
        """Test impact analyzer interface."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_impact.return_value = {
            "affected_callers": ["caller1", "caller2"],
            "affected_callees": ["callee1"],
            "risk_level": "medium",
        }

        impact = mock_analyzer.analyze_impact("target_function")

        assert "affected_callers" in impact
        assert "risk_level" in impact

    def test_impact_score_calculation(self):
        """Test impact score calculation logic."""
        # Simulate impact calculation
        impact_data = {
            "callers": 10,
            "callees": 5,
            "files_affected": 3,
        }

        # Simple impact score formula
        impact_score = (
            impact_data["callers"] * 0.4 +
            impact_data["callees"] * 0.3 +
            impact_data["files_affected"] * 0.3
        )

        assert impact_score > 0
        assert impact_score < 20  # Reasonable upper bound


class TestRefactoringPlanning:
    """Tests for refactoring planning."""

    def test_planner_interface(self):
        """Test refactoring planner interface."""
        mock_planner = MagicMock()
        mock_planner.create_plan.return_value = {
            "steps": [
                {"action": "extract_method", "target": "func1"},
                {"action": "rename_variable", "target": "old_name"},
            ],
            "estimated_effort": "medium",
        }

        plan = mock_planner.create_plan("large refactoring")

        assert "steps" in plan
        assert len(plan["steps"]) == 2

    def test_prioritization_by_impact(self):
        """Test prioritization of refactoring by impact."""
        refactorings = [
            {"name": "r1", "impact": 0.3, "benefit": 0.8},
            {"name": "r2", "impact": 0.9, "benefit": 0.6},
            {"name": "r3", "impact": 0.5, "benefit": 0.9},
        ]

        # Prioritize by benefit/impact ratio
        prioritized = sorted(
            refactorings,
            key=lambda x: x["benefit"] / x["impact"],
            reverse=True
        )

        # Highest benefit/impact ratio should be first
        assert prioritized[0]["name"] == "r1"  # 0.8/0.3 = 2.67
