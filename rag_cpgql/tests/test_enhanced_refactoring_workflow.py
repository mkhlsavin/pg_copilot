"""
Test Suite for Enhanced Refactoring Workflow (Week 6, Phase 2)

Tests the specialized refactoring agents and enhanced refactoring_workflow:
- TechnicalDebtDetector
- ImpactAnalyzer
- RefactoringPlanner
- Enhanced refactoring_workflow integration
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
    CodeSmellFinding,
    DependencyInfo,
    ImpactAnalysis,
    RefactoringTask,
    RefactoringReport,
    CodeSmellSeverity,
    CodeSmellCategory,
    REFACTORING_PATTERNS,
)
from src.workflow.multi_scenario_workflow import refactoring_workflow, MultiScenarioState


class TestTechnicalDebtDetector(unittest.TestCase):
    """Test TechnicalDebtDetector agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.detector = TechnicalDebtDetector(self.mock_cpg)

    def test_detect_pattern_basic(self):
        """Test basic pattern detection"""
        # Mock CPG query results for god class pattern
        self.mock_cpg.execute_query.return_value = [
            {
                'filename': 'src/backend/executor/execMain.c',
                'method_count': 45,
                'total_lines': 1500,
                'smell_type': 'GOD_CLASS',
                'severity': 'HIGH'
            },
            {
                'filename': 'src/backend/optimizer/plan/planner.c',
                'method_count': 38,
                'total_lines': 1200,
                'smell_type': 'GOD_CLASS',
                'severity': 'HIGH'
            }
        ]

        # Get a pattern to test
        pattern = REFACTORING_PATTERNS['GOD_CLASS']
        findings = self.detector.detect_pattern(pattern, limit=10)

        # Assertions
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].pattern_name, 'God Class / Large Class')
        self.assertEqual(findings[0].severity, 'high')
        self.assertEqual(findings[0].category, 'bloaters')
        self.assertIn('execMain.c', findings[0].filename)
        self.assertGreater(findings[0].effort_hours, 0)

    def test_detect_all_smells(self):
        """Test detecting all code smells"""
        # Mock CPG to return empty results for all patterns
        self.mock_cpg.execute_query.return_value = []

        findings = self.detector.detect_all_smells(limit_per_pattern=5)

        # Should return empty list since mock returns no results
        self.assertEqual(len(findings), 0)

    def test_calculate_debt_metrics(self):
        """Test technical debt metrics calculation"""
        # Create mock findings
        findings = [
            CodeSmellFinding(
                finding_id='GOD_CLASS_001',
                pattern_id='GOD_CLASS',
                pattern_name='God Class',
                category='bloaters',
                severity='high',
                method_id=1,
                method_name='main_executor',
                filename='backend/executor/execMain.c',
                line_number=100,
                code_snippet='class TooManyMethods { ... }',
                description='Class has 45 methods',
                symptoms=['Too many methods'],
                refactoring_technique='Extract Class',
                effort_hours=8.0,
                metadata={'method_count': 45}
            ),
            CodeSmellFinding(
                finding_id='LONG_METHOD_001',
                pattern_id='LONG_METHOD',
                pattern_name='Long Method',
                category='bloaters',
                severity='critical',
                method_id=2,
                method_name='process_query',
                filename='backend/optimizer/planner.c',
                line_number=500,
                code_snippet='void process_query() { ... 250 lines ... }',
                description='Method has 250 lines',
                symptoms=['Too many lines'],
                refactoring_technique='Extract Method',
                effort_hours=4.0,
                metadata={'line_count': 250}
            ),
            CodeSmellFinding(
                finding_id='DEAD_CODE_001',
                pattern_id='DEAD_CODE',
                pattern_name='Dead Code',
                category='dispensables',
                severity='low',
                method_id=3,
                method_name='unused_function',
                filename='backend/utils/old_code.c',
                line_number=200,
                code_snippet='void unused_function() { ... }',
                description='Function is never called',
                symptoms=['No callers'],
                refactoring_technique='Delete Code',
                effort_hours=0.5,
                metadata={}
            )
        ]

        metrics = self.detector.calculate_debt_metrics(findings)

        # Assertions
        self.assertEqual(metrics['total_smells'], 3)
        self.assertEqual(metrics['total_effort_hours'], 12.5)
        self.assertEqual(metrics['by_severity']['critical'], 1)
        self.assertEqual(metrics['by_severity']['high'], 1)
        self.assertEqual(metrics['by_severity']['low'], 1)
        self.assertEqual(metrics['by_category']['bloaters'], 2)
        self.assertEqual(metrics['by_category']['dispensables'], 1)
        self.assertGreater(metrics['debt_ratio'], 0)
        self.assertLessEqual(metrics['debt_ratio'], 1.0)

    def test_debt_ratio_calculation(self):
        """Test debt ratio calculation"""
        # High debt scenario
        high_debt_findings = [
            CodeSmellFinding(
                f'FINDING_{i}', 'GOD_CLASS', 'God Class', 'bloaters', 'critical',
                i, f'method_{i}', 'file.c', 100, '', '', [], '', 20.0, {}
            )
            for i in range(50)  # 50 findings * 20 hours = 1000 hours
        ]

        metrics = self.detector.calculate_debt_metrics(high_debt_findings)
        self.assertEqual(metrics['debt_ratio'], 1.0)  # Capped at 1.0

        # Low debt scenario
        low_debt_findings = [
            CodeSmellFinding(
                'FINDING_1', 'DEAD_CODE', 'Dead Code', 'dispensables', 'low',
                1, 'method_1', 'file.c', 100, '', '', [], '', 0.5, {}
            )
        ]

        metrics = self.detector.calculate_debt_metrics(low_debt_findings)
        self.assertLess(metrics['debt_ratio'], 0.01)

    def test_detect_by_category(self):
        """Test detecting smells by category"""
        # Mock CPG to return empty results
        self.mock_cpg.execute_query.return_value = []

        from src.refactoring.refactoring_patterns import CodeSmellCategory
        findings = self.detector.detect_by_category(CodeSmellCategory.BLOATERS, limit=10)

        # Should return empty list since mock returns no results
        self.assertEqual(len(findings), 0)


class TestImpactAnalyzer(unittest.TestCase):
    """Test ImpactAnalyzer agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.analyzer = ImpactAnalyzer(self.mock_cpg)

    def test_find_dependencies(self):
        """Test finding method dependencies"""
        self.mock_cpg.execute_query.return_value = [
            {
                'from_method': 'target_method',
                'from_file': 'backend/executor/execMain.c',
                'to_method': 'helper_function',
                'dep_type': 'calls'
            },
            {
                'from_method': 'target_method',
                'from_file': 'backend/executor/execMain.c',
                'to_method': 'another_helper',
                'dep_type': 'calls'
            }
        ]

        deps = self.analyzer.find_dependencies('target_method', depth=1)

        self.assertEqual(len(deps), 2)
        self.assertIsInstance(deps[0], DependencyInfo)
        self.assertEqual(deps[0].to_method, 'helper_function')
        self.assertEqual(deps[0].dependency_type, 'calls')

    def test_analyze_method_impact(self):
        """Test method impact analysis"""
        # Mock direct callers query result, then indirect callers for each direct caller
        self.mock_cpg.execute_query.side_effect = [
            [  # Direct callers
                {'id': 10, 'caller_name': 'func1', 'caller_file': 'f1.c'},
                {'id': 11, 'caller_name': 'func2', 'caller_file': 'f2.c'}
            ],
            [  # Indirect callers for func1
                {'name': 'caller_of_func1'}
            ],
            [  # Indirect callers for func2
                {'name': 'caller_of_func2'}
            ]
        ]

        impact = self.analyzer.analyze_method_impact('target_method', 'target.c')

        # Assertions
        self.assertIsInstance(impact, ImpactAnalysis)
        self.assertEqual(impact.target_method, 'target_method')
        self.assertEqual(impact.target_file, 'target.c')
        self.assertEqual(len(impact.direct_dependents), 2)
        self.assertEqual(impact.direct_dependents[0], 'func1')
        self.assertGreater(impact.impact_score, 0)
        self.assertLessEqual(impact.impact_score, 1.0)
        self.assertIn(impact.risk_level, ['low', 'medium', 'high', 'unknown'])


    def test_analyze_bulk_impact(self):
        """Test bulk impact analysis"""
        findings = [
            CodeSmellFinding(
                'FINDING_1', 'GOD_CLASS', 'God Class', 'bloaters', 'high',
                1, 'executor', 'exec.c', 100, '', '', [], '', 8.0, {'id': 1}
            ),
            CodeSmellFinding(
                'FINDING_2', 'LONG_METHOD', 'Long Method', 'bloaters', 'critical',
                2, 'planner', 'plan.c', 200, '', '', [], '', 4.0, {'id': 2}
            )
        ]

        # Mock the queries for both findings (direct callers + indirect callers for each)
        self.mock_cpg.execute_query.side_effect = [
            # Finding 1: executor
            [{'id': 10, 'caller_name': 'f1', 'caller_file': 'f.c'}],  # direct callers
            [{'name': 'indirect1'}],  # indirect callers for f1
            # Finding 2: planner
            [{'id': 11, 'caller_name': 'f2', 'caller_file': 'f.c'}],  # direct callers
            [{'name': 'indirect2'}],  # indirect callers for f2
        ]

        impacts = self.analyzer.analyze_bulk_impact(findings, limit=10)

        self.assertEqual(len(impacts), 2)
        self.assertIsInstance(impacts[0], ImpactAnalysis)
        self.assertIsInstance(impacts[1], ImpactAnalysis)
        self.assertEqual(impacts[0].target_method, 'executor')
        self.assertEqual(impacts[1].target_method, 'planner')


class TestRefactoringPlanner(unittest.TestCase):
    """Test RefactoringPlanner agent"""

    def setUp(self):
        self.planner = RefactoringPlanner()


    def test_parse_refactoring_steps(self):
        """Test parsing refactoring steps"""
        technique = """1. Extract class
2. Move methods to new class
3. Update references"""

        steps = self.planner._parse_refactoring_steps(technique)

        self.assertEqual(len(steps), 3)
        self.assertIn('Extract class', steps[0])
        self.assertIn('Move methods', steps[1])
        self.assertIn('Update references', steps[2])

    def test_create_refactoring_plan(self):
        """Test creating refactoring plan"""
        findings = [
            CodeSmellFinding(
                'GOD_CLASS_001', 'GOD_CLASS', 'God Class', 'bloaters', 'high',
                1, 'executor', 'exec.c', 100, '', 'Large class', [],
                '1. Extract class\n2. Move methods', 8.0, {}
            ),
            CodeSmellFinding(
                'LONG_METHOD_001', 'LONG_METHOD', 'Long Method', 'bloaters', 'critical',
                2, 'planner', 'plan.c', 200, '', 'Long method', [],
                '1. Extract method\n2. Simplify logic', 4.0, {}
            ),
            CodeSmellFinding(
                'DEAD_CODE_001', 'DEAD_CODE', 'Dead Code', 'dispensables', 'low',
                3, 'unused', 'old.c', 300, '', 'Unused code', [],
                '1. Delete code', 0.5, {}
            )
        ]

        impact_analyses = [
            ImpactAnalysis('IA1', 'executor', 'exec.c', [], [], [], 0.7, 'high', 2.0),
            ImpactAnalysis('IA2', 'planner', 'plan.c', [], [], [], 0.5, 'medium', 1.5),
            ImpactAnalysis('IA3', 'unused', 'old.c', [], [], [], 0.0, 'low', 0.1)
        ]

        tasks = self.planner.create_refactoring_plan(findings, impact_analyses)

        # Assertions
        self.assertEqual(len(tasks), 3)
        self.assertIsInstance(tasks[0], RefactoringTask)

        # Should be sorted by priority (highest first)
        self.assertGreaterEqual(tasks[0].priority, tasks[1].priority)
        self.assertGreaterEqual(tasks[1].priority, tasks[2].priority)

        # Check task structure
        self.assertGreater(len(tasks[0].refactoring_steps), 0)
        self.assertGreater(tasks[0].effort_hours, 0)

    def test_generate_report(self):
        """Test report generation"""
        findings = [
            CodeSmellFinding(
                'GOD_CLASS_001', 'GOD_CLASS', 'God Class', 'bloaters', 'high',
                1, 'executor', 'exec.c', 100, '', 'Large class', [], '', 8.0, {}
            )
        ]

        impact_analyses = [
            ImpactAnalysis('IA1', 'executor', 'exec.c', [], [], [], 0.7, 'high', 2.0)
        ]

        tasks = [
            RefactoringTask(
                task_id='TASK_001',
                finding_id='GOD_CLASS_001',
                pattern_name='God Class',
                target_method='executor',
                target_file='exec.c',
                priority=8,
                effort_hours=8.0,
                impact_score=0.7,
                refactoring_steps=['Extract class', 'Move methods'],
                dependencies=[],
                estimated_value=16.0
            )
        ]

        report = self.planner.generate_report(findings, impact_analyses, tasks)

        # Assertions
        self.assertIsInstance(report, RefactoringReport)
        self.assertEqual(report.total_smells, 1)
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(len(report.impact_analyses), 1)
        self.assertEqual(len(report.tasks), 1)
        self.assertGreater(report.total_effort_hours, 0)
        self.assertGreater(report.estimated_value, 0)
        self.assertGreater(len(report.summary), 0)
        self.assertGreater(len(report.recommendations), 0)


class TestEnhancedRefactoringWorkflow(unittest.TestCase):
    """Test enhanced refactoring_workflow integration"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.TechnicalDebtDetector')
    @patch('src.workflow.multi_scenario_workflow.ImpactAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.RefactoringPlanner')
    def test_enhanced_refactoring_workflow(
        self,
        mock_planner_class,
        mock_analyzer_class,
        mock_detector_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test enhanced refactoring workflow with all agents"""
        # Setup mocks
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Mock TechnicalDebtDetector
        mock_detector = Mock()
        mock_detector.detect_all_smells.return_value = [
            CodeSmellFinding(
                'GOD_CLASS_001', 'GOD_CLASS', 'God Class', 'bloaters', 'high',
                1, 'executor', 'execMain.c', 100, 'class { ... }', 'Large class',
                ['Too many methods'], 'Extract class', 8.0, {'method_count': 45}
            ),
            CodeSmellFinding(
                'LONG_METHOD_001', 'LONG_METHOD', 'Long Method', 'bloaters', 'critical',
                2, 'planner', 'planner.c', 200, 'void func() { ... }', 'Long method',
                ['Too many lines'], 'Extract method', 4.0, {'line_count': 250}
            )
        ]
        mock_detector.calculate_debt_metrics.return_value = {
            'total_smells': 2,
            'total_effort_hours': 12.0,
            'by_severity': {'critical': 1, 'high': 1, 'medium': 0, 'low': 0},
            'by_category': {'bloaters': 2, 'dispensables': 0},
            'debt_ratio': 0.012,
            'avg_effort_per_smell': 6.0
        }
        mock_detector_class.return_value = mock_detector

        # Mock ImpactAnalyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_bulk_impact.return_value = [
            ImpactAnalysis(
                analysis_id='IA1', target_method='executor', target_file='execMain.c',
                direct_dependents=[], indirect_dependents=[], affected_files=['execMain.c', 'executor.c'],
                impact_score=0.7, risk_level='high', estimated_test_effort=2.0
            ),
            ImpactAnalysis(
                analysis_id='IA2', target_method='planner', target_file='planner.c',
                direct_dependents=[], indirect_dependents=[], affected_files=['planner.c'],
                impact_score=0.5, risk_level='medium', estimated_test_effort=1.5
            )
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Mock RefactoringPlanner
        mock_planner = Mock()
        mock_tasks = [
            RefactoringTask(
                task_id='TASK_001',
                finding_id='LONG_METHOD_001',
                pattern_name='Long Method',
                target_method='planner',
                target_file='planner.c',
                priority=9,
                effort_hours=4.0,
                impact_score=0.5,
                refactoring_steps=['Extract method', 'Simplify'],
                dependencies=[],
                estimated_value=18.0
            ),
            RefactoringTask(
                task_id='TASK_002',
                finding_id='GOD_CLASS_001',
                pattern_name='God Class',
                target_method='executor',
                target_file='execMain.c',
                priority=7,
                effort_hours=8.0,
                impact_score=0.7,
                refactoring_steps=['Extract class', 'Move methods'],
                dependencies=[],
                estimated_value=14.0
            )
        ]
        mock_planner.create_refactoring_plan.return_value = mock_tasks

        mock_report = Mock(spec=RefactoringReport)
        mock_report.report_id = 'REFACTOR_REPORT_TEST'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_smells = 2
        mock_report.by_severity = {'critical': 1, 'high': 1, 'medium': 0, 'low': 0}
        mock_report.by_category = {'bloaters': 2, 'dispensables': 0}
        mock_report.findings = mock_detector.detect_all_smells.return_value
        mock_report.impact_analyses = mock_analyzer.analyze_bulk_impact.return_value
        mock_report.tasks = mock_tasks
        mock_report.total_effort_hours = 12.0
        mock_report.estimated_value = 32.0
        mock_report.summary = 'Test refactoring summary'
        mock_report.recommendations = ['Fix god class', 'Simplify long methods']
        mock_planner.generate_report.return_value = mock_report
        mock_planner_class.return_value = mock_planner

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = 'Enhanced refactoring analysis complete. Found 2 code smells.'
        mock_llm_class.return_value = mock_llm

        # Create initial state
        state = MultiScenarioState(
            query='Identify code smells and suggest refactoring',
            context=None,
            intent='refactoring',
            scenario_id='scenario_5',
            cpg_results=[],
            methods=[],
            answer='',
            evidence=[],
            metadata={}
        )

        # Execute workflow
        result = refactoring_workflow(state)

        # Assertions
        self.assertIsNotNone(result)
        self.assertNotIn('error', result)
        self.assertEqual(result['intent'], 'refactoring')
        self.assertGreater(len(result['answer']), 0)
        self.assertGreater(len(result['evidence']), 0)

        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'REFACTOR_REPORT_TEST')
        self.assertEqual(metadata['total_smells'], 2)
        self.assertEqual(metadata['total_effort_hours'], 12.0)
        self.assertEqual(metadata['debt_ratio'], 0.012)
        self.assertTrue(metadata['enhanced_mode'])

        # Verify all agents were called
        mock_detector.detect_all_smells.assert_called_once()
        mock_detector.calculate_debt_metrics.assert_called_once()
        mock_analyzer.analyze_bulk_impact.assert_called_once()
        mock_planner.create_refactoring_plan.assert_called_once()
        mock_planner.generate_report.assert_called_once()
        mock_llm.generate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
