"""PostgreSQL Domain Plugin Implementation.

Provides PostgreSQL-specific configurations for the CodeGraph Copilot.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..base import DomainPlugin, SubsystemInfo, SecurityPattern, IntentPattern
from .subsystems import get_default_subsystems
from .prompts import get_default_prompts
from .functions import (
    get_memory_functions,
    get_lock_functions,
    get_debug_functions,
    get_dml_functions,
    get_subsystem_functions,
    get_breakpoint_functions,
    get_concurrency_functions,
    get_assertion_functions,
    get_trace_functions,
    get_error_levels,
    get_noise_functions,
)
from .patterns import (
    get_entry_point_patterns,
    get_entry_points,
    get_sensitive_functions,
    get_error_handling_patterns,
    get_concurrency_keywords,
    get_memory_keywords,
    get_sanitization_confidence,
    get_sanitization_patterns,
    get_taint_sources,
    get_taint_sinks,
    get_vulnerability_function_mappings,
    get_duplicate_pattern_functions,
    get_compliance_patterns,
    get_refactoring_patterns,
    get_sql_query_patterns,
    get_documentation_patterns,
    get_domain_keywords,
    get_keyword_mappings,
)

logger = logging.getLogger(__name__)


class PostgreSQLDomainPlugin(DomainPlugin):
    """
    Domain plugin for PostgreSQL source code analysis.

    Provides:
    - PostgreSQL subsystem definitions (executor, parser, planner, etc.)
    - Security vulnerability patterns specific to PostgreSQL
    - Intent classification patterns with PostgreSQL-specific keywords
    - LLM prompts tailored for PostgreSQL expertise
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the PostgreSQL domain plugin.

        Args:
            config_dir: Optional path to configuration files.
                       Defaults to the directory containing this plugin.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        super().__init__(config_dir)

    @property
    def name(self) -> str:
        return "postgresql"

    @property
    def display_name(self) -> str:
        return "PostgreSQL"

    @property
    def description(self) -> str:
        return (
            "PostgreSQL is an advanced open-source relational database management system. "
            "This plugin provides analysis capabilities for PostgreSQL's C codebase, "
            "including the executor, parser, optimizer, storage, and replication subsystems."
        )

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load PostgreSQL subsystem definitions from YAML."""
        config = self._load_yaml_config("subsystems.yaml")

        subsystems = {}
        for name, data in config.get("subsystems", {}).items():
            subsystems[name] = SubsystemInfo(
                name=name,
                description=data.get("description", ""),
                key_functions=data.get("key_functions", []),
                patterns=data.get("patterns", []),
                related_files=data.get("related_files", []),
            )

        # If no config file, use fallback defaults
        if not subsystems:
            subsystems = self._get_default_subsystems()

        return subsystems

    def _get_default_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Fallback subsystem definitions if YAML not available."""
        return get_default_subsystems()

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load PostgreSQL-specific prompt templates."""
        config = self._load_yaml_config("prompts.yaml")

        if config:
            return config.get("prompts", {})

        return get_default_prompts()

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load PostgreSQL-specific intent classification patterns."""
        config = self._load_yaml_config("intent_patterns.yaml")

        patterns = {}
        for intent_id, data in config.get("intents", {}).items():
            patterns[intent_id] = IntentPattern(
                intent_id=intent_id,
                keywords=data.get("keywords", []),
                patterns=data.get("patterns", []),
                examples=data.get("examples", []),
                priority=data.get("priority", 0),
            )

        return patterns

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load PostgreSQL-specific security vulnerability patterns."""
        config = self._load_yaml_config("security_patterns.yaml")

        patterns = []
        for data in config.get("patterns", []):
            patterns.append(SecurityPattern(
                id=data.get("id", ""),
                name=data.get("name", ""),
                description=data.get("description", ""),
                severity=data.get("severity", "medium"),
                cwe_id=data.get("cwe_id"),
                indicators=data.get("indicators", []),
                sinks=data.get("sinks", []),
                sources=data.get("sources", []),
                sanitizers=data.get("sanitizers", []),
            ))

        return patterns

    def get_expert_role(self) -> str:
        """Get the PostgreSQL expert role for LLM prompts."""
        return "PostgreSQL database internals expert"

    def get_domain_context(self) -> str:
        """Get PostgreSQL-specific context for LLM prompts."""
        return "analyzing PostgreSQL database system source code (C language)"

    # Delegate to pattern module
    def get_entry_point_patterns(self) -> List[str]:
        return get_entry_point_patterns()

    def get_sensitive_functions(self) -> List[str]:
        return get_sensitive_functions()

    def get_memory_functions(self) -> Dict[str, str]:
        return get_memory_functions()

    def get_lock_functions(self) -> List[str]:
        return get_lock_functions()

    def get_error_handling_patterns(self) -> Dict[str, Any]:
        return get_error_handling_patterns()

    def get_error_levels(self) -> List[str]:
        return get_error_levels()

    def get_debug_functions(self) -> Dict[str, List[str]]:
        return get_debug_functions()

    def get_assertion_functions(self) -> List[str]:
        return get_assertion_functions()

    def get_trace_functions(self) -> List[str]:
        return get_trace_functions()

    def get_dml_functions(self) -> Dict[str, List[str]]:
        return get_dml_functions()

    def get_entry_points(self) -> List[str]:
        return get_entry_points()

    def get_subsystem_functions(self) -> Dict[str, List[str]]:
        return get_subsystem_functions()

    def get_concurrency_keywords(self) -> List[str]:
        return get_concurrency_keywords()

    def get_memory_keywords(self) -> List[str]:
        return get_memory_keywords()

    def get_breakpoint_functions(self) -> Dict[str, List[str]]:
        return get_breakpoint_functions()

    def get_sanitization_confidence(self) -> Dict[str, float]:
        return get_sanitization_confidence()

    def get_sanitization_patterns(self) -> List[Dict]:
        return get_sanitization_patterns()

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        return get_vulnerability_function_mappings()

    def get_duplicate_pattern_functions(self) -> Dict[str, List[str]]:
        return get_duplicate_pattern_functions()

    def get_taint_sources(self) -> List[str]:
        return get_taint_sources()

    def get_taint_sinks(self) -> List[str]:
        return get_taint_sinks()

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        return get_concurrency_functions()

    # Domain abstraction methods
    def get_compliance_patterns(self) -> Dict[str, List[str]]:
        return get_compliance_patterns()

    def get_refactoring_patterns(self) -> Dict[str, str]:
        return get_refactoring_patterns()

    def get_sql_query_patterns(self) -> Dict[str, List[str]]:
        return get_sql_query_patterns()

    def get_documentation_patterns(self) -> List[str]:
        return get_documentation_patterns()

    def get_domain_keywords(self) -> Dict[str, List[str]]:
        return get_domain_keywords()

    def get_noise_functions(self) -> List[str]:
        return get_noise_functions()

    def get_keyword_mappings(self) -> Dict[str, List[str]]:
        return get_keyword_mappings()


# Auto-register the plugin when module is imported
def _auto_register():
    """Auto-register PostgreSQL plugin with the registry."""
    try:
        from ..registry import DomainRegistry
        plugin = PostgreSQLDomainPlugin()
        DomainRegistry.register(plugin)
        logger.debug(f"Auto-registered {plugin.name} domain plugin")
    except ImportError:
        # Registry not available yet, skip auto-registration
        pass


_auto_register()
