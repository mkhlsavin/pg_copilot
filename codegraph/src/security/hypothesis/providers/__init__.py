"""
Pattern Provider Interface for Hypothesis Generation.

Defines the abstract interface for security pattern providers (plugins).
Each provider contributes language-specific sinks, sources, sanitizers,
and vulnerability patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Avoid circular import by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import LanguagePattern


class PatternProvider(ABC):
    """Abstract interface for security pattern providers.

    Providers supply project-specific or language-specific patterns
    for vulnerability detection. Examples: PostgreSQL, MySQL, Linux Kernel.

    Usage:
        class MyProvider(PatternProvider):
            @property
            def name(self) -> str:
                return "my_project"

            def get_language_patterns(self) -> List[LanguagePattern]:
                return [...]

        # Auto-register on import
        from .providers import ProviderRegistry
        ProviderRegistry.register(MyProvider())
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g., 'postgresql', 'mysql')."""
        pass

    @property
    @abstractmethod
    def languages(self) -> List[str]:
        """List of supported languages (e.g., ['C', 'C++'])."""
        pass

    @abstractmethod
    def get_language_patterns(self) -> List["LanguagePattern"]:
        """Return vulnerability patterns for this provider.

        Returns:
            List of LanguagePattern instances defining source/sink/sanitizer
            patterns for various vulnerability categories.
        """
        pass

    @abstractmethod
    def get_sinks(self) -> Dict[str, List[str]]:
        """Return sink functions grouped by category.

        Returns:
            Dict mapping category name to list of sink function names.
            Example: {"memory_alloc": ["palloc", "pfree"], ...}
        """
        pass

    @abstractmethod
    def get_sources(self) -> Dict[str, List[str]]:
        """Return source functions grouped by category.

        Returns:
            Dict mapping category name to list of source function names.
            Example: {"database": ["PQgetvalue", "SPI_getvalue"], ...}
        """
        pass

    @abstractmethod
    def get_sanitizers(self) -> Dict[str, List[str]]:
        """Return sanitizer functions grouped by category.

        Returns:
            Dict mapping category name to list of sanitizer function names.
            Example: {"escaping": ["fmtId", "quote_identifier"], ...}
        """
        pass

    def get_query_templates(self) -> Dict[str, str]:
        """Return SQL query templates for vulnerability detection.

        Optional method for providers that have custom SQL templates.

        Returns:
            Dict mapping template name to SQL query string.
        """
        return {}

    def get_template_categories(self) -> Dict[str, Dict[str, Any]]:
        """Return template category configurations.

        Optional method for providers that have custom template categories.

        Returns:
            Dict mapping category name to configuration dict with keys:
            - template: str (template name)
            - default_sinks: List[str]
            - default_sources: List[str]
            - default_sanitizers: List[str]
        """
        return {}


# Re-export registry for convenience
from .registry import ProviderRegistry

__all__ = [
    "PatternProvider",
    "ProviderRegistry",
]
