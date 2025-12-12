"""
Provider Registry for Hypothesis Generation.

Central registry for security pattern providers. Providers auto-register
themselves when imported, making them available for use by the knowledge base.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import PatternProvider
    from ..models import LanguagePattern

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Central registry for security pattern providers.

    Maintains a collection of registered providers and provides methods
    to access their patterns, sinks, sources, and sanitizers.

    Usage:
        # Register a provider
        ProviderRegistry.register(MyProvider())

        # Get a specific provider
        pg_provider = ProviderRegistry.get("postgresql")

        # Get all patterns from all providers
        all_patterns = ProviderRegistry.get_all_patterns()
    """

    _providers: Dict[str, "PatternProvider"] = {}

    @classmethod
    def register(cls, provider: "PatternProvider") -> None:
        """Register a pattern provider.

        Args:
            provider: PatternProvider instance to register.
        """
        if provider.name in cls._providers:
            logger.warning(f"Provider '{provider.name}' already registered, overwriting")
        cls._providers[provider.name] = provider
        logger.debug(f"Registered pattern provider: {provider.name}")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a provider by name.

        Args:
            name: Provider name to unregister.

        Returns:
            True if provider was found and removed, False otherwise.
        """
        if name in cls._providers:
            del cls._providers[name]
            logger.debug(f"Unregistered pattern provider: {name}")
            return True
        return False

    @classmethod
    def get(cls, name: str) -> Optional["PatternProvider"]:
        """Get a provider by name.

        Args:
            name: Provider name (e.g., 'postgresql').

        Returns:
            PatternProvider instance or None if not found.
        """
        return cls._providers.get(name)

    @classmethod
    def all(cls) -> List["PatternProvider"]:
        """Get all registered providers.

        Returns:
            List of all PatternProvider instances.
        """
        return list(cls._providers.values())

    @classmethod
    def names(cls) -> List[str]:
        """Get names of all registered providers.

        Returns:
            List of provider names.
        """
        return list(cls._providers.keys())

    @classmethod
    def get_all_patterns(cls) -> List["LanguagePattern"]:
        """Collect patterns from all registered providers.

        Returns:
            Combined list of LanguagePattern from all providers.
        """
        patterns = []
        for provider in cls._providers.values():
            patterns.extend(provider.get_language_patterns())
        return patterns

    @classmethod
    def get_all_sinks(cls) -> Dict[str, List[str]]:
        """Collect sinks from all registered providers.

        Returns:
            Dict mapping category to list of sink functions.
            Categories are prefixed with provider name to avoid collisions.
        """
        all_sinks: Dict[str, List[str]] = {}
        for provider in cls._providers.values():
            for category, sinks in provider.get_sinks().items():
                key = f"{provider.name}:{category}"
                all_sinks[key] = sinks
        return all_sinks

    @classmethod
    def get_all_sources(cls) -> Dict[str, List[str]]:
        """Collect sources from all registered providers.

        Returns:
            Dict mapping category to list of source functions.
        """
        all_sources: Dict[str, List[str]] = {}
        for provider in cls._providers.values():
            for category, sources in provider.get_sources().items():
                key = f"{provider.name}:{category}"
                all_sources[key] = sources
        return all_sources

    @classmethod
    def get_all_sanitizers(cls) -> Dict[str, List[str]]:
        """Collect sanitizers from all registered providers.

        Returns:
            Dict mapping category to list of sanitizer functions.
        """
        all_sanitizers: Dict[str, List[str]] = {}
        for provider in cls._providers.values():
            for category, sanitizers in provider.get_sanitizers().items():
                key = f"{provider.name}:{category}"
                all_sanitizers[key] = sanitizers
        return all_sanitizers

    @classmethod
    def get_all_query_templates(cls) -> Dict[str, str]:
        """Collect query templates from all registered providers.

        Returns:
            Dict mapping template name to SQL query string.
        """
        all_templates: Dict[str, str] = {}
        for provider in cls._providers.values():
            all_templates.update(provider.get_query_templates())
        return all_templates

    @classmethod
    def get_all_template_categories(cls) -> Dict[str, Dict[str, Any]]:
        """Collect template categories from all registered providers.

        Returns:
            Dict mapping category name to configuration.
        """
        all_categories: Dict[str, Dict[str, Any]] = {}
        for provider in cls._providers.values():
            all_categories.update(provider.get_template_categories())
        return all_categories

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers. Mainly for testing."""
        cls._providers.clear()
        logger.debug("Cleared all pattern providers")
