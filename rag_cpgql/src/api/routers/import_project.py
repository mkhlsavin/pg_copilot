"""
Project Import Router.

REST API endpoints for importing new codebases.
Integrates with PostgreSQL for job tracking and supports Docker execution.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID as PyUUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.database.repositories.group_repo import ProjectGroupRepository
from src.api.dependencies import get_current_active_user
from src.project_import import (
    FRONTENDS,
    ImportMode,
    JoernServerManager,
    ProjectImportPipeline,
    ProjectImportRequest,
    ProjectImportStatus,
    ProjectRegistry,
    SupportedLanguage,
    get_config,
    list_supported_languages,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job storage for fast lookups (backed by PostgreSQL)
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
    use_docker: bool = Field(False, description="Use Docker for Joern")
    group_id: Optional[str] = Field(None, description="Target project group ID")


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
    description: str
    supports_joern_parse: bool


class SupportedLanguagesResponse(BaseModel):
    """List of supported languages."""

    languages: List[LanguageInfo]


class ImportStepRequest(BaseModel):
    """Request for running a single step."""

    step_id: str = Field(..., description="Step ID to run")
    context: Dict = Field(default_factory=dict, description="Step context")


class ServerStatusResponse(BaseModel):
    """Joern server status response."""

    running: bool
    mode: str
    endpoint: str
    docker_image: Optional[str]


# Endpoints


@router.get(
    "/languages",
    response_model=SupportedLanguagesResponse,
    summary="List supported languages",
    description="Get list of supported programming languages for import.",
)
async def get_supported_languages(
    current_user: User = Depends(get_current_active_user),
) -> SupportedLanguagesResponse:
    """Get list of supported programming languages."""
    languages_info = list_supported_languages()

    return SupportedLanguagesResponse(
        languages=[
            LanguageInfo(
                id=lang["language"],
                name=lang["language"].title(),
                extensions=lang["extensions"],
                joern_command=lang["command"],
                description=lang["description"],
                supports_joern_parse=lang["supports_joern_parse"],
            )
            for lang in languages_info
        ]
    )


@router.get(
    "/server/status",
    response_model=ServerStatusResponse,
    summary="Get Joern server status",
    description="Check if Joern server is running.",
)
async def get_server_status(
    current_user: User = Depends(get_current_active_user),
) -> ServerStatusResponse:
    """Get Joern server status."""
    config = get_config()
    manager = JoernServerManager(config)

    return ServerStatusResponse(
        running=manager.is_running(),
        mode="docker" if config.joern.use_docker else "local",
        endpoint=f"{config.joern.server_host}:{config.joern.server_port}",
        docker_image=config.joern.docker_image if config.joern.use_docker else None,
    )


@router.post(
    "/server/start",
    summary="Start Joern server",
    description="Start the Joern server.",
)
async def start_server(
    use_docker: bool = False,
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Start Joern server."""
    config = get_config()
    if use_docker:
        config.joern.use_docker = True

    manager = JoernServerManager(config)

    if manager.is_running():
        return {"status": "already_running", "message": "Server is already running"}

    success = manager.start()
    if success:
        return {"status": "started", "message": "Server started successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Joern server",
        )


@router.post(
    "/server/stop",
    summary="Stop Joern server",
    description="Stop the Joern server.",
)
async def stop_server(
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Stop Joern server."""
    config = get_config()
    manager = JoernServerManager(config)

    if not manager.is_running():
        return {"status": "not_running", "message": "Server is not running"}

    success = manager.stop()
    if success:
        return {"status": "stopped", "message": "Server stopped successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop Joern server",
        )


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
    db: AsyncSession = Depends(get_db),
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

    # Resolve group ID
    group_id = None
    if request.group_id:
        try:
            group_id = PyUUID(request.group_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid group_id format",
            )
    else:
        # Get or create default group
        registry = ProjectRegistry(db)
        group = await registry.get_or_create_default_group()
        group_id = group.id

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
    background_tasks.add_task(
        _run_import_pipeline,
        job_id,
        import_request,
        current_user.id,
        group_id,
        request.use_docker,
    )

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
    db: AsyncSession = Depends(get_db),
) -> ProjectImportStatus:
    """Get current status of import job."""
    # Check in-memory first
    if job_id in _import_jobs:
        return _import_jobs[job_id]

    # Check PostgreSQL
    try:
        registry = ProjectRegistry(db)
        job = await registry.get_import_job(PyUUID(job_id))
        if job:
            return ProjectImportStatus(
                job_id=str(job.id),
                project_name=job.project_name,
                status=job.status.value,
                steps=[],
                overall_progress=job.progress,
                current_step=job.current_step,
                created_at=job.created_at,
                updated_at=job.updated_at,
                error=job.error_message,
                result=job.result,
            )
    except Exception as e:
        logger.warning(f"Error fetching job from PostgreSQL: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job {job_id} not found",
    )


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
    db: AsyncSession = Depends(get_db),
) -> List[ProjectImportStatus]:
    """List import jobs, optionally filtered by status."""
    # Combine in-memory and PostgreSQL jobs
    jobs = []

    # In-memory jobs
    for job_status in _import_jobs.values():
        if status_filter and job_status.status != status_filter:
            continue
        jobs.append(job_status)

    # PostgreSQL jobs (for historical data)
    try:
        registry = ProjectRegistry(db)
        db_jobs = await registry.list_import_jobs(
            user_id=current_user.id,
            status=status_filter,
            limit=limit,
        )
        for job in db_jobs:
            if job.id not in [PyUUID(j.job_id) for j in jobs]:
                jobs.append(
                    ProjectImportStatus(
                        job_id=str(job.id),
                        project_name=job.project_name,
                        status=job.status.value,
                        steps=[],
                        overall_progress=job.progress,
                        current_step=job.current_step,
                        created_at=job.created_at,
                        updated_at=job.updated_at,
                        error=job.error_message,
                        result=job.result,
                    )
                )
    except Exception as e:
        logger.warning(f"Error fetching jobs from PostgreSQL: {e}")

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
    use_docker: bool = False,
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

    config = get_config()
    if use_docker:
        config.joern.use_docker = True

    pipeline = ProjectImportPipeline(config=config)

    try:
        result = await pipeline.run_step(request.step_id, request.context)
        return {"step": request.step_id, "status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Step {request.step_id} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        pipeline.shutdown()


# Helper Functions


async def _run_import_pipeline(
    job_id: str,
    request: ProjectImportRequest,
    user_id: PyUUID,
    group_id: PyUUID,
    use_docker: bool = False,
) -> None:
    """Background task to run import pipeline."""
    # Get database session for registry
    from src.api.database.connection import async_session_maker

    def progress_callback(status: ProjectImportStatus) -> None:
        _import_jobs[job_id] = status
        # Broadcast via WebSocket
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
            pass

    # Configure pipeline
    config = get_config()
    if use_docker:
        config.joern.use_docker = True

    async with async_session_maker() as session:
        registry = ProjectRegistry(session)

        pipeline = ProjectImportPipeline(
            progress_callback=progress_callback,
            config=config,
            registry=registry,
        )

        try:
            result = await pipeline.run(
                request,
                user_id=user_id,
                group_id=group_id,
            )

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

        finally:
            pipeline.shutdown()


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
