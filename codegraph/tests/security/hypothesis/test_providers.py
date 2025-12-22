"""
Tests for Pattern Provider Interface and Registry.

Tests for:
- PatternProvider abstract interface
- ProviderRegistry class methods
- PostgreSQLPatternProvider concrete implementation
"""

import pytest
from typing import Dict, List
from unittest.mock import MagicMock

from src.security.hypothesis.providers import PatternProvider, ProviderRegistry
from src.security.hypothesis.postgresql.provider import PostgreSQLPatternProvider
from src.security.hypothesis.models import LanguagePattern


# =============================================================================
# Test Fixtures
# =============================================================================

class MockProvider(PatternProvider):
    """Mock provider for testing."""

    @property
    def name(self) -> str:
        return "mock_provider"

    @property
    def languages(self) -> List[str]:
        return ["C", "Python"]

    def get_sinks(self) -> Dict[str, List[str]]:
        return {"memory": ["malloc", "free"]}

    def get_sources(self) -> Dict[str, List[str]]:
        return {"input": ["read", "fgets"]}

    def get_sanitizers(self) -> Dict[str, List[str]]:
        return {"validation": ["check", "validate"]}

    def get_language_patterns(self) -> List[LanguagePattern]:
        return [
            LanguagePattern(
                language="C",
                category="test_category",
                sinks=["malloc"],
                sources=["read"],
                sanitizers=["check"],
                related_cwes=["CWE-123"],
                description="Test pattern",
            )
        ]


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider()


@pytest.fixture
def clean_registry():
    """Provide a clean registry for testing.

    Saves and restores the registry state to avoid test interference.
    """
    # Save current state
    saved = dict(ProviderRegistry._providers)

    # Clear for test
    ProviderRegistry.clear()

    yield ProviderRegistry

    # Restore state
    ProviderRegistry._providers = saved


# =============================================================================
# PatternProvider Interface Tests
# =============================================================================

class TestPatternProviderInterface:
    """Tests for PatternProvider abstract interface."""

    def test_provider_has_name(self, mock_provider):
        """Test provider has name property."""
        assert mock_provider.name == "mock_provider"

    def test_provider_has_languages(self, mock_provider):
        """Test provider has languages property."""
        assert "C" in mock_provider.languages

    def test_provider_get_sinks(self, mock_provider):
        """Test provider get_sinks returns dict."""
        sinks = mock_provider.get_sinks()
        assert isinstance(sinks, dict)
        assert "memory" in sinks

    def test_provider_get_sources(self, mock_provider):
        """Test provider get_sources returns dict."""
        sources = mock_provider.get_sources()
        assert isinstance(sources, dict)
        assert "input" in sources

    def test_provider_get_sanitizers(self, mock_provider):
        """Test provider get_sanitizers returns dict."""
        sanitizers = mock_provider.get_sanitizers()
        assert isinstance(sanitizers, dict)
        assert "validation" in sanitizers

    def test_provider_get_language_patterns(self, mock_provider):
        """Test provider get_language_patterns returns list."""
        patterns = mock_provider.get_language_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert isinstance(patterns[0], LanguagePattern)

    def test_provider_get_query_templates_default(self, mock_provider):
        """Test provider get_query_templates returns empty dict by default."""
        templates = mock_provider.get_query_templates()
        assert isinstance(templates, dict)
        assert templates == {}

    def test_provider_get_template_categories_default(self, mock_provider):
        """Test provider get_template_categories returns empty dict by default."""
        categories = mock_provider.get_template_categories()
        assert isinstance(categories, dict)
        assert categories == {}


# =============================================================================
# ProviderRegistry Tests
# =============================================================================

class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    def test_register_provider(self, clean_registry, mock_provider):
        """Test registering a provider."""
        clean_registry.register(mock_provider)
        assert mock_provider.name in clean_registry.names()

    def test_register_overwrites_existing(self, clean_registry):
        """Test registering overwrites existing provider with same name."""
        provider1 = MockProvider()
        provider2 = MockProvider()

        clean_registry.register(provider1)
        clean_registry.register(provider2)

        assert clean_registry.get("mock_provider") is provider2

    def test_unregister_provider(self, clean_registry, mock_provider):
        """Test unregistering a provider."""
        clean_registry.register(mock_provider)
        result = clean_registry.unregister("mock_provider")

        assert result is True
        assert "mock_provider" not in clean_registry.names()

    def test_unregister_nonexistent(self, clean_registry):
        """Test unregistering non-existent provider returns False."""
        result = clean_registry.unregister("nonexistent")
        assert result is False

    def test_get_provider(self, clean_registry, mock_provider):
        """Test getting a provider by name."""
        clean_registry.register(mock_provider)
        provider = clean_registry.get("mock_provider")

        assert provider is mock_provider

    def test_get_nonexistent_returns_none(self, clean_registry):
        """Test getting non-existent provider returns None."""
        provider = clean_registry.get("nonexistent")
        assert provider is None

    def test_all_returns_all_providers(self, clean_registry, mock_provider):
        """Test all() returns all registered providers."""
        clean_registry.register(mock_provider)
        all_providers = clean_registry.all()

        assert len(all_providers) == 1
        assert mock_provider in all_providers

    def test_names_returns_all_names(self, clean_registry, mock_provider):
        """Test names() returns all provider names."""
        clean_registry.register(mock_provider)
        names = clean_registry.names()

        assert "mock_provider" in names

    def test_get_all_patterns(self, clean_registry, mock_provider):
        """Test get_all_patterns collects from all providers."""
        clean_registry.register(mock_provider)
        patterns = clean_registry.get_all_patterns()

        assert len(patterns) >= 1
        assert any(p.category == "test_category" for p in patterns)

    def test_get_all_sinks(self, clean_registry, mock_provider):
        """Test get_all_sinks collects from all providers."""
        clean_registry.register(mock_provider)
        sinks = clean_registry.get_all_sinks()

        assert "mock_provider:memory" in sinks
        assert "malloc" in sinks["mock_provider:memory"]

    def test_get_all_sources(self, clean_registry, mock_provider):
        """Test get_all_sources collects from all providers."""
        clean_registry.register(mock_provider)
        sources = clean_registry.get_all_sources()

        assert "mock_provider:input" in sources
        assert "read" in sources["mock_provider:input"]

    def test_get_all_sanitizers(self, clean_registry, mock_provider):
        """Test get_all_sanitizers collects from all providers."""
        clean_registry.register(mock_provider)
        sanitizers = clean_registry.get_all_sanitizers()

        assert "mock_provider:validation" in sanitizers
        assert "check" in sanitizers["mock_provider:validation"]

    def test_get_all_query_templates(self, clean_registry, mock_provider):
        """Test get_all_query_templates collects from all providers."""
        clean_registry.register(mock_provider)
        templates = clean_registry.get_all_query_templates()

        # Mock provider returns empty dict
        assert isinstance(templates, dict)

    def test_get_all_template_categories(self, clean_registry, mock_provider):
        """Test get_all_template_categories collects from all providers."""
        clean_registry.register(mock_provider)
        categories = clean_registry.get_all_template_categories()

        assert isinstance(categories, dict)

    def test_clear(self, clean_registry, mock_provider):
        """Test clear removes all providers."""
        clean_registry.register(mock_provider)
        clean_registry.clear()

        assert len(clean_registry.names()) == 0


# =============================================================================
# PostgreSQLPatternProvider Tests
# =============================================================================

class TestPostgreSQLPatternProvider:
    """Tests for PostgreSQLPatternProvider concrete implementation."""

    @pytest.fixture
    def pg_provider(self):
        """Create PostgreSQL provider instance."""
        return PostgreSQLPatternProvider()

    def test_provider_name(self, pg_provider):
        """Test provider name is 'postgresql'."""
        assert pg_provider.name == "postgresql"

    def test_provider_languages(self, pg_provider):
        """Test provider supports C language."""
        assert "C" in pg_provider.languages

    def test_get_sinks_returns_dict(self, pg_provider):
        """Test get_sinks returns dictionary."""
        sinks = pg_provider.get_sinks()
        assert isinstance(sinks, dict)

    def test_get_sinks_has_categories(self, pg_provider):
        """Test get_sinks has expected categories."""
        sinks = pg_provider.get_sinks()
        assert "pg_dump" in sinks
        assert "spi" in sinks
        assert "libpq" in sinks

    def test_get_sources_returns_dict(self, pg_provider):
        """Test get_sources returns dictionary."""
        sources = pg_provider.get_sources()
        assert isinstance(sources, dict)

    def test_get_sources_has_categories(self, pg_provider):
        """Test get_sources has expected categories."""
        sources = pg_provider.get_sources()
        assert "database" in sources
        assert "spi" in sources

    def test_get_sanitizers_returns_dict(self, pg_provider):
        """Test get_sanitizers returns dictionary."""
        sanitizers = pg_provider.get_sanitizers()
        assert isinstance(sanitizers, dict)

    def test_get_sanitizers_has_categories(self, pg_provider):
        """Test get_sanitizers has expected categories."""
        sanitizers = pg_provider.get_sanitizers()
        assert "escaping" in sanitizers
        assert "acl_check" in sanitizers

    def test_get_language_patterns_returns_list(self, pg_provider):
        """Test get_language_patterns returns list."""
        patterns = pg_provider.get_language_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_get_language_patterns_has_pg_dump_injection(self, pg_provider):
        """Test patterns include pg_dump_injection."""
        patterns = pg_provider.get_language_patterns()
        categories = [p.category for p in patterns]
        assert "pg_dump_injection" in categories

    def test_get_language_patterns_has_spi_sql_injection(self, pg_provider):
        """Test patterns include spi_sql_injection."""
        patterns = pg_provider.get_language_patterns()
        categories = [p.category for p in patterns]
        assert "spi_sql_injection" in categories

    def test_get_language_patterns_has_statistics_disclosure(self, pg_provider):
        """Test patterns include statistics_disclosure."""
        patterns = pg_provider.get_language_patterns()
        categories = [p.category for p in patterns]
        assert "statistics_disclosure" in categories

    def test_get_query_templates_returns_dict(self, pg_provider):
        """Test get_query_templates returns dictionary."""
        templates = pg_provider.get_query_templates()
        assert isinstance(templates, dict)
        assert len(templates) > 0

    def test_get_query_templates_has_expected(self, pg_provider):
        """Test templates include expected categories."""
        templates = pg_provider.get_query_templates()
        assert "pg_dump_injection" in templates
        assert "spi_sql_injection" in templates

    def test_get_template_categories_returns_dict(self, pg_provider):
        """Test get_template_categories returns dictionary."""
        categories = pg_provider.get_template_categories()
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_get_cve_patterns_returns_dict(self, pg_provider):
        """Test get_cve_patterns returns CVE patterns."""
        patterns = pg_provider.get_cve_patterns()
        assert isinstance(patterns, dict)
        assert "CVE-2025-8713" in patterns
        assert "CVE-2025-8714" in patterns
        assert "CVE-2025-8715" in patterns


# =============================================================================
# Auto-Registration Tests
# =============================================================================

class TestProviderAutoRegistration:
    """Tests for provider auto-registration."""

    def test_postgresql_provider_auto_registered(self):
        """Test PostgreSQL provider is auto-registered on import."""
        # Import triggers auto-registration
        from src.security.hypothesis.postgresql import provider

        # Should be in registry
        names = ProviderRegistry.names()
        assert "postgresql" in names

    def test_can_get_postgresql_provider(self):
        """Test can retrieve PostgreSQL provider from registry."""
        provider = ProviderRegistry.get("postgresql")
        assert provider is not None
        assert provider.name == "postgresql"
