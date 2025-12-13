"""
Project Import Module.

Provides functionality for importing new codebases into RAG-CPGQL system.
Supports multiple programming languages via Joern frontends.
"""

from .config import (
    JoernConfig,
    ProjectImportConfig,
    get_config,
    load_config,
)
from .frontends import (
    FRONTENDS,
    JoernFrontend as JoernFrontendConfig,
    detect_language,
    detect_language_with_stats,
    get_exclude_patterns,
    get_frontend,
    list_supported_languages,
)
from .models import (
    ImportMode,
    ImportStep,
    ImportStepStatus,
    JoernFrontend,
    ProjectImportRequest,
    ProjectImportResult,
    ProjectImportStatus,
    SupportedLanguage,
)
from .pipeline import (
    ProjectImportPipeline,
    import_project,
    import_project_simple,
)
from .registry import ProjectRegistry
from .server import (
    DockerJoernRunner,
    JoernServerManager,
    LocalJoernRunner,
)

__all__ = [
    # Models
    "SupportedLanguage",
    "JoernFrontend",
    "ImportMode",
    "ImportStepStatus",
    "ImportStep",
    "ProjectImportRequest",
    "ProjectImportStatus",
    "ProjectImportResult",
    # Configuration
    "JoernConfig",
    "ProjectImportConfig",
    "get_config",
    "load_config",
    # Pipeline
    "ProjectImportPipeline",
    "import_project",
    "import_project_simple",
    # Registry
    "ProjectRegistry",
    # Server Management
    "JoernServerManager",
    "LocalJoernRunner",
    "DockerJoernRunner",
    # Frontends
    "FRONTENDS",
    "JoernFrontendConfig",
    "get_frontend",
    "detect_language",
    "detect_language_with_stats",
    "list_supported_languages",
    "get_exclude_patterns",
]
