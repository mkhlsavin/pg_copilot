"""
CPG Configuration Management

Manages CPG domain configuration and integrates with PromptRegistry.

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025
"""

import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.prompts import get_global_registry

logger = logging.getLogger(__name__)


@dataclass
class CPGDomainInfo:
    """
    Information about a CPG domain.

    Attributes:
        key: Domain identifier (e.g., "postgresql", "linux_kernel")
        name: Human-readable name
        description: Domain description
        version_target: Target version (e.g., "17.6" for PostgreSQL)
        metadata: Additional metadata
    """
    key: str
    name: str
    description: str = ""
    version_target: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CPGConfig:
    """
    CPG Configuration Manager.

    Manages:
    - CPG domain selection
    - PromptRegistry integration
    - Domain-specific settings
    - Auto-detection of CPG type
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize CPG configuration.

        Args:
            config_path: Path to config.yaml (if None, uses default)
        """
        if config_path is None:
            project_root = Path(__file__).parents[2]
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self.config_data = self._load_config()

        # Get CPG type from config
        cpg_config = self.config_data.get('cpg', {})
        self.cpg_type = cpg_config.get('type', 'generic')
        self.custom_config_path = cpg_config.get('custom_config_path')

        # Load domain info
        self.domain_info = self._load_domain_info()

        # Set PromptRegistry domain
        prompt_registry = get_global_registry()
        prompt_registry.set_domain(self.cpg_type)

        logger.info(f"CPG Config initialized for domain: {self.cpg_type}")

    def _load_config(self) -> Dict:
        """Load main config.yaml."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _load_domain_info(self) -> CPGDomainInfo:
        """
        Load domain information from cpg_domains.yaml.

        Returns:
            CPGDomainInfo for current domain
        """
        # Path to cpg_domains.yaml
        domains_file = self.config_path.parent / "config" / "prompts" / "cpg_domains.yaml"

        if not domains_file.exists():
            logger.warning(f"Domain config not found: {domains_file}")
            return CPGDomainInfo(
                key=self.cpg_type,
                name=self.cpg_type.replace('_', ' ').title()
            )

        try:
            with open(domains_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            domains = data.get('domains', {})

            if self.cpg_type in domains:
                domain_data = domains[self.cpg_type]
                return CPGDomainInfo(
                    key=self.cpg_type,
                    name=domain_data.get('name', self.cpg_type),
                    description=domain_data.get('description', ''),
                    version_target=domain_data.get('version_target', ''),
                    metadata=domain_data.get('metadata', {})
                )
            else:
                logger.warning(f"Domain '{self.cpg_type}' not found in cpg_domains.yaml")
                return CPGDomainInfo(
                    key=self.cpg_type,
                    name=self.cpg_type.replace('_', ' ').title()
                )

        except Exception as e:
            logger.error(f"Error loading domain info: {e}")
            return CPGDomainInfo(
                key=self.cpg_type,
                name=self.cpg_type.replace('_', ' ').title()
            )

    def get_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Get domain-specific prompt.

        Args:
            prompt_name: Name of the prompt
            **kwargs: Variables for template rendering

        Returns:
            Rendered prompt string

        Example:
            config = CPGConfig()
            prompt = config.get_prompt("cpgql_generation_system", version="17.6")
        """
        registry = get_global_registry()

        # Add domain version to kwargs if not present
        if 'version' not in kwargs and self.domain_info.version_target:
            kwargs['version'] = self.domain_info.version_target

        return registry.get(prompt_name, domain=self.cpg_type, **kwargs)

    def get_code_analyst_title(self) -> str:
        """
        Get code analyst title for current domain.

        Returns:
            Analyst title string

        Example:
            config = CPGConfig()
            title = config.get_code_analyst_title()
            # "PostgreSQL 17.6 expert" for PostgreSQL domain
        """
        return self.get_prompt('code_analyst_title')

    def get_cpg_elements(self) -> str:
        """
        Get CPG elements description for current domain.

        Returns:
            CPG elements string
        """
        metadata = self.domain_info.metadata
        return metadata.get('cpg_elements', 'methods, calls, files')

    def auto_detect_cpg_type(self, cpg_path: Optional[Path] = None) -> str:
        """
        Auto-detect CPG type based on CPG content or file structure.

        Args:
            cpg_path: Path to CPG file (optional)

        Returns:
            Detected CPG type (postgresql, linux_kernel, llvm, or generic)

        Detection heuristics:
            - PostgreSQL: palloc/pfree, SPI_*, PG_FUNCTION_*, src/backend paths
            - Linux Kernel: kmalloc/kfree, __init/__exit, include/linux paths
            - LLVM: llvm::, Pass::, include/llvm paths
        """
        try:
            from src.services.cpg_query_service import CPGQueryService

            detection_scores = {
                'postgresql': 0,
                'linux_kernel': 0,
                'llvm': 0
            }

            with CPGQueryService() as cpg:
                # Check file paths for domain indicators
                try:
                    paths_query = """
                        SELECT filename FROM nodes_method
                        WHERE filename IS NOT NULL
                        LIMIT 100
                    """
                    results = cpg.execute_query(paths_query)
                    for row in results:
                        path = row.get('filename', '').lower()
                        if 'src/backend' in path or 'postgresql' in path:
                            detection_scores['postgresql'] += 2
                        elif 'include/linux' in path or 'kernel/' in path:
                            detection_scores['linux_kernel'] += 2
                        elif 'llvm/' in path or 'clang/' in path:
                            detection_scores['llvm'] += 2
                except Exception as e:
                    logger.debug(f"Path detection failed: {e}")

                # Check for domain-specific functions
                domain_functions = {
                    'postgresql': ['palloc', 'pfree', 'SPI_execute', 'elog', 'ereport'],
                    'linux_kernel': ['kmalloc', 'kfree', 'printk', 'module_init'],
                    'llvm': ['runOnFunction', 'getAnalysis', 'createPass']
                }

                for domain, funcs in domain_functions.items():
                    for func in funcs:
                        try:
                            result = cpg.execute_query(f"""
                                SELECT COUNT(*) as cnt FROM nodes_method
                                WHERE name LIKE '%{func}%' LIMIT 1
                            """)
                            if result and result[0].get('cnt', 0) > 0:
                                detection_scores[domain] += 3
                        except Exception:
                            pass

            # Determine best match
            best_domain = max(detection_scores, key=detection_scores.get)
            best_score = detection_scores[best_domain]

            if best_score >= 5:  # Threshold for confident detection
                logger.info(f"Auto-detected CPG type: {best_domain} (score: {best_score})")
                return best_domain
            else:
                logger.info(f"Low confidence detection. Using configured type: {self.cpg_type}")
                return self.cpg_type

        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}. Using configured type: {self.cpg_type}")
            return self.cpg_type

    def get_agent_prompt(self, agent_name: str, **kwargs) -> Dict[str, str]:
        """
        Get agent-specific prompts with domain injection.

        Args:
            agent_name: Name of the agent (e.g., 'code_reviewer', 'security_auditor')
            **kwargs: Additional variables for template rendering

        Returns:
            Dict with 'system' and 'user' prompt strings

        Example:
            config = get_global_cpg_config()
            prompts = config.get_agent_prompt('security_auditor', query="find SQL injection")
        """
        registry = get_global_registry()

        # Add domain name to kwargs for template substitution
        kwargs['domain'] = self.domain_info.name

        return registry.get_agent_prompt(agent_name, **kwargs)

    def get_domain_specialization(self, key: str, default: str = "") -> str:
        """
        Get domain-specific specialization knowledge.

        Args:
            key: Specialization key (e.g., 'memory_management', 'security_patterns')
            default: Default value if not found

        Returns:
            Specialization content string

        Example:
            config = get_global_cpg_config()
            mem_info = config.get_domain_specialization('memory_management')
        """
        registry = get_global_registry()
        return registry.get_domain_specialization(self.cpg_type, key, default)

    def set_cpg_type(self, cpg_type: str):
        """
        Change CPG domain type.

        Args:
            cpg_type: New CPG type (e.g., "linux_kernel")

        Example:
            config = CPGConfig()
            config.set_cpg_type("linux_kernel")
        """
        self.cpg_type = cpg_type
        self.domain_info = self._load_domain_info()

        # Update PromptRegistry
        prompt_registry = get_global_registry()
        prompt_registry.set_domain(cpg_type)

        logger.info(f"Changed CPG type to: {cpg_type}")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get domain metadata value.

        Args:
            key: Metadata key
            default: Default value if not found

        Returns:
            Metadata value
        """
        return self.domain_info.metadata.get(key, default)

    def get_domain_info(self) -> CPGDomainInfo:
        """Get full domain information."""
        return self.domain_info

    @classmethod
    def from_config_file(cls, config_path: Path) -> 'CPGConfig':
        """
        Create CPGConfig from config file.

        Args:
            config_path: Path to config.yaml

        Returns:
            CPGConfig instance
        """
        return cls(config_path=config_path)


# Global instance
_global_cpg_config: Optional[CPGConfig] = None


def get_global_cpg_config() -> CPGConfig:
    """
    Get global CPGConfig instance (singleton).

    Returns:
        Global CPGConfig

    Example:
        from src.config.cpg_config import get_global_cpg_config

        config = get_global_cpg_config()
        prompt = config.get_prompt("cpgql_generation_system")
    """
    global _global_cpg_config
    if _global_cpg_config is None:
        _global_cpg_config = CPGConfig()
    return _global_cpg_config


def set_global_cpg_config(config: CPGConfig):
    """Set global CPGConfig (useful for testing)."""
    global _global_cpg_config
    _global_cpg_config = config


def reset_global_cpg_config():
    """Reset global CPGConfig (useful for testing)."""
    global _global_cpg_config
    _global_cpg_config = None
