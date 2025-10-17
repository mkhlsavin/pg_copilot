"""Test Enrichment Coverage Improvement

This script tests the enrichment coverage improvements to verify that:
1. Domain coverage has increased (from 38% to 100%)
2. Tags per question have increased (from 3 to 7+)
3. Overall enrichment coverage has improved (target: >0.60 from 0.44)

Usage:
    conda activate llama.cpp
    python test_enrichment_coverage.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.enrichment_agent import EnrichmentAgent


# Test questions covering various domains
TEST_QUESTIONS = [
    # Vacuum domain
    "How does PostgreSQL vacuum work?",
    "What is autovacuum and when does it run?",
    "How does freeze operation work in vacuum?",

    # WAL domain
    "What is the purpose of WAL in PostgreSQL?",
    "How does checkpoint process work?",
    "How does WAL recovery work?",

    # MVCC domain
    "How does MVCC work in PostgreSQL?",
    "What is snapshot isolation?",
    "How does PostgreSQL handle transaction visibility?",

    # Query planning domain
    "How does the query planner work?",
    "What is cost-based optimization?",
    "How does PostgreSQL estimate selectivity?",

    # Memory domain
    "How does PostgreSQL manage memory?",
    "What is a memory context?",
    "How does memory allocation work?",

    # Replication domain
    "How does streaming replication work?",
    "What is logical replication?",
    "How does WAL sender work?",

    # Storage domain
    "How does PostgreSQL store data on disk?",
    "What is TOAST?",
    "How does buffer management work?",

    # Indexes domain
    "How do B-tree indexes work?",
    "What is a bitmap scan?",
    "How does index creation work?",

    # Locking domain
    "How does PostgreSQL handle locking?",
    "What are lock modes?",
    "How does deadlock detection work?",

    # Parallel domain
    "How does parallel query work?",
    "What are worker processes?",
    "How does work stealing work?",

    # JSONB domain
    "How does PostgreSQL store JSONB data?",
    "How are JSONB indexes implemented?",
    "What is JSONB containment?",

    # Background processes
    "What does the postmaster do?",
    "How do background workers work?",
    "What is the checkpointer process?",

    # Security (new)
    "How does SCRAM authentication work?",

    # Partitioning (new)
    "How does table partitioning work?",
]


def test_domain_coverage():
    """Test 1: Verify domain coverage has increased."""
    print("\n" + "="*80)
    print("TEST 1: Domain Coverage")
    print("="*80)

    analyzer = AnalyzerAgent()
    enrichment = EnrichmentAgent()

    # Analyze all test questions and collect domains
    domains_found = set()
    domains_with_enrichment = set()

    for question in TEST_QUESTIONS:
        analysis = analyzer.analyze(question)
        domain = analysis['domain']
        domains_found.add(domain)

        # Get enrichment hints
        hints = enrichment.get_enrichment_hints(question, analysis)

        # Check if domain has any enrichment
        has_enrichment = any([
            hints['subsystems'],
            hints['function_purposes'],
            hints['data_structures'],
            hints['algorithms'],
            hints['domain_concepts']
        ])

        if has_enrichment:
            domains_with_enrichment.add(domain)

    total_domains = len(domains_found)
    enriched_domains = len(domains_with_enrichment)
    coverage_pct = (enriched_domains / total_domains * 100) if total_domains > 0 else 0

    print(f"\n📊 Domain Statistics:")
    print(f"  Total domains found: {total_domains}")
    print(f"  Domains with enrichment: {enriched_domains}")
    print(f"  Domain coverage: {coverage_pct:.1f}%")
    print(f"\n  Domains found: {sorted(domains_found)}")
    print(f"  Enriched domains: {sorted(domains_with_enrichment)}")

    if domains_found - domains_with_enrichment:
        print(f"  ⚠️  Missing enrichment: {sorted(domains_found - domains_with_enrichment)}")

    # Target: 100% domain coverage
    if coverage_pct >= 90:
        print(f"\n✓ PASS: Domain coverage {coverage_pct:.1f}% >= 90%")
        return True
    else:
        print(f"\n✗ FAIL: Domain coverage {coverage_pct:.1f}% < 90%")
        return False


def test_tags_per_question():
    """Test 2: Verify tags per question has increased."""
    print("\n" + "="*80)
    print("TEST 2: Tags Per Question")
    print("="*80)

    analyzer = AnalyzerAgent()
    enrichment = EnrichmentAgent()

    tag_counts = []

    for question in TEST_QUESTIONS[:10]:  # Sample 10 questions
        analysis = analyzer.analyze(question)
        hints = enrichment.get_enrichment_hints(question, analysis)

        tag_count = len(hints.get('tags', []))
        tag_counts.append(tag_count)

        print(f"  Q: {question[:60]}...")
        print(f"     Domain: {analysis['domain']}, Tags: {tag_count}")

    avg_tags = sum(tag_counts) / len(tag_counts) if tag_counts else 0

    print(f"\n📊 Tag Statistics:")
    print(f"  Average tags per question: {avg_tags:.1f}")
    print(f"  Min: {min(tag_counts) if tag_counts else 0}")
    print(f"  Max: {max(tag_counts) if tag_counts else 0}")

    # Target: Average >= 5 tags (increased from 3)
    if avg_tags >= 5:
        print(f"\n✓ PASS: Average tags {avg_tags:.1f} >= 5")
        return True
    else:
        print(f"\n✗ FAIL: Average tags {avg_tags:.1f} < 5")
        return False


def test_enrichment_coverage_score():
    """Test 3: Verify overall enrichment coverage score."""
    print("\n" + "="*80)
    print("TEST 3: Enrichment Coverage Score")
    print("="*80)

    analyzer = AnalyzerAgent()
    enrichment = EnrichmentAgent()

    coverage_scores = []

    for question in TEST_QUESTIONS:
        analysis = analyzer.analyze(question)
        hints = enrichment.get_enrichment_hints(question, analysis)

        coverage = hints.get('coverage_score', 0.0)
        coverage_scores.append(coverage)

    avg_coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0

    print(f"\n📊 Coverage Statistics:")
    print(f"  Average coverage: {avg_coverage:.3f}")
    print(f"  Min: {min(coverage_scores):.3f}")
    print(f"  Max: {max(coverage_scores):.3f}")
    print(f"  Questions with coverage >= 0.6: {sum(1 for c in coverage_scores if c >= 0.6)}/{len(coverage_scores)}")

    # Distribution
    print(f"\n  Coverage distribution:")
    print(f"    0.0-0.2: {sum(1 for c in coverage_scores if 0.0 <= c < 0.2)}")
    print(f"    0.2-0.4: {sum(1 for c in coverage_scores if 0.2 <= c < 0.4)}")
    print(f"    0.4-0.6: {sum(1 for c in coverage_scores if 0.4 <= c < 0.6)}")
    print(f"    0.6-0.8: {sum(1 for c in coverage_scores if 0.6 <= c < 0.8)}")
    print(f"    0.8-1.0: {sum(1 for c in coverage_scores if 0.8 <= c <= 1.0)}")

    # Target: Average coverage >= 0.60 (from 0.44)
    if avg_coverage >= 0.60:
        print(f"\n✓ PASS: Average coverage {avg_coverage:.3f} >= 0.60")
        return True
    else:
        print(f"\n✗ FAIL: Average coverage {avg_coverage:.3f} < 0.60")
        print(f"  Improvement needed: +{0.60 - avg_coverage:.3f}")
        return False


def test_tag_quality():
    """Test 4: Verify tag quality and relevance."""
    print("\n" + "="*80)
    print("TEST 4: Tag Quality & Relevance")
    print("="*80)

    analyzer = AnalyzerAgent()
    enrichment = EnrichmentAgent()

    # Test specific questions with known expected tags
    test_cases = [
        {
            'question': "How does vacuum work?",
            'expected_tags': ['function-purpose', 'domain-concept'],
            'expected_values': ['maintenance', 'vacuum']
        },
        {
            'question': "How does WAL work?",
            'expected_tags': ['function-purpose', 'domain-concept'],
            'expected_values': ['logging', 'wal']
        },
        {
            'question': "How does memory allocation work?",
            'expected_tags': ['function-purpose', 'data-structure'],
            'expected_values': ['memory-management', 'memory-context']
        },
    ]

    passed = 0
    failed = 0

    for tc in test_cases:
        analysis = analyzer.analyze(tc['question'])
        hints = enrichment.get_enrichment_hints(tc['question'], analysis)

        tags = hints.get('tags', [])
        tag_names = {t['tag_name'] for t in tags}
        tag_values = {t['tag_value'].lower() for t in tags}

        print(f"\n  Q: {tc['question']}")
        print(f"     Expected tags: {tc['expected_tags']}")
        print(f"     Found tags: {list(tag_names)[:5]}")

        # Check if expected tags are present
        found_tags = sum(1 for et in tc['expected_tags'] if et in tag_names)
        found_values = sum(1 for ev in tc['expected_values'] if any(ev in tv for tv in tag_values))

        if found_tags >= len(tc['expected_tags']) * 0.5:  # At least 50% match
            print(f"     ✓ Tag types match")
            passed += 1
        else:
            print(f"     ✗ Tag types mismatch")
            failed += 1

    print(f"\n📊 Quality Statistics:")
    print(f"  Test cases passed: {passed}/{len(test_cases)}")

    if passed >= len(test_cases) * 0.7:  # 70% pass rate
        print(f"\n✓ PASS: Tag quality acceptable ({passed}/{len(test_cases)})")
        return True
    else:
        print(f"\n✗ FAIL: Tag quality insufficient ({passed}/{len(test_cases)})")
        return False


def test_prompt_builder_integration():
    """Test 5: Verify EnrichmentPromptBuilder produces good output."""
    print("\n" + "="*80)
    print("TEST 5: EnrichmentPromptBuilder Integration")
    print("="*80)

    from src.agents.enrichment_prompt_builder import EnrichmentPromptBuilder

    analyzer = AnalyzerAgent()
    enrichment = EnrichmentAgent()
    builder = EnrichmentPromptBuilder()

    test_question = "How does PostgreSQL vacuum work?"

    analysis = analyzer.analyze(test_question)
    hints = enrichment.get_enrichment_hints(test_question, analysis)

    # Build enrichment context
    context = builder.build_enrichment_context(
        hints=hints,
        question=test_question,
        analysis=analysis,
        max_tags=7,
        max_patterns=5
    )

    print(f"\n  Question: {test_question}")
    print(f"\n  Generated Context:")
    print("-" * 80)
    print(context)
    print("-" * 80)

    # Verify context contains key elements
    checks = {
        'Has tag emoji': '🏷️' in context,
        'Has patterns': 'cpg.method.where' in context or 'cpg.file.where' in context,
        'Has .tag.nameExact': '.tag.nameExact' in context,
        'Has .valueExact': '.valueExact' in context,
        'Has multiple tags': context.count('.tag.') >= 3,
    }

    print(f"\n📊 Context Quality Checks:")
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")

    passed = sum(checks.values())
    total = len(checks)

    if passed >= total * 0.8:  # 80% pass rate
        print(f"\n✓ PASS: Context quality {passed}/{total}")
        return True
    else:
        print(f"\n✗ FAIL: Context quality {passed}/{total}")
        return False


def run_all_tests():
    """Run all enrichment coverage tests."""
    print("\n" + "="*80)
    print("ENRICHMENT COVERAGE TEST SUITE")
    print("="*80)
    print(f"Testing with {len(TEST_QUESTIONS)} questions across multiple domains")

    tests = [
        ("Domain Coverage", test_domain_coverage),
        ("Tags Per Question", test_tags_per_question),
        ("Enrichment Coverage Score", test_enrichment_coverage_score),
        ("Tag Quality", test_tag_quality),
        ("Prompt Builder Integration", test_prompt_builder_integration),
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
        print("Enrichment coverage improvement successful!")
        return True
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        print("Further improvements needed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
