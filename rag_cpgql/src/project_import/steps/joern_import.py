"""
Joern Import Step.

Creates CPG using Joern frontend for the detected language.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models import ImportMode, JoernFrontend

logger = logging.getLogger(__name__)


class JoernImportStep:
    """Step for importing code into Joern and creating CPG."""

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize Joern import step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Joern import to create CPG.

        Args:
            context: Pipeline context with request, source_path, and joern_frontend.

        Returns:
            Dictionary with cpg_path and import stats.
        """
        request = context["request"]
        source_path = Path(context["source_path"])
        frontend: JoernFrontend = context["joern_frontend"]

        # Determine Joern paths
        joern_home = Path(
            request.joern_home
            or os.environ.get("JOERN_HOME", "C:/Users/user/joern")
        )
        cpg_name = request.cpg_name or f"{source_path.name}.cpg"
        workspace_path = Path(request.workspace_path or joern_home / "workspace")
        cpg_path = workspace_path / cpg_name

        workspace_path.mkdir(parents=True, exist_ok=True)

        # Determine import path based on mode
        import_path = self._get_import_path(source_path, request)

        self._report_progress(5, f"Starting {frontend.command}...")

        # Build and execute Joern command
        cmd = self._build_joern_command(
            joern_home, frontend, import_path, cpg_path, request
        )

        logger.info(f"Running Joern command: {' '.join(str(c) for c in cmd)}")

        # Check if frontend exists
        frontend_path = joern_home / "joern-cli" / frontend.command
        if not frontend_path.exists():
            # Try with .bat extension on Windows
            frontend_path_bat = joern_home / "joern-cli" / f"{frontend.command}.bat"
            if frontend_path_bat.exists():
                cmd[0] = str(frontend_path_bat)
            else:
                # Try in joern-cli/bin
                frontend_path_bin = joern_home / "joern-cli" / "bin" / frontend.command
                if frontend_path_bin.exists():
                    cmd[0] = str(frontend_path_bin)
                else:
                    logger.warning(
                        f"Frontend not found at expected paths, using command as-is: {frontend.command}"
                    )

        self._report_progress(10, "Parsing source files...")

        process = await asyncio.create_subprocess_exec(
            *[str(c) for c in cmd],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(joern_home),
            env={**os.environ, "JAVA_OPTS": f"-Xmx{request.joern_memory_gb}g"},
        )

        # Monitor progress from stderr
        async def monitor_stderr():
            while True:
                if process.stderr is None:
                    break
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode(errors="ignore").strip()
                if line_str:
                    logger.debug(f"Joern: {line_str}")
                    # Parse progress from output
                    lower_line = line_str.lower()
                    if "parsing" in lower_line:
                        self._report_progress(30, "Parsing source files...")
                    elif "creating" in lower_line or "generating" in lower_line:
                        self._report_progress(50, "Creating CPG nodes...")
                    elif "linking" in lower_line:
                        self._report_progress(70, "Linking CPG edges...")
                    elif "writing" in lower_line or "serializing" in lower_line:
                        self._report_progress(85, "Writing CPG to disk...")

        await asyncio.gather(process.wait(), monitor_stderr())

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode(errors="ignore") if stderr else "Unknown error"
            raise RuntimeError(f"Joern import failed (exit code {process.returncode}): {error_msg}")

        # Verify CPG was created
        if not cpg_path.exists():
            # Check if it was created with different extension
            possible_paths = [
                cpg_path,
                cpg_path.with_suffix(".bin"),
                cpg_path.with_suffix(".cpg.bin"),
            ]
            for p in possible_paths:
                if p.exists():
                    cpg_path = p
                    break
            else:
                raise RuntimeError(f"CPG file not created. Expected at: {cpg_path}")

        cpg_size_mb = cpg_path.stat().st_size / (1024 * 1024)

        self._report_progress(100, f"CPG created ({cpg_size_mb:.1f} MB)")

        logger.info(f"CPG created at {cpg_path} ({cpg_size_mb:.1f} MB)")

        return {
            "cpg_path": str(cpg_path),
            "joern_home": str(joern_home),
            "import_stats": {
                "source_path": str(source_path),
                "cpg_size_mb": round(cpg_size_mb, 2),
                "frontend": frontend.command,
                "language_flag": frontend.joern_language_flag,
            },
        }

    def _get_import_path(self, source_path: Path, request) -> Path:
        """
        Determine path for import based on mode.

        For selective mode, uses the first include path.
        Otherwise uses the full source path.
        """
        if request.mode == ImportMode.SELECTIVE and request.include_paths:
            # For selective mode, we'll need to handle multiple paths differently
            # For now, use the first include path
            first_include = source_path / request.include_paths[0]
            if first_include.exists():
                return first_include
            logger.warning(f"Include path not found: {first_include}, using root")

        return source_path

    def _build_joern_command(
        self,
        joern_home: Path,
        frontend: JoernFrontend,
        import_path: Path,
        cpg_path: Path,
        request,
    ) -> List:
        """Build the Joern frontend command."""
        # Try to find the frontend binary
        frontend_binary = joern_home / "joern-cli" / frontend.command

        cmd = [
            str(frontend_binary),
            str(import_path),
            "-o",
            str(cpg_path),
        ]

        # Add exclude patterns
        all_excludes = list(frontend.exclude_patterns)
        if request.exclude_paths:
            all_excludes.extend(request.exclude_paths)

        for exclude in all_excludes:
            cmd.extend(["--exclude", exclude])

        return cmd

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Joern import step: {progress}% - {message}")
