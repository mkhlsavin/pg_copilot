"""
Project Import Pipeline.

Main orchestrator for the import process with PostgreSQL integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .config import ProjectImportConfig, get_config
from .models import (
    ImportMode,
    ImportStep,
    ImportStepStatus,
    ProjectImportRequest,
    ProjectImportResult,
    ProjectImportStatus,
)
from .registry import ProjectRegistry
from .server import JoernServerManager
from .steps import (
    ChromaDBImportStep,
    CloneStep,
    CpgExportStep,
    DetectLanguageStep,
    DomainSetupStep,
    JoernImportStep,
    ValidateStep,
)

logger = logging.getLogger(__name__)


# Step registry: (step_id, display_name, step_class)
PIPELINE_STEPS: List[Tuple[str, str, Type]] = [
    ("clone", "Clone Repository", CloneStep),
    ("detect_language", "Detect Language", DetectLanguageStep),
    ("joern_import", "Create CPG", JoernImportStep),
    ("cpg_export", "Export to DuckDB", CpgExportStep),
    ("validate", "Validate CPG", ValidateStep),
    ("chromadb_import", "Import Documentation", ChromaDBImportStep),
    ("domain_setup", "Setup Domain Plugin", DomainSetupStep),
]


class ProjectImportPipeline:
    """
    Main pipeline for importing projects.

    Orchestrates the execution of import steps, tracks progress,
    and integrates with PostgreSQL project registry.
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[ProjectImportStatus], None]] = None,
        config: Optional[ProjectImportConfig] = None,
        registry: Optional[ProjectRegistry] = None,
        session: Optional[AsyncSession] = None,
    ):
        """
        Initialize the import pipeline.

        Args:
            progress_callback: Optional callback for progress updates.
            config: Import configuration. If None, loads from config.yaml.
            registry: Project registry for PostgreSQL operations.
            session: SQLAlchemy async session (used if registry not provided).
        """
        self.progress_callback = progress_callback
        self.config = config or get_config()

        # Initialize registry
        if registry:
            self.registry = registry
        elif session:
            self.registry = ProjectRegistry(session)
        else:
            self.registry = None

        # Server manager initialized lazily
        self._server_manager: Optional[JoernServerManager] = None
        self._status: Optional[ProjectImportStatus] = None
        self._job_id: Optional[str] = None
        self._db_job_id: Optional[UUID] = None
        self._cancelled = False

    @property
    def server_manager(self) -> JoernServerManager:
        """Get or create Joern server manager."""
        if self._server_manager is None:
            self._server_manager = JoernServerManager(self.config)
        return self._server_manager

    async def run(
        self,
        request: ProjectImportRequest,
        user_id: Optional[UUID] = None,
        group_id: Optional[UUID] = None,
    ) -> ProjectImportResult:
        """
        Run the full import pipeline.

        Args:
            request: Import request with configuration.
            user_id: User initiating the import (for PostgreSQL tracking).
            group_id: Project group ID (for PostgreSQL tracking).

        Returns:
            ProjectImportResult with all output paths and statistics.

        Raises:
            RuntimeError: If import fails.
            ValueError: If request is invalid.
        """
        self._job_id = str(uuid.uuid4())
        self._cancelled = False

        project_name = self._extract_project_name(request)

        # Create import job in PostgreSQL if registry available
        if self.registry and user_id and group_id:
            try:
                db_job = await self.registry.create_import_job(
                    user_id=user_id,
                    group_id=group_id,
                    project_name=project_name,
                    source_url=request.repo_url,
                    language=request.language.value if request.language else None,
                    import_mode=request.mode.value if request.mode else ImportMode.FULL.value,
                )
                self._db_job_id = db_job.id
                logger.info(f"Created import job in PostgreSQL: {db_job.id}")
            except Exception as e:
                logger.warning(f"Failed to create import job in PostgreSQL: {e}")

        # Initialize status
        self._status = ProjectImportStatus(
            job_id=self._job_id,
            project_name=project_name,
            status="in_progress",
            steps=[
                ImportStep(name=display_name, status=ImportStepStatus.PENDING)
                for _, display_name, _ in PIPELINE_STEPS
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Execution context shared between steps
        context: Dict[str, Any] = {
            "request": request,
            "config": self.config,
            "server_manager": self.server_manager,
        }

        start_time = datetime.utcnow()

        try:
            # Ensure Joern server is ready
            logger.info("Ensuring Joern server is ready...")
            if not self.server_manager.ensure_running():
                raise RuntimeError("Failed to start Joern server")

            for i, (step_id, step_name, step_class) in enumerate(PIPELINE_STEPS):
                if self._cancelled:
                    raise RuntimeError("Import cancelled by user")

                # Check if step should be skipped
                if self._should_skip_step(step_id, request):
                    await self._update_step_status(
                        i, ImportStepStatus.SKIPPED, 100, "Skipped"
                    )
                    continue

                # Start step
                await self._update_step_status(
                    i, ImportStepStatus.IN_PROGRESS, 0, f"Starting {step_name}..."
                )
                self._status.current_step = step_id

                # Update PostgreSQL job
                await self._update_db_job(
                    current_step=step_id,
                    progress=self._status.overall_progress,
                )

                # Create step instance with progress callback
                step = step_class(
                    progress_callback=lambda p, m, idx=i: asyncio.create_task(
                        self._step_progress(idx, p, m)
                    )
                )

                try:
                    # Execute step
                    logger.info(f"Executing step: {step_name}")
                    result = await step.execute(context)

                    # Merge result into context
                    context.update(result)

                    await self._update_step_status(
                        i, ImportStepStatus.COMPLETED, 100, "Done"
                    )

                except Exception as e:
                    logger.error(f"Step {step_name} failed: {e}", exc_info=True)
                    await self._update_step_status(
                        i, ImportStepStatus.FAILED, 0, str(e), error=str(e)
                    )
                    raise RuntimeError(f"Step '{step_name}' failed: {e}") from e

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Get detected language
            detected_language = context.get("detected_language")

            # Build result
            result = ProjectImportResult(
                cpg_path=context.get("cpg_path", ""),
                duckdb_path=context.get("duckdb_path", ""),
                domain_plugin_path=context.get("domain_plugin_path"),
                chromadb_collection=context.get("chromadb_collection"),
                chromadb_stats=context.get("chromadb_stats", {}),
                cpg_stats=context.get("cpg_stats", {}),
                validation_report=context.get("validation_report", {}),
                detected_language=detected_language,
                import_duration_seconds=duration,
                source_info=context.get("clone_info", {}),
            )

            self._status.status = "completed"
            self._status.result = result.model_dump()
            await self._notify_progress()

            logger.info(f"Import completed in {duration:.1f}s")

            # Create project in PostgreSQL
            project_id = await self._create_project_record(
                context=context,
                result=result,
                group_id=group_id,
            )

            # Complete import job in PostgreSQL
            if self.registry and self._db_job_id and project_id:
                try:
                    await self.registry.complete_import_job(
                        job_id=self._db_job_id,
                        project_id=project_id,
                        result={
                            "cpg_path": result.cpg_path,
                            "duckdb_path": result.duckdb_path,
                            "cpg_stats": result.cpg_stats,
                            "duration_seconds": duration,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to complete import job: {e}")

            return result

        except Exception as e:
            self._status.status = "failed"
            self._status.error = str(e)
            await self._notify_progress()

            # Mark job as failed in PostgreSQL
            if self.registry and self._db_job_id:
                try:
                    await self.registry.fail_import_job(
                        job_id=self._db_job_id,
                        error_message=str(e),
                    )
                except Exception as db_error:
                    logger.warning(f"Failed to update job status: {db_error}")

            raise

    async def _create_project_record(
        self,
        context: Dict[str, Any],
        result: ProjectImportResult,
        group_id: Optional[UUID],
    ) -> Optional[UUID]:
        """
        Create project record in PostgreSQL.

        Args:
            context: Pipeline execution context.
            result: Import result.
            group_id: Project group ID.

        Returns:
            Created project ID or None.
        """
        if not self.registry:
            logger.debug("No registry configured, skipping project creation")
            return None

        try:
            # Get or create default group if not specified
            if not group_id:
                group = await self.registry.get_or_create_default_group()
                group_id = group.id

            detected_language = context.get("detected_language")
            language_str = (
                detected_language.value
                if detected_language
                else "unknown"
            )

            project = await self.registry.create_project(
                name=self._status.project_name if self._status else "unknown",
                group_id=group_id,
                source_path=context.get("source_path", ""),
                cpg_path=result.cpg_path,
                duckdb_path=result.duckdb_path,
                language=language_str,
                description=f"Imported from {context.get('request', {}).repo_url or context.get('source_path', 'local')}",
                metadata={
                    "cpg_stats": result.cpg_stats,
                    "chromadb_collection": result.chromadb_collection,
                    "domain_plugin_path": result.domain_plugin_path,
                    "import_duration_seconds": result.import_duration_seconds,
                    "validation_report": result.validation_report,
                },
            )

            logger.info(f"Created project in PostgreSQL: {project.id}")

            # Set as active project
            await self.registry.set_active_project(project.id)

            return project.id

        except Exception as e:
            logger.warning(f"Failed to create project record: {e}")
            return None

    async def run_step(
        self, step_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a single step of the pipeline.

        Args:
            step_id: ID of the step to run.
            context: Execution context with required data.

        Returns:
            Step result dictionary.

        Raises:
            ValueError: If step_id is invalid.
        """
        # Ensure context has config and server_manager
        if "config" not in context:
            context["config"] = self.config
        if "server_manager" not in context:
            context["server_manager"] = self.server_manager

        for sid, name, step_class in PIPELINE_STEPS:
            if sid == step_id:
                logger.info(f"Running single step: {name}")
                step = step_class(
                    progress_callback=lambda p, m: logger.info(f"{name}: {p}% - {m}")
                )
                return await step.execute(context)

        valid_steps = [s[0] for s in PIPELINE_STEPS]
        raise ValueError(f"Unknown step: {step_id}. Valid steps: {valid_steps}")

    def cancel(self) -> None:
        """Cancel the running import."""
        self._cancelled = True
        if self._status:
            self._status.status = "cancelled"

    def get_status(self) -> Optional[ProjectImportStatus]:
        """Get current status."""
        return self._status

    def shutdown(self) -> None:
        """Shutdown the pipeline and cleanup resources."""
        if self._server_manager:
            try:
                self._server_manager.stop()
            except Exception as e:
                logger.warning(f"Error stopping server: {e}")

    def _should_skip_step(self, step_id: str, request: ProjectImportRequest) -> bool:
        """Determine if a step should be skipped."""
        if step_id == "clone" and request.local_path:
            return True
        if step_id == "chromadb_import" and not request.import_docs:
            return True
        if step_id == "domain_setup" and not request.create_domain_plugin:
            return True
        return False

    async def _update_step_status(
        self,
        step_index: int,
        status: ImportStepStatus,
        progress: int,
        message: str,
        error: Optional[str] = None,
    ) -> None:
        """Update the status of a step."""
        if not self._status or step_index >= len(self._status.steps):
            return

        step = self._status.steps[step_index]
        step.status = status
        step.progress = progress
        step.message = message
        step.error = error

        if status == ImportStepStatus.IN_PROGRESS:
            step.started_at = datetime.utcnow()
        elif status in (ImportStepStatus.COMPLETED, ImportStepStatus.FAILED):
            step.completed_at = datetime.utcnow()

        self._status.overall_progress = self._calculate_overall_progress()
        self._status.updated_at = datetime.utcnow()

        await self._notify_progress()

    async def _step_progress(
        self, step_index: int, progress: int, message: str
    ) -> None:
        """Handle progress update from a step."""
        if not self._status or step_index >= len(self._status.steps):
            return

        self._status.steps[step_index].progress = progress
        self._status.steps[step_index].message = message
        self._status.overall_progress = self._calculate_overall_progress()

        await self._notify_progress()

        # Update PostgreSQL job periodically
        if progress % 25 == 0:
            await self._update_db_job(progress=self._status.overall_progress)

    def _calculate_overall_progress(self) -> int:
        """Calculate overall progress from step progresses."""
        if not self._status or not self._status.steps:
            return 0

        total = sum(s.progress for s in self._status.steps)
        return total // len(self._status.steps)

    async def _notify_progress(self) -> None:
        """Notify progress callback."""
        if self.progress_callback and self._status:
            try:
                self.progress_callback(self._status)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    async def _update_db_job(
        self,
        current_step: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> None:
        """Update import job in PostgreSQL."""
        if not self.registry or not self._db_job_id:
            return

        try:
            await self.registry.update_import_job(
                job_id=self._db_job_id,
                status="running",
                progress=progress,
                current_step=current_step,
            )
        except Exception as e:
            logger.debug(f"Failed to update import job: {e}")

    def _extract_project_name(self, request: ProjectImportRequest) -> str:
        """Extract project name from request."""
        if request.repo_url:
            name = request.repo_url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return name
        if request.local_path:
            return Path(request.local_path).name
        return "unknown_project"


# Convenience function for running the pipeline
async def import_project(
    repo_url: Optional[str] = None,
    local_path: Optional[str] = None,
    language: Optional[str] = None,
    branch: str = "main",
    shallow_clone: bool = True,
    import_docs: bool = True,
    create_domain_plugin: bool = True,
    use_docker: bool = False,
    progress_callback: Optional[Callable[[ProjectImportStatus], None]] = None,
    session: Optional[AsyncSession] = None,
    user_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
) -> ProjectImportResult:
    """
    Convenience function to import a project.

    Args:
        repo_url: Git repository URL.
        local_path: Local path to source code.
        language: Programming language (auto-detect if None).
        branch: Git branch to clone.
        shallow_clone: Use shallow clone.
        import_docs: Import documentation.
        create_domain_plugin: Create domain plugin.
        use_docker: Use Docker for Joern.
        progress_callback: Progress callback.
        session: SQLAlchemy async session for PostgreSQL tracking.
        user_id: User ID for PostgreSQL tracking.
        group_id: Project group ID for PostgreSQL tracking.

    Returns:
        ProjectImportResult with import results.
    """
    from .models import SupportedLanguage

    request = ProjectImportRequest(
        repo_url=repo_url,
        local_path=local_path,
        language=SupportedLanguage(language) if language else None,
        branch=branch,
        shallow_clone=shallow_clone,
        import_docs=import_docs,
        create_domain_plugin=create_domain_plugin,
    )

    # Get config and optionally enable Docker
    config = get_config()
    if use_docker:
        config.joern.use_docker = True

    pipeline = ProjectImportPipeline(
        progress_callback=progress_callback,
        config=config,
        session=session,
    )

    try:
        return await pipeline.run(request, user_id=user_id, group_id=group_id)
    finally:
        pipeline.shutdown()


async def import_project_simple(
    source: str,
    language: Optional[str] = None,
    use_docker: bool = False,
) -> ProjectImportResult:
    """
    Simplified import function for quick imports.

    Args:
        source: Repository URL or local path.
        language: Programming language (auto-detect if None).
        use_docker: Use Docker for Joern.

    Returns:
        ProjectImportResult with import results.
    """
    # Determine if source is URL or local path
    is_url = source.startswith(("http://", "https://", "git@", "ssh://"))

    return await import_project(
        repo_url=source if is_url else None,
        local_path=None if is_url else source,
        language=language,
        use_docker=use_docker,
        import_docs=False,
        create_domain_plugin=False,
    )
