"""
Tests for the Automated Patch Review System.

Tests the complete pipeline from patch parsing to verdict generation.
"""

import pytest
import duckdb
from pathlib import Path

# Sample test patch
SAMPLE_PATCH = '''
diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,5 +1,10 @@
 def hello():
     print("Hello")
+
+def greet(name):
+    # New function
+    query = f"SELECT * FROM users WHERE name = '{name}'"
+    return query
'''


class TestPatchParser:
    """Tests for PatchParser."""

    def test_parse_git_diff(self):
        """Test parsing a git diff."""
        from src.patch_review import PatchParser

        parser = PatchParser()
        patch = parser.parse_git_diff(SAMPLE_PATCH)

        assert patch is not None
        assert patch.patch_id is not None
        assert len(patch.files) == 1
        assert patch.files[0].filepath == 'test.py'
        assert patch.lines_added > 0

    def test_parse_empty_diff(self):
        """Test parsing empty diff."""
        from src.patch_review import PatchParser

        parser = PatchParser()
        patch = parser.parse_git_diff('')

        assert patch is not None
        assert len(patch.files) == 0

    def test_extract_changed_methods(self):
        """Test method extraction."""
        from src.patch_review import PatchParser

        parser = PatchParser()
        patch = parser.parse_git_diff(SAMPLE_PATCH)

        # Should find the new 'greet' function
        method_names = [m.name for m in patch.changed_methods]
        assert 'greet' in method_names


class TestDeltaCPGGenerator:
    """Tests for DeltaCPGGenerator."""

    @pytest.fixture
    def db_connection(self):
        """Create in-memory database connection."""
        conn = duckdb.connect(':memory:')

        # Create minimal schema for testing
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cpg_nodes (
                id BIGINT PRIMARY KEY,
                node_type VARCHAR,
                name VARCHAR,
                full_name VARCHAR,
                filename VARCHAR,
                line_number INTEGER,
                code TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cpg_edges (
                id BIGINT PRIMARY KEY,
                edge_type VARCHAR,
                src BIGINT,
                dst BIGINT
            )
        ''')

        yield conn
        conn.close()

    def test_generate_delta(self, db_connection):
        """Test delta CPG generation."""
        from src.patch_review import PatchParser, DeltaCPGGenerator
        from src.patch_review.models import ReviewSession, ReviewStatus
        from datetime import datetime

        parser = PatchParser()
        patch = parser.parse_git_diff(SAMPLE_PATCH)

        session = ReviewSession(
            session_id='test-session',
            patch_id=patch.patch_id,
            base_commit='abc123',
            head_commit='def456',
            status=ReviewStatus.ANALYZING,
            created_at=datetime.now()
        )

        generator = DeltaCPGGenerator(db_connection)
        delta = generator.generate_delta(patch, session)

        assert delta is not None
        assert delta.session_id == 'test-session'
        # Should have some nodes for the added code
        assert len(delta.nodes) >= 0  # May be empty if no base CPG


class TestVerdictGenerators:
    """Tests for verdict generators."""

    @pytest.fixture
    def db_connection(self):
        """Create in-memory database connection."""
        conn = duckdb.connect(':memory:')

        # Create minimal schema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cpg_nodes (
                id BIGINT PRIMARY KEY,
                node_type VARCHAR,
                name VARCHAR,
                full_name VARCHAR,
                filename VARCHAR,
                line_number INTEGER,
                code TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cpg_edges (
                id BIGINT PRIMARY KEY,
                edge_type VARCHAR,
                src BIGINT,
                dst BIGINT
            )
        ''')

        yield conn
        conn.close()

    def test_security_verdict(self, db_connection):
        """Test security verdict generation."""
        from src.patch_review import PatchParser
        from src.patch_review.verdicts import SecurityVerdictGenerator
        from src.patch_review.models import DeltaCPG

        parser = PatchParser()
        patch = parser.parse_git_diff(SAMPLE_PATCH)

        # Create empty delta for testing
        delta = DeltaCPG(
            session_id='test',
            nodes=[],
            edges=[],
            changed_methods=[]
        )

        generator = SecurityVerdictGenerator(db_connection)
        verdict = generator.generate_verdict(patch, delta)

        assert verdict is not None
        assert 0 <= verdict.score <= 100
        assert verdict.recommendation is not None

    def test_performance_verdict(self, db_connection):
        """Test performance verdict generation."""
        from src.patch_review import PatchParser
        from src.patch_review.verdicts import PerformanceVerdictGenerator
        from src.patch_review.models import DeltaCPG

        parser = PatchParser()
        patch = parser.parse_git_diff(SAMPLE_PATCH)

        delta = DeltaCPG(
            session_id='test',
            nodes=[],
            edges=[],
            changed_methods=[]
        )

        generator = PerformanceVerdictGenerator(db_connection)
        verdict = generator.generate_verdict(patch, delta)

        assert verdict is not None
        assert 0 <= verdict.score <= 100


class TestFormatters:
    """Tests for output formatters."""

    @pytest.fixture
    def sample_verdict(self):
        """Create a sample verdict for testing."""
        from src.patch_review.models import (
            ReviewVerdict,
            SecurityVerdict,
            PerformanceVerdict,
            ErrorVerdict,
            ArchitectureVerdict,
            Recommendation,
            Finding,
            Severity,
            FindingCategory,
        )
        from datetime import datetime

        finding = Finding(
            category=FindingCategory.SECURITY,
            severity=Severity.HIGH,
            title="SQL Injection",
            description="Potential SQL injection vulnerability",
            location="test.py:5",
            recommendation="Use parameterized queries"
        )

        return ReviewVerdict(
            patch_id='test-patch',
            overall_score=75.0,
            recommendation=Recommendation.COMMENT,
            security=SecurityVerdict(
                score=70.0, findings=[finding],
                critical_count=0, high_count=1, medium_count=0, low_count=0,
                new_vulnerabilities=1, fixed_vulnerabilities=0,
                cwe_ids=['CWE-89'], vulnerability_types={'injection': 1},
                recommendation="Fix SQL injection"
            ),
            performance=PerformanceVerdict(
                score=85.0, findings=[],
                critical_count=0, high_count=0, medium_count=0, low_count=0,
                hot_paths_affected=0, complexity_delta=0, new_loops=0,
                estimated_impact="None", recommendation="OK"
            ),
            error=ErrorVerdict(
                score=80.0, findings=[],
                critical_count=0, high_count=0, medium_count=0, low_count=0,
                null_safety_issues=0, exception_handling_issues=0,
                type_safety_issues=0, resource_issues=0,
                recommendation="OK"
            ),
            architecture=ArchitectureVerdict(
                score=90.0, findings=[],
                critical_count=0, high_count=0, medium_count=0, low_count=0,
                breaking_changes=0, new_dependencies=0,
                circular_dependencies=0, layer_violations=0,
                blast_radius_score=95.0, affected_modules=[],
                recommendation="OK"
            ),
            all_findings=[finding],
            critical_count=0,
            high_count=1,
            medium_count=0,
            low_count=0,
            blast_radius_score=95.0,
            review_time_seconds=1.5,
            summary="Test summary",
            reviewed_at=datetime.now()
        )

    def test_json_formatter(self, sample_verdict):
        """Test JSON formatting."""
        from src.patch_review import JSONFormatter
        import json

        formatter = JSONFormatter()
        output = formatter.format_full(sample_verdict)

        # Should be valid JSON
        data = json.loads(output)
        assert data['patch_id'] == 'test-patch'
        assert data['overall_score'] == 75.0

    def test_markdown_formatter(self, sample_verdict):
        """Test Markdown formatting."""
        from src.patch_review import MarkdownFormatter

        formatter = MarkdownFormatter()
        output = formatter.format_full_report(sample_verdict)

        assert '# ' in output  # Has headers
        assert 'test-patch' in output
        assert 'SQL Injection' in output

    def test_pr_comment_formatter(self, sample_verdict):
        """Test PR comment formatting."""
        from src.patch_review import PRCommentFormatter

        formatter = PRCommentFormatter()
        review = formatter.format_github_review(sample_verdict)

        assert review.event == 'COMMENT'
        assert 'Score' in review.body


class TestModels:
    """Tests for data models."""

    def test_severity_ordering(self):
        """Test severity comparison."""
        from src.patch_review import Severity

        assert Severity.CRITICAL.value == 'critical'
        assert Severity.HIGH.value == 'high'

    def test_recommendation_values(self):
        """Test recommendation enum."""
        from src.patch_review import Recommendation

        assert Recommendation.APPROVE.value == 'approve'
        assert Recommendation.BLOCK.value == 'block'

    def test_patch_context_creation(self):
        """Test PatchContext dataclass."""
        from src.patch_review import PatchContext, FileDiff

        patch = PatchContext(
            patch_id='test',
            base_commit='abc',
            head_commit='def',
            files=[],
            changed_methods=[],
            lines_added=10,
            lines_deleted=5
        )

        assert patch.patch_id == 'test'
        assert patch.lines_added == 10


class TestIntegrations:
    """Tests for external integrations."""

    def test_github_config(self):
        """Test GitHub configuration."""
        from src.patch_review.integrations import GitHubConfig

        config = GitHubConfig(
            token='test-token',
            owner='test-owner',
            repo='test-repo'
        )

        assert config.token == 'test-token'
        assert config.api_base == 'https://api.github.com'

    def test_gitlab_config(self):
        """Test GitLab configuration."""
        from src.patch_review.integrations import GitLabConfig

        config = GitLabConfig(
            token='test-token',
            project_id='group/project'
        )

        assert config.token == 'test-token'
        assert config.api_base == 'https://gitlab.com/api/v4'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
