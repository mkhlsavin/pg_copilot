"""
Integration tests for P0 Critical Fixes

Tests the blocking issues that prevent any workflow from running:
- P0-1: LLMInterface initialization fix (now uses configurable LLM provider)
- P0-2: CPGQueryService.execute_query() method implementation
- P0-3: Basic error handling

These tests validate that the fundamental infrastructure works.

Updated: November 25, 2025 - Now uses configurable LLM provider (GigaChat/local)
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Use new configurable LLM interface
from src.llm.llm_interface_compat import LLMInterface
from src.services.cpg_query_service import CPGQueryService


class TestP01_LLMInterface:
    """Test P0-1: LLMInterface initialization with configurable provider"""

    def test_llm_interface_default_initialization(self):
        """Test that LLMInterface() works with no arguments (uses config.yaml)"""
        try:
            llm = LLMInterface()
            assert llm is not None
            assert llm.is_available()
            # Provider should be initialized
            assert llm.provider is not None
        except Exception as e:
            pytest.fail(f"LLMInterface() initialization failed: {e}")

    def test_llm_interface_generate(self):
        """Test that LLMInterface.generate() returns string"""
        llm = LLMInterface()
        response = llm.generate(
            system_prompt="You are helpful. Answer in one word.",
            user_prompt="What is 1+1?"
        )
        assert isinstance(response, str)
        assert len(response) > 0

    def test_llm_interface_generate_simple(self):
        """Test that LLMInterface.generate_simple() returns string"""
        llm = LLMInterface()
        response = llm.generate_simple("Say hello")
        assert isinstance(response, str)
        assert len(response) > 0


class TestP02_CPGQueryService:
    """Test P0-2: CPGQueryService.execute_query() implementation"""

    def test_execute_query_exists(self):
        """Test that execute_query() method exists"""
        cpg = CPGQueryService()
        assert hasattr(cpg, 'execute_query')
        assert callable(cpg.execute_query)
        cpg.close()

    def test_execute_query_simple(self):
        """Test execute_query() with simple query"""
        with CPGQueryService() as cpg:
            # Simple query to count methods
            query = "SELECT COUNT(*) as count FROM nodes_method LIMIT 1"
            results = cpg.execute_query(query)

            assert isinstance(results, list)
            if results:  # May be empty if DB not populated
                assert isinstance(results[0], dict)
                assert 'count' in results[0]

    def test_execute_query_with_parameters(self):
        """Test execute_query() with parameterized query"""
        with CPGQueryService() as cpg:
            # Parameterized query
            query = "SELECT * FROM nodes_method LIMIT ?"
            results = cpg.execute_query(query, (5,))

            assert isinstance(results, list)
            assert len(results) <= 5

    def test_execute_query_returns_dicts(self):
        """Test that execute_query() returns list of dictionaries"""
        with CPGQueryService() as cpg:
            query = "SELECT id, name FROM nodes_method LIMIT 3"
            results = cpg.execute_query(query)

            assert isinstance(results, list)
            for row in results:
                assert isinstance(row, dict)
                # Should have column names as keys
                assert 'id' in row or len(row) == 0  # Empty if no data
                assert 'name' in row or len(row) == 0

    def test_execute_custom_sql_alias(self):
        """Test that execute_custom_sql() is an alias for execute_query()"""
        cpg = CPGQueryService()
        assert hasattr(cpg, 'execute_custom_sql')
        assert callable(cpg.execute_custom_sql)

        # Both should return same type
        query = "SELECT COUNT(*) as count FROM nodes_method"
        result1 = cpg.execute_query(query)
        result2 = cpg.execute_custom_sql(query)

        assert type(result1) == type(result2)
        assert isinstance(result1, list)
        cpg.close()


class TestP03_ErrorHandling:
    """Test P0-3: Basic error handling in workflows"""

    def test_execute_query_error_handling(self):
        """Test that execute_query() raises clear errors on bad queries"""
        with CPGQueryService() as cpg:
            # Invalid query should raise exception
            with pytest.raises(Exception) as exc_info:
                cpg.execute_query("SELECT * FROM nonexistent_table")

            # Error should mention query execution failed
            assert "Query execution failed" in str(exc_info.value)

    def test_cpg_service_context_manager(self):
        """Test that CPGQueryService can be used as context manager"""
        # Should not raise exception
        try:
            with CPGQueryService() as cpg:
                assert cpg.conn is not None
            # Connection should be closed after exiting context
            # (conn might still exist but should be closed)
        except Exception as e:
            pytest.fail(f"Context manager failed: {e}")


class TestP0_Integration:
    """Integration tests combining P0-1 and P0-2"""

    def test_workflow_can_initialize_llm_and_cpg(self):
        """Test that a workflow can initialize both LLM and CPG service"""
        try:
            # This is what workflows do
            llm = LLMInterface()
            with CPGQueryService() as cpg:
                assert llm is not None
                assert llm.is_available()
                assert cpg is not None
                # Basic query
                results = cpg.get_database_stats()
                assert isinstance(results, dict)
        except Exception as e:
            pytest.fail(f"Workflow initialization failed: {e}")

    def test_end_to_end_query(self):
        """Test end-to-end: LLM + CPG query + LLM interpretation"""
        llm = LLMInterface()
        with CPGQueryService() as cpg:
            # Get some data
            stats = cpg.get_database_stats()

            # Ask LLM to summarize
            response = llm.generate(
                system_prompt="You are a database analyst. Be brief.",
                user_prompt=f"The database has {stats.get('method_count', 0)} methods. Is this a large codebase?"
            )

            assert isinstance(response, str)
            assert len(response) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
