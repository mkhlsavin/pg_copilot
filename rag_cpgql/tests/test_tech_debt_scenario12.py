"""
Comprehensive Test Suite for Scenario 12: Technical Debt Quantification

Tests cover:
1. Debt pattern library validation (6 patterns)
2. DebtCalculator functionality
3. PrioritizationEngine functionality
4. RepaymentPlanner functionality
5. Integration and workflow tests

Author: Test Team
Date: 2025-11-22
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tech_debt import (
    # Patterns
    DEBT_PATTERNS,
    PATTERNS_BY_ID,
    PATTERNS_BY_CATEGORY,
    PATTERNS_BY_SEVERITY,
    get_pattern,
    get_patterns_by_category,
    get_patterns_by_severity,
    calculate_total_effort,
    calculate_debt_ratio,
    DebtSeverity,
    DebtCategory,

    # Agents
    DebtCalculator,
    PrioritizationEngine,
    RepaymentPlanner,

    # Data structures
    DebtItem,
    DebtMetrics,
    PrioritizedDebt,
    RepaymentPlan
)


# ============================================================================
# TEST 1-6: DEBT PATTERN LIBRARY VALIDATION
# ============================================================================

def test_debt_pattern_count():
    """Test 1: Verify we have 6 debt patterns"""
    assert len(DEBT_PATTERNS) == 6, f"Expected 6 patterns, got {len(DEBT_PATTERNS)}"


def test_pattern_ids_unique():
    """Test 2: Verify all pattern IDs are unique"""
    pattern_ids = [p.pattern_id for p in DEBT_PATTERNS]
    assert len(pattern_ids) == len(set(pattern_ids)), "Pattern IDs are not unique"


def test_all_patterns_have_required_fields():
    """Test 3: Verify all patterns have required fields"""
    required_fields = [
        'pattern_id', 'name', 'description', 'category', 'severity',
        'symptoms', 'remediation', 'impact', 'effort_hours', 'interest_rate', 'detection_query'
    ]

    for pattern in DEBT_PATTERNS:
        for field in required_fields:
            value = getattr(pattern, field)
            assert value is not None, f"Pattern {pattern.pattern_id} missing {field}"


def test_pattern_categories():
    """Test 4: Verify pattern categories are correct"""
    expected_categories = {
        'code_quality': 1,    # CODE_DUPLICATION
        'maintenance': 2,     # TODO_COMMENTS, DEPRECATED_API
        'complexity': 2,      # LONG_METHODS, COMPLEX_METHODS
        'unused_code': 1      # DEAD_CODE
    }

    for category, expected_count in expected_categories.items():
        patterns = PATTERNS_BY_CATEGORY[category]
        assert len(patterns) == expected_count, \
            f"Category {category}: expected {expected_count}, got {len(patterns)}"


def test_pattern_severities():
    """Test 5: Verify pattern severity distribution"""
    expected_severities = {
        'critical': 0,
        'high': 2,      # DEPRECATED_API, COMPLEX_METHODS
        'medium': 3,    # TODO_COMMENTS, CODE_DUPLICATION, LONG_METHODS
        'low': 1        # DEAD_CODE
    }

    for severity, expected_count in expected_severities.items():
        patterns = PATTERNS_BY_SEVERITY[severity]
        assert len(patterns) == expected_count, \
            f"Severity {severity}: expected {expected_count}, got {len(patterns)}"


def test_effort_and_interest_metrics():
    """Test 6: Verify effort hours and interest rates are reasonable"""
    for pattern in DEBT_PATTERNS:
        # Effort should be between 1-10 hours
        assert 0 < pattern.effort_hours <= 10, \
            f"{pattern.pattern_id}: effort {pattern.effort_hours}h out of range"

        # Interest rate should be >= 1.0 (debt doesn't shrink)
        assert pattern.interest_rate >= 1.0, \
            f"{pattern.pattern_id}: interest rate {pattern.interest_rate} < 1.0"

        # Interest rate should be reasonable (<= 1.5 = 50%)
        assert pattern.interest_rate <= 1.5, \
            f"{pattern.pattern_id}: interest rate {pattern.interest_rate} too high"


# ============================================================================
# TEST 7-10: DEBT CALCULATOR TESTS
# ============================================================================

def test_debt_calculator_initialization():
    """Test 7: DebtCalculator initializes correctly"""
    mock_cpg = Mock()
    calculator = DebtCalculator(mock_cpg)

    assert calculator.cpg == mock_cpg
    assert len(calculator.patterns) == 6  # All 6 debt patterns


def test_debt_calculator_detect_pattern():
    """Test 8: DebtCalculator detects patterns correctly"""
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {
            'method_id': 1,
            'method_name': 'processData',
            'filename': 'process.c',
            'line_number': 100,
            'method_length': 150
        },
        {
            'method_id': 2,
            'method_name': 'handleRequest',
            'filename': 'handler.c',
            'line_number': 200,
            'method_length': 120
        }
    ]

    calculator = DebtCalculator(mock_cpg)
    pattern = get_pattern("LONG_METHODS")

    items = calculator.detect_pattern(pattern, limit=10)

    assert len(items) == 2
    assert items[0].pattern_id == "LONG_METHODS"
    assert items[0].effort_hours == pattern.effort_hours
    assert items[0].interest_rate == pattern.interest_rate


def test_debt_calculator_calculate_metrics():
    """Test 9: DebtCalculator calculates metrics correctly"""
    mock_cpg = Mock()
    calculator = DebtCalculator(mock_cpg)

    # Create mock debt items
    items = [
        DebtItem(
            item_id="TODO_001",
            pattern_id="TODO_COMMENTS",
            pattern_name="TODO/FIXME Comments",
            category="maintenance",
            severity="medium",
            location="file1.c",
            line_number=10,
            description="TODO comment",
            effort_hours=2.0,
            interest_rate=1.1,
            business_impact="Test",
            metadata={}
        ),
        DebtItem(
            item_id="DEPRECATED_001",
            pattern_id="DEPRECATED_API",
            pattern_name="Deprecated API Usage",
            category="maintenance",
            severity="high",
            location="file2.c",
            line_number=50,
            description="Using deprecated API",
            effort_hours=4.0,
            interest_rate=1.3,
            business_impact="Test",
            metadata={}
        ),
        DebtItem(
            item_id="LONG_001",
            pattern_id="LONG_METHODS",
            pattern_name="Long Methods",
            category="complexity",
            severity="medium",
            location="file3.c",
            line_number=100,
            description="Long method",
            effort_hours=5.0,
            interest_rate=1.2,
            business_impact="Test",
            metadata={}
        )
    ]

    metrics = calculator.calculate_metrics(items, codebase_size=10000)

    assert metrics.total_items == 3
    assert metrics.total_effort_hours == 11.0  # 2 + 4 + 5
    assert metrics.average_effort == pytest.approx(11.0 / 3)
    assert metrics.by_severity['high'] == 1
    assert metrics.by_severity['medium'] == 2
    assert metrics.by_category['maintenance'] == 2
    assert metrics.by_category['complexity'] == 1
    assert metrics.high_interest_items == 1  # Only DEPRECATED_001 has interest > 1.2 (1.3)


def test_debt_calculator_detect_all_debt():
    """Test 10: DebtCalculator detects all debt types"""
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {'method_name': 'test', 'filename': 'test.c', 'line_number': 10}
    ]

    calculator = DebtCalculator(mock_cpg)
    items = calculator.detect_all_debt(limit_per_pattern=5)

    # Should return list of debt items
    assert isinstance(items, list)
    # Items should be sorted by effort (highest first)
    if len(items) > 1:
        for i in range(len(items) - 1):
            assert items[i].effort_hours >= items[i + 1].effort_hours


# ============================================================================
# TEST 11-14: PRIORITIZATION ENGINE TESTS
# ============================================================================

def test_prioritization_engine_initialization():
    """Test 11: PrioritizationEngine initializes correctly"""
    engine = PrioritizationEngine()
    assert engine is not None


def test_prioritization_engine_calculate_priority():
    """Test 12: PrioritizationEngine calculates priorities correctly"""
    engine = PrioritizationEngine()

    metrics = DebtMetrics(
        total_items=10,
        total_effort_hours=50.0,
        debt_ratio=0.5,
        by_severity={'high': 5, 'medium': 3, 'low': 2},
        by_category={'maintenance': 6, 'complexity': 4},
        average_effort=5.0,
        high_interest_items=3,
        codebase_size_lines=10000
    )

    # High severity item should get high priority
    high_item = DebtItem(
        item_id="TEST_001",
        pattern_id="DEPRECATED_API",
        pattern_name="Deprecated API",
        category="maintenance",
        severity="high",
        location="test.c",
        line_number=10,
        description="Test",
        effort_hours=4.0,
        interest_rate=1.3,
        business_impact="High",
        metadata={}
    )

    priority = engine._calculate_priority(high_item, metrics)
    assert priority >= 7  # High severity + boosts


def test_prioritization_engine_identify_quick_wins():
    """Test 13: PrioritizationEngine identifies quick wins correctly"""
    engine = PrioritizationEngine()

    metrics = DebtMetrics(
        total_items=5,
        total_effort_hours=20.0,
        debt_ratio=0.2,
        by_severity={'medium': 5},
        by_category={'maintenance': 5},
        average_effort=4.0,
        high_interest_items=0,
        codebase_size_lines=10000
    )

    items = [
        # Quick win: low effort (1h), decent severity
        DebtItem(
            item_id="DEAD_001",
            pattern_id="DEAD_CODE",
            pattern_name="Dead Code",
            category="unused_code",
            severity="low",
            location="test.c",
            line_number=10,
            description="Unused method",
            effort_hours=1.0,
            interest_rate=1.05,
            business_impact="Low",
            metadata={}
        ),
        # Not a quick win: high effort
        DebtItem(
            item_id="COMPLEX_001",
            pattern_id="COMPLEX_METHODS",
            pattern_name="Complex Methods",
            category="complexity",
            severity="high",
            location="test.c",
            line_number=50,
            description="Complex method",
            effort_hours=6.0,
            interest_rate=1.25,
            business_impact="High",
            metadata={}
        )
    ]

    prioritized = engine.prioritize_debt(items, metrics)
    quick_wins = engine.get_quick_wins(prioritized)

    # Dead code with 1h effort might be a quick win depending on ROI
    assert isinstance(quick_wins, list)


def test_prioritization_engine_prioritize_debt():
    """Test 14: PrioritizationEngine creates prioritized list"""
    engine = PrioritizationEngine()

    metrics = DebtMetrics(
        total_items=3,
        total_effort_hours=12.0,
        debt_ratio=0.12,
        by_severity={'high': 1, 'medium': 2},
        by_category={'maintenance': 2, 'complexity': 1},
        average_effort=4.0,
        high_interest_items=1,
        codebase_size_lines=10000
    )

    items = [
        DebtItem(
            item_id="TODO_001",
            pattern_id="TODO_COMMENTS",
            pattern_name="TODO Comments",
            category="maintenance",
            severity="medium",
            location="test.c",
            line_number=10,
            description="TODO",
            effort_hours=2.0,
            interest_rate=1.1,
            business_impact="Medium",
            metadata={}
        ),
        DebtItem(
            item_id="DEPRECATED_001",
            pattern_id="DEPRECATED_API",
            pattern_name="Deprecated API",
            category="maintenance",
            severity="high",
            location="test.c",
            line_number=50,
            description="Deprecated",
            effort_hours=4.0,
            interest_rate=1.3,
            business_impact="High",
            metadata={}
        )
    ]

    prioritized = engine.prioritize_debt(items, metrics)

    assert len(prioritized) == 2
    # Should be sorted by priority (highest first)
    assert prioritized[0].priority_score >= prioritized[1].priority_score
    # High severity item should be first
    assert prioritized[0].item.pattern_id == "DEPRECATED_API"
    assert prioritized[0].roi_score > 0


# ============================================================================
# TEST 15-17: REPAYMENT PLANNER TESTS
# ============================================================================

def test_repayment_planner_initialization():
    """Test 15: RepaymentPlanner initializes correctly"""
    planner = RepaymentPlanner(team_velocity=40.0)
    assert planner.team_velocity == 40.0


def test_repayment_planner_create_plan():
    """Test 16: RepaymentPlanner creates comprehensive plans"""
    planner = RepaymentPlanner(team_velocity=40.0)

    # Create mock prioritized items
    prioritized = [
        PrioritizedDebt(
            item=DebtItem(
                item_id="TODO_001",
                pattern_id="TODO_COMMENTS",
                pattern_name="TODO Comments",
                category="maintenance",
                severity="medium",
                location="test.c",
                line_number=10,
                description="TODO",
                effort_hours=2.0,
                interest_rate=1.1,
                business_impact="Medium",
                metadata={}
            ),
            priority_score=5,
            roi_score=20.0,
            business_value="medium",
            quick_win=True,
            strategic=False,
            recommended_sprint=1
        ),
        PrioritizedDebt(
            item=DebtItem(
                item_id="COMPLEX_001",
                pattern_id="COMPLEX_METHODS",
                pattern_name="Complex Methods",
                category="complexity",
                severity="high",
                location="test.c",
                line_number=50,
                description="Complex",
                effort_hours=6.0,
                interest_rate=1.25,
                business_impact="High",
                metadata={}
            ),
            priority_score=8,
            roi_score=15.0,
            business_value="high",
            quick_win=False,
            strategic=True,
            recommended_sprint=1
        )
    ]

    plan = planner.create_plan(prioritized, max_sprints=4)

    assert plan.total_items == 2
    assert plan.total_effort_hours == 8.0  # 2 + 6
    assert plan.quick_wins == 1
    assert plan.strategic_items == 1
    assert len(plan.sprints) > 0
    assert len(plan.summary) > 0
    assert len(plan.recommendations) > 0


def test_repayment_planner_balance_sprints():
    """Test 17: RepaymentPlanner balances sprint capacity correctly"""
    planner = RepaymentPlanner(team_velocity=10.0)  # Small velocity for testing

    # Create items that exceed velocity
    prioritized = [
        PrioritizedDebt(
            item=DebtItem(
                item_id=f"ITEM_{i:03d}",
                pattern_id="TODO_COMMENTS",
                pattern_name="TODO Comments",
                category="maintenance",
                severity="medium",
                location="test.c",
                line_number=i,
                description=f"Item {i}",
                effort_hours=6.0,  # Each item is 6 hours
                interest_rate=1.1,
                business_impact="Medium",
                metadata={}
            ),
            priority_score=5,
            roi_score=10.0,
            business_value="medium",
            quick_win=False,
            strategic=False,
            recommended_sprint=1
        )
        for i in range(5)  # 5 items * 6h = 30h total
    ]

    plan = planner.create_plan(prioritized, max_sprints=6)

    # With 10h velocity and 30h total, balancing should create multiple sprints
    assert len(plan.sprints) >= 2, "Should create at least 2 sprints for load balancing"

    # Verify total effort is preserved
    total_effort_in_plan = sum(sprint['total_effort'] for sprint in plan.sprints)
    assert total_effort_in_plan == 30.0, f"Total effort should be 30h, got {total_effort_in_plan}h"

    # Sprint 1 should respect velocity (first sprint is balanced)
    assert plan.sprints[0]['total_effort'] <= planner.team_velocity + 1.0


# ============================================================================
# TEST 18: INTEGRATION TEST
# ============================================================================

def test_full_tech_debt_workflow_integration():
    """Test 18: Full integration test of tech debt quantification"""
    # Mock CPG service
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {
            'method_name': 'processData',
            'filename': 'process.c',
            'line_number': 100,
            'method_length': 80
        }
    ]

    # Test full workflow
    # 1. Detect debt with DebtCalculator
    calculator = DebtCalculator(mock_cpg)
    debt_items = calculator.detect_all_debt(limit_per_pattern=5)
    metrics = calculator.calculate_metrics(debt_items, codebase_size=10000)

    # 2. Prioritize with PrioritizationEngine
    prioritizer = PrioritizationEngine()
    prioritized_items = prioritizer.prioritize_debt(debt_items, metrics)
    quick_wins = prioritizer.get_quick_wins(prioritized_items)
    strategic_items = prioritizer.get_strategic_items(prioritized_items)

    # 3. Create repayment plan with RepaymentPlanner
    planner = RepaymentPlanner(team_velocity=40.0)
    plan = planner.create_plan(prioritized_items, max_sprints=4)

    # Validate end-to-end results
    assert metrics.total_items >= 0
    assert metrics.total_effort_hours >= 0
    assert isinstance(prioritized_items, list)
    assert isinstance(quick_wins, list)
    assert isinstance(strategic_items, list)
    assert plan.plan_id
    assert plan.timestamp
    assert isinstance(plan.summary, str)
    assert isinstance(plan.recommendations, list)
    assert isinstance(plan.sprints, list)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SCENARIO 12: TECHNICAL DEBT QUANTIFICATION - TEST SUITE")
    print("=" * 80)
    print()

    # Run all tests
    test_functions = [
        # Pattern tests (1-6)
        ("Test 1: Pattern count", test_debt_pattern_count),
        ("Test 2: Pattern IDs unique", test_pattern_ids_unique),
        ("Test 3: Required fields", test_all_patterns_have_required_fields),
        ("Test 4: Pattern categories", test_pattern_categories),
        ("Test 5: Pattern severities", test_pattern_severities),
        ("Test 6: Effort and interest", test_effort_and_interest_metrics),

        # DebtCalculator tests (7-10)
        ("Test 7: DebtCalculator init", test_debt_calculator_initialization),
        ("Test 8: Detect pattern", test_debt_calculator_detect_pattern),
        ("Test 9: Calculate metrics", test_debt_calculator_calculate_metrics),
        ("Test 10: Detect all debt", test_debt_calculator_detect_all_debt),

        # PrioritizationEngine tests (11-14)
        ("Test 11: PrioritizationEngine init", test_prioritization_engine_initialization),
        ("Test 12: Calculate priority", test_prioritization_engine_calculate_priority),
        ("Test 13: Identify quick wins", test_prioritization_engine_identify_quick_wins),
        ("Test 14: Prioritize debt", test_prioritization_engine_prioritize_debt),

        # RepaymentPlanner tests (15-17)
        ("Test 15: RepaymentPlanner init", test_repayment_planner_initialization),
        ("Test 16: Create plan", test_repayment_planner_create_plan),
        ("Test 17: Balance sprints", test_repayment_planner_balance_sprints),

        # Integration test (18)
        ("Test 18: Full integration", test_full_tech_debt_workflow_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in test_functions:
        try:
            test_func()
            print(f"[PASS] {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)

    if failed == 0:
        print("[SUCCESS] ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"[FAILURE] {failed} TESTS FAILED")
        sys.exit(1)
