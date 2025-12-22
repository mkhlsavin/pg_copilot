"""
Domain Setup Step.

Generates a domain plugin for the imported project.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class DomainSetupStep:
    """Step for setting up a domain plugin."""

    # Template for the plugin Python file
    PLUGIN_TEMPLATE = '''"""
{display_name} Domain Plugin.

Auto-generated domain plugin for {project_name} codebase.
Language: {language}
"""

from pathlib import Path
from typing import Dict, List, Any, Optional

from src.domains.base import DomainPlugin, SubsystemInfo, SecurityPattern, IntentPattern


class {class_name}Plugin(DomainPlugin):
    """Domain plugin for {display_name} source code analysis."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        super().__init__(config_dir)

    @property
    def name(self) -> str:
        return "{domain_name}"

    @property
    def display_name(self) -> str:
        return "{display_name}"

    @property
    def description(self) -> str:
        return "{description}"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load subsystem definitions."""
        config = self._load_yaml_config("subsystems.yaml")
        subsystems = {{}}
        for name, data in config.get("subsystems", {{}}).items():
            subsystems[name] = SubsystemInfo(
                name=name,
                description=data.get("description", ""),
                key_functions=data.get("key_functions", []),
                patterns=data.get("patterns", []),
                related_files=data.get("related_files", []),
            )
        return subsystems if subsystems else self._get_default_subsystems()

    def _get_default_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Return default subsystem configuration."""
        return {{
            "core": SubsystemInfo(
                name="core",
                description="Core functionality",
                key_functions={entry_points},
                patterns=["src", "lib"],
                related_files=[],
            ),
        }}

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load LLM prompts."""
        config = self._load_yaml_config("prompts.yaml")
        return config.get("prompts", {{}})

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load intent patterns."""
        return {{}}

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load security patterns."""
        return []

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Return vulnerability to function mappings."""
        return {{
            "buffer_overflow": {buffer_overflow_funcs},
            "sql_injection": {sql_injection_funcs},
            "null_pointer": {null_pointer_funcs},
        }}

    def get_taint_sources(self) -> List[str]:
        """Return taint source functions."""
        return {taint_sources}

    def get_taint_sinks(self) -> List[str]:
        """Return taint sink functions."""
        return {taint_sinks}
'''

    # Template for subsystems.yaml
    SUBSYSTEMS_TEMPLATE = """# Auto-generated subsystems configuration for {project_name}
# Language: {language}

subsystems:
  core:
    description: "Core application logic"
    key_functions:
{entry_points_yaml}
    patterns:
      - "src"
      - "lib"
      - "main"
    related_files: []

  utils:
    description: "Utility functions"
    key_functions: []
    patterns:
      - "util"
      - "helper"
      - "common"
    related_files: []
"""

    # Template for prompts.yaml
    PROMPTS_TEMPLATE = """# Auto-generated prompts for {project_name}
# Language: {language}

prompts:
  onboarding:
    system: |
      You are a {display_name} expert helping developers understand the codebase.
      The codebase is written primarily in {language}.
    user_template: |
      Help me understand the following aspect of {display_name}: {{query}}

  security:
    system: |
      You are a security expert analyzing {display_name} ({language}) code for vulnerabilities.
      Focus on common vulnerability patterns for {language}.
    user_template: |
      Analyze the following code for security vulnerabilities:
      {{code}}

  documentation:
    system: |
      You are a documentation expert for {display_name}.
      Generate clear, concise documentation.
    user_template: |
      Generate documentation for:
      {{code}}

  code_review:
    system: |
      You are a code reviewer for {display_name} ({language}).
      Review code for quality, security, and best practices.
    user_template: |
      Review the following code changes:
      {{diff}}
"""

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize domain setup step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute domain plugin generation.

        Args:
            context: Pipeline context with source_path, detected_language, etc.

        Returns:
            Dictionary with domain_plugin_path and domain_config.
        """
        request = context["request"]
        source_path = Path(context["source_path"])
        detected_language = context["detected_language"]
        duckdb_path = context.get("duckdb_path")

        # Determine domain name
        project_name = source_path.name
        domain_name = (
            request.domain_name
            or project_name.lower().replace("-", "_").replace(".", "_")
        )
        class_name = self._to_class_name(domain_name)
        display_name = self._to_display_name(domain_name)

        self._report_progress(10, f"Creating domain plugin: {domain_name}")

        # Plugin directory
        domains_dir = Path("src/domains")
        plugin_dir = domains_dir / domain_name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Detect entry points and patterns from CPG
        self._report_progress(30, "Analyzing code structure...")

        entry_points = []
        vulnerability_funcs = {
            "buffer_overflow": [],
            "sql_injection": [],
            "null_pointer": [],
        }
        taint_sources = []
        taint_sinks = []

        if duckdb_path:
            entry_points = await self._detect_entry_points(duckdb_path)
            vulnerability_funcs = await self._detect_vulnerability_functions(
                duckdb_path, detected_language
            )
            taint_sources, taint_sinks = await self._detect_taint_functions(
                duckdb_path, detected_language
            )

        if not entry_points:
            entry_points = ["main"]

        self._report_progress(50, "Generating plugin files...")

        # Generate __init__.py
        init_content = f'from .plugin import {class_name}Plugin\n\n__all__ = ["{class_name}Plugin"]\n'
        (plugin_dir / "__init__.py").write_text(init_content)

        # Generate plugin.py
        plugin_content = self.PLUGIN_TEMPLATE.format(
            display_name=display_name,
            project_name=project_name,
            class_name=class_name,
            domain_name=domain_name,
            language=detected_language.value,
            description=f"Auto-generated plugin for {display_name} ({detected_language.value}) codebase",
            entry_points=entry_points[:10],
            buffer_overflow_funcs=vulnerability_funcs.get("buffer_overflow", [])[:10],
            sql_injection_funcs=vulnerability_funcs.get("sql_injection", [])[:10],
            null_pointer_funcs=vulnerability_funcs.get("null_pointer", [])[:10],
            taint_sources=taint_sources[:10],
            taint_sinks=taint_sinks[:10],
        )
        (plugin_dir / "plugin.py").write_text(plugin_content)

        self._report_progress(70, "Generating configuration files...")

        # Generate subsystems.yaml
        entry_points_yaml = "\n".join(f'      - "{ep}"' for ep in entry_points[:20])
        subsystems_content = self.SUBSYSTEMS_TEMPLATE.format(
            project_name=project_name,
            language=detected_language.value,
            entry_points_yaml=entry_points_yaml,
        )
        (plugin_dir / "subsystems.yaml").write_text(subsystems_content)

        # Generate prompts.yaml
        prompts_content = self.PROMPTS_TEMPLATE.format(
            project_name=project_name,
            display_name=display_name,
            language=detected_language.value,
        )
        (plugin_dir / "prompts.yaml").write_text(prompts_content)

        self._report_progress(100, "Domain plugin created")

        logger.info(f"Domain plugin created at {plugin_dir}")

        return {
            "domain_plugin_path": str(plugin_dir),
            "domain_name": domain_name,
            "domain_config": {
                "name": domain_name,
                "display_name": display_name,
                "language": detected_language.value,
                "entry_points": entry_points[:20],
                "plugin_class": f"{class_name}Plugin",
            },
        }

    async def _detect_entry_points(self, duckdb_path: str) -> List[str]:
        """Detect entry point functions from CPG."""
        entry_points = []

        try:
            conn = duckdb.connect(duckdb_path, read_only=True)

            # Find main-like functions
            results = conn.execute("""
                SELECT DISTINCT name
                FROM nodes_method
                WHERE name IN ('main', 'Main', 'init', 'Init', 'start', 'Start',
                              'run', 'Run', 'execute', 'Execute', 'setup', 'Setup')
                   OR name LIKE '%_main'
                   OR name LIKE 'Init%'
                   OR name LIKE '%Main'
                LIMIT 30
            """).fetchall()

            entry_points = [r[0] for r in results]
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to detect entry points: {e}")

        return entry_points

    async def _detect_vulnerability_functions(
        self, duckdb_path: str, language
    ) -> Dict[str, List[str]]:
        """Detect functions related to common vulnerabilities."""
        result = {
            "buffer_overflow": [],
            "sql_injection": [],
            "null_pointer": [],
        }

        # Language-specific patterns
        patterns = {
            "c": {
                "buffer_overflow": ["strcpy", "strcat", "sprintf", "gets", "memcpy"],
                "sql_injection": ["sqlite3_exec", "mysql_query", "PQexec"],
                "null_pointer": ["malloc", "calloc", "realloc"],
            },
            "java": {
                "buffer_overflow": [],
                "sql_injection": ["executeQuery", "execute", "prepareStatement"],
                "null_pointer": ["get", "find", "load"],
            },
            "python": {
                "buffer_overflow": [],
                "sql_injection": ["execute", "executemany", "raw"],
                "null_pointer": [],
            },
            "javascript": {
                "buffer_overflow": [],
                "sql_injection": ["query", "execute", "raw"],
                "null_pointer": [],
            },
        }

        lang_key = language.value if hasattr(language, "value") else str(language)
        lang_patterns = patterns.get(lang_key, patterns.get("c", {}))

        try:
            conn = duckdb.connect(duckdb_path, read_only=True)

            for vuln_type, funcs in lang_patterns.items():
                if not funcs:
                    continue

                placeholders = ", ".join(f"'{f}'" for f in funcs)
                query = f"""
                    SELECT DISTINCT name
                    FROM nodes_call
                    WHERE name IN ({placeholders})
                    LIMIT 20
                """
                found = conn.execute(query).fetchall()
                result[vuln_type] = [r[0] for r in found]

            conn.close()

        except Exception as e:
            logger.warning(f"Failed to detect vulnerability functions: {e}")

        return result

    async def _detect_taint_functions(
        self, duckdb_path: str, language
    ) -> tuple:
        """Detect taint source and sink functions."""
        sources = []
        sinks = []

        # Language-specific taint patterns
        taint_patterns = {
            "c": {
                "sources": ["recv", "read", "fgets", "getenv", "scanf"],
                "sinks": ["system", "exec", "popen", "write", "send"],
            },
            "java": {
                "sources": ["getParameter", "getHeader", "getInputStream"],
                "sinks": ["execute", "write", "print", "eval"],
            },
            "python": {
                "sources": ["input", "request", "read", "recv"],
                "sinks": ["eval", "exec", "system", "execute", "write"],
            },
        }

        lang_key = language.value if hasattr(language, "value") else str(language)
        patterns = taint_patterns.get(lang_key, taint_patterns.get("c", {}))

        try:
            conn = duckdb.connect(duckdb_path, read_only=True)

            for source in patterns.get("sources", []):
                found = conn.execute(f"""
                    SELECT DISTINCT name FROM nodes_call
                    WHERE name LIKE '%{source}%'
                    LIMIT 5
                """).fetchall()
                sources.extend([r[0] for r in found])

            for sink in patterns.get("sinks", []):
                found = conn.execute(f"""
                    SELECT DISTINCT name FROM nodes_call
                    WHERE name LIKE '%{sink}%'
                    LIMIT 5
                """).fetchall()
                sinks.extend([r[0] for r in found])

            conn.close()

        except Exception as e:
            logger.warning(f"Failed to detect taint functions: {e}")

        return list(set(sources))[:10], list(set(sinks))[:10]

    def _to_class_name(self, domain_name: str) -> str:
        """Convert domain name to class name (PascalCase)."""
        return "".join(word.capitalize() for word in domain_name.split("_"))

    def _to_display_name(self, domain_name: str) -> str:
        """Convert domain name to display name."""
        return " ".join(word.capitalize() for word in domain_name.split("_"))

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Domain setup step: {progress}% - {message}")
