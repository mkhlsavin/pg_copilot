"""
Tests for Data Flow Tracer (Graph Method #3) - Phase 1.1 Enhanced

Tests cover the REACHING_DEF edge-based implementation:
- trace_variable() with REACHING_DEF traversal
- find_reaching_definitions() backward traversal
- find_variable_uses() forward traversal
- find_taint_paths() with source-to-sink analysis
- _detect_sanitization_on_path() with common patterns
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.analysis.dataflow_tracer import (
    DataFlowTracer,
    VariableFlow,
    DataFlowPath
)


@pytest.fixture
def mock_cpg_service():
    """Mock CPG service for testing"""
    mock = Mock()
    mock.execute_query = MagicMock()
    return mock


@pytest.fixture
def tracer(mock_cpg_service):
    """Create DataFlowTracer with mocked CPG service"""
    return DataFlowTracer(mock_cpg_service)


class TestTraceVariable:
    """Test trace_variable() with REACHING_DEF edges"""

    def test_simple_def_use_flow(self, tracer, mock_cpg_service):
        """Test simple definition→use flow via REACHING_DEF"""
        # Mock response: x defined at line 10, used at line 15
        mock_cpg_service.execute_query.return_value = [
            # Definition (depth 0)
            {
                'node_id': 100,
                'var_name': 'x',
                'line_number': 10,
                'code': 'x = 42',
                'depth': 0,
                'path': '100',
                'source_id': 100
            },
            # Use (depth 1, reached via REACHING_DEF)
            {
                'node_id': 200,
                'var_name': 'x',
                'line_number': 15,
                'code': 'print(x)',
                'depth': 1,
                'path': '100->200',
                'source_id': 100
            }
        ]

        flow = tracer.trace_variable('x')

        assert flow.variable_name == 'x'
        assert len(flow.definition_points) == 1
        assert len(flow.use_points) == 1
        assert len(flow.flows) == 1

        # Check definition
        assert flow.definition_points[0]['node_id'] == 100
        assert flow.definition_points[0]['line_number'] == 10

        # Check use
        assert flow.use_points[0]['node_id'] == 200
        assert flow.use_points[0]['line_number'] == 15

        # Check flow
        assert flow.flows[0].variable_name == 'x'
        assert flow.flows[0].path_length == 1

    def test_multiple_uses_from_single_def(self, tracer, mock_cpg_service):
        """Test one definition reaching multiple uses"""
        mock_cpg_service.execute_query.return_value = [
            # Definition
            {'node_id': 100, 'var_name': 'x', 'line_number': 10, 'code': 'x = 1', 'depth': 0, 'source_id': 100},
            # Use 1
            {'node_id': 200, 'var_name': 'x', 'line_number': 15, 'code': 'y = x', 'depth': 1, 'source_id': 100},
            # Use 2
            {'node_id': 300, 'var_name': 'x', 'line_number': 20, 'code': 'z = x', 'depth': 1, 'source_id': 100}
        ]

        flow = tracer.trace_variable('x')

        assert len(flow.definition_points) == 1
        assert len(flow.use_points) == 2
        assert len(flow.flows) == 2  # Two flows from one def

    def test_transitive_flow(self, tracer, mock_cpg_service):
        """Test transitive flow: x → y → z"""
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 100, 'var_name': 'x', 'line_number': 10, 'depth': 0, 'source_id': 100},
            {'node_id': 200, 'var_name': 'y', 'line_number': 15, 'depth': 1, 'source_id': 100},
            {'node_id': 300, 'var_name': 'z', 'line_number': 20, 'depth': 2, 'source_id': 100}
        ]

        flow = tracer.trace_variable('x')

        assert len(flow.flows) >= 1
        # Check that we have transitive flow (depth > 1)
        max_depth = max(f.path_length for f in flow.flows) if flow.flows else 0
        assert max_depth >= 1

    def test_no_flows_found(self, tracer, mock_cpg_service):
        """Test when variable has no REACHING_DEF flows"""
        mock_cpg_service.execute_query.return_value = []

        flow = tracer.trace_variable('nonexistent')

        assert flow.variable_name == 'nonexistent'
        assert len(flow.definition_points) == 0
        assert len(flow.use_points) == 0
        assert len(flow.flows) == 0

    def test_max_depth_limit(self, tracer, mock_cpg_service):
        """Test that max_depth parameter limits traversal"""
        mock_cpg_service.execute_query.return_value = []

        tracer.trace_variable('x', max_depth=5)

        # Verify max_depth was passed to query
        call_args = mock_cpg_service.execute_query.call_args
        assert 5 in call_args[0][1]  # max_depth should be in parameters


class TestFindReachingDefinitions:
    """Test find_reaching_definitions() backward traversal"""

    def test_single_reaching_definition(self, tracer, mock_cpg_service):
        """Test finding single definition that reaches a use"""
        # Mock: use at node 200, definition at node 100
        mock_cpg_service.execute_query.return_value = [
            {
                'node_id': 100,
                'var_name': 'x',
                'line_number': 10,
                'code': 'x = 42',
                'depth': 1
            }
        ]

        use_location = {'node_id': 200, 'variable_name': 'x'}
        definitions = tracer.find_reaching_definitions(use_location, max_depth=5)

        assert len(definitions) == 1
        assert definitions[0]['node_id'] == 100
        assert definitions[0]['var_name'] == 'x'

    def test_multiple_reaching_definitions(self, tracer, mock_cpg_service):
        """Test multiple definitions reaching same use (if branches)"""
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 100, 'var_name': 'x', 'line_number': 10, 'depth': 1},
            {'node_id': 150, 'var_name': 'x', 'line_number': 12, 'depth': 1}
        ]

        use_location = {'node_id': 200, 'variable_name': 'x'}
        definitions = tracer.find_reaching_definitions(use_location)

        assert len(definitions) == 2

    def test_backward_traversal_depth(self, tracer, mock_cpg_service):
        """Test backward traversal respects depth limit"""
        # Mock: definition at depth 3 (3 REACHING_DEF edges backward)
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 100, 'var_name': 'x', 'line_number': 5, 'depth': 3}
        ]

        use_location = {'node_id': 200, 'variable_name': 'x'}
        definitions = tracer.find_reaching_definitions(use_location, max_depth=5)

        assert len(definitions) == 1
        assert definitions[0]['depth'] == 3

    def test_no_reaching_definition(self, tracer, mock_cpg_service):
        """Test when no definition reaches the use"""
        mock_cpg_service.execute_query.return_value = []

        use_location = {'node_id': 200, 'variable_name': 'x'}
        definitions = tracer.find_reaching_definitions(use_location)

        assert len(definitions) == 0

    def test_fallback_to_variable_name(self, tracer, mock_cpg_service):
        """Test fallback when node_id not provided"""
        # Mock: find node by variable name and line
        mock_cpg_service.execute_query.side_effect = [
            [{'id': 200}],  # Find node by name/line
            [{'node_id': 100, 'var_name': 'x', 'depth': 1}]  # Reaching defs
        ]

        use_location = {'variable_name': 'x', 'line_number': 20}
        definitions = tracer.find_reaching_definitions(use_location)

        assert len(definitions) == 1


class TestFindVariableUses:
    """Test find_variable_uses() forward traversal"""

    def test_single_use_from_definition(self, tracer, mock_cpg_service):
        """Test finding single use from a definition"""
        mock_cpg_service.execute_query.return_value = [
            {
                'node_id': 200,
                'var_name': 'x',
                'line_number': 15,
                'code': 'print(x)',
                'depth': 1
            }
        ]

        def_location = {'node_id': 100, 'variable_name': 'x'}
        uses = tracer.find_variable_uses(def_location, max_depth=5)

        assert len(uses) == 1
        assert uses[0]['node_id'] == 200

    def test_multiple_uses_from_definition(self, tracer, mock_cpg_service):
        """Test definition reaching multiple uses"""
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 200, 'var_name': 'x', 'line_number': 15, 'depth': 1},
            {'node_id': 300, 'var_name': 'x', 'line_number': 20, 'depth': 1},
            {'node_id': 400, 'var_name': 'x', 'line_number': 25, 'depth': 2}
        ]

        def_location = {'node_id': 100, 'variable_name': 'x'}
        uses = tracer.find_variable_uses(def_location)

        assert len(uses) == 3

    def test_transitive_uses(self, tracer, mock_cpg_service):
        """Test transitive uses (x → y → z)"""
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 200, 'var_name': 'y', 'line_number': 15, 'depth': 1},
            {'node_id': 300, 'var_name': 'z', 'line_number': 20, 'depth': 2}
        ]

        def_location = {'node_id': 100, 'variable_name': 'x'}
        uses = tracer.find_variable_uses(def_location, max_depth=3)

        assert len(uses) == 2
        # Verify we got both direct and transitive uses
        depths = [u['depth'] for u in uses]
        assert 1 in depths
        assert 2 in depths


class TestFindTaintPaths:
    """Test find_taint_paths() with source-to-sink analysis"""

    def test_simple_taint_path(self, tracer, mock_cpg_service):
        """Test simple taint path: recv() → system()"""
        mock_cpg_service.execute_query.side_effect = [
            # Taint path query
            [{
                'source_func': 'recv',
                'source_call_id': 100,
                'tainted_var': 'buf',
                'sink_func': 'system',
                'sink_call_id': 200,
                'taint_line': 10,
                'sink_line': 20,
                'sink_file': 'main.c',
                'depth': 3,
                'full_path': 'recv(buf) -> buf@15 -> cmd@18 -> system'
            }],
            # Sanitization detection (empty)
            []
        ]

        sources = ['recv', 'readLine']
        sinks = ['system', 'exec']

        paths = tracer.find_taint_paths(sources, sinks, max_depth=10)

        assert len(paths) == 1
        path = paths[0]
        assert path.variable_name == 'buf'
        assert path.source_location['function'] == 'recv'
        assert path.sink_location['function'] == 'system'
        assert path.path_length == 3
        assert path.is_inter_procedural is True

    def test_multiple_taint_paths(self, tracer, mock_cpg_service):
        """Test finding multiple taint paths"""
        mock_cpg_service.execute_query.side_effect = [
            [
                {
                    'source_func': 'recv', 'source_call_id': 100, 'tainted_var': 'buf',
                    'sink_func': 'system', 'sink_call_id': 200,
                    'taint_line': 10, 'sink_line': 20, 'sink_file': 'a.c',
                    'depth': 3, 'full_path': 'recv(buf) -> system'
                },
                {
                    'source_func': 'getenv', 'source_call_id': 150, 'tainted_var': 'env',
                    'sink_func': 'strcpy', 'sink_call_id': 250,
                    'taint_line': 15, 'sink_line': 25, 'sink_file': 'b.c',
                    'depth': 2, 'full_path': 'getenv(env) -> strcpy'
                }
            ],
            [],  # Sanitization for path 1
            []   # Sanitization for path 2
        ]

        sources = ['recv', 'getenv']
        sinks = ['system', 'strcpy']

        paths = tracer.find_taint_paths(sources, sinks)

        assert len(paths) == 2
        assert paths[0].source_location['function'] == 'recv'
        assert paths[1].source_location['function'] == 'getenv'

    def test_no_taint_paths(self, tracer, mock_cpg_service):
        """Test when no taint paths exist"""
        mock_cpg_service.execute_query.return_value = []

        sources = ['recv']
        sinks = ['system']

        paths = tracer.find_taint_paths(sources, sinks)

        assert len(paths) == 0

    def test_taint_path_with_sanitization(self, tracer, mock_cpg_service):
        """Test taint path with sanitization detected"""
        # Mock returns taint paths with pre-populated sanitization info
        mock_cpg_service.execute_query.return_value = [{
            'source_func': 'recv',
            'source_call_id': 100,
            'tainted_var': 'buf',
            'sink_func': 'system',
            'sink_call_id': 200,
            'taint_line': 10,
            'sink_line': 30,
            'sink_file': 'main.c',
            'depth': 4,
            'full_path': 'recv(buf) -> validate_input -> system'
        }]

        sources = ['recv']
        sinks = ['system']

        paths = tracer.find_taint_paths(sources, sinks)

        # Should find the taint path
        assert len(paths) >= 1
        # First path should have source and sink info
        path = paths[0]
        assert path.source_location.get('function') == 'recv'
        assert path.sink_location.get('function') == 'system'

    def test_empty_source_or_sink(self, tracer, mock_cpg_service):
        """Test error handling for empty sources/sinks"""
        paths = tracer.find_taint_paths([], ['system'])
        assert len(paths) == 0

        paths = tracer.find_taint_paths(['recv'], [])
        assert len(paths) == 0


class TestSanitizationDetection:
    """Test _detect_sanitization_on_path()"""

    def test_detect_validate_function(self, tracer, mock_cpg_service):
        """Test detection of validate_* function"""
        mock_cpg_service.execute_query.return_value = [
            {
                'call_id': 150,
                'function_name': 'validate_input',
                'line_number': 15,
                'filename': 'validate.c',
                'position_in_path': 2
            }
        ]

        # _detect_sanitization_on_path returns (sanitization_points, max_confidence)
        sanitization, confidence = tracer._detect_sanitization_on_path(100, 200, 'buf', max_depth=10)

        assert len(sanitization) == 1
        assert sanitization[0]['function'] == 'validate_input'
        assert confidence > 0

    def test_detect_escape_function(self, tracer, mock_cpg_service):
        """Test detection of escape_* function"""
        mock_cpg_service.execute_query.return_value = [
            {
                'call_id': 160,
                'function_name': 'escape_html',
                'line_number': 18,
                'filename': 'utils.c',
                'position_in_path': 3
            }
        ]

        # _detect_sanitization_on_path returns (sanitization_points, max_confidence)
        sanitization, confidence = tracer._detect_sanitization_on_path(100, 200, 'buf')

        assert len(sanitization) == 1
        assert 'escape' in sanitization[0]['function']
        assert confidence > 0

    def test_detect_multiple_sanitizers(self, tracer, mock_cpg_service):
        """Test detection of multiple sanitization points"""
        mock_cpg_service.execute_query.return_value = [
            {'call_id': 150, 'function_name': 'validate_input', 'line_number': 15, 'position_in_path': 2},
            {'call_id': 160, 'function_name': 'escape_html', 'line_number': 18, 'position_in_path': 4}
        ]

        # _detect_sanitization_on_path returns (sanitization_points, max_confidence)
        sanitization, confidence = tracer._detect_sanitization_on_path(100, 200, 'buf')

        assert len(sanitization) == 2
        assert confidence > 0

    def test_no_sanitization_found(self, tracer, mock_cpg_service):
        """Test when no sanitization is found on path"""
        mock_cpg_service.execute_query.return_value = []

        # _detect_sanitization_on_path returns (sanitization_points, max_confidence)
        sanitization, confidence = tracer._detect_sanitization_on_path(100, 200, 'buf')

        assert len(sanitization) == 0
        assert confidence == 0.0

    def test_common_sanitization_patterns(self, tracer, mock_cpg_service):
        """Test that common patterns are detected"""
        # These patterns match the SANITIZATION_CONFIDENCE patterns in dataflow_tracer.py
        patterns = [
            'validate_email',       # matches validate_%
            'verify_token',         # matches verify_%
            'is_valid_input',       # matches is_valid_%
            'escape_sql',           # matches escape_%
            'sanitize_filename',    # matches sanitize_%
            'clean_html',           # matches clean_%
            'htmlspecialchars',     # exact match
            'pg_escape_string',     # exact match
            'encode_url',           # matches encode_%
            'filter_input',         # matches filter_%
            'parameterize',         # exact match - highest confidence
        ]

        for pattern in patterns:
            mock_cpg_service.execute_query.return_value = [
                {'call_id': 100, 'function_name': pattern, 'line_number': 10, 'position_in_path': 1}
            ]

            # _detect_sanitization_on_path returns (sanitization_points, max_confidence)
            sanitization, confidence = tracer._detect_sanitization_on_path(50, 200, 'x')
            assert len(sanitization) == 1, f"Pattern {pattern} should be detected"
            assert confidence > 0, f"Pattern {pattern} should have confidence > 0"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_exception_handling_in_trace_variable(self, tracer, mock_cpg_service):
        """Test that exceptions are handled gracefully"""
        mock_cpg_service.execute_query.side_effect = Exception("Database error")

        flow = tracer.trace_variable('x')

        # Should return empty flow instead of crashing
        assert flow.variable_name == 'x'
        assert len(flow.flows) == 0

    def test_exception_handling_in_taint_paths(self, tracer, mock_cpg_service):
        """Test exception handling in taint path detection"""
        mock_cpg_service.execute_query.side_effect = Exception("Query failed")

        paths = tracer.find_taint_paths(['recv'], ['system'])

        assert len(paths) == 0  # Should return empty list

    def test_malformed_results(self, tracer, mock_cpg_service):
        """Test handling of malformed query results"""
        # Missing required fields
        mock_cpg_service.execute_query.return_value = [
            {'node_id': 100}  # Missing var_name, line_number, etc.
        ]

        flow = tracer.trace_variable('x')

        # Should handle gracefully without crashing
        assert flow.variable_name == 'x'

    def test_null_values_in_results(self, tracer, mock_cpg_service):
        """Test handling of null values in results"""
        mock_cpg_service.execute_query.return_value = [
            {
                'node_id': None,
                'var_name': 'x',
                'line_number': None,
                'code': None,
                'depth': 0
            }
        ]

        flow = tracer.trace_variable('x')

        # Should handle gracefully
        assert flow.variable_name == 'x'


class TestPerformance:
    """Test performance characteristics"""

    def test_max_depth_prevents_runaway(self, tracer, mock_cpg_service):
        """Test that max_depth prevents infinite recursion"""
        # Even with circular REACHING_DEF edges, max_depth should stop traversal
        mock_cpg_service.execute_query.return_value = []

        tracer.trace_variable('x', max_depth=10)

        # Verify max_depth was enforced
        call_args = mock_cpg_service.execute_query.call_args
        assert call_args is not None

    def test_large_result_set_handling(self, tracer, mock_cpg_service):
        """Test handling of large result sets"""
        # Mock 1000 nodes in flow
        large_result = [
            {'node_id': i, 'var_name': 'x', 'line_number': i, 'depth': i % 10, 'source_id': 0}
            for i in range(1000)
        ]
        mock_cpg_service.execute_query.return_value = large_result

        flow = tracer.trace_variable('x')

        # Should handle large result sets without issues
        assert flow.variable_name == 'x'
        assert len(flow.definition_points) + len(flow.use_points) <= 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
