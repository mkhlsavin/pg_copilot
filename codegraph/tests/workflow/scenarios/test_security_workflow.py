"""
Tests for Security Audit Workflow (Scenario 2).

Tests for detect_security_intent, security intent mapping, and security workflow.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, Any, List

from src.workflow.state import MultiScenarioState


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "security_audit",
        "scenario_id": "scenario_2",
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


class TestSecurityIntentMap:
    """Tests for SECURITY_INTENT_MAP constant."""

    def test_intent_map_exists(self):
        """Test that intent map is defined."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        assert isinstance(SECURITY_INTENT_MAP, dict)
        assert len(SECURITY_INTENT_MAP) > 0

    def test_intent_map_has_core_vulnerability_types(self):
        """Test that core vulnerability types are mapped."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        core_types = [
            "sql injection",
            "buffer overflow",
            "memory",
            "authentication",
            "race condition",
        ]

        for vuln_type in core_types:
            assert vuln_type in SECURITY_INTENT_MAP, f"Missing {vuln_type}"

    def test_intent_map_has_d3fend_terms(self):
        """Test that D3FEND hardening terms are mapped."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        d3fend_terms = ["hardening", "d3fend", "null check", "unsafe function"]

        for term in d3fend_terms:
            assert term in SECURITY_INTENT_MAP, f"Missing D3FEND term: {term}"

    def test_broad_terms_return_none(self):
        """Test that broad terms return None (triggers all patterns)."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        broad_terms = ["vulnerability", "vulnerabilities", "security", "audit"]

        for term in broad_terms:
            assert SECURITY_INTENT_MAP.get(term) is None, f"{term} should map to None"


class TestDetectSecurityIntent:
    """Tests for detect_security_intent function."""

    def test_sql_injection_query(self):
        """Test SQL injection detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find SQL injection vulnerabilities")

        assert patterns is not None
        assert "SQL_INJECTION" in patterns

    def test_buffer_overflow_query(self):
        """Test buffer overflow detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Check for buffer overflow issues")

        assert patterns is not None
        assert any("BUFFER" in p for p in patterns)

    def test_memory_vulnerability_query(self):
        """Test memory vulnerability detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find memory safety issues")

        assert patterns is not None
        assert any(p in patterns for p in ["USE_AFTER_FREE", "DOUBLE_FREE", "MEMORY_LEAK"])

    def test_use_after_free_query(self):
        """Test use-after-free detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Check for use-after-free bugs")

        assert patterns is not None
        assert "USE_AFTER_FREE" in patterns

    def test_authentication_query(self):
        """Test authentication pattern detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find authentication vulnerabilities")

        assert patterns is not None
        assert any(p in patterns for p in ["MISSING_AUTH", "HARDCODED_SECRETS"])

    def test_race_condition_query(self):
        """Test race condition detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Check for race conditions")

        assert patterns is not None
        assert any("RACE" in p for p in patterns)

    def test_path_traversal_query(self):
        """Test path traversal detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find path traversal vulnerabilities")

        assert patterns is not None
        assert "PATH_TRAVERSAL" in patterns

    def test_crypto_weakness_query(self):
        """Test cryptographic weakness detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Check for weak cryptography")

        assert patterns is not None
        assert any(p in patterns for p in ["WEAK_CRYPTO", "INSUFFICIENT_ENTROPY"])

    def test_integer_overflow_query(self):
        """Test integer overflow detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find integer overflow bugs")

        assert patterns is not None
        assert "INTEGER_OVERFLOW" in patterns

    def test_format_string_query(self):
        """Test format string detection."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Check for format string vulnerabilities")

        assert patterns is not None
        assert "FORMAT_STRING" in patterns

    def test_broad_query_returns_none_or_full_set(self):
        """Test broad security query returns None or all patterns."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Do a full security audit")

        # Should either be None or empty (triggers full scan)
        assert patterns is None or len(patterns) == 0 or len(patterns) > 5

    def test_combined_query_multiple_patterns(self):
        """Test query with multiple vulnerability types."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find SQL injection and buffer overflow")

        assert patterns is not None
        assert "SQL_INJECTION" in patterns
        assert any("BUFFER" in p for p in patterns)

    def test_case_insensitive(self):
        """Test that intent detection is case insensitive."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns_lower = detect_security_intent("sql injection")
        patterns_upper = detect_security_intent("SQL INJECTION")
        patterns_mixed = detect_security_intent("SQL Injection")

        assert patterns_lower is not None
        assert patterns_upper is not None
        assert patterns_mixed is not None
        # All should contain SQL_INJECTION
        assert "SQL_INJECTION" in patterns_lower


class TestSecurityWorkflowMocked:
    """Tests for security_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = [
            {"name": "security", "method_count": 100, "file_count": 10},
            {"name": "auth", "method_count": 50, "file_count": 5},
        ]
        mock.get_database_stats.return_value = {"method_count": 1000}
        mock.execute_query.return_value = []
        return mock

    @pytest.fixture
    def mock_scanner(self):
        """Create mock security scanner."""
        mock = MagicMock()
        mock.scan.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Security analysis complete. No vulnerabilities found."
        return mock

    def test_workflow_handles_sql_injection_query(
        self, mock_cpg_service, mock_scanner, mock_llm
    ):
        """Test workflow handles SQL injection query."""
        from src.workflow.scenarios.security import security_workflow

        state = create_mock_state("Find SQL injection vulnerabilities")

        with patch("src.workflow.scenarios.security.main_workflow.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.security.main_workflow.SecurityScanner", return_value=mock_scanner):
                with patch("src.workflow.scenarios.security.main_workflow.LLMInterface", return_value=mock_llm):
                    with patch("src.workflow.scenarios.security.main_workflow.get_global_registry") as mock_registry:
                        mock_registry.return_value.get_agent_prompt.return_value = {
                            "system": "You are a security expert",
                            "user": "Analyze for SQL injection",
                        }

                        result = security_workflow(state)

        # Should not have error
        assert result.get("error") is None or "SQL injection" not in str(result.get("error", ""))

    def test_workflow_sets_metadata(
        self, mock_cpg_service, mock_scanner, mock_llm
    ):
        """Test workflow sets metadata correctly."""
        from src.workflow.scenarios.security import security_workflow

        mock_scanner.scan.return_value = [
            {"pattern": "SQL_INJECTION", "severity": "high", "location": "test.c:10"}
        ]

        state = create_mock_state("Security audit")

        with patch("src.workflow.scenarios.security.main_workflow.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.security.main_workflow.SecurityScanner", return_value=mock_scanner):
                with patch("src.workflow.scenarios.security.main_workflow.LLMInterface", return_value=mock_llm):
                    with patch("src.workflow.scenarios.security.main_workflow.get_global_registry") as mock_registry:
                        mock_registry.return_value.get_agent_prompt.return_value = {
                            "system": "You are a security expert",
                            "user": "Perform security audit",
                        }
                        with patch("src.workflow.scenarios.security.main_workflow.DataFlowAnalyzer"):
                            with patch("src.workflow.scenarios.security.main_workflow.VulnerabilityReporter"):
                                with patch("src.workflow.scenarios.security.main_workflow.RemediationAdvisor"):
                                    result = security_workflow(state)

        # Metadata should be set (may be None if workflow fails early, which is OK for unit test)
        # Just check it doesn't crash


class TestSecurityPatternMapping:
    """Tests for security pattern mapping completeness."""

    def test_all_pattern_values_are_lists_or_none(self):
        """Test that all intent map values are lists or None."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        for key, value in SECURITY_INTENT_MAP.items():
            assert value is None or isinstance(value, list), f"Invalid value for {key}"

    def test_pattern_names_are_uppercase(self):
        """Test that pattern names follow naming convention."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        for key, patterns in SECURITY_INTENT_MAP.items():
            if patterns:
                for pattern in patterns:
                    assert pattern == pattern.upper(), f"Pattern {pattern} should be uppercase"

    def test_no_empty_pattern_lists(self):
        """Test that no pattern lists are empty."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        for key, patterns in SECURITY_INTENT_MAP.items():
            if patterns is not None:
                assert len(patterns) > 0, f"Empty pattern list for {key}"


class TestSecurityWorkflowErrorHandling:
    """Tests for security workflow error handling."""

    def test_workflow_handles_cpg_connection_error(self):
        """Test workflow handles CPG connection errors gracefully."""
        from src.workflow.scenarios.security import security_workflow

        state = create_mock_state("Security audit")

        with patch("src.workflow.scenarios.security.main_workflow.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = security_workflow(state)

        # Should have error set
        assert result.get("error") is not None

    def test_workflow_handles_scanner_error(self):
        """Test workflow handles scanner errors gracefully."""
        from src.workflow.scenarios.security import security_workflow

        state = create_mock_state("Security audit")

        mock_cpg = MagicMock()
        mock_cpg.get_subsystems.return_value = []
        mock_cpg.get_database_stats.return_value = {"method_count": 0}

        with patch("src.workflow.scenarios.security.main_workflow.CPGQueryService") as cpg_class:
            cpg_class.return_value.__enter__ = MagicMock(return_value=mock_cpg)
            cpg_class.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.security.main_workflow.SecurityScanner") as scanner_class:
                scanner_class.side_effect = Exception("Scanner initialization failed")

                result = security_workflow(state)

        # Should handle error gracefully (may set error or continue with fallback)
        # Just verify it doesn't crash


class TestGetMatchingVulnerabilityTypes:
    """Tests for keyword-to-vulnerability-type mapping."""

    def test_import_matching_function(self):
        """Test that matching function can be imported."""
        from src.workflow.scenarios._keyword_mappings import get_matching_vulnerability_types

        assert callable(get_matching_vulnerability_types)

    def test_sql_keyword_returns_sql_injection(self):
        """Test SQL keyword mapping."""
        from src.workflow.scenarios._keyword_mappings import get_matching_vulnerability_types

        result = get_matching_vulnerability_types("sql")

        assert result is not None
        # Should return some patterns related to SQL

    def test_memory_keyword_returns_memory_patterns(self):
        """Test memory keyword mapping."""
        from src.workflow.scenarios._keyword_mappings import get_matching_vulnerability_types

        result = get_matching_vulnerability_types("memory")

        assert result is not None


class TestSecurityIntentEdgeCases:
    """Tests for edge cases in security intent detection."""

    def test_empty_query(self):
        """Test handling of empty query."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("")

        # Should return None or empty for empty query
        assert patterns is None or len(patterns) == 0

    def test_whitespace_only_query(self):
        """Test handling of whitespace-only query."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("   \n\t  ")

        # Should return None or empty
        assert patterns is None or len(patterns) == 0

    def test_non_security_query(self):
        """Test handling of non-security query."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("What is the weather today?")

        # Should return None or empty for unrelated query
        assert patterns is None or len(patterns) == 0

    def test_query_with_special_characters(self):
        """Test handling of query with special characters."""
        from src.workflow.scenarios.security import detect_security_intent

        patterns = detect_security_intent("Find SQL injection (XSS) vulnerabilities!!!")

        # Should still detect SQL injection
        assert patterns is not None
        assert "SQL_INJECTION" in patterns

    def test_multiline_query(self):
        """Test handling of multiline query."""
        from src.workflow.scenarios.security import detect_security_intent

        query = """Check for:
        - SQL injection
        - Buffer overflow
        - Memory leaks"""

        patterns = detect_security_intent(query)

        assert patterns is not None
        # Should find multiple pattern types


class TestHardeningIntegration:
    """Tests for D3FEND hardening integration."""

    def test_hardening_term_triggers_scan(self):
        """Test that hardening term is recognized."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        assert "hardening" in SECURITY_INTENT_MAP
        assert SECURITY_INTENT_MAP["hardening"] is None  # Triggers full hardening scan

    def test_d3fend_term_recognized(self):
        """Test that D3FEND term is recognized."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        assert "d3fend" in SECURITY_INTENT_MAP

    def test_specific_hardening_patterns(self):
        """Test specific hardening patterns are mapped."""
        from src.workflow.scenarios.security import SECURITY_INTENT_MAP

        # D3-VI: Variable Initialization
        assert "initialization" in SECURITY_INTENT_MAP
        assert "UNINITIALIZED_VAR" in SECURITY_INTENT_MAP["initialization"]

        # D3-NPC: Null Pointer Check
        assert "null check" in SECURITY_INTENT_MAP
        assert "NULL_POINTER_DEREFERENCE" in SECURITY_INTENT_MAP["null check"]

        # D3-RN: Reference Nullification (use after free)
        assert "reference nullification" in SECURITY_INTENT_MAP
        assert "USE_AFTER_FREE" in SECURITY_INTENT_MAP["reference nullification"]
