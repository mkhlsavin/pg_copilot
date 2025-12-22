"""
Prompt Registry - Centralized Prompt Management

Управляет всеми промптами системы, поддерживает:
- Domain-specific промпты (PostgreSQL, Linux Kernel, LLVM)
- Template substitution (Jinja2-подобные шаблоны)
- Fallback to defaults
- Hot reloading from YAML files

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from string import Template

logger = logging.getLogger(__name__)


@dataclass
class Prompt:
    """
    Prompt template with metadata.

    Attributes:
        name: Unique prompt identifier
        template: Template string (supports ${variable} syntax)
        description: What this prompt does
        category: Category (e.g., "generation", "interpretation", "analysis")
        domain: CPG domain (e.g., "postgresql", "linux_kernel", "generic")
        version: Prompt version for tracking changes
    """
    name: str
    template: str
    description: str = ""
    category: str = "general"
    domain: str = "generic"
    version: str = "1.0"

    def render(self, **kwargs) -> str:
        """
        Render template with variables.

        Args:
            **kwargs: Template variables

        Returns:
            Rendered prompt string

        Example:
            prompt = Prompt(
                name="greeting",
                template="Hello, ${name}! You are a ${role}."
            )
            result = prompt.render(name="Alice", role="developer")
            # "Hello, Alice! You are a developer."
        """
        try:
            template = Template(self.template)
            return template.safe_substitute(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering prompt '{self.name}': {e}")
            return self.template


@dataclass
class AgentPrompt:
    """
    Agent-specific prompt with system and user templates.

    Attributes:
        name: Agent identifier (e.g., "code_reviewer", "security_auditor")
        system_prompt: System prompt template
        user_prompt: User prompt template
        description: What this agent does
        category: Agent category (e.g., "code_review", "security")
        version: Prompt version for tracking changes
    """
    name: str
    system_prompt: str
    user_prompt: str
    description: str = ""
    category: str = "general"
    version: str = "1.0"

    def render_system(self, **kwargs) -> str:
        """Render system prompt with variables."""
        try:
            template = Template(self.system_prompt)
            return template.safe_substitute(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering system prompt for '{self.name}': {e}")
            return self.system_prompt

    def render_user(self, **kwargs) -> str:
        """Render user prompt with variables."""
        try:
            template = Template(self.user_prompt)
            return template.safe_substitute(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering user prompt for '{self.name}': {e}")
            return self.user_prompt

    def render(self, **kwargs) -> Dict[str, str]:
        """
        Render both system and user prompts with variables.

        Returns:
            Dict with 'system' and 'user' keys containing rendered prompts
        """
        return {
            'system': self.render_system(**kwargs),
            'user': self.render_user(**kwargs)
        }


@dataclass
class DomainSpecialization:
    """
    Domain-specific specialization data.

    Attributes:
        name: Domain name (e.g., "PostgreSQL", "Linux Kernel")
        description: Domain description
        specializations: Dict of specialization areas to content
    """
    name: str
    description: str = ""
    specializations: Dict[str, str] = None

    def __post_init__(self):
        if self.specializations is None:
            self.specializations = {}

    def get(self, key: str, default: str = "") -> str:
        """Get specialization content by key."""
        return self.specializations.get(key, default)


class PromptRegistry:
    """
    Centralized registry for all system prompts.

    Features:
    - Load prompts from YAML files
    - Domain-specific prompts with fallback
    - Template variable substitution
    - Prompt versioning
    - Hot reload support
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize PromptRegistry.

        Args:
            config_dir: Directory containing prompt YAML files
                       If None, uses project root config/prompts/
        """
        if config_dir is None:
            # Default: project_root/config/prompts/
            project_root = Path(__file__).parents[2]
            config_dir = project_root / "config" / "prompts"

        self.config_dir = Path(config_dir)
        self.prompts: Dict[str, Dict[str, Prompt]] = {}  # {domain: {prompt_name: Prompt}}
        self.agent_prompts: Dict[str, AgentPrompt] = {}  # {agent_name: AgentPrompt}
        self.domain_specializations: Dict[str, DomainSpecialization] = {}  # {domain_key: DomainSpecialization}
        self.current_domain = "generic"

        # Load prompts
        self._load_prompts()

    def _load_prompts(self):
        """Load all prompts from YAML files in config directory."""
        if not self.config_dir.exists():
            logger.warning(f"Prompt config directory not found: {self.config_dir}")
            logger.warning("Using empty prompt registry. Create config/prompts/ directory with YAML files.")
            return

        logger.info(f"Loading prompts from: {self.config_dir}")

        # Load prompts.yaml (generic prompts)
        generic_file = self.config_dir / "prompts.yaml"
        if generic_file.exists():
            self._load_prompt_file(generic_file, domain="generic")

        # Load cpg_domains.yaml (domain-specific prompts)
        domains_file = self.config_dir / "cpg_domains.yaml"
        if domains_file.exists():
            self._load_domains_file(domains_file)

        # Load agent_prompts.yaml (agent-specific prompts)
        agent_prompts_file = self.config_dir / "agent_prompts.yaml"
        if agent_prompts_file.exists():
            self._load_agent_prompts_file(agent_prompts_file)

        logger.info(f"Loaded prompts for domains: {list(self.prompts.keys())}")

    def _load_prompt_file(self, file_path: Path, domain: str = "generic"):
        """
        Load prompts from a single YAML file.

        Args:
            file_path: Path to YAML file
            domain: CPG domain for these prompts
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty prompt file: {file_path}")
                return

            # Initialize domain if not exists
            if domain not in self.prompts:
                self.prompts[domain] = {}

            # Load prompts from 'prompts' section
            prompts_data = data.get('prompts', {})
            for prompt_name, prompt_config in prompts_data.items():
                prompt = Prompt(
                    name=prompt_name,
                    template=prompt_config.get('template', ''),
                    description=prompt_config.get('description', ''),
                    category=prompt_config.get('category', 'general'),
                    domain=domain,
                    version=prompt_config.get('version', '1.0')
                )
                self.prompts[domain][prompt_name] = prompt

            logger.info(f"Loaded {len(prompts_data)} prompts for domain '{domain}' from {file_path}")

        except Exception as e:
            logger.error(f"Error loading prompt file {file_path}: {e}")

    def _load_domains_file(self, file_path: Path):
        """
        Load domain-specific prompts from cpg_domains.yaml.

        File structure:
        domains:
          postgresql:
            name: PostgreSQL
            prompts:
              cpgql_generation_system: "..."
              ...
          linux_kernel:
            name: Linux Kernel
            prompts:
              cpgql_generation_system: "..."
              ...
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            domains_data = data.get('domains', {})

            for domain_key, domain_config in domains_data.items():
                if domain_key not in self.prompts:
                    self.prompts[domain_key] = {}

                # Load prompts for this domain
                prompts_data = domain_config.get('prompts', {})
                for prompt_name, prompt_config in prompts_data.items():
                    # Handle both simple string templates and full config
                    if isinstance(prompt_config, str):
                        template = prompt_config
                        description = ""
                        category = "general"
                        version = "1.0"
                    else:
                        template = prompt_config.get('template', '')
                        description = prompt_config.get('description', '')
                        category = prompt_config.get('category', 'general')
                        version = prompt_config.get('version', '1.0')

                    prompt = Prompt(
                        name=prompt_name,
                        template=template,
                        description=description,
                        category=category,
                        domain=domain_key,
                        version=version
                    )
                    self.prompts[domain_key][prompt_name] = prompt

                logger.info(f"Loaded {len(prompts_data)} prompts for domain '{domain_key}'")

        except Exception as e:
            logger.error(f"Error loading domains file {file_path}: {e}")

    def set_domain(self, domain: str):
        """
        Set current CPG domain.

        Args:
            domain: Domain name (e.g., "postgresql", "linux_kernel")

        Example:
            registry.set_domain("postgresql")
            prompt = registry.get("cpgql_generation_system")
        """
        if domain not in self.prompts and domain != "generic":
            logger.warning(f"Domain '{domain}' not found. Available: {list(self.prompts.keys())}")
            logger.warning(f"Falling back to 'generic' domain")
            domain = "generic"

        self.current_domain = domain
        logger.info(f"Set current domain to: {domain}")

    def get(
        self,
        prompt_name: str,
        domain: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> str:
        """
        Get prompt template by name.

        Args:
            prompt_name: Name of the prompt
            domain: CPG domain (if None, uses current_domain)
            fallback: If True, fallback to generic domain if not found
            **kwargs: Variables for template rendering

        Returns:
            Rendered prompt string

        Example:
            # Get PostgreSQL-specific prompt
            prompt = registry.get(
                "cpgql_generation_system",
                domain="postgresql",
                code_elements="methods, calls, files"
            )

            # Fallback to generic if domain not found
            prompt = registry.get("interpretation_system", fallback=True)
        """
        if domain is None:
            domain = self.current_domain

        # Try to get from specified domain
        if domain in self.prompts and prompt_name in self.prompts[domain]:
            prompt = self.prompts[domain][prompt_name]
            return prompt.render(**kwargs)

        # Fallback to generic domain
        if fallback and domain != "generic":
            if "generic" in self.prompts and prompt_name in self.prompts["generic"]:
                logger.debug(f"Prompt '{prompt_name}' not found in '{domain}', using generic")
                prompt = self.prompts["generic"][prompt_name]
                return prompt.render(**kwargs)

        # Not found
        logger.error(f"Prompt '{prompt_name}' not found in domain '{domain}'")
        return f"[ERROR: Prompt '{prompt_name}' not found]"

    def get_prompt(
        self,
        prompt_name: str,
        domain: Optional[str] = None,
        fallback: bool = True
    ) -> Optional[Prompt]:
        """
        Get Prompt object (without rendering).

        Args:
            prompt_name: Name of the prompt
            domain: CPG domain (if None, uses current_domain)
            fallback: If True, fallback to generic domain

        Returns:
            Prompt object or None
        """
        if domain is None:
            domain = self.current_domain

        # Try specified domain
        if domain in self.prompts and prompt_name in self.prompts[domain]:
            return self.prompts[domain][prompt_name]

        # Fallback to generic
        if fallback and domain != "generic":
            if "generic" in self.prompts and prompt_name in self.prompts["generic"]:
                return self.prompts["generic"][prompt_name]

        return None

    def list_prompts(self, domain: Optional[str] = None, category: Optional[str] = None) -> List[Prompt]:
        """
        List all prompts, optionally filtered.

        Args:
            domain: Filter by domain (None = all domains)
            category: Filter by category (None = all categories)

        Returns:
            List of Prompt objects
        """
        results = []

        # Determine domains to search
        if domain is not None:
            domains = [domain] if domain in self.prompts else []
        else:
            domains = list(self.prompts.keys())

        # Collect prompts
        for dom in domains:
            for prompt in self.prompts[dom].values():
                if category is None or prompt.category == category:
                    results.append(prompt)

        return results

    def reload(self):
        """Reload all prompts from YAML files."""
        logger.info("Reloading prompts...")
        self.prompts = {}
        self._load_prompts()

    def register_prompt(
        self,
        prompt_name: str,
        template: str,
        domain: str = "generic",
        description: str = "",
        category: str = "general",
        version: str = "1.0"
    ):
        """
        Register a prompt programmatically (useful for testing or dynamic prompts).

        Args:
            prompt_name: Unique prompt name
            template: Template string
            domain: CPG domain
            description: Prompt description
            category: Prompt category
            version: Version string
        """
        if domain not in self.prompts:
            self.prompts[domain] = {}

        prompt = Prompt(
            name=prompt_name,
            template=template,
            description=description,
            category=category,
            domain=domain,
            version=version
        )

        self.prompts[domain][prompt_name] = prompt
        logger.info(f"Registered prompt '{prompt_name}' for domain '{domain}'")

    # =========================================================================
    # AGENT PROMPT METHODS
    # =========================================================================

    def _load_agent_prompts_file(self, file_path: Path):
        """
        Load agent prompts from agent_prompts.yaml.

        File structure:
        agents:
          code_reviewer:
            system_prompt: "..."
            user_prompt: "..."
            description: "..."
            category: "code_review"
            version: "2.0"
        domains:
          postgresql:
            name: "PostgreSQL"
            description: "..."
            specializations:
              memory_management: "..."
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty agent prompts file: {file_path}")
                return

            # Load agents
            agents_data = data.get('agents', {})
            for agent_name, agent_config in agents_data.items():
                agent_prompt = AgentPrompt(
                    name=agent_name,
                    system_prompt=agent_config.get('system_prompt', ''),
                    user_prompt=agent_config.get('user_prompt', ''),
                    description=agent_config.get('description', ''),
                    category=agent_config.get('category', 'general'),
                    version=agent_config.get('version', '1.0')
                )
                self.agent_prompts[agent_name] = agent_prompt

            logger.info(f"Loaded {len(agents_data)} agent prompts from {file_path}")

            # Load domain specializations
            domains_data = data.get('domains', {})
            for domain_key, domain_config in domains_data.items():
                specializations = domain_config.get('specializations', {})
                domain_spec = DomainSpecialization(
                    name=domain_config.get('name', domain_key),
                    description=domain_config.get('description', ''),
                    specializations=specializations
                )
                self.domain_specializations[domain_key] = domain_spec

            logger.info(f"Loaded {len(domains_data)} domain specializations from {file_path}")

        except Exception as e:
            logger.error(f"Error loading agent prompts file {file_path}: {e}")

    def get_agent_prompt(
        self,
        agent_name: str,
        domain: Optional[str] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Get agent prompt with domain-specific specializations.

        Args:
            agent_name: Name of the agent (e.g., "code_reviewer", "security_auditor")
            domain: CPG domain for specialization (if None, uses current_domain)
            **kwargs: Variables for template rendering

        Returns:
            Dict with 'system' and 'user' keys containing rendered prompts

        Example:
            prompts = registry.get_agent_prompt(
                "code_reviewer",
                domain="postgresql",
                files_changed=5,
                additions=100,
                deletions=50
            )
            system_prompt = prompts['system']
            user_prompt = prompts['user']
        """
        if agent_name not in self.agent_prompts:
            logger.error(f"Agent prompt '{agent_name}' not found")
            return {
                'system': f"[ERROR: Agent '{agent_name}' not found]",
                'user': f"[ERROR: Agent '{agent_name}' not found]"
            }

        agent = self.agent_prompts[agent_name]

        # Get domain for specialization
        if domain is None:
            domain = self.current_domain

        # Add domain to kwargs if not present
        if 'domain' not in kwargs:
            if domain in self.domain_specializations:
                kwargs['domain'] = self.domain_specializations[domain].name
            else:
                kwargs['domain'] = domain

        # Add domain specializations if available
        if domain in self.domain_specializations:
            spec = self.domain_specializations[domain]
            for key, value in spec.specializations.items():
                # Only add if not already in kwargs
                if key not in kwargs:
                    kwargs[key] = value

        return agent.render(**kwargs)

    def get_agent_prompt_raw(self, agent_name: str) -> Optional[AgentPrompt]:
        """
        Get AgentPrompt object (without rendering).

        Args:
            agent_name: Name of the agent

        Returns:
            AgentPrompt object or None
        """
        return self.agent_prompts.get(agent_name)

    def get_domain_specialization(
        self,
        domain: str,
        key: str,
        default: str = ""
    ) -> str:
        """
        Get domain-specific specialization content.

        Args:
            domain: Domain key (e.g., "postgresql", "linux_kernel")
            key: Specialization key (e.g., "memory_management", "security_patterns")
            default: Default value if not found

        Returns:
            Specialization content or default

        Example:
            mem_info = registry.get_domain_specialization(
                "postgresql",
                "memory_management"
            )
        """
        if domain not in self.domain_specializations:
            return default

        return self.domain_specializations[domain].get(key, default)

    def list_agent_prompts(self, category: Optional[str] = None) -> List[AgentPrompt]:
        """
        List all agent prompts, optionally filtered by category.

        Args:
            category: Filter by category (None = all categories)

        Returns:
            List of AgentPrompt objects
        """
        results = []
        for agent in self.agent_prompts.values():
            if category is None or agent.category == category:
                results.append(agent)
        return results

    def list_domain_specializations(self) -> List[str]:
        """
        List all available domain specializations.

        Returns:
            List of domain keys
        """
        return list(self.domain_specializations.keys())


# Global registry instance
_global_registry: Optional[PromptRegistry] = None


def get_global_registry() -> PromptRegistry:
    """
    Get global PromptRegistry instance (singleton).

    Returns:
        Global PromptRegistry

    Example:
        from src.prompts.prompt_registry import get_global_registry

        registry = get_global_registry()
        prompt = registry.get("cpgql_generation_system")
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PromptRegistry()
    return _global_registry


def set_global_registry(registry: PromptRegistry):
    """Set global registry (useful for testing)."""
    global _global_registry
    _global_registry = registry


def reset_global_registry():
    """Reset global registry (useful for testing)."""
    global _global_registry
    _global_registry = None
