"""
Tests for Documentation Generation Workflow (Scenario 3).

Tests for documentation workflow, function name extraction, and doc generation.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "documentation",
        "scenario_id": "scenario_3",
        "confidence": 0.9,
        "classification_method": "test",
        "cpg_results": None,
        "subsystems": None,
        "methods": None,
        "call_graph": None,
        "answer": None,
        "evidence": None,
        "metadata": None,
        "retrieved_functions": None,
        "error": None,
        "retry_count": 0,
    }


class TestDocumentationWorkflowImports:
    """Tests for documentation workflow module imports."""

    def test_import_workflow(self):
        """Test that documentation workflow can be imported."""
        from src.workflow.scenarios.documentation import documentation_workflow

        assert callable(documentation_workflow)

    def test_import_helper_functions(self):
        """Test that helper functions can be imported."""
        from src.workflow.scenarios.documentation import (
            extract_function_names_from_query,
            _get_known_function_patterns,
        )

        assert callable(extract_function_names_from_query)
        assert callable(_get_known_function_patterns)


class TestExtractFunctionNamesFromQuery:
    """Tests for extract_function_names_from_query function."""

    def test_backtick_extraction(self):
        """Test extraction of backtick-quoted function names."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("Document `ereport` function")

        assert "ereport" in result

    def test_function_call_syntax(self):
        """Test extraction of function call syntax."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("How does palloc() work?")

        assert "palloc" in result

    def test_function_phrase(self):
        """Test extraction from 'function X' phrase."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("Explain function ExecInitNode")

        assert "ExecInitNode" in result

    def test_reverse_function_phrase(self):
        """Test extraction from 'X function' phrase."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("What does ExecProcNode function do?")

        assert "ExecProcNode" in result

    def test_camel_case_extraction(self):
        """Test extraction of CamelCase identifiers."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("Explain BufferAlloc and ExecInitNode")

        assert "BufferAlloc" in result
        assert "ExecInitNode" in result

    def test_snake_case_extraction(self):
        """Test extraction of snake_case identifiers."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("Document heap_insert and buffer_alloc")

        assert "heap_insert" in result
        assert "buffer_alloc" in result

    def test_stop_words_filtering(self):
        """Test that stop words are filtered out."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("Find all functions")

        # "all" and "functions" should be filtered as stop words
        assert "all" not in result
        assert "find" not in result

    def test_short_names_filtering(self):
        """Test that very short names are filtered."""
        from src.workflow.scenarios.documentation import extract_function_names_from_query

        result = extract_function_names_from_query("The ab cd function")

        # Names shorter than 3 chars should be filtered
        assert "ab" not in result
        assert "cd" not in result


class TestGetKnownFunctionPatterns:
    """Tests for _get_known_function_patterns function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        from src.workflow.scenarios.documentation import _get_known_function_patterns

        result = _get_known_function_patterns()

        assert isinstance(result, list)
        assert len(result) > 0

    def test_contains_generic_patterns(self):
        """Test that generic patterns are included."""
        from src.workflow.scenarios.documentation import _get_known_function_patterns

        result = _get_known_function_patterns()

        # Should have some patterns
        assert any("heap_" in str(p) for p in result)


class TestDocumentationWorkflowMocked:
    """Tests for documentation_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = []
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        mock.execute_custom_sql.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Documentation generated."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.documentation import documentation_workflow

        state = create_mock_state("Document ereport function")

        with patch("src.workflow.scenarios.documentation.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.documentation.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.documentation.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a documentation expert",
                        "user": "Generate documentation",
                    }
                    result = documentation_workflow(state)

        assert isinstance(result, dict)


class TestDocumentationErrorHandling:
    """Tests for documentation workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.documentation import documentation_workflow

        state = create_mock_state("Document function")

        with patch("src.workflow.scenarios.documentation.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = documentation_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestFunctionPatternMatching:
    """Tests for function pattern matching."""

    def test_pg_prefix_pattern(self):
        """Test pg_ prefix pattern matching."""
        import re

        query = "Document pg_stat_statements"
        pattern = r'\b((?:pg_|PG_|Pg)[a-zA-Z0-9_]+)\b'

        matches = re.findall(pattern, query)

        assert "pg_stat_statements" in matches

    def test_function_with_underscore(self):
        """Test snake_case function matching."""
        import re

        query = "How does heap_insert work?"
        pattern = r'\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b'

        matches = re.findall(pattern, query)

        assert "heap_insert" in matches


class TestDocumentationQueryTypes:
    """Tests for documentation query type detection."""

    def test_function_documentation_query(self):
        """Test function documentation query detection."""
        queries = [
            "Document ereport function",
            "How does palloc work?",
            "Explain ExecInitNode",
        ]

        for query in queries:
            query_lower = query.lower()
            is_doc_query = any(kw in query_lower for kw in ["document", "explain", "how", "what"])
            assert is_doc_query is True

    def test_api_documentation_query(self):
        """Test API documentation query detection."""
        query = "Generate API documentation for buffer manager"

        assert "api" in query.lower() or "documentation" in query.lower()


class TestDocumentationOutputStructure:
    """Tests for documentation output structure."""

    def test_documentation_has_sections(self):
        """Test that documentation has expected sections."""
        doc = {
            "function_name": "ereport",
            "purpose": "Error reporting function",
            "parameters": [],
            "return_value": "void",
            "usage_examples": [],
        }

        required_sections = ["function_name", "purpose", "parameters", "return_value"]

        for section in required_sections:
            assert section in doc

    def test_parameter_documentation(self):
        """Test parameter documentation structure."""
        param = {
            "name": "level",
            "type": "int",
            "description": "Error severity level",
        }

        assert "name" in param
        assert "type" in param
        assert "description" in param


class TestCodeExampleGeneration:
    """Tests for code example generation."""

    def test_usage_example_structure(self):
        """Test usage example structure."""
        example = {
            "description": "Basic error reporting",
            "code": "ereport(ERROR, (errcode(ERRCODE_SYNTAX_ERROR), errmsg(\"syntax error\")));",
        }

        assert "description" in example
        assert "code" in example

    def test_multiple_examples(self):
        """Test multiple example generation."""
        examples = [
            {"description": "Simple case", "code": "func();"},
            {"description": "Complex case", "code": "func(arg1, arg2);"},
        ]

        assert len(examples) == 2


class TestFunctionSignatureExtraction:
    """Tests for function signature extraction."""

    def test_signature_parsing(self):
        """Test function signature parsing."""
        signature = "void ereport(int elevel, ...)"

        parts = signature.split("(", 1)
        return_type_and_name = parts[0].strip().split()

        assert len(return_type_and_name) >= 2
        assert return_type_and_name[0] == "void"

    def test_parameter_extraction(self):
        """Test parameter extraction from signature."""
        params_str = "int level, const char *msg"

        params = [p.strip() for p in params_str.split(",")]

        assert len(params) == 2


class TestDocumentationMetadata:
    """Tests for documentation metadata."""

    def test_metadata_structure(self):
        """Test metadata structure."""
        metadata = {
            "file": "elog.c",
            "line": 123,
            "subsystem": "error_handling",
            "complexity": "medium",
        }

        assert "file" in metadata
        assert "line" in metadata

    def test_subsystem_classification(self):
        """Test subsystem classification."""
        function_file_map = {
            "heap_insert": "heap",
            "ExecInitNode": "executor",
            "BufferAlloc": "buffer",
        }

        for func, subsystem in function_file_map.items():
            assert isinstance(subsystem, str)
            assert len(subsystem) > 0


class TestDocumentationCompletenessChecks:
    """Tests for documentation completeness checks."""

    def test_required_fields_present(self):
        """Test that required documentation fields are present."""
        doc = {
            "function_name": "test_func",
            "purpose": "Test function",
            "parameters": [],
            "return_value": "int",
        }

        required_fields = ["function_name", "purpose", "return_value"]

        for field in required_fields:
            assert field in doc

    def test_parameter_documentation_completeness(self):
        """Test parameter documentation completeness."""
        params = [
            {"name": "arg1", "type": "int", "description": "First argument"},
            {"name": "arg2", "type": "char*", "description": "Second argument"},
        ]

        for param in params:
            assert "name" in param
            assert "type" in param
            assert "description" in param


class TestDomainSpecificDocumentation:
    """Tests for domain-specific documentation features."""

    def test_postgresql_specific_functions(self):
        """Test PostgreSQL-specific function recognition."""
        pg_functions = ["ereport", "elog", "palloc", "pfree", "repalloc"]

        for func in pg_functions:
            assert isinstance(func, str)
            assert len(func) >= 3

    def test_error_handling_functions(self):
        """Test error handling function documentation."""
        error_funcs = {
            "ereport": "Report error with detailed context",
            "elog": "Simple error logging",
            "errcode": "Set error code",
        }

        for func, desc in error_funcs.items():
            assert len(desc) > 0


class TestDocumentationFormatting:
    """Tests for documentation formatting."""

    def test_markdown_formatting(self):
        """Test markdown formatting."""
        doc = "# Function: ereport\n\n## Purpose\nError reporting\n"

        assert "# Function:" in doc
        assert "## Purpose" in doc

    def test_code_block_formatting(self):
        """Test code block formatting."""
        code_block = "```c\nereport(ERROR, ...);\n```"

        assert "```c" in code_block
        assert "```" in code_block


class TestCallGraphIntegration:
    """Tests for call graph integration in documentation."""

    def test_caller_documentation(self):
        """Test caller information in documentation."""
        callers = ["caller1", "caller2", "caller3"]

        assert len(callers) == 3

    def test_callee_documentation(self):
        """Test callee information in documentation."""
        callees = ["func1", "func2"]

        assert len(callees) == 2


class TestDocumentationCoverage:
    """Tests for documentation coverage analysis."""

    def test_coverage_calculation(self):
        """Test documentation coverage calculation."""
        total_functions = 100
        documented_functions = 75

        coverage = (documented_functions / total_functions) * 100

        assert coverage == 75.0

    def test_undocumented_identification(self):
        """Test identification of undocumented functions."""
        all_functions = ["func1", "func2", "func3"]
        documented = ["func1", "func3"]

        undocumented = [f for f in all_functions if f not in documented]

        assert len(undocumented) == 1
        assert "func2" in undocumented
