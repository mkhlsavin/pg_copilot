"""
Unified Configuration Module.

Provides a single entry point for all application configuration.
Consolidates multiple config systems into one coherent interface.

Usage:
    from src.config.unified_config import get_unified_config

    config = get_unified_config()

    # Access different config sections
    endpoint = config.joern.endpoint
    db_url = config.api.database_url
    llm_provider = config.llm.provider
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Data Classes
# ============================================================================

@dataclass
class JoernSettings:
    """Joern server and CPG settings."""

    home: Optional[Path] = None
    endpoint: str = "localhost:8080"
    cpg_path: Optional[Path] = None
    source_path: Optional[Path] = None
    server_port: int = 8080
    query_timeout: int = 60
    memory_gb: int = 16
    use_docker: bool = False
    docker_image: str = "ghcr.io/joernio/joern:latest"

    @property
    def host(self) -> str:
        """Extract host from endpoint."""
        return self.endpoint.split(":")[0]

    @property
    def port(self) -> int:
        """Extract port from endpoint."""
        parts = self.endpoint.split(":")
        return int(parts[1]) if len(parts) > 1 else 8080

    @property
    def joern_cli_path(self) -> Optional[Path]:
        """Get path to joern-cli directory."""
        if self.home:
            return self.home / "joern-cli"
        return None


@dataclass
class LLMSettings:
    """LLM provider settings."""

    provider: str = "gigachat"
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60

    # Provider-specific
    gigachat_auth_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


@dataclass
class APISettings:
    """API server settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    database_url: Optional[str] = None
    redis_url: Optional[str] = None


@dataclass
class RetrievalSettings:
    """RAG retrieval settings."""

    embedding_model: str = "all-MiniLM-L6-v2"
    top_k_qa: int = 3
    top_k_cpgql: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200


@dataclass
class CPGSettings:
    """CPG domain settings."""

    type: str = "postgresql"
    version_target: str = ""
    custom_config_path: Optional[str] = None


@dataclass
class TimeoutSettings:
    """Timeout configuration."""

    http_client: int = 30
    db_pool: int = 30
    docker_operation: int = 60
    docker_build: int = 600
    sast_scan: int = 300
    joern_query: int = 60


@dataclass
class LimitSettings:
    """Resource limits configuration."""

    db_pool_size: int = 10
    db_max_overflow: int = 20
    cache_max_size: int = 1000
    cache_ttl: int = 3600
    query_result_limit: int = 100
    session_turns_limit: int = 10


# ============================================================================
# Unified Configuration Class
# ============================================================================

class UnifiedConfig:
    """
    Single entry point for all application configuration.

    Loads configuration from config.yaml with environment variable interpolation.
    Provides typed access to all configuration sections.

    Example:
        config = UnifiedConfig.get_instance()
        print(config.joern.endpoint)
        print(config.llm.provider)
    """

    _instance: Optional["UnifiedConfig"] = None
    _config_path: Optional[Path] = None

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize unified configuration.

        Args:
            config_path: Path to config.yaml. If None, searches in project root.
        """
        if config_path is None:
            config_path = self._find_config_path()

        self._path = config_path
        self._raw: Dict[str, Any] = {}
        self._load()

        # Initialize typed settings
        self._joern: Optional[JoernSettings] = None
        self._llm: Optional[LLMSettings] = None
        self._api: Optional[APISettings] = None
        self._retrieval: Optional[RetrievalSettings] = None
        self._cpg: Optional[CPGSettings] = None
        self._timeouts: Optional[TimeoutSettings] = None
        self._limits: Optional[LimitSettings] = None

    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> "UnifiedConfig":
        """
        Get singleton instance.

        Args:
            config_path: Path to config.yaml (only used on first call)

        Returns:
            UnifiedConfig instance
        """
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None

    def _find_config_path(self) -> Path:
        """Find config.yaml in project structure."""
        # Try current directory first
        if Path("config.yaml").exists():
            return Path("config.yaml")

        # Try relative to this file
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        config_path = project_root / "config.yaml"

        if config_path.exists():
            return config_path

        # Fallback
        return Path("config.yaml")

    def _load(self) -> None:
        """Load and parse config.yaml with env var interpolation."""
        if not self._path.exists():
            logger.warning(f"Config file not found: {self._path}")
            self._raw = {}
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                content = f.read()

            # Interpolate environment variables
            content = self._interpolate_env_vars(content)

            self._raw = yaml.safe_load(content) or {}
            logger.info(f"Loaded configuration from {self._path}")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._raw = {}

    def _interpolate_env_vars(self, content: str) -> str:
        """
        Replace ${VAR} and ${VAR:-default} with environment values.

        Args:
            content: Raw YAML content

        Returns:
            Content with interpolated environment variables
        """
        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

        def replace(match):
            var_name = match.group(1)
            default_value = match.group(2)
            env_value = os.environ.get(var_name)

            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                # Keep original if no value and no default
                return match.group(0)

        return re.sub(pattern, replace, content)

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
        # Reset cached settings
        self._joern = None
        self._llm = None
        self._api = None
        self._retrieval = None
        self._cpg = None
        self._timeouts = None
        self._limits = None

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get nested configuration value.

        Args:
            *keys: Path to config value (e.g., "joern", "endpoint")
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        value = self._raw
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def raw(self) -> Dict[str, Any]:
        """Get raw configuration dictionary."""
        return self._raw

    # ========================================================================
    # Typed Configuration Properties
    # ========================================================================

    @property
    def joern(self) -> JoernSettings:
        """Get Joern settings."""
        if self._joern is None:
            joern_data = self._raw.get("joern", {})

            home = joern_data.get("home") or joern_data.get("installation_path")
            if home and home.lower() != "auto":
                home = Path(home)
            else:
                home = self._detect_joern_home()

            cpg_path = joern_data.get("cpg_path")
            if cpg_path:
                cpg_path = Path(cpg_path)

            source_path = joern_data.get("source_path")
            if source_path:
                source_path = Path(source_path)

            self._joern = JoernSettings(
                home=home,
                endpoint=joern_data.get("endpoint", "localhost:8080"),
                cpg_path=cpg_path,
                source_path=source_path,
                server_port=joern_data.get("server_port", 8080),
                query_timeout=joern_data.get("query_timeout", 60),
                memory_gb=joern_data.get("memory_gb", 16),
                use_docker=joern_data.get("use_docker", False),
                docker_image=joern_data.get(
                    "docker_image", "ghcr.io/joernio/joern:latest"
                ),
            )

        return self._joern

    def _detect_joern_home(self) -> Optional[Path]:
        """Auto-detect Joern installation."""
        # Check JOERN_HOME env var
        env_home = os.environ.get("JOERN_HOME")
        if env_home:
            path = Path(env_home)
            if path.exists():
                return path

        # Check common paths
        common_paths = [
            Path.home() / "joern",
            Path("C:/joern"),
            Path("/opt/joern"),
            Path("/usr/local/joern"),
        ]

        for path in common_paths:
            if path.exists() and (path / "joern-cli").exists():
                return path

        return None

    @property
    def llm(self) -> LLMSettings:
        """Get LLM settings."""
        if self._llm is None:
            llm_data = self._raw.get("llm", {})

            self._llm = LLMSettings(
                provider=llm_data.get("provider", "gigachat"),
                model=llm_data.get("model", ""),
                temperature=llm_data.get("temperature", 0.1),
                max_tokens=llm_data.get("max_tokens", 4096),
                timeout=llm_data.get("timeout", 60),
                gigachat_auth_key=os.environ.get("GIGACHAT_AUTH_KEY"),
                openai_api_key=os.environ.get("OPENAI_API_KEY"),
                anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )

        return self._llm

    @property
    def api(self) -> APISettings:
        """Get API settings."""
        if self._api is None:
            api_data = self._raw.get("api", {})
            cors_data = api_data.get("cors", {})

            self._api = APISettings(
                host=api_data.get("host", "0.0.0.0"),
                port=api_data.get("port", 8000),
                debug=api_data.get("debug", False),
                cors_origins=cors_data.get(
                    "allowed_origins", ["http://localhost:3000"]
                ),
                jwt_secret=os.environ.get("JWT_SECRET_KEY"),
                jwt_algorithm=api_data.get("jwt_algorithm", "HS256"),
                jwt_expiry_hours=api_data.get("jwt_expiry_hours", 24),
                database_url=os.environ.get("DATABASE_URL"),
                redis_url=os.environ.get("REDIS_URL"),
            )

        return self._api

    @property
    def retrieval(self) -> RetrievalSettings:
        """Get retrieval settings."""
        if self._retrieval is None:
            ret_data = self._raw.get("retrieval", {})

            self._retrieval = RetrievalSettings(
                embedding_model=ret_data.get("embedding_model", "all-MiniLM-L6-v2"),
                top_k_qa=ret_data.get("top_k_qa", 3),
                top_k_cpgql=ret_data.get("top_k_cpgql", 5),
                chunk_size=ret_data.get("chunk_size", 1000),
                chunk_overlap=ret_data.get("chunk_overlap", 200),
            )

        return self._retrieval

    @property
    def cpg(self) -> CPGSettings:
        """Get CPG domain settings."""
        if self._cpg is None:
            cpg_data = self._raw.get("cpg", {})

            self._cpg = CPGSettings(
                type=cpg_data.get("type", "postgresql"),
                version_target=cpg_data.get("version_target", ""),
                custom_config_path=cpg_data.get("custom_config_path"),
            )

        return self._cpg

    @property
    def timeouts(self) -> TimeoutSettings:
        """Get timeout settings."""
        if self._timeouts is None:
            timeout_data = self._raw.get("timeouts", {})

            self._timeouts = TimeoutSettings(
                http_client=timeout_data.get("http_client", 30),
                db_pool=timeout_data.get("db_pool", 30),
                docker_operation=timeout_data.get("docker_operation", 60),
                docker_build=timeout_data.get("docker_build", 600),
                sast_scan=timeout_data.get("sast_scan", 300),
                joern_query=timeout_data.get("joern_query", 60),
            )

        return self._timeouts

    @property
    def limits(self) -> LimitSettings:
        """Get resource limit settings."""
        if self._limits is None:
            limit_data = self._raw.get("limits", {})

            self._limits = LimitSettings(
                db_pool_size=limit_data.get("db_pool_size", 10),
                db_max_overflow=limit_data.get("db_max_overflow", 20),
                cache_max_size=limit_data.get("cache_max_size", 1000),
                cache_ttl=limit_data.get("cache_ttl", 3600),
                query_result_limit=limit_data.get("query_result_limit", 100),
                session_turns_limit=limit_data.get("session_turns_limit", 10),
            )

        return self._limits


# ============================================================================
# Convenience Functions
# ============================================================================

def get_unified_config(config_path: Optional[Path] = None) -> UnifiedConfig:
    """
    Get the unified configuration instance.

    Args:
        config_path: Path to config.yaml (only used on first call)

    Returns:
        UnifiedConfig singleton instance
    """
    return UnifiedConfig.get_instance(config_path)


def reset_unified_config() -> None:
    """Reset unified configuration (useful for testing)."""
    UnifiedConfig.reset()
