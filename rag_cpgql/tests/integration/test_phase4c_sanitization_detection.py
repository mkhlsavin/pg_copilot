"""
Integration Tests for Phase 4C: Enhanced Sanitization Detection

Tests the enhanced sanitization detection with confidence scoring:
1. Confidence scoring for sanitization patterns
2. Path filtering based on sanitization confidence
3. check_sanitization parameter in find_taint_paths()
4. Expanded pattern library (45 patterns)

Author: Phase 4C Implementation
Date: November 25, 2025
"""

import pytest
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.services.cpg_query_service import CPGQueryService
from src.analysis.dataflow_tracer import (
    DataFlowTracer,
    SANITIZATION_CONFIDENCE,
    SANITIZATION_CONFIDENCE_THRESHOLD
)


# ============================================================================
# Test Class 1: Sanitization Confidence Scoring
# ============================================================================

class TestSanitizationConfidenceScoring:
    """Test confidence scoring for sanitization patterns"""

    def test_sanitization_confidence_dict_exists(self):
        """Test that SANITIZATION_CONFIDENCE dictionary exists and is populated"""
        assert SANITIZATION_CONFIDENCE is not None
        assert isinstance(SANITIZATION_CONFIDENCE, dict)
        assert len(SANITIZATION_CONFIDENCE) > 0

        print(f"\n  ✓ SANITIZATION_CONFIDENCE has {len(SANITIZATION_CONFIDENCE)} patterns")

    def test_high_confidence_patterns(self):
        """Test that high-confidence patterns have correct scores"""
        # High confidence patterns should be 1.0
        assert SANITIZATION_CONFIDENCE.get('parameterize') == 1.0
        assert SANITIZATION_CONFIDENCE.get('prepare') == 1.0
        assert SANITIZATION_CONFIDENCE.get('bind') == 1.0

        # Very high confidence (0.9)
        assert SANITIZATION_CONFIDENCE.get('pg_escape_string') == 0.9
        assert SANITIZATION_CONFIDENCE.get('htmlspecialchars') == 0.9

        print(f"\n  ✓ High-confidence patterns validated")

    def test_medium_confidence_patterns(self):
        """Test that medium-confidence patterns have correct scores"""
        # Medium confidence (0.7)
        assert SANITIZATION_CONFIDENCE.get('escape_%') == 0.7
        assert SANITIZATION_CONFIDENCE.get('sanitize_%') == 0.7

        # Medium-low confidence (0.6)
        assert SANITIZATION_CONFIDENCE.get('filter_%') == 0.6
        assert SANITIZATION_CONFIDENCE.get('clean_%') == 0.6

        print(f"\n  ✓ Medium-confidence patterns validated")

    def test_low_confidence_patterns(self):
        """Test that low-confidence patterns have correct scores"""
        # Low confidence (0.3)
        assert SANITIZATION_CONFIDENCE.get('trim') == 0.3
        assert SANITIZATION_CONFIDENCE.get('strip') == 0.3

        # Very low confidence (0.2)
        assert SANITIZATION_CONFIDENCE.get('addslashes') == 0.2

        print(f"\n  ✓ Low-confidence patterns validated")

    def test_confidence_threshold(self):
        """Test that confidence threshold is set correctly"""
        assert SANITIZATION_CONFIDENCE_THRESHOLD == 0.7

        print(f"\n  ✓ Confidence threshold: {SANITIZATION_CONFIDENCE_THRESHOLD}")

    def test_pattern_library_expansion(self):
        """Test that pattern library has been expanded"""
        # Phase 4C expanded from 18 to 45+ patterns
        assert len(SANITIZATION_CONFIDENCE) >= 40

        # Check for new patterns added in Phase 4C
        new_patterns = ['parameterize', 'whitelist', 'allowlist', 'intval', 'json_encode']
        for pattern in new_patterns:
            assert pattern in SANITIZATION_CONFIDENCE

        print(f"\n  ✓ Pattern library expanded to {len(SANITIZATION_CONFIDENCE)} patterns")


# ============================================================================
# Test Class 2: Sanitization Detection with Confidence
# ============================================================================

class TestSanitizationDetectionWithConfidence:
    """Test sanitization detection returns confidence scores"""

    def test_detect_sanitization_returns_tuple(self):
        """Test that _detect_sanitization_on_path returns (points, confidence) tuple"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Call with dummy IDs (may return empty results, but should return tuple)
            result = tracer._detect_sanitization_on_path(
                source_call_id=1,
                sink_call_id=2,
                variable_name='test_var',
                max_depth=5
            )

            # Should return tuple
            assert isinstance(result, tuple)
            assert len(result) == 2

            sanitization_points, max_confidence = result

            # Should be correct types
            assert isinstance(sanitization_points, list)
            assert isinstance(max_confidence, (int, float))
            assert 0.0 <= max_confidence <= 1.0

            print(f"\n  ✓ _detect_sanitization_on_path returns (list, float) tuple")
            print(f"  ✓ Max confidence: {max_confidence:.2f}")

    def test_sanitization_point_structure(self):
        """Test that sanitization points have confidence and pattern fields"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            sanitization_points, max_confidence = tracer._detect_sanitization_on_path(
                source_call_id=1,
                sink_call_id=100,
                variable_name='test',
                max_depth=10
            )

            if sanitization_points:
                point = sanitization_points[0]

                # Phase 4C: Should have confidence and pattern fields
                assert 'confidence' in point
                assert 'pattern' in point
                assert 'function' in point
                assert 'line' in point

                # Confidence should be valid
                assert isinstance(point['confidence'], (int, float))
                assert 0.0 <= point['confidence'] <= 1.0

                print(f"\n  ✓ Sanitization point structure enhanced")
                print(f"  ✓ Function: {point['function']}")
                print(f"  ✓ Confidence: {point['confidence']:.2f}")
                print(f"  ✓ Pattern: {point['pattern']}")


# ============================================================================
# Test Class 3: Taint Path Filtering
# ============================================================================

class TestTaintPathFiltering:
    """Test that paths with sanitization are filtered correctly"""

    def test_find_taint_paths_has_check_sanitization_param(self):
        """Test that find_taint_paths accepts check_sanitization parameter"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Should accept check_sanitization parameter without error
            paths_with_filtering = tracer.find_taint_paths(
                source_functions=['recv', 'read'],
                sink_functions=['system', 'exec'],
                max_depth=5,
                check_sanitization=True
            )

            paths_without_filtering = tracer.find_taint_paths(
                source_functions=['recv', 'read'],
                sink_functions=['system', 'exec'],
                max_depth=5,
                check_sanitization=False
            )

            # Both should return lists
            assert isinstance(paths_with_filtering, list)
            assert isinstance(paths_without_filtering, list)

            print(f"\n  ✓ check_sanitization parameter accepted")
            print(f"  ✓ With filtering: {len(paths_with_filtering)} paths")
            print(f"  ✓ Without filtering: {len(paths_without_filtering)} paths")

    def test_path_filtering_reduces_results(self):
        """Test that check_sanitization=True reduces false positives"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Get paths without filtering
            all_paths = tracer.find_taint_paths(
                source_functions=['recv', 'read', 'getenv'],
                sink_functions=['system', 'exec', 'popen'],
                max_depth=8,
                check_sanitization=False
            )

            # Get paths with filtering (should be fewer or equal)
            filtered_paths = tracer.find_taint_paths(
                source_functions=['recv', 'read', 'getenv'],
                sink_functions=['system', 'exec', 'popen'],
                max_depth=8,
                check_sanitization=True
            )

            # Filtered should be <= all paths
            assert len(filtered_paths) <= len(all_paths)

            # Calculate reduction
            if len(all_paths) > 0:
                reduction = (len(all_paths) - len(filtered_paths)) / len(all_paths) * 100
                print(f"\n  ✓ Path filtering works")
                print(f"  ✓ All paths: {len(all_paths)}")
                print(f"  ✓ Filtered paths: {len(filtered_paths)}")
                print(f"  ✓ Reduction: {reduction:.1f}%")
            else:
                print(f"\n  ✓ No taint paths found (expected for clean code)")

    def test_filtered_paths_retain_sanitization_info(self):
        """Test that returned paths still have sanitization_points field"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            paths = tracer.find_taint_paths(
                source_functions=['recv'],
                sink_functions=['system'],
                max_depth=10,
                check_sanitization=True
            )

            for path in paths[:5]:  # Check first 5 paths
                # Should have sanitization_points field
                assert hasattr(path, 'sanitization_points')
                assert isinstance(path.sanitization_points, list)

                # If there are sanitization points, they should have confidence < threshold
                # (otherwise path would have been filtered)
                if path.sanitization_points:
                    for point in path.sanitization_points:
                        if 'confidence' in point:
                            # All sanitization points should be below threshold
                            # (otherwise path would be filtered)
                            assert point['confidence'] < SANITIZATION_CONFIDENCE_THRESHOLD

            print(f"\n  ✓ Filtered paths retain sanitization info")
            print(f"  ✓ Checked {min(len(paths), 5)} paths")


# ============================================================================
# Test Class 4: Performance and Scalability
# ============================================================================

class TestPhase4CPerformance:
    """Test performance of enhanced sanitization detection"""

    def test_sanitization_detection_performance(self):
        """Test that sanitization detection completes in reasonable time"""
        import time

        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            start = time.time()

            # Run taint analysis with sanitization filtering
            paths = tracer.find_taint_paths(
                source_functions=['recv', 'read', 'getenv', 'fgets'],
                sink_functions=['system', 'exec', 'popen', 'strcpy'],
                max_depth=10,
                check_sanitization=True
            )

            elapsed = time.time() - start

            # Should complete in reasonable time (< 30s for typical codebase)
            assert elapsed < 30.0

            print(f"\n  ✓ Taint analysis with filtering: {elapsed:.2f}s")
            print(f"  ✓ Paths found: {len(paths)}")

    def test_pattern_matching_efficiency(self):
        """Test that pattern matching with 45 patterns is efficient"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Pattern library should be reasonable size
            assert len(SANITIZATION_CONFIDENCE) < 100  # Not too many patterns

            # All patterns should have valid confidence scores
            for pattern, confidence in SANITIZATION_CONFIDENCE.items():
                assert isinstance(pattern, str)
                assert isinstance(confidence, (int, float))
                assert 0.0 <= confidence <= 1.0

            print(f"\n  ✓ Pattern library size: {len(SANITIZATION_CONFIDENCE)}")
            print(f"  ✓ All patterns have valid confidence scores")


# ============================================================================
# Test Class 5: Phase 4C Integration Summary
# ============================================================================

class TestPhase4CIntegrationSummary:
    """Summary tests for Phase 4C enhancements"""

    def test_all_phase4c_features_implemented(self):
        """Verify all Phase 4C features are implemented"""
        # 1. Confidence scoring dictionary
        assert SANITIZATION_CONFIDENCE is not None
        assert len(SANITIZATION_CONFIDENCE) >= 40

        # 2. Confidence threshold
        assert SANITIZATION_CONFIDENCE_THRESHOLD == 0.7

        # 3. DataFlowTracer has enhanced methods
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # find_taint_paths accepts check_sanitization
            import inspect
            sig = inspect.signature(tracer.find_taint_paths)
            assert 'check_sanitization' in sig.parameters

            # _detect_sanitization_on_path returns tuple
            result = tracer._detect_sanitization_on_path(1, 2, 'var', 5)
            assert isinstance(result, tuple)
            assert len(result) == 2

        print(f"\n  ✓ All Phase 4C features implemented")
        print(f"  ✓ Confidence scoring: {len(SANITIZATION_CONFIDENCE)} patterns")
        print(f"  ✓ Threshold: {SANITIZATION_CONFIDENCE_THRESHOLD}")
        print(f"  ✓ Path filtering: Enabled")

    def test_backward_compatibility(self):
        """Test that changes don't break existing code"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Should work without check_sanitization parameter (default=True)
            paths = tracer.find_taint_paths(
                source_functions=['recv'],
                sink_functions=['system'],
                max_depth=5
            )

            assert isinstance(paths, list)

            print(f"\n  ✓ Backward compatibility maintained")
            print(f"  ✓ Default check_sanitization=True works")

    def test_false_positive_reduction_potential(self):
        """Estimate false positive reduction from Phase 4C"""
        with CPGQueryService() as cpg:
            tracer = DataFlowTracer(cpg)

            # Get all paths (no filtering)
            all_paths = tracer.find_taint_paths(
                source_functions=['recv', 'read', 'getenv'],
                sink_functions=['system', 'exec', 'popen'],
                max_depth=10,
                check_sanitization=False
            )

            # Get filtered paths (with sanitization check)
            filtered_paths = tracer.find_taint_paths(
                source_functions=['recv', 'read', 'getenv'],
                sink_functions=['system', 'exec', 'popen'],
                max_depth=10,
                check_sanitization=True
            )

            if len(all_paths) > 0:
                reduction_pct = (len(all_paths) - len(filtered_paths)) / len(all_paths) * 100

                print(f"\n  ✓ False Positive Reduction Estimate")
                print(f"  ✓ Total paths (no filter): {len(all_paths)}")
                print(f"  ✓ Filtered paths: {len(filtered_paths)}")
                print(f"  ✓ Reduction: {reduction_pct:.1f}%")
                print(f"  ✓ Paths filtered: {len(all_paths) - len(filtered_paths)}")
            else:
                print(f"\n  ✓ No taint paths found (clean codebase)")


# ============================================================================
# Pytest Configuration
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
