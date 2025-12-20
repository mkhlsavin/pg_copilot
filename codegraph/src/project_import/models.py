"""
Project Import Models.

Pydantic models for project import functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SupportedLanguage(str, Enum):
    """Supported programming languages for Joern analysis."""

    C = "c"
    CSHARP = "csharp"
    GO = "go"
    JAVA = "java"
    JAVA_BYTECODE = "java_bytecode"  # Java bytecode via Jimple IR
    JAVASCRIPT = "javascript"
    KOTLIN = "kotlin"
    PHP = "php"
    PYTHON = "python"
    RUBY = "ruby"
    SWIFT = "swift"
    GHIDRA = "ghidra"  # Binary analysis


class JoernFrontend(BaseModel):
    """Configuration for a Joern language frontend."""

    language: SupportedLanguage
    command: str  # e.g., "c2cpg", "javasrc2cpg"
    joern_language_flag: str  # e.g., "C", "JAVASRC"
    file_extensions: List[str]
    exclude_patterns: List[str] = Field(default_factory=list)


class ImportMode(str, Enum):
    """Import mode for project."""

    FULL = "full"  # Import entire codebase
    SELECTIVE = "selective"  # Import only specified paths
    INCREMENTAL = "incremental"  # Import only changes since last import


class ImportStepStatus(str, Enum):
    """Status of an import step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ImportStep(BaseModel):
    """Information about an import step."""

    name: str
    status: ImportStepStatus = ImportStepStatus.PENDING
    progress: int = Field(ge=0, le=100, default=0)
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ProjectImportRequest(BaseModel):
    """Request to import a project."""

    # Source
    repo_url: Optional[str] = Field(None, description="Git repository URL")
    local_path: Optional[str] = Field(None, description="Local path to source code")

    # Clone settings
    branch: str = Field("main", description="Git branch to clone")
    shallow_clone: bool = Field(True, description="Use shallow clone for large repos")
    shallow_depth: int = Field(1, description="Depth for shallow clone")

    # Language
    language: Optional[SupportedLanguage] = Field(
        None, description="Programming language (auto-detect if None)"
    )

    # Import mode
    mode: ImportMode = Field(ImportMode.FULL, description="Import mode")
    include_paths: List[str] = Field(
        default_factory=list, description="Paths to include (for selective mode)"
    )
    exclude_paths: List[str] = Field(
        default_factory=list, description="Paths to exclude"
    )

    # CPG settings
    cpg_name: Optional[str] = Field(None, description="Name for CPG file")
    workspace_path: Optional[str] = Field(None, description="Joern workspace path")
    joern_home: Optional[str] = Field(None, description="Joern installation path")

    # Domain Plugin
    create_domain_plugin: bool = Field(True, description="Create domain plugin")
    domain_name: Optional[str] = Field(
        None, description="Domain name (auto-generate if None)"
    )

    # ChromaDB
    import_docs: bool = Field(True, description="Import documentation to ChromaDB")
    import_readme: bool = Field(True, description="Import README files")
    import_comments: bool = Field(True, description="Import code comments from CPG")

    # Joern settings
    joern_memory_gb: int = Field(16, description="Memory for Joern (GB)")
    batch_size: int = Field(10000, description="Batch size for DuckDB export")

    # Incremental settings
    previous_commit: Optional[str] = Field(
        None, description="Previous commit hash for incremental import"
    )


class ProjectImportStatus(BaseModel):
    """Status of a project import job."""

    job_id: str
    project_name: str
    status: str  # "pending", "in_progress", "completed", "failed", "cancelled"
    steps: List[ImportStep]
    current_step: Optional[str] = None
    overall_progress: int = Field(ge=0, le=100, default=0)
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProjectImportResult(BaseModel):
    """Result of a successful project import."""

    cpg_path: str
    duckdb_path: str
    domain_plugin_path: Optional[str] = None
    chromadb_collection: Optional[str] = None
    chromadb_stats: Dict[str, int] = Field(default_factory=dict)
    cpg_stats: Dict[str, int] = Field(default_factory=dict)
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    detected_language: SupportedLanguage
    import_duration_seconds: float
    source_info: Dict[str, Any] = Field(default_factory=dict)


class CloneResult(BaseModel):
    """Result of clone step."""

    source_path: str
    clone_info: Dict[str, Any] = Field(default_factory=dict)


class DetectLanguageResult(BaseModel):
    """Result of language detection step."""

    detected_language: SupportedLanguage
    joern_frontend: JoernFrontend
    detection_method: str  # "explicit" or "auto"
    file_stats: Dict[str, int] = Field(default_factory=dict)


class JoernImportResult(BaseModel):
    """Result of Joern import step."""

    cpg_path: str
    joern_home: str
    import_stats: Dict[str, Any] = Field(default_factory=dict)


class CpgExportResult(BaseModel):
    """Result of CPG export step."""

    duckdb_path: str
    cpg_stats: Dict[str, int] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of validation step."""

    status: str  # "passed" or "failed"
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    quality_score: int = Field(ge=0, le=100)


class ChromaDBImportResult(BaseModel):
    """Result of ChromaDB import step."""

    chromadb_collection: str
    stats: Dict[str, int] = Field(default_factory=dict)


class DomainSetupResult(BaseModel):
    """Result of domain setup step."""

    domain_plugin_path: str
    domain_name: str
    domain_config: Dict[str, Any] = Field(default_factory=dict)
