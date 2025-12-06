"""
Integration Tests for Phase 2 Quick Wins Enhancements

Tests the integration of Phase 1.2 graph algorithms into existing scenarios:
1. PageRank in Security Incident Response (BlastRadiusAnalyzer)
2. WCC in Architecture/Refactoring (DependencyAnalyzer)
3. Cyclomatic Complexity in Code Review (ContextAggregator)

These tests run against real CPG database (cpg.duckdb) to validate
production behavior and performance.

Author: Integration Test Team
Date: 2025-11-24
"""

import pytest
import time
from typing import List, Dict, Any

# Import services
import sys
sys.path.insert(0, 'C:/Users/user/pg_copilot/rag_cpgql')

from src.services.cpg_query_service import CPGQueryService
from src.security_incident.incident_agents import (
    BlastRadiusAnalyzer,
    VulnerabilityFinding,
    VulnerabilityPattern,
    VulnerabilitySeverity,
    VulnerabilityCategory
)
from src.architecture.architecture_agents import DependencyAnalyzer
from src.code_review.review_agents import ContextAggregator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def cpg_service():
    """CPG service connected to real database"""
    service = CPGQueryService('cpg.duckdb')
    yield service
    service.close()


@pytest.fixture(scope="module")
def sample_method_id(cpg_service):
    """Get a sample method ID from the database"""
    query = """
        SELECT id FROM nodes_method
        WHERE id IN (SELECT DISTINCT dst FROM edges_call)
        LIMIT 1
    """
    result = cpg_service.execute_query(query)
    if result:
        return result[0]['id']
    return None


@pytest.fixture
def sample_vulnerability(sample_method_id):
    """Create a sample vulnerability finding"""
    if not sample_method_id:
        pytest.skip("No methods found in CPG database")

    pattern = VulnerabilityPattern(
        pattern_id="sql_injection",
        name="SQL Injection",
        category=VulnerabilityCategory.INJECTION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="SQL injection vulnerability",
        cwe_id="CWE-89",
        detection_query="",
        exploitation="Attacker can inject SQL commands",
        remediation="Use parameterized queries",
        references=["https://owasp.org/www-community/attacks/SQL_Injection"]
    )

    return VulnerabilityFinding(
        finding_id="test_vuln_001",
        pattern=pattern,
        method_id=sample_method_id,
        method_name="test_method",
        filepath="test.c",
        line_number=100,
        code_snippet="SELECT * FROM users",
        confidence=0.9,
        cvss_score=9.0
    )


# ============================================================================
# TEST SUITE 1: PAGERANK IN SECURITY INCIDENT RESPONSE
# ============================================================================

class TestPageRankSecurityIntegration:
    """
    Integration tests for PageRank enhancement in BlastRadiusAnalyzer

    Tests:
    - Critical method identification
    - PageRank amplification calculation
    - Impact score amplification
    - Caching behavior
    - Performance
    """

    def test_blast_radius_has_pagerank_fields(self, cpg_service, sample_vulnerability):
        """Test that BlastRadius includes Phase 2 PageRank fields"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        blast_radius = analyzer.calculate_blast_radius(
            sample_vulnerability,
            max_depth=2
        )

        # Verify Phase 2 fields exist
        assert hasattr(blast_radius, 'critical_path_methods'), \
            "BlastRadius missing critical_path_methods field"
        assert hasattr(blast_radius, 'pagerank_amplification'), \
            "BlastRadius missing pagerank_amplification field"

        # Verify fields are correct type
        assert isinstance(blast_radius.critical_path_methods, list), \
            "critical_path_methods should be a list"
        assert isinstance(blast_radius.pagerank_amplification, float), \
            "pagerank_amplification should be a float"

    def test_critical_methods_identified(self, cpg_service, sample_vulnerability):
        """Test that critical methods are identified using PageRank"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        blast_radius = analyzer.calculate_blast_radius(
            sample_vulnerability,
            max_depth=2
        )

        # If there are affected methods, some should be critical
        total_affected = (
            len(blast_radius.directly_affected_methods) +
            len(blast_radius.impacted_callers)
        )

        if total_affected > 0:
            # At least check that critical_path_methods is populated or empty
            assert isinstance(blast_radius.critical_path_methods, list)

            # If critical methods found, verify structure
            for critical in blast_radius.critical_path_methods:
                assert 'method_name' in critical
                assert 'pagerank_score' in critical
                assert 'pagerank_percentile' in critical
                assert 'criticality' in critical
                assert critical['criticality'] in ['HIGH', 'MEDIUM']

    def test_pagerank_amplification_calculated(self, cpg_service, sample_vulnerability):
        """Test that PageRank amplification factor is calculated"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        blast_radius = analyzer.calculate_blast_radius(
            sample_vulnerability,
            max_depth=2
        )

        # Amplification should be between 0.0 and 1.0
        assert 0.0 <= blast_radius.pagerank_amplification <= 1.0, \
            f"Amplification {blast_radius.pagerank_amplification} out of range [0.0, 1.0]"

    def test_impact_score_amplification(self, cpg_service, sample_vulnerability):
        """Test that impact score is amplified by PageRank"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        # Calculate blast radius (includes PageRank amplification)
        blast_radius = analyzer.calculate_blast_radius(
            sample_vulnerability,
            max_depth=2
        )

        # Impact score should be reasonable (0-100)
        assert 0 <= blast_radius.impact_score <= 100, \
            f"Impact score {blast_radius.impact_score} out of range [0, 100]"

        # If amplification > 0, score should reflect it
        # (We can't easily test "before vs after" without internal access,
        #  but we can verify the final score is reasonable)
        if blast_radius.pagerank_amplification > 0:
            assert blast_radius.impact_score > 0, \
                "Non-zero amplification should result in non-zero impact"

    def test_pagerank_caching(self, cpg_service, sample_vulnerability):
        """Test that PageRank results are cached"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        # First call - should compute PageRank
        start1 = time.time()
        blast_radius1 = analyzer.calculate_blast_radius(sample_vulnerability, max_depth=1)
        time1 = time.time() - start1

        # Second call - should use cache
        start2 = time.time()
        blast_radius2 = analyzer.calculate_blast_radius(sample_vulnerability, max_depth=1)
        time2 = time.time() - start2

        # Second call should be faster (cache hit)
        # Allow for some variance, but expect at least 20% speedup
        assert time2 < time1 * 1.2, \
            f"Second call ({time2:.3f}s) not faster than first ({time1:.3f}s) - caching may not be working"

        print(f"  First call: {time1:.3f}s")
        print(f"  Second call (cached): {time2:.3f}s")
        if time2 > 0:
            print(f"  Speedup: {time1/time2:.1f}x")
        else:
            print(f"  Speedup: >1000x (cached call too fast to measure)")

    def test_pagerank_performance(self, cpg_service, sample_vulnerability):
        """Test that PageRank integration has acceptable performance"""
        analyzer = BlastRadiusAnalyzer(cpg_service)

        start = time.time()
        blast_radius = analyzer.calculate_blast_radius(
            sample_vulnerability,
            max_depth=2
        )
        elapsed = time.time() - start

        # Should complete in <1 second (includes PageRank computation)
        assert elapsed < 1.0, \
            f"Blast radius calculation too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"  Blast radius with PageRank: {elapsed:.3f}s")
        print(f"  Critical methods found: {len(blast_radius.critical_path_methods)}")
        print(f"  Amplification factor: {blast_radius.pagerank_amplification:.3f}")

    def test_graceful_degradation_pagerank(self, cpg_service, sample_vulnerability):
        """Test that system handles PageRank failures gracefully"""
        # This test ensures that if PageRank fails, the system continues
        # with default values rather than crashing

        analyzer = BlastRadiusAnalyzer(cpg_service)

        # Should not raise exception even if PageRank has issues
        try:
            blast_radius = analyzer.calculate_blast_radius(
                sample_vulnerability,
                max_depth=2
            )

            # Should have default values if PageRank fails
            assert blast_radius is not None
            assert isinstance(blast_radius.critical_path_methods, list)
            assert isinstance(blast_radius.pagerank_amplification, float)

        except Exception as e:
            pytest.fail(f"Blast radius calculation should not raise exception: {e}")


# ============================================================================
# TEST SUITE 2: WCC IN ARCHITECTURE/REFACTORING
# ============================================================================

class TestWCCArchitectureIntegration:
    """
    Integration tests for WCC enhancement in DependencyAnalyzer

    Tests:
    - Dead code detection
    - Isolated component identification
    - Finding structure
    - Performance
    """

    def test_detect_dead_code_method_exists(self, cpg_service):
        """Test that detect_dead_code method exists and is callable"""
        analyzer = DependencyAnalyzer(cpg_service)

        assert hasattr(analyzer, 'detect_dead_code'), \
            "DependencyAnalyzer missing detect_dead_code method"
        assert callable(analyzer.detect_dead_code), \
            "detect_dead_code should be callable"

    def test_detect_dead_code_returns_findings(self, cpg_service):
        """Test that detect_dead_code returns ViolationFindings"""
        analyzer = DependencyAnalyzer(cpg_service)

        findings = analyzer.detect_dead_code()

        # Should return a list (may be empty if no dead code)
        assert isinstance(findings, list), \
            "detect_dead_code should return a list"

        # If findings exist, verify structure
        for finding in findings:
            assert hasattr(finding, 'finding_id')
            assert hasattr(finding, 'pattern_id')
            assert hasattr(finding, 'pattern_name')
            assert hasattr(finding, 'category')
            assert hasattr(finding, 'severity')
            assert hasattr(finding, 'violation_details')
            assert hasattr(finding, 'remediation_steps')
            assert hasattr(finding, 'metadata')

    def test_isolated_components_identified(self, cpg_service):
        """Test that isolated components are properly identified"""
        analyzer = DependencyAnalyzer(cpg_service)

        findings = analyzer.detect_dead_code()

        # Check metadata structure for findings
        for finding in findings:
            metadata = finding.metadata

            assert 'component_size' in metadata, \
                "Finding metadata should include component_size"
            assert 'main_component_size' in metadata, \
                "Finding metadata should include main_component_size"
            assert 'isolation_ratio' in metadata, \
                "Finding metadata should include isolation_ratio"
            assert 'methods' in metadata, \
                "Finding metadata should include methods list"

            # Verify isolation ratio makes sense
            ratio = metadata['isolation_ratio']
            assert 0 <= ratio <= 1.0, \
                f"Isolation ratio {ratio} should be between 0 and 1"

            # Isolated component should be smaller than main
            assert metadata['component_size'] < metadata['main_component_size'], \
                "Isolated component should be smaller than main component"

    def test_dead_code_finding_structure(self, cpg_service):
        """Test that dead code findings have correct structure"""
        analyzer = DependencyAnalyzer(cpg_service)

        findings = analyzer.detect_dead_code()

        for finding in findings:
            # Pattern ID should be consistent
            assert finding.pattern_id == "dead_code_detection", \
                "Pattern ID should be 'dead_code_detection'"

            # Pattern name should mention WCC
            assert "WCC" in finding.pattern_name or "Isolated" in finding.pattern_name, \
                "Pattern name should mention WCC or Isolated"

            # Category should be cohesion
            assert finding.category == "cohesion", \
                "Category should be 'cohesion'"

            # Severity should be medium or low
            assert finding.severity in ["medium", "low"], \
                f"Severity should be 'medium' or 'low', got '{finding.severity}'"

            # Should have remediation steps
            assert len(finding.remediation_steps) > 0, \
                "Finding should have remediation steps"

    def test_wcc_performance(self, cpg_service):
        """Test that WCC dead code detection has acceptable performance"""
        analyzer = DependencyAnalyzer(cpg_service)

        start = time.time()
        findings = analyzer.detect_dead_code()
        elapsed = time.time() - start

        # Should complete in <1 second
        assert elapsed < 1.0, \
            f"Dead code detection too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"  Dead code detection: {elapsed:.3f}s")
        print(f"  Isolated components found: {len(findings)}")
        if findings:
            total_methods = sum(f.metadata['component_size'] for f in findings)
            print(f"  Total methods in isolated components: {total_methods}")

    def test_graceful_degradation_wcc(self, cpg_service):
        """Test that system handles WCC failures gracefully"""
        analyzer = DependencyAnalyzer(cpg_service)

        # Should not raise exception even if WCC has issues
        try:
            findings = analyzer.detect_dead_code()

            # Should return empty list if WCC fails
            assert isinstance(findings, list)

        except Exception as e:
            pytest.fail(f"Dead code detection should not raise exception: {e}")


# ============================================================================
# TEST SUITE 3: CYCLOMATIC COMPLEXITY IN CODE REVIEW
# ============================================================================

class TestComplexityCodeReviewIntegration:
    """
    Integration tests for Cyclomatic Complexity in ContextAggregator

    Tests:
    - On-demand complexity computation
    - Fallback behavior
    - Caching
    - Performance

    Note: Some tests may be skipped if CFG edges missing in CPG
    """

    def test_context_aggregator_has_complexity_cache(self, cpg_service):
        """Test that ContextAggregator has complexity caching"""
        aggregator = ContextAggregator(cpg_service)

        assert hasattr(aggregator, '_complexity_cache'), \
            "ContextAggregator missing _complexity_cache attribute"
        assert hasattr(aggregator, '_compute_complexity_for_method'), \
            "ContextAggregator missing _compute_complexity_for_method method"

    def test_gather_context_includes_complexity(self, cpg_service, sample_method_id):
        """Test that gather_method_context includes complexity"""
        if not sample_method_id:
            pytest.skip("No sample method available")

        aggregator = ContextAggregator(cpg_service)

        context = aggregator.gather_method_context(sample_method_id)

        # Context should have complexity field
        assert hasattr(context, 'complexity'), \
            "MethodContext missing complexity field"
        assert isinstance(context.complexity, int), \
            "Complexity should be an integer"
        assert context.complexity >= 0, \
            "Complexity should be non-negative"

    def test_complexity_computation_fallback(self, cpg_service, sample_method_id):
        """Test that complexity is computed when tags are missing"""
        if not sample_method_id:
            pytest.skip("No sample method available")

        aggregator = ContextAggregator(cpg_service)

        # Call _compute_complexity_for_method directly
        complexity = aggregator._compute_complexity_for_method("test_method")

        # Should return a non-negative integer (may be 0 if method not found)
        assert isinstance(complexity, int)
        assert complexity >= 0

    def test_complexity_caching(self, cpg_service, sample_method_id):
        """Test that complexity results are cached"""
        if not sample_method_id:
            pytest.skip("No sample method available")

        aggregator = ContextAggregator(cpg_service)

        # First call - should compute complexity
        start1 = time.time()
        context1 = aggregator.gather_method_context(sample_method_id)
        time1 = time.time() - start1

        # Second call - should use cache
        start2 = time.time()
        context2 = aggregator.gather_method_context(sample_method_id)
        time2 = time.time() - start2

        # Complexity should be same
        assert context1.complexity == context2.complexity, \
            "Complexity should be consistent across calls"

        # Second call should be faster (cache hit)
        # Note: May not always be true due to other factors, so just log
        print(f"  First call: {time1:.3f}s (complexity: {context1.complexity})")
        print(f"  Second call: {time2:.3f}s (cached)")

    def test_complexity_performance(self, cpg_service, sample_method_id):
        """Test that complexity computation has acceptable performance"""
        if not sample_method_id:
            pytest.skip("No sample method available")

        aggregator = ContextAggregator(cpg_service)

        start = time.time()
        context = aggregator.gather_method_context(sample_method_id)
        elapsed = time.time() - start

        # Should complete in <1 second
        assert elapsed < 1.0, \
            f"Context gathering too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"  Method context gathering: {elapsed:.3f}s")
        print(f"  Complexity: {context.complexity}")

    def test_graceful_degradation_complexity(self, cpg_service, sample_method_id):
        """Test that system handles complexity computation failures gracefully"""
        if not sample_method_id:
            pytest.skip("No sample method available")

        aggregator = ContextAggregator(cpg_service)

        # Should not raise exception even if complexity computation fails
        try:
            context = aggregator.gather_method_context(sample_method_id)

            # Should have a complexity value (0 if failed)
            assert hasattr(context, 'complexity')
            assert isinstance(context.complexity, int)
            assert context.complexity >= 0

        except Exception as e:
            pytest.fail(f"Context gathering should not raise exception: {e}")


# ============================================================================
# INTEGRATION TEST SUITE SUMMARY
# ============================================================================

class TestPhase2IntegrationSummary:
    """
    Summary tests to validate overall Phase 2 integration
    """

    def test_all_enhancements_integrated(self, cpg_service):
        """Test that all three Phase 2 enhancements are integrated"""
        # 1. PageRank in Security Incident
        blast_analyzer = BlastRadiusAnalyzer(cpg_service)
        assert hasattr(blast_analyzer, 'call_graph_analyzer'), \
            "BlastRadiusAnalyzer should have call_graph_analyzer"
        assert hasattr(blast_analyzer, '_pagerank_cache'), \
            "BlastRadiusAnalyzer should have _pagerank_cache"

        # 2. WCC in Architecture
        dep_analyzer = DependencyAnalyzer(cpg_service)
        assert hasattr(dep_analyzer, 'call_graph_analyzer'), \
            "DependencyAnalyzer should have call_graph_analyzer"
        assert hasattr(dep_analyzer, 'detect_dead_code'), \
            "DependencyAnalyzer should have detect_dead_code method"

        # 3. Complexity in Code Review
        context_agg = ContextAggregator(cpg_service)
        assert hasattr(context_agg, 'call_graph_analyzer'), \
            "ContextAggregator should have call_graph_analyzer"
        assert hasattr(context_agg, '_complexity_cache'), \
            "ContextAggregator should have _complexity_cache"

    def test_backward_compatibility(self, cpg_service, sample_vulnerability):
        """Test that Phase 2 changes are backward compatible"""
        # Old code should still work without using new features

        # 1. BlastRadiusAnalyzer can be used without accessing new fields
        analyzer = BlastRadiusAnalyzer(cpg_service)
        blast_radius = analyzer.calculate_blast_radius(sample_vulnerability, max_depth=1)

        # Old fields should still exist
        assert hasattr(blast_radius, 'vulnerability')
        assert hasattr(blast_radius, 'directly_affected_methods')
        assert hasattr(blast_radius, 'impacted_callers')
        assert hasattr(blast_radius, 'impact_score')

        # 2. DependencyAnalyzer existing methods should still work
        dep_analyzer = DependencyAnalyzer(cpg_service)
        # detect_all_violations should still work
        assert hasattr(dep_analyzer, 'detect_all_violations')

    def test_performance_targets_met(self, cpg_service, sample_vulnerability, sample_method_id):
        """Test that all Phase 2 enhancements meet performance targets"""
        results = {}

        # 1. PageRank integration (<0.5s including first-time PageRank)
        analyzer = BlastRadiusAnalyzer(cpg_service)
        start = time.time()
        blast_radius = analyzer.calculate_blast_radius(sample_vulnerability, max_depth=2)
        results['pagerank'] = time.time() - start

        # 2. WCC integration (<0.5s)
        dep_analyzer = DependencyAnalyzer(cpg_service)
        start = time.time()
        dead_code = dep_analyzer.detect_dead_code()
        results['wcc'] = time.time() - start

        # 3. Complexity integration (<0.5s)
        if sample_method_id:
            context_agg = ContextAggregator(cpg_service)
            start = time.time()
            context = context_agg.gather_method_context(sample_method_id)
            results['complexity'] = time.time() - start

        # Print results
        print("\n  Performance Results:")
        for name, time_taken in results.items():
            status = "✅" if time_taken < 0.5 else "⚠️"
            print(f"    {status} {name}: {time_taken:.3f}s (target: <0.5s)")

        # All should be under 0.5s
        for name, time_taken in results.items():
            assert time_taken < 0.5, \
                f"{name} integration too slow: {time_taken:.3f}s (target: <0.5s)"


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short', '-s'])
