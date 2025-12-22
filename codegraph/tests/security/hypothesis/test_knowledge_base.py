"""
Tests for Security Knowledge Base.

Tests for:
- CWE_DATABASE entries
- CAPEC_DATABASE entries
- C_DANGEROUS_SINKS patterns
- C_TAINT_SOURCES patterns
- C_SANITIZERS patterns
- C_LANGUAGE_PATTERNS
- SecurityKnowledgeBase class
- get_knowledge_base singleton
"""

import pytest
from unittest.mock import patch, MagicMock

from src.security.hypothesis.models import Severity, CWEEntry, CAPECPattern, LanguagePattern
from src.security.hypothesis.knowledge_base import (
    CWE_DATABASE,
    CAPEC_DATABASE,
    C_DANGEROUS_SINKS,
    C_TAINT_SOURCES,
    C_SANITIZERS,
    C_LANGUAGE_PATTERNS,
    SecurityKnowledgeBase,
    get_knowledge_base,
)


# =============================================================================
# CWE Database Tests
# =============================================================================

class TestCWEDatabase:
    """Tests for CWE_DATABASE."""

    def test_cwe_database_not_empty(self):
        """Test CWE database contains entries."""
        assert len(CWE_DATABASE) > 0

    def test_cwe_database_minimum_entries(self):
        """Test CWE database has minimum expected entries."""
        # Should have at least common CWEs
        assert len(CWE_DATABASE) >= 20

    def test_cwe_database_critical_entries(self):
        """Test critical CWEs are present."""
        critical_cwes = ["CWE-120", "CWE-119", "CWE-787", "CWE-78", "CWE-89"]
        for cwe_id in critical_cwes:
            assert cwe_id in CWE_DATABASE, f"{cwe_id} should be in database"

    def test_cwe_entries_are_valid(self):
        """Test all CWE entries have required fields."""
        for cwe_id, cwe in CWE_DATABASE.items():
            assert isinstance(cwe, CWEEntry)
            assert cwe.id == cwe_id
            assert len(cwe.name) > 0
            assert cwe.severity in Severity
            assert 0 <= cwe.cvss_base <= 10
            assert len(cwe.languages) > 0
            assert 0 <= cwe.prevalence <= 1
            assert 0 <= cwe.exploitability <= 1

    def test_cwe_severity_distribution(self):
        """Test CWE database has entries at various severities."""
        severities = {cwe.severity for cwe in CWE_DATABASE.values()}
        assert Severity.CRITICAL in severities
        assert Severity.HIGH in severities

    def test_cwe_c_language_coverage(self):
        """Test CWE database has C language entries."""
        c_cwes = [cwe for cwe in CWE_DATABASE.values() if "C" in cwe.languages]
        assert len(c_cwes) > 10

    def test_cwe_buffer_overflow_entry(self):
        """Test buffer overflow CWE-120 entry is correct."""
        cwe = CWE_DATABASE["CWE-120"]
        assert cwe.name == "Buffer Copy without Checking Size of Input"
        assert cwe.severity == Severity.CRITICAL
        assert cwe.cvss_base >= 9.0
        assert "C" in cwe.languages
        assert "CWE-119" in cwe.related_cwes

    def test_cwe_command_injection_entry(self):
        """Test command injection CWE-78 entry is correct."""
        cwe = CWE_DATABASE["CWE-78"]
        assert "Command Injection" in cwe.name
        assert cwe.severity == Severity.CRITICAL
        assert "C" in cwe.languages


# =============================================================================
# CAPEC Database Tests
# =============================================================================

class TestCAPECDatabase:
    """Tests for CAPEC_DATABASE."""

    def test_capec_database_not_empty(self):
        """Test CAPEC database contains entries."""
        assert len(CAPEC_DATABASE) > 0

    def test_capec_database_minimum_entries(self):
        """Test CAPEC database has minimum expected entries."""
        assert len(CAPEC_DATABASE) >= 5

    def test_capec_critical_patterns(self):
        """Test critical attack patterns are present."""
        critical_capecs = ["CAPEC-100", "CAPEC-88", "CAPEC-66"]
        for capec_id in critical_capecs:
            assert capec_id in CAPEC_DATABASE, f"{capec_id} should be in database"

    def test_capec_entries_are_valid(self):
        """Test all CAPEC entries have required fields."""
        for capec_id, capec in CAPEC_DATABASE.items():
            assert isinstance(capec, CAPECPattern)
            assert capec.id == capec_id
            assert len(capec.name) > 0
            assert len(capec.related_cwes) > 0
            assert capec.typical_severity in Severity

    def test_capec_buffer_overflow_pattern(self):
        """Test CAPEC-100 buffer overflow pattern."""
        capec = CAPEC_DATABASE["CAPEC-100"]
        assert capec.name == "Overflow Buffers"
        assert "CWE-120" in capec.related_cwes
        assert len(capec.attack_steps) > 0

    def test_capec_cwe_relationships(self):
        """Test CAPEC entries have at least some valid CWE relationships."""
        for capec in CAPEC_DATABASE.values():
            # At least one related CWE should be in the CWE database
            found_in_db = any(cwe_id in CWE_DATABASE for cwe_id in capec.related_cwes)
            assert found_in_db, f"No related CWEs from {capec.id} found in CWE database"

    def test_capec_skill_levels(self):
        """Test CAPEC skill levels are valid."""
        valid_skills = {"Low", "Medium", "High", "Expert"}
        for capec in CAPEC_DATABASE.values():
            assert capec.skill_level in valid_skills


# =============================================================================
# Language Pattern Tests
# =============================================================================

class TestCDangerousSinks:
    """Tests for C_DANGEROUS_SINKS."""

    def test_memory_sinks_exist(self):
        """Test memory sinks are defined."""
        assert "memory" in C_DANGEROUS_SINKS
        assert "strcpy" in C_DANGEROUS_SINKS["memory"]
        assert "memcpy" in C_DANGEROUS_SINKS["memory"]

    def test_format_sinks_exist(self):
        """Test format string sinks are defined."""
        assert "format" in C_DANGEROUS_SINKS
        assert "printf" in C_DANGEROUS_SINKS["format"]
        assert "sprintf" in C_DANGEROUS_SINKS["format"]

    def test_command_sinks_exist(self):
        """Test command execution sinks are defined."""
        assert "command" in C_DANGEROUS_SINKS
        assert "system" in C_DANGEROUS_SINKS["command"]
        assert "popen" in C_DANGEROUS_SINKS["command"]

    def test_file_sinks_exist(self):
        """Test file operation sinks are defined."""
        assert "file" in C_DANGEROUS_SINKS


class TestCTaintSources:
    """Tests for C_TAINT_SOURCES."""

    def test_network_sources_exist(self):
        """Test network sources are defined."""
        assert "network" in C_TAINT_SOURCES
        assert "recv" in C_TAINT_SOURCES["network"]

    def test_file_sources_exist(self):
        """Test file sources are defined."""
        assert "file" in C_TAINT_SOURCES
        assert "fgets" in C_TAINT_SOURCES["file"]

    def test_user_input_sources_exist(self):
        """Test user input sources are defined."""
        assert "user_input" in C_TAINT_SOURCES
        assert "getenv" in C_TAINT_SOURCES["user_input"]


class TestCSanitizers:
    """Tests for C_SANITIZERS."""

    def test_bounds_check_sanitizers(self):
        """Test bounds checking sanitizers."""
        assert "bounds_check" in C_SANITIZERS
        assert "sizeof" in C_SANITIZERS["bounds_check"]

    def test_safe_string_sanitizers(self):
        """Test safe string function sanitizers."""
        assert "safe_string" in C_SANITIZERS
        assert "snprintf" in C_SANITIZERS["safe_string"]


class TestCLanguagePatterns:
    """Tests for C_LANGUAGE_PATTERNS."""

    def test_patterns_not_empty(self):
        """Test language patterns list is not empty."""
        assert len(C_LANGUAGE_PATTERNS) > 0

    def test_patterns_are_language_pattern_type(self):
        """Test all patterns are LanguagePattern instances."""
        for pattern in C_LANGUAGE_PATTERNS:
            assert isinstance(pattern, LanguagePattern)

    def test_buffer_overflow_pattern(self):
        """Test buffer overflow pattern exists."""
        patterns = [p for p in C_LANGUAGE_PATTERNS if p.category == "buffer_overflow"]
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern.language == "C"
        assert "strcpy" in pattern.sinks
        assert "CWE-120" in pattern.related_cwes

    def test_command_injection_pattern(self):
        """Test command injection pattern exists."""
        patterns = [p for p in C_LANGUAGE_PATTERNS if p.category == "command_injection"]
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert "system" in pattern.sinks
        assert "CWE-78" in pattern.related_cwes

    def test_format_string_pattern(self):
        """Test format string pattern exists."""
        patterns = [p for p in C_LANGUAGE_PATTERNS if p.category == "format_string"]
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert "printf" in pattern.sinks


# =============================================================================
# SecurityKnowledgeBase Tests
# =============================================================================

class TestSecurityKnowledgeBase:
    """Tests for SecurityKnowledgeBase class."""

    @pytest.fixture
    def kb(self):
        """Create a knowledge base instance."""
        return SecurityKnowledgeBase(providers=[])  # No providers for isolated testing

    def test_kb_initialization(self, kb):
        """Test knowledge base initializes correctly."""
        assert kb.cwe_db is not None
        assert kb.capec_db is not None
        assert kb.c_patterns is not None

    def test_kb_get_cwe_exists(self, kb):
        """Test get_cwe returns existing CWE."""
        cwe = kb.get_cwe("CWE-120")
        assert cwe is not None
        assert cwe.id == "CWE-120"

    def test_kb_get_cwe_not_exists(self, kb):
        """Test get_cwe returns None for non-existent CWE."""
        cwe = kb.get_cwe("CWE-99999")
        assert cwe is None

    def test_kb_get_cwes_by_severity(self, kb):
        """Test get_cwes_by_severity returns correct entries."""
        critical = kb.get_cwes_by_severity(Severity.CRITICAL)
        assert len(critical) > 0
        for cwe in critical:
            assert cwe.severity == Severity.CRITICAL

    def test_kb_get_cwes_by_language(self, kb):
        """Test get_cwes_by_language returns C language CWEs."""
        c_cwes = kb.get_cwes_by_language("C")
        assert len(c_cwes) > 0
        for cwe in c_cwes:
            assert "C" in cwe.languages

    def test_kb_get_cwes_by_language_non_existent(self, kb):
        """Test get_cwes_by_language returns empty for unknown language."""
        result = kb.get_cwes_by_language("Brainfuck")
        assert result == []

    def test_kb_get_top_cwes(self, kb):
        """Test get_top_cwes returns sorted CWEs."""
        top = kb.get_top_cwes("C", n=5)
        assert len(top) == 5
        # Should be sorted by risk_score descending
        for i in range(len(top) - 1):
            assert top[i].risk_score >= top[i + 1].risk_score

    def test_kb_get_top_cwes_limit(self, kb):
        """Test get_top_cwes respects limit."""
        top = kb.get_top_cwes("C", n=3)
        assert len(top) == 3

    def test_kb_get_capec_exists(self, kb):
        """Test get_capec returns existing CAPEC."""
        capec = kb.get_capec("CAPEC-100")
        assert capec is not None
        assert capec.id == "CAPEC-100"

    def test_kb_get_capec_not_exists(self, kb):
        """Test get_capec returns None for non-existent CAPEC."""
        capec = kb.get_capec("CAPEC-99999")
        assert capec is None

    def test_kb_get_capecs_for_cwe(self, kb):
        """Test get_capecs_for_cwe returns related patterns."""
        capecs = kb.get_capecs_for_cwe("CWE-120")
        assert len(capecs) > 0
        for capec in capecs:
            assert "CWE-120" in capec.related_cwes

    def test_kb_get_capecs_for_cwe_none(self, kb):
        """Test get_capecs_for_cwe returns empty for unrelated CWE."""
        capecs = kb.get_capecs_for_cwe("CWE-99999")
        assert capecs == []

    def test_kb_get_patterns_by_language(self, kb):
        """Test get_patterns_by_language returns C patterns."""
        patterns = kb.get_patterns_by_language("C")
        assert len(patterns) >= 5  # Universal patterns
        for p in patterns:
            assert p.language == "C"

    def test_kb_get_patterns_by_language_non_existent(self, kb):
        """Test get_patterns_by_language returns empty for unknown language."""
        patterns = kb.get_patterns_by_language("COBOL")
        assert patterns == []

    def test_kb_get_patterns_by_category(self, kb):
        """Test get_patterns_by_category returns correct patterns."""
        patterns = kb.get_patterns_by_category("buffer_overflow")
        assert len(patterns) >= 1
        for p in patterns:
            assert p.category == "buffer_overflow"

    def test_kb_get_sinks_for_category(self, kb):
        """Test get_sinks_for_category aggregates sinks."""
        sinks = kb.get_sinks_for_category("buffer_overflow")
        assert len(sinks) > 0
        assert "strcpy" in sinks

    def test_kb_get_sources_for_category(self, kb):
        """Test get_sources_for_category aggregates sources."""
        sources = kb.get_sources_for_category("buffer_overflow")
        assert len(sources) > 0
        assert "recv" in sources or "getenv" in sources

    def test_kb_get_sanitizers_for_category(self, kb):
        """Test get_sanitizers_for_category aggregates sanitizers."""
        sanitizers = kb.get_sanitizers_for_category("buffer_overflow")
        # Buffer overflow category should have sanitizers
        assert "snprintf" in sanitizers or "strlcpy" in sanitizers

    def test_kb_get_stats(self, kb):
        """Test get_stats returns all expected keys."""
        stats = kb.get_stats()
        assert "total_cwes" in stats
        assert "total_capecs" in stats
        assert "total_patterns" in stats
        assert "critical_cwes" in stats
        assert "high_cwes" in stats
        assert "c_patterns" in stats

    def test_kb_get_stats_values(self, kb):
        """Test get_stats values are correct."""
        stats = kb.get_stats()
        assert stats["total_cwes"] == len(CWE_DATABASE)
        assert stats["total_capecs"] == len(CAPEC_DATABASE)
        assert stats["total_patterns"] >= len(C_LANGUAGE_PATTERNS)


class TestSecurityKnowledgeBaseWithProviders:
    """Tests for SecurityKnowledgeBase with providers."""

    def test_kb_loads_all_providers_by_default(self):
        """Test KB loads all providers when none specified."""
        kb = SecurityKnowledgeBase()
        # Should have more patterns than just universal C patterns
        stats = kb.get_stats()
        assert stats["total_patterns"] >= len(C_LANGUAGE_PATTERNS)

    def test_kb_loads_specific_providers(self):
        """Test KB loads specific provider by name."""
        # Load with postgresql provider
        kb = SecurityKnowledgeBase(providers=["postgresql"])
        patterns = kb.get_patterns_by_language("C")
        # Should have postgresql-specific patterns
        pg_patterns = [p for p in patterns if "pg_dump" in p.category or "spi" in p.category]
        assert len(pg_patterns) >= 1

    def test_kb_loads_empty_providers(self):
        """Test KB with empty provider list only has universal patterns."""
        kb = SecurityKnowledgeBase(providers=[])
        stats = kb.get_stats()
        assert stats["total_patterns"] == len(C_LANGUAGE_PATTERNS)

    def test_kb_ignores_invalid_providers(self):
        """Test KB ignores non-existent providers."""
        kb = SecurityKnowledgeBase(providers=["nonexistent_provider"])
        stats = kb.get_stats()
        # Should still have universal patterns
        assert stats["total_patterns"] == len(C_LANGUAGE_PATTERNS)


# =============================================================================
# Singleton Tests
# =============================================================================

class TestGetKnowledgeBaseSingleton:
    """Tests for get_knowledge_base singleton."""

    def test_get_knowledge_base_returns_instance(self):
        """Test get_knowledge_base returns a SecurityKnowledgeBase."""
        kb = get_knowledge_base()
        assert isinstance(kb, SecurityKnowledgeBase)

    def test_get_knowledge_base_singleton(self):
        """Test get_knowledge_base returns same instance."""
        kb1 = get_knowledge_base()
        kb2 = get_knowledge_base()
        assert kb1 is kb2

    def test_singleton_has_all_data(self):
        """Test singleton instance has all expected data."""
        kb = get_knowledge_base()
        assert len(kb.cwe_db) > 0
        assert len(kb.capec_db) > 0
        assert len(kb.c_patterns) > 0
