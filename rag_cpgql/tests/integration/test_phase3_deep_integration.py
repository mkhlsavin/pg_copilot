"""
Integration Tests for Phase 3 Deep Integration (SCC and Betweenness Centrality)

Tests the integration of Phase 1.2 graph algorithms (SCC and Betweenness) into:
- Performance Analysis (SCC + Betweenness)
- Refactoring Assistance (SCC)
- Architecture Violations (SCC)
- Architecture Analysis (Betweenness)

Date: November 24, 2025
"""

import pytest
import time
from pathlib import Path

from src.services.cpg_query_service import CPGQueryService
from src.performance.performance_agents import PerformanceProfiler
from src.architecture.architecture_agents import DependencyAnalyzer, LayerValidator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def cpg_service():
    """Provide CPGQueryService connected to real CPG database"""
    cpg = CPGQueryService()
    cpg.__enter__()
    yield cpg
    cpg.__exit__(None, None, None)


@pytest.fixture(scope="module")
def performance_profiler(cpg_service):
    """Provide PerformanceProfiler instance"""
    return PerformanceProfiler(cpg_service)


@pytest.fixture(scope="module")
def dependency_analyzer(cpg_service):
    """Provide DependencyAnalyzer instance"""
    return DependencyAnalyzer(cpg_service)


@pytest.fixture(scope="module")
def layer_validator(cpg_service):
    """Provide LayerValidator instance"""
    return LayerValidator(cpg_service)


# ============================================================================
# TEST CLASS 1: SCC - PERFORMANCE ANALYSIS
# ============================================================================

class TestSCCPerformanceAnalysis:
    """Test SCC integration in Performance Analysis (detect_cycles_scc)"""

    def test_detect_cycles_scc_method_exists(self, performance_profiler):
        """Test that detect_cycles_scc method exists"""
        assert hasattr(performance_profiler, 'detect_cycles_scc')
        assert callable(performance_profiler.detect_cycles_scc)

    def test_detect_cycles_scc_returns_findings(self, performance_profiler):
        """Test that detect_cycles_scc returns list of BottleneckFindings"""
        findings = performance_profiler.detect_cycles_scc()

        assert isinstance(findings, list)
        # Note: May be empty if no cycles in the codebase

        if findings:
            finding = findings[0]
            assert hasattr(finding, 'finding_id')
            assert hasattr(finding, 'pattern_id')
            assert hasattr(finding, 'severity')
            assert finding.pattern_id == 'mutual_recursion_scc'

    def test_cycles_have_metadata(self, performance_profiler):
        """Test that cycle findings include SCC metadata"""
        findings = performance_profiler.detect_cycles_scc()

        if findings:
            finding = findings[0]
            assert 'detection_algorithm' in finding.metadata
            assert finding.metadata['detection_algorithm'] == 'tarjan_scc'
            assert 'cycle_size' in finding.metadata
            assert 'all_methods' in finding.metadata
            assert isinstance(finding.metadata['cycle_size'], int)
            assert finding.metadata['cycle_size'] > 1  # Cycles must have >1 method

    def test_cycle_severity_classification(self, performance_profiler):
        """Test that cycles are classified by severity"""
        findings = performance_profiler.detect_cycles_scc()

        if findings:
            for finding in findings:
                assert finding.severity in ['critical', 'high', 'medium', 'low']
                cycle_size = finding.metadata.get('cycle_size', 0)

                # Verify severity matches cycle size
                if cycle_size > 10:
                    assert finding.severity == 'critical'
                elif cycle_size > 5:
                    assert finding.severity == 'high'
                else:
                    assert finding.severity == 'medium'

    def test_scc_performance(self, performance_profiler):
        """Test that SCC cycle detection has acceptable performance"""
        start = time.time()
        findings = performance_profiler.detect_cycles_scc()
        elapsed = time.time() - start

        # Should complete in <1.0 second (target: <0.2s)
        assert elapsed < 1.0, \
            f"SCC cycle detection too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"\n  SCC cycle detection: {elapsed:.3f}s")
        print(f"  Cycles found: {len(findings)}")

    def test_graceful_degradation_scc_cycles(self, performance_profiler):
        """Test graceful degradation when SCC fails"""
        # This should not raise exceptions even if graph is malformed
        try:
            findings = performance_profiler.detect_cycles_scc()
            assert isinstance(findings, list)
        except Exception as e:
            pytest.fail(f"SCC should not raise exceptions: {e}")


# ============================================================================
# TEST CLASS 2: SCC - REFACTORING ASSISTANCE
# ============================================================================

class TestSCCRefactoringAssistance:
    """Test SCC integration in Refactoring Assistance (detect_circular_dependencies)"""

    def test_detect_circular_dependencies_method_exists(self, dependency_analyzer):
        """Test that detect_circular_dependencies method exists"""
        assert hasattr(dependency_analyzer, 'detect_circular_dependencies')
        assert callable(dependency_analyzer.detect_circular_dependencies)

    def test_detect_circular_dependencies_returns_findings(self, dependency_analyzer):
        """Test that detect_circular_dependencies returns ViolationFindings"""
        findings = dependency_analyzer.detect_circular_dependencies()

        assert isinstance(findings, list)
        # May be empty if no circular dependencies

        if findings:
            finding = findings[0]
            assert hasattr(finding, 'finding_id')
            assert hasattr(finding, 'pattern_id')
            assert finding.pattern_id == 'circular_module_dependency'
            assert finding.category == 'coupling'

    def test_circular_deps_span_modules(self, dependency_analyzer):
        """Test that circular dependency findings span multiple modules"""
        findings = dependency_analyzer.detect_circular_dependencies()

        if findings:
            finding = findings[0]
            assert 'modules_involved' in finding.metadata
            modules = finding.metadata['modules_involved']
            assert len(modules) > 1, "Circular dependency should span multiple modules"

    def test_circular_deps_metadata(self, dependency_analyzer):
        """Test that circular dependency findings include SCC metadata"""
        findings = dependency_analyzer.detect_circular_dependencies()

        if findings:
            finding = findings[0]
            assert 'detection_algorithm' in finding.metadata
            assert finding.metadata['detection_algorithm'] == 'tarjan_scc'
            assert 'scc_size' in finding.metadata
            assert 'modules_involved' in finding.metadata
            assert 'sample_methods' in finding.metadata

    def test_circular_deps_severity(self, dependency_analyzer):
        """Test that circular dependencies have appropriate severity"""
        findings = dependency_analyzer.detect_circular_dependencies()

        if findings:
            for finding in findings:
                assert finding.severity in ['critical', 'high', 'medium']

                modules = finding.metadata.get('modules_involved', [])
                scc_size = finding.metadata.get('scc_size', 0)

                # Verify severity matches scope
                if len(modules) > 5 or scc_size > 20:
                    assert finding.severity == 'critical'
                elif len(modules) > 3 or scc_size > 10:
                    assert finding.severity == 'high'

    def test_circular_deps_performance(self, dependency_analyzer):
        """Test that circular dependency detection has acceptable performance"""
        start = time.time()
        findings = dependency_analyzer.detect_circular_dependencies()
        elapsed = time.time() - start

        assert elapsed < 1.0, \
            f"Circular dependency detection too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"\n  Circular dependency detection: {elapsed:.3f}s")
        print(f"  Circular dependencies found: {len(findings)}")

    def test_graceful_degradation_circular_deps(self, dependency_analyzer):
        """Test graceful degradation when circular dependency detection fails"""
        try:
            findings = dependency_analyzer.detect_circular_dependencies()
            assert isinstance(findings, list)
        except Exception as e:
            pytest.fail(f"Circular dependency detection should not raise exceptions: {e}")


# ============================================================================
# TEST CLASS 3: SCC - ARCHITECTURE VIOLATIONS
# ============================================================================

class TestSCCArchitectureViolations:
    """Test SCC integration in Architecture Violations (check_layering_violations_scc)"""

    def test_layering_violations_scc_method_exists(self, layer_validator):
        """Test that check_layering_violations_scc method exists"""
        assert hasattr(layer_validator, 'check_layering_violations_scc')
        assert callable(layer_validator.check_layering_violations_scc)

    def test_layering_violations_scc_returns_findings(self, layer_validator):
        """Test that check_layering_violations_scc returns ViolationFindings"""
        findings = layer_validator.check_layering_violations_scc()

        assert isinstance(findings, list)
        # May be empty if architecture is clean

        if findings:
            finding = findings[0]
            assert hasattr(finding, 'finding_id')
            assert hasattr(finding, 'pattern_id')
            assert finding.pattern_id == 'layering_violation_scc'
            assert finding.category == 'architecture'

    def test_layering_violations_span_layers(self, layer_validator):
        """Test that layering violations span multiple layers"""
        findings = layer_validator.check_layering_violations_scc()

        if findings:
            finding = findings[0]
            assert 'layers_involved' in finding.metadata
            layers = finding.metadata['layers_involved']
            assert len(layers) > 1, "Layering violation should span multiple layers"

    def test_layering_violations_always_critical(self, layer_validator):
        """Test that layering violations are always critical severity"""
        findings = layer_validator.check_layering_violations_scc()

        if findings:
            for finding in findings:
                assert finding.severity == 'critical', \
                    "Layer violations should always be critical"

    def test_layering_violations_metadata(self, layer_validator):
        """Test that layering violation findings include SCC metadata"""
        findings = layer_validator.check_layering_violations_scc()

        if findings:
            finding = findings[0]
            assert 'detection_algorithm' in finding.metadata
            assert finding.metadata['detection_algorithm'] == 'tarjan_scc'
            assert 'scc_size' in finding.metadata
            assert 'layers_involved' in finding.metadata
            assert 'sample_methods' in finding.metadata

    def test_layering_violations_performance(self, layer_validator):
        """Test that layering violation detection has acceptable performance"""
        start = time.time()
        findings = layer_validator.check_layering_violations_scc()
        elapsed = time.time() - start

        assert elapsed < 1.0, \
            f"Layering violation detection too slow: {elapsed:.2f}s (target: <1.0s)"

        print(f"\n  Layering violation detection: {elapsed:.3f}s")
        print(f"  Violations found: {len(findings)}")

    def test_graceful_degradation_layering_scc(self, layer_validator):
        """Test graceful degradation when layering check fails"""
        try:
            findings = layer_validator.check_layering_violations_scc()
            assert isinstance(findings, list)
        except Exception as e:
            pytest.fail(f"Layering violation check should not raise exceptions: {e}")


# ============================================================================
# TEST CLASS 4: BETWEENNESS - ARCHITECTURE ANALYSIS
# ============================================================================

class TestBetweennessArchitectureAnalysis:
    """Test Betweenness integration in Architecture Analysis (identify_architectural_chokepoints)"""

    def test_identify_chokepoints_method_exists(self, dependency_analyzer):
        """Test that identify_architectural_chokepoints method exists"""
        assert hasattr(dependency_analyzer, 'identify_architectural_chokepoints')
        assert callable(dependency_analyzer.identify_architectural_chokepoints)

    def test_identify_chokepoints_returns_list(self, dependency_analyzer):
        """Test that identify_architectural_chokepoints returns list of dicts"""
        chokepoints = dependency_analyzer.identify_architectural_chokepoints()

        assert isinstance(chokepoints, list)
        # May be empty if no high-betweenness methods

        if chokepoints:
            cp = chokepoints[0]
            assert isinstance(cp, dict)
            assert 'method_name' in cp
            assert 'betweenness_score' in cp
            assert 'is_bridge' in cp

    def test_chokepoints_have_required_fields(self, dependency_analyzer):
        """Test that chokepoint dicts have all required fields"""
        chokepoints = dependency_analyzer.identify_architectural_chokepoints()

        if chokepoints:
            cp = chokepoints[0]
            required_fields = [
                'method_name', 'betweenness_score', 'betweenness_percentile',
                'is_bridge', 'risk_level', 'impact', 'recommendation',
                'detection_algorithm'
            ]
            for field in required_fields:
                assert field in cp, f"Chokepoint missing field: {field}"

    def test_chokepoints_risk_levels(self, dependency_analyzer):
        """Test that chokepoints have appropriate risk levels"""
        chokepoints = dependency_analyzer.identify_architectural_chokepoints()

        if chokepoints:
            for cp in chokepoints:
                assert cp['risk_level'] in ['critical', 'high']
                assert cp['is_bridge'] == True

    def test_chokepoints_performance(self, dependency_analyzer):
        """Test that chokepoint identification has acceptable performance"""
        start = time.time()
        chokepoints = dependency_analyzer.identify_architectural_chokepoints()
        elapsed = time.time() - start

        # Betweenness can be slower due to sampling, target: <5.0s
        assert elapsed < 5.0, \
            f"Chokepoint identification too slow: {elapsed:.2f}s (target: <5.0s)"

        print(f"\n  Chokepoint identification: {elapsed:.3f}s")
        print(f"  Chokepoints found: {len(chokepoints)}")

    def test_graceful_degradation_chokepoints(self, dependency_analyzer):
        """Test graceful degradation when chokepoint detection fails"""
        try:
            chokepoints = dependency_analyzer.identify_architectural_chokepoints()
            assert isinstance(chokepoints, list)
        except Exception as e:
            pytest.fail(f"Chokepoint detection should not raise exceptions: {e}")


# ============================================================================
# TEST CLASS 5: BETWEENNESS - PERFORMANCE ANALYSIS
# ============================================================================

class TestBetweennessPerformanceAnalysis:
    """Test Betweenness integration in Performance Analysis (identify_bottleneck_methods)"""

    def test_identify_bottlenecks_method_exists(self, performance_profiler):
        """Test that identify_bottleneck_methods method exists"""
        assert hasattr(performance_profiler, 'identify_bottleneck_methods')
        assert callable(performance_profiler.identify_bottleneck_methods)

    def test_identify_bottlenecks_returns_findings(self, performance_profiler):
        """Test that identify_bottleneck_methods returns BottleneckFindings"""
        findings = performance_profiler.identify_bottleneck_methods()

        assert isinstance(findings, list)
        # May be empty if no high-betweenness methods

        if findings:
            finding = findings[0]
            assert hasattr(finding, 'finding_id')
            assert hasattr(finding, 'pattern_id')
            assert finding.pattern_id == 'high_traffic_method'

    def test_bottlenecks_have_betweenness_metadata(self, performance_profiler):
        """Test that bottleneck findings include betweenness metadata"""
        findings = performance_profiler.identify_bottleneck_methods()

        if findings:
            finding = findings[0]
            assert 'detection_algorithm' in finding.metadata
            assert finding.metadata['detection_algorithm'] == 'brandes_betweenness'
            assert 'betweenness_score' in finding.metadata
            assert 'percentile' in finding.metadata
            assert 'optimization_priority' in finding.metadata

    def test_bottlenecks_severity_classification(self, performance_profiler):
        """Test that bottlenecks are classified by severity"""
        findings = performance_profiler.identify_bottleneck_methods()

        if findings:
            for finding in findings:
                assert finding.severity in ['critical', 'high', 'medium']
                percentile = finding.metadata.get('percentile', 0)

                # Verify severity matches percentile
                if percentile > 95:
                    assert finding.severity == 'critical'
                elif percentile > 90:
                    assert finding.severity == 'high'

    def test_bottlenecks_performance(self, performance_profiler):
        """Test that bottleneck identification has acceptable performance"""
        start = time.time()
        findings = performance_profiler.identify_bottleneck_methods()
        elapsed = time.time() - start

        # Betweenness can be slower, target: <5.0s
        assert elapsed < 5.0, \
            f"Bottleneck identification too slow: {elapsed:.2f}s (target: <5.0s)"

        print(f"\n  Bottleneck identification: {elapsed:.3f}s")
        print(f"  Bottlenecks found: {len(findings)}")

    def test_graceful_degradation_bottlenecks(self, performance_profiler):
        """Test graceful degradation when bottleneck detection fails"""
        try:
            findings = performance_profiler.identify_bottleneck_methods()
            assert isinstance(findings, list)
        except Exception as e:
            pytest.fail(f"Bottleneck detection should not raise exceptions: {e}")


# ============================================================================
# TEST CLASS 6: PHASE 3 INTEGRATION SUMMARY
# ============================================================================

class TestPhase3IntegrationSummary:
    """Test overall Phase 3 integration completeness"""

    def test_all_scc_methods_available(self, performance_profiler, dependency_analyzer, layer_validator):
        """Test that all SCC methods are available"""
        # Performance Analysis
        assert hasattr(performance_profiler, 'detect_cycles_scc')
        assert callable(performance_profiler.detect_cycles_scc)

        # Refactoring Assistance
        assert hasattr(dependency_analyzer, 'detect_circular_dependencies')
        assert callable(dependency_analyzer.detect_circular_dependencies)

        # Architecture Violations
        assert hasattr(layer_validator, 'check_layering_violations_scc')
        assert callable(layer_validator.check_layering_violations_scc)

    def test_all_betweenness_methods_available(self, performance_profiler, dependency_analyzer):
        """Test that all Betweenness methods are available"""
        # Architecture Analysis
        assert hasattr(dependency_analyzer, 'identify_architectural_chokepoints')
        assert callable(dependency_analyzer.identify_architectural_chokepoints)

        # Performance Analysis
        assert hasattr(performance_profiler, 'identify_bottleneck_methods')
        assert callable(performance_profiler.identify_bottleneck_methods)

    def test_all_phase3_methods_run_successfully(
        self,
        performance_profiler,
        dependency_analyzer,
        layer_validator
    ):
        """Test that all Phase 3 methods run without errors"""
        try:
            # SCC methods
            _ = performance_profiler.detect_cycles_scc()
            _ = dependency_analyzer.detect_circular_dependencies()
            _ = layer_validator.check_layering_violations_scc()

            # Betweenness methods
            _ = dependency_analyzer.identify_architectural_chokepoints()
            _ = performance_profiler.identify_bottleneck_methods()

        except Exception as e:
            pytest.fail(f"Phase 3 method raised exception: {e}")

    def test_phase3_performance_targets_met(
        self,
        performance_profiler,
        dependency_analyzer,
        layer_validator
    ):
        """Test that all Phase 3 methods meet performance targets"""
        results = {}

        # SCC methods (target: <1.0s each)
        start = time.time()
        _ = performance_profiler.detect_cycles_scc()
        results['scc_cycles'] = time.time() - start

        start = time.time()
        _ = dependency_analyzer.detect_circular_dependencies()
        results['scc_circular_deps'] = time.time() - start

        start = time.time()
        _ = layer_validator.check_layering_violations_scc()
        results['scc_layering'] = time.time() - start

        # Betweenness methods (target: <5.0s each)
        start = time.time()
        _ = dependency_analyzer.identify_architectural_chokepoints()
        results['betweenness_chokepoints'] = time.time() - start

        start = time.time()
        _ = performance_profiler.identify_bottleneck_methods()
        results['betweenness_bottlenecks'] = time.time() - start

        # Print results
        print("\n  Phase 3 Performance Benchmarks:")
        print(f"    SCC - Cycle Detection: {results['scc_cycles']:.3f}s")
        print(f"    SCC - Circular Dependencies: {results['scc_circular_deps']:.3f}s")
        print(f"    SCC - Layering Violations: {results['scc_layering']:.3f}s")
        print(f"    Betweenness - Chokepoints: {results['betweenness_chokepoints']:.3f}s")
        print(f"    Betweenness - Bottlenecks: {results['betweenness_bottlenecks']:.3f}s")

        # Verify targets
        assert results['scc_cycles'] < 1.0, "SCC cycle detection too slow"
        assert results['scc_circular_deps'] < 1.0, "SCC circular deps too slow"
        assert results['scc_layering'] < 1.0, "SCC layering check too slow"
        assert results['betweenness_chokepoints'] < 5.0, "Betweenness chokepoints too slow"
        assert results['betweenness_bottlenecks'] < 5.0, "Betweenness bottlenecks too slow"

    def test_phase3_backward_compatibility(self, cpg_service):
        """Test that Phase 3 enhancements don't break existing functionality"""
        # Verify agents can still be instantiated
        try:
            profiler = PerformanceProfiler(cpg_service)
            analyzer = DependencyAnalyzer(cpg_service)
            validator = LayerValidator(cpg_service)

            # Verify CallGraphAnalyzer is initialized
            assert hasattr(profiler, 'call_graph_analyzer')
            assert hasattr(analyzer, 'call_graph_analyzer')
            assert hasattr(validator, 'call_graph_analyzer')

        except Exception as e:
            pytest.fail(f"Phase 3 broke backward compatibility: {e}")

    def test_phase3_algorithms_consistency(
        self,
        performance_profiler,
        dependency_analyzer,
        layer_validator
    ):
        """Test that Phase 3 algorithms produce consistent results"""
        # Run SCC twice, should get same cycles
        cycles1 = performance_profiler.detect_cycles_scc()
        cycles2 = performance_profiler.detect_cycles_scc()

        assert len(cycles1) == len(cycles2), \
            "SCC should produce consistent results across runs"

        # Run betweenness twice, should get similar top results
        # Note: Sampling may cause slight variations, but top methods should be similar
        chokepoints1 = dependency_analyzer.identify_architectural_chokepoints()
        chokepoints2 = dependency_analyzer.identify_architectural_chokepoints()

        if chokepoints1 and chokepoints2:
            # Compare top 5 methods (order may vary slightly due to sampling)
            top5_methods1 = set(cp['method_name'] for cp in chokepoints1[:5])
            top5_methods2 = set(cp['method_name'] for cp in chokepoints2[:5])

            # At least 3 of top 5 should be the same
            overlap = len(top5_methods1 & top5_methods2)
            assert overlap >= 3, \
                f"Betweenness should produce similar top results (overlap: {overlap}/5)"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
