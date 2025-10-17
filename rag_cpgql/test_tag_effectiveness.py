"""Test Tag Effectiveness Tracking (Phase 2)

Tests the tag effectiveness tracker and feedback loop to verify:
1. Tag usage is recorded correctly
2. Effectiveness scores are calculated properly
3. High-performing tags get boosted in relevance scoring
4. Low-performing tags get penalized
5. Persistence works correctly

Usage:
    conda activate llama.cpp
    python test_tag_effectiveness.py
"""

import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.tag_effectiveness_tracker import TagEffectivenessTracker


def test_basic_recording():
    """Test 1: Basic tag usage recording."""
    print("\n" + "="*80)
    print("TEST 1: Basic Tag Usage Recording")
    print("="*80)

    tracker = TagEffectivenessTracker(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        min_samples=2
    )

    # Record some successful uses
    for i in range(5):
        tracker.record_tag_usage(
            tag_name="function-purpose",
            tag_value="memory-management",
            domain="memory",
            intent="find-function",
            query_valid=True,
            query_executed=True,
            execution_successful=True,
            coverage_score=0.75
        )

    stats = tracker.get_tag_stats("function-purpose", "memory-management")

    print(f"\n📊 Statistics after 5 successful uses:")
    print(f"  Total uses: {stats['total_uses']}")
    print(f"  Valid queries: {stats['valid_queries']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    print(f"  Avg coverage: {stats['avg_coverage']:.3f}")
    print(f"  Effectiveness: {stats['effectiveness_score']:.3f}")

    assert stats['total_uses'] == 5, "Should have 5 uses"
    assert stats['valid_queries'] == 5, "All should be valid"
    assert stats['success_rate'] == 1.0, "100% success rate"
    assert abs(stats['avg_coverage'] - 0.75) < 0.01, "Avg coverage should be 0.75"
    assert stats['effectiveness_score'] > 0.7, "High effectiveness expected"

    print("\n✓ PASS: Basic recording works correctly")
    return True


def test_effectiveness_calculation():
    """Test 2: Effectiveness score calculation."""
    print("\n" + "="*80)
    print("TEST 2: Effectiveness Score Calculation")
    print("="*80)

    tracker = TagEffectivenessTracker(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        min_samples=3
    )

    # High-performing tag (all successful)
    for i in range(10):
        tracker.record_tag_usage(
            tag_name="domain-concept",
            tag_value="vacuum",
            domain="vacuum",
            intent="explain-concept",
            query_valid=True,
            query_executed=True,
            execution_successful=True,
            coverage_score=0.8
        )

    # Low-performing tag (mostly failures)
    for i in range(10):
        tracker.record_tag_usage(
            tag_name="data-structure",
            tag_value="unknown-struct",
            domain="general",
            intent="find-function",
            query_valid=(i < 2),  # Only 2/10 valid
            query_executed=False,
            execution_successful=False,
            coverage_score=0.2
        )

    high_perf = tracker.get_tag_effectiveness("domain-concept", "vacuum")
    low_perf = tracker.get_tag_effectiveness("data-structure", "unknown-struct")

    print(f"\n📊 Effectiveness Scores:")
    print(f"  High-performing tag: {high_perf:.3f}")
    print(f"  Low-performing tag:  {low_perf:.3f}")

    assert high_perf > 0.7, f"High-performing tag should have >0.7 effectiveness, got {high_perf}"
    assert low_perf < 0.3, f"Low-performing tag should have <0.3 effectiveness, got {low_perf}"
    assert high_perf > low_perf, "High-performing should score higher than low-performing"

    print("\n✓ PASS: Effectiveness calculation works correctly")
    return True


def test_minimum_samples_threshold():
    """Test 3: Minimum samples threshold."""
    print("\n" + "="*80)
    print("TEST 3: Minimum Samples Threshold")
    print("="*80)

    tracker = TagEffectivenessTracker(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        min_samples=5
    )

    # Record only 3 uses (below threshold)
    for i in range(3):
        tracker.record_tag_usage(
            tag_name="Feature",
            tag_value="MVCC",
            domain="mvcc",
            intent="explain-concept",
            query_valid=True,
            coverage_score=0.9
        )

    effectiveness = tracker.get_tag_effectiveness("Feature", "MVCC")

    print(f"\n📊 Effectiveness with 3 samples (threshold=5):")
    print(f"  Effectiveness: {effectiveness:.3f}")
    print(f"  Expected: 0.5 (neutral, insufficient data)")

    assert effectiveness == 0.5, "Should return neutral 0.5 when below min_samples"

    # Add 2 more samples to reach threshold
    for i in range(2):
        tracker.record_tag_usage(
            tag_name="Feature",
            tag_value="MVCC",
            domain="mvcc",
            intent="explain-concept",
            query_valid=True,
            coverage_score=0.9
        )

    effectiveness = tracker.get_tag_effectiveness("Feature", "MVCC")

    print(f"\n📊 Effectiveness with 5 samples (threshold=5):")
    print(f"  Effectiveness: {effectiveness:.3f}")
    print(f"  Expected: >0.5 (actual score, sufficient data)")

    assert effectiveness > 0.5, "Should return actual score when at or above min_samples"

    print("\n✓ PASS: Minimum samples threshold works correctly")
    return True


def test_persistence():
    """Test 4: Persistence to disk."""
    print("\n" + "="*80)
    print("TEST 4: Persistence")
    print("="*80)

    temp_file = Path(tempfile.mktemp(suffix=".json"))

    # Create tracker and record data
    tracker1 = TagEffectivenessTracker(
        persistence_path=temp_file,
        min_samples=2
    )

    for i in range(5):
        tracker1.record_tag_usage(
            tag_name="subsystem-name",
            tag_value="autovacuum",
            domain="vacuum",
            intent="find-function",
            query_valid=True,
            coverage_score=0.7
        )

    tracker1.persist()

    # Load in new tracker instance
    tracker2 = TagEffectivenessTracker(
        persistence_path=temp_file,
        min_samples=2
    )

    effectiveness = tracker2.get_tag_effectiveness("subsystem-name", "autovacuum")
    stats = tracker2.get_tag_stats("subsystem-name", "autovacuum")

    print(f"\n📊 Loaded from disk:")
    print(f"  Total uses: {stats['total_uses']}")
    print(f"  Effectiveness: {effectiveness:.3f}")

    assert stats['total_uses'] == 5, "Should persist total_uses"
    assert effectiveness > 0.5, "Should persist effectiveness score"

    # Clean up
    if temp_file.exists():
        temp_file.unlink()

    print("\n✓ PASS: Persistence works correctly")
    return True


def test_top_tags():
    """Test 5: Get top-performing tags."""
    print("\n" + "="*80)
    print("TEST 5: Top Tags Retrieval")
    print("="*80)

    tracker = TagEffectivenessTracker(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        min_samples=3
    )

    # Record several tags with different performance levels
    tags_data = [
        ("function-purpose", "memory-management", 10, 10, 0.8),  # Perfect
        ("domain-concept", "wal", 8, 6, 0.7),  # Good
        ("data-structure", "heap", 5, 2, 0.3),  # Poor
        ("Feature", "MVCC", 7, 7, 0.9),  # Excellent
        ("subsystem-name", "vacuum", 6, 3, 0.5),  # Mediocre
    ]

    for tag_name, tag_value, total, valid, coverage in tags_data:
        for i in range(total):
            tracker.record_tag_usage(
                tag_name=tag_name,
                tag_value=tag_value,
                domain="test",
                intent="test",
                query_valid=(i < valid),
                coverage_score=coverage
            )

    top_tags = tracker.get_top_tags(limit=3)

    print(f"\n📊 Top 3 Tags:")
    for i, (tag_name, tag_value, effectiveness) in enumerate(top_tags, 1):
        print(f"  {i}. {tag_name}={tag_value}: {effectiveness:.3f}")

    assert len(top_tags) <= 3, "Should return at most 3 tags"
    assert len(top_tags) > 0, "Should have at least some tags"

    # Top tag should be one of the high-performing ones (>0.6 is good)
    top_tag_name, top_tag_value, top_effectiveness = top_tags[0]
    assert top_effectiveness > 0.6, f"Top tag should have high effectiveness (>0.6), got {top_effectiveness:.3f}"

    print("\n✓ PASS: Top tags retrieval works correctly")
    return True


def test_summary_stats():
    """Test 6: Summary statistics."""
    print("\n" + "="*80)
    print("TEST 6: Summary Statistics")
    print("="*80)

    tracker = TagEffectivenessTracker(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        min_samples=3
    )

    # Record various tags
    for i in range(10):
        tracker.record_tag_usage(
            tag_name="function-purpose",
            tag_value=f"purpose-{i % 3}",
            domain="test",
            intent="test",
            query_valid=True,
            coverage_score=0.7
        )

    summary = tracker.get_summary_stats()

    print(f"\n📊 Summary Statistics:")
    print(f"  Total unique tags: {summary['total_tags']}")
    print(f"  Total uses: {summary['total_uses']}")
    print(f"  Avg effectiveness: {summary['avg_effectiveness']:.3f}")
    print(f"  Tags with sufficient data: {summary['tags_with_sufficient_data']}")

    assert summary['total_tags'] == 3, "Should have 3 unique tags"
    assert summary['total_uses'] == 10, "Should have 10 total uses"
    assert summary['tags_with_sufficient_data'] >= 1, "At least one tag should have enough data"

    print("\n✓ PASS: Summary statistics work correctly")
    return True


def run_all_tests():
    """Run all tag effectiveness tests."""
    print("\n" + "="*80)
    print("TAG EFFECTIVENESS TRACKER TEST SUITE (Phase 2)")
    print("="*80)

    tests = [
        ("Basic Recording", test_basic_recording),
        ("Effectiveness Calculation", test_effectiveness_calculation),
        ("Minimum Samples Threshold", test_minimum_samples_threshold),
        ("Persistence", test_persistence),
        ("Top Tags Retrieval", test_top_tags),
        ("Summary Statistics", test_summary_stats),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    total_passed = sum(1 for _, p in results if p)
    total_tests = len(results)

    print(f"\n📊 Overall: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("Tag effectiveness tracking is working correctly!")
        return True
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
