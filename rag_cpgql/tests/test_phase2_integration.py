"""
Phase 2 End-to-End Integration Test Suite

Tests the complete integration of all Phase 2 enhanced workflows:
- Week 5: Enhanced Security Audit (security_workflow)
- Week 6: Enhanced Refactoring (refactoring_workflow)
- Week 7: Enhanced Performance Analysis (performance_workflow)

This test suite validates that all three enhanced workflows work correctly
with the multi-scenario graph and produce expected outputs.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.multi_scenario_workflow import (
    security_workflow,
    refactoring_workflow,
    performance_workflow,
    MultiScenarioState
)


class TestPhase2SecurityIntegration(unittest.TestCase):
    """Integration tests for Enhanced Security Workflow (Week 5)"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.SecurityScanner')
    @patch('src.workflow.multi_scenario_workflow.DataFlowAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.VulnerabilityReporter')
    @patch('src.workflow.multi_scenario_workflow.RemediationAdvisor')
    def test_security_workflow_end_to_end(
        self,
        mock_advisor_class,
        mock_reporter_class,
        mock_dataflow_class,
        mock_scanner_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test complete security workflow execution"""
        # Setup CPG mock
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Setup SecurityScanner mock
        mock_scanner = Mock()
        from src.security import SecurityFinding
        mock_scanner.scan_all_vulnerabilities.return_value = [
            SecurityFinding(
                finding_id='SQL_INJ_001',
                pattern_id='SQL_INJECTION',
                pattern_name='SQL Injection',
                category='injection',
                severity='critical',
                method_id=1,
                method_name='execute_query',
                filename='db.c',
                line_number=100,
                code_snippet='sprintf(query...)',
                description='User input in SQL',
                cwe_ids=['CWE-89'],
                confidence=0.9,
                metadata={'cve': 'CVE-2021-12345'}
            )
        ]
        mock_scanner.calculate_security_metrics.return_value = {
            'total_vulnerabilities': 1,
            'critical_count': 1,
            'by_severity': {'critical': 1},
            'by_category': {'injection': 1}
        }
        mock_scanner_class.return_value = mock_scanner

        # Setup DataFlowAnalyzer mock
        mock_dataflow = Mock()
        from src.security import DataFlowPath
        mock_dataflow.analyze_bulk_dataflows.return_value = [
            DataFlowPath(
                'DF1', 'execute_query', 'user_input', 'sql_query', 'tainted',
                ['user_input', 'sprintf', 'sql_query'], ['validate_input'],
                'User input reaches SQL query without validation', 'high'
            )
        ]
        mock_dataflow_class.return_value = mock_dataflow

        # Setup VulnerabilityReporter mock
        mock_reporter = Mock()
        from src.security import VulnerabilityReport
        mock_report = Mock(spec=VulnerabilityReport)
        mock_report.report_id = 'SEC_REPORT_001'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_vulnerabilities = 1
        mock_report.critical_count = 1
        mock_report.by_severity = {'critical': 1}
        mock_report.by_category = {'injection': 1}
        mock_report.findings_by_category = {'injection': 1}  # Add this for the workflow
        mock_report.summary = 'Found 1 critical SQL injection vulnerability'
        mock_report.risk_score = 9.5
        mock_report.compliance_issues = []
        mock_reporter.generate_report.return_value = mock_report
        mock_reporter_class.return_value = mock_reporter

        # Setup RemediationAdvisor mock
        mock_advisor = Mock()
        from src.security import RemediationAdvice
        mock_advisor.create_remediation_plan.return_value = [
            RemediationAdvice(
                'REM_001', 'SQL_INJ_001', 'execute_query', 'db.c', 'critical',
                ['Use prepared statements', 'Add input validation'], '// Code example',
                'medium', 9, 'medium', ['Update all SQL calls'], 'Before next release'
            )
        ]
        mock_advisor_class.return_value = mock_advisor

        # Setup LLM mock
        mock_llm = Mock()
        mock_llm.generate.return_value = "Security analysis complete"
        mock_llm_class.return_value = mock_llm

        # Execute workflow
        state = {
            'query': 'Find security vulnerabilities in the database layer',
            'intent': 'security_audit'
        }
        result = security_workflow(state)

        # Assertions
        self.assertIn('answer', result)
        self.assertIn('evidence', result)
        self.assertIn('metadata', result)

        # Verify metadata structure
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'SEC_REPORT_001')
        self.assertEqual(metadata['total_vulnerabilities'], 1)
        self.assertEqual(metadata['critical_count'], 1)
        self.assertTrue(metadata['enhanced_mode'])

        # Verify all agents were called
        mock_scanner.scan_all_vulnerabilities.assert_called_once()
        mock_dataflow.analyze_bulk_dataflows.assert_called_once()
        mock_reporter.generate_report.assert_called_once()
        mock_advisor.create_remediation_plan.assert_called_once()
        mock_llm.generate.assert_called_once()


class TestPhase2RefactoringIntegration(unittest.TestCase):
    """Integration tests for Enhanced Refactoring Workflow (Week 6)"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.TechnicalDebtDetector')
    @patch('src.workflow.multi_scenario_workflow.ImpactAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.RefactoringPlanner')
    def test_refactoring_workflow_end_to_end(
        self,
        mock_planner_class,
        mock_analyzer_class,
        mock_detector_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test complete refactoring workflow execution"""
        # Setup CPG mock
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Setup TechnicalDebtDetector mock
        mock_detector = Mock()
        from src.refactoring import CodeSmellFinding
        mock_detector.detect_all_smells.return_value = [
            CodeSmellFinding(
                'GOD_CLASS_001', 'GOD_CLASS', 'God Class', 'bloaters', 'high',
                1, 'ExecutorMain', 'execMain.c', 100, 'class { ... }', 'Too many methods',
                ['High complexity'], 'Extract class', 8.0, {'method_count': 45}
            )
        ]
        mock_detector.calculate_debt_metrics.return_value = {
            'total_smells': 1,
            'total_effort_hours': 8.0,
            'by_severity': {'high': 1},
            'by_category': {'bloaters': 1},
            'debt_ratio': 0.008,
            'avg_effort_per_smell': 8.0
        }
        mock_detector_class.return_value = mock_detector

        # Setup ImpactAnalyzer mock
        mock_analyzer = Mock()
        from src.refactoring import ImpactAnalysis
        mock_analyzer.analyze_bulk_impact.return_value = [
            ImpactAnalysis(
                'IA1', 'ExecutorMain', 'execMain.c', [], [], ['execMain.c', 'executor.c'],
                0.6, 'medium', 1.5
            )
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Setup RefactoringPlanner mock
        mock_planner = Mock()
        from src.refactoring import RefactoringTask, RefactoringReport
        mock_planner.create_refactoring_plan.return_value = [
            RefactoringTask(
                'TASK_001', 'GOD_CLASS_001', 'God Class', 'ExecutorMain', 'execMain.c',
                8, 8.0, 0.6, ['Extract class', 'Move methods'], [], 16.0
            )
        ]

        mock_report = Mock(spec=RefactoringReport)
        mock_report.report_id = 'REFACTOR_REPORT_001'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_smells = 1
        mock_report.by_severity = {'high': 1}
        mock_report.by_category = {'bloaters': 1}
        mock_report.total_effort_hours = 8.0
        mock_report.debt_ratio = 0.008
        mock_report.summary = 'Found 1 code smell'
        mock_report.recommendations = ['Refactor God Class']
        mock_report.estimated_value = 16.0
        mock_planner.generate_report.return_value = mock_report
        mock_planner_class.return_value = mock_planner

        # Setup LLM mock
        mock_llm = Mock()
        mock_llm.generate.return_value = "Refactoring analysis complete"
        mock_llm_class.return_value = mock_llm

        # Execute workflow
        state = {
            'query': 'Identify code smells in the executor',
            'intent': 'refactoring'
        }
        result = refactoring_workflow(state)

        # Assertions
        self.assertIn('answer', result)
        self.assertIn('evidence', result)
        self.assertIn('metadata', result)

        # Verify metadata structure
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'REFACTOR_REPORT_001')
        self.assertEqual(metadata['total_smells'], 1)
        self.assertEqual(metadata['total_effort_hours'], 8.0)
        self.assertTrue(metadata['enhanced_mode'])

        # Verify all agents were called
        mock_detector.detect_all_smells.assert_called_once()
        mock_analyzer.analyze_bulk_impact.assert_called_once()
        mock_planner.create_refactoring_plan.assert_called_once()
        mock_planner.generate_report.assert_called_once()
        mock_llm.generate.assert_called_once()


class TestPhase2PerformanceIntegration(unittest.TestCase):
    """Integration tests for Enhanced Performance Workflow (Week 7)"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.PerformanceProfiler')
    @patch('src.workflow.multi_scenario_workflow.ResourceAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.OptimizationAdvisor')
    def test_performance_workflow_end_to_end(
        self,
        mock_advisor_class,
        mock_analyzer_class,
        mock_profiler_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test complete performance workflow execution"""
        # Setup CPG mock
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Setup PerformanceProfiler mock
        mock_profiler = Mock()
        from src.performance import BottleneckFinding
        mock_profiler.profile_all_bottlenecks.return_value = [
            BottleneckFinding(
                'NESTED_LOOPS_001', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
                1, 'sortData', 'sort.c', 100, 'for { for { } }', 'O(n²) complexity',
                ['Slow with large data'], 'Use quicksort', 'O(n²) to O(n log n) - up to 100x',
                {'complexity': 25}
            )
        ]
        mock_profiler.calculate_performance_metrics.return_value = {
            'total_bottlenecks': 1,
            'critical_count': 0,
            'by_severity': {'high': 1},
            'by_category': {'algorithmic': 1}
        }
        mock_profiler_class.return_value = mock_profiler

        # Setup ResourceAnalyzer mock
        mock_analyzer = Mock()
        from src.performance import ResourceUsage
        mock_analyzer.analyze_bulk_resources.return_value = [
            ResourceUsage('RA1', 'sortData', 'sort.c', 25, 5, 'high', 'high', 2, 0.7)
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Setup OptimizationAdvisor mock
        mock_advisor = Mock()
        from src.performance import OptimizationRecommendation, PerformanceReport
        mock_advisor.create_optimization_plan.return_value = [
            OptimizationRecommendation(
                'REC_001', 'NESTED_LOOPS_001', 'NESTED_LOOPS',
                ['Replace bubble sort with quicksort'], 'quicksort(array, 0, n-1)',
                'O(n²) to O(n log n) - up to 100x', 'medium', 8, 'medium'
            )
        ]

        mock_report = Mock(spec=PerformanceReport)
        mock_report.report_id = 'PERF_REPORT_001'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_bottlenecks = 1
        mock_report.by_severity = {'high': 1}
        mock_report.by_category = {'algorithmic': 1}
        mock_report.total_potential_speedup = 'Up to 100x for algorithmic improvements'
        mock_report.summary = 'Found 1 algorithmic bottleneck'
        mock_report.action_items = ['Optimize sorting algorithm']
        mock_advisor.generate_report.return_value = mock_report
        mock_advisor_class.return_value = mock_advisor

        # Setup LLM mock
        mock_llm = Mock()
        mock_llm.generate.return_value = "Performance analysis complete"
        mock_llm_class.return_value = mock_llm

        # Execute workflow
        state = {
            'query': 'Find performance bottlenecks in sorting',
            'intent': 'performance_optimization'
        }
        result = performance_workflow(state)

        # Assertions
        self.assertIn('answer', result)
        self.assertIn('evidence', result)
        self.assertIn('metadata', result)

        # Verify metadata structure
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'PERF_REPORT_001')
        self.assertEqual(metadata['total_bottlenecks'], 1)
        self.assertIn('100x', metadata['total_potential_speedup'])
        self.assertTrue(metadata['enhanced_mode'])

        # Verify all agents were called
        mock_profiler.profile_all_bottlenecks.assert_called_once()
        mock_analyzer.analyze_bulk_resources.assert_called_once()
        mock_advisor.create_optimization_plan.assert_called_once()
        mock_advisor.generate_report.assert_called_once()
        mock_llm.generate.assert_called_once()


class TestPhase2CrossWorkflowIntegration(unittest.TestCase):
    """Cross-workflow integration tests for Phase 2"""

    def test_all_workflows_use_enhanced_mode_flag(self):
        """Verify all Phase 2 workflows set enhanced_mode flag in metadata"""
        # This is a smoke test to verify consistency across all workflows
        # Each workflow should set enhanced_mode: True in metadata

        # Security workflow
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService'), \
             patch('src.workflow.multi_scenario_workflow.LLMInterface'), \
             patch('src.workflow.multi_scenario_workflow.SecurityScanner') as mock_scanner, \
             patch('src.workflow.multi_scenario_workflow.DataFlowAnalyzer'), \
             patch('src.workflow.multi_scenario_workflow.VulnerabilityReporter') as mock_reporter, \
             patch('src.workflow.multi_scenario_workflow.RemediationAdvisor'):

            mock_scanner.return_value.scan_all_vulnerabilities.return_value = []
            mock_scanner.return_value.calculate_security_metrics.return_value = {
                'total_vulnerabilities': 0, 'critical_count': 0,
                'by_severity': {}, 'by_category': {}
            }

            mock_report = Mock()
            mock_report.report_id = 'TEST'
            mock_report.total_vulnerabilities = 0
            mock_report.critical_count = 0
            mock_report.by_severity = {}
            mock_report.by_category = {}
            mock_report.findings_by_category = {}  # Required by workflow
            mock_report.findings = []
            mock_report.remediation_plans = []
            mock_report.recommendations = []  # Add this missing attribute
            mock_report.total_findings = 0  # Add this
            mock_report.high_count = 0  # Add this
            mock_report.medium_count = 0  # Add this
            mock_report.low_count = 0  # Add this
            mock_report.summary = 'Test security summary'  # Add this
            mock_reporter.return_value.generate_report.return_value = mock_report

            state = {'query': 'test', 'intent': 'security_audit'}
            result = security_workflow(state)
            self.assertTrue(result['metadata'].get('enhanced_mode', False),
                          "Security workflow should set enhanced_mode=True")

        # Refactoring workflow
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService'), \
             patch('src.workflow.multi_scenario_workflow.LLMInterface'), \
             patch('src.workflow.multi_scenario_workflow.TechnicalDebtDetector') as mock_detector, \
             patch('src.workflow.multi_scenario_workflow.ImpactAnalyzer'), \
             patch('src.workflow.multi_scenario_workflow.RefactoringPlanner') as mock_planner:

            mock_detector.return_value.detect_all_smells.return_value = []
            mock_detector.return_value.calculate_debt_metrics.return_value = {
                'total_smells': 0, 'total_effort_hours': 0,
                'by_severity': {}, 'by_category': {},
                'debt_ratio': 0, 'avg_effort_per_smell': 0
            }

            mock_report = Mock()
            mock_report.report_id = 'TEST'
            mock_report.total_smells = 0
            mock_report.by_severity = {}
            mock_report.by_category = {}
            mock_report.total_effort_hours = 0
            mock_report.debt_ratio = 0
            mock_report.recommendations = []  # Add this missing attribute
            mock_report.estimated_value = 0  # Add this
            mock_report.summary = 'Test refactoring summary'  # Add this
            mock_planner.return_value.create_refactoring_plan.return_value = []
            mock_planner.return_value.generate_report.return_value = mock_report

            state = {'query': 'test', 'intent': 'refactoring'}
            result = refactoring_workflow(state)
            self.assertTrue(result['metadata'].get('enhanced_mode', False),
                          "Refactoring workflow should set enhanced_mode=True")

        # Performance workflow
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService'), \
             patch('src.workflow.multi_scenario_workflow.LLMInterface'), \
             patch('src.workflow.multi_scenario_workflow.PerformanceProfiler') as mock_profiler, \
             patch('src.workflow.multi_scenario_workflow.ResourceAnalyzer'), \
             patch('src.workflow.multi_scenario_workflow.OptimizationAdvisor') as mock_advisor:

            mock_profiler.return_value.profile_all_bottlenecks.return_value = []
            mock_profiler.return_value.calculate_performance_metrics.return_value = {
                'total_bottlenecks': 0, 'critical_count': 0,
                'by_severity': {}, 'by_category': {}
            }

            mock_report = Mock()
            mock_report.report_id = 'TEST'
            mock_report.total_bottlenecks = 0
            mock_report.by_severity = {}
            mock_report.by_category = {}
            mock_report.total_potential_speedup = 'Test speedup'  # Add this
            mock_report.action_items = []  # Add this
            mock_report.summary = 'Test performance summary'  # Add this
            mock_advisor.return_value.create_optimization_plan.return_value = []
            mock_advisor.return_value.generate_report.return_value = mock_report

            state = {'query': 'test', 'intent': 'performance_optimization'}
            result = performance_workflow(state)
            self.assertTrue(result['metadata'].get('enhanced_mode', False),
                          "Performance workflow should set enhanced_mode=True")

    def test_workflow_error_handling(self):
        """Verify all workflows handle errors gracefully"""
        # Security workflow error handling
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService') as mock_cpg:
            mock_cpg.return_value.__enter__.side_effect = Exception("CPG connection failed")

            state = {'query': 'test', 'intent': 'security_audit'}
            result = security_workflow(state)

            self.assertIn('error', result)
            self.assertIn('answer', result)
            self.assertIn('Error during enhanced security audit', result['answer'])

        # Refactoring workflow error handling
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService') as mock_cpg:
            mock_cpg.return_value.__enter__.side_effect = Exception("CPG connection failed")

            state = {'query': 'test', 'intent': 'refactoring'}
            result = refactoring_workflow(state)

            self.assertIn('error', result)
            self.assertIn('answer', result)
            self.assertIn('Error during enhanced refactoring', result['answer'])

        # Performance workflow error handling
        with patch('src.workflow.multi_scenario_workflow.CPGQueryService') as mock_cpg:
            mock_cpg.return_value.__enter__.side_effect = Exception("CPG connection failed")

            state = {'query': 'test', 'intent': 'performance_optimization'}
            result = performance_workflow(state)

            self.assertIn('error', result)
            self.assertIn('answer', result)
            self.assertIn('Error during enhanced performance', result['answer'])


if __name__ == '__main__':
    unittest.main()
