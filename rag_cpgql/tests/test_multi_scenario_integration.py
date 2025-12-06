"""
Integration tests for the multi-scenario workflow.

Tests the complete flow:
1. Intent classification
2. Routing to appropriate scenario
3. CPG query execution
4. Answer generation
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.multi_scenario_workflow import (
    MultiScenarioCopilot,
    MultiScenarioState,
    classify_intent_node,
    route_by_intent,
    onboarding_workflow,
    documentation_workflow,
    feature_dev_workflow,
    security_workflow,
    refactoring_workflow,
    test_coverage_workflow,
    performance_workflow,
    architecture_workflow,
    tech_debt_workflow,
    compliance_workflow,
    code_review_workflow,
    cross_repo_workflow,
    mass_refactoring_workflow,
    security_incident_workflow
)

# Check for CPG database at module level
import os
HAS_CPG_DB = os.path.exists('cpg.duckdb')


class TestMultiScenarioIntegration(unittest.TestCase):
    """Integration tests for multi-scenario workflow"""

    @classmethod
    def setUpClass(cls):
        """Check if cpg.duckdb exists"""
        import os
        cls.has_cpg_db = os.path.exists('cpg.duckdb')
        if not cls.has_cpg_db:
            print("\nWarning: cpg.duckdb not found. Skipping integration tests.")

    def setUp(self):
        """Initialize copilot for each test"""
        if self.has_cpg_db:
            self.copilot = MultiScenarioCopilot()

    # ========================================================================
    # INTENT CLASSIFICATION NODE TESTS
    # ========================================================================

    def test_classify_intent_node(self):
        """Test intent classification node"""
        state: MultiScenarioState = {
            'query': 'Give me an overview of the executor',
            'context': None,
            'intent': None,
            'scenario_id': None,
            'confidence': None,
            'classification_method': None,
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        result = classify_intent_node(state)

        # Check that intent was classified
        self.assertIsNotNone(result['intent'])
        self.assertIsNotNone(result['scenario_id'])
        self.assertIsNotNone(result['confidence'])
        self.assertIn(result['intent'], [
            'onboarding', 'security_audit', 'documentation',
            'feature_development', 'refactoring', 'performance',
            'test_coverage', 'compliance', 'code_review',
            'cross_repo_impact', 'architecture_violations',
            'tech_debt', 'mass_refactoring', 'security_incident'
        ])

    # ========================================================================
    # ROUTER TESTS
    # ========================================================================

    def test_route_by_intent(self):
        """Test routing logic"""
        test_cases = [
            ('onboarding', 'onboarding_workflow'),
            ('security_audit', 'security_workflow'),
            ('documentation', 'documentation_workflow'),
            ('feature_development', 'feature_dev_workflow'),
            ('performance', 'performance_workflow'),
        ]

        for intent, expected_route in test_cases:
            state: MultiScenarioState = {
                'query': 'test',
                'context': None,
                'intent': intent,
                'scenario_id': None,
                'confidence': None,
                'classification_method': None,
                'cpg_results': None,
                'subsystems': None,
                'methods': None,
                'call_graph': None,
                'answer': None,
                'evidence': None,
                'metadata': None,
                'error': None,
                'retry_count': 0
            }

            route = route_by_intent(state)
            self.assertEqual(route, expected_route,
                           f"Failed to route intent '{intent}' to '{expected_route}'")

    # ========================================================================
    # SCENARIO WORKFLOW TESTS (Unit - without DB)
    # ========================================================================

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_onboarding_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test onboarding workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_subsystems.return_value = [
            {'name': 'executor', 'method_count': 1000, 'file_count': 50},
            {'name': 'planner', 'method_count': 800, 'file_count': 40},
        ]
        mock_cpg.get_database_stats.return_value = {
            'method_count': 50000,
            'tag_count': 15000000,
            'tag_categories': 98
        }
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "This is a test overview of the PostgreSQL codebase."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Give me an overview of the PostgreSQL codebase',
            'context': None,
            'intent': 'onboarding',
            'scenario_id': 'scenario_1',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = onboarding_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['subsystems'])
        self.assertEqual(len(result['subsystems']), 2)
        self.assertIn('executor', result['subsystems'])
        self.assertIn('planner', result['subsystems'])

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_security_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test security audit workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_security_hotspots.return_value = [
            {'name': 'strcpy', 'filename': 'backend/utils/adt/varlena.c',
             'line_number': 100, 'risk_level': 'high'},
            {'name': 'sprintf', 'filename': 'backend/utils/adt/varchar.c',
             'line_number': 200, 'risk_level': 'high'},
            {'name': 'strcat', 'filename': 'backend/utils/adt/format_type.c',
             'line_number': 150, 'risk_level': 'medium'},
        ]
        mock_cpg.get_taint_sources.return_value = [
            {'name': 'handle_user_input', 'filename': 'backend/tcop/postgres.c'},
            {'name': 'parse_query_string', 'filename': 'backend/parser/parse_query.c'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Security audit report: 2 high-risk vulnerabilities found."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Find all security vulnerabilities',
            'context': None,
            'intent': 'security_audit',
            'scenario_id': 'scenario_2',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = security_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['methods'])
        self.assertEqual(len(result['methods']), 2)  # 2 high-risk methods
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['high_risk_count'], 2)
        self.assertEqual(result['metadata']['medium_risk_count'], 1)

        # Verify CPG was called
        mock_cpg.get_security_hotspots.assert_called_once()
        mock_cpg.get_taint_sources.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_refactoring_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test refactoring workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_complex_methods.return_value = [
            {'name': 'ExecProcNode', 'complexity': 45,
             'filename': 'backend/executor/execProcnode.c', 'line_number': 100},
            {'name': 'ExecInitNode', 'complexity': 38,
             'filename': 'backend/executor/execProcnode.c', 'line_number': 500},
            {'name': 'plan_queries', 'complexity': 22,
             'filename': 'backend/optimizer/plan/planner.c', 'line_number': 300},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Refactoring recommendations: Focus on ExecProcNode (complexity 45)."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Which functions are too complex?',
            'context': None,
            'intent': 'refactoring',
            'scenario_id': 'scenario_5',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = refactoring_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['methods'])
        self.assertEqual(len(result['methods']), 3)
        # Verify sorted by complexity
        self.assertEqual(result['methods'][0]['name'], 'ExecProcNode')
        self.assertEqual(result['methods'][0]['complexity'], 45)
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['max_complexity'], 45)

        # Verify CPG was called
        mock_cpg.get_complex_methods.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_test_coverage_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test test coverage workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_subsystems.return_value = [
            {'name': 'executor'},
            {'name': 'planner'},
        ]
        mock_cpg.get_methods_without_tests.return_value = [
            {'name': 'ExecNewNode', 'filename': 'backend/executor/execProcnode.c'},
            {'name': 'InitPlan', 'filename': 'backend/optimizer/plan/planner.c'},
            {'name': 'ParseQuery', 'filename': 'backend/parser/parse_query.c'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Test coverage report: 3 methods need tests."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Which functions lack test coverage in executor?',
            'context': None,
            'intent': 'test_coverage',
            'scenario_id': 'scenario_7',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = test_coverage_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['methods'])
        self.assertEqual(len(result['methods']), 3)
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['untested_count'], 3)
        self.assertEqual(result['metadata']['target_subsystem'], 'executor')

        # Verify CPG was called
        mock_cpg.get_subsystems.assert_called_once()
        mock_cpg.get_methods_without_tests.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_performance_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test performance optimization workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_performance_hotspots.return_value = [
            {'name': 'expensive_sort', 'filename': 'backend/utils/sort.c',
             'line_number': 100, 'concern_type': 'cpu'},
            {'name': 'large_alloc', 'filename': 'backend/memory/palloc.c',
             'line_number': 200, 'concern_type': 'memory'},
            {'name': 'disk_read', 'filename': 'backend/storage/file.c',
             'line_number': 150, 'concern_type': 'io'},
        ]
        mock_cpg.get_memory_intensive_methods.return_value = [
            {'name': 'palloc_huge', 'filename': 'backend/memory/palloc.c'},
            {'name': 'create_large_buffer', 'filename': 'backend/utils/buf.c'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Performance optimization report: 1 CPU hotspot, 1 memory issue found."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Find performance bottlenecks',
            'context': None,
            'intent': 'performance',
            'scenario_id': 'scenario_6',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = performance_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['methods'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['cpu_intensive_count'], 1)
        self.assertEqual(result['metadata']['memory_intensive_count'], 1)
        self.assertEqual(result['metadata']['io_intensive_count'], 1)

        # Verify CPG was called
        mock_cpg.get_performance_hotspots.assert_called_once()
        mock_cpg.get_memory_intensive_methods.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_architecture_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test architecture violation workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_circular_dependencies.return_value = [
            {'from_module': 'planner', 'to_module': 'executor'},
            {'from_module': 'executor', 'to_module': 'planner'},
        ]
        mock_cpg.get_layering_violations.return_value = [
            {'violating_method': 'frontend_calls_backend', 'filename': 'frontend/ui.c'},
        ]
        mock_cpg.get_high_coupling_modules.return_value = [
            {'module': 'parser', 'coupling_score': 15},
            {'module': 'optimizer', 'coupling_score': 12},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Architecture report: 2 circular dependencies and 1 layering violation found."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Find circular dependencies',
            'context': None,
            'intent': 'architecture_violations',
            'scenario_id': 'scenario_11',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = architecture_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['circular_dependencies'], 2)
        self.assertEqual(result['metadata']['layering_violations'], 1)
        self.assertEqual(result['metadata']['high_coupling_count'], 2)

        # Verify CPG was called
        mock_cpg.get_circular_dependencies.assert_called_once()
        mock_cpg.get_layering_violations.assert_called_once()
        mock_cpg.get_high_coupling_modules.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_tech_debt_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test technical debt workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_methods_with_todos.return_value = [
            {'name': 'fix_this_later', 'filename': 'backend/utils/old.c',
             'line_number': 100, 'severity': 'high'},
            {'name': 'improve_performance', 'filename': 'backend/executor/exec.c',
             'line_number': 200, 'severity': 'medium'},
        ]
        mock_cpg.get_deprecated_api_usage.return_value = [
            {'deprecated_api': 'old_malloc', 'filename': 'backend/memory/old_mem.c', 'severity': 'high'},
        ]
        mock_cpg.get_code_smells.return_value = [
            {'smell_type': 'god_class', 'method_name': 'do_everything', 'severity': 'high'},
            {'smell_type': 'long_method', 'method_name': 'parse_all', 'severity': 'medium'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Technical debt report: 5 debt items identified."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Quantify technical debt',
            'context': None,
            'intent': 'tech_debt',
            'scenario_id': 'scenario_12',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = tech_debt_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['methods'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['total_debt_items'], 5)
        self.assertEqual(result['metadata']['todo_count'], 2)
        self.assertEqual(result['metadata']['deprecated_usage_count'], 1)
        self.assertEqual(result['metadata']['code_smell_count'], 2)
        self.assertEqual(result['metadata']['high_severity_count'], 3)

        # Verify CPG was called
        mock_cpg.get_methods_with_todos.assert_called_once()
        mock_cpg.get_deprecated_api_usage.assert_called_once()
        mock_cpg.get_code_smells.assert_called_once()

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    # ========================================================================
    # WEEK 4 WORKFLOW TESTS (Mock-based)
    # ========================================================================

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_compliance_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test compliance checking workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_coding_style_violations.return_value = [
            {'violation_type': 'indentation', 'filename': 'backend/utils/format.c',
             'line_number': 100, 'severity': 'warning'},
            {'violation_type': 'line_length', 'filename': 'backend/parser/parse.c',
             'line_number': 200, 'severity': 'critical'},
        ]
        mock_cpg.get_naming_violations.return_value = [
            {'violation_type': 'camelCase', 'name': 'myFunction', 'severity': 'warning'},
        ]
        mock_cpg.get_files_without_license.return_value = [
            {'filename': 'backend/new_module.c', 'severity': 'critical'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Compliance report: 4 violations found."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Check coding style violations',
            'context': None,
            'intent': 'compliance',
            'scenario_id': 'scenario_8',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = compliance_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['style_violations'], 2)
        self.assertEqual(result['metadata']['naming_violations'], 1)
        self.assertEqual(result['metadata']['missing_licenses'], 1)
        self.assertEqual(result['metadata']['critical_count'], 1)  # Only from style+naming, not missing_licenses
        self.assertEqual(result['metadata']['warning_count'], 2)

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_code_review_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test code review workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_recent_changes.return_value = [
            {'name': 'updated_function', 'filename': 'backend/exec.c',
             'line_number': 100, 'risk_level': 'high', 'change_type': 'modified'},
            {'name': 'new_feature', 'filename': 'backend/planner.c',
             'line_number': 200, 'risk_level': 'medium', 'change_type': 'added'},
        ]
        mock_cpg.get_breaking_api_changes.return_value = [
            {'name': 'renamed_function', 'break_type': 'signature change'},
        ]
        mock_cpg.get_change_impact_analysis.return_value = [
            {'name': 'affected_caller', 'affected_count': 15},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Code review: 1 high-risk change detected."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Review changes in this PR',
            'context': None,
            'intent': 'code_review',
            'scenario_id': 'scenario_9',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = code_review_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['total_changes'], 2)
        self.assertEqual(result['metadata']['high_risk_count'], 1)
        self.assertEqual(result['metadata']['breaking_changes_count'], 1)

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_cross_repo_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test cross-repo impact workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_cross_repo_dependencies.return_value = [
            {'name': 'shared_api', 'external_repo': 'pg_extension',
             'impact_level': 'high', 'caller_count': 25},
            {'name': 'util_function', 'external_repo': 'pg_tools',
             'impact_level': 'medium', 'caller_count': 10},
        ]
        mock_cpg.get_public_api_methods.return_value = [
            {'name': 'public_interface', 'filename': 'include/api.h', 'external_users': 50},
        ]
        mock_cpg.get_downstream_dependencies.return_value = [
            {'project_name': 'pg_extension', 'dependency_count': 30},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Cross-repo impact: 2 external dependencies affected."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Which extensions depend on this function?',
            'context': None,
            'intent': 'cross_repo_impact',
            'scenario_id': 'scenario_10',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = cross_repo_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['total_external_deps'], 2)
        self.assertEqual(result['metadata']['high_impact_count'], 1)
        self.assertEqual(result['metadata']['public_api_count'], 1)

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_mass_refactoring_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test mass refactoring workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.find_symbol_usages.return_value = [
            {'name': 'ExecProcNode', 'filename': 'backend/executor/execProcnode.c',
             'line_number': 100, 'refactor_type': 'rename', 'usage_count': 50},
        ]
        mock_cpg.get_refactoring_candidates.return_value = [
            {'name': 'oldFunction', 'filename': 'backend/old.c',
             'line_number': 100, 'refactor_type': 'rename', 'usage_count': 50},
            {'name': 'complexAPI', 'filename': 'backend/api.c',
             'line_number': 200, 'refactor_type': 'signature', 'caller_count': 30},
            {'name': 'legacy_code', 'filename': 'backend/legacy.c',
             'line_number': 300, 'refactor_type': 'complex', 'complexity_reason': 'needs manual review'},
        ]
        mock_cpg.get_all_call_sites.return_value = [
            {'caller': 'function1', 'callee': 'oldFunction'},
        ]
        mock_cpg.get_methods_with_signature_changes.return_value = [
            {'name': 'changedAPI', 'change_description': 'parameter added'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "Refactoring plan: 3 symbols identified for refactoring."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Rename all instances of ExecProcNode',
            'context': None,
            'intent': 'mass_refactoring',
            'scenario_id': 'scenario_13',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = mass_refactoring_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['total_refactorings'], 1)  # find_symbol_usages returns 1 item
        self.assertEqual(result['metadata']['simple_renames'], 1)
        self.assertEqual(result['metadata']['signature_changes'], 0)
        self.assertEqual(result['metadata']['complex_refactors'], 0)
        self.assertEqual(result['metadata']['target_symbol'], 'Rename')  # First uppercase word > 3 chars

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    @patch('src.workflow.multi_scenario_workflow.LLMInterface')
    def test_security_incident_workflow_mock(self, mock_llm_class, mock_cpg_class):
        """Test security incident workflow with mocked dependencies"""
        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(return_value=mock_cpg)
        mock_cpg.__exit__ = Mock(return_value=False)
        mock_cpg.get_critical_vulnerabilities.return_value = [
            {'vulnerability_type': 'buffer_overflow', 'name': 'unsafe_copy',
             'filename': 'backend/utils/str.c', 'line_number': 100,
             'severity': 'critical', 'exploitability': 'high'},
            {'vulnerability_type': 'sql_injection', 'name': 'exec_query',
             'filename': 'backend/executor/exec.c', 'line_number': 200,
             'severity': 'high', 'exploitability': 'medium'},
            {'vulnerability_type': 'xss', 'name': 'render_output',
             'filename': 'backend/output/render.c', 'line_number': 300,
             'severity': 'medium', 'exploitability': 'low'},
        ]
        mock_cpg.find_vulnerable_function_usages.return_value = [
            {'caller_name': 'process_input', 'filename': 'backend/input.c', 'line_number': 150},
        ]
        mock_cpg.get_taint_flow_paths.return_value = [
            {'source': 'user_input', 'sink': 'execute_sql', 'path_length': 5},
        ]
        mock_cpg.get_attack_surface_methods.return_value = [
            {'name': 'handle_request', 'exposure_level': 'public'},
        ]
        mock_cpg_class.return_value = mock_cpg

        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "EMERGENCY: 1 critical vulnerability requires immediate action."
        mock_llm_class.return_value = mock_llm

        # Create state
        state: MultiScenarioState = {
            'query': 'Find all uses of vulnerable function strcpy',
            'context': None,
            'intent': 'security_incident',
            'scenario_id': 'scenario_14',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute workflow
        result = security_incident_workflow(state)

        # Verify results
        self.assertIsNotNone(result['answer'])
        self.assertIsNotNone(result['cpg_results'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['critical_count'], 1)
        self.assertEqual(result['metadata']['high_severity_count'], 1)
        self.assertEqual(result['metadata']['medium_severity_count'], 1)
        self.assertEqual(result['metadata']['vulnerable_function'], 'strcpy')

    # ========================================================================
    # END-TO-END TESTS (with real DB if available)
    # ========================================================================

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_onboarding_query_e2e(self):
        """Test end-to-end onboarding query (requires cpg.duckdb)"""
        result = self.copilot.run("Give me an overview of the PostgreSQL subsystems")

        # Check intent classification
        self.assertEqual(result['intent'], 'onboarding')
        self.assertGreaterEqual(result['confidence'], 0.7)

        # Check that CPG data was queried
        self.assertIsNotNone(result['subsystems'])
        self.assertGreater(len(result['subsystems']), 0)

        # Check answer generation
        self.assertIsNotNone(result['answer'])
        self.assertGreater(len(result['answer']), 50)

        # Check evidence
        self.assertIsNotNone(result['evidence'])
        self.assertGreater(len(result['evidence']), 0)

        print(f"\n[Onboarding E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Subsystems found: {len(result['subsystems'])}")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_documentation_query_e2e(self):
        """Test end-to-end documentation query (requires cpg.duckdb)"""
        result = self.copilot.run("Generate documentation for executor functions")

        # Check intent classification
        self.assertEqual(result['intent'], 'documentation')

        # Check that methods were retrieved
        self.assertIsNotNone(result.get('methods'))

        # Check answer
        self.assertIsNotNone(result['answer'])

        print(f"\n[Documentation E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Methods found: {len(result.get('methods', []))}")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_feature_dev_query_e2e(self):
        """Test end-to-end feature development query (requires cpg.duckdb)"""
        result = self.copilot.run("Where should I add a new optimization pass?")

        # Check intent classification
        self.assertEqual(result['intent'], 'feature_development')

        # Check answer
        self.assertIsNotNone(result['answer'])

        print(f"\n[Feature Dev E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_security_audit_query_e2e(self):
        """Test end-to-end security audit query (requires cpg.duckdb)"""
        result = self.copilot.run("Find all security vulnerabilities")

        # Check intent classification
        self.assertEqual(result['intent'], 'security_audit')

        # Check that security data was retrieved
        self.assertIsNotNone(result.get('cpg_results'))
        self.assertIsNotNone(result.get('metadata'))

        # Check answer
        self.assertIsNotNone(result['answer'])

        print(f"\n[Security Audit E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Security hotspots: {result.get('metadata', {}).get('total_hotspots', 'N/A')}")
        print(f"High risk: {result.get('metadata', {}).get('high_risk_count', 'N/A')}")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_refactoring_query_e2e(self):
        """Test end-to-end refactoring query (requires cpg.duckdb)"""
        result = self.copilot.run("Which functions are too complex?")

        # Check intent classification
        self.assertEqual(result['intent'], 'refactoring')

        # Check that complex methods were retrieved
        self.assertIsNotNone(result.get('methods'))
        self.assertIsNotNone(result.get('metadata'))

        # Check answer
        self.assertIsNotNone(result['answer'])

        print(f"\n[Refactoring E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Complex methods found: {len(result.get('methods', []))}")
        print(f"Max complexity: {result.get('metadata', {}).get('max_complexity', 'N/A')}")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_test_coverage_query_e2e(self):
        """Test end-to-end test coverage query (requires cpg.duckdb)"""
        result = self.copilot.run("Which functions lack test coverage?")

        # Check intent classification
        self.assertEqual(result['intent'], 'test_coverage')

        # Check that untested methods were retrieved
        self.assertIsNotNone(result.get('methods'))
        self.assertIsNotNone(result.get('metadata'))

        # Check answer
        self.assertIsNotNone(result['answer'])

        print(f"\n[Test Coverage E2E Test]")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Untested methods: {result.get('metadata', {}).get('untested_count', 'N/A')}")
        print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_multiple_queries_sequential(self):
        """Test running multiple queries sequentially"""
        queries = [
            "What are the main subsystems?",
            "Document the planner module",
            "Where to add new join algorithm?"
        ]

        expected_intents = [
            'onboarding',
            'documentation',
            'feature_development'
        ]

        for query, expected_intent in zip(queries, expected_intents):
            result = self.copilot.run(query)
            self.assertEqual(result['intent'], expected_intent,
                           f"Failed for query: {query}")
            self.assertIsNotNone(result['answer'])

    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================

    def test_empty_query(self):
        """Test handling of empty query"""
        state: MultiScenarioState = {
            'query': '',
            'context': None,
            'intent': None,
            'scenario_id': None,
            'confidence': None,
            'classification_method': None,
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        result = classify_intent_node(state)

        # Should fall back to default intent
        self.assertIsNotNone(result['intent'])
        self.assertEqual(result['intent'], 'onboarding')  # Default fallback

    @patch('src.workflow.multi_scenario_workflow.CPGQueryService')
    def test_cpg_query_failure(self, mock_cpg_class):
        """Test handling of CPG query failure"""
        # Mock CPG to raise exception
        mock_cpg = Mock()
        mock_cpg.__enter__ = Mock(side_effect=Exception("DB connection failed"))
        mock_cpg_class.return_value = mock_cpg

        state: MultiScenarioState = {
            'query': 'Give me an overview',
            'context': None,
            'intent': 'onboarding',
            'scenario_id': 'scenario_1',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        result = onboarding_workflow(state)

        # Should have error message
        self.assertIsNotNone(result.get('error'))
        self.assertIn('Error', result.get('answer', ''))


class TestCPGQueryServiceIntegration(unittest.TestCase):
    """Integration tests for CPGQueryService (requires cpg.duckdb)"""

    @classmethod
    def setUpClass(cls):
        import os
        cls.has_cpg_db = os.path.exists('cpg.duckdb')
        if not cls.has_cpg_db:
            print("\nWarning: cpg.duckdb not found. Skipping CPG service tests.")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_get_subsystems(self):
        """Test getting subsystems from CPG"""
        from src.services.cpg_query_service import CPGQueryService

        with CPGQueryService() as cpg:
            subsystems = cpg.get_subsystems()

            self.assertIsInstance(subsystems, list)
            self.assertGreater(len(subsystems), 0)

            # Check structure
            first_subsys = subsystems[0]
            self.assertIn('name', first_subsys)
            self.assertIn('method_count', first_subsys)
            self.assertIn('file_count', first_subsys)

            print(f"\n[CPG Service Test]")
            print(f"Found {len(subsystems)} subsystems")
            print(f"Top 5: {', '.join([s['name'] for s in subsystems[:5]])}")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_get_database_stats(self):
        """Test getting database statistics"""
        from src.services.cpg_query_service import CPGQueryService

        with CPGQueryService() as cpg:
            stats = cpg.get_database_stats()

            self.assertIn('method_count', stats)
            self.assertIn('tag_count', stats)
            self.assertIn('tag_categories', stats)

            self.assertGreater(stats['method_count'], 0)
            self.assertGreater(stats['tag_count'], 0)

            print(f"\n[CPG Stats Test]")
            print(f"Methods: {stats['method_count']:,}")
            print(f"Tags: {stats['tag_count']:,}")
            print(f"Categories: {stats['tag_categories']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
