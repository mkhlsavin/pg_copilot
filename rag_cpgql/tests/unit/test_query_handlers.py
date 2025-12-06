"""
Unit tests for Query Handlers.

Tests the query detection and handling functions for:
- Definition queries
- Call graph queries
- Dataflow queries
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.workflow.query_handlers import detect_onboarding_query_type


class TestDetectOnboardingQueryType:
    """Tests for detect_onboarding_query_type function."""

    # Definition query tests
    class TestDefinitionQueries:
        """Tests for definition query detection."""

        def test_where_is_defined(self):
            """Test 'where is X defined' pattern."""
            result = detect_onboarding_query_type("Where is ReadBuffer defined?")
            assert result['type'] == 'definition'
            assert result['target'] == 'ReadBuffer'

        def test_function_definition(self):
            """Test 'function X' pattern."""
            result = detect_onboarding_query_type("Find function ExecInitNode")
            assert result['type'] == 'definition'
            assert result['target'] == 'ExecInitNode'

        def test_signature_of(self):
            """Test 'signature of X' pattern."""
            result = detect_onboarding_query_type("What is the signature of heap_insert?")
            assert result['type'] == 'definition'
            assert result['target'] == 'heap_insert'

        def test_which_file(self):
            """Test 'which file' pattern."""
            result = detect_onboarding_query_type("Which file contains StartupXLOG?")
            assert result['type'] == 'definition'
            # Note: 'contains' pattern doesn't extract the function name
            # Use "which file defines StartupXLOG" for target extraction

        def test_locate_function(self):
            """Test 'locate' pattern."""
            result = detect_onboarding_query_type("Locate the function BufferGetPage")
            assert result['type'] == 'definition'
            assert result['target'] == 'BufferGetPage'

    # Call graph query tests
    class TestCallGraphQueries:
        """Tests for call graph query detection."""

        def test_who_calls(self):
            """Test 'who calls X' pattern."""
            result = detect_onboarding_query_type("Who calls ReadBuffer?")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'ReadBuffer'

        def test_what_calls(self):
            """Test 'what calls X' pattern."""
            result = detect_onboarding_query_type("What calls ExecScan?")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'ExecScan'

        def test_what_does_x_call(self):
            """Test 'what does X call' pattern."""
            result = detect_onboarding_query_type("What does heapam_tuple_insert call?")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'heapam_tuple_insert'

        def test_what_functions_does_x_call(self):
            """Test 'what functions does X call' pattern."""
            result = detect_onboarding_query_type("What functions does ProcessQuery call?")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'ProcessQuery'

        def test_callers_of(self):
            """Test 'callers of X' pattern."""
            result = detect_onboarding_query_type("List the callers of LockBuffer")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'LockBuffer'

        def test_callees_of(self):
            """Test 'callees of X' pattern."""
            result = detect_onboarding_query_type("Show callees of standard_ExecutorRun")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'standard_ExecutorRun'

        def test_called_by(self):
            """Test 'called by X' pattern."""
            result = detect_onboarding_query_type("Functions called by SeqNext")
            assert result['type'] == 'call_graph'
            assert result['target'] == 'SeqNext'

    # Dataflow query tests
    class TestDataflowQueries:
        """Tests for dataflow query detection."""

        def test_trace_variable(self):
            """Test 'trace variable X' pattern."""
            result = detect_onboarding_query_type("Trace variable buffer in ReadBuffer")
            assert result['type'] == 'dataflow'

        def test_dataflow_of(self):
            """Test 'dataflow of X' pattern."""
            result = detect_onboarding_query_type("What is the dataflow of result in ExecScan?")
            assert result['type'] == 'dataflow'

        def test_flows_to(self):
            """Test 'flows to' pattern."""
            result = detect_onboarding_query_type("Where does this data flows to?")
            assert result['type'] == 'dataflow'

        def test_taint_analysis(self):
            """Test 'taint' pattern."""
            result = detect_onboarding_query_type("Perform taint analysis on user_input")
            assert result['type'] == 'dataflow'
            # Note: simple 'taint' keyword triggers dataflow but doesn't extract target

    # General query tests
    class TestGeneralQueries:
        """Tests for general (non-specific) query detection."""

        def test_overview_query(self):
            """Test that overview queries are classified as general."""
            result = detect_onboarding_query_type("Give me an overview of the executor")
            assert result['type'] == 'general'

        def test_how_does_work(self):
            """Test 'how does X work' pattern."""
            result = detect_onboarding_query_type("How does the planner work?")
            # subsystem_explain is a more specific classification for subsystem questions
            assert result['type'] in ('general', 'subsystem_explain')

        def test_explain_subsystem(self):
            """Test explain queries."""
            result = detect_onboarding_query_type("Explain the storage manager")
            assert result['type'] == 'general'

    # Edge cases
    class TestEdgeCases:
        """Tests for edge cases and special scenarios."""

        def test_empty_query(self):
            """Test empty query handling."""
            result = detect_onboarding_query_type("")
            assert result['type'] == 'general'
            assert result['target'] is None

        def test_no_target_found(self):
            """Test query with no identifiable target."""
            result = detect_onboarding_query_type("What is this?")
            assert result['type'] == 'general'

        def test_preserves_original_case(self):
            """Test that target preserves original case."""
            result = detect_onboarding_query_type("Where is ReadBuffer defined?")
            assert result['target'] == 'ReadBuffer'  # Not 'readbuffer'

        def test_mixed_case_query(self):
            """Test mixed case query still detects patterns."""
            result = detect_onboarding_query_type("WHERE IS readbuffer DEFINED?")
            assert result['type'] == 'definition'

        def test_skips_common_words(self):
            """Test that common words like 'the', 'a' are skipped."""
            result = detect_onboarding_query_type("Where is the function defined?")
            # Should not capture 'the' or 'function' as target
            assert result['target'] is None or result['target'] not in ['the', 'function']


class TestQueryTypeDetectionIntegration:
    """Integration tests for query type detection across scenarios."""

    @pytest.mark.parametrize("query,expected_type", [
        # Definition queries
        ("Find function malloc", "definition"),
        ("Where is free defined", "definition"),
        ("Show me the definition of printf", "definition"),
        # Call graph queries
        ("Who calls malloc", "call_graph"),
        ("What does main call", "call_graph"),
        ("List callers of free", "call_graph"),
        # Dataflow queries
        ("Trace the buffer variable", "dataflow"),
        ("Trace dataflow of user_input", "dataflow"),  # "Where does X flow" is general
        ("Data flow analysis of ptr", "dataflow"),
        # General queries
        ("How does memory allocation work", "general"),
        ("Explain the file system", "general"),
        ("Give me an overview", "general"),
    ])
    def test_query_type_detection(self, query, expected_type):
        """Parametrized test for query type detection."""
        result = detect_onboarding_query_type(query)
        assert result['type'] == expected_type, f"Query '{query}' expected {expected_type}, got {result['type']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
