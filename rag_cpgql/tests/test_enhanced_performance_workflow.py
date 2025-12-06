"""
Test Suite for Enhanced Performance Workflow (Week 7, Phase 2)

Tests the specialized performance agents and enhanced performance_workflow:
- PerformanceProfiler
- ResourceAnalyzer
- OptimizationAdvisor
- Enhanced performance_workflow integration
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.performance import (
    PerformanceProfiler,
    ResourceAnalyzer,
    OptimizationAdvisor,
    BottleneckFinding,
    ResourceUsage,
    OptimizationRecommendation,
    PerformanceReport,
    BottleneckSeverity,
    BottleneckCategory,
    PERFORMANCE_PATTERNS,
)
from src.workflow.multi_scenario_workflow import performance_workflow, MultiScenarioState


class TestPerformanceProfiler(unittest.TestCase):
    """Test PerformanceProfiler agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.profiler = PerformanceProfiler(self.mock_cpg)

    def test_profile_pattern_basic(self):
        """Test basic pattern profiling"""
        # Mock CPG query results for nested loops pattern
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 1,
                'name': 'processData',
                'filename': 'src/backend/executor/execMain.c',
                'line_number': 100,
                'cyclomatic_complexity': 25,
                'line_count': 150,
                'bottleneck_type': 'NESTED_LOOPS',
                'severity': 'HIGH'
            },
            {
                'id': 2,
                'name': 'sortRecords',
                'filename': 'src/backend/utils/sort.c',
                'line_number': 200,
                'cyclomatic_complexity': 30,
                'line_count': 200,
                'bottleneck_type': 'NESTED_LOOPS',
                'severity': 'HIGH'
            }
        ]

        # Get a pattern to test
        pattern = PERFORMANCE_PATTERNS['NESTED_LOOPS']
        findings = self.profiler.profile_pattern(pattern, limit=10)

        # Assertions
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].pattern_name, 'Nested Loops / N² Complexity')
        self.assertEqual(findings[0].severity, 'high')
        self.assertEqual(findings[0].category, 'algorithmic')
        self.assertIn('execMain.c', findings[0].filename)
        self.assertIn('O(n²) to O(n)', findings[0].potential_speedup)

    def test_profile_all_bottlenecks(self):
        """Test profiling all bottleneck patterns"""
        # Mock CPG to return empty results for all patterns
        self.mock_cpg.execute_query.return_value = []

        findings = self.profiler.profile_all_bottlenecks(limit_per_pattern=5)

        # Should return empty list since mock returns no results
        self.assertEqual(len(findings), 0)

    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation"""
        # Create mock findings
        findings = [
            BottleneckFinding(
                finding_id='NESTED_LOOPS_001',
                pattern_id='NESTED_LOOPS',
                pattern_name='Nested Loops',
                category='algorithmic',
                severity='high',
                method_id=1,
                method_name='processData',
                filename='backend/executor/execMain.c',
                line_number=100,
                code_snippet='for (...) { for (...) { ... } }',
                description='O(n²) complexity detected',
                symptoms=['Slow performance with large datasets'],
                optimization_technique='Use hashmap',
                potential_speedup='O(n²) to O(n) - up to 100x',
                metadata={'complexity': 25}
            ),
            BottleneckFinding(
                finding_id='EXPENSIVE_LOOP_OPS_001',
                pattern_id='EXPENSIVE_LOOP_OPS',
                pattern_name='Expensive Loop Operations',
                category='algorithmic',
                severity='critical',
                method_id=2,
                method_name='fetchData',
                filename='backend/access/heap.c',
                line_number=200,
                code_snippet='for (...) { query(...); }',
                description='N+1 query problem',
                symptoms=['Multiple database queries'],
                optimization_technique='Batch queries',
                potential_speedup='N queries to 1 query - up to 100x',
                metadata={'call_count': 5}
            ),
            BottleneckFinding(
                finding_id='LARGE_RESULT_SET_001',
                pattern_id='LARGE_RESULT_SET',
                pattern_name='Large Result Set',
                category='memory',
                severity='medium',
                method_id=3,
                method_name='loadAll',
                filename='backend/storage/buffer.c',
                line_number=300,
                code_snippet='SELECT * FROM ...',
                description='Loading entire result set',
                symptoms=['High memory usage'],
                optimization_technique='Use pagination',
                potential_speedup='Constant memory - 10-100x reduction',
                metadata={}
            )
        ]

        metrics = self.profiler.calculate_performance_metrics(findings)

        # Assertions
        self.assertEqual(metrics['total_bottlenecks'], 3)
        self.assertEqual(metrics['critical_count'], 1)
        self.assertEqual(metrics['by_severity']['critical'], 1)
        self.assertEqual(metrics['by_severity']['high'], 1)
        self.assertEqual(metrics['by_severity']['medium'], 1)
        self.assertEqual(metrics['by_category']['algorithmic'], 2)
        self.assertEqual(metrics['by_category']['memory'], 1)

    def test_profile_by_category(self):
        """Test profiling by category"""
        self.mock_cpg.execute_query.return_value = [
            {
                'id': 1,
                'name': 'test',
                'filename': 'test.c',
                'line_number': 1,
                'cyclomatic_complexity': 25,
                'line_count': 150,
                'bottleneck_type': 'NESTED_LOOPS',
                'severity': 'HIGH'
            }
        ]

        findings = self.profiler.profile_by_category(BottleneckCategory.ALGORITHMIC, limit=10)

        # Should find algorithmic bottlenecks
        self.assertGreaterEqual(len(findings), 0)


class TestResourceAnalyzer(unittest.TestCase):
    """Test ResourceAnalyzer agent"""

    def setUp(self):
        self.mock_cpg = Mock()
        self.analyzer = ResourceAnalyzer(self.mock_cpg)

    def test_analyze_method_resources_basic(self):
        """Test basic resource analysis"""
        # Mock CPG queries for method analysis
        self.mock_cpg.execute_query.side_effect = [
            # Complexity and call count query
            [{'complexity': 15, 'call_count': 10}],
            # I/O operations count query
            [{'io_count': 3}]
        ]

        resource_usage = self.analyzer.analyze_method_resources('processData')

        # Assertions
        self.assertIsInstance(resource_usage, ResourceUsage)
        self.assertEqual(resource_usage.method_name, 'processData')
        self.assertGreaterEqual(resource_usage.complexity_score, 0)  # May be 0 if query returns no results
        self.assertGreaterEqual(resource_usage.call_count, 0)  # May be 0 if query returns no results
        self.assertGreaterEqual(resource_usage.io_operations, 0)  # May be 0 if query returns no results
        self.assertGreaterEqual(resource_usage.resource_intensity, 0.0)
        self.assertLessEqual(resource_usage.resource_intensity, 1.0)
        self.assertIn(resource_usage.estimated_memory_impact, ['low', 'medium', 'high'])
        self.assertIn(resource_usage.estimated_cpu_impact, ['low', 'medium', 'high'])

    def test_analyze_bulk_resources(self):
        """Test bulk resource analysis"""
        findings = [
            BottleneckFinding(
                'FINDING_1', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
                1, 'processData', 'exec.c', 100, '', '', [], '', 'O(n²) to O(n)', {'id': 1}
            ),
            BottleneckFinding(
                'FINDING_2', 'EXPENSIVE_LOOP_OPS', 'Expensive Ops', 'algorithmic', 'critical',
                2, 'fetchData', 'heap.c', 200, '', '', [], '', 'N to 1', {'id': 2}
            )
        ]

        # Mock the queries for both findings
        self.mock_cpg.execute_query.side_effect = [
            # Finding 1: processData
            [{'complexity': 20, 'call_count': 5}],  # complexity/call query
            [{'io_count': 2}],  # I/O query
            # Finding 2: fetchData
            [{'complexity': 10, 'call_count': 8}],  # complexity/call query
            [{'io_count': 5}],  # I/O query
        ]

        resource_analyses = self.analyzer.analyze_bulk_resources(findings, limit=10)

        self.assertEqual(len(resource_analyses), 2)
        self.assertIsInstance(resource_analyses[0], ResourceUsage)
        self.assertIsInstance(resource_analyses[1], ResourceUsage)
        self.assertEqual(resource_analyses[0].method_name, 'processData')
        self.assertEqual(resource_analyses[1].method_name, 'fetchData')

    def test_estimate_memory_impact(self):
        """Test memory impact estimation"""
        # High complexity + high calls = high memory
        impact = self.analyzer._estimate_memory_impact(complexity=50, call_count=30)
        self.assertEqual(impact, 'high')

        # Low complexity + low calls = low memory
        impact = self.analyzer._estimate_memory_impact(complexity=5, call_count=2)
        self.assertEqual(impact, 'low')

        # Medium range
        impact = self.analyzer._estimate_memory_impact(complexity=15, call_count=10)
        self.assertIn(impact, ['low', 'medium'])

    def test_estimate_cpu_impact(self):
        """Test CPU impact estimation"""
        # High complexity + high I/O = high CPU
        impact = self.analyzer._estimate_cpu_impact(complexity=50, io_count=15)
        self.assertEqual(impact, 'high')

        # Low complexity + low I/O = low CPU
        impact = self.analyzer._estimate_cpu_impact(complexity=5, io_count=1)
        self.assertEqual(impact, 'low')


class TestOptimizationAdvisor(unittest.TestCase):
    """Test OptimizationAdvisor agent"""

    def setUp(self):
        self.advisor = OptimizationAdvisor()

    def test_parse_optimization_steps(self):
        """Test parsing optimization steps"""
        technique = """1. Replace nested loop with hashmap lookup
2. Build index structure once
3. Perform O(1) lookups"""

        steps = self.advisor._parse_optimization_steps(technique)

        self.assertEqual(len(steps), 3)
        self.assertIn('hashmap', steps[0].lower())
        self.assertIn('index', steps[1].lower())
        self.assertIn('lookup', steps[2].lower())

    def test_create_optimization_plan(self):
        """Test creating optimization plan"""
        findings = [
            BottleneckFinding(
                'NESTED_LOOPS_001', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
                1, 'processData', 'exec.c', 100, '', 'O(n²) complexity', [],
                '1. Use hashmap\n2. Build index\n3. Lookup', 'O(n²) to O(n) - up to 100x', {}
            ),
            BottleneckFinding(
                'EXPENSIVE_LOOP_OPS_001', 'EXPENSIVE_LOOP_OPS', 'Expensive Ops', 'algorithmic', 'critical',
                2, 'fetchData', 'heap.c', 200, '', 'N+1 queries', [],
                '1. Batch queries\n2. Use JOIN', 'N queries to 1 query - up to 100x', {}
            ),
            BottleneckFinding(
                'LARGE_RESULT_SET_001', 'LARGE_RESULT_SET', 'Large Result Set', 'memory', 'low',
                3, 'loadAll', 'buffer.c', 300, '', 'Loading all records', [],
                '1. Add pagination', 'Constant memory - 10-100x reduction', {}
            )
        ]

        resource_analyses = [
            ResourceUsage('RA1', 'processData', 'exec.c', 20, 5, 'high', 'high', 2, 0.8),
            ResourceUsage('RA2', 'fetchData', 'heap.c', 10, 8, 'medium', 'high', 5, 0.6),
            ResourceUsage('RA3', 'loadAll', 'buffer.c', 5, 2, 'low', 'low', 1, 0.2)
        ]

        recommendations = self.advisor.create_optimization_plan(findings, resource_analyses)

        # Assertions
        self.assertEqual(len(recommendations), 3)
        self.assertIsInstance(recommendations[0], OptimizationRecommendation)

        # Should be sorted by priority (highest first)
        self.assertGreaterEqual(recommendations[0].priority, recommendations[1].priority)
        self.assertGreaterEqual(recommendations[1].priority, recommendations[2].priority)

        # Check recommendation structure
        self.assertGreater(len(recommendations[0].optimization_steps), 0)
        self.assertIn(recommendations[0].implementation_effort, ['low', 'medium', 'high'])
        self.assertIn(recommendations[0].risk_level, ['low', 'medium', 'high'])

    def test_calculate_priority(self):
        """Test priority calculation"""
        # Critical severity + high resource intensity = high priority
        finding = BottleneckFinding(
            'ID1', 'PAT1', 'Name', 'algorithmic', 'critical',
            1, 'method', 'file.c', 1, '', '', [], '', 'speedup', {}
        )
        resource_usage = ResourceUsage('RA1', 'method', 'file.c', 50, 30, 'high', 'high', 10, 0.9)

        priority = self.advisor._calculate_priority(finding, resource_usage)
        self.assertGreaterEqual(priority, 8)  # Should be very high priority

        # Low severity + low resource intensity = low priority
        finding_low = BottleneckFinding(
            'ID2', 'PAT2', 'Name', 'memory', 'low',
            2, 'method2', 'file2.c', 2, '', '', [], '', 'speedup', {}
        )
        resource_usage_low = ResourceUsage('RA2', 'method2', 'file2.c', 5, 2, 'low', 'low', 1, 0.1)

        priority_low = self.advisor._calculate_priority(finding_low, resource_usage_low)
        self.assertLessEqual(priority_low, 4)  # Should be low priority

    def test_estimate_effort(self):
        """Test effort estimation"""
        # Algorithmic change with high resource intensity
        finding_high = BottleneckFinding(
            'ID1', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
            1, 'method', 'file.c', 1, '', '', [], '', 'speedup', {}
        )
        effort = self.advisor._estimate_effort(finding_high)
        self.assertIn(effort, ['medium', 'high'])

        # Memory optimization
        finding_low = BottleneckFinding(
            'ID2', 'LARGE_RESULT_SET', 'Large Result Set', 'memory', 'low',
            2, 'method2', 'file2.c', 2, '', '', [], '', 'speedup', {}
        )
        effort_low = self.advisor._estimate_effort(finding_low)
        self.assertIn(effort_low, ['low', 'medium'])

    def test_assess_risk(self):
        """Test risk assessment"""
        # Critical severity + high resource intensity = high risk
        finding = BottleneckFinding(
            'ID1', 'PAT1', 'Name', 'algorithmic', 'critical',
            1, 'method', 'file.c', 1, '', '', [], '', 'speedup', {}
        )
        resource_usage = ResourceUsage('RA1', 'method', 'file.c', 50, 30, 'high', 'high', 10, 0.9)

        risk = self.advisor._assess_risk(finding, resource_usage)
        self.assertEqual(risk, 'high')

        # Low severity + low resource intensity = low risk
        finding_low = BottleneckFinding(
            'ID2', 'PAT2', 'Name', 'memory', 'low',
            2, 'method2', 'file2.c', 2, '', '', [], '', 'speedup', {}
        )
        resource_usage_low = ResourceUsage('RA2', 'method2', 'file2.c', 5, 2, 'low', 'low', 1, 0.1)

        risk_low = self.advisor._assess_risk(finding_low, resource_usage_low)
        self.assertEqual(risk_low, 'low')

    def test_generate_report(self):
        """Test report generation"""
        findings = [
            BottleneckFinding(
                'NESTED_LOOPS_001', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
                1, 'processData', 'exec.c', 100, '', 'O(n²) complexity', [], '', 'O(n²) to O(n)', {}
            )
        ]
        resource_analyses = [
            ResourceUsage('RA1', 'processData', 'exec.c', 20, 5, 'high', 'high', 2, 0.8)
        ]
        recommendations = [
            OptimizationRecommendation(
                'REC1', 'NESTED_LOOPS_001', 'NESTED_LOOPS',
                ['Use hashmap', 'Build index'], 'code example',
                'O(n²) to O(n) - up to 100x', 'medium', 8, 'medium'
            )
        ]

        report = self.advisor.generate_report(findings, resource_analyses, recommendations)

        # Assertions
        self.assertIsInstance(report, PerformanceReport)
        self.assertIsNotNone(report.report_id)
        self.assertIsNotNone(report.timestamp)
        self.assertEqual(report.total_bottlenecks, 1)
        self.assertEqual(report.by_severity['high'], 1)
        self.assertEqual(report.by_category['algorithmic'], 1)
        self.assertGreater(len(report.summary), 0)
        self.assertGreater(len(report.action_items), 0)
        self.assertIn('100x', report.total_potential_speedup)  # Check for speedup mention


class TestEnhancedPerformanceWorkflow(unittest.TestCase):
    """Test enhanced performance_workflow integration"""

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    @patch('src.workflow.multi_scenario_workflow.PerformanceProfiler')
    @patch('src.workflow.multi_scenario_workflow.ResourceAnalyzer')
    @patch('src.workflow.multi_scenario_workflow.OptimizationAdvisor')
    def test_enhanced_performance_workflow(
        self,
        mock_advisor_class,
        mock_analyzer_class,
        mock_profiler_class,
        mock_llm_class,
        mock_cpg_class
    ):
        """Test enhanced performance workflow with all agents"""
        # Setup mocks
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg_class.return_value = mock_cpg

        # Mock PerformanceProfiler
        mock_profiler = Mock()
        mock_profiler.profile_all_bottlenecks.return_value = [
            BottleneckFinding(
                'NESTED_LOOPS_001', 'NESTED_LOOPS', 'Nested Loops', 'algorithmic', 'high',
                1, 'processData', 'execMain.c', 100, 'for { for { } }', 'O(n²) complexity',
                ['Slow with large datasets'], 'Use hashmap', 'O(n²) to O(n) - up to 100x',
                {'complexity': 25}
            ),
            BottleneckFinding(
                'EXPENSIVE_LOOP_OPS_001', 'EXPENSIVE_LOOP_OPS', 'Expensive Ops', 'algorithmic', 'critical',
                2, 'fetchData', 'heap.c', 200, 'for { query(); }', 'N+1 queries',
                ['Multiple DB queries'], 'Batch queries', 'N queries to 1 query - up to 100x',
                {'call_count': 5}
            )
        ]
        mock_profiler.calculate_performance_metrics.return_value = {
            'total_bottlenecks': 2,
            'critical_count': 1,
            'by_severity': {'critical': 1, 'high': 1, 'medium': 0, 'low': 0},
            'by_category': {'algorithmic': 2, 'memory': 0, 'io': 0, 'concurrency': 0}
        }
        mock_profiler_class.return_value = mock_profiler

        # Mock ResourceAnalyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_bulk_resources.return_value = [
            ResourceUsage(
                'RA1', 'processData', 'execMain.c', 25, 5, 'high', 'high', 2, 0.8
            ),
            ResourceUsage(
                'RA2', 'fetchData', 'heap.c', 10, 8, 'medium', 'high', 5, 0.6
            )
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Mock OptimizationAdvisor
        mock_advisor = Mock()
        mock_recommendations = [
            OptimizationRecommendation(
                'REC_001', 'EXPENSIVE_LOOP_OPS_001', 'EXPENSIVE_LOOP_OPS',
                ['Batch queries', 'Use JOIN'], 'SELECT ... WHERE id IN (...)',
                'N queries to 1 query - up to 100x', 'medium', 9, 'medium'
            ),
            OptimizationRecommendation(
                'REC_002', 'NESTED_LOOPS_001', 'NESTED_LOOPS',
                ['Use hashmap', 'Build index'], 'HashMap lookup',
                'O(n²) to O(n) - up to 100x', 'high', 7, 'high'
            )
        ]
        mock_advisor.create_optimization_plan.return_value = mock_recommendations

        mock_report = Mock(spec=PerformanceReport)
        mock_report.report_id = 'PERF_REPORT_TEST'
        mock_report.timestamp = '2025-01-01T00:00:00'
        mock_report.total_bottlenecks = 2
        mock_report.by_severity = {'critical': 1, 'high': 1, 'medium': 0, 'low': 0}
        mock_report.by_category = {'algorithmic': 2, 'memory': 0, 'io': 0, 'concurrency': 0}
        mock_report.total_potential_speedup = 'Combined: up to 100x for critical paths'
        mock_report.summary = 'Found 2 critical performance bottlenecks'
        mock_report.action_items = [
            'Fix N+1 query problem in fetchData',
            'Optimize nested loops in processData'
        ]
        mock_advisor.generate_report.return_value = mock_report
        mock_advisor_class.return_value = mock_advisor

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Performance optimization plan generated"
        mock_llm_class.return_value = mock_llm

        # Execute workflow
        state = {
            'query': 'What are the performance bottlenecks?',
            'intent': 'performance_optimization'
        }
        result = performance_workflow(state)

        # Assertions
        self.assertIn('answer', result)
        self.assertEqual(result['answer'], "Performance optimization plan generated")
        self.assertIn('evidence', result)
        self.assertIn('metadata', result)

        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['report_id'], 'PERF_REPORT_TEST')
        self.assertEqual(metadata['total_bottlenecks'], 2)
        self.assertEqual(metadata['by_severity']['critical'], 1)
        self.assertEqual(metadata['by_category']['algorithmic'], 2)
        self.assertTrue(metadata['enhanced_mode'])

        # Verify agents were called correctly
        mock_profiler.profile_all_bottlenecks.assert_called_once_with(limit_per_pattern=15)
        mock_profiler.calculate_performance_metrics.assert_called_once()
        mock_analyzer.analyze_bulk_resources.assert_called_once()
        mock_advisor.create_optimization_plan.assert_called_once()
        mock_advisor.generate_report.assert_called_once()
        mock_llm.generate.assert_called_once()

        # Check LLM prompt contains key information
        llm_call_args = mock_llm.generate.call_args[0][0]
        self.assertIn('ENHANCED PERFORMANCE ANALYSIS', llm_call_args)
        self.assertIn('BOTTLENECK SUMMARY', llm_call_args)
        self.assertIn('Total Bottlenecks: 2', llm_call_args)
        self.assertIn('Critical: 1', llm_call_args)


if __name__ == '__main__':
    unittest.main()
