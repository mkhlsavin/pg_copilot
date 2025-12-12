"""
Project Import Router.

REST API endpoints for importing new codebases.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.database.models import User
from src.api.dependencies import get_current_active_user
from src.project_import.models import (
    ImportMode,
    ProjectImportRequest,
    ProjectImportStatus,
    SupportedLanguage,
)
from src.project_import.pipeline import ProjectImportPipeline
from src.project_import.steps import JOERN_FRONTENDS

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job storage (use Redis/DB in production)
_import_jobs: Dict[str, ProjectImportStatus] = {}


# Request/Response Models


class ImportProjectRequestAPI(BaseModel):
    """API request model for project import."""

    repo_url: Optional[str] = Field(None, description="Git repository URL")
    local_path: Optional[str] = Field(None, description="Local path to source code")
    branch: str = Field("main", description="Git branch to clone")
    shallow_clone: bool = Field(True, description="Use shallow clone")
    shallow_depth: int = Field(1, description="Shallow clone depth")
    language: Optional[SupportedLanguage] = Field(
        None, description="Programming language (auto-detect if None)"
    )
    mode: ImportMode = Field(ImportMode.FULL, description="Import mode")
    include_paths: List[str] = Field(
        default_factory=list, description="Paths to include"
    )
    exclude_paths: List[str] = Field(
        default_factory=list, description="Paths to exclude"
    )
    create_domain_plugin: bool = Field(True, description="Create domain plugin")
    domain_name: Optional[str] = Field(None, description="Custom domain name")
    import_docs: bool = Field(True, description="Import documentation")
    import_readme: bool = Field(True, description="Import README files")
    import_comments: bool = Field(True, description="Import code comments")
    joern_memory_gb: int = Field(16, description="Joern memory (GB)")
    batch_size: int = Field(10000, description="DuckDB batch size")


class ImportJobResponse(BaseModel):
    """Response for async import job."""

    job_id: str
    status: str
    message: str


class LanguageInfo(BaseModel):
    """Information about a supported language."""

    id: str
    name: str
    extensions: List[str]
    joern_command: str
    joern_flag: str


class SupportedLanguagesResponse(BaseModel):
    """List of supported languages."""

    languages: List[LanguageInfo]


class ImportStepRequest(BaseModel):
    """Request for running a single step."""

    step_id: str = Field(..., description="Step ID to run")
    context: Dict = Field(default_factory=dict, description="Step context")


# Endpoints


@router.get(
    "/languages",
    response_model=SupportedLanguagesResponse,
    summary="List supported languages",
    description="Get list of supported programming languages for import.",
)
async def list_supported_languages(
    current_user: User = Depends(get_current_active_user),
) -> SupportedLanguagesResponse:
    """Get list of supported programming languages."""
    languages = []
    for lang, frontend in JOERN_FRONTENDS.items():
        languages.append(
            LanguageInfo(
                id=lang.value,
                name=lang.name,
                extensions=frontend.file_extensions,
                joern_command=frontend.command,
                joern_flag=frontend.joern_language_flag,
            )
        )

    return SupportedLanguagesResponse(languages=languages)


@router.post(
    "/start",
    response_model=ImportJobResponse,
    summary="Start project import",
    description="Start asynchronous import of a new codebase.",
)
async def start_import(
    request: ImportProjectRequestAPI,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
) -> ImportJobResponse:
    """
    Start project import as background task.

    Returns job ID for tracking progress via GET /import/status/{job_id}
    or WebSocket connection.
    """
    if not request.repo_url and not request.local_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either repo_url or local_path must be specified",
        )

    job_id = str(uuid.uuid4())

    # Create initial status
    project_name = _extract_project_name(request)
    initial_status = ProjectImportStatus(
        job_id=job_id,
        project_name=project_name,
        status="pending",
        steps=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    _import_jobs[job_id] = initial_status

    # Convert API request to internal request
    import_request = ProjectImportRequest(
        repo_url=request.repo_url,
        local_path=request.local_path,
        branch=request.branch,
        shallow_clone=request.shallow_clone,
        shallow_depth=request.shallow_depth,
        language=request.language,
        mode=request.mode,
        include_paths=request.include_paths,
        exclude_paths=request.exclude_paths,
        create_domain_plugin=request.create_domain_plugin,
        domain_name=request.domain_name,
        import_docs=request.import_docs,
        import_readme=request.import_readme,
        import_comments=request.import_comments,
        joern_memory_gb=request.joern_memory_gb,
        batch_size=request.batch_size,
    )

    # Start background task
    background_tasks.add_task(_run_import_pipeline, job_id, import_request)

    logger.info(f"Started import job {job_id} for {project_name}")

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        message="Import started. Use job_id to track progress.",
    )


@router.get(
    "/status/{job_id}",
    response_model=ProjectImportStatus,
    summary="Get import status",
    description="Get current status of an import job.",
)
async def get_import_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
) -> ProjectImportStatus:
    """Get current status of import job."""
    if job_id not in _import_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return _import_jobs[job_id]


@router.get(
    "/jobs",
    response_model=List[ProjectImportStatus],
    summary="List import jobs",
    description="List all import jobs.",
)
async def list_import_jobs(
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
) -> List[ProjectImportStatus]:
    """List import jobs, optionally filtered by status."""
    jobs = list(_import_jobs.values())

    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]

    # Sort by creation time, newest first
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    return jobs[:limit]


@router.delete(
    "/cancel/{job_id}",
    summary="Cancel import job",
    description="Cancel a running import job.",
)
async def cancel_import(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Cancel running import job."""
    if job_id not in _import_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job = _import_jobs[job_id]
    if job.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed job",
        )

    job.status = "cancelled"
    job.updated_at = datetime.utcnow()

    logger.info(f"Cancelled import job {job_id}")

    return {"job_id": job_id, "status": "cancelled"}


@router.post(
    "/step",
    summary="Run single import step",
    description="Run a single step of the import pipeline.",
)
async def run_single_step(
    request: ImportStepRequest,
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """
    Run a single step of the import pipeline.

    Valid steps: clone, detect_language, joern_import, cpg_export,
                 validate, chromadb_import, domain_setup
    """
    valid_steps = [
        "clone",
        "detect_language",
        "joern_import",
        "cpg_export",
        "validate",
        "chromadb_import",
        "domain_setup",
    ]

    if request.step_id not in valid_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step: {request.step_id}. Valid steps: {valid_steps}",
        )

    pipeline = ProjectImportPipeline()

    try:
        result = await pipeline.run_step(request.step_id, request.context)
        return {"step": request.step_id, "status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Step {request.step_id} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Helper Functions


async def _run_import_pipeline(job_id: str, request: ProjectImportRequest) -> None:
    """Background task to run import pipeline."""

    def progress_callback(status: ProjectImportStatus) -> None:
        _import_jobs[job_id] = status
        # Could also broadcast via WebSocket here
        try:
            from src.api.websocket.manager import get_ws_manager
            from src.api.websocket.models import create_job_progress

            ws_manager = get_ws_manager()
            asyncio.create_task(
                ws_manager.broadcast_to_job(
                    job_id,
                    create_job_progress(
                        job_id, status.overall_progress, status.current_step
                    ),
                )
            )
        except Exception:
            pass  # WebSocket not available

    pipeline = ProjectImportPipeline(progress_callback=progress_callback)

    try:
        result = await pipeline.run(request)
        _import_jobs[job_id].status = "completed"
        _import_jobs[job_id].result = result.model_dump()
        _import_jobs[job_id].updated_at = datetime.utcnow()

        logger.info(f"Import job {job_id} completed successfully")

        # Broadcast completion
        try:
            from src.api.websocket.manager import get_ws_manager
            from src.api.websocket.models import create_job_completed

            ws_manager = get_ws_manager()
            asyncio.create_task(
                ws_manager.broadcast_to_job(
                    job_id, create_job_completed(job_id, result.model_dump())
                )
            )
        except Exception:
            pass

    except Exception as e:
        _import_jobs[job_id].status = "failed"
        _import_jobs[job_id].error = str(e)
        _import_jobs[job_id].updated_at = datetime.utcnow()

        logger.error(f"Import job {job_id} failed: {e}", exc_info=True)

        # Broadcast failure
        try:
            from src.api.websocket.manager import get_ws_manager
            from src.api.websocket.models import create_job_failed

            ws_manager = get_ws_manager()
            asyncio.create_task(
                ws_manager.broadcast_to_job(job_id, create_job_failed(job_id, str(e)))
            )
        except Exception:
            pass


def _extract_project_name(request: ImportProjectRequestAPI) -> str:
    """Extract project name from request."""
    if request.repo_url:
        name = request.repo_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name
    if request.local_path:
        from pathlib import Path

        return Path(request.local_path).name
    return "unknown"
