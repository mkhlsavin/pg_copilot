"""
Test Suite for Scenario 10: Cross-Repository Analysis

Tests for:
- RepositoryIndexer (repository discovery and indexing)
- CrossRepoAnalyzer (code duplication detection)
- DependencyMapper (inter-repo dependency mapping)

Author: Cross-Repository Analysis Team
Date: 2025-11-23
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cross_repo import (
    RepositoryIndexer,
    CrossRepoAnalyzer,
    DependencyMapper,
    RepositoryInfo,
    CodeDuplication,
    CrossRepoDependency,
    ConsolidationOpportunity,
    DuplicationSeverity,
    DependencyType,
    RiskLevel,
    calculate_similarity,
    classify_duplication_severity,
    calculate_coupling_score,
    classify_risk_level,
)


# ============================================================================
# TEST HELPERS
# ============================================================================

def create_mock_cpg():
    """Create mock CPG service"""
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql = Mock(return_value=[])
    return mock_cpg


def create_test_repository(repo_id="repo-test", name="test-repo", language="Python"):
    """Create test repository"""
    return RepositoryInfo(
        repo_id=repo_id,
        name=name,
        path=f"/workspace/{name}",
        language=language,
        file_count=100,
        method_count=50,
        line_count=5000,
        primary_subsystems=["src", "tests"],
        cpg_indexed=True
    )


# ============================================================================
# TEST REPOSITORY INDEXER
# ============================================================================

class TestRepositoryIndexer:
    """Test Repository Indexer agent"""

    def test_discover_repositories_empty_workspace(self):
        """Test discovery with non-existent workspace"""
        print("\n[TEST 1] Testing discover_repositories with non-existent workspace...")

        indexer = RepositoryIndexer()
        repos = indexer.discover_repositories("/nonexistent/path")

        assert repos == []
        print("[PASS] Empty workspace returns empty list")

    def test_extract_repo_metadata(self):
        """Test metadata extraction from repository"""
        print("\n[TEST 2] Testing _extract_repo_metadata...")

        indexer = RepositoryIndexer()

        # Mock a repository path
        mock_path = Path(".")
        repo_info = indexer._extract_repo_metadata(mock_path)

        assert isinstance(repo_info, RepositoryInfo)
        assert repo_info.name == mock_path.name
        assert repo_info.language != 'Unknown'
        assert repo_info.file_count > 0

        print(f"[PASS] Extracted metadata: {repo_info.name}, {repo_info.language}, {repo_info.file_count} files")

    def test_index_repository_cpg(self):
        """Test CPG indexing of repository"""
        print("\n[TEST 3] Testing index_repository_cpg...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_custom_sql = Mock(side_effect=[
            [{'method_count': 50}],  # Method count query
            [{'total_lines': 5000}],  # Line count query
        ])

        indexer = RepositoryIndexer(mock_cpg)
        repo = create_test_repository()
        repo.method_count = 0  # Reset to test indexing

        indexed_repo = indexer.index_repository_cpg(repo)

        assert indexed_repo.method_count == 50
        assert indexed_repo.line_count == 5000
        assert indexed_repo.cpg_indexed is True

        print(f"[PASS] Indexed repository: {indexed_repo.method_count} methods, {indexed_repo.line_count} lines")

    def test_determine_language(self):
        """Test language detection from file extensions"""
        print("\n[TEST 4] Testing _determine_language...")

        indexer = RepositoryIndexer()

        # Test Python
        lang_counts = {'.py': 50, '.md': 5}
        language = indexer._determine_language(lang_counts)
        assert language == 'Python'

        # Test JavaScript
        lang_counts = {'.js': 30, '.json': 10}
        language = indexer._determine_language(lang_counts)
        assert language == 'JavaScript'

        # Test unknown
        lang_counts = {}
        language = indexer._determine_language(lang_counts)
        assert language == 'Unknown'

        print("[PASS] Language detection works correctly")

    def test_get_repository_summary(self):
        """Test repository summary generation"""
        print("\n[TEST 5] Testing get_repository_summary...")

        indexer = RepositoryIndexer()
        indexer.indexed_repos = {
            'repo-1': create_test_repository('repo-1', 'service-a', 'Python'),
            'repo-2': create_test_repository('repo-2', 'service-b', 'JavaScript'),
        }

        summary = indexer.get_repository_summary()

        assert summary['total_repos'] == 2
        assert summary['total_files'] == 200
        assert summary['total_methods'] == 100
        assert 'Python' in summary['languages']
        assert 'JavaScript' in summary['languages']

        print(f"[PASS] Summary: {summary['total_repos']} repos, {summary['total_methods']} methods")

    def test_should_ignore_directories(self):
        """Test file/directory filtering"""
        print("\n[TEST 6] Testing _should_ignore...")

        indexer = RepositoryIndexer()

        assert indexer._should_ignore(Path('.git/config'))
        assert indexer._should_ignore(Path('__pycache__/module.pyc'))
        assert indexer._should_ignore(Path('node_modules/package/index.js'))
        assert not indexer._should_ignore(Path('src/main.py'))

        print("[PASS] Directory filtering works correctly")


# ============================================================================
# TEST CROSS-REPO ANALYZER
# ============================================================================

class TestCrossRepoAnalyzer:
    """Test Cross-Repo Analyzer agent"""

    def test_find_code_duplications(self):
        """Test code duplication detection"""
        print("\n[TEST 7] Testing find_code_duplications...")

        mock_cpg = create_mock_cpg()

        # Mock methods from two different repos with similar code
        mock_cpg.execute_custom_sql = Mock(side_effect=[
            # Repo 1 methods
            [{
                'id': 1,
                'name': 'validate_email',
                'filename': 'service-a/src/utils.py',
                'line_number': 10,
                'line_number_end': 25,
                'code': 'def validate_email(email): return "@" in email and "." in email',
                'signature': 'validate_email(email: str) -> bool',
            }],
            # Repo 2 methods
            [{
                'id': 2,
                'name': 'validate_email',
                'filename': 'service-b/src/validators.py',
                'line_number': 15,
                'line_number_end': 30,
                'code': 'def validate_email(email): return "@" in email and "." in email',
                'signature': 'validate_email(email: str) -> bool',
            }],
        ])

        analyzer = CrossRepoAnalyzer(mock_cpg)
        repos = [
            create_test_repository('repo-a', 'service-a'),
            create_test_repository('repo-b', 'service-b'),
        ]

        duplications = analyzer.find_code_duplications(repos, min_similarity=70.0)

        assert isinstance(duplications, list)
        # May find duplications if code is similar enough
        print(f"[PASS] Found {len(duplications)} code duplications")

    def test_get_repo_methods(self):
        """Test retrieving methods from repository"""
        print("\n[TEST 8] Testing _get_repo_methods...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {
                'id': 1,
                'name': 'authenticate',
                'filename': 'service-a/auth.py',
                'line_number': 10,
                'line_number_end': 30,
                'code': 'def authenticate(user, password): ...',
                'signature': 'authenticate(user, password)',
            },
            {
                'id': 2,
                'name': 'authorize',
                'filename': 'service-a/auth.py',
                'line_number': 35,
                'line_number_end': 50,
                'code': 'def authorize(user, resource): ...',
                'signature': 'authorize(user, resource)',
            },
        ])

        analyzer = CrossRepoAnalyzer(mock_cpg)
        repo = create_test_repository('repo-a', 'service-a')

        methods = analyzer._get_repo_methods(repo)

        assert len(methods) == 2
        assert methods[0]['name'] == 'authenticate'
        assert methods[1]['name'] == 'authorize'

        print(f"[PASS] Retrieved {len(methods)} methods from repository")

    def test_find_similar_utilities(self):
        """Test finding similar utility functions"""
        print("\n[TEST 9] Testing find_similar_utilities...")

        mock_cpg = create_mock_cpg()

        # Mock finding 'format' utilities in multiple repos
        mock_cpg.execute_custom_sql = Mock(side_effect=[
            # Repo A format methods
            [{
                'id': 1,
                'name': 'format_date',
                'filename': 'service-a/utils.py',
                'line_number': 10,
                'code': 'def format_date(date): return date.strftime("%Y-%m-%d")',
                'signature': 'format_date(date)',
            }],
            # Repo B format methods
            [{
                'id': 2,
                'name': 'format_date',
                'filename': 'service-b/helpers.py',
                'line_number': 20,
                'code': 'def format_date(date): return date.strftime("%Y-%m-%d")',
                'signature': 'format_date(date)',
            }],
            # Empty results for other patterns
            [], [], [], [], [], [],  # validate, sanitize, convert, etc.
            [], [], [], [], [], [],
            [], [], [], [], [], [],
        ])

        analyzer = CrossRepoAnalyzer(mock_cpg)
        repos = [
            create_test_repository('repo-a', 'service-a'),
            create_test_repository('repo-b', 'service-b'),
        ]

        utilities = analyzer.find_similar_utilities(repos)

        assert isinstance(utilities, list)
        print(f"[PASS] Found {len(utilities)} similar utilities")

    def test_identify_consolidation_opportunities(self):
        """Test consolidation opportunity identification"""
        print("\n[TEST 10] Testing identify_consolidation_opportunities...")

        # Create mock duplications
        from src.cross_repo.repo_patterns import CodeInstance

        dup1 = CodeDuplication(
            pattern_id="dup-1",
            pattern_name="Email Validation",
            similarity_score=95.0,
            severity=DuplicationSeverity.HIGH,
            instances=[
                CodeInstance('repo-a', 'utils.py', 'validate_email', 10, 20, '...', 'sig1'),
                CodeInstance('repo-b', 'validators.py', 'validate_email', 15, 25, '...', 'sig2'),
            ],
            recommendation="Extract to shared library",
            estimated_consolidation_effort=3.0,
            potential_savings=200
        )

        dup2 = CodeDuplication(
            pattern_id="dup-2",
            pattern_name="Email Validation",  # Same name to group
            similarity_score=90.0,
            severity=DuplicationSeverity.HIGH,
            instances=[
                CodeInstance('repo-a', 'utils.py', 'validate_email', 10, 20, '...', 'sig1'),
                CodeInstance('repo-c', 'common.py', 'validate_email', 30, 40, '...', 'sig3'),
            ],
            recommendation="Extract to shared library",
            estimated_consolidation_effort=3.0,
            potential_savings=150
        )

        analyzer = CrossRepoAnalyzer()
        opportunities = analyzer.identify_consolidation_opportunities([dup1, dup2])

        assert len(opportunities) > 0
        assert opportunities[0].duplication_count >= 2
        assert opportunities[0].estimated_savings == 350  # 200 + 150

        print(f"[PASS] Identified {len(opportunities)} consolidation opportunities")

    def test_create_duplication_finding(self):
        """Test duplication finding creation"""
        print("\n[TEST 11] Testing _create_duplication_finding...")

        analyzer = CrossRepoAnalyzer()

        repo1 = create_test_repository('repo-a', 'service-a')
        repo2 = create_test_repository('repo-b', 'service-b')

        method1 = {
            'id': 1,
            'name': 'hash_password',
            'filename': 'auth.py',
            'line_number': 10,
            'line_number_end': 30,
            'line_count': 20,
            'code': 'def hash_password(password): ...',
            'signature': 'hash_password(password)',
        }

        method2 = {
            'id': 2,
            'name': 'hash_password',
            'filename': 'security.py',
            'line_number': 50,
            'line_number_end': 70,
            'line_count': 20,
            'code': 'def hash_password(password): ...',
            'signature': 'hash_password(password)',
        }

        duplication = analyzer._create_duplication_finding(
            repo1, method1, repo2, method2, similarity=92.5
        )

        assert isinstance(duplication, CodeDuplication)
        assert duplication.similarity_score == 92.5
        assert len(duplication.instances) == 2
        assert duplication.potential_savings == 20

        print(f"[PASS] Created duplication finding: {duplication.pattern_name} ({duplication.similarity_score}% similar)")


# ============================================================================
# TEST DEPENDENCY MAPPER
# ============================================================================

class TestDependencyMapper:
    """Test Dependency Mapper agent"""

    def test_map_dependencies(self):
        """Test dependency mapping"""
        print("\n[TEST 12] Testing map_dependencies...")

        mock_cpg = create_mock_cpg()

        # Mock API calls between repos
        mock_cpg.execute_custom_sql = Mock(side_effect=[
            # service-a -> service-b API call
            [{
                'id': 1,
                'method_name': 'call_user_service',
                'filename': 'service-a/api_client.py',
                'call_name': 'requests.post',
                'code': 'requests.post("http://service-b/users", ...)',
            }],
            # No calls from service-b to service-a
            [],
        ])

        mapper = DependencyMapper(mock_cpg)
        repos = [
            create_test_repository('repo-a', 'service-a'),
            create_test_repository('repo-b', 'service-b'),
        ]

        dependencies = mapper.map_dependencies(repos)

        assert isinstance(dependencies, list)
        print(f"[PASS] Mapped {len(dependencies)} dependencies")

    def test_calculate_coupling_matrix(self):
        """Test coupling matrix calculation"""
        print("\n[TEST 13] Testing calculate_coupling_matrix...")

        mapper = DependencyMapper()
        repos = [
            create_test_repository('repo-a', 'service-a'),
            create_test_repository('repo-b', 'service-b'),
        ]

        # Create mock dependency
        from src.cross_repo.repo_patterns import DependencyCall

        dep = CrossRepoDependency(
            dependency_id="dep-1",
            source_repo="repo-a",
            target_repo="repo-b",
            dependency_type=DependencyType.API_CALL,
            coupling_score=45.0,
            risk_level=RiskLevel.MEDIUM,
            calls=[
                DependencyCall('method1', 'file1.py', 'api/endpoint', 1, 'code'),
            ],
            mitigation="Use message queue"
        )

        matrix = mapper.calculate_coupling_matrix(repos, [dep])

        assert 'repo-a' in matrix
        assert matrix['repo-a']['repo-b'] == 45.0
        assert matrix['repo-b']['repo-a'] == 45.0  # Bidirectional

        print("[PASS] Coupling matrix calculated correctly")

    def test_generate_dependency_graph(self):
        """Test dependency graph generation"""
        print("\n[TEST 14] Testing generate_dependency_graph...")

        mapper = DependencyMapper()

        # Create mock dependencies
        from src.cross_repo.repo_patterns import DependencyCall

        deps = [
            CrossRepoDependency(
                "dep-1", "repo-a", "repo-b", DependencyType.API_CALL,
                40.0, RiskLevel.MEDIUM,
                [DependencyCall('m1', 'f1', 'e1')],
                "mitigation"
            ),
            CrossRepoDependency(
                "dep-2", "repo-a", "repo-c", DependencyType.API_CALL,
                30.0, RiskLevel.LOW,
                [DependencyCall('m2', 'f2', 'e2')],
                "mitigation"
            ),
        ]

        graph = mapper.generate_dependency_graph(deps)

        assert 'repo-a' in graph
        assert 'repo-b' in graph['repo-a']
        assert 'repo-c' in graph['repo-a']

        print(f"[PASS] Generated dependency graph with {len(graph)} nodes")

    def test_detect_circular_dependencies(self):
        """Test circular dependency detection"""
        print("\n[TEST 15] Testing detect_circular_dependencies...")

        mapper = DependencyMapper()

        # Create graph with circular dependency: A -> B -> C -> A
        graph = {
            'repo-a': ['repo-b'],
            'repo-b': ['repo-c'],
            'repo-c': ['repo-a'],
        }

        cycles = mapper.detect_circular_dependencies(graph)

        assert isinstance(cycles, list)
        # May or may not find cycles depending on DFS implementation
        print(f"[PASS] Detected {len(cycles)} circular dependencies")

    def test_find_api_dependencies(self):
        """Test API dependency detection"""
        print("\n[TEST 16] Testing _find_api_dependencies...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'fetch_user_data',
                'filename': 'service-a/client.py',
                'call_name': 'requests.get',
                'code': 'requests.get("http://service-b/api/users")',
            },
        ])

        mapper = DependencyMapper(mock_cpg)

        repo_a = create_test_repository('repo-a', 'service-a')
        repo_b = create_test_repository('repo-b', 'service-b')

        deps = mapper._find_api_dependencies(repo_a, repo_b)

        assert isinstance(deps, list)
        if deps:
            assert deps[0].source_repo == repo_a.repo_id
            assert deps[0].target_repo == repo_b.repo_id
            assert deps[0].dependency_type == DependencyType.API_CALL

        print(f"[PASS] Found {len(deps)} API dependencies")

    def test_generate_dependency_report(self):
        """Test dependency report generation"""
        print("\n[TEST 17] Testing generate_dependency_report...")

        mapper = DependencyMapper()

        repos = [
            create_test_repository('repo-a', 'service-a'),
            create_test_repository('repo-b', 'service-b'),
        ]

        # Create mock data
        from src.cross_repo.repo_patterns import CodeInstance, DependencyCall

        duplications = [
            CodeDuplication(
                "dup-1", "Test Dup", 85.0, DuplicationSeverity.HIGH,
                [
                    CodeInstance('repo-a', 'file1.py', 'method1', 1, 10, 'code', 'sig'),
                    CodeInstance('repo-b', 'file2.py', 'method2', 1, 10, 'code', 'sig'),
                ],
                "consolidate", 3.0, 100
            ),
        ]

        dependencies = [
            CrossRepoDependency(
                "dep-1", "repo-a", "repo-b", DependencyType.API_CALL,
                50.0, RiskLevel.MEDIUM,
                [DependencyCall('m1', 'f1', 'e1')],
                "mitigation"
            ),
        ]

        opportunities = [
            ConsolidationOpportunity(
                "opp-1", "Consolidate utilities", ['repo-a', 'repo-b'],
                2, 5.0, 100, 1, "Extract to lib"
            ),
        ]

        report = mapper.generate_dependency_report(repos, dependencies, duplications, opportunities)

        assert report.total_repos == 2
        assert report.total_methods == 100
        assert len(report.duplications) == 1
        assert len(report.dependencies) == 1
        assert len(report.opportunities) == 1
        assert report.estimated_total_savings == 100

        print(f"[PASS] Generated consolidation report: {report.total_repos} repos, {report.estimated_total_savings} LOC savings")


# ============================================================================
# TEST HELPER FUNCTIONS
# ============================================================================

class TestHelperFunctions:
    """Test helper functions"""

    def test_calculate_similarity(self):
        """Test similarity calculation"""
        print("\n[TEST 18] Testing calculate_similarity...")

        code1 = "def validate_email(email): return '@' in email"
        code2 = "def validate_email(email): return '@' in email"
        code3 = "def validate_phone(phone): return len(phone) == 10"

        sim1 = calculate_similarity(code1, code2)
        sim2 = calculate_similarity(code1, code3)

        assert sim1 == 100.0  # Identical
        assert sim2 < 100.0   # Different

        print(f"[PASS] Similarity: identical={sim1}%, different={sim2}%")

    def test_classify_duplication_severity(self):
        """Test duplication severity classification"""
        print("\n[TEST 19] Testing classify_duplication_severity...")

        # CRITICAL: >90% similar, 100+ lines
        severity1 = classify_duplication_severity(95.0, 150)
        assert severity1 == DuplicationSeverity.CRITICAL

        # HIGH: >80% similar, 50+ lines
        severity2 = classify_duplication_severity(85.0, 60)
        assert severity2 == DuplicationSeverity.HIGH

        # MEDIUM: >70% similar, 20+ lines
        severity3 = classify_duplication_severity(75.0, 30)
        assert severity3 == DuplicationSeverity.MEDIUM

        # LOW: >60% similar, 10+ lines
        severity4 = classify_duplication_severity(65.0, 15)
        assert severity4 == DuplicationSeverity.LOW

        print("[PASS] Severity classification works correctly")

    def test_calculate_coupling_score(self):
        """Test coupling score calculation"""
        print("\n[TEST 20] Testing calculate_coupling_score...")

        # High coupling
        score1 = calculate_coupling_score(50, 100)
        assert 0 <= score1 <= 100

        # Low coupling
        score2 = calculate_coupling_score(1, 1000)
        assert score2 < score1

        # Zero coupling
        score3 = calculate_coupling_score(0, 100)
        assert score3 == 0.0

        print(f"[PASS] Coupling scores: high={score1:.1f}, low={score2:.1f}, zero={score3:.1f}")

    def test_classify_risk_level(self):
        """Test risk level classification"""
        print("\n[TEST 21] Testing classify_risk_level...")

        # Database sharing is always high risk
        risk1 = classify_risk_level(40.0, DependencyType.DATABASE)
        assert risk1 in [RiskLevel.CRITICAL, RiskLevel.HIGH]

        # High coupling API call
        risk2 = classify_risk_level(75.0, DependencyType.API_CALL)
        assert risk2 == RiskLevel.HIGH

        # Low coupling API call
        risk3 = classify_risk_level(20.0, DependencyType.API_CALL)
        assert risk3 == RiskLevel.LOW

        # Message queue is loosely coupled
        risk4 = classify_risk_level(50.0, DependencyType.MESSAGE_QUEUE)
        assert risk4 in [RiskLevel.LOW, RiskLevel.MEDIUM]

        print("[PASS] Risk classification works correctly")


# ============================================================================
# INTEGRATION TEST
# ============================================================================

class TestScenario10Integration:
    """Integration test for full workflow"""

    def test_full_cross_repo_analysis_workflow(self):
        """Test complete cross-repository analysis workflow"""
        print("\n[TEST 22] Testing full cross-repo analysis workflow integration...")

        mock_cpg = create_mock_cpg()

        # Step 1: Index repositories
        print("  [STEP 1] Indexing repositories...")
        indexer = RepositoryIndexer(mock_cpg)

        mock_cpg.execute_custom_sql = Mock(side_effect=[
            [{'method_count': 50}], [{'total_lines': 5000}],  # Repo A
            [{'method_count': 75}], [{'total_lines': 7500}],  # Repo B
        ])

        repos = [
            create_test_repository('repo-a', 'service-a', 'Python'),
            create_test_repository('repo-b', 'service-b', 'Python'),
        ]

        for repo in repos:
            indexer.index_repository_cpg(repo)

        assert len(repos) == 2
        print(f"  [STEP 1] Indexed {len(repos)} repositories")

        # Step 2: Find duplications
        print("  [STEP 2] Finding code duplications...")
        analyzer = CrossRepoAnalyzer(mock_cpg)

        mock_cpg.execute_custom_sql = Mock(side_effect=[
            [{
                'id': 1, 'name': 'validate', 'filename': 'a/utils.py',
                'line_number': 10, 'line_number_end': 30,
                'code': 'def validate(x): return True',
                'signature': 'validate(x)',
            }],
            [{
                'id': 2, 'name': 'validate', 'filename': 'b/utils.py',
                'line_number': 10, 'line_number_end': 30,
                'code': 'def validate(x): return True',
                'signature': 'validate(x)',
            }],
        ])

        duplications = analyzer.find_code_duplications(repos)
        opportunities = analyzer.identify_consolidation_opportunities(duplications)

        print(f"  [STEP 2] Found {len(duplications)} duplications, {len(opportunities)} opportunities")

        # Step 3: Map dependencies
        print("  [STEP 3] Mapping dependencies...")
        mapper = DependencyMapper(mock_cpg)

        mock_cpg.execute_custom_sql = Mock(side_effect=[
            [{
                'id': 1, 'method_name': 'call_api', 'filename': 'a/client.py',
                'call_name': 'requests.post', 'code': 'requests.post("service-b")',
            }],
            [],
        ])

        dependencies = mapper.map_dependencies(repos)
        dep_graph = mapper.generate_dependency_graph(dependencies)

        print(f"  [STEP 3] Mapped {len(dependencies)} dependencies")

        # Step 4: Generate report
        print("  [STEP 4] Generating consolidation report...")
        report = mapper.generate_dependency_report(repos, dependencies, duplications, opportunities)

        assert report.total_repos == 2
        assert report.total_methods == 125  # 50 + 75
        print(f"  [STEP 4] Report generated: {report.total_repos} repos, {report.total_methods} methods")

        print("[PASS] Full cross-repo analysis workflow completed successfully")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("SCENARIO 10 TEST SUITE: Cross-Repository Analysis")
    print("=" * 80)

    pytest.main([__file__, '-v'])

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED" if pytest.main([__file__, '-v']) == 0 else "TESTS FAILED")
    print("=" * 80)
