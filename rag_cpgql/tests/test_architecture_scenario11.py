"""
Comprehensive Test Suite for Scenario 11: Architecture Violation Detection

Tests cover:
1. Pattern library validation (6 patterns)
2. DependencyAnalyzer functionality
3. LayerValidator functionality
4. ArchitectureReporter functionality
5. Integration and workflow tests

Author: Test Team
Date: 2025-11-22
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.architecture import (
    # Patterns
    ARCHITECTURE_PATTERNS,
    PATTERNS_BY_ID,
    PATTERNS_BY_CATEGORY,
    PATTERNS_BY_SEVERITY,
    get_pattern,
    get_patterns_by_category,
    get_patterns_by_severity,
    ViolationSeverity,
    ViolationCategory,

    # Agents
    DependencyAnalyzer,
    LayerValidator,
    ArchitectureReporter,

    # Data structures
    ViolationFinding,
    DependencyAnalysis,
    ArchitectureReport
)


# ============================================================================
# TEST 1-6: PATTERN LIBRARY VALIDATION
# ============================================================================

def test_architecture_pattern_count():
    """Test 1: Verify we have 6 architecture patterns"""
    assert len(ARCHITECTURE_PATTERNS) == 6, f"Expected 6 patterns, got {len(ARCHITECTURE_PATTERNS)}"


def test_pattern_ids_unique():
    """Test 2: Verify all pattern IDs are unique"""
    pattern_ids = [p.pattern_id for p in ARCHITECTURE_PATTERNS]
    assert len(pattern_ids) == len(set(pattern_ids)), "Pattern IDs are not unique"


def test_all_patterns_have_required_fields():
    """Test 3: Verify all patterns have required fields"""
    required_fields = [
        'pattern_id', 'name', 'description', 'category', 'severity',
        'symptoms', 'remediation', 'impact', 'detection_query'
    ]

    for pattern in ARCHITECTURE_PATTERNS:
        for field in required_fields:
            value = getattr(pattern, field)
            assert value, f"Pattern {pattern.pattern_id} missing {field}"


def test_pattern_categories():
    """Test 4: Verify pattern categories are correct"""
    expected_categories = {
        'dependency': 2,  # CIRCULAR_DEPS, UNSTABLE_DEPS
        'layering': 1,    # LAYER_VIOLATION
        'coupling': 2,    # GOD_MODULE, INAPPROPRIATE_INTIMACY
        'cohesion': 1     # FEATURE_ENVY
    }

    for category, expected_count in expected_categories.items():
        patterns = PATTERNS_BY_CATEGORY[category]
        assert len(patterns) == expected_count, \
            f"Category {category}: expected {expected_count}, got {len(patterns)}"


def test_pattern_severities():
    """Test 5: Verify pattern severity distribution"""
    expected_severities = {
        'critical': 1,  # LAYER_VIOLATION
        'high': 3,      # CIRCULAR_DEPS, GOD_MODULE, INAPPROPRIATE_INTIMACY
        'medium': 2,    # UNSTABLE_DEPS, FEATURE_ENVY
        'low': 0
    }

    for severity, expected_count in expected_severities.items():
        patterns = PATTERNS_BY_SEVERITY[severity]
        assert len(patterns) == expected_count, \
            f"Severity {severity}: expected {expected_count}, got {len(patterns)}"


def test_get_pattern_by_id():
    """Test 6: Verify get_pattern() retrieves correct patterns"""
    pattern = get_pattern("CIRCULAR_DEPS")
    assert pattern is not None
    assert pattern.pattern_id == "CIRCULAR_DEPS"
    assert pattern.name == "Circular Dependencies"

    # Test non-existent pattern
    assert get_pattern("NONEXISTENT") is None


# ============================================================================
# TEST 7-10: DEPENDENCY ANALYZER TESTS
# ============================================================================

def test_dependency_analyzer_initialization():
    """Test 7: DependencyAnalyzer initializes correctly"""
    mock_cpg = Mock()
    analyzer = DependencyAnalyzer(mock_cpg)

    assert analyzer.cpg == mock_cpg
    assert len(analyzer.patterns) >= 5  # Should have dependency, coupling, cohesion patterns


def test_dependency_analyzer_detect_pattern():
    """Test 8: DependencyAnalyzer detects patterns correctly"""
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {
            'from_file': 'module_a.c',
            'to_file': 'module_b.c',
            'path': 'module_a.c -> module_b.c -> module_a.c',
            'depth': 2
        },
        {
            'from_file': 'module_x.c',
            'to_file': 'module_y.c',
            'path': 'module_x.c -> module_y.c -> module_x.c',
            'depth': 2
        }
    ]

    analyzer = DependencyAnalyzer(mock_cpg)
    pattern = get_pattern("CIRCULAR_DEPS")

    findings = analyzer.detect_pattern(pattern, limit=10)

    assert len(findings) == 2
    assert findings[0].pattern_id == "CIRCULAR_DEPS"
    assert findings[0].module_a == 'module_a.c'
    assert findings[0].module_b == 'module_b.c'


def test_dependency_analyzer_calculate_metrics():
    """Test 9: DependencyAnalyzer calculates metrics correctly"""
    mock_cpg = Mock()
    analyzer = DependencyAnalyzer(mock_cpg)

    # Create mock findings
    findings = [
        ViolationFinding(
            finding_id="CIRCULAR_DEPS_001",
            pattern_id="CIRCULAR_DEPS",
            pattern_name="Circular Dependencies",
            category="dependency",
            severity="high",
            module_a="module_a.c",
            module_b="module_b.c",
            violation_details="Test circular dep",
            impact_description="Test impact",
            remediation_steps=["Step 1"],
            metadata={'from_file': 'module_a.c', 'to_file': 'module_b.c'}
        ),
        ViolationFinding(
            finding_id="GOD_MODULE_001",
            pattern_id="GOD_MODULE",
            pattern_name="God Modules",
            category="coupling",
            severity="high",
            module_a="god_module.c",
            violation_details="Test god module",
            impact_description="Test impact",
            remediation_steps=["Step 1"],
            metadata={'module_file': 'god_module.c', 'outgoing_dependencies': 25, 'incoming_dependencies': 35}
        )
    ]

    analysis = analyzer.calculate_dependency_metrics(findings)

    assert analysis.total_violations == 2
    assert analysis.violations_by_severity['high'] == 2
    assert analysis.violations_by_category['dependency'] == 1
    assert analysis.violations_by_category['coupling'] == 1
    assert analysis.circular_dependency_count == 1
    assert analysis.god_module_count == 1


def test_dependency_analyzer_detect_all_violations():
    """Test 10: DependencyAnalyzer detects all violation types"""
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {'from_file': 'test.c', 'to_file': 'test2.c', 'path': 'test.c -> test2.c', 'depth': 1}
    ]

    analyzer = DependencyAnalyzer(mock_cpg)
    findings = analyzer.detect_all_violations(limit_per_pattern=5)

    # Should call detect_pattern for each pattern
    assert isinstance(findings, list)
    # Findings should be sorted by severity (critical first)
    if len(findings) > 1:
        severities = [f.severity for f in findings]
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        for i in range(len(severities) - 1):
            assert severity_order[severities[i]] <= severity_order[severities[i + 1]]


# ============================================================================
# TEST 11-13: LAYER VALIDATOR TESTS
# ============================================================================

def test_layer_validator_initialization():
    """Test 11: LayerValidator initializes correctly"""
    mock_cpg = Mock()
    validator = LayerValidator(mock_cpg)

    assert validator.cpg == mock_cpg
    assert len(validator.layer_hierarchy) > 0
    assert 'presentation' in validator.layer_hierarchy
    assert 'business' in validator.layer_hierarchy
    assert 'data' in validator.layer_hierarchy


def test_layer_validator_validate_rule():
    """Test 12: LayerValidator validates layer rules correctly"""
    mock_cpg = Mock()
    validator = LayerValidator(mock_cpg)

    # Valid: presentation can call business (higher -> lower)
    assert validator.validate_layer_rule('presentation', 'business') == True

    # Valid: business can call data (higher -> lower)
    assert validator.validate_layer_rule('business', 'data') == True

    # Invalid: data cannot call presentation (lower -> higher)
    assert validator.validate_layer_rule('data', 'presentation') == False

    # Invalid: data cannot call business (lower -> higher)
    assert validator.validate_layer_rule('data', 'business') == False


def test_layer_validator_get_layer_metrics():
    """Test 13: LayerValidator calculates layer metrics correctly"""
    mock_cpg = Mock()
    validator = LayerValidator(mock_cpg)

    # Create mock layering violations
    findings = [
        ViolationFinding(
            finding_id="LAYER_001",
            pattern_id="LAYER_VIOLATION",
            pattern_name="Layering Violations",
            category="layering",
            severity="critical",
            module_a="data_layer.c",
            module_b="presentation_layer.c",
            violation_details="data -> presentation",
            impact_description="Test",
            remediation_steps=["Fix it"],
            metadata={'caller_layer': 'data', 'callee_layer': 'presentation'}
        ),
        ViolationFinding(
            finding_id="LAYER_002",
            pattern_id="LAYER_VIOLATION",
            pattern_name="Layering Violations",
            category="layering",
            severity="critical",
            module_a="data_layer.c",
            module_b="business_layer.c",
            violation_details="data -> business",
            impact_description="Test",
            remediation_steps=["Fix it"],
            metadata={'caller_layer': 'data', 'callee_layer': 'business'}
        )
    ]

    metrics = validator.get_layer_metrics(findings)

    assert metrics['total_violations'] == 2
    assert metrics['unique_layer_pairs'] == 2
    assert 'data -> presentation' in metrics['violations_by_layer_pair']


# ============================================================================
# TEST 14-16: ARCHITECTURE REPORTER TESTS
# ============================================================================

def test_architecture_reporter_initialization():
    """Test 14: ArchitectureReporter initializes correctly"""
    reporter = ArchitectureReporter()
    assert reporter is not None


def test_architecture_reporter_generate_report():
    """Test 15: ArchitectureReporter generates comprehensive reports"""
    reporter = ArchitectureReporter()

    # Create mock findings
    findings = [
        ViolationFinding(
            finding_id="TEST_001",
            pattern_id="CIRCULAR_DEPS",
            pattern_name="Circular Dependencies",
            category="dependency",
            severity="high",
            module_a="module_a.c",
            module_b="module_b.c",
            violation_details="Test violation",
            impact_description="Test impact",
            remediation_steps=["Step 1", "Step 2"],
            metadata={}
        ),
        ViolationFinding(
            finding_id="TEST_002",
            pattern_id="LAYER_VIOLATION",
            pattern_name="Layering Violations",
            category="layering",
            severity="critical",
            module_a="data.c",
            module_b="ui.c",
            violation_details="Test violation",
            impact_description="Test impact",
            remediation_steps=["Step 1"],
            metadata={}
        )
    ]

    # Create mock dependency analysis
    dependency_analysis = DependencyAnalysis(
        analysis_id="test123",
        timestamp="2025-11-22",
        total_modules=10,
        total_violations=2,
        violations_by_severity={'critical': 1, 'high': 1},
        violations_by_category={'dependency': 1, 'layering': 1},
        circular_dependency_count=1,
        god_module_count=0,
        module_metrics=[],
        high_coupling_modules=[]
    )

    report = reporter.generate_report(findings, dependency_analysis)

    assert report.total_violations == 2
    assert report.by_severity['critical'] == 1
    assert report.by_severity['high'] == 1
    assert report.by_category['dependency'] == 1
    assert report.by_category['layering'] == 1
    assert len(report.summary) > 0
    assert len(report.recommendations) > 0
    assert len(report.remediation_actions) == 2


def test_architecture_reporter_create_remediation_plan():
    """Test 16: ArchitectureReporter creates prioritized remediation plans"""
    reporter = ArchitectureReporter()

    findings = [
        ViolationFinding(
            finding_id="CRITICAL_001",
            pattern_id="LAYER_VIOLATION",
            pattern_name="Layering Violations",
            category="layering",
            severity="critical",
            module_a="module_a.c",
            module_b="module_b.c",
            violation_details="Test",
            impact_description="Test",
            remediation_steps=["Fix"],
            metadata={}
        ),
        ViolationFinding(
            finding_id="LOW_001",
            pattern_id="FEATURE_ENVY",
            pattern_name="Feature Envy",
            category="cohesion",
            severity="medium",
            module_a="module_c.c",
            module_b="module_d.c",
            violation_details="Test",
            impact_description="Test",
            remediation_steps=["Fix"],
            metadata={}
        )
    ]

    actions = reporter.create_remediation_plan(findings)

    assert len(actions) == 2
    # Should be sorted by priority (highest first)
    assert actions[0].priority >= actions[1].priority
    # Critical should have higher priority
    assert actions[0].finding_id == "CRITICAL_001"
    assert actions[0].priority == 10  # Critical + layering boost


# ============================================================================
# TEST 17: INTEGRATION TEST
# ============================================================================

def test_full_architecture_workflow_integration():
    """Test 17: Full integration test of architecture violation detection"""
    # Mock CPG service
    mock_cpg = Mock()
    mock_cpg.execute_custom_sql.return_value = [
        {
            'from_file': 'auth.c',
            'to_file': 'db.c',
            'path': 'auth.c -> db.c -> auth.c',
            'depth': 2
        }
    ]

    # Test full workflow
    # 1. Detect violations with DependencyAnalyzer
    analyzer = DependencyAnalyzer(mock_cpg)
    dependency_findings = analyzer.detect_all_violations(limit_per_pattern=10)
    dependency_analysis = analyzer.calculate_dependency_metrics(dependency_findings)

    # 2. Validate layers with LayerValidator
    validator = LayerValidator(mock_cpg)
    layering_findings = validator.validate_all_layers(limit=10)
    layer_metrics = validator.get_layer_metrics(layering_findings)

    # 3. Combine findings
    all_findings = dependency_findings + layering_findings

    # 4. Generate report with ArchitectureReporter
    reporter = ArchitectureReporter()
    report = reporter.generate_report(all_findings, dependency_analysis, layer_metrics)

    # Validate report
    assert report.total_violations >= 0
    assert report.report_id
    assert report.timestamp
    assert isinstance(report.summary, str)
    assert isinstance(report.recommendations, list)
    assert isinstance(report.remediation_actions, list)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SCENARIO 11: ARCHITECTURE VIOLATION DETECTION - TEST SUITE")
    print("=" * 80)
    print()

    # Run all tests
    test_functions = [
        # Pattern tests (1-6)
        ("Test 1: Pattern count", test_architecture_pattern_count),
        ("Test 2: Pattern IDs unique", test_pattern_ids_unique),
        ("Test 3: Required fields", test_all_patterns_have_required_fields),
        ("Test 4: Pattern categories", test_pattern_categories),
        ("Test 5: Pattern severities", test_pattern_severities),
        ("Test 6: Get pattern by ID", test_get_pattern_by_id),

        # DependencyAnalyzer tests (7-10)
        ("Test 7: DependencyAnalyzer init", test_dependency_analyzer_initialization),
        ("Test 8: Detect pattern", test_dependency_analyzer_detect_pattern),
        ("Test 9: Calculate metrics", test_dependency_analyzer_calculate_metrics),
        ("Test 10: Detect all violations", test_dependency_analyzer_detect_all_violations),

        # LayerValidator tests (11-13)
        ("Test 11: LayerValidator init", test_layer_validator_initialization),
        ("Test 12: Validate rules", test_layer_validator_validate_rule),
        ("Test 13: Layer metrics", test_layer_validator_get_layer_metrics),

        # ArchitectureReporter tests (14-16)
        ("Test 14: Reporter init", test_architecture_reporter_initialization),
        ("Test 15: Generate report", test_architecture_reporter_generate_report),
        ("Test 16: Remediation plan", test_architecture_reporter_create_remediation_plan),

        # Integration test (17)
        ("Test 17: Full integration", test_full_architecture_workflow_integration),
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
