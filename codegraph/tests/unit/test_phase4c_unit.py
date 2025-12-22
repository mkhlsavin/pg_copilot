"""
Unit Tests for Phase 4C: Sanitization Confidence Scoring

Tests the confidence scoring logic without database queries.

Author: Phase 4C Implementation
Date: November 25, 2025
"""

import pytest
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.analysis.dataflow_tracer import (
    SANITIZATION_CONFIDENCE,
    SANITIZATION_CONFIDENCE_THRESHOLD
)


class TestSanitizationConfidenceConstants:
    """Test confidence scoring constants"""

    def test_sanitization_confidence_exists(self):
        """Test that SANITIZATION_CONFIDENCE dictionary exists"""
        assert SANITIZATION_CONFIDENCE is not None
        # SANITIZATION_CONFIDENCE is a lazy-loading proxy that behaves like a dict
        assert hasattr(SANITIZATION_CONFIDENCE, '__getitem__')
        assert hasattr(SANITIZATION_CONFIDENCE, '__len__')
        print(f"\n  ✓ SANITIZATION_CONFIDENCE exists with {len(SANITIZATION_CONFIDENCE)} patterns")

    def test_pattern_count(self):
        """Test that pattern library has been expanded"""
        # Phase 4C expanded from 18 to 45+ patterns
        assert len(SANITIZATION_CONFIDENCE) >= 40
        print(f"\n  ✓ Pattern library: {len(SANITIZATION_CONFIDENCE)} patterns (target: 45+)")

    def test_high_confidence_patterns(self):
        """Test high-confidence patterns (1.0)"""
        high_conf_patterns = ['parameterize', 'prepare', 'bind', 'bind_param', 'placeholder']

        for pattern in high_conf_patterns:
            assert pattern in SANITIZATION_CONFIDENCE
            assert SANITIZATION_CONFIDENCE[pattern] == 1.0

        print(f"\n  ✓ High-confidence patterns (1.0): {len(high_conf_patterns)}")

    def test_very_high_confidence_patterns(self):
        """Test very high-confidence patterns (0.9)"""
        very_high_patterns = [
            'pg_escape_string',
            'pg_escape_bytea',
            'mysqli_real_escape_string',
            'mysql_real_escape_string',
            'htmlspecialchars',
            'htmlentities'
        ]

        for pattern in very_high_patterns:
            assert pattern in SANITIZATION_CONFIDENCE
            assert SANITIZATION_CONFIDENCE[pattern] == 0.9

        print(f"\n  ✓ Very high-confidence patterns (0.9): {len(very_high_patterns)}")

    def test_medium_confidence_patterns(self):
        """Test medium-confidence patterns (0.7-0.8)"""
        medium_patterns = [
            'validate_%',  # 0.8
            'verify_%',    # 0.8
            'escape_%',    # 0.7
            'sanitize_%',  # 0.7
            'encode_%',    # 0.7
        ]

        for pattern in medium_patterns:
            assert pattern in SANITIZATION_CONFIDENCE
            assert 0.7 <= SANITIZATION_CONFIDENCE[pattern] <= 0.8

        print(f"\n  ✓ Medium-confidence patterns (0.7-0.8): {len(medium_patterns)}")

    def test_low_confidence_patterns(self):
        """Test low-confidence patterns (0.2-0.3)"""
        low_patterns = [
            'trim',          # 0.3
            'strip',         # 0.3
            'addslashes',    # 0.2
            'str_replace',   # 0.2
        ]

        for pattern in low_patterns:
            assert pattern in SANITIZATION_CONFIDENCE
            assert 0.2 <= SANITIZATION_CONFIDENCE[pattern] <= 0.3

        print(f"\n  ✓ Low-confidence patterns (0.2-0.3): {len(low_patterns)}")

    def test_all_confidence_scores_valid(self):
        """Test that all confidence scores are in range [0.0, 1.0]"""
        for pattern, confidence in SANITIZATION_CONFIDENCE.items():
            assert isinstance(confidence, (int, float))
            assert 0.0 <= confidence <= 1.0
            assert isinstance(pattern, str)

        print(f"\n  ✓ All {len(SANITIZATION_CONFIDENCE)} patterns have valid scores [0.0-1.0]")

    def test_confidence_threshold(self):
        """Test that confidence threshold is set correctly"""
        assert SANITIZATION_CONFIDENCE_THRESHOLD == 0.7
        print(f"\n  ✓ Confidence threshold: {SANITIZATION_CONFIDENCE_THRESHOLD}")

    def test_pattern_categories(self):
        """Test that patterns cover all major categories"""
        # Check that we have patterns in each category

        # Parameterization (highest confidence)
        param_patterns = [p for p in SANITIZATION_CONFIDENCE.keys() if 'param' in p or 'bind' in p or 'prepare' in p]
        assert len(param_patterns) >= 4

        # Escaping
        escape_patterns = [p for p in SANITIZATION_CONFIDENCE.keys() if 'escape' in p or 'html' in p]
        assert len(escape_patterns) >= 5

        # Validation
        validation_patterns = [p for p in SANITIZATION_CONFIDENCE.keys() if 'validate' in p or 'verify' in p or 'check' in p]
        assert len(validation_patterns) >= 3

        # Type conversion
        type_patterns = [p for p in SANITIZATION_CONFIDENCE.keys() if 'int' in p or 'float' in p]
        assert len(type_patterns) >= 4

        print(f"\n  ✓ Pattern categories covered:")
        print(f"    - Parameterization: {len(param_patterns)}")
        print(f"    - Escaping: {len(escape_patterns)}")
        print(f"    - Validation: {len(validation_patterns)}")
        print(f"    - Type conversion: {len(type_patterns)}")

    def test_new_phase4c_patterns(self):
        """Test that Phase 4C added new patterns"""
        # These patterns should be new in Phase 4C
        new_patterns = [
            'parameterize',
            'placeholder',
            'whitelist',
            'allowlist',
            'intval',
            'floatval',
            'json_encode',
            'htmlentities',
            'pg_escape_bytea'
        ]

        for pattern in new_patterns:
            assert pattern in SANITIZATION_CONFIDENCE

        print(f"\n  ✓ Phase 4C added {len(new_patterns)} new patterns")


class TestConfidenceScoringLogic:
    """Test confidence scoring logic"""

    def test_threshold_filters_weak_sanitization(self):
        """Test that threshold (0.7) filters weak sanitization"""
        # Patterns below threshold should not pass
        weak_patterns = ['trim', 'strip', 'addslashes', 'str_replace']

        for pattern in weak_patterns:
            assert SANITIZATION_CONFIDENCE[pattern] < SANITIZATION_CONFIDENCE_THRESHOLD

        print(f"\n  ✓ Weak sanitization patterns below threshold")

    def test_threshold_accepts_strong_sanitization(self):
        """Test that threshold (0.7) accepts strong sanitization"""
        # Patterns at or above threshold should pass
        strong_patterns = [
            'parameterize',        # 1.0
            'prepare',             # 1.0
            'pg_escape_string',    # 0.9
            'htmlspecialchars',    # 0.9
            'validate_%',          # 0.8
            'escape_%',            # 0.7
            'sanitize_%',          # 0.7
        ]

        for pattern in strong_patterns:
            assert SANITIZATION_CONFIDENCE[pattern] >= SANITIZATION_CONFIDENCE_THRESHOLD

        print(f"\n  ✓ Strong sanitization patterns at/above threshold")

    def test_confidence_distribution(self):
        """Test that confidence scores are well-distributed"""
        scores = list(SANITIZATION_CONFIDENCE.values())

        # Should have patterns across confidence spectrum
        high_conf = [s for s in scores if s >= 0.9]
        medium_conf = [s for s in scores if 0.6 <= s < 0.9]
        low_conf = [s for s in scores if s < 0.6]

        assert len(high_conf) >= 5   # At least 5 high-confidence
        assert len(medium_conf) >= 10  # At least 10 medium
        assert len(low_conf) >= 5    # At least 5 low

        print(f"\n  ✓ Confidence distribution:")
        print(f"    - High (≥0.9): {len(high_conf)}")
        print(f"    - Medium (0.6-0.9): {len(medium_conf)}")
        print(f"    - Low (<0.6): {len(low_conf)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
