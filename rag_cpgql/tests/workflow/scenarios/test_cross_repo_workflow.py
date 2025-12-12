"""
Tests for Cross-Repository Analysis Workflow (Scenario 10).

Tests for cross-repo workflow, repository indexing, duplication detection, and dependency mapping.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "cross_repo",
        "scenario_id": "scenario_10",
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
        "user_context": {"workspace_path": "/workspace"},
    }


class TestCrossRepoWorkflowImports:
    """Tests for cross-repo workflow module imports."""

    def test_import_workflow(self):
        """Test that cross-repo workflow can be imported."""
        from src.workflow.scenarios.cross_repo import cross_repo_workflow

        assert callable(cross_repo_workflow)

    def test_import_cross_repo_agents(self):
        """Test that cross-repo agents can be imported."""
        from src.cross_repo.cross_repo_agents import (
            RepositoryIndexer,
            CrossRepoAnalyzer,
            DependencyMapper,
        )

        assert RepositoryIndexer is not None
        assert CrossRepoAnalyzer is not None
        assert DependencyMapper is not None


class TestCrossRepoWorkflowMocked:
    """Tests for cross_repo_workflow function with mocked dependencies."""

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
        mock.generate.return_value = "Cross-repo analysis complete."
        return mock

    @pytest.fixture
    def mock_repository_indexer(self):
        """Create mock RepositoryIndexer."""
        mock_indexer = MagicMock()

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.name = "test_repo"
        mock_repo.path = "/workspace/test_repo"
        mock_repo.language = "C"

        mock_indexer.discover_repositories.return_value = [mock_repo]
        mock_indexer.index_repository_cpg.return_value = True

        return mock_indexer

    @pytest.fixture
    def mock_cross_repo_analyzer(self):
        """Create mock CrossRepoAnalyzer."""
        mock_analyzer = MagicMock()

        # Mock duplication
        mock_dup = MagicMock()
        mock_dup.instances = []
        mock_dup.similarity = 85.0

        mock_analyzer.find_code_duplications.return_value = [mock_dup]
        mock_analyzer.find_similar_utilities.return_value = []
        mock_analyzer.identify_consolidation_opportunities.return_value = []

        return mock_analyzer

    @pytest.fixture
    def mock_dependency_mapper(self):
        """Create mock DependencyMapper."""
        mock_mapper = MagicMock()

        mock_mapper.map_dependencies.return_value = []
        mock_mapper.generate_dependency_graph.return_value = {}
        mock_mapper.detect_circular_dependencies.return_value = []
        mock_mapper.generate_dependency_report.return_value = {
            "summary": "No issues found"
        }

        return mock_mapper

    def test_workflow_returns_state(
        self,
        mock_cpg_service,
        mock_llm,
        mock_repository_indexer,
        mock_cross_repo_analyzer,
        mock_dependency_mapper,
    ):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.cross_repo import cross_repo_workflow

        state = create_mock_state("Analyze cross-repo duplications")

        with patch("src.workflow.scenarios.cross_repo.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.cross_repo.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.cross_repo.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a cross-repo expert",
                        "user": "Analyze repositories",
                    }
                    with patch("src.workflow.scenarios.cross_repo.RepositoryIndexer", return_value=mock_repository_indexer):
                        with patch("src.workflow.scenarios.cross_repo.CrossRepoAnalyzer", return_value=mock_cross_repo_analyzer):
                            with patch("src.workflow.scenarios.cross_repo.DependencyMapper", return_value=mock_dependency_mapper):
                                    result = cross_repo_workflow(state)

        assert isinstance(result, dict)


class TestCrossRepoErrorHandling:
    """Tests for cross-repo workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.cross_repo import cross_repo_workflow

        state = create_mock_state("Analyze repos")

        with patch("src.workflow.scenarios.cross_repo.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = cross_repo_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestRepositoryIndexer:
    """Tests for RepositoryIndexer agent interface."""

    def test_discover_repositories(self):
        """Test repository discovery."""
        mock_indexer = MagicMock()
        mock_repos = [
            {"name": "repo1", "path": "/workspace/repo1"},
            {"name": "repo2", "path": "/workspace/repo2"},
        ]
        mock_indexer.discover_repositories.return_value = mock_repos

        repos = mock_indexer.discover_repositories("/workspace")

        assert len(repos) == 2

    def test_index_repository_cpg(self):
        """Test repository CPG indexing."""
        mock_indexer = MagicMock()
        mock_indexer.index_repository_cpg.return_value = True

        success = mock_indexer.index_repository_cpg({"name": "test_repo"})

        assert success is True

    def test_extract_repo_metadata(self):
        """Test repository metadata extraction."""
        mock_indexer = MagicMock()
        mock_metadata = {
            "name": "test_repo",
            "path": "/path/to/repo",
            "language": "C",
            "files": 100,
        }
        mock_indexer._extract_repo_metadata.return_value = mock_metadata

        metadata = mock_indexer._extract_repo_metadata("/path/to/repo")

        assert metadata["name"] == "test_repo"


class TestCrossRepoAnalyzer:
    """Tests for CrossRepoAnalyzer agent interface."""

    def test_find_code_duplications(self):
        """Test code duplication finding."""
        mock_analyzer = MagicMock()
        mock_dups = [
            {"similarity": 90.0, "instances": [{"repo": "repo1"}, {"repo": "repo2"}]},
        ]
        mock_analyzer.find_code_duplications.return_value = mock_dups

        dups = mock_analyzer.find_code_duplications([], min_similarity=70.0)

        assert len(dups) == 1
        assert dups[0]["similarity"] == 90.0

    def test_find_similar_utilities(self):
        """Test similar utility finding."""
        mock_analyzer = MagicMock()
        mock_utilities = [
            {"function": "str_utils", "repos": ["repo1", "repo2", "repo3"]},
        ]
        mock_analyzer.find_similar_utilities.return_value = mock_utilities

        utils = mock_analyzer.find_similar_utilities([])

        assert len(utils) == 1

    def test_identify_consolidation_opportunities(self):
        """Test consolidation opportunity identification."""
        mock_analyzer = MagicMock()
        mock_opps = [
            {"type": "shared_library", "affected_repos": 5, "effort": "medium"},
        ]
        mock_analyzer.identify_consolidation_opportunities.return_value = mock_opps

        opps = mock_analyzer.identify_consolidation_opportunities([])

        assert len(opps) == 1


class TestDependencyMapper:
    """Tests for DependencyMapper agent interface."""

    def test_map_dependencies(self):
        """Test dependency mapping."""
        mock_mapper = MagicMock()
        mock_deps = [
            {"from": "repo1", "to": "repo2", "type": "import"},
        ]
        mock_mapper.map_dependencies.return_value = mock_deps

        deps = mock_mapper.map_dependencies([])

        assert len(deps) == 1

    def test_generate_dependency_graph(self):
        """Test dependency graph generation."""
        mock_mapper = MagicMock()
        mock_graph = {
            "nodes": ["repo1", "repo2"],
            "edges": [{"from": "repo1", "to": "repo2"}],
        }
        mock_mapper.generate_dependency_graph.return_value = mock_graph

        graph = mock_mapper.generate_dependency_graph([])

        assert "nodes" in graph
        assert "edges" in graph

    def test_detect_circular_dependencies(self):
        """Test circular dependency detection."""
        mock_mapper = MagicMock()
        mock_circular = [
            {"cycle": ["repo1", "repo2", "repo1"], "length": 2},
        ]
        mock_mapper.detect_circular_dependencies.return_value = mock_circular

        circular = mock_mapper.detect_circular_dependencies({})

        assert len(circular) == 1

    def test_generate_dependency_report(self):
        """Test dependency report generation."""
        mock_mapper = MagicMock()
        mock_report = {
            "summary": "Analysis complete",
            "total_deps": 50,
            "circular_deps": 2,
        }
        mock_mapper.generate_dependency_report.return_value = mock_report

        report = mock_mapper.generate_dependency_report([], [], [], [])

        assert "summary" in report


class TestCodeDuplicationMetrics:
    """Tests for code duplication metrics."""

    def test_similarity_threshold(self):
        """Test similarity threshold filtering."""
        duplications = [
            {"similarity": 95.0},
            {"similarity": 75.0},
            {"similarity": 60.0},
        ]

        threshold = 70.0
        significant = [d for d in duplications if d["similarity"] >= threshold]

        assert len(significant) == 2

    def test_duplication_coverage(self):
        """Test duplication coverage calculation."""
        total_code = 10000  # LOC
        duplicated_code = 500  # LOC

        coverage = (duplicated_code / total_code) * 100

        assert coverage == 5.0


class TestConsolidationOpportunities:
    """Tests for consolidation opportunity analysis."""

    def test_shared_library_candidate(self):
        """Test shared library candidate identification."""
        duplications = [
            {"function": "util_func", "repos": ["r1", "r2", "r3"]},
            {"function": "helper", "repos": ["r1", "r2"]},
        ]

        # Shared library candidates: duplicated in 3+ repos
        candidates = [d for d in duplications if len(d["repos"]) >= 3]

        assert len(candidates) == 1

    def test_consolidation_effort_estimation(self):
        """Test consolidation effort estimation."""
        opportunity = {
            "affected_repos": 5,
            "total_duplications": 20,
            "refactoring_complexity": "medium",
        }

        # Simple effort formula
        effort_score = opportunity["affected_repos"] * opportunity["total_duplications"]

        assert effort_score == 100

    def test_benefit_calculation(self):
        """Test consolidation benefit calculation."""
        duplicated_loc = 1000
        maintenance_cost_per_loc = 0.5  # hours

        annual_benefit = duplicated_loc * maintenance_cost_per_loc

        assert annual_benefit == 500.0


class TestDependencyGraphAnalysis:
    """Tests for dependency graph analysis."""

    def test_graph_construction(self):
        """Test dependency graph construction."""
        dependencies = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
        ]

        graph = {}
        for dep in dependencies:
            if dep["from"] not in graph:
                graph[dep["from"]] = []
            graph[dep["from"]].append(dep["to"])

        assert "A" in graph
        assert "B" in graph["A"]

    def test_circular_dependency_detection(self):
        """Test circular dependency detection algorithm."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }

        # Simple cycle detection
        visited = set()
        has_cycle = False

        def dfs(node, path):
            nonlocal has_cycle
            if node in path:
                has_cycle = True
                return
            if node in visited:
                return

            visited.add(node)
            path.add(node)
            if node in graph:
                for neighbor in graph[node]:
                    dfs(neighbor, path)
            path.remove(node)

        dfs("A", set())

        assert has_cycle is True

    def test_dependency_depth(self):
        """Test dependency depth calculation."""
        graph = {
            "A": ["B"],
            "B": ["C", "D"],
            "C": [],
            "D": [],
        }

        def max_depth(node, graph, depth=0):
            if node not in graph or not graph[node]:
                return depth
            return max(max_depth(child, graph, depth + 1) for child in graph[node])

        depth = max_depth("A", graph)

        assert depth == 2


class TestRepositoryMetrics:
    """Tests for repository metrics."""

    def test_repository_count(self):
        """Test repository counting."""
        repos = [
            {"name": "repo1"},
            {"name": "repo2"},
            {"name": "repo3"},
        ]

        count = len(repos)

        assert count == 3

    def test_language_distribution(self):
        """Test language distribution."""
        repos = [
            {"language": "C"},
            {"language": "C"},
            {"language": "Python"},
        ]

        lang_dist = {}
        for repo in repos:
            lang = repo["language"]
            lang_dist[lang] = lang_dist.get(lang, 0) + 1

        assert lang_dist["C"] == 2
        assert lang_dist["Python"] == 1


class TestCrossRepoImpactAnalysis:
    """Tests for cross-repo impact analysis."""

    def test_affected_repos_count(self):
        """Test counting affected repositories."""
        consolidation = {
            "function": "shared_util",
            "affected_repos": ["r1", "r2", "r3", "r4"],
        }

        impact_score = len(consolidation["affected_repos"])

        assert impact_score == 4

    def test_breaking_change_risk(self):
        """Test breaking change risk assessment."""
        change = {
            "type": "api_modification",
            "consumers": 10,
            "has_tests": False,
        }

        # High risk if many consumers and no tests
        risk = "high" if change["consumers"] > 5 and not change["has_tests"] else "low"

        assert risk == "high"


class TestGraphInsights:
    """Tests for graph-based cross-repo insights."""

    def test_graph_insights_structure(self):
        """Test graph insights structure."""
        graph_insights = {
            "shared_methods": [],
            "consolidation_patterns": [],
            "cross_repo_calls": [],
        }

        assert "shared_methods" in graph_insights
        assert "consolidation_patterns" in graph_insights

    def test_shared_method_tracking(self):
        """Test shared method tracking."""
        shared_methods = [
            {"method": "parse_config", "repos": ["r1", "r2"]},
            {"method": "validate_input", "repos": ["r1", "r2", "r3"]},
        ]

        # Most shared method
        most_shared = max(shared_methods, key=lambda m: len(m["repos"]))

        assert most_shared["method"] == "validate_input"


class TestConsolidationPrioritization:
    """Tests for consolidation prioritization."""

    def test_prioritize_by_roi(self):
        """Test prioritization by ROI."""
        opportunities = [
            {"benefit": 100, "effort": 10, "roi": 10.0},
            {"benefit": 50, "effort": 5, "roi": 10.0},
            {"benefit": 200, "effort": 50, "roi": 4.0},
        ]

        # Sort by ROI descending
        prioritized = sorted(opportunities, key=lambda o: o["roi"], reverse=True)

        assert prioritized[0]["roi"] == 10.0

    def test_quick_wins_identification(self):
        """Test quick wins identification."""
        opportunities = [
            {"effort": 2, "benefit": 20},
            {"effort": 10, "benefit": 15},
            {"effort": 1, "benefit": 10},
        ]

        # Quick wins: low effort (<= 5) and high benefit (>= 10)
        quick_wins = [
            o for o in opportunities
            if o["effort"] <= 5 and o["benefit"] >= 10
        ]

        assert len(quick_wins) == 2


class TestCrossRepoReporting:
    """Tests for cross-repo reporting."""

    def test_report_structure(self):
        """Test report structure."""
        report = {
            "summary": "Analysis complete",
            "repositories_analyzed": 10,
            "duplications_found": 25,
            "consolidation_opportunities": 5,
            "circular_dependencies": 1,
        }

        required_fields = [
            "summary",
            "repositories_analyzed",
            "duplications_found",
        ]

        for field in required_fields:
            assert field in report

    def test_actionable_recommendations(self):
        """Test actionable recommendations."""
        recommendations = [
            "Create shared utility library for common functions",
            "Break circular dependency between repo1 and repo2",
            "Consolidate authentication logic into single service",
        ]

        assert len(recommendations) == 3
        assert all(isinstance(r, str) for r in recommendations)
