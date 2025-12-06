"""
Unit tests for Workflow State definitions.

Tests the state classes and helper functions used across all workflow scenarios.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.workflow.state import (
    MultiScenarioState,
    SecurityWorkflowState,
    PerformanceWorkflowState,
    ArchitectureWorkflowState,
    create_initial_state,
)


class TestMultiScenarioState:
    """Tests for MultiScenarioState TypedDict."""

    def test_create_state_manually(self):
        """Test creating a state manually with all fields."""
        state: MultiScenarioState = {
            'query': 'test query',
            'context': {'file': 'test.c'},
            'intent': 'security',
            'scenario_id': 'scenario_2',
            'confidence': 0.95,
            'classification_method': 'keyword',
            'cpg_results': [{'name': 'func1'}],
            'subsystems': ['executor'],
            'methods': [{'name': 'test_method'}],
            'call_graph': None,
            'answer': 'Test answer',
            'evidence': ['evidence 1'],
            'metadata': {'key': 'value'},
            'retrieved_functions': ['func1', 'func2'],
            'error': None,
            'retry_count': 0,
        }
        assert state['query'] == 'test query'
        assert state['intent'] == 'security'
        assert state['confidence'] == 0.95

    def test_state_with_none_values(self):
        """Test that state accepts None for optional fields."""
        state: MultiScenarioState = {
            'query': 'test',
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
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0,
        }
        assert state['query'] == 'test'
        assert state['intent'] is None

    def test_state_update(self):
        """Test updating state values."""
        state: MultiScenarioState = {
            'query': 'initial',
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
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0,
        }

        # Update intent
        state['intent'] = 'security'
        state['confidence'] = 0.9
        state['answer'] = 'Found vulnerabilities'

        assert state['intent'] == 'security'
        assert state['confidence'] == 0.9
        assert state['answer'] == 'Found vulnerabilities'


class TestCreateInitialState:
    """Tests for create_initial_state helper function."""

    def test_create_with_query_only(self):
        """Test creating initial state with just a query."""
        state = create_initial_state("Find SQL injection vulnerabilities")

        assert state['query'] == "Find SQL injection vulnerabilities"
        assert state['context'] is None
        assert state['intent'] is None
        assert state['scenario_id'] is None
        assert state['confidence'] is None
        assert state['classification_method'] is None
        assert state['cpg_results'] is None
        assert state['subsystems'] is None
        assert state['methods'] is None
        assert state['call_graph'] is None
        assert state['answer'] is None
        assert state['evidence'] is None
        assert state['metadata'] is None
        assert state['retrieved_functions'] is None
        assert state['error'] is None
        assert state['retry_count'] == 0

    def test_create_with_context(self):
        """Test creating initial state with context."""
        context = {
            'file': 'src/backend/executor/execMain.c',
            'subsystem': 'executor',
        }
        state = create_initial_state("Explain this function", context=context)

        assert state['query'] == "Explain this function"
        assert state['context'] == context
        assert state['context']['file'] == 'src/backend/executor/execMain.c'

    def test_create_returns_typed_dict(self):
        """Test that create_initial_state returns a proper TypedDict."""
        state = create_initial_state("test query")

        # TypedDict acts like a dict
        assert isinstance(state, dict)
        assert 'query' in state
        assert 'intent' in state
        assert 'retry_count' in state

    def test_state_is_mutable(self):
        """Test that the returned state can be modified."""
        state = create_initial_state("test query")

        # Modify the state
        state['intent'] = 'performance'
        state['confidence'] = 0.85
        state['answer'] = 'Performance analysis complete'

        assert state['intent'] == 'performance'
        assert state['confidence'] == 0.85
        assert state['answer'] == 'Performance analysis complete'

    def test_retry_count_initialized_to_zero(self):
        """Test that retry_count starts at 0."""
        state = create_initial_state("test")
        assert state['retry_count'] == 0

    def test_empty_query(self):
        """Test creating state with empty query."""
        state = create_initial_state("")
        assert state['query'] == ""

    def test_long_query(self):
        """Test creating state with long query."""
        long_query = "A" * 10000
        state = create_initial_state(long_query)
        assert state['query'] == long_query
        assert len(state['query']) == 10000


class TestSecurityWorkflowState:
    """Tests for SecurityWorkflowState TypedDict."""

    def test_create_security_state(self):
        """Test creating a security-specific state."""
        state: SecurityWorkflowState = {
            'query': 'Find buffer overflows',
            'context': None,
            'intent': 'security',
            'vulnerabilities': [
                {'id': 'VULN-001', 'type': 'buffer_overflow', 'severity': 'high'}
            ],
            'taint_paths': [
                {'source': 'user_input', 'sink': 'strcpy'}
            ],
            'security_findings': [],
            'risk_score': 0.85,
            'answer': 'Found 1 vulnerability',
            'evidence': ['strcpy at line 42'],
            'error': None,
        }

        assert state['intent'] == 'security'
        assert len(state['vulnerabilities']) == 1
        assert state['risk_score'] == 0.85


class TestPerformanceWorkflowState:
    """Tests for PerformanceWorkflowState TypedDict."""

    def test_create_performance_state(self):
        """Test creating a performance-specific state."""
        state: PerformanceWorkflowState = {
            'query': 'Find hotspots',
            'context': None,
            'intent': 'performance',
            'hotspots': [
                {'function': 'expensive_loop', 'complexity': 'O(n^2)'}
            ],
            'complexity_metrics': {
                'cyclomatic': 15,
                'cognitive': 20,
            },
            'bottlenecks': [],
            'optimization_suggestions': ['Use hash table instead of nested loop'],
            'answer': 'Found 1 hotspot',
            'evidence': ['O(n^2) loop at line 100'],
            'error': None,
        }

        assert state['intent'] == 'performance'
        assert len(state['hotspots']) == 1
        assert state['complexity_metrics']['cyclomatic'] == 15


class TestArchitectureWorkflowState:
    """Tests for ArchitectureWorkflowState TypedDict."""

    def test_create_architecture_state(self):
        """Test creating an architecture-specific state."""
        state: ArchitectureWorkflowState = {
            'query': 'Find circular dependencies',
            'context': None,
            'intent': 'architecture',
            'dependencies': [
                {'from': 'module_a', 'to': 'module_b'}
            ],
            'layer_violations': [],
            'circular_deps': [
                {'cycle': ['module_a', 'module_b', 'module_a']}
            ],
            'subsystem_info': {
                'name': 'executor',
                'files': 50,
            },
            'answer': 'Found 1 circular dependency',
            'evidence': ['Cycle: module_a -> module_b -> module_a'],
            'error': None,
        }

        assert state['intent'] == 'architecture'
        assert len(state['circular_deps']) == 1
        assert state['subsystem_info']['name'] == 'executor'


class TestStateWorkflowIntegration:
    """Integration tests simulating state flow through a workflow."""

    def test_state_flow_simulation(self):
        """Simulate how state flows through a typical workflow."""
        # 1. Create initial state
        state = create_initial_state(
            "Find SQL injection vulnerabilities",
            context={'subsystem': 'executor'}
        )

        # 2. Simulate intent classification
        state['intent'] = 'security'
        state['scenario_id'] = 'scenario_2'
        state['confidence'] = 0.92
        state['classification_method'] = 'keyword'

        # 3. Simulate CPG query results
        state['cpg_results'] = [
            {'name': 'pg_exec_query', 'file': 'exec.c'},
            {'name': 'SPI_execute', 'file': 'spi.c'},
        ]
        state['subsystems'] = ['executor', 'spi']
        state['methods'] = [
            {'name': 'pg_exec_query', 'line': 100},
            {'name': 'SPI_execute', 'line': 200},
        ]

        # 4. Simulate answer generation
        state['answer'] = "Found 2 potential SQL injection entry points"
        state['evidence'] = [
            "pg_exec_query in exec.c:100 accepts user input",
            "SPI_execute in spi.c:200 lacks proper sanitization",
        ]
        state['metadata'] = {
            'total_findings': 2,
            'severity': 'high',
        }
        state['retrieved_functions'] = ['pg_exec_query', 'SPI_execute']

        # Verify final state
        assert state['query'] == "Find SQL injection vulnerabilities"
        assert state['intent'] == 'security'
        assert state['confidence'] == 0.92
        assert len(state['cpg_results']) == 2
        assert len(state['evidence']) == 2
        assert state['error'] is None

    def test_error_handling_flow(self):
        """Simulate error handling in workflow state."""
        state = create_initial_state("Invalid query")

        # Simulate an error occurring
        state['intent'] = 'unknown'
        state['error'] = "Could not classify intent"
        state['retry_count'] = 1

        assert state['error'] is not None
        assert state['retry_count'] == 1
        assert state['answer'] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
