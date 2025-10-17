"""Test Phase 3: Query Pattern Library Enhancement

Tests the expanded TAG_QUERY_PATTERNS, complexity-aware selection,
and intent-specific template system.

Usage:
    conda activate llama.cpp
    python test_phase3_patterns.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.enrichment_prompt_builder import (
    EnrichmentPromptBuilder,
    TAG_QUERY_PATTERNS,
    COMPLEXITY_PATTERNS,
    INTENT_TAG_PRIORITY
)


def test_pattern_coverage():
    """Test 1: Verify TAG_QUERY_PATTERNS has 15+ categories."""
    print("\n" + "="*80)
    print("TEST 1: Pattern Library Coverage")
    print("="*80)

    print(f"\n📊 TAG_QUERY_PATTERNS categories:")
    for i, category in enumerate(sorted(TAG_QUERY_PATTERNS.keys()), 1):
        pattern_count = len(TAG_QUERY_PATTERNS[category])
        print(f"  {i:2d}. {category:25s} ({pattern_count} patterns)")

    total_categories = len(TAG_QUERY_PATTERNS)
    total_patterns = sum(len(patterns) for patterns in TAG_QUERY_PATTERNS.values())

    print(f"\n📈 Summary:")
    print(f"  Total categories: {total_categories}")
    print(f"  Total patterns: {total_patterns}")
    print(f"  Target: 15+ categories")

    assert total_categories >= 15, f"Expected 15+ categories, got {total_categories}"
    assert total_patterns >= 45, f"Expected 45+ patterns (3 per category), got {total_patterns}"

    print("\n✓ PASS: Pattern library meets coverage targets")
    return True


def test_complexity_patterns():
    """Test 2: Verify COMPLEXITY_PATTERNS has all three levels."""
    print("\n" + "="*80)
    print("TEST 2: Complexity-Aware Patterns")
    print("="*80)

    required_levels = ['simple', 'moderate', 'complex']

    print(f"\n📊 COMPLEXITY_PATTERNS levels:")
    for level in required_levels:
        if level in COMPLEXITY_PATTERNS:
            pattern_count = len(COMPLEXITY_PATTERNS[level])
            print(f"  • {level:10s}: {pattern_count} patterns")
            assert pattern_count >= 3, f"Expected 3+ patterns for {level}, got {pattern_count}"
        else:
            print(f"  ✗ {level:10s}: MISSING")
            assert False, f"Missing complexity level: {level}"

    print("\n✓ PASS: All complexity levels implemented")
    return True


def test_intent_priorities():
    """Test 3: Verify INTENT_TAG_PRIORITY covers all key intents."""
    print("\n" + "="*80)
    print("TEST 3: Intent-Specific Tag Priorities")
    print("="*80)

    required_intents = [
        'find-function',
        'explain-concept',
        'trace-flow',
        'security-check',
        'find-bug',
        'analyze-component',
        'api-usage'
    ]

    print(f"\n📊 INTENT_TAG_PRIORITY mappings:")
    for intent in required_intents:
        if intent in INTENT_TAG_PRIORITY:
            priorities = INTENT_TAG_PRIORITY[intent]
            print(f"  • {intent:20s}: {', '.join(priorities[:3])}")
            assert len(priorities) >= 3, f"Expected 3+ priority tags for {intent}"
        else:
            print(f"  ✗ {intent:20s}: MISSING")
            assert False, f"Missing intent priority: {intent}"

    print("\n✓ PASS: All intent priorities defined")
    return True


def test_complexity_determination():
    """Test 4: Test query complexity determination logic."""
    print("\n" + "="*80)
    print("TEST 4: Query Complexity Determination")
    print("="*80)

    builder = EnrichmentPromptBuilder()

    test_cases = [
        # (question, analysis, num_tags, expected_complexity)
        ("Find function foo", {'intent': 'find-function', 'keywords': ['foo']}, 1, 'simple'),
        ("How does memory allocation work in vacuum?", {'intent': 'explain-concept', 'keywords': ['memory', 'allocation', 'vacuum']}, 3, 'moderate'),
        ("Trace the flow of WAL writes from backend to disk including checkpoints", {'intent': 'trace-flow', 'keywords': ['wal', 'writes', 'backend', 'disk', 'checkpoint']}, 5, 'complex'),
        ("Find security vulnerabilities", {'intent': 'security-check', 'keywords': ['security', 'vulnerability']}, 2, 'complex'),
        ("Find untested complex functions", {'intent': 'find-bug', 'keywords': ['untested', 'complex']}, 2, 'complex'),
    ]

    print(f"\n📊 Complexity determination test cases:")
    for question, analysis, num_tags, expected in test_cases:
        complexity = builder._determine_query_complexity(question, analysis, num_tags)
        status = "✓" if complexity == expected else "✗"
        print(f"  {status} \"{question[:50]}...\"")
        print(f"    Intent: {analysis['intent']}, Tags: {num_tags}")
        print(f"    Expected: {expected}, Got: {complexity}")

        assert complexity == expected, f"Complexity mismatch for '{question}'"

    print("\n✓ PASS: Complexity determination works correctly")
    return True


def test_template_selection():
    """Test 5: Test intent-aware template selection."""
    print("\n" + "="*80)
    print("TEST 5: Intent-Aware Template Selection")
    print("="*80)

    builder = EnrichmentPromptBuilder()

    # Test templates for function-purpose
    templates = TAG_QUERY_PATTERNS['function-purpose']

    test_cases = [
        ('find-function', 'simple', lambda t: '.name.l' in t and 'callIn' not in t),
        ('trace-flow', 'complex', lambda t: 'callIn' in t or 'callOut' in t),
        ('explain-concept', 'moderate', lambda t: 'file' in t or 'callIn' in t),
    ]

    print(f"\n📊 Template selection test cases:")
    for intent, complexity, validator in test_cases:
        selected = builder._select_template_for_intent(templates, intent, complexity)
        is_valid = validator(selected)
        status = "✓" if is_valid else "✗"

        print(f"  {status} Intent: {intent:20s}, Complexity: {complexity:10s}")
        print(f"    Selected: {selected[:80]}...")

        assert is_valid, f"Template validation failed for {intent}/{complexity}"

    print("\n✓ PASS: Template selection works correctly")
    return True


def test_enrichment_context_building():
    """Test 6: Test full enrichment context building with Phase 3 features."""
    print("\n" + "="*80)
    print("TEST 6: Enrichment Context Building (End-to-End)")
    print("="*80)

    builder = EnrichmentPromptBuilder()

    # Mock enrichment hints
    hints = {
        'function_purposes': ['memory-management', 'locking', 'io-operations'],
        'domain_concepts': ['vacuum', 'wal', 'buffer'],
        'subsystems': ['autovacuum', 'storage'],
        'data_structures': ['heap-tuple', 'buffer-page'],
        'cyclomatic_complexity': ['1', '5', '10', '20'],
        'test_coverage': ['untested', 'partial', 'full'],
        'coverage_score': 0.75,
    }

    question = "How does autovacuum handle memory management?"

    analysis = {
        'intent': 'explain-concept',
        'domain': 'vacuum',
        'keywords': ['autovacuum', 'memory', 'management']
    }

    context = builder.build_enrichment_context(hints, question, analysis, max_tags=7, max_patterns=5)

    print(f"\n📊 Generated enrichment context:")
    print("─" * 80)
    print(context)
    print("─" * 80)

    # Validation checks
    assert "ENRICHMENT TAGS" in context, "Should have enrichment tags header"
    assert "Tag Query Patterns" in context, "Should have patterns section"
    assert "complexity" in context.lower(), "Should indicate complexity level"

    # Check that complexity-aware patterns are shown
    assert any(word in context for word in ['simple', 'moderate', 'complex']), \
        "Should show complexity level"

    # Check that specific tag patterns are shown
    assert "cpg.method.where" in context or "cpg.file.where" in context, \
        "Should include specific CPGQL patterns"

    print("\n✓ PASS: Enrichment context building works correctly")
    return True


def test_new_tag_categories():
    """Test 7: Verify new tag categories from Phase 3."""
    print("\n" + "="*80)
    print("TEST 7: New Tag Categories (Phase 3)")
    print("="*80)

    new_categories = [
        'cyclomatic-complexity',
        'test-coverage',
        'refactor-priority',
        'lines-of-code',
        'api-public',
        'api-typical-usage',
        'loop-depth',
    ]

    print(f"\n📊 New tag categories added in Phase 3:")
    for category in new_categories:
        if category in TAG_QUERY_PATTERNS:
            patterns = TAG_QUERY_PATTERNS[category]
            print(f"  ✓ {category:25s} ({len(patterns)} patterns)")

            # Verify each has 2+ patterns
            assert len(patterns) >= 2, f"Expected 2+ patterns for {category}"

            # Show first pattern as example
            print(f"    Example: {patterns[0][:70]}...")
        else:
            print(f"  ✗ {category:25s} MISSING")
            assert False, f"Missing new category: {category}"

    print("\n✓ PASS: All new Phase 3 categories present")
    return True


def test_hybrid_patterns():
    """Test 8: Verify hybrid pattern combinations."""
    print("\n" + "="*80)
    print("TEST 8: Hybrid Pattern Combinations")
    print("="*80)

    assert 'hybrid' in TAG_QUERY_PATTERNS, "Should have hybrid patterns category"

    hybrid_patterns = TAG_QUERY_PATTERNS['hybrid']

    print(f"\n📊 Hybrid patterns ({len(hybrid_patterns)} total):")
    for i, pattern in enumerate(hybrid_patterns, 1):
        # Count number of filters (.where() and .whereNot())
        where_count = pattern.count('.where(') + pattern.count('.whereNot(')

        print(f"  {i}. {pattern[:70]}...")
        print(f"     Filters: {where_count}")

        # Hybrid patterns should have multiple filters (or multiple tag references)
        tag_count = pattern.count('tag.nameExact')
        combined_complexity = where_count >= 2 or tag_count >= 2

        assert combined_complexity, f"Hybrid pattern should have 2+ filters or tags, got where={where_count}, tags={tag_count}"

    print("\n✓ PASS: Hybrid patterns combine multiple tags")
    return True


def run_all_tests():
    """Run all Phase 3 pattern library tests."""
    print("\n" + "="*80)
    print("PHASE 3: QUERY PATTERN LIBRARY TEST SUITE")
    print("="*80)

    tests = [
        ("Pattern Coverage", test_pattern_coverage),
        ("Complexity Patterns", test_complexity_patterns),
        ("Intent Priorities", test_intent_priorities),
        ("Complexity Determination", test_complexity_determination),
        ("Template Selection", test_template_selection),
        ("Enrichment Context Building", test_enrichment_context_building),
        ("New Tag Categories", test_new_tag_categories),
        ("Hybrid Patterns", test_hybrid_patterns),
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
        print("\n🎉 ALL PHASE 3 TESTS PASSED!")
        print("Query pattern library is working correctly!")
        return True
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
