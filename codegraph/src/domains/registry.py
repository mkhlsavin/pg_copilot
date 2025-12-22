"""
Domain Plugin Registry.

Manages registration and activation of domain plugins, providing
a central point for accessing the currently active domain configuration.
"""

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import DomainPlugin

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Registry for domain plugins.

    This class manages the lifecycle of domain plugins:
    - Registration of available plugins
    - Activation of a specific domain
    - Access to the currently active domain

    Usage:
        # Register plugins (usually done automatically)
        DomainRegistry.register(PostgreSQLDomainPlugin())

        # Activate a domain
        DomainRegistry.activate('postgresql')

        # Get active domain
        domain = DomainRegistry.get_active()
        print(domain.subsystems)
    """

    _plugins: Dict[str, DomainPlugin] = {}
    _active: Optional[DomainPlugin] = None
    _default_domain: str = 'postgresql'

    @classmethod
    def register(cls, plugin: DomainPlugin) -> None:
        """
        Register a domain plugin.

        Args:
            plugin: The domain plugin instance to register
        """
        cls._plugins[plugin.name] = plugin
        logger.debug(f"Registered domain plugin: {plugin.name}")

    @classmethod
    def unregister(cls, domain_name: str) -> bool:
        """
        Unregister a domain plugin.

        Args:
            domain_name: Name of the domain to unregister

        Returns:
            True if the plugin was unregistered, False if not found
        """
        if domain_name in cls._plugins:
            del cls._plugins[domain_name]
            if cls._active and cls._active.name == domain_name:
                cls._active = None
            logger.debug(f"Unregistered domain plugin: {domain_name}")
            return True
        return False

    @classmethod
    def activate(cls, domain_name: str) -> DomainPlugin:
        """
        Activate a domain plugin.

        Args:
            domain_name: Name of the domain to activate

        Returns:
            The activated domain plugin

        Raises:
            ValueError: If the domain is not registered
        """
        if domain_name not in cls._plugins:
            available = list(cls._plugins.keys())
            raise ValueError(
                f"Domain '{domain_name}' is not registered. "
                f"Available domains: {available}"
            )

        cls._active = cls._plugins[domain_name]
        logger.info(f"Activated domain: {domain_name}")
        return cls._active

    @classmethod
    def get_active(cls) -> DomainPlugin:
        """
        Get the currently active domain plugin.

        Returns:
            The active domain plugin

        Raises:
            RuntimeError: If no domain is activated
        """
        if cls._active is None:
            # Try to activate default domain
            if cls._default_domain in cls._plugins:
                return cls.activate(cls._default_domain)
            raise RuntimeError(
                "No domain is activated. Call DomainRegistry.activate(domain_name) first."
            )
        return cls._active

    @classmethod
    def get_active_or_none(cls) -> Optional[DomainPlugin]:
        """
        Get the currently active domain plugin, or None if not set.

        Returns:
            The active domain plugin or None
        """
        return cls._active

    @classmethod
    def get(cls, domain_name: str) -> Optional[DomainPlugin]:
        """
        Get a specific domain plugin by name.

        Args:
            domain_name: Name of the domain

        Returns:
            The domain plugin or None if not found
        """
        return cls._plugins.get(domain_name)

    @classmethod
    def list_domains(cls) -> List[str]:
        """
        Get list of all registered domain names.

        Returns:
            List of domain names
        """
        return list(cls._plugins.keys())

    @classmethod
    def get_all(cls) -> Dict[str, DomainPlugin]:
        """
        Get all registered domain plugins.

        Returns:
            Dictionary mapping domain names to plugins
        """
        return cls._plugins.copy()

    @classmethod
    def is_registered(cls, domain_name: str) -> bool:
        """
        Check if a domain is registered.

        Args:
            domain_name: Name of the domain

        Returns:
            True if the domain is registered
        """
        return domain_name in cls._plugins

    @classmethod
    def set_default(cls, domain_name: str) -> None:
        """
        Set the default domain to activate when none is specified.

        Args:
            domain_name: Name of the domain to set as default
        """
        cls._default_domain = domain_name

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered plugins and reset the registry.
        Mainly useful for testing.
        """
        cls._plugins.clear()
        cls._active = None
        cls._default_domain = 'postgresql'

    @classmethod
    def auto_discover(cls, plugins_dir: Optional[Path] = None) -> List[str]:
        """
        Auto-discover and register domain plugins.

        Looks for plugin modules in the specified directory (or default
        src/domains/) and registers any found plugins.

        Args:
            plugins_dir: Optional directory to search for plugins

        Returns:
            List of discovered and registered domain names
        """
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent

        discovered = []

        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_module = item / 'plugin.py'
                if plugin_module.exists():
                    try:
                        # Import the plugin module
                        module_name = f"src.domains.{item.name}.plugin"
                        module = importlib.import_module(module_name)

                        # Look for a plugin class
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and
                                issubclass(attr, DomainPlugin) and
                                attr is not DomainPlugin):
                                plugin = attr()
                                cls.register(plugin)
                                discovered.append(plugin.name)
                                break
                    except Exception as e:
                        logger.warning(f"Failed to load plugin from {item.name}: {e}")

        return discovered


def get_active_domain() -> DomainPlugin:
    """
    Convenience function to get the active domain plugin.

    Returns:
        The active domain plugin
    """
    return DomainRegistry.get_active()


def register_domain(plugin: DomainPlugin) -> None:
    """
    Convenience function to register a domain plugin.

    Args:
        plugin: The domain plugin to register
    """
    DomainRegistry.register(plugin)
