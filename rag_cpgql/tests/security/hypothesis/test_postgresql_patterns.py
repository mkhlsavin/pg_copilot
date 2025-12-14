"""
Tests for PostgreSQL-specific vulnerability patterns.

Tests for:
- pg_dump patterns (PG_DUMP_SINKS, PG_DUMP_SOURCES, PG_DUMP_SANITIZERS)
- SPI patterns (PG_SPI_SINKS, PG_SPI_SOURCES, PG_SPI_SANITIZERS)
- libpq patterns (PG_LIBPQ_SINKS, PG_LIBPQ_SOURCES, PG_LIBPQ_SANITIZERS)
- ACL functions (PG_ACL_FUNCTIONS)
- CVEPattern dataclass
- POSTGRESQL_CVE_PATTERNS dictionary
- CVE-2025-8713 pattern (statistics disclosure)
- CVE-2025-8714 pattern (pg_dump RCE)
- CVE-2025-8715 pattern (newline injection)
- get_pg_pattern_for_cve function
- get_all_pg_sinks function
- get_all_pg_sources function
- get_all_pg_sanitizers function
"""

import pytest

from src.security.hypothesis.postgresql.patterns import (
    # pg_dump patterns
    PG_DUMP_SINKS,
    PG_DUMP_SOURCES,
    PG_DUMP_SANITIZERS,
    # SPI patterns
    PG_SPI_SINKS,
    PG_SPI_SOURCES,
    PG_SPI_SANITIZERS,
    # libpq patterns
    PG_LIBPQ_SINKS,
    PG_LIBPQ_SOURCES,
    PG_LIBPQ_SANITIZERS,
    # ACL functions
    PG_ACL_FUNCTIONS,
    # CVE patterns
    CVEPattern,
    POSTGRESQL_CVE_PATTERNS,
    # Functions
    get_pg_pattern_for_cve,
    get_all_pg_sinks,
    get_all_pg_sources,
    get_all_pg_sanitizers,
)


# =============================================================================
# pg_dump Patterns Tests
# =============================================================================

class TestPGDumpPatterns:
    """Tests for pg_dump patterns."""

    def test_pg_dump_sinks_not_empty(self):
        """Test pg_dump sinks list is not empty."""
        assert len(PG_DUMP_SINKS) > 0

    def test_pg_dump_sinks_contains_expected(self):
        """Test pg_dump sinks contains expected functions."""
        assert "appendPQExpBuffer" in PG_DUMP_SINKS
        assert "appendPQExpBufferStr" in PG_DUMP_SINKS
        assert "appendStringInfo" in PG_DUMP_SINKS
        assert "ahprintf" in PG_DUMP_SINKS

    def test_pg_dump_sources_not_empty(self):
        """Test pg_dump sources list is not empty."""
        assert len(PG_DUMP_SOURCES) > 0

    def test_pg_dump_sources_contains_expected(self):
        """Test pg_dump sources contains expected functions."""
        assert "PQgetvalue" in PG_DUMP_SOURCES
        assert "PQfname" in PG_DUMP_SOURCES
        assert "getTables" in PG_DUMP_SOURCES
        assert "getTableAttrs" in PG_DUMP_SOURCES

    def test_pg_dump_sanitizers_not_empty(self):
        """Test pg_dump sanitizers list is not empty."""
        assert len(PG_DUMP_SANITIZERS) > 0

    def test_pg_dump_sanitizers_contains_expected(self):
        """Test pg_dump sanitizers contains expected functions."""
        assert "fmtId" in PG_DUMP_SANITIZERS
        assert "fmtQualifiedId" in PG_DUMP_SANITIZERS
        assert "fmtQualifiedDumpable" in PG_DUMP_SANITIZERS

    def test_pg_dump_sinks_are_strings(self):
        """Test all pg_dump sinks are strings."""
        for sink in PG_DUMP_SINKS:
            assert isinstance(sink, str)

    def test_pg_dump_sources_are_strings(self):
        """Test all pg_dump sources are strings."""
        for source in PG_DUMP_SOURCES:
            assert isinstance(source, str)


# =============================================================================
# SPI Patterns Tests
# =============================================================================

class TestSPIPatterns:
    """Tests for SPI (Server Programming Interface) patterns."""

    def test_spi_sinks_not_empty(self):
        """Test SPI sinks list is not empty."""
        assert len(PG_SPI_SINKS) > 0

    def test_spi_sinks_contains_expected(self):
        """Test SPI sinks contains expected functions."""
        assert "SPI_execute" in PG_SPI_SINKS
        assert "SPI_exec" in PG_SPI_SINKS
        assert "SPI_prepare" in PG_SPI_SINKS
        assert "SPI_cursor_open" in PG_SPI_SINKS

    def test_spi_sources_not_empty(self):
        """Test SPI sources list is not empty."""
        assert len(PG_SPI_SOURCES) > 0

    def test_spi_sources_contains_expected(self):
        """Test SPI sources contains expected functions."""
        assert "SPI_getvalue" in PG_SPI_SOURCES
        assert "SPI_getbinval" in PG_SPI_SOURCES
        assert "DatumGetCString" in PG_SPI_SOURCES

    def test_spi_sanitizers_not_empty(self):
        """Test SPI sanitizers list is not empty."""
        assert len(PG_SPI_SANITIZERS) > 0

    def test_spi_sanitizers_contains_expected(self):
        """Test SPI sanitizers contains expected functions."""
        assert "quote_literal" in PG_SPI_SANITIZERS
        assert "quote_identifier" in PG_SPI_SANITIZERS


# =============================================================================
# libpq Patterns Tests
# =============================================================================

class TestLibpqPatterns:
    """Tests for libpq patterns."""

    def test_libpq_sinks_not_empty(self):
        """Test libpq sinks list is not empty."""
        assert len(PG_LIBPQ_SINKS) > 0

    def test_libpq_sinks_contains_expected(self):
        """Test libpq sinks contains expected functions."""
        assert "PQexec" in PG_LIBPQ_SINKS
        assert "PQexecParams" in PG_LIBPQ_SINKS
        assert "PQprepare" in PG_LIBPQ_SINKS

    def test_libpq_sources_not_empty(self):
        """Test libpq sources list is not empty."""
        assert len(PG_LIBPQ_SOURCES) > 0

    def test_libpq_sources_contains_expected(self):
        """Test libpq sources contains expected functions."""
        assert "PQgetvalue" in PG_LIBPQ_SOURCES
        assert "PQfname" in PG_LIBPQ_SOURCES

    def test_libpq_sanitizers_not_empty(self):
        """Test libpq sanitizers list is not empty."""
        assert len(PG_LIBPQ_SANITIZERS) > 0

    def test_libpq_sanitizers_contains_expected(self):
        """Test libpq sanitizers contains expected functions."""
        assert "PQescapeIdentifier" in PG_LIBPQ_SANITIZERS
        assert "PQescapeLiteral" in PG_LIBPQ_SANITIZERS
        assert "PQescapeString" in PG_LIBPQ_SANITIZERS


# =============================================================================
# ACL Functions Tests
# =============================================================================

class TestACLFunctions:
    """Tests for PostgreSQL ACL functions."""

    def test_acl_functions_not_empty(self):
        """Test ACL functions list is not empty."""
        assert len(PG_ACL_FUNCTIONS) > 0

    def test_acl_functions_contains_table_checks(self):
        """Test ACL functions contains table-level checks."""
        assert "pg_class_aclcheck" in PG_ACL_FUNCTIONS
        assert "has_table_privilege" in PG_ACL_FUNCTIONS

    def test_acl_functions_contains_column_checks(self):
        """Test ACL functions contains column-level checks."""
        assert "pg_attribute_aclcheck" in PG_ACL_FUNCTIONS
        assert "has_column_privilege" in PG_ACL_FUNCTIONS

    def test_acl_functions_contains_schema_checks(self):
        """Test ACL functions contains schema-level checks."""
        assert "pg_namespace_aclcheck" in PG_ACL_FUNCTIONS
        assert "has_schema_privilege" in PG_ACL_FUNCTIONS

    def test_acl_functions_contains_rls_checks(self):
        """Test ACL functions contains row-level security checks."""
        assert "check_enable_rls" in PG_ACL_FUNCTIONS
        assert "row_security_active" in PG_ACL_FUNCTIONS


# =============================================================================
# CVEPattern Dataclass Tests
# =============================================================================

class TestCVEPattern:
    """Tests for CVEPattern dataclass."""

    def test_cve_pattern_creation(self):
        """Test CVEPattern can be created."""
        pattern = CVEPattern(
            cve_id="CVE-TEST-0001",
            description="Test vulnerability",
            affected_versions=["1.0", "1.1"],
            fixed_versions=["1.2"],
            cwes=["CWE-123"],
            sinks=["test_sink"],
            sources=["test_source"],
            sanitizers=["test_sanitizer"],
            affected_files=["test.c"],
            detection_query="SELECT * FROM test",
        )
        assert pattern.cve_id == "CVE-TEST-0001"
        assert pattern.description == "Test vulnerability"

    def test_cve_pattern_fix_description_optional(self):
        """Test CVEPattern fix_description is optional."""
        pattern = CVEPattern(
            cve_id="CVE-TEST-0001",
            description="Test",
            affected_versions=[],
            fixed_versions=[],
            cwes=[],
            sinks=[],
            sources=[],
            sanitizers=[],
            affected_files=[],
            detection_query="",
        )
        assert pattern.fix_description == ""


# =============================================================================
# POSTGRESQL_CVE_PATTERNS Tests
# =============================================================================

class TestPostgresqlCVEPatterns:
    """Tests for POSTGRESQL_CVE_PATTERNS dictionary."""

    def test_cve_patterns_not_empty(self):
        """Test CVE patterns dictionary is not empty."""
        assert len(POSTGRESQL_CVE_PATTERNS) > 0

    def test_cve_patterns_contains_expected_cves(self):
        """Test CVE patterns contains expected CVEs."""
        assert "CVE-2025-8713" in POSTGRESQL_CVE_PATTERNS
        assert "CVE-2025-8714" in POSTGRESQL_CVE_PATTERNS
        assert "CVE-2025-8715" in POSTGRESQL_CVE_PATTERNS

    def test_cve_patterns_are_cve_pattern_type(self):
        """Test all patterns are CVEPattern instances."""
        for cve_id, pattern in POSTGRESQL_CVE_PATTERNS.items():
            assert isinstance(pattern, CVEPattern)
            assert pattern.cve_id == cve_id


# =============================================================================
# CVE-2025-8713 Tests (Statistics Disclosure)
# =============================================================================

class TestCVE20258713:
    """Tests for CVE-2025-8713 pattern (statistics disclosure)."""

    @pytest.fixture
    def pattern(self):
        """Get CVE-2025-8713 pattern."""
        return POSTGRESQL_CVE_PATTERNS["CVE-2025-8713"]

    def test_cve_id(self, pattern):
        """Test CVE ID is correct."""
        assert pattern.cve_id == "CVE-2025-8713"

    def test_description(self, pattern):
        """Test description mentions statistics."""
        assert "statistic" in pattern.description.lower()

    def test_affected_versions(self, pattern):
        """Test affected versions include 17.5."""
        assert "17.5" in pattern.affected_versions

    def test_fixed_versions(self, pattern):
        """Test fixed in 17.6."""
        assert "17.6" in pattern.fixed_versions

    def test_cwes(self, pattern):
        """Test CWE associations."""
        assert "CWE-200" in pattern.cwes  # Information Disclosure
        assert "CWE-862" in pattern.cwes  # Missing Authorization

    def test_affected_files(self, pattern):
        """Test affected files include analyze.c."""
        analyze_files = [f for f in pattern.affected_files if "analyze" in f]
        assert len(analyze_files) > 0

    def test_sanitizers_include_acl(self, pattern):
        """Test sanitizers include ACL functions."""
        assert "pg_class_aclcheck" in pattern.sanitizers

    def test_detection_query_has_content(self, pattern):
        """Test detection query is not empty."""
        assert len(pattern.detection_query) > 0
        assert "SELECT" in pattern.detection_query


# =============================================================================
# CVE-2025-8714 Tests (pg_dump RCE)
# =============================================================================

class TestCVE20258714:
    """Tests for CVE-2025-8714 pattern (pg_dump RCE)."""

    @pytest.fixture
    def pattern(self):
        """Get CVE-2025-8714 pattern."""
        return POSTGRESQL_CVE_PATTERNS["CVE-2025-8714"]

    def test_cve_id(self, pattern):
        """Test CVE ID is correct."""
        assert pattern.cve_id == "CVE-2025-8714"

    def test_description(self, pattern):
        """Test description mentions pg_dump."""
        assert "pg_dump" in pattern.description.lower()

    def test_cwes(self, pattern):
        """Test CWE associations."""
        assert "CWE-94" in pattern.cwes  # Code Injection
        assert "CWE-78" in pattern.cwes  # Command Injection

    def test_sinks(self, pattern):
        """Test sinks are pg_dump sinks."""
        assert pattern.sinks == PG_DUMP_SINKS

    def test_sources(self, pattern):
        """Test sources are pg_dump sources."""
        assert pattern.sources == PG_DUMP_SOURCES

    def test_sanitizers(self, pattern):
        """Test sanitizers are pg_dump sanitizers."""
        assert pattern.sanitizers == PG_DUMP_SANITIZERS

    def test_affected_files(self, pattern):
        """Test affected files include pg_dump."""
        pg_dump_files = [f for f in pattern.affected_files if "pg_dump" in f]
        assert len(pg_dump_files) > 0

    def test_detection_query_checks_escaping(self, pattern):
        """Test detection query checks for escaping."""
        assert "fmtId" in pattern.detection_query
        assert "fmtQualifiedId" in pattern.detection_query


# =============================================================================
# CVE-2025-8715 Tests (Newline Injection)
# =============================================================================

class TestCVE20258715:
    """Tests for CVE-2025-8715 pattern (newline injection)."""

    @pytest.fixture
    def pattern(self):
        """Get CVE-2025-8715 pattern."""
        return POSTGRESQL_CVE_PATTERNS["CVE-2025-8715"]

    def test_cve_id(self, pattern):
        """Test CVE ID is correct."""
        assert pattern.cve_id == "CVE-2025-8715"

    def test_description(self, pattern):
        """Test description mentions newline."""
        assert "newline" in pattern.description.lower()

    def test_cwes(self, pattern):
        """Test CWE associations."""
        assert "CWE-94" in pattern.cwes  # Code Injection
        assert "CWE-93" in pattern.cwes  # CRLF Injection

    def test_sinks(self, pattern):
        """Test sinks include pg_dump output functions."""
        assert "appendPQExpBuffer" in pattern.sinks
        assert "ahprintf" in pattern.sinks

    def test_sanitizers_include_newline_handling(self, pattern):
        """Test sanitizers include newline handling."""
        # Should have newline-specific sanitizers
        assert "replace_newline" in pattern.sanitizers or "escape_newline" in pattern.sanitizers

    def test_affected_files(self, pattern):
        """Test affected files include pg_dump."""
        pg_dump_files = [f for f in pattern.affected_files if "pg_dump" in f]
        assert len(pg_dump_files) > 0


# =============================================================================
# get_pg_pattern_for_cve Tests
# =============================================================================

class TestGetPgPatternForCVE:
    """Tests for get_pg_pattern_for_cve function."""

    def test_returns_pattern_for_known_cve(self):
        """Test function returns pattern for known CVE."""
        pattern = get_pg_pattern_for_cve("CVE-2025-8713")
        assert pattern is not None
        assert pattern.cve_id == "CVE-2025-8713"

    def test_returns_none_for_unknown_cve(self):
        """Test function returns None for unknown CVE."""
        pattern = get_pg_pattern_for_cve("CVE-9999-9999")
        assert pattern is None

    def test_returns_all_known_cves(self):
        """Test function returns pattern for all known CVEs."""
        for cve_id in ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]:
            pattern = get_pg_pattern_for_cve(cve_id)
            assert pattern is not None


# =============================================================================
# get_all_pg_sinks Tests
# =============================================================================

class TestGetAllPgSinks:
    """Tests for get_all_pg_sinks function."""

    def test_returns_list(self):
        """Test function returns a list."""
        sinks = get_all_pg_sinks()
        assert isinstance(sinks, list)

    def test_includes_pg_dump_sinks(self):
        """Test result includes pg_dump sinks."""
        sinks = get_all_pg_sinks()
        for sink in PG_DUMP_SINKS:
            assert sink in sinks

    def test_includes_spi_sinks(self):
        """Test result includes SPI sinks."""
        sinks = get_all_pg_sinks()
        for sink in PG_SPI_SINKS:
            assert sink in sinks

    def test_includes_libpq_sinks(self):
        """Test result includes libpq sinks."""
        sinks = get_all_pg_sinks()
        for sink in PG_LIBPQ_SINKS:
            assert sink in sinks

    def test_is_sorted(self):
        """Test result is sorted."""
        sinks = get_all_pg_sinks()
        assert sinks == sorted(sinks)

    def test_no_duplicates(self):
        """Test result has no duplicates."""
        sinks = get_all_pg_sinks()
        assert len(sinks) == len(set(sinks))


# =============================================================================
# get_all_pg_sources Tests
# =============================================================================

class TestGetAllPgSources:
    """Tests for get_all_pg_sources function."""

    def test_returns_list(self):
        """Test function returns a list."""
        sources = get_all_pg_sources()
        assert isinstance(sources, list)

    def test_includes_pg_dump_sources(self):
        """Test result includes pg_dump sources."""
        sources = get_all_pg_sources()
        for source in PG_DUMP_SOURCES:
            assert source in sources

    def test_includes_spi_sources(self):
        """Test result includes SPI sources."""
        sources = get_all_pg_sources()
        for source in PG_SPI_SOURCES:
            assert source in sources

    def test_includes_libpq_sources(self):
        """Test result includes libpq sources."""
        sources = get_all_pg_sources()
        for source in PG_LIBPQ_SOURCES:
            assert source in sources

    def test_is_sorted(self):
        """Test result is sorted."""
        sources = get_all_pg_sources()
        assert sources == sorted(sources)


# =============================================================================
# get_all_pg_sanitizers Tests
# =============================================================================

class TestGetAllPgSanitizers:
    """Tests for get_all_pg_sanitizers function."""

    def test_returns_list(self):
        """Test function returns a list."""
        sanitizers = get_all_pg_sanitizers()
        assert isinstance(sanitizers, list)

    def test_includes_pg_dump_sanitizers(self):
        """Test result includes pg_dump sanitizers."""
        sanitizers = get_all_pg_sanitizers()
        for san in PG_DUMP_SANITIZERS:
            assert san in sanitizers

    def test_includes_spi_sanitizers(self):
        """Test result includes SPI sanitizers."""
        sanitizers = get_all_pg_sanitizers()
        for san in PG_SPI_SANITIZERS:
            assert san in sanitizers

    def test_includes_libpq_sanitizers(self):
        """Test result includes libpq sanitizers."""
        sanitizers = get_all_pg_sanitizers()
        for san in PG_LIBPQ_SANITIZERS:
            assert san in sanitizers

    def test_includes_acl_functions(self):
        """Test result includes ACL functions."""
        sanitizers = get_all_pg_sanitizers()
        for acl_func in PG_ACL_FUNCTIONS:
            assert acl_func in sanitizers

    def test_is_sorted(self):
        """Test result is sorted."""
        sanitizers = get_all_pg_sanitizers()
        assert sanitizers == sorted(sanitizers)
