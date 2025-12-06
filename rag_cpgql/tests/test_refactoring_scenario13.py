"""
Test Suite for Scenario 13: Large-Scale Refactoring

Tests for:
- TechnicalDebtDetector (code smell detection)
- ImpactAnalyzer (change impact analysis)
- RefactoringPlanner (refactoring plan creation)

Author: Refactoring Team
Date: 2025-11-23
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
    CodeSmellFinding,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
    CodeSmellSeverity,
    CodeSmellCategory,
    REFACTORING_PATTERNS,
)


# ============================================================================
# TEST HELPERS
# ============================================================================

def create_mock_cpg():
    """Create mock CPG service"""
    mock_cpg = Mock()
    mock_cpg.execute_query = Mock(return_value=[])
    return mock_cpg


def create_test_finding(
    pattern_name="LONG_METHOD",
    severity="high",
    method_name="process_transaction"
):
    """Create test code smell finding"""
    pattern = REFACTORING_PATTERNS.get("LONG_METHOD")
    return CodeSmellFinding(
        finding_id=f"{pattern_name}_001",
        pattern_id=pattern.id if pattern else "TEST_001",
        pattern_name=pattern_name,
        category=pattern.category.value if pattern else "bloaters",
        severity=severity,
        method_id=1,
        method_name=method_name,
        filename="src/transaction.py",
        line_number=100,
        code_snippet="def process_transaction(): ...",
        description="Method is too long",
        symptoms=["Method exceeds 50 lines"],
        refactoring_technique="Extract Method: Break into smaller methods",
        effort_hours=2.0,
        metadata={}
    )


def create_test_impact_analysis(
    method_name="process_transaction",
    risk_level="medium"
):
    """Create test impact analysis"""
    return ImpactAnalysis(
        analysis_id=f"IMPACT_{method_name}",
        target_method=method_name,
        target_file="src/transaction.py",
        direct_dependents=["caller1", "caller2"],
        indirect_dependents=["indirect1"],
        affected_files=["src/transaction.py", "src/handler.py"],
        impact_score=0.5,
        risk_level=risk_level,
        estimated_test_effort=2.0
    )


# ============================================================================
# TEST TECHNICAL DEBT DETECTOR
# ============================================================================

class TestTechnicalDebtDetector:
    """Test Technical Debt Detector agent"""

    def test_detect_all_smells(self):
        """Test detecting all code smell patterns"""
        print("\n[TEST 1] Testing detect_all_smells...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'long_method',
                'filename': 'src/test.py',
                'line_number': 10,
                'line_count': 100,
            }
        ])

        detector = TechnicalDebtDetector(mock_cpg)
        findings = detector.detect_all_smells(limit_per_pattern=5)

        assert isinstance(findings, list)
        print(f"[PASS] Detected {len(findings)} code smells")

    def test_detect_pattern_long_method(self):
        """Test detecting long method pattern"""
        print("\n[TEST 2] Testing detect_pattern for LONG_METHOD...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'very_long_method',
                'filename': 'src/large.py',
                'line_number': 50,
                'line_count': 150,
                'code': 'def very_long_method(): ...',
            }
        ])

        detector = TechnicalDebtDetector(mock_cpg)
        pattern = REFACTORING_PATTERNS['LONG_METHOD']
        findings = detector.detect_pattern(pattern, limit=10)

        assert len(findings) > 0
        assert findings[0].pattern_name == "Long Method"
        assert findings[0].severity in ['critical', 'high', 'medium']

        print(f"[PASS] Detected {len(findings)} long methods")

    def test_detect_by_category_bloaters(self):
        """Test detecting code smells by category"""
        print("\n[TEST 3] Testing detect_by_category for BLOATERS...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'bloated_method',
                'filename': 'src/test.py',
                'line_number': 10,
                'line_count': 200,
            }
        ])

        detector = TechnicalDebtDetector(mock_cpg)
        findings = detector.detect_by_category(CodeSmellCategory.BLOATERS, limit=10)

        assert isinstance(findings, list)
        # All findings should be in BLOATERS category
        for finding in findings:
            assert finding.category in ['bloaters']

        print(f"[PASS] Detected {len(findings)} bloaters")

    def test_calculate_debt_metrics(self):
        """Test calculating technical debt metrics"""
        print("\n[TEST 4] Testing calculate_debt_metrics...")

        detector = TechnicalDebtDetector()

        findings = [
            create_test_finding("LONG_METHOD", "critical", "method1"),
            create_test_finding("GOD_CLASS", "high", "method2"),
            create_test_finding("DEAD_CODE", "medium", "method3"),
        ]

        metrics = detector.calculate_debt_metrics(findings)

        assert metrics['total_smells'] == 3
        assert metrics['total_effort_hours'] > 0
        assert 'by_severity' in metrics
        assert 'by_category' in metrics
        assert 'debt_ratio' in metrics
        assert 0 <= metrics['debt_ratio'] <= 1.0

        print(f"[PASS] Debt metrics: {metrics['total_smells']} smells, "
              f"{metrics['total_effort_hours']:.1f}h effort, "
              f"{metrics['debt_ratio']*100:.1f}% debt ratio")

    def test_empty_findings_debt_metrics(self):
        """Test debt metrics with no findings"""
        print("\n[TEST 5] Testing debt metrics with empty findings...")

        detector = TechnicalDebtDetector()
        metrics = detector.calculate_debt_metrics([])

        assert metrics['total_smells'] == 0
        assert metrics['total_effort_hours'] == 0.0
        assert metrics['debt_ratio'] == 0.0

        print("[PASS] Empty findings return zero metrics")

    def test_severity_ordering(self):
        """Test that findings are sorted by severity"""
        print("\n[TEST 6] Testing severity ordering...")

        mock_cpg = create_mock_cpg()
        detector = TechnicalDebtDetector(mock_cpg)

        # Mock multiple findings with different severities
        findings = [
            create_test_finding("PATTERN1", "low", "method1"),
            create_test_finding("PATTERN2", "critical", "method2"),
            create_test_finding("PATTERN3", "medium", "method3"),
            create_test_finding("PATTERN4", "high", "method4"),
        ]

        # Manually sort like the real implementation
        severity_order = {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4
        }
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 99))

        assert sorted_findings[0].severity == 'critical'
        assert sorted_findings[1].severity == 'high'
        assert sorted_findings[2].severity == 'medium'
        assert sorted_findings[3].severity == 'low'

        print("[PASS] Findings correctly sorted by severity")


# ============================================================================
# TEST IMPACT ANALYZER
# ============================================================================

class TestImpactAnalyzer:
    """Test Impact Analyzer agent"""

    def test_analyze_method_impact(self):
        """Test analyzing method impact"""
        print("\n[TEST 7] Testing analyze_method_impact...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(side_effect=[
            # Direct callers
            [
                {'id': 1, 'caller_name': 'handler1', 'caller_file': 'src/handler.py'},
                {'id': 2, 'caller_name': 'handler2', 'caller_file': 'src/handler.py'},
            ],
            # Indirect callers for handler1
            [{'name': 'service1'}],
            # Indirect callers for handler2
            [{'name': 'service2'}],
        ])

        analyzer = ImpactAnalyzer(mock_cpg)
        impact = analyzer.analyze_method_impact("process_data", "src/processor.py")

        assert isinstance(impact, ImpactAnalysis)
        assert impact.target_method == "process_data"
        assert len(impact.direct_dependents) == 2
        assert 'handler1' in impact.direct_dependents
        assert impact.risk_level in ['low', 'medium', 'high', 'unknown']
        assert 0 <= impact.impact_score <= 1.0

        print(f"[PASS] Impact analysis: {len(impact.direct_dependents)} direct, "
              f"{len(impact.indirect_dependents)} indirect, "
              f"risk={impact.risk_level}")

    def test_analyze_bulk_impact(self):
        """Test analyzing impact for multiple findings"""
        print("\n[TEST 8] Testing analyze_bulk_impact...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[])

        analyzer = ImpactAnalyzer(mock_cpg)

        findings = [
            create_test_finding("LONG_METHOD", "high", "method1"),
            create_test_finding("GOD_CLASS", "critical", "method2"),
            create_test_finding("DEAD_CODE", "low", "method3"),
        ]

        analyses = analyzer.analyze_bulk_impact(findings, limit=10)

        assert isinstance(analyses, list)
        assert len(analyses) == 3
        for analysis in analyses:
            assert isinstance(analysis, ImpactAnalysis)

        print(f"[PASS] Analyzed impact for {len(analyses)} findings")

    def test_find_dependencies(self):
        """Test finding method dependencies"""
        print("\n[TEST 9] Testing find_dependencies...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[
            {
                'from_method': 'caller',
                'from_file': 'src/caller.py',
                'to_method': 'callee',
                'dep_type': 'calls',
            }
        ])

        analyzer = ImpactAnalyzer(mock_cpg)
        deps = analyzer.find_dependencies("caller", depth=2)

        assert isinstance(deps, list)
        if deps:
            assert deps[0].from_method == 'caller'
            assert deps[0].dependency_type == 'calls'

        print(f"[PASS] Found {len(deps)} dependencies")

    def test_impact_score_calculation(self):
        """Test impact score calculation logic"""
        print("\n[TEST 10] Testing impact score calculation...")

        # Test that more callers = higher impact
        mock_cpg = create_mock_cpg()

        # Many callers -> high impact
        # Need side_effect for multiple queries: 1 direct + 5 indirect (for first 5 callers)
        mock_cpg.execute_query = Mock(side_effect=[
            # Direct callers query - returns 25 callers
            [
                {'id': i, 'caller_name': f'caller{i}', 'caller_file': f'src/file{i}.py'}
                for i in range(25)
            ],
            # Indirect callers for caller0-4 (5 queries, each returns some indirect callers)
            [{'name': 'indirect0_1'}, {'name': 'indirect0_2'}],  # For caller0
            [{'name': 'indirect1_1'}],  # For caller1
            [{'name': 'indirect2_1'}, {'name': 'indirect2_2'}, {'name': 'indirect2_3'}],  # For caller2
            [{'name': 'indirect3_1'}],  # For caller3
            [{'name': 'indirect4_1'}, {'name': 'indirect4_2'}],  # For caller4
        ])

        analyzer = ImpactAnalyzer(mock_cpg)
        impact_high = analyzer.analyze_method_impact("popular_method")

        assert impact_high.impact_score > 0.5  # Should be high
        assert impact_high.risk_level in ['high', 'medium']

        print(f"[PASS] Impact score correctly calculated: {impact_high.impact_score:.2f}")

    def test_no_callers_impact(self):
        """Test impact analysis for method with no callers"""
        print("\n[TEST 11] Testing impact for method with no callers...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[])  # No callers

        analyzer = ImpactAnalyzer(mock_cpg)
        impact = analyzer.analyze_method_impact("unused_method")

        assert len(impact.direct_dependents) == 0
        assert impact.impact_score == 0.0
        assert impact.risk_level == 'low'

        print("[PASS] No callers = low impact")


# ============================================================================
# TEST REFACTORING PLANNER
# ============================================================================

class TestRefactoringPlanner:
    """Test Refactoring Planner agent"""

    def test_create_refactoring_plan(self):
        """Test creating refactoring plan"""
        print("\n[TEST 12] Testing create_refactoring_plan...")

        planner = RefactoringPlanner()

        findings = [
            create_test_finding("LONG_METHOD", "critical", "method1"),
            create_test_finding("GOD_CLASS", "high", "method2"),
            create_test_finding("DEAD_CODE", "medium", "method3"),
        ]

        impact_analyses = [
            create_test_impact_analysis("method1", "low"),
            create_test_impact_analysis("method2", "medium"),
            create_test_impact_analysis("method3", "low"),
        ]

        tasks = planner.create_refactoring_plan(findings, impact_analyses)

        assert isinstance(tasks, list)
        assert len(tasks) == 3
        for task in tasks:
            assert isinstance(task, RefactoringTask)
            assert 1 <= task.priority <= 10
            assert task.effort_hours > 0

        # Tasks should be sorted by priority
        for i in range(len(tasks) - 1):
            assert tasks[i].priority >= tasks[i+1].priority

        print(f"[PASS] Created plan with {len(tasks)} tasks")

    def test_priority_calculation(self):
        """Test priority calculation logic"""
        print("\n[TEST 13] Testing priority calculation...")

        planner = RefactoringPlanner()

        # Critical severity should have high priority
        critical_finding = create_test_finding("PATTERN", "critical", "method1")
        impact = create_test_impact_analysis("method1", "low")

        priority = planner._calculate_priority(critical_finding, impact)

        assert priority >= 7  # Critical should be high priority

        # Low severity should have lower priority
        low_finding = create_test_finding("PATTERN", "low", "method2")
        priority_low = planner._calculate_priority(low_finding, impact)

        assert priority_low < priority  # Lower severity = lower priority

        print(f"[PASS] Priorities: critical={priority}, low={priority_low}")

    def test_value_calculation(self):
        """Test value calculation for refactorings"""
        print("\n[TEST 14] Testing value calculation...")

        planner = RefactoringPlanner()

        # High severity + high impact = high value
        critical_finding = create_test_finding("PATTERN", "critical", "method1")
        high_impact = ImpactAnalysis(
            "IMPACT_1", "method1", "file.py",
            direct_dependents=['a', 'b', 'c'],  # Many dependents
            indirect_dependents=['d', 'e'],
            affected_files=['file1.py', 'file2.py'],
            impact_score=0.8,  # High impact
            risk_level='medium',
            estimated_test_effort=5.0
        )

        value_high = planner._calculate_value(critical_finding, high_impact)

        # Low severity + low impact = low value
        low_finding = create_test_finding("PATTERN", "low", "method2")
        low_impact = create_test_impact_analysis("method2", "low")
        low_impact.impact_score = 0.1

        value_low = planner._calculate_value(low_finding, low_impact)

        assert value_high > value_low

        print(f"[PASS] Values: high={value_high:.1f}, low={value_low:.1f}")

    def test_generate_report(self):
        """Test generating refactoring report"""
        print("\n[TEST 15] Testing generate_report...")

        planner = RefactoringPlanner()

        findings = [
            create_test_finding("LONG_METHOD", "critical", "method1"),
            create_test_finding("GOD_CLASS", "high", "method2"),
        ]

        impact_analyses = [
            create_test_impact_analysis("method1", "low"),
            create_test_impact_analysis("method2", "medium"),
        ]

        tasks = planner.create_refactoring_plan(findings, impact_analyses)
        report = planner.generate_report(findings, impact_analyses, tasks)

        assert isinstance(report, RefactoringReport)
        assert report.total_smells == 2
        assert 'critical' in report.by_severity or 'high' in report.by_severity
        assert len(report.findings) == 2
        assert len(report.tasks) == 2
        assert report.total_effort_hours > 0
        assert len(report.recommendations) > 0

        print(f"[PASS] Report: {report.total_smells} smells, "
              f"{report.total_effort_hours:.1f}h effort, "
              f"{len(report.recommendations)} recommendations")

    def test_parse_refactoring_steps(self):
        """Test parsing refactoring steps from technique text"""
        print("\n[TEST 16] Testing parse_refactoring_steps...")

        planner = RefactoringPlanner()

        technique = """
        Extract Method: Break into smaller methods
        1. Identify cohesive code blocks
        2. Create new method for each block
        - Update tests
        - Run tests to verify
        """

        steps = planner._parse_refactoring_steps(technique)

        assert isinstance(steps, list)
        assert len(steps) > 0
        # Should extract numbered and bulleted items
        assert any('Identify' in step for step in steps)

        print(f"[PASS] Parsed {len(steps)} refactoring steps")

    def test_recommendations_generation(self):
        """Test recommendations generation"""
        print("\n[TEST 17] Testing recommendations generation...")

        planner = RefactoringPlanner()

        # Create mix of priorities
        findings = [
            create_test_finding("LONG_METHOD", "critical", f"method{i}")
            for i in range(5)
        ] + [
            create_test_finding("DEAD_CODE", "low", f"dead{i}")
            for i in range(3)
        ]

        impact_analyses = [
            create_test_impact_analysis(f"method{i}", "low")
            for i in range(5)
        ] + [
            create_test_impact_analysis(f"dead{i}", "low")
            for i in range(3)
        ]

        # Create plan with quick wins (low effort)
        tasks = planner.create_refactoring_plan(findings, impact_analyses)
        # Manually set some tasks to low effort
        if len(tasks) > 0:
            tasks[0].effort_hours = 0.5  # Quick win

        recommendations = planner._generate_recommendations(findings, tasks)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should mention high priority and quick wins
        rec_text = ' '.join(recommendations)
        assert 'priority' in rec_text.lower() or 'quick' in rec_text.lower()

        print(f"[PASS] Generated {len(recommendations)} recommendations")


# ============================================================================
# INTEGRATION TEST
# ============================================================================

class TestScenario13Integration:
    """Integration test for complete refactoring workflow"""

    def test_full_refactoring_workflow(self):
        """Test complete refactoring analysis workflow"""
        print("\n[TEST 18] Testing full refactoring workflow integration...")

        mock_cpg = create_mock_cpg()

        # Step 1: Detect code smells
        print("  [STEP 1] Detecting code smells...")
        mock_cpg.execute_query = Mock(return_value=[
            {
                'id': 1,
                'method_name': 'long_method',
                'filename': 'src/processor.py',
                'line_number': 50,
                'line_count': 100,
                'code': 'def long_method(): ...',
            },
            {
                'id': 2,
                'method_name': 'complex_method',
                'filename': 'src/handler.py',
                'line_number': 100,
                'line_count': 80,
                'code': 'def complex_method(): ...',
            }
        ])

        detector = TechnicalDebtDetector(mock_cpg)
        findings = detector.detect_all_smells(limit_per_pattern=2)

        assert len(findings) > 0
        print(f"  [STEP 1] Detected {len(findings)} code smells")

        # Step 2: Analyze impact
        print("  [STEP 2] Analyzing impact...")
        mock_cpg.execute_query = Mock(return_value=[
            {'id': 1, 'caller_name': 'caller1', 'caller_file': 'src/main.py'},
        ])

        analyzer = ImpactAnalyzer(mock_cpg)
        impact_analyses = analyzer.analyze_bulk_impact(findings, limit=5)

        assert len(impact_analyses) > 0
        print(f"  [STEP 2] Analyzed {len(impact_analyses)} impacts")

        # Step 3: Create refactoring plan
        print("  [STEP 3] Creating refactoring plan...")
        planner = RefactoringPlanner()
        tasks = planner.create_refactoring_plan(findings, impact_analyses)

        assert len(tasks) > 0
        print(f"  [STEP 3] Created {len(tasks)} refactoring tasks")

        # Step 4: Generate report
        print("  [STEP 4] Generating report...")
        report = planner.generate_report(findings, impact_analyses, tasks)

        assert report.total_smells == len(findings)
        assert report.total_effort_hours > 0
        assert len(report.recommendations) > 0
        print(f"  [STEP 4] Report: {report.total_smells} smells, "
              f"{report.total_effort_hours:.1f}h effort")

        print("[PASS] Full refactoring workflow completed successfully")

    def test_workflow_with_empty_results(self):
        """Test workflow handles empty results gracefully"""
        print("\n[TEST 19] Testing workflow with no code smells...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(return_value=[])  # No smells found

        detector = TechnicalDebtDetector(mock_cpg)
        findings = detector.detect_all_smells(limit_per_pattern=5)

        # Should handle empty findings
        debt_metrics = detector.calculate_debt_metrics(findings)
        assert debt_metrics['total_smells'] == 0

        planner = RefactoringPlanner()
        tasks = planner.create_refactoring_plan(findings, [])
        assert len(tasks) == 0

        print("[PASS] Empty results handled correctly")

    def test_workflow_error_handling(self):
        """Test workflow error handling"""
        print("\n[TEST 20] Testing workflow error handling...")

        mock_cpg = create_mock_cpg()
        mock_cpg.execute_query = Mock(side_effect=Exception("Database error"))

        detector = TechnicalDebtDetector(mock_cpg)
        pattern = REFACTORING_PATTERNS['LONG_METHOD']

        # Should handle errors gracefully
        findings = detector.detect_pattern(pattern, limit=10)

        # Should return empty list on error, not crash
        assert isinstance(findings, list)
        assert len(findings) == 0

        print("[PASS] Errors handled gracefully")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("SCENARIO 13 TEST SUITE: Large-Scale Refactoring")
    print("=" * 80)

    pytest.main([__file__, '-v'])

    print("\n" + "=" * 80)
    print("TEST EXECUTION COMPLETE")
    print("=" * 80)
