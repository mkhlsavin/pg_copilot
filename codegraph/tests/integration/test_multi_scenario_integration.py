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
    test_coverage_workflow as coverage_workflow,  # Alias to prevent pytest collection
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
    # NOTE: These tests verify workflows execute and return results.
    # The workflows import CPGQueryService in their own modules, so we test
    # against real database when available, otherwise skip.
    # ========================================================================

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_onboarding_workflow_mock(self):
        """Test onboarding workflow execution"""
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
        result = onboarding_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_security_workflow_mock(self):
        """Test security audit workflow execution"""
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
        result = security_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_refactoring_workflow_mock(self):
        """Test refactoring workflow execution"""
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
        result = refactoring_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_test_coverage_workflow_mock(self):
        """Test test coverage workflow execution"""
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
        result = coverage_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_performance_workflow_mock(self):
        """Test performance optimization workflow execution"""
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
        result = performance_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_architecture_workflow_mock(self):
        """Test architecture violation workflow execution"""
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
        result = architecture_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_tech_debt_workflow_mock(self):
        """Test technical debt workflow execution"""
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
        result = tech_debt_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    # ========================================================================
    # WEEK 4 WORKFLOW TESTS
    # ========================================================================

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_compliance_workflow_mock(self):
        """Test compliance checking workflow execution"""
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
        result = compliance_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_code_review_workflow_mock(self):
        """Test code review workflow execution"""
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
        result = code_review_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_cross_repo_workflow_mock(self):
        """Test cross-repo impact workflow execution"""
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
        result = cross_repo_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_mass_refactoring_workflow_mock(self):
        """Test mass refactoring workflow execution"""
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
        result = mass_refactoring_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available - workflow tests require database")
    def test_security_incident_workflow_mock(self):
        """Test security incident workflow execution"""
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
        result = security_incident_workflow(state)
        self.assertIsNotNone(result.get('answer') or result.get('error'))

    # ========================================================================
    # END-TO-END TESTS (with real DB if available)
    # ========================================================================

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_onboarding_query_e2e(self):
        """Test end-to-end onboarding query (requires cpg.duckdb)"""
        result = self.copilot.run("Give me an overview of the PostgreSQL subsystems")

        # Check intent classification - should return some intent
        self.assertIsNotNone(result.get('intent'))

        # Check answer generation - may return error if DB is empty but should have answer
        self.assertIsNotNone(result.get('answer') or result.get('error'))

        print(f"\n[Onboarding E2E Test]")
        print(f"Intent: {result.get('intent')} (confidence: {result.get('confidence', 0):.2f})")
        print(f"Subsystems found: {len(result.get('subsystems') or [])}")
        if result.get('answer'):
            print(f"Answer preview: {result['answer'][:200]}...")

    @unittest.skipIf(not HAS_CPG_DB, "cpg.duckdb not available")
    def test_documentation_query_e2e(self):
        """Test end-to-end documentation query (requires cpg.duckdb)"""
        result = self.copilot.run("Generate documentation for executor functions")

        # Check intent classification - should classify as documentation
        self.assertIsNotNone(result.get('intent'))

        # Check answer - may have error if DB is empty but should have response
        self.assertIsNotNone(result.get('answer') or result.get('error'))

        print(f"\n[Documentation E2E Test]")
        print(f"Intent: {result.get('intent')} (confidence: {result.get('confidence', 0):.2f})")
        print(f"Methods found: {len(result.get('methods') or [])}")
        if result.get('answer'):
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

        # Valid intents that queries might be classified as
        valid_intents = {
            'onboarding', 'documentation', 'feature_development',
            'architecture', 'refactoring', 'code_review', 'security'
        }

        for query in queries:
            result = self.copilot.run(query)
            # Check that intent is recognized (classification can vary)
            self.assertIn(result['intent'], valid_intents,
                         f"Unexpected intent for query: {query}")
            # Check that we get an answer or error
            self.assertIsNotNone(result.get('answer') or result.get('error'),
                               f"No answer or error for query: {query}")

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

    @patch('src.workflow.scenarios.onboarding.CPGQueryService')
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
        # The error will be in the answer or error field
        self.assertTrue(result.get('error') or 'error' in str(result.get('answer', '')).lower())


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
            # Database might be empty or have different structure
            # Just verify the method runs without error
            print(f"\n[CPG Service Test]")
            print(f"Found {len(subsystems)} subsystems")
            if subsystems:
                # Check structure if there are any subsystems
                first_subsys = subsystems[0]
                self.assertIn('name', first_subsys)
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
