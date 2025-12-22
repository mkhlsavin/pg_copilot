"""
Configuration Validator

Validates configuration and required environment variables at startup.
Provides early detection of configuration issues before runtime errors.

Author: CodeGraph Project
Date: December 2025
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def __bool__(self) -> bool:
        """Return True if configuration is valid."""
        return self.valid


# Provider-specific environment variable requirements
PROVIDER_ENV_REQUIREMENTS = {
    "gigachat": {
        "required": [
            ("GIGACHAT_AUTH_KEY", "GigaChat API authentication key (base64)"),
        ],
        "optional": [
            ("GIGACHAT_CREDENTIALS", "Alternative name for GIGACHAT_AUTH_KEY"),
        ],
    },
    "openai": {
        "required": [
            ("OPENAI_API_KEY", "OpenAI API key"),
        ],
        "optional": [
            ("OPENAI_BASE_URL", "Custom OpenAI API endpoint"),
        ],
    },
    "local": {
        "required": [],
        "optional": [
            ("LLMXCPG_MODEL_PATH", "Path to fine-tuned LLMxCPG-Q model (.gguf)"),
            ("QWEN3_MODEL_PATH", "Path to base Qwen3-Coder model (.gguf)"),
        ],
    },
}


class ConfigValidator:
    """
    Configuration validator for CodeGraph.

    Validates:
    - LLM provider configuration
    - Required environment variables
    - File paths and dependencies
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config validator.

        Args:
            config_path: Path to config.yaml (auto-detected if None)
        """
        if config_path is None:
            # Try to find config.yaml
            project_root = Path(__file__).parents[2]
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}

    def load_config(self) -> bool:
        """
        Load configuration file.

        Returns:
            True if config loaded successfully
        """
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            return True
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False

    def validate(self) -> ValidationResult:
        """
        Validate configuration and environment.

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True)

        # Load config
        if not self.load_config():
            result.add_error(f"Cannot load config file: {self.config_path}")
            return result

        # Validate LLM provider
        self._validate_llm_provider(result)

        # Validate RAGAS provider if separate
        self._validate_ragas_provider(result)

        # Validate paths
        self._validate_paths(result)

        return result

    def _validate_llm_provider(self, result: ValidationResult):
        """Validate LLM provider configuration."""
        llm_config = self._config.get("llm", {})
        provider = llm_config.get("provider", "local")

        result.info["llm_provider"] = provider

        if provider not in PROVIDER_ENV_REQUIREMENTS:
            result.add_warning(
                f"Unknown LLM provider: '{provider}'. "
                f"Supported: {list(PROVIDER_ENV_REQUIREMENTS.keys())}"
            )
            return

        requirements = PROVIDER_ENV_REQUIREMENTS[provider]

        # Check required environment variables
        for env_var, description in requirements.get("required", []):
            value = os.environ.get(env_var)

            # Check alternative names (e.g., GIGACHAT_CREDENTIALS for GIGACHAT_AUTH_KEY)
            if not value and provider == "gigachat":
                value = os.environ.get("GIGACHAT_CREDENTIALS")

            # Also check config file value (might have ${VAR} syntax)
            if not value:
                provider_config = llm_config.get(provider, {})
                config_value = provider_config.get("credentials")
                # Check if value is a placeholder like ${GIGACHAT_AUTH_KEY}
                if config_value and not config_value.startswith("${"):
                    value = config_value

            if not value:
                result.add_error(
                    f"Missing required environment variable: {env_var}\n"
                    f"  Description: {description}\n"
                    f"  Provider: {provider}\n"
                    f"  Solution: Set {env_var} in .env file or environment"
                )

        # Check optional environment variables
        for env_var, description in requirements.get("optional", []):
            value = os.environ.get(env_var)
            if not value:
                result.add_warning(
                    f"Optional environment variable not set: {env_var} ({description})"
                )

    def _validate_ragas_provider(self, result: ValidationResult):
        """Validate RAGAS evaluation provider configuration."""
        ragas_config = self._config.get("ragas", {})

        if not ragas_config.get("use_separate_llm", False):
            return  # Using main LLM provider

        provider = ragas_config.get("provider")
        if not provider:
            return  # Will use main LLM provider

        result.info["ragas_provider"] = provider

        if provider not in PROVIDER_ENV_REQUIREMENTS:
            result.add_warning(f"Unknown RAGAS provider: '{provider}'")
            return

        # RAGAS uses GIGACHAT_CREDENTIALS instead of GIGACHAT_AUTH_KEY
        if provider == "gigachat":
            value = os.environ.get("GIGACHAT_CREDENTIALS") or os.environ.get("GIGACHAT_AUTH_KEY")
            if not value:
                result.add_error(
                    "Missing environment variable for RAGAS GigaChat: "
                    "GIGACHAT_CREDENTIALS or GIGACHAT_AUTH_KEY"
                )

    def _validate_paths(self, result: ValidationResult):
        """Validate file paths in configuration."""
        joern_config = self._config.get("joern", {})

        # Check CPG path
        cpg_path = joern_config.get("cpg_path")
        if cpg_path:
            cpg_file = Path(cpg_path)
            if not cpg_file.exists():
                result.add_warning(f"CPG file not found: {cpg_path}")
            else:
                result.info["cpg_path"] = str(cpg_file)

        # Check Joern installation
        joern_path = joern_config.get("installation_path")
        if joern_path:
            joern_dir = Path(joern_path)
            if not joern_dir.exists():
                result.add_warning(f"Joern installation not found: {joern_path}")

    def get_provider_info(self) -> Tuple[str, Dict[str, Any]]:
        """
        Get current LLM provider and its configuration.

        Returns:
            Tuple of (provider_name, provider_config)
        """
        if not self._config:
            self.load_config()

        llm_config = self._config.get("llm", {})
        provider = llm_config.get("provider", "local")
        provider_config = llm_config.get(provider, {})

        return provider, provider_config


def validate_config(config_path: Optional[Path] = None) -> ValidationResult:
    """
    Validate configuration (convenience function).

    Args:
        config_path: Path to config.yaml

    Returns:
        ValidationResult
    """
    validator = ConfigValidator(config_path)
    return validator.validate()


def check_gigachat_credentials() -> Tuple[bool, str]:
    """
    Quick check for GigaChat credentials.

    Returns:
        Tuple of (is_valid, message)
    """
    creds = os.environ.get("GIGACHAT_AUTH_KEY") or os.environ.get("GIGACHAT_CREDENTIALS")

    if not creds:
        return False, (
            "GigaChat credentials not found.\n"
            "Set GIGACHAT_AUTH_KEY environment variable:\n"
            "  Windows: set GIGACHAT_AUTH_KEY=your_base64_key\n"
            "  Linux/Mac: export GIGACHAT_AUTH_KEY=your_base64_key\n"
            "  Or add to .env file: GIGACHAT_AUTH_KEY=your_base64_key"
        )

    # Basic validation of base64 format
    import base64
    try:
        decoded = base64.b64decode(creds)
        if b":" not in decoded:
            return False, (
                "GigaChat credentials appear invalid.\n"
                "Expected format: base64(client_id:client_secret)"
            )
    except Exception as e:
        # Might be a different format, let GigaChat API validate
        logger.debug(f"GigaChat credentials base64 decode failed (may be valid format): {e}")

    return True, "GigaChat credentials found"


def check_openai_credentials() -> Tuple[bool, str]:
    """
    Quick check for OpenAI credentials.

    Returns:
        Tuple of (is_valid, message)
    """
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return False, (
            "OpenAI API key not found.\n"
            "Set OPENAI_API_KEY environment variable:\n"
            "  Windows: set OPENAI_API_KEY=sk-...\n"
            "  Linux/Mac: export OPENAI_API_KEY=sk-...\n"
            "  Or add to .env file: OPENAI_API_KEY=sk-..."
        )

    if not api_key.startswith("sk-"):
        return False, (
            "OpenAI API key appears invalid.\n"
            "Expected format: sk-..."
        )

    return True, "OpenAI API key found"
