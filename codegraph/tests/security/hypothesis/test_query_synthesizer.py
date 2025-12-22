"""
Tests for Query Synthesizer.

Tests for:
- QuerySynthesizer initialization
- synthesize_query method
- synthesize_batch method
- PGQ query synthesis
- Helper methods
- create_custom_query method
- synthesize_queries_for_batch function
"""

import pytest

from src.security.hypothesis.models import SecurityHypothesis
from src.security.hypothesis.query_synthesizer import (
    QuerySynthesizer,
    synthesize_queries_for_batch,
)


# =============================================================================
# QuerySynthesizer Initialization Tests
# =============================================================================

class TestQuerySynthesizerInit:
    """Tests for QuerySynthesizer initialization."""

    def test_init_has_templates(self):
        """Test synthesizer initializes with templates."""
        synth = QuerySynthesizer()
        assert len(synth.templates) > 0

    def test_init_has_pgq_templates(self):
        """Test synthesizer initializes with PGQ templates."""
        synth = QuerySynthesizer()
        assert len(synth.pgq_templates) > 0

    def test_init_has_template_categories(self):
        """Test synthesizer initializes with template categories."""
        synth = QuerySynthesizer()
        assert len(synth._template_categories) > 0

    def test_init_loads_provider_templates(self):
        """Test synthesizer loads templates from providers."""
        synth = QuerySynthesizer()
        # Should have PostgreSQL-specific templates if provider is loaded
        assert "buffer_overflow" in synth.templates


# =============================================================================
# synthesize_query Tests
# =============================================================================

class TestSynthesizeQuery:
    """Tests for synthesize_query method."""

    @pytest.fixture
    def synth(self):
        """Create a synthesizer instance."""
        return QuerySynthesizer()

    def test_synthesize_query_returns_string(self, synth, sample_hypothesis):
        """Test synthesize_query returns a string."""
        query = synth.synthesize_query(sample_hypothesis)
        assert isinstance(query, str)

    def test_synthesize_query_has_select(self, synth, sample_hypothesis):
        """Test generated query has SELECT statement."""
        query = synth.synthesize_query(sample_hypothesis)
        assert "SELECT" in query

    def test_synthesize_query_contains_sinks(self, synth, sample_hypothesis):
        """Test query contains sink patterns."""
        query = synth.synthesize_query(sample_hypothesis)
        # Should have sink names in the query
        assert "strcpy" in query or "memcpy" in query

    def test_synthesize_query_stores_in_hypothesis(self, synth, sample_hypothesis):
        """Test query is stored in hypothesis."""
        synth.synthesize_query(sample_hypothesis)
        assert sample_hypothesis.sql_query is not None
        assert len(sample_hypothesis.sql_query) > 0

    def test_synthesize_query_buffer_overflow(self, synth):
        """Test buffer overflow query generation."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv", "getenv"],
            sink_patterns=["strcpy", "memcpy"],
            sanitizer_patterns=["strlcpy"],
        )
        query = synth.synthesize_query(hyp)
        assert "strcpy" in query
        assert "memcpy" in query
        assert "recv" in query

    def test_synthesize_query_command_injection(self, synth):
        """Test command injection query generation."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-78"],
            capec_ids=[],
            language="C",
            category="command_injection",
            source_patterns=["getenv"],
            sink_patterns=["system", "popen"],
            sanitizer_patterns=[],
        )
        query = synth.synthesize_query(hyp)
        assert "system" in query or "popen" in query

    def test_synthesize_query_uses_defaults_when_empty(self, synth):
        """Test synthesizer uses defaults when patterns are empty."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=[],
            sink_patterns=[],
            sanitizer_patterns=[],
        )
        query = synth.synthesize_query(hyp)
        # Should have default sinks like strcpy
        assert "strcpy" in query or "memcpy" in query


# =============================================================================
# synthesize_batch Tests
# =============================================================================

class TestSynthesizeBatch:
    """Tests for synthesize_batch method."""

    @pytest.fixture
    def synth(self):
        """Create a synthesizer instance."""
        return QuerySynthesizer()

    def test_synthesize_batch_returns_list(self, synth, sample_hypothesis):
        """Test synthesize_batch returns a list."""
        result = synth.synthesize_batch([sample_hypothesis])
        assert isinstance(result, list)

    def test_synthesize_batch_returns_tuples(self, synth, sample_hypothesis):
        """Test synthesize_batch returns tuples of (hypothesis, query)."""
        result = synth.synthesize_batch([sample_hypothesis])
        assert len(result) == 1
        hyp, query = result[0]
        assert isinstance(hyp, SecurityHypothesis)
        assert isinstance(query, str)

    def test_synthesize_batch_multiple(self, synth):
        """Test synthesize_batch handles multiple hypotheses."""
        hyp1 = SecurityHypothesis(
            id="1",
            hypothesis_text="Test1",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        hyp2 = SecurityHypothesis(
            id="2",
            hypothesis_text="Test2",
            cwe_ids=["CWE-78"],
            capec_ids=[],
            language="C",
            category="command_injection",
            source_patterns=["getenv"],
            sink_patterns=["system"],
            sanitizer_patterns=[],
        )
        result = synth.synthesize_batch([hyp1, hyp2])
        assert len(result) == 2


# =============================================================================
# PGQ Query Synthesis Tests
# =============================================================================

class TestPGQQuerySynthesis:
    """Tests for PGQ query generation."""

    @pytest.fixture
    def synth(self):
        """Create a synthesizer instance."""
        return QuerySynthesizer()

    def test_synthesize_pgq_query(self, synth, sample_hypothesis):
        """Test PGQ query generation."""
        query = synth.synthesize_query(sample_hypothesis, use_pgq=True)
        assert "GRAPH_TABLE" in query

    def test_pgq_query_has_match(self, synth, sample_hypothesis):
        """Test PGQ query has MATCH clause."""
        query = synth.synthesize_query(sample_hypothesis, use_pgq=True)
        assert "MATCH" in query

    def test_pgq_query_contains_sinks(self, synth, sample_hypothesis):
        """Test PGQ query contains sink patterns."""
        query = synth.synthesize_query(sample_hypothesis, use_pgq=True)
        # Should have sink patterns formatted
        assert "strcpy" in query or "memcpy" in query


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def synth(self):
        """Create a synthesizer instance."""
        return QuerySynthesizer()

    def test_select_template_known(self, synth):
        """Test _select_template returns template for known category."""
        template = synth._select_template("buffer_overflow")
        assert len(template) > 0
        assert "SELECT" in template

    def test_select_template_unknown(self, synth):
        """Test _select_template returns default for unknown category."""
        template = synth._select_template("unknown_category")
        # Should return buffer_overflow as default
        assert len(template) > 0

    def test_build_sanitizer_conditions_empty(self, synth):
        """Test _build_sanitizer_conditions with empty list."""
        conditions = synth._build_sanitizer_conditions([])
        assert conditions == "1=0"  # Never match

    def test_build_sanitizer_conditions_single(self, synth):
        """Test _build_sanitizer_conditions with single sanitizer."""
        conditions = synth._build_sanitizer_conditions(["strlcpy"])
        assert "strlcpy" in conditions
        assert "LIKE" in conditions

    def test_build_sanitizer_conditions_pattern(self, synth):
        """Test _build_sanitizer_conditions with pattern."""
        conditions = synth._build_sanitizer_conditions(["%check%"])
        assert "%check%" in conditions

    def test_build_sanitizer_conditions_comparison(self, synth):
        """Test _build_sanitizer_conditions with comparison pattern."""
        conditions = synth._build_sanitizer_conditions(["= NULL"])
        assert "NULL" in conditions

    def test_build_sink_conditions_empty(self, synth):
        """Test _build_sink_conditions with empty list."""
        conditions = synth._build_sink_conditions([], "buffer_overflow")
        assert conditions == "1=1"

    def test_build_sink_conditions_information_disclosure(self, synth):
        """Test _build_sink_conditions for information_disclosure category."""
        conditions = synth._build_sink_conditions([], "information_disclosure")
        assert "statistic" in conditions or "sample" in conditions

    def test_build_sink_conditions_with_sinks(self, synth):
        """Test _build_sink_conditions with sink list."""
        conditions = synth._build_sink_conditions(["strcpy", "memcpy"], "buffer_overflow")
        assert "strcpy" in conditions
        assert "memcpy" in conditions


# =============================================================================
# create_custom_query Tests
# =============================================================================

class TestCreateCustomQuery:
    """Tests for create_custom_query method."""

    @pytest.fixture
    def synth(self):
        """Create a synthesizer instance."""
        return QuerySynthesizer()

    def test_create_custom_query_valid_template(self, synth):
        """Test create_custom_query with valid template."""
        query = synth.create_custom_query(
            template_name="buffer_overflow",
            sinks=["strcpy"],
            sources=["getenv"],
            sanitizers=["strlcpy"],
        )
        assert "SELECT" in query
        assert "strcpy" in query

    def test_create_custom_query_invalid_template(self, synth):
        """Test create_custom_query raises for invalid template."""
        with pytest.raises(ValueError, match="Unknown template"):
            synth.create_custom_query(
                template_name="nonexistent_template",
                sinks=["test"],
                sources=["test"],
            )

    def test_create_custom_query_with_extra_conditions(self, synth):
        """Test create_custom_query with extra conditions."""
        query = synth.create_custom_query(
            template_name="buffer_overflow",
            sinks=["strcpy"],
            sources=["getenv"],
            extra_conditions="c.filename LIKE '%pg_dump%'",
        )
        assert "pg_dump" in query


# =============================================================================
# synthesize_queries_for_batch Tests
# =============================================================================

class TestSynthesizeQueriesForBatch:
    """Tests for synthesize_queries_for_batch function."""

    def test_function_returns_list(self, sample_hypothesis):
        """Test function returns list of hypotheses."""
        result = synthesize_queries_for_batch([sample_hypothesis])
        assert isinstance(result, list)
        assert len(result) == 1

    def test_function_populates_sql_query(self, sample_hypothesis):
        """Test function populates sql_query field."""
        sample_hypothesis.sql_query = None
        synthesize_queries_for_batch([sample_hypothesis])
        assert sample_hypothesis.sql_query is not None

    def test_function_preserves_existing_query(self):
        """Test function doesn't overwrite existing queries."""
        hyp = SecurityHypothesis(
            id="test",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["getenv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
            sql_query="EXISTING QUERY",
        )
        synthesize_queries_for_batch([hyp])
        assert hyp.sql_query == "EXISTING QUERY"
