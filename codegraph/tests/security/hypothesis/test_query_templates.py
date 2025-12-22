"""
Tests for Query Templates.

Tests for:
- SQL_TEMPLATES
- PGQ_TEMPLATES
- TEMPLATE_CATEGORIES
- get_template function
- get_pgq_template function
- get_category_defaults function
"""

import pytest

from src.security.hypothesis.query_templates import (
    SQL_TEMPLATES,
    PGQ_TEMPLATES,
    TEMPLATE_CATEGORIES,
    get_template,
    get_pgq_template,
    get_category_defaults,
)


# =============================================================================
# SQL_TEMPLATES Tests
# =============================================================================

class TestSQLTemplates:
    """Tests for SQL_TEMPLATES."""

    def test_sql_templates_not_empty(self):
        """Test SQL templates dictionary is not empty."""
        assert len(SQL_TEMPLATES) > 0

    def test_sql_templates_expected_count(self):
        """Test expected number of SQL templates."""
        expected_templates = [
            "buffer_overflow",
            "command_injection",
            "format_string",
            "sql_injection",
            "code_injection",
            "information_disclosure",
            "use_after_free",
            "integer_overflow",
            "null_pointer_deref",
        ]
        for template in expected_templates:
            assert template in SQL_TEMPLATES, f"Missing template: {template}"

    def test_sql_templates_are_strings(self):
        """Test all SQL templates are strings."""
        for name, template in SQL_TEMPLATES.items():
            assert isinstance(template, str), f"{name} is not a string"

    def test_sql_templates_have_select(self):
        """Test all SQL templates have SELECT statements."""
        for name, template in SQL_TEMPLATES.items():
            assert "SELECT" in template, f"{name} missing SELECT"

    def test_sql_templates_have_placeholders(self):
        """Test SQL templates have parameter placeholders."""
        # Most templates should have sinks placeholder
        templates_with_sinks = [
            "buffer_overflow",
            "command_injection",
            "format_string",
            "use_after_free",
            "integer_overflow",
            "null_pointer_deref",
        ]
        for name in templates_with_sinks:
            template = SQL_TEMPLATES[name]
            assert "{sinks}" in template, f"{name} missing {{sinks}} placeholder"

    def test_buffer_overflow_template(self):
        """Test buffer overflow template structure."""
        template = SQL_TEMPLATES["buffer_overflow"]
        assert "{sinks}" in template
        assert "{sources}" in template
        assert "nodes_call" in template
        assert "CWE-120" in template

    def test_command_injection_template(self):
        """Test command injection template structure."""
        template = SQL_TEMPLATES["command_injection"]
        assert "{sinks}" in template
        assert "{sources}" in template
        assert "{sanitizers}" in template
        assert "CWE-78" in template


# =============================================================================
# PGQ_TEMPLATES Tests
# =============================================================================

class TestPGQTemplates:
    """Tests for PGQ_TEMPLATES."""

    def test_pgq_templates_not_empty(self):
        """Test PGQ templates dictionary is not empty."""
        assert len(PGQ_TEMPLATES) > 0

    def test_pgq_templates_expected_count(self):
        """Test expected number of PGQ templates."""
        expected = [
            "taint_flow_path",
            "call_chain_to_sink",
            "control_dependent_flow",
            "unsanitized_path",
        ]
        for template in expected:
            assert template in PGQ_TEMPLATES, f"Missing PGQ template: {template}"

    def test_pgq_templates_are_strings(self):
        """Test all PGQ templates are strings."""
        for name, template in PGQ_TEMPLATES.items():
            assert isinstance(template, str)

    def test_pgq_templates_have_graph_table(self):
        """Test PGQ templates use GRAPH_TABLE syntax."""
        for name, template in PGQ_TEMPLATES.items():
            assert "GRAPH_TABLE" in template, f"{name} missing GRAPH_TABLE"

    def test_pgq_templates_have_match(self):
        """Test PGQ templates have MATCH clause."""
        for name, template in PGQ_TEMPLATES.items():
            assert "MATCH" in template, f"{name} missing MATCH"

    def test_taint_flow_path_template(self):
        """Test taint_flow_path template structure."""
        template = PGQ_TEMPLATES["taint_flow_path"]
        assert "{sources}" in template
        assert "{sinks}" in template
        assert "REACHING_DEF" in template

    def test_unsanitized_path_template(self):
        """Test unsanitized_path template structure."""
        template = PGQ_TEMPLATES["unsanitized_path"]
        assert "{sources}" in template
        assert "{sinks}" in template
        assert "{sanitizers}" in template


# =============================================================================
# TEMPLATE_CATEGORIES Tests
# =============================================================================

class TestTemplateCategories:
    """Tests for TEMPLATE_CATEGORIES."""

    def test_categories_not_empty(self):
        """Test categories dictionary is not empty."""
        assert len(TEMPLATE_CATEGORIES) > 0

    def test_categories_have_required_keys(self):
        """Test each category has required keys."""
        required_keys = ["template", "default_sinks", "default_sources", "default_sanitizers"]
        for category, config in TEMPLATE_CATEGORIES.items():
            for key in required_keys:
                assert key in config, f"{category} missing {key}"

    def test_buffer_overflow_category(self):
        """Test buffer_overflow category configuration."""
        config = TEMPLATE_CATEGORIES["buffer_overflow"]
        assert config["template"] == "buffer_overflow"
        assert "strcpy" in config["default_sinks"]
        assert "recv" in config["default_sources"]

    def test_command_injection_category(self):
        """Test command_injection category configuration."""
        config = TEMPLATE_CATEGORIES["command_injection"]
        assert config["template"] == "command_injection"
        assert "system" in config["default_sinks"]
        assert "getenv" in config["default_sources"]

    def test_format_string_no_sanitizers(self):
        """Test format_string has no sanitizers (must be literals)."""
        config = TEMPLATE_CATEGORIES["format_string"]
        assert config["default_sanitizers"] == []


# =============================================================================
# get_template Tests
# =============================================================================

class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_template_known_category(self):
        """Test get_template returns template for known category."""
        template = get_template("buffer_overflow")
        assert len(template) > 0
        assert "SELECT" in template

    def test_get_template_unknown_category(self):
        """Test get_template returns default for unknown category."""
        template = get_template("unknown_category")
        # Should return buffer_overflow template as default
        assert len(template) > 0
        assert "SELECT" in template

    def test_get_template_direct_name(self):
        """Test get_template with direct template name."""
        template = get_template("use_after_free")
        assert "CWE-416" in template


# =============================================================================
# get_pgq_template Tests
# =============================================================================

class TestGetPGQTemplate:
    """Tests for get_pgq_template function."""

    def test_get_pgq_template_known(self):
        """Test get_pgq_template returns template for known name."""
        template = get_pgq_template("taint_flow_path")
        assert len(template) > 0
        assert "GRAPH_TABLE" in template

    def test_get_pgq_template_unknown(self):
        """Test get_pgq_template returns empty string for unknown name."""
        template = get_pgq_template("unknown_template")
        assert template == ""


# =============================================================================
# get_category_defaults Tests
# =============================================================================

class TestGetCategoryDefaults:
    """Tests for get_category_defaults function."""

    def test_get_category_defaults_known(self):
        """Test get_category_defaults returns config for known category."""
        defaults = get_category_defaults("buffer_overflow")
        assert "template" in defaults
        assert "default_sinks" in defaults
        assert "strcpy" in defaults["default_sinks"]

    def test_get_category_defaults_unknown(self):
        """Test get_category_defaults returns fallback for unknown category."""
        defaults = get_category_defaults("unknown_category")
        assert "template" in defaults
        assert defaults["template"] == "buffer_overflow"
        assert "default_sinks" in defaults
        assert defaults["default_sinks"] == []
