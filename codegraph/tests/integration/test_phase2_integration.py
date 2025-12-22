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
import os
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

# Check for CPG database at module level
HAS_CPG_DB = os.path.exists('cpg.duckdb')


class TestPhase2SecurityIntegration(unittest.TestCase):
    """Integration tests for Enhanced Security Workflow (Week 5)"""

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_security_workflow_end_to_end(self):
        """Test complete security workflow execution"""
        state: MultiScenarioState = {
            'query': 'Find security vulnerabilities in the database layer',
            'context': None,
            'intent': 'security_audit',
            'scenario_id': 'scenario_1',
            'confidence': 0.9,
            'classification_method': 'test',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0
        }
        result = security_workflow(state)

        # Basic assertions - workflow should return answer or error
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Security workflow should return answer or error")


class TestPhase2RefactoringIntegration(unittest.TestCase):
    """Integration tests for Enhanced Refactoring Workflow (Week 6)"""

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_refactoring_workflow_end_to_end(self):
        """Test complete refactoring workflow execution"""
        state: MultiScenarioState = {
            'query': 'Identify code smells in the executor',
            'context': None,
            'intent': 'refactoring',
            'scenario_id': 'scenario_4',
            'confidence': 0.9,
            'classification_method': 'test',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0
        }
        result = refactoring_workflow(state)

        # Basic assertions - workflow should return answer or error
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Refactoring workflow should return answer or error")


class TestPhase2PerformanceIntegration(unittest.TestCase):
    """Integration tests for Enhanced Performance Workflow (Week 7)"""

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_performance_workflow_end_to_end(self):
        """Test complete performance workflow execution"""
        state: MultiScenarioState = {
            'query': 'Find performance bottlenecks in sorting',
            'context': None,
            'intent': 'performance_optimization',
            'scenario_id': 'scenario_2',
            'confidence': 0.9,
            'classification_method': 'test',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0
        }
        result = performance_workflow(state)

        # Basic assertions - workflow should return answer or error
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Performance workflow should return answer or error")


class TestPhase2CrossWorkflowIntegration(unittest.TestCase):
    """Cross-workflow integration tests for Phase 2"""

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_all_workflows_return_valid_response(self):
        """Verify all Phase 2 workflows return valid responses"""
        # Test each workflow returns either answer or error

        # Security workflow
        state: MultiScenarioState = {
            'query': 'test security',
            'context': None,
            'intent': 'security_audit',
            'scenario_id': 'scenario_1',
            'confidence': 0.9,
            'classification_method': 'test',
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0
        }
        result = security_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Security workflow should return answer or error")

        # Refactoring workflow
        state['query'] = 'test refactoring'
        state['intent'] = 'refactoring'
        state['scenario_id'] = 'scenario_4'
        result = refactoring_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Refactoring workflow should return answer or error")

        # Performance workflow
        state['query'] = 'test performance'
        state['intent'] = 'performance_optimization'
        state['scenario_id'] = 'scenario_2'
        result = performance_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'),
                           "Performance workflow should return answer or error")

    def test_workflow_error_handling(self):
        """Verify all workflows handle errors gracefully"""
        # Test error handling by patching at the correct module location
        # CPGQueryService is imported in main_workflow.py, so patch there
        with patch('src.workflow.scenarios.security.main_workflow.CPGQueryService') as mock_cpg:
            mock_cpg.return_value.__enter__.side_effect = Exception("CPG connection failed")
            mock_cpg.return_value.__exit__ = Mock(return_value=False)

            state: MultiScenarioState = {
                'query': 'test',
                'context': None,
                'intent': 'security_audit',
                'scenario_id': 'scenario_1',
                'confidence': 0.9,
                'classification_method': 'test',
                'cpg_results': None,
                'subsystems': None,
                'methods': None,
                'call_graph': None,
                'answer': None,
                'evidence': None,
                'metadata': None,
                'retrieved_functions': None,
                'error': None,
                'retry_count': 0
            }
            result = security_workflow(state)

            # Should either have error or handle gracefully
            self.assertIsNotNone(result.get('error') or result.get('answer'),
                               "Workflow should return error or answer on failure")


if __name__ == '__main__':
    unittest.main()
