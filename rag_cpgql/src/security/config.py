"""
Enterprise Security Configuration Models.

Provides Pydantic models for configuring:
- LLM request/response logging
- SIEM integration (SysLog, CEF, LEEF)
- DLP (Data Loss Prevention) with patterns and actions
- HashiCorp Vault integration
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import os
import yaml
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class DLPAction(str, Enum):
    """Actions to take when DLP pattern matches."""
    BLOCK = "BLOCK"        # Block the request entirely
    MASK = "MASK"          # Replace sensitive data with placeholder
    WARN = "WARN"          # Allow but log warning
    LOG_ONLY = "LOG_ONLY"  # Only log, no action


class SIEMProtocol(str, Enum):
    """Protocol for SIEM communication."""
    UDP = "udp"
    TCP = "tcp"
    TLS = "tls"


class SIEMSeverity(int, Enum):
    """Syslog severity levels (RFC 5424)."""
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7


class VaultAuthMethod(str, Enum):
    """Vault authentication methods."""
    TOKEN = "token"
    APPROLE = "approle"
    KUBERNETES = "kubernetes"


class SIEMFacility(int, Enum):
    """Syslog facility codes (RFC 5424)."""
    KERN = 0
    USER = 1
    MAIL = 2
    DAEMON = 3
    AUTH = 4
    SYSLOG = 5
    LPR = 6
    NEWS = 7
    UUCP = 8
    CRON = 9
    AUTHPRIV = 10
    FTP = 11
    LOCAL0 = 16
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


# =============================================================================
# SIEM Configuration
# =============================================================================

class TLSConfig(BaseModel):
    """TLS configuration for secure SIEM connections."""
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    verify: bool = True


class SysLogConfig(BaseModel):
    """SysLog RFC 5424 handler configuration."""
    enabled: bool = True
    protocol: SIEMProtocol = SIEMProtocol.UDP
    host: str = "localhost"
    port: int = 514
    facility: int = SIEMFacility.LOCAL0.value
    app_name: str = "codegraph"
    hostname: Optional[str] = None  # Auto-detected if None
    tls: Optional[TLSConfig] = None

    class Config:
        use_enum_values = True


class CEFConfig(BaseModel):
    """Common Event Format (ArcSight) configuration."""
    enabled: bool = False
    host: str = ""
    port: int = 514
    protocol: SIEMProtocol = SIEMProtocol.UDP
    device_vendor: str = "CodeGraph"
    device_product: str = "CodeAnalysis"
    device_version: str = "1.0"

    class Config:
        use_enum_values = True


class LEEFConfig(BaseModel):
    """Log Event Extended Format (QRadar) configuration."""
    enabled: bool = False
    host: str = ""
    port: int = 514
    protocol: SIEMProtocol = SIEMProtocol.UDP
    product_vendor: str = "CodeGraph"
    product_name: str = "CodeAnalysis"
    product_version: str = "1.0"

    class Config:
        use_enum_values = True


class SIEMBufferConfig(BaseModel):
    """Buffer configuration for reliable delivery."""
    max_size: int = 10000
    flush_interval_seconds: int = 5
    retry_attempts: int = 3
    retry_backoff_seconds: float = 2.0


class SIEMConfig(BaseModel):
    """Complete SIEM integration configuration."""
    enabled: bool = True
    syslog: SysLogConfig = Field(default_factory=SysLogConfig)
    cef: CEFConfig = Field(default_factory=CEFConfig)
    leef: LEEFConfig = Field(default_factory=LEEFConfig)
    buffer: SIEMBufferConfig = Field(default_factory=SIEMBufferConfig)


# =============================================================================
# DLP Configuration
# =============================================================================

class DLPPatternConfig(BaseModel):
    """Single DLP pattern definition."""
    name: str
    regex: str
    mask_with: str = "[REDACTED]"
    description: Optional[str] = None


class DLPCategoryConfig(BaseModel):
    """DLP category with patterns and action."""
    enabled: bool = True
    action: DLPAction = DLPAction.WARN
    patterns: List[DLPPatternConfig] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class DLPKeywordListConfig(BaseModel):
    """Keyword list for DLP scanning."""
    words: List[str] = Field(default_factory=list)
    case_sensitive: bool = False


class DLPWebhookConfig(BaseModel):
    """External DLP webhook configuration."""
    enabled: bool = False
    endpoint: Optional[str] = None
    auth_header: Optional[str] = None
    timeout_seconds: int = 10
    retry_attempts: int = 3
    notify_on: List[DLPAction] = Field(default_factory=lambda: [DLPAction.BLOCK, DLPAction.WARN])

    class Config:
        use_enum_values = True


class DLPPreRequestConfig(BaseModel):
    """Pre-request filtering configuration."""
    enabled: bool = True
    default_action: DLPAction = DLPAction.WARN

    class Config:
        use_enum_values = True


class DLPPostResponseConfig(BaseModel):
    """Post-response filtering configuration."""
    enabled: bool = True
    default_action: DLPAction = DLPAction.MASK

    class Config:
        use_enum_values = True


class DLPConfig(BaseModel):
    """Complete DLP configuration."""
    enabled: bool = True
    pre_request: DLPPreRequestConfig = Field(default_factory=DLPPreRequestConfig)
    post_response: DLPPostResponseConfig = Field(default_factory=DLPPostResponseConfig)
    categories: Dict[str, DLPCategoryConfig] = Field(default_factory=dict)
    keywords: Dict[str, DLPKeywordListConfig] = Field(default_factory=dict)
    keywords_action: DLPAction = DLPAction.LOG_ONLY
    webhook: DLPWebhookConfig = Field(default_factory=DLPWebhookConfig)

    class Config:
        use_enum_values = True


# =============================================================================
# Vault Configuration
# =============================================================================

class VaultTokenAuthConfig(BaseModel):
    """Token-based Vault authentication."""
    value: Optional[str] = None


class VaultAppRoleAuthConfig(BaseModel):
    """AppRole Vault authentication."""
    role_id: Optional[str] = None
    secret_id: Optional[str] = None


class VaultKubernetesAuthConfig(BaseModel):
    """Kubernetes Vault authentication."""
    role: Optional[str] = None
    jwt_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"


class VaultSecretPathConfig(BaseModel):
    """Secret path configuration."""
    path: str
    keys: Dict[str, str] = Field(default_factory=dict)


class VaultConfig(BaseModel):
    """HashiCorp Vault configuration."""
    enabled: bool = False
    url: str = "http://localhost:8200"
    auth_method: str = "token"  # token, approle, kubernetes
    namespace: Optional[str] = None
    token: VaultTokenAuthConfig = Field(default_factory=VaultTokenAuthConfig)
    approle: VaultAppRoleAuthConfig = Field(default_factory=VaultAppRoleAuthConfig)
    kubernetes: VaultKubernetesAuthConfig = Field(default_factory=VaultKubernetesAuthConfig)
    secrets: Dict[str, VaultSecretPathConfig] = Field(default_factory=dict)
    secrets_mount_point: str = "secret"
    llm_secrets_path: str = "codegraph/llm"
    cache_ttl_seconds: int = 300
    timeout_seconds: int = 30
    tls_verify: bool = True
    rotation_enabled: bool = False
    rotation_check_interval: int = 300
    audit_access: bool = True


# =============================================================================
# LLM Logging Configuration
# =============================================================================

class LLMLoggingConfig(BaseModel):
    """LLM request/response logging configuration."""
    enabled: bool = True
    log_prompts: bool = True
    redact_prompts: bool = True
    max_prompt_length: int = 2000
    log_responses: bool = True
    max_response_length: int = 5000
    log_token_usage: bool = True
    log_latency: bool = True
    log_to_database: bool = True
    log_to_siem: bool = True


# =============================================================================
# Main Security Configuration
# =============================================================================

class SecurityConfig(BaseModel):
    """
    Main Enterprise Security Configuration.

    Controls all security features for LLM interactions:
    - Request/response logging
    - SIEM integration
    - DLP filtering
    - Vault secrets management
    """
    enabled: bool = False  # Disabled by default
    llm_logging: LLMLoggingConfig = Field(default_factory=LLMLoggingConfig)
    siem: SIEMConfig = Field(default_factory=SIEMConfig)
    dlp: DLPConfig = Field(default_factory=DLPConfig)
    vault: VaultConfig = Field(default_factory=VaultConfig)


# =============================================================================
# Configuration Loading
# =============================================================================

_security_config: Optional[SecurityConfig] = None


def _resolve_env_vars(obj: Any) -> Any:
    """Recursively resolve environment variables in config values."""
    if isinstance(obj, str):
        # Handle ${VAR:-default} syntax
        if obj.startswith("${") and "}" in obj:
            var_part = obj[2:obj.index("}")]
            if ":-" in var_part:
                var_name, default = var_part.split(":-", 1)
            else:
                var_name, default = var_part, ""
            return os.environ.get(var_name, default)
        # Handle simple $VAR syntax
        elif obj.startswith("$") and not obj.startswith("${"):
            var_name = obj[1:]
            return os.environ.get(var_name, "")
        return obj
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


def load_security_config(config_path: Optional[str] = None) -> SecurityConfig:
    """
    Load security configuration from config.yaml.

    Args:
        config_path: Path to config.yaml (auto-detected if None)

    Returns:
        SecurityConfig instance
    """
    global _security_config

    if config_path is None:
        # Auto-detect config.yaml location
        possible_paths = [
            os.path.join(os.getcwd(), "config.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f)

            security_section = full_config.get("security", {})
            security_section = _resolve_env_vars(security_section)

            _security_config = SecurityConfig(**security_section)
            logger.info(f"Loaded security config from {config_path}")

        except Exception as e:
            logger.warning(f"Failed to load security config: {e}, using defaults")
            _security_config = SecurityConfig()
    else:
        logger.info("No config.yaml found, using default security config")
        _security_config = SecurityConfig()

    return _security_config


def get_security_config() -> SecurityConfig:
    """
    Get the current security configuration (singleton).

    Returns:
        SecurityConfig instance
    """
    global _security_config

    if _security_config is None:
        _security_config = load_security_config()

    return _security_config


def reload_security_config(config_path: Optional[str] = None) -> SecurityConfig:
    """
    Force reload of security configuration.

    Args:
        config_path: Path to config.yaml

    Returns:
        New SecurityConfig instance
    """
    global _security_config
    _security_config = None
    return load_security_config(config_path)


# =============================================================================
# Default DLP Patterns
# =============================================================================

def get_default_dlp_categories() -> Dict[str, DLPCategoryConfig]:
    """
    Get default DLP categories with common patterns.

    Returns:
        Dictionary of category name to DLPCategoryConfig
    """
    return {
        "credentials": DLPCategoryConfig(
            enabled=True,
            action=DLPAction.BLOCK,
            patterns=[
                DLPPatternConfig(
                    name="api_key_generic",
                    regex=r'(?i)(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?',
                    description="Generic API key pattern"
                ),
                DLPPatternConfig(
                    name="aws_access_key",
                    regex=r'AKIA[0-9A-Z]{16}',
                    description="AWS Access Key ID"
                ),
                DLPPatternConfig(
                    name="aws_secret_key",
                    regex=r'(?i)aws[_\s]*secret[_\s]*access[_\s]*key["\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?',
                    description="AWS Secret Access Key"
                ),
                DLPPatternConfig(
                    name="private_key",
                    regex=r'-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
                    description="Private key header"
                ),
                DLPPatternConfig(
                    name="password_pattern",
                    regex=r'(?i)(password|passwd|pwd)["\s:=]+["\']?([^\s"\']{8,})["\']?',
                    mask_with="[PASSWORD]",
                    description="Password in config/code"
                ),
                DLPPatternConfig(
                    name="bearer_token",
                    regex=r'(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+',
                    mask_with="[TOKEN]",
                    description="JWT Bearer token"
                ),
                DLPPatternConfig(
                    name="github_token",
                    regex=r'gh[pousr]_[A-Za-z0-9_]{36,}',
                    description="GitHub personal access token"
                ),
            ]
        ),
        "pii": DLPCategoryConfig(
            enabled=True,
            action=DLPAction.MASK,
            patterns=[
                DLPPatternConfig(
                    name="email",
                    regex=r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                    mask_with="[EMAIL]",
                    description="Email address"
                ),
                DLPPatternConfig(
                    name="phone_ru",
                    regex=r'(\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
                    mask_with="[PHONE]",
                    description="Russian phone number"
                ),
                DLPPatternConfig(
                    name="phone_us",
                    regex=r'(\+1)?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
                    mask_with="[PHONE]",
                    description="US phone number"
                ),
                DLPPatternConfig(
                    name="ssn",
                    regex=r'\b\d{3}-\d{2}-\d{4}\b',
                    mask_with="[SSN]",
                    description="US Social Security Number"
                ),
                DLPPatternConfig(
                    name="credit_card",
                    regex=r'\b(?:\d{4}[\s-]?){3}\d{4}\b',
                    mask_with="[CARD]",
                    description="Credit card number"
                ),
                DLPPatternConfig(
                    name="ip_address",
                    regex=r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                    mask_with="[IP]",
                    description="IPv4 address"
                ),
                DLPPatternConfig(
                    name="passport_ru",
                    regex=r'\b\d{2}\s?\d{2}\s?\d{6}\b',
                    mask_with="[PASSPORT]",
                    description="Russian passport number"
                ),
            ]
        ),
        "source_code": DLPCategoryConfig(
            enabled=True,
            action=DLPAction.WARN,
            patterns=[
                DLPPatternConfig(
                    name="connection_string",
                    regex=r'(?i)(jdbc|mysql|postgresql|mongodb|redis)://[^\s"\'<>]+',
                    mask_with="[CONN_STRING]",
                    description="Database connection string"
                ),
                DLPPatternConfig(
                    name="internal_path_unix",
                    regex=r'(/home/|/var/|/etc/|/opt/)[^\s"\'<>|]+',
                    mask_with="[PATH]",
                    description="Unix internal path"
                ),
                DLPPatternConfig(
                    name="internal_path_windows",
                    regex=r'[A-Z]:\\(Users|Windows|Program)[^\s"\'<>|]*',
                    mask_with="[PATH]",
                    description="Windows internal path"
                ),
            ]
        ),
    }
