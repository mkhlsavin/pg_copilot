"""
Base class for domain plugins.

Each domain (PostgreSQL, Linux Kernel, LLVM, etc.) should implement this interface
to provide domain-specific configurations, prompts, and analysis patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml


@dataclass
class SubsystemInfo:
    """Information about a code subsystem within a domain."""
    name: str
    description: str
    key_functions: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)


@dataclass
class SecurityPattern:
    """A security vulnerability pattern for detection."""
    id: str
    name: str
    description: str
    severity: str  # critical, high, medium, low
    cwe_id: Optional[str] = None
    indicators: List[str] = field(default_factory=list)
    sinks: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    sanitizers: List[str] = field(default_factory=list)


@dataclass
class IntentPattern:
    """Pattern for classifying user intent."""
    intent_id: str
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    priority: int = 0


class DomainPlugin(ABC):
    """
    Abstract base class for domain-specific plugins.

    Each domain plugin provides:
    - Subsystem definitions (executor, planner, etc.)
    - LLM prompts customized for the domain
    - Intent classification patterns
    - Security vulnerability patterns
    - Domain-specific validation
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the domain plugin.

        Args:
            config_dir: Optional path to domain configuration files.
                       If None, uses default path relative to plugin location.
        """
        self._config_dir = config_dir
        self._subsystems: Optional[Dict[str, SubsystemInfo]] = None
        self._prompts: Optional[Dict[str, Dict[str, str]]] = None
        self._intent_patterns: Optional[Dict[str, IntentPattern]] = None
        self._security_patterns: Optional[List[SecurityPattern]] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this domain.

        Returns:
            Domain name (e.g., 'postgresql', 'linux_kernel', 'llvm')
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name for this domain.

        Returns:
            Display name (e.g., 'PostgreSQL', 'Linux Kernel', 'LLVM')
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Description of what this domain covers.

        Returns:
            Domain description
        """
        pass

    @property
    def subsystems(self) -> Dict[str, SubsystemInfo]:
        """
        Get subsystem definitions for this domain.

        Returns:
            Dictionary mapping subsystem names to SubsystemInfo objects
        """
        if self._subsystems is None:
            self._subsystems = self._load_subsystems()
        return self._subsystems

    @abstractmethod
    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """
        Load subsystem definitions from configuration.

        Returns:
            Dictionary of subsystem definitions
        """
        pass

    def get_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Get LLM prompts for this domain.

        Returns:
            Dictionary mapping intent names to prompt templates.
            Each template has 'system' and 'user_template' keys.
        """
        if self._prompts is None:
            self._prompts = self._load_prompts()
        return self._prompts

    @abstractmethod
    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Load prompt templates from configuration.

        Returns:
            Dictionary of prompt templates
        """
        pass

    def get_intent_patterns(self) -> Dict[str, IntentPattern]:
        """
        Get intent classification patterns.

        Returns:
            Dictionary mapping intent IDs to IntentPattern objects
        """
        if self._intent_patterns is None:
            self._intent_patterns = self._load_intent_patterns()
        return self._intent_patterns

    @abstractmethod
    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """
        Load intent patterns from configuration.

        Returns:
            Dictionary of intent patterns
        """
        pass

    def get_security_patterns(self) -> List[SecurityPattern]:
        """
        Get security vulnerability patterns for this domain.

        Returns:
            List of SecurityPattern objects
        """
        if self._security_patterns is None:
            self._security_patterns = self._load_security_patterns()
        return self._security_patterns

    @abstractmethod
    def _load_security_patterns(self) -> List[SecurityPattern]:
        """
        Load security patterns from configuration.

        Returns:
            List of security patterns
        """
        pass

    def get_subsystem_functions(self, subsystem: str) -> List[str]:
        """
        Get key functions for a specific subsystem.

        Args:
            subsystem: Subsystem name

        Returns:
            List of function names
        """
        if subsystem in self.subsystems:
            return self.subsystems[subsystem].key_functions
        return []

    def get_all_key_functions(self) -> List[str]:
        """
        Get all key functions across all subsystems.

        Returns:
            List of all key function names
        """
        functions = []
        for info in self.subsystems.values():
            functions.extend(info.key_functions)
        return functions

    def find_subsystem_for_function(self, func_name: str) -> Optional[str]:
        """
        Find which subsystem a function belongs to.

        Args:
            func_name: Function name to look up

        Returns:
            Subsystem name or None if not found
        """
        import re
        for subsystem_name, info in self.subsystems.items():
            if func_name in info.key_functions:
                return subsystem_name
            for pattern in info.patterns:
                if re.match(pattern, func_name):
                    return subsystem_name
        return None

    def validate_function(self, func_name: str) -> bool:
        """
        Check if a function name is valid for this domain.

        Args:
            func_name: Function name to validate

        Returns:
            True if the function appears to be from this domain
        """
        return self.find_subsystem_for_function(func_name) is not None

    def get_expert_role(self) -> str:
        """
        Get the expert role description for LLM prompts.

        Returns:
            Expert role string (e.g., "PostgreSQL database expert")
        """
        return f"{self.display_name} expert"

    def get_domain_context(self) -> str:
        """
        Get domain context for LLM prompts.

        Returns:
            Domain context description
        """
        return f"analyzing {self.display_name} source code"

    def _load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """
        Helper to load a YAML configuration file.

        Args:
            filename: Name of the YAML file

        Returns:
            Parsed YAML content
        """
        if self._config_dir:
            config_path = self._config_dir / filename
        else:
            # Default to same directory as the plugin
            import inspect
            plugin_file = inspect.getfile(self.__class__)
            config_path = Path(plugin_file).parent / filename

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
