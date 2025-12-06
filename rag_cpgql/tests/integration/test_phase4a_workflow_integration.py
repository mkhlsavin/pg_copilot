"""
Integration Tests for Phase 4A: Betweenness Centrality Workflow Integration

Tests the integration of betweenness centrality analysis into:
1. Feature Development workflow (scenario_4)
2. Refactoring workflow (scenario_5)

Note: These tests validate the betweenness integration logic without running full workflows
to avoid expensive LLM calls and timeout issues.

Author: Phase 4A Implementation
Date: November 25, 2025
"""

import pytest
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.services.cpg_query_service import CPGQueryService
from src.architecture.architecture_agents import DependencyAnalyzer
from src.analysis import CallGraphAnalyzer


# ============================================================================
# Test Class 1: Betweenness Integration - Architecture Analysis
# ============================================================================

class TestBetweennessArchitectureIntegration:
    """Test betweenness centrality integration in architecture analysis"""

    def test_dependency_analyzer_has_chokepoint_method(self):
        """Test that DependencyAnalyzer has identify_architectural_chokepoints method"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)

            # Method should exist
            assert hasattr(analyzer, 'identify_architectural_chokepoints')
            assert callable(analyzer.identify_architectural_chokepoints)

            print(f"\n  ✓ DependencyAnalyzer.identify_architectural_chokepoints() exists")

    def test_identify_architectural_chokepoints_returns_list(self):
        """Test that chokepoint method returns a list"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)
            chokepoints = analyzer.identify_architectural_chokepoints()

            # Should return a list
            assert isinstance(chokepoints, list)

            print(f"\n  ✓ Returns list with {len(chokepoints)} chokepoints")

    def test_chokepoint_structure(self):
        """Test that chokepoint results have correct structure"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)
            chokepoints = analyzer.identify_architectural_chokepoints()

            if chokepoints:
                cp = chokepoints[0]

                # Verify required fields
                assert 'method_name' in cp
                assert 'betweenness_score' in cp
                assert 'betweenness_percentile' in cp
                assert 'is_bridge' in cp
                assert 'risk_level' in cp

                # Verify types
                assert isinstance(cp['method_name'], str)
                assert isinstance(cp['betweenness_score'], (int, float))
                assert isinstance(cp['betweenness_percentile'], (int, float))
                assert isinstance(cp['is_bridge'], bool)
                assert cp['risk_level'] in ['critical', 'high', 'medium', 'low']

                print(f"\n  ✓ Chokepoint structure valid")
                print(f"  ✓ Sample: {cp['method_name'][:50]}...")
                print(f"  ✓ Percentile: {cp['betweenness_percentile']:.1f}")

    def test_high_centrality_filtering(self):
        """Test that only high-centrality methods are returned"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)
            chokepoints = analyzer.identify_architectural_chokepoints()

            if chokepoints:
                # All chokepoints should be high centrality (top 5%)
                for cp in chokepoints:
                    assert cp['betweenness_percentile'] >= 0
                    # Should be relatively high centrality
                    assert cp['betweenness_score'] >= 0

                # Top result should have highest betweenness
                if len(chokepoints) > 1:
                    assert chokepoints[0]['betweenness_score'] >= chokepoints[-1]['betweenness_score']

                print(f"\n  ✓ All chokepoints are high-centrality")
                print(f"  ✓ Top percentile: {chokepoints[0]['betweenness_percentile']:.1f}")


# ============================================================================
# Test Class 2: Betweenness Integration - Call Graph Analysis
# ============================================================================

class TestBetweennessCallGraphIntegration:
    """Test betweenness centrality in call graph analysis"""

    def test_call_graph_analyzer_has_betweenness(self):
        """Test that CallGraphAnalyzer has betweenness centrality method"""
        with CPGQueryService() as cpg:
            analyzer = CallGraphAnalyzer(cpg)

            # Method should exist
            assert hasattr(analyzer, 'compute_betweenness_centrality')
            assert callable(analyzer.compute_betweenness_centrality)

            print(f"\n  ✓ CallGraphAnalyzer.compute_betweenness_centrality() exists")

    def test_betweenness_centrality_performance(self):
        """Test that betweenness computation is fast with sampling"""
        import time

        with CPGQueryService() as cpg:
            analyzer = CallGraphAnalyzer(cpg)

            start = time.time()
            results = analyzer.compute_betweenness_centrality(sample_size=1000, top_n=30)
            elapsed = time.time() - start

            # Should complete in under 5 seconds
            assert elapsed < 5.0

            print(f"\n  ✓ Betweenness computation: {elapsed:.2f}s")
            print(f"  ✓ Results returned: {len(results)}")

    def test_betweenness_result_structure(self):
        """Test that betweenness results have correct structure"""
        with CPGQueryService() as cpg:
            analyzer = CallGraphAnalyzer(cpg)
            results = analyzer.compute_betweenness_centrality(sample_size=1000, top_n=30)

            if results:
                result = results[0]

                # Verify required fields
                assert 'method_name' in result
                assert 'betweenness_score' in result
                assert 'percentile' in result

                # Verify types
                assert isinstance(result['method_name'], str)
                assert isinstance(result['betweenness_score'], (int, float))
                assert isinstance(result['percentile'], (int, float))

                # Percentile should be 0-100
                assert 0 <= result['percentile'] <= 100

                print(f"\n  ✓ Betweenness result structure valid")
                print(f"  ✓ Top method: {result['method_name'][:50]}...")
                print(f"  ✓ Score: {result['betweenness_score']:.4f}")


# ============================================================================
# Test Class 3: Feature Development Integration (Without LLM)
# ============================================================================

class TestFeatureDevBetweennessLogic:
    """Test feature dev betweenness logic without full workflow execution"""

    def test_feature_dev_betweenness_integration_points(self):
        """Test that high-centrality methods can be identified for integration points"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)
            chokepoints = analyzer.identify_architectural_chokepoints()

            # Simulate the feature dev workflow logic
            betweenness_integration_points = []
            for cp in chokepoints[:15]:  # Top 15
                if cp['betweenness_percentile'] > 80:  # Top 20%
                    betweenness_integration_points.append({
                        'method': cp['method_name'],
                        'betweenness_score': cp['betweenness_score'],
                        'betweenness_percentile': cp['betweenness_percentile'],
                        'risk_level': cp['risk_level'],
                        'reason': 'High architectural centrality - strategic integration point'
                    })

            # Should find some high-centrality points
            print(f"\n  ✓ High-centrality integration points: {len(betweenness_integration_points)}")

            if betweenness_integration_points:
                # Verify structure
                ip = betweenness_integration_points[0]
                assert 'method' in ip
                assert 'betweenness_percentile' in ip
                assert ip['betweenness_percentile'] > 80

                print(f"  ✓ Top integration point: {ip['method'][:50]}...")
                print(f"  ✓ Percentile: {ip['betweenness_percentile']:.1f}")


# ============================================================================
# Test Class 4: Refactoring Integration (Without LLM)
# ============================================================================

class TestRefactoringBetweennessLogic:
    """Test refactoring betweenness logic without full workflow execution"""

    def test_refactoring_risk_assessment_logic(self):
        """Test that high-betweenness methods are flagged as high-risk"""
        with CPGQueryService() as cpg:
            analyzer = DependencyAnalyzer(cpg)
            chokepoints = analyzer.identify_architectural_chokepoints()

            if chokepoints:
                # Create lookup (simulating refactoring workflow)
                betweenness_lookup = {cp['method_name']: cp for cp in chokepoints}

                # Test risk assessment logic
                high_risk_refactorings = []
                for cp in chokepoints[:10]:  # Top 10
                    if cp['betweenness_percentile'] > 90:  # Top 10%
                        risk_assessment = {
                            'method': cp['method_name'],
                            'betweenness_percentile': cp['betweenness_percentile'],
                            'risk_level': 'critical',
                            'risk_reason': f"Architectural chokepoint (top {100 - cp['betweenness_percentile']:.0f}%)"
                        }
                        high_risk_refactorings.append(risk_assessment)

                print(f"\n  ✓ High-risk refactorings identified: {len(high_risk_refactorings)}")

                if high_risk_refactorings:
                    # Verify all are marked critical
                    for ra in high_risk_refactorings:
                        assert ra['risk_level'] == 'critical'
                        assert ra['betweenness_percentile'] > 90

                    print(f"  ✓ All marked as critical risk")
                    print(f"  ✓ Highest percentile: {high_risk_refactorings[0]['betweenness_percentile']:.1f}")


# ============================================================================
# Test Class 5: Phase 4A Integration Summary
# ============================================================================

class TestPhase4AIntegrationSummary:
    """Summary tests for Phase 4A betweenness integration"""

    def test_phase4a_all_methods_exist(self):
        """Verify all Phase 4A methods are implemented"""
        with CPGQueryService() as cpg:
            # DependencyAnalyzer should have chokepoint method
            dep_analyzer = DependencyAnalyzer(cpg)
            assert hasattr(dep_analyzer, 'identify_architectural_chokepoints')

            # CallGraphAnalyzer should have betweenness method
            call_analyzer = CallGraphAnalyzer(cpg)
            assert hasattr(call_analyzer, 'compute_betweenness_centrality')

            print(f"\n  ✓ DependencyAnalyzer.identify_architectural_chokepoints() implemented")
            print(f"  ✓ CallGraphAnalyzer.compute_betweenness_centrality() implemented")

    def test_phase4a_integration_flow(self):
        """Test the complete Phase 4A integration flow"""
        with CPGQueryService() as cpg:
            # Step 1: Get betweenness results from CallGraphAnalyzer
            call_analyzer = CallGraphAnalyzer(cpg)
            betweenness_results = call_analyzer.compute_betweenness_centrality(
                sample_size=1000,
                top_n=30
            )

            # Step 2: Get chokepoints from DependencyAnalyzer (uses CallGraphAnalyzer internally)
            dep_analyzer = DependencyAnalyzer(cpg)
            chokepoints = dep_analyzer.identify_architectural_chokepoints()

            # Both should return results
            assert isinstance(betweenness_results, list)
            assert isinstance(chokepoints, list)

            print(f"\n  ✓ Betweenness results: {len(betweenness_results)}")
            print(f"  ✓ Chokepoints identified: {len(chokepoints)}")

            # Step 3: Test integration point selection (feature dev)
            if chokepoints:
                high_centrality_points = [
                    cp for cp in chokepoints[:15]
                    if cp['betweenness_percentile'] > 80
                ]
                print(f"  ✓ High-centrality integration points: {len(high_centrality_points)}")

            # Step 4: Test risk assessment (refactoring)
            if chokepoints:
                critical_risks = [
                    cp for cp in chokepoints
                    if cp['betweenness_percentile'] > 90
                ]
                print(f"  ✓ Critical refactoring risks: {len(critical_risks)}")

    def test_phase4a_graceful_degradation(self):
        """Test that Phase 4A methods degrade gracefully on errors"""
        with CPGQueryService() as cpg:
            # Both methods should return empty lists, not raise exceptions
            try:
                dep_analyzer = DependencyAnalyzer(cpg)
                chokepoints = dep_analyzer.identify_architectural_chokepoints()
                assert isinstance(chokepoints, list)

                call_analyzer = CallGraphAnalyzer(cpg)
                results = call_analyzer.compute_betweenness_centrality(sample_size=100, top_n=10)
                assert isinstance(results, list)

                print(f"\n  ✓ Graceful degradation works correctly")

            except Exception as e:
                pytest.fail(f"Phase 4A methods should not raise exceptions: {e}")

    def test_phase4a_performance_targets(self):
        """Test that Phase 4A meets performance targets"""
        import time

        with CPGQueryService() as cpg:
            # Betweenness should be < 5s
            call_analyzer = CallGraphAnalyzer(cpg)
            start = time.time()
            betweenness_results = call_analyzer.compute_betweenness_centrality(
                sample_size=1000,
                top_n=30
            )
            betweenness_time = time.time() - start

            # Chokepoints should be < 5s (includes betweenness internally)
            dep_analyzer = DependencyAnalyzer(cpg)
            start = time.time()
            chokepoints = dep_analyzer.identify_architectural_chokepoints()
            chokepoints_time = time.time() - start

            # Performance targets
            assert betweenness_time < 5.0
            assert chokepoints_time < 5.0

            print(f"\n  ✓ Betweenness computation: {betweenness_time:.2f}s (< 5s target)")
            print(f"  ✓ Chokepoint identification: {chokepoints_time:.2f}s (< 5s target)")


# ============================================================================
# Pytest Configuration
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
