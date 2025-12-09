"""
Project Import Pipeline.

Main orchestrator for the import process.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from .models import (
    ImportStep,
    ImportStepStatus,
    ProjectImportRequest,
    ProjectImportResult,
    ProjectImportStatus,
)
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

    Orchestrates the execution of import steps and tracks progress.
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[ProjectImportStatus], None]] = None,
        config_path: Optional[Path] = None,
    ):
        """
        Initialize the import pipeline.

        Args:
            progress_callback: Optional callback for progress updates.
            config_path: Optional path to configuration file.
        """
        self.progress_callback = progress_callback
        self.config_path = config_path or Path("config.yaml")
        self._status: Optional[ProjectImportStatus] = None
        self._job_id: Optional[str] = None
        self._cancelled = False

    async def run(self, request: ProjectImportRequest) -> ProjectImportResult:
        """
        Run the full import pipeline.

        Args:
            request: Import request with configuration.

        Returns:
            ProjectImportResult with all output paths and statistics.

        Raises:
            RuntimeError: If import fails.
            ValueError: If request is invalid.
        """
        self._job_id = str(uuid.uuid4())
        self._cancelled = False

        # Initialize status
        self._status = ProjectImportStatus(
            job_id=self._job_id,
            project_name=self._extract_project_name(request),
            status="in_progress",
            steps=[
                ImportStep(name=display_name, status=ImportStepStatus.PENDING)
                for _, display_name, _ in PIPELINE_STEPS
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Execution context shared between steps
        context: Dict[str, Any] = {"request": request}

        start_time = datetime.utcnow()

        try:
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

            # Build result
            result = ProjectImportResult(
                cpg_path=context.get("cpg_path", ""),
                duckdb_path=context.get("duckdb_path", ""),
                domain_plugin_path=context.get("domain_plugin_path"),
                chromadb_collection=context.get("chromadb_collection"),
                chromadb_stats=context.get("chromadb_stats", {}),
                cpg_stats=context.get("cpg_stats", {}),
                validation_report=context.get("validation_report", {}),
                detected_language=context.get("detected_language"),
                import_duration_seconds=duration,
                source_info=context.get("clone_info", {}),
            )

            self._status.status = "completed"
            self._status.result = result.model_dump()
            await self._notify_progress()

            logger.info(f"Import completed in {duration:.1f}s")

            return result

        except Exception as e:
            self._status.status = "failed"
            self._status.error = str(e)
            await self._notify_progress()
            raise

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
    progress_callback: Optional[Callable[[ProjectImportStatus], None]] = None,
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
        progress_callback: Progress callback.

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

    pipeline = ProjectImportPipeline(progress_callback=progress_callback)
    return await pipeline.run(request)
