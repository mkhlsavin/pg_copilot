"""
Test Suite for Enhanced Security Workflow (Week 5, Phase 2)

Tests the specialized security agents and enhanced security_workflow:
- SecurityScanner
- DataFlowAnalyzer
- VulnerabilityReporter
- RemediationAdvisor
- Enhanced security_workflow integration
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.security import (
    SecurityScanner,
    DataFlowAnalyzer,
    VulnerabilityReporter,
    RemediationAdvisor,
    SecurityFinding,
    DataFlowPath,
    VulnerabilityReport,
    RemediationAdvice,
    VulnerabilitySeverity,
    VulnerabilityCategory,
    SECURITY_PATTERNS,
)
from src.workflow.multi_scenario_workflow import security_workflow, MultiScenarioState


class TestSecurityScanner(unittest.TestCase):
    """Test SecurityScanner agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.scanner = SecurityScanner(self.mock_cpg)

    def test_scan_pattern_basic(self):
        """Test basic pattern scanning"""
        # Mock CPG query results
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 1,
                'method_name': 'unsafe_function',
                'filename': 'backend/utils/format.c',
                'line_number': 100,
                'code': 'strcpy(dest, src);'
            },
            {
                'id': 2,
                'method_name': 'another_unsafe',
                'filename': 'backend/parser/parse.c',
                'line_number': 200,
                'code': 'strcat(buffer, input);'
            }
        ]

        # Get a pattern to test
        pattern = SECURITY_PATTERNS['BUFFER_OVERFLOW_STRCPY']
        findings = self.scanner.scan_pattern(pattern, limit=10)

        # Assertions
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].pattern_name, 'Buffer Overflow via strcpy/strcat')
        self.assertEqual(findings[0].severity, 'critical')
        self.assertEqual(findings[0].method_name, 'unsafe_function')
        self.assertIn('CWE-120', findings[0].cwe_ids)

    def test_scan_all_patterns(self):
        """Test scanning with all patterns"""
        # Mock CPG to return empty results for all patterns
        self.mock_cpg.execute_query.return_value = []

        findings = self.scanner.scan_all_patterns(limit_per_pattern=5)

        # Should return empty list since mock returns no results
        self.assertEqual(len(findings), 0)

    def test_scan_critical_only(self):
        """Test scanning only critical patterns"""
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 1,
                'method_name': 'sql_vulnerable',
                'filename': 'src/backend/commands/explain.c',
                'line_number': 500,
                'code': 'sprintf(query, "SELECT * FROM %s", table);'
            }
        ]

        findings = self.scanner.scan_critical_only(limit=10)

        # Should only return critical findings
        for finding in findings:
            self.assertEqual(finding.severity, 'critical')

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # Test result with no validation keywords - higher confidence
        result_no_validation = {
            'filename': 'backend/utils/format.c',
            'complexity': 5,
            'code': 'strcpy(dest, src);'
        }

        pattern = SECURITY_PATTERNS['BUFFER_OVERFLOW_STRCPY']
        confidence1 = self.scanner._calculate_confidence(result_no_validation, pattern)
        self.assertGreater(confidence1, 0.5)

        # Test result with validation keywords - lower confidence
        result_with_validation = {
            'filename': 'backend/utils/format.c',
            'complexity': 5,
            'code': 'if (validate_input(src)) strcpy(dest, src);'
        }

        confidence2 = self.scanner._calculate_confidence(result_with_validation, pattern)
        self.assertLess(confidence2, confidence1)

        # Test file lower confidence
        result_test_file = {
            'filename': 'src/test/regress/sql/test_buffer.sql',
            'complexity': 5,
            'code': 'strcpy(dest, src);'
        }

        confidence3 = self.scanner._calculate_confidence(result_test_file, pattern)
        self.assertLess(confidence3, 0.5)


class TestDataFlowAnalyzer(unittest.TestCase):
    """Test DataFlowAnalyzer agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.analyzer = DataFlowAnalyzer(self.mock_cpg)

    def test_find_taint_sources(self):
        """Test finding taint sources"""
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 1,
                'method_name': 'handle_user_input',
                'full_name': 'void handle_user_input(char *input)',
                'filename': 'backend/tcop/postgres.c',
                'line_number': 1000,
                'tag': 'SECURITY_TAINT_SOURCE',
                'category': 2
            },
            {
                'id': 2,
                'method_name': 'read_client_data',
                'full_name': 'int read_client_data()',
                'filename': 'backend/libpq/pqcomm.c',
                'line_number': 500,
                'tag': 'SECURITY_INPUT_HANDLER',
                'category': 2
            }
        ]

        sources = self.analyzer.find_taint_sources(limit=50)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]['method_name'], 'handle_user_input')
        self.assertIn('TAINT_SOURCE', sources[0]['tag'])

    def test_find_taint_sinks(self):
        """Test finding taint sinks"""
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 10,
                'method_name': 'execute_sql_query',
                'full_name': 'void execute_sql_query(char *query)',
                'filename': 'backend/executor/execMain.c',
                'line_number': 2000,
                'sink_function': 'exec_simple_query'
            },
            {
                'id': 11,
                'method_name': 'run_system_command',
                'full_name': 'int run_system_command(char *cmd)',
                'filename': 'backend/utils/adt/genfile.c',
                'line_number': 300,
                'sink_function': 'system'
            }
        ]

        sinks = self.analyzer.find_taint_sinks(limit=50)

        self.assertEqual(len(sinks), 2)
        self.assertEqual(sinks[0]['sink_function'], 'exec_simple_query')
        self.assertEqual(sinks[1]['sink_function'], 'system')

    def test_trace_taint_flows(self):
        """Test tracing taint flows"""
        # Mock taint sources
        self.mock_cpg.execute_query.side_effect = [
            [  # Sources
                {
                    'id': 1,
                    'method_name': 'handle_input',
                    'filename': 'backend/tcop/postgres.c',
                    'line_number': 100,
                    'tag': 'SECURITY_TAINT_SOURCE',
                    'category': 2
                }
            ],
            [  # Sinks
                {
                    'id': 2,
                    'method_name': 'exec_query',
                    'filename': 'backend/executor/execMain.c',
                    'line_number': 200,
                    'sink_function': 'exec_simple_query'
                }
            ]
        ]

        flows = self.analyzer.trace_taint_flows(limit=10)

        self.assertGreater(len(flows), 0)
        self.assertIsInstance(flows[0], DataFlowPath)
        self.assertEqual(flows[0].source_method, 'handle_input')
        self.assertEqual(flows[0].sink_method, 'exec_query')

    def test_classify_taint_type(self):
        """Test taint type classification"""
        source_input = {'tag': 'SECURITY_INPUT_HANDLER', 'method_name': 'read_input'}
        taint_type = self.analyzer._classify_taint_type(source_input)
        self.assertEqual(taint_type, 'user_input')

        source_network = {'tag': 'NETWORK_HANDLER', 'method_name': 'recv_data'}
        taint_type = self.analyzer._classify_taint_type(source_network)
        self.assertEqual(taint_type, 'network_data')

        source_file = {'tag': 'FILE_IO', 'method_name': 'file_read'}
        taint_type = self.analyzer._classify_taint_type(source_file)
        self.assertEqual(taint_type, 'file_data')


class TestVulnerabilityReporter(unittest.TestCase):
    """Test VulnerabilityReporter agent"""

    def setUp(self):
        self.reporter = VulnerabilityReporter()

    def test_generate_report(self):
        """Test vulnerability report generation"""
        # Create mock findings
        findings = [
            SecurityFinding(
                finding_id='TEST_001',
                pattern_id='SQL_INJECTION_001',
                pattern_name='SQL Injection',
                category='injection',
                severity='critical',
                method_id=1,
                method_name='build_query',
                filename='backend/executor/execMain.c',
                line_number=100,
                code_snippet='sprintf(query, "SELECT * FROM %s", table);',
                description='SQL injection vulnerability',
                cwe_ids=['CWE-89'],
                confidence=0.9,
                metadata={}
            ),
            SecurityFinding(
                finding_id='TEST_002',
                pattern_id='BUFFER_OVERFLOW_001',
                pattern_name='Buffer Overflow',
                category='buffer_overflow',
                severity='high',
                method_id=2,
                method_name='copy_string',
                filename='backend/utils/format.c',
                line_number=200,
                code_snippet='strcpy(dest, src);',
                description='Buffer overflow via strcpy',
                cwe_ids=['CWE-120'],
                confidence=0.85,
                metadata={}
            )
        ]

        # Create mock data flows
        data_flows = [
            DataFlowPath(
                path_id='FLOW_001',
                source_method='handle_input',
                source_file='backend/tcop/postgres.c',
                source_line=100,
                sink_method='exec_query',
                sink_file='backend/executor/execMain.c',
                sink_line=200,
                path_length=2,
                intermediate_nodes=[],
                taint_type='user_input',
                sanitized=False
            )
        ]

        report = self.reporter.generate_report(findings, data_flows)

        # Assertions
        self.assertIsInstance(report, VulnerabilityReport)
        self.assertEqual(report.total_findings, 2)
        self.assertEqual(report.critical_count, 1)
        self.assertEqual(report.high_count, 1)
        self.assertEqual(len(report.data_flows), 1)
        self.assertIn('injection', report.findings_by_category)
        self.assertIn('buffer_overflow', report.findings_by_category)
        self.assertGreater(len(report.summary), 0)
        self.assertGreater(len(report.recommendations), 0)

    def test_count_by_severity(self):
        """Test severity counting"""
        findings = [
            SecurityFinding('1', 'P1', 'Test', 'injection', 'critical', 1, 'f1', 'file.c', 1, '', '', ['CWE-1'], 0.9, {}),
            SecurityFinding('2', 'P2', 'Test', 'injection', 'critical', 2, 'f2', 'file.c', 2, '', '', ['CWE-2'], 0.9, {}),
            SecurityFinding('3', 'P3', 'Test', 'memory_safety', 'high', 3, 'f3', 'file.c', 3, '', '', ['CWE-3'], 0.8, {}),
            SecurityFinding('4', 'P4', 'Test', 'input_validation', 'medium', 4, 'f4', 'file.c', 4, '', '', ['CWE-4'], 0.7, {}),
        ]

        counts = self.reporter._count_by_severity(findings)

        self.assertEqual(counts['critical'], 2)
        self.assertEqual(counts['high'], 1)
        self.assertEqual(counts['medium'], 1)


class TestRemediationAdvisor(unittest.TestCase):
    """Test RemediationAdvisor agent"""

    def setUp(self):
        self.advisor = RemediationAdvisor()

    def test_get_remediation_advice(self):
        """Test getting remediation advice for a finding"""
        finding = SecurityFinding(
            finding_id='SQL_INJECTION_001_001',
            pattern_id='SQL_INJECTION_001',
            pattern_name='SQL Injection via String Concatenation',
            category='injection',
            severity='critical',
            method_id=1,
            method_name='build_user_query',
            filename='backend/executor/execMain.c',
            line_number=100,
            code_snippet='sprintf(query, "SELECT * FROM users WHERE name=\'%s\'", user_input);',
            description='SQL injection vulnerability',
            cwe_ids=['CWE-89'],
            confidence=0.95,
            metadata={}
        )

        advice = self.advisor.get_remediation_advice(finding)

        # Assertions
        self.assertIsInstance(advice, RemediationAdvice)
        self.assertEqual(advice.finding_id, 'SQL_INJECTION_001_001')
        self.assertEqual(advice.pattern_id, 'SQL_INJECTION_001')
        self.assertGreater(len(advice.remediation_steps), 0)
        self.assertGreater(len(advice.code_example), 0)
        self.assertGreater(advice.priority, 0)
        self.assertIn(advice.estimated_effort, ['low', 'medium', 'high'])

    def test_calculate_priority(self):
        """Test priority calculation"""
        critical_finding = SecurityFinding(
            '1', 'P1', 'Test', 'injection', 'critical', 1, 'f', 'file.c', 1, '', '', ['CWE-89'], 1.0, {}
        )
        priority_critical = self.advisor._calculate_priority(critical_finding)
        self.assertGreaterEqual(priority_critical, 8)

        low_finding = SecurityFinding(
            '2', 'P2', 'Test', 'input_validation', 'low', 2, 'f', 'file.c', 2, '', '', ['CWE-20'], 0.5, {}
        )
        priority_low = self.advisor._calculate_priority(low_finding)
        self.assertLess(priority_low, priority_critical)

    def test_estimate_effort(self):
        """Test effort estimation"""
        pattern = SECURITY_PATTERNS['SQL_INJECTION']
        finding_injection = SecurityFinding(
            '1', 'P1', 'Test', 'injection', 'critical', 1, 'f', 'file.c', 1, '', '', ['CWE-89'], 0.9, {}
        )
        effort = self.advisor._estimate_effort(finding_injection, pattern)
        self.assertIn(effort, ['low', 'medium', 'high'])

    def test_bulk_remediation_plan(self):
        """Test bulk remediation plan generation"""
        findings = [
            SecurityFinding('1', 'P1', 'SQL Injection', 'injection', 'critical', 1, 'f1', 'file.c', 1, '', '', ['CWE-89'], 0.95, {}),
            SecurityFinding('2', 'P2', 'Buffer Overflow', 'buffer_overflow', 'high', 2, 'f2', 'file.c', 2, '', '', ['CWE-120'], 0.85, {}),
            SecurityFinding('3', 'P3', 'Memory Leak', 'memory_safety', 'medium', 3, 'f3', 'file.c', 3, '', '', ['CWE-401'], 0.70, {}),
        ]

        plan = self.advisor.get_bulk_remediation_plan(findings)

        # Should be sorted by priority (highest first)
        self.assertEqual(len(plan), 3)
        self.assertGreaterEqual(plan[0].priority, plan[1].priority)
        self.assertGreaterEqual(plan[1].priority, plan[2].priority)


class TestEnhancedSecurityWorkflow(unittest.TestCase):
    """Test enhanced security_workflow integration"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.SecurityScanner')
    @patch('src.workflow.multi_scenario_workflow.DataFlowAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.VulnerabilityReporter')
    @patch('src.workflow.multi_scenario_workflow.RemediationAdvisor')
    def test_enhanced_security_workflow(
        self,
        mock_advisor_class,
        mock_reporter_class,
        mock_analyzer_class,
        mock_scanner_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test enhanced security workflow with all agents"""
        # Setup mocks
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Mock SecurityScanner
        mock_scanner = Mock()
        mock_scanner.scan_all_patterns.return_value = [
            SecurityFinding('1', 'SQL_INJECTION_001', 'SQL Injection', 'injection', 'critical',
                          1, 'build_query', 'exec.c', 100, 'code', 'desc', ['CWE-89'], 0.9, {'id': 1}),
            SecurityFinding('2', 'BUFFER_OVERFLOW_001', 'Buffer Overflow', 'buffer_overflow', 'high',
                          2, 'copy_str', 'utils.c', 200, 'code', 'desc', ['CWE-120'], 0.85, {'id': 2}),
        ]
        mock_scanner_class.return_value = mock_scanner

        # Mock DataFlowAnalyzer
        mock_analyzer = Mock()
        mock_analyzer.trace_taint_flows.return_value = [
            DataFlowPath('FLOW_001', 'input_handler', 'tcp.c', 100, 'exec_query', 'exec.c', 200,
                        2, [], 'user_input', False)
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Mock VulnerabilityReporter
        mock_reporter = Mock()
        mock_report = Mock(spec=VulnerabilityReport)
        mock_report.report_id = 'VULN_REPORT_TEST'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_findings = 2
        mock_report.critical_count = 1
        mock_report.high_count = 1
        mock_report.medium_count = 0
        mock_report.low_count = 0
        mock_report.findings_by_category = {'injection': 1, 'buffer_overflow': 1}
        mock_report.findings = mock_scanner.scan_all_patterns.return_value
        mock_report.data_flows = mock_analyzer.trace_taint_flows.return_value
        mock_report.summary = 'Test security summary'
        mock_report.recommendations = ['Fix SQL injection', 'Fix buffer overflow']
        mock_reporter.generate_report.return_value = mock_report
        mock_reporter_class.return_value = mock_reporter

        # Mock RemediationAdvisor
        mock_advisor = Mock()
        mock_advisor.get_bulk_remediation_plan.return_value = [
            RemediationAdvice('1', 'SQL_INJECTION_001', ['Use prepared statements'],
                            'exec_params("SELECT...")', ['CWE-89'], 'medium', 10)
        ]
        mock_advisor_class.return_value = mock_advisor

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = 'Enhanced security audit complete. Found 2 vulnerabilities.'
        mock_llm_class.return_value = mock_llm

        # Create initial state
        state = MultiScenarioState(
            query='Find all security vulnerabilities',
            context=None,
            intent='security_audit',
            scenario_id='scenario_2',
            cpg_results=[],
            methods=[],
            answer='',
            evidence=[],
            metadata={}
        )

        # Execute workflow
        result = security_workflow(state)

        # Assertions
        self.assertIsNotNone(result)
        self.assertNotIn('error', result)
        self.assertEqual(result['intent'], 'security_audit')
        self.assertGreater(len(result['answer']), 0)
        self.assertGreater(len(result['evidence']), 0)

        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'VULN_REPORT_TEST')
        self.assertEqual(metadata['total_findings'], 2)
        self.assertEqual(metadata['critical_count'], 1)
        self.assertEqual(metadata['high_count'], 1)
        self.assertTrue(metadata['enhanced_mode'])

        # Verify all agents were called
        mock_scanner.scan_all_patterns.assert_called_once()
        mock_analyzer.trace_taint_flows.assert_called_once()
        mock_reporter.generate_report.assert_called_once()
        mock_advisor.get_bulk_remediation_plan.assert_called_once()
        mock_llm.generate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
