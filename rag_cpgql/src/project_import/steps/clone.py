"""
Clone Step.

Handles git repository cloning with support for shallow clones.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CloneStep:
    """Step for cloning a git repository."""

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize clone step.

        Args:
            progress_callback: Optional callback for reporting progress (0-100, message).
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the clone step.

        Args:
            context: Pipeline context containing 'request' key with ProjectImportRequest.

        Returns:
            Dictionary with 'source_path' and 'clone_info' keys.
        """
        request = context["request"]

        if request.local_path:
            # Local path specified - skip cloning
            source_path = Path(request.local_path)
            if not source_path.exists():
                raise ValueError(f"Local path does not exist: {source_path}")

            self._report_progress(100, "Using local path")
            return {
                "source_path": source_path,
                "clone_info": {"type": "local", "path": str(source_path)},
            }

        if not request.repo_url:
            raise ValueError("Either repo_url or local_path must be specified")

        # Determine destination path
        project_name = self._extract_project_name(request.repo_url)
        workspace = Path(request.workspace_path or "workspace")
        dest_path = workspace / project_name

        workspace.mkdir(parents=True, exist_ok=True)

        # Check if already cloned
        if dest_path.exists() and (dest_path / ".git").exists():
            self._report_progress(50, "Repository already exists, pulling latest...")
            await self._pull_latest(dest_path, request.branch)
            self._report_progress(100, "Repository updated")
            return {
                "source_path": dest_path,
                "clone_info": {
                    "type": "existing",
                    "url": request.repo_url,
                    "branch": request.branch,
                    "path": str(dest_path),
                },
            }

        # Build git clone command
        cmd = ["git", "clone"]

        if request.shallow_clone:
            cmd.extend(["--depth", str(request.shallow_depth)])

        if request.branch and request.branch != "main":
            cmd.extend(["--branch", request.branch])

        cmd.append(request.repo_url)
        cmd.append(str(dest_path))

        self._report_progress(10, f"Cloning {request.repo_url}...")

        # Execute clone
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Git clone failed: {error_msg}")

        self._report_progress(100, "Clone completed")

        return {
            "source_path": dest_path,
            "clone_info": {
                "type": "cloned",
                "url": request.repo_url,
                "branch": request.branch,
                "shallow": request.shallow_clone,
                "depth": request.shallow_depth if request.shallow_clone else None,
                "path": str(dest_path),
            },
        }

    async def _pull_latest(self, repo_path: Path, branch: str) -> None:
        """Pull latest changes from remote."""
        try:
            # Fetch and pull
            fetch_cmd = ["git", "-C", str(repo_path), "fetch", "origin"]
            pull_cmd = ["git", "-C", str(repo_path), "pull", "origin", branch]

            process = await asyncio.create_subprocess_exec(
                *fetch_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            process = await asyncio.create_subprocess_exec(
                *pull_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

        except Exception as e:
            logger.warning(f"Failed to pull latest: {e}")

    def _extract_project_name(self, repo_url: str) -> str:
        """Extract project name from repository URL."""
        name = repo_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Clone step: {progress}% - {message}")
