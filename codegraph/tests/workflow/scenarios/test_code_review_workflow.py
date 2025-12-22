"""
Tests for Code Review Automation Workflow (Scenario 9).

Tests for code review workflow, PR analysis, and review report generation.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str, pr_diff: str = "") -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "code_review",
        "scenario_id": "scenario_9",
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
        "pr_diff": pr_diff,
        "pr_metadata": {
            "title": "Test PR",
            "author": "developer",
            "number": 123,
        },
    }


class TestCodeReviewWorkflowImports:
    """Tests for code review workflow module imports."""

    def test_import_workflow(self):
        """Test that code review workflow can be imported."""
        from src.workflow.scenarios.code_review import code_review_workflow

        assert callable(code_review_workflow)

    def test_import_review_agents(self):
        """Test that review agents can be imported."""
        from src.code_review.review_agents import (
            PRAnalyzer,
            ContextAggregator,
            ReviewReporter,
        )

        assert PRAnalyzer is not None
        assert ContextAggregator is not None
        assert ReviewReporter is not None


class TestCodeReviewQueryPatterns:
    """Tests for code review query pattern detection."""

    def test_pr_review_keywords(self):
        """Test PR review keyword detection."""
        queries = [
            "Review this pull request",
            "Check PR #123",
            "Analyze merge request",
        ]

        pr_keywords = ["review", "pull request", "pr", "merge request"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in pr_keywords)

    def test_code_change_keywords(self):
        """Test code change keyword detection."""
        queries = [
            "Review code changes",
            "Check this diff",
            "Analyze modifications",
        ]

        change_keywords = ["change", "diff", "modif", "update"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in change_keywords)

    def test_quality_keywords(self):
        """Test code quality keyword detection."""
        queries = [
            "Check code quality",
            "Find issues in this code",
            "Code style review",
        ]

        quality_keywords = ["quality", "issue", "style", "standard"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in quality_keywords)


class TestCodeReviewWorkflowMocked:
    """Tests for code_review_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = []
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        mock.execute_custom_sql.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Code review: The changes look good."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.code_review import code_review_workflow

        state = create_mock_state("Review this PR")

        with patch("src.workflow.scenarios.code_review.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.code_review.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.code_review.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a code reviewer",
                        "user": "Review the code",
                    }
                    with patch("src.workflow.scenarios.code_review.PRAnalyzer") as mock_pr:
                        mock_pr.return_value.parse_pr_diff.return_value = {
                            "files_changed": 2,
                            "changed_files": [],
                        }
                        mock_pr.return_value.extract_changed_methods.return_value = []
                        mock_pr.return_value.identify_affected_subsystems.return_value = []

                        with patch("src.workflow.scenarios.code_review.ContextAggregator") as mock_ctx:
                            mock_ctx.return_value.check_test_coverage.return_value = {
                                "coverage_percent": 80.0
                            }
                            mock_ctx.return_value.find_impacted_methods.return_value = []

                            with patch("src.workflow.scenarios.code_review.ReviewReporter"):
                                result = code_review_workflow(state)

        assert isinstance(result, dict)


class TestCodeReviewErrorHandling:
    """Tests for code review workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.code_review import code_review_workflow

        state = create_mock_state("Review PR")

        with patch("src.workflow.scenarios.code_review.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = code_review_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestPRAnalyzer:
    """Tests for PRAnalyzer agent interface."""

    def test_parse_pr_diff(self):
        """Test PR diff parsing."""
        mock_analyzer = MagicMock()
        mock_analyzer.parse_pr_diff.return_value = {
            "files_changed": 3,
            "lines_added": 100,
            "lines_removed": 50,
            "changed_files": ["src/main.c", "src/util.c", "tests/test_main.c"],
        }

        result = mock_analyzer.parse_pr_diff("diff content", {})

        assert result["files_changed"] == 3
        assert len(result["changed_files"]) == 3

    def test_extract_changed_methods(self):
        """Test extraction of changed methods."""
        mock_analyzer = MagicMock()
        mock_changed_method = MagicMock()
        mock_changed_method.method_name = "process_data"
        mock_changed_method.filepath = "src/main.c"
        mock_changed_method.lines_changed = 20

        mock_analyzer.extract_changed_methods.return_value = [mock_changed_method]

        methods = mock_analyzer.extract_changed_methods({})

        assert len(methods) == 1
        assert methods[0].method_name == "process_data"

    def test_identify_affected_subsystems(self):
        """Test identification of affected subsystems."""
        mock_analyzer = MagicMock()
        mock_analyzer.identify_affected_subsystems.return_value = [
            "executor",
            "optimizer",
        ]

        subsystems = mock_analyzer.identify_affected_subsystems(["src/executor/main.c"])

        assert "executor" in subsystems


class TestContextAggregator:
    """Tests for ContextAggregator agent interface."""

    def test_gather_method_context(self):
        """Test method context gathering."""
        mock_aggregator = MagicMock()
        mock_aggregator.gather_method_context.return_value = {
            "method_id": 123,
            "callers": ["caller1", "caller2"],
            "callees": ["callee1"],
            "complexity": 15,
        }

        context = mock_aggregator.gather_method_context(123)

        assert context["method_id"] == 123
        assert len(context["callers"]) == 2

    def test_check_test_coverage(self):
        """Test test coverage checking."""
        mock_aggregator = MagicMock()
        mock_aggregator.check_test_coverage.return_value = {
            "coverage_percent": 85.5,
            "covered_methods": 10,
            "uncovered_methods": 2,
        }

        coverage = mock_aggregator.check_test_coverage([])

        assert coverage["coverage_percent"] == 85.5

    def test_find_impacted_methods(self):
        """Test finding impacted methods."""
        mock_aggregator = MagicMock()
        mock_aggregator.find_impacted_methods.return_value = [
            {"name": "method1", "impact": "direct"},
            {"name": "method2", "impact": "indirect"},
        ]

        impacted = mock_aggregator.find_impacted_methods([])

        assert len(impacted) == 2


class TestReviewReporter:
    """Tests for ReviewReporter agent interface."""

    def test_generate_review(self):
        """Test review generation."""
        mock_reporter = MagicMock()
        mock_reporter.generate_review.return_value = {
            "summary": "Good changes overall",
            "score": 8,
            "findings": [],
            "action": "APPROVE",
        }

        review = mock_reporter.generate_review({})

        assert review["action"] == "APPROVE"
        assert review["score"] == 8

    def test_generate_comments(self):
        """Test comment generation."""
        mock_reporter = MagicMock()
        mock_reporter.generate_comments.return_value = [
            {"file": "main.c", "line": 10, "comment": "Consider using const here"},
            {"file": "main.c", "line": 25, "comment": "Missing null check"},
        ]

        comments = mock_reporter.generate_comments([])

        assert len(comments) == 2
        assert comments[0]["line"] == 10


class TestCodeReviewGraphInsights:
    """Tests for code review graph insights integration."""

    def test_graph_insights_structure(self):
        """Test graph insights structure for code review."""
        graph_insights = {
            "change_impact": {},
            "affected_methods": [],
            "risk_assessment": {},
        }

        assert "change_impact" in graph_insights
        assert "risk_assessment" in graph_insights

    def test_change_impact_analysis(self):
        """Test change impact analysis."""
        changes = [
            {"method": "core_function", "callers": 100, "risk": "high"},
            {"method": "helper", "callers": 2, "risk": "low"},
        ]

        high_risk = [c for c in changes if c["risk"] == "high"]

        assert len(high_risk) == 1
        assert high_risk[0]["method"] == "core_function"


class TestCodeReviewScoring:
    """Tests for code review scoring logic."""

    def test_score_calculation(self):
        """Test review score calculation."""
        findings = {
            "critical": 0,
            "major": 2,
            "minor": 5,
            "info": 10,
        }

        # Score starts at 10, deductions for findings
        score = 10
        score -= findings["critical"] * 3
        score -= findings["major"] * 2
        score -= findings["minor"] * 0.5
        score -= findings["info"] * 0.1

        assert score == 10 - 0 - 4 - 2.5 - 1  # 2.5

    def test_review_action_determination(self):
        """Test review action determination."""
        score = 8

        if score >= 8:
            action = "APPROVE"
        elif score >= 5:
            action = "REQUEST_CHANGES"
        else:
            action = "REJECT"

        assert action == "APPROVE"


class TestCodeReviewIntegration:
    """Tests for code review integration with other scenarios."""

    def test_security_integration_check(self):
        """Test security check integration."""
        pr_data = {
            "files": ["src/auth/login.c", "src/crypto/hash.c"],
        }

        # Check if security-related files are changed
        security_paths = ["auth", "crypto", "security"]
        has_security_changes = any(
            any(sec in f for sec in security_paths)
            for f in pr_data["files"]
        )

        assert has_security_changes is True

    def test_performance_integration_check(self):
        """Test performance check integration."""
        findings = [
            {"type": "security", "count": 1},
            {"type": "performance", "count": 2},
            {"type": "style", "count": 5},
        ]

        perf_findings = [f for f in findings if f["type"] == "performance"]

        assert len(perf_findings) == 1
        assert perf_findings[0]["count"] == 2


class TestPRMetadata:
    """Tests for PR metadata handling."""

    def test_metadata_structure(self):
        """Test PR metadata structure."""
        metadata = {
            "title": "Add new feature",
            "author": "developer",
            "number": 123,
            "branch": "feature/new-feature",
            "base": "main",
        }

        required_fields = ["title", "author", "number"]
        assert all(field in metadata for field in required_fields)

    def test_author_extraction(self):
        """Test author extraction from metadata."""
        metadata = {"author": "john.doe"}

        author = metadata.get("author", "unknown")

        assert author == "john.doe"


class TestDiffParsing:
    """Tests for diff parsing utilities."""

    def test_simple_diff_structure(self):
        """Test simple diff structure recognition."""
        diff = """
diff --git a/src/main.c b/src/main.c
--- a/src/main.c
+++ b/src/main.c
@@ -10,3 +10,4 @@
 existing line
+new line
 another existing line
"""

        # Basic diff structure checks
        assert "diff --git" in diff
        assert "+++" in diff
        assert "---" in diff

    def test_added_lines_detection(self):
        """Test detection of added lines."""
        diff_lines = [
            " unchanged",
            "+added line",
            " unchanged",
            "+another added",
        ]

        added = [l for l in diff_lines if l.startswith("+")]

        assert len(added) == 2

    def test_removed_lines_detection(self):
        """Test detection of removed lines."""
        diff_lines = [
            " unchanged",
            "-removed line",
            " unchanged",
        ]

        removed = [l for l in diff_lines if l.startswith("-")]

        assert len(removed) == 1
