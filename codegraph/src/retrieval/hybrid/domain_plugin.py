"""
Domain Plugin Integration for Hybrid Retrieval

Provides functions to load subsystem definitions from domain plugins.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _get_subsystems_from_domain_plugin() -> Optional[Dict[str, Dict]]:
    """
    Try to get subsystems from the active domain plugin.

    Returns:
        Dictionary of subsystems or None if plugin not available
    """
    try:
        from src.domains import DomainRegistry

        domain = DomainRegistry.get_active_or_none()
        if domain is None:
            logger.debug("No active domain plugin")
            return None

        # Load YAML config once for efficiency
        yaml_data = domain._load_yaml_config("subsystems.yaml")
        yaml_subsystems = yaml_data.get('subsystems', {}) if yaml_data else {}

        # Convert domain plugin subsystems to legacy format
        subsystems = {}
        for name, info in domain.subsystems.items():
            # Get keywords from YAML (preferred) or fall back to empty list
            yaml_entry = yaml_subsystems.get(name, {})
            keywords = yaml_entry.get('keywords', [])

            subsystems[name] = {
                'patterns': info.patterns,
                'description': info.description,
                'keywords': keywords,
                'key_functions': info.key_functions,
            }

        logger.debug(f"Loaded {len(subsystems)} subsystems from {domain.name} plugin")
        return subsystems if subsystems else None
    except Exception as e:
        logger.debug(f"Could not load subsystems from domain plugin: {e}")
        return None


def get_subsystems() -> Dict[str, Dict]:
    """
    Get subsystems from the active domain plugin.

    Returns:
        Dictionary of subsystem definitions
    """
    subsystems = _get_subsystems_from_domain_plugin()
    if subsystems:
        return subsystems

    # If no plugin available, return empty dict and log warning
    logger.warning("No domain plugin active - subsystem mapping disabled")
    return {}


__all__ = ['get_subsystems', '_get_subsystems_from_domain_plugin']
