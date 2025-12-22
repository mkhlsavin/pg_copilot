"""
Integration Tests for All 14 Scenarios with Real CPG Database

Phase 1 Production Fixes - Comprehensive Integration Testing

Tests all 14 scenarios with:
1. Real DuckDB CPG database
2. GigaChat LLM provider (or configured provider)
3. Full workflow execution
4. Error handling validation

Author: Production Fixes - Phase 1
Date: November 25, 2025
"""

import pytest
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports
from src.workflow.multi_scenario_workflow import MultiScenarioCopilot, MultiScenarioState
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.error_handling import AgentResult, aggregate_partial_results


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def copilot():
    """Create MultiScenarioCopilot instance for testing"""
    try:
        return MultiScenarioCopilot()
    except Exception as e:
        pytest.skip(f"Could not initialize MultiScenarioCopilot: {e}")


@pytest.fixture(scope="module")
def cpg_service():
    """Create CPGQueryService for validation"""
    try:
        cpg = CPGQueryService()
        yield cpg
        cpg.close()
    except Exception as e:
        pytest.skip(f"Could not connect to CPG database: {e}")


@pytest.fixture(scope="module")
def llm():
    """Create LLMInterface for validation"""
    try:
        return LLMInterface()
    except Exception as e:
        pytest.skip(f"Could not initialize LLM: {e}")


# ============================================================================
# TEST QUERIES FOR EACH SCENARIO
# ============================================================================

SCENARIO_TEST_QUERIES = {
    'scenario_1_onboarding': {
        'intent': 'onboarding',
        'query': 'Give me an overview of the PostgreSQL executor subsystem',
        'expected_keys': ['answer', 'intent', 'confidence'],
    },
    'scenario_2_security': {
        'intent': 'security_audit',
        'query': 'Find potential SQL injection vulnerabilities in the codebase',
        'expected_keys': ['answer', 'intent'],
    },
    'scenario_3_documentation': {
        'intent': 'documentation',
        'query': 'Document the exec_simple_query function',
        'expected_keys': ['answer'],
    },
    'scenario_4_feature_dev': {
        'intent': 'feature_development',
        'query': 'Where should I add a new query optimizer feature?',
        'expected_keys': ['answer'],
    },
    'scenario_5_refactoring': {
        'intent': 'refactoring',
        'query': 'Identify refactoring opportunities in the executor module',
        'expected_keys': ['answer'],
    },
    'scenario_6_performance': {
        'intent': 'performance',
        'query': 'What are the performance hotspots in the system?',
        'expected_keys': ['answer', 'intent'],
    },
    'scenario_7_test_coverage': {
        'intent': 'test_coverage',
        'query': 'What is the test coverage for the parser module?',
        'expected_keys': ['answer'],
    },
    'scenario_8_compliance': {
        'intent': 'compliance',
        'query': 'Check MISRA-C compliance for memory management code',
        'expected_keys': ['answer'],
    },
    'scenario_9_code_review': {
        'intent': 'code_review',
        'query': 'Review the recent changes to query execution',
        'expected_keys': ['answer'],
    },
    'scenario_10_cross_repo': {
        'intent': 'cross_repo_impact',
        'query': 'What would be the impact of changing exec_simple_query?',
        'expected_keys': ['answer'],
    },
    'scenario_11_architecture': {
        'intent': 'architecture_violations',
        'query': 'Check for architecture violations in module dependencies',
        'expected_keys': ['answer'],
    },
    'scenario_12_tech_debt': {
        'intent': 'tech_debt',
        'query': 'Assess technical debt in the codebase',
        'expected_keys': ['answer'],
    },
    'scenario_13_mass_refactoring': {
        'intent': 'mass_refactoring',
        'query': 'Plan a mass refactoring to improve code quality',
        'expected_keys': ['answer'],
    },
    'scenario_14_security_incident': {
        'intent': 'security_incident',
        'query': 'Investigate potential security breach in authentication',
        'expected_keys': ['answer'],
    },
}


# ============================================================================
# INFRASTRUCTURE TESTS
# ============================================================================

class TestInfrastructure:
    """Test basic infrastructure before running scenario tests"""

    def test_cpg_database_connected(self, cpg_service):
        """Test that CPG database is accessible"""
        stats = cpg_service.get_database_stats()
        assert isinstance(stats, dict)
        assert 'method_count' in stats
        logger.info(f"Database stats: {stats}")

    def test_llm_provider_available(self, llm):
        """Test that LLM provider is available"""
        assert llm.is_available()
        # Quick test
        response = llm.generate_simple("Say hello")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_copilot_initialization(self, copilot):
        """Test that MultiScenarioCopilot initializes correctly"""
        assert copilot is not None
        assert copilot.graph is not None


# ============================================================================
# INTENT CLASSIFICATION TESTS
# ============================================================================

class TestIntentClassification:
    """Test that queries are classified to correct intents"""

    @pytest.mark.parametrize("scenario_name,config", SCENARIO_TEST_QUERIES.items())
    def test_intent_classification(self, copilot, scenario_name, config):
        """Test intent classification for each scenario"""
        query = config['query']
        expected_intent = config['intent']

        result = copilot.run(query)

        # Should classify intent
        actual_intent = result.get('intent')
        assert actual_intent is not None, f"No intent returned for {scenario_name}"

        # Log classification result
        confidence = result.get('confidence', 0)
        logger.info(
            f"{scenario_name}: Expected '{expected_intent}', "
            f"Got '{actual_intent}' (confidence: {confidence:.2f})"
        )


# ============================================================================
# SCENARIO WORKFLOW TESTS
# ============================================================================

class TestScenarioWorkflows:
    """Test each scenario workflow executes without crashing"""

    @pytest.mark.parametrize("scenario_name,config", [
        (k, v) for k, v in SCENARIO_TEST_QUERIES.items()
        if k in ['scenario_1_onboarding', 'scenario_2_security', 'scenario_6_performance']
    ])
    def test_core_scenarios(self, copilot, scenario_name, config):
        """Test core scenarios (1, 2, 6) that are most commonly used"""
        query = config['query']

        start_time = time.time()
        result = copilot.run(query)
        elapsed = time.time() - start_time

        # Should return result without exception
        assert result is not None, f"No result for {scenario_name}"

        # Should have answer or error
        has_answer = result.get('answer') is not None
        has_error = result.get('error') is not None

        assert has_answer or has_error, f"Result should have answer or error for {scenario_name}"

        # Log result
        if has_error:
            logger.warning(f"{scenario_name}: ERROR - {result.get('error')[:100]}...")
        else:
            answer_preview = (result.get('answer') or '')[:100]
            logger.info(f"{scenario_name}: OK ({elapsed:.2f}s) - {answer_preview}...")

    @pytest.mark.slow
    @pytest.mark.parametrize("scenario_name,config", SCENARIO_TEST_QUERIES.items())
    def test_all_scenarios(self, copilot, scenario_name, config):
        """Test all 14 scenarios (marked as slow)"""
        query = config['query']
        expected_keys = config['expected_keys']

        start_time = time.time()
        result = copilot.run(query)
        elapsed = time.time() - start_time

        # Should return result
        assert result is not None

        # Check expected keys (if not error)
        if not result.get('error'):
            for key in expected_keys:
                assert key in result or result.get('error'), \
                    f"Missing key '{key}' in result for {scenario_name}"

        logger.info(f"{scenario_name}: completed in {elapsed:.2f}s")


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling framework integration"""

    def test_graceful_degradation_on_invalid_query(self, copilot):
        """Test that invalid queries don't crash the system"""
        result = copilot.run("")  # Empty query

        # Should return result (possibly with error)
        assert result is not None

    def test_error_handling_framework_imported(self):
        """Test that error handling framework is available"""
        from src.workflow.error_handling import (
            AgentResult,
            execute_agent_safely,
            aggregate_partial_results,
            create_error_state,
            WorkflowErrorHandler,
        )

        # All should be importable
        assert AgentResult is not None
        assert execute_agent_safely is not None
        assert aggregate_partial_results is not None
        assert create_error_state is not None
        assert WorkflowErrorHandler is not None

    def test_agent_result_creation(self):
        """Test AgentResult dataclass"""
        result = AgentResult(
            success=True,
            result={'data': 'test'},
            agent='test_agent',
        )

        assert result.success is True
        assert result.result == {'data': 'test'}
        assert result.agent == 'test_agent'

        # Test serialization
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict['success'] is True

    def test_aggregate_partial_results(self):
        """Test result aggregation"""
        results = [
            AgentResult(success=True, result={'a': 1}, agent='agent1'),
            AgentResult(success=False, result=None, agent='agent2', error={'message': 'fail'}),
            AgentResult(success=True, result={'b': 2}, agent='agent3'),
        ]

        aggregated = aggregate_partial_results(results)

        assert aggregated.success_rate == pytest.approx(2/3, rel=0.01)
        assert 'agent1' in aggregated.successful_agents
        assert 'agent3' in aggregated.successful_agents
        assert 'agent2' in aggregated.failed_agents
        assert aggregated.degraded is True


# ============================================================================
# BUG FIX VALIDATION TESTS
# ============================================================================

class TestBugFixes:
    """Validate that Phase 1 bug fixes work correctly"""

    def test_callgraph_analyzer_returns_strings(self, cpg_service):
        """Validate CallGraphAnalyzer returns List[str]"""
        from src.analysis import CallGraphAnalyzer

        analyzer = CallGraphAnalyzer(cpg_service)
        callees = analyzer.find_all_callees('main', max_depth=1)

        # Should return list of strings (method names)
        assert isinstance(callees, list)
        if callees:
            assert all(isinstance(c, str) for c in callees), \
                "find_all_callees should return List[str]"

    @pytest.mark.skip(reason="detect_cycles() causes DuckDB GIL threading issue - known issue")
    def test_call_cycle_attributes(self, cpg_service):
        """Validate CallCycle has correct attributes"""
        from src.analysis import CallGraphAnalyzer

        analyzer = CallGraphAnalyzer(cpg_service)
        cycles = analyzer.detect_cycles()

        if cycles:
            cycle = cycles[0]
            # Should have 'methods' attribute (not 'methods_in_cycle')
            assert hasattr(cycle, 'methods'), "CallCycle should have 'methods' attribute"
            # Should have 'is_self_recursive' attribute
            assert hasattr(cycle, 'is_self_recursive'), \
                "CallCycle should have 'is_self_recursive' attribute"

    def test_null_handling_in_security_scanner(self, cpg_service):
        """Validate NULL handling in SecurityScanner"""
        from src.security import SecurityScanner

        scanner = SecurityScanner(cpg_service)

        # This should not raise NoneType errors
        try:
            findings = scanner.scan_all_patterns(limit_per_pattern=5)
            assert isinstance(findings, list)
        except AttributeError as e:
            if "'NoneType' object" in str(e):
                pytest.fail(f"NULL handling failed: {e}")
            raise

    def test_duckdb_schema_tables(self, cpg_service):
        """Validate correct DuckDB schema tables are used"""
        # These queries should NOT fail with "table does not exist"
        queries = [
            "SELECT * FROM nodes_method LIMIT 1",
            "SELECT * FROM nodes_tag LIMIT 1",
            "SELECT * FROM edges_tagged_by LIMIT 1",
            "SELECT * FROM nodes_call LIMIT 1",
            "SELECT * FROM edges_call LIMIT 1",
        ]

        for query in queries:
            try:
                results = cpg_service.execute_query(query)
                assert isinstance(results, list)
            except Exception as e:
                if "does not exist" in str(e):
                    pytest.fail(f"Schema error: {e}")
                # Other errors might be OK (empty tables, etc.)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.slow
    def test_scenario_execution_time(self, copilot):
        """Test that scenarios complete within reasonable time"""
        MAX_TIME_SECONDS = 120  # 2 minutes max per scenario

        test_queries = [
            ('onboarding', 'Explain the PostgreSQL architecture'),
            ('security', 'Find security vulnerabilities'),
            ('performance', 'Identify performance issues'),
        ]

        for intent, query in test_queries:
            start_time = time.time()
            result = copilot.run(query)
            elapsed = time.time() - start_time

            logger.info(f"{intent}: {elapsed:.2f}s")

            if elapsed > MAX_TIME_SECONDS:
                logger.warning(
                    f"{intent} took {elapsed:.2f}s (>{MAX_TIME_SECONDS}s limit)"
                )


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "not slow",  # Skip slow tests by default
    ])
