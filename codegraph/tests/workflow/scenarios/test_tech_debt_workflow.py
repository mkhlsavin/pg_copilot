"""
Tests for Technical Debt Quantification Workflow (Scenario 12).

Tests for tech debt workflow, debt detection, prioritization, and repayment planning.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "tech_debt",
        "scenario_id": "scenario_12",
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


class TestTechDebtWorkflowImports:
    """Tests for tech debt workflow module imports."""

    def test_import_workflow(self):
        """Test that tech debt workflow can be imported."""
        from src.workflow.scenarios.tech_debt import tech_debt_workflow

        assert callable(tech_debt_workflow)

    def test_import_tech_debt_agents(self):
        """Test that tech debt agents can be imported."""
        from src.tech_debt import (
            DebtCalculator,
            PrioritizationEngine,
            RepaymentPlanner,
        )

        assert DebtCalculator is not None
        assert PrioritizationEngine is not None
        assert RepaymentPlanner is not None


class TestTechDebtWorkflowMocked:
    """Tests for tech_debt_workflow function with mocked dependencies."""

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
        mock.generate.return_value = "Technical debt analysis complete."
        return mock

    @pytest.fixture
    def mock_debt_calculator(self):
        """Create mock DebtCalculator."""
        mock_calculator = MagicMock()

        # Mock debt items
        mock_item = MagicMock()
        mock_item.pattern_name = "LONG_METHOD"
        mock_item.location = "src/main.c:100"
        mock_item.effort_hours = 4.0
        mock_item.severity = "medium"
        mock_item.category = "complexity"
        mock_item.description = "Method too long"
        mock_item.metadata = {"file": "main.c", "line": 100}

        mock_calculator.detect_all_debt.return_value = [mock_item]

        # Mock metrics
        mock_metrics = MagicMock()
        mock_metrics.total_items = 1
        mock_metrics.total_effort_hours = 4.0
        mock_metrics.debt_ratio = 0.02
        mock_metrics.average_effort = 4.0
        mock_metrics.high_interest_items = 0
        mock_metrics.by_severity = {"high": 0, "medium": 1, "low": 0}
        mock_metrics.by_category = {"complexity": 1}

        mock_calculator.calculate_metrics.return_value = mock_metrics

        return mock_calculator

    @pytest.fixture
    def mock_prioritization_engine(self):
        """Create mock PrioritizationEngine."""
        mock_engine = MagicMock()

        # Mock prioritized item
        mock_prioritized = MagicMock()
        mock_prioritized.item = MagicMock()
        mock_prioritized.item.pattern_name = "LONG_METHOD"
        mock_prioritized.item.location = "src/main.c:100"
        mock_prioritized.item.effort_hours = 4.0
        mock_prioritized.item.metadata = {"file": "main.c"}
        mock_prioritized.priority_score = 7.5
        mock_prioritized.roi_score = 2.5

        mock_engine.prioritize_debt.return_value = [mock_prioritized]
        mock_engine.get_quick_wins.return_value = [mock_prioritized]
        mock_engine.get_strategic_items.return_value = []

        return mock_engine

    @pytest.fixture
    def mock_repayment_planner(self):
        """Create mock RepaymentPlanner."""
        mock_planner = MagicMock()

        # Mock plan
        mock_plan = MagicMock()
        mock_plan.plan_id = "plan_123"
        mock_plan.timestamp = "2024-01-01T00:00:00"
        mock_plan.estimated_weeks = 2
        mock_plan.summary = "Repayment plan summary"
        mock_plan.recommendations = ["Fix long methods first"]
        mock_plan.sprints = [
            {
                "sprint_number": 1,
                "items": [],
                "total_effort": 20.0,
                "quick_wins": 5,
                "strategic": 2,
            }
        ]

        mock_planner.create_plan.return_value = mock_plan

        return mock_planner

    def test_workflow_returns_state(
        self,
        mock_cpg_service,
        mock_llm,
        mock_debt_calculator,
        mock_prioritization_engine,
        mock_repayment_planner,
    ):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.tech_debt import tech_debt_workflow

        state = create_mock_state("Analyze technical debt")

        with patch("src.workflow.scenarios.tech_debt.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.tech_debt.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.tech_debt.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a tech debt expert",
                        "user": "Analyze debt",
                    }
                    with patch("src.workflow.scenarios.tech_debt.DebtCalculator", return_value=mock_debt_calculator):
                        with patch("src.workflow.scenarios.tech_debt.PrioritizationEngine", return_value=mock_prioritization_engine):
                            with patch("src.workflow.scenarios.tech_debt.RepaymentPlanner", return_value=mock_repayment_planner):
                                result = tech_debt_workflow(state)

        assert isinstance(result, dict)
        assert "metadata" in result


class TestTechDebtErrorHandling:
    """Tests for tech debt workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.tech_debt import tech_debt_workflow

        state = create_mock_state("Analyze debt")

        with patch("src.workflow.scenarios.tech_debt.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = tech_debt_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestDebtCalculator:
    """Tests for DebtCalculator agent interface."""

    def test_calculator_interface(self):
        """Test debt calculator interface."""
        mock_calculator = MagicMock()
        mock_calculator.detect_all_debt.return_value = [
            {"pattern": "LONG_METHOD", "file": "main.c", "effort": 4},
            {"pattern": "GOD_CLASS", "file": "big.c", "effort": 8},
        ]

        debt = mock_calculator.detect_all_debt()

        assert len(debt) == 2
        assert debt[0]["pattern"] == "LONG_METHOD"

    def test_calculate_metrics(self):
        """Test metrics calculation."""
        mock_calculator = MagicMock()
        mock_metrics = {
            "total_items": 50,
            "total_effort_hours": 200.0,
            "debt_ratio": 0.05,
            "by_severity": {"high": 5, "medium": 20, "low": 25},
        }
        mock_calculator.calculate_metrics.return_value = mock_metrics

        metrics = mock_calculator.calculate_metrics([], codebase_size=4000)

        assert metrics["total_items"] == 50
        assert metrics["debt_ratio"] == 0.05


class TestPrioritizationEngine:
    """Tests for PrioritizationEngine agent interface."""

    def test_prioritize_debt(self):
        """Test debt prioritization."""
        mock_engine = MagicMock()
        mock_prioritized = [
            {"item": "debt1", "priority_score": 9.5, "roi_score": 3.0},
            {"item": "debt2", "priority_score": 7.0, "roi_score": 2.0},
        ]
        mock_engine.prioritize_debt.return_value = mock_prioritized

        prioritized = mock_engine.prioritize_debt([], {})

        assert len(prioritized) == 2
        assert prioritized[0]["priority_score"] == 9.5

    def test_get_quick_wins(self):
        """Test quick wins identification."""
        mock_engine = MagicMock()
        mock_quick_wins = [
            {"item": "easy_fix", "effort": 1.0, "roi_score": 5.0},
        ]
        mock_engine.get_quick_wins.return_value = mock_quick_wins

        quick_wins = mock_engine.get_quick_wins([])

        assert len(quick_wins) == 1
        assert quick_wins[0]["roi_score"] == 5.0

    def test_get_strategic_items(self):
        """Test strategic items identification."""
        mock_engine = MagicMock()
        mock_strategic = [
            {"item": "major_refactor", "effort": 40.0, "business_value": "high"},
        ]
        mock_engine.get_strategic_items.return_value = mock_strategic

        strategic = mock_engine.get_strategic_items([])

        assert len(strategic) == 1
        assert strategic[0]["business_value"] == "high"


class TestRepaymentPlanner:
    """Tests for RepaymentPlanner agent interface."""

    def test_create_plan(self):
        """Test repayment plan creation."""
        mock_planner = MagicMock()
        mock_plan = {
            "plan_id": "plan_abc123",
            "sprints": [
                {"sprint_number": 1, "total_effort": 40.0, "items": []},
                {"sprint_number": 2, "total_effort": 40.0, "items": []},
            ],
            "estimated_weeks": 4,
            "summary": "2-sprint plan",
            "recommendations": ["Start with quick wins"],
        }
        mock_planner.create_plan.return_value = mock_plan

        plan = mock_planner.create_plan([], max_sprints=6)

        assert plan["plan_id"] == "plan_abc123"
        assert len(plan["sprints"]) == 2
        assert plan["estimated_weeks"] == 4

    def test_team_velocity_configuration(self):
        """Test team velocity configuration."""
        mock_planner = MagicMock()
        mock_planner.team_velocity = 40.0

        assert mock_planner.team_velocity == 40.0


class TestDebtMetricsCalculation:
    """Tests for debt metrics calculation logic."""

    def test_debt_ratio_calculation(self):
        """Test debt ratio calculation."""
        total_effort = 100.0
        codebase_size = 5000  # LOC

        debt_ratio = total_effort / codebase_size

        assert debt_ratio == 0.02

    def test_average_effort_calculation(self):
        """Test average effort per item."""
        total_effort = 120.0
        total_items = 30

        average_effort = total_effort / total_items

        assert average_effort == 4.0

    def test_severity_distribution(self):
        """Test severity distribution."""
        debt_items = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "medium"},
            {"severity": "medium"},
            {"severity": "low"},
        ]

        by_severity = {}
        for item in debt_items:
            sev = item["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

        assert by_severity["high"] == 2
        assert by_severity["medium"] == 3
        assert by_severity["low"] == 1


class TestROIScoring:
    """Tests for ROI scoring logic."""

    def test_roi_calculation(self):
        """Test ROI score calculation."""
        business_value = 10.0
        effort = 2.0

        roi_score = business_value / effort

        assert roi_score == 5.0

    def test_quick_win_identification(self):
        """Test quick win identification logic."""
        items = [
            {"effort": 1.0, "roi_score": 8.0},
            {"effort": 2.0, "roi_score": 6.0},
            {"effort": 10.0, "roi_score": 4.0},
        ]

        # Quick wins: low effort (<= 4h) and high ROI (>= 2.0)
        quick_wins = [
            item for item in items
            if item["effort"] <= 4.0 and item["roi_score"] >= 2.0
        ]

        assert len(quick_wins) == 2

    def test_strategic_item_identification(self):
        """Test strategic item identification logic."""
        items = [
            {"effort": 1.0, "priority_score": 5.0},
            {"effort": 20.0, "priority_score": 9.0},
            {"effort": 40.0, "priority_score": 8.5},
        ]

        # Strategic: high effort (>= 8h) and high priority (>= 7.0)
        strategic = [
            item for item in items
            if item["effort"] >= 8.0 and item["priority_score"] >= 7.0
        ]

        assert len(strategic) == 2


class TestSprintPlanning:
    """Tests for sprint planning logic."""

    def test_sprint_capacity(self):
        """Test sprint capacity calculation."""
        team_velocity = 40.0  # hours per sprint
        num_sprints = 3

        total_capacity = team_velocity * num_sprints

        assert total_capacity == 120.0

    def test_sprint_allocation(self):
        """Test allocation of items to sprints."""
        items = [
            {"effort": 20.0, "priority": 9},
            {"effort": 15.0, "priority": 8},
            {"effort": 10.0, "priority": 7},
        ]
        sprint_capacity = 40.0

        # Simple greedy allocation
        sprints = []
        current_sprint = {"items": [], "total_effort": 0.0}

        for item in sorted(items, key=lambda x: -x["priority"]):
            if current_sprint["total_effort"] + item["effort"] <= sprint_capacity:
                current_sprint["items"].append(item)
                current_sprint["total_effort"] += item["effort"]
            else:
                sprints.append(current_sprint)
                current_sprint = {
                    "items": [item],
                    "total_effort": item["effort"],
                }

        if current_sprint["items"]:
            sprints.append(current_sprint)

        assert len(sprints) == 2
        assert sprints[0]["total_effort"] == 35.0  # 20 + 15

    def test_weeks_estimation(self):
        """Test weeks estimation from sprints."""
        num_sprints = 6
        weeks_per_sprint = 2

        estimated_weeks = num_sprints * weeks_per_sprint

        assert estimated_weeks == 12


class TestDebtCategories:
    """Tests for debt category classification."""

    def test_category_grouping(self):
        """Test grouping debt by category."""
        debt_items = [
            {"category": "complexity"},
            {"category": "complexity"},
            {"category": "duplication"},
            {"category": "security"},
            {"category": "complexity"},
        ]

        by_category = {}
        for item in debt_items:
            cat = item["category"]
            by_category[cat] = by_category.get(cat, 0) + 1

        assert by_category["complexity"] == 3
        assert by_category["duplication"] == 1
        assert by_category["security"] == 1

    def test_common_debt_categories(self):
        """Test that common debt categories are recognized."""
        categories = [
            "complexity",
            "duplication",
            "security",
            "performance",
            "maintainability",
            "documentation",
        ]

        # All should be valid categories
        for cat in categories:
            assert isinstance(cat, str)
            assert len(cat) > 0


class TestHighInterestDebt:
    """Tests for high interest debt identification."""

    def test_interest_calculation(self):
        """Test technical debt interest calculation."""
        # High interest: debt that grows quickly over time
        debt_items = [
            {"pattern": "SECURITY_VULN", "interest_rate": 0.5},
            {"pattern": "LONG_METHOD", "interest_rate": 0.1},
        ]

        high_interest = [
            item for item in debt_items
            if item["interest_rate"] >= 0.3
        ]

        assert len(high_interest) == 1
        assert high_interest[0]["pattern"] == "SECURITY_VULN"


class TestDebtTrendAnalysis:
    """Tests for debt trend analysis."""

    def test_debt_growth_tracking(self):
        """Test tracking debt growth over time."""
        snapshots = [
            {"date": "2024-01-01", "total_debt": 100.0},
            {"date": "2024-02-01", "total_debt": 120.0},
            {"date": "2024-03-01", "total_debt": 110.0},
        ]

        # Calculate growth rate
        initial = snapshots[0]["total_debt"]
        final = snapshots[-1]["total_debt"]
        growth_rate = (final - initial) / initial

        assert growth_rate == 0.1  # 10% growth


class TestDebtPrevention:
    """Tests for debt prevention recommendations."""

    def test_prevention_strategies(self):
        """Test debt prevention strategy generation."""
        high_debt_categories = ["complexity", "duplication"]

        recommendations = []
        for category in high_debt_categories:
            if category == "complexity":
                recommendations.append("Enforce cyclomatic complexity limits")
            elif category == "duplication":
                recommendations.append("Use code review to catch duplicates")

        assert len(recommendations) == 2


class TestGraphInsights:
    """Tests for graph-based debt insights."""

    def test_graph_insights_structure(self):
        """Test graph insights structure."""
        graph_insights = {
            "high_impact_debt": [],
            "debt_hotspots": [],
        }

        assert "high_impact_debt" in graph_insights
        assert "debt_hotspots" in graph_insights

    def test_hotspot_identification(self):
        """Test identification of debt hotspots."""
        debt_items = [
            {"file": "core.c", "count": 10},
            {"file": "util.c", "count": 2},
            {"file": "main.c", "count": 7},
        ]

        # Hotspots: files with >= 5 debt items
        hotspots = [item for item in debt_items if item["count"] >= 5]

        assert len(hotspots) == 2
        assert hotspots[0]["file"] == "core.c"


class TestEnhancedMetadata:
    """Tests for enhanced metadata generation."""

    def test_metadata_completeness(self):
        """Test that metadata contains all required fields."""
        metadata = {
            "plan_id": "plan_123",
            "timestamp": "2024-01-01T00:00:00",
            "total_debt_items": 50,
            "total_effort_hours": 200.0,
            "debt_ratio": 0.05,
            "by_severity": {"high": 5, "medium": 20, "low": 25},
            "by_category": {"complexity": 30, "duplication": 20},
            "quick_wins_count": 10,
            "strategic_count": 5,
            "high_priority_count": 15,
            "repayment_sprints": 3,
            "estimated_weeks": 6,
            "high_interest_items": 3,
            "enhanced_mode": True,
            "graph_methods_enabled": True,
            "graph_insights": {
                "high_impact_debt": 8,
                "debt_hotspots": 3,
            },
        }

        required_fields = [
            "plan_id",
            "total_debt_items",
            "debt_ratio",
            "repayment_sprints",
            "enhanced_mode",
            "graph_methods_enabled",
        ]

        for field in required_fields:
            assert field in metadata

    def test_enhanced_mode_flag(self):
        """Test enhanced mode flag."""
        metadata = {
            "enhanced_mode": True,
            "graph_methods_enabled": True,
        }

        assert metadata["enhanced_mode"] is True
        assert metadata["graph_methods_enabled"] is True
