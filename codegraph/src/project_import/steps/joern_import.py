"""
Joern Import Step.

Creates CPG using Joern frontend for the detected language.
Updated to use JoernServerManager and frontend registry.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..config import ProjectImportConfig, get_config
from ..frontends import JoernFrontend, get_frontend, get_exclude_patterns
from ..server import JoernServerManager


def get_joern_home() -> str:
    """Get Joern home directory from environment or default location."""
    import os
    return os.environ.get('JOERN_HOME', os.path.expanduser('~/joern'))

logger = logging.getLogger(__name__)


class JoernImportStep:
    """Step for importing code into Joern and creating CPG."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        server_manager: Optional[JoernServerManager] = None,
    ):
        """
        Initialize Joern import step.

        Args:
            progress_callback: Optional callback for reporting progress.
            server_manager: Optional pre-configured server manager.
        """
        self.progress_callback = progress_callback
        self._server_manager = server_manager

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Joern import to create CPG.

        Args:
            context: Pipeline context with:
                - request: ProjectImportRequest
                - source_path: Path to source code
                - joern_frontend: JoernFrontend configuration
                - config (optional): ProjectImportConfig
                - server_manager (optional): JoernServerManager

        Returns:
            Dictionary with cpg_path and import stats.
        """
        request = context["request"]
        source_path = Path(context["source_path"])
        frontend: JoernFrontend = context["joern_frontend"]

        # Get configuration
        config: ProjectImportConfig = context.get("config") or get_config()

        # Get or create server manager
        server_manager = (
            context.get("server_manager")
            or self._server_manager
            or JoernServerManager(config)
        )

        # Determine output paths
        workspace_path = config.workspace_path or config.joern.workspace_path
        if not workspace_path:
            workspace_path = Path("./workspace")

        workspace_path.mkdir(parents=True, exist_ok=True)

        cpg_name = request.cpg_name or f"{source_path.name}.cpg"
        cpg_path = workspace_path / cpg_name

        self._report_progress(5, f"Starting {frontend.command}...")

        # Determine import path based on mode
        import_path = self._get_import_path(source_path, request)

        # Build exclude patterns
        exclude_patterns = self._build_exclude_patterns(frontend, request, config)

        self._report_progress(10, "Running CPG frontend...")

        try:
            # Use server manager to run frontend
            success = await server_manager.run_frontend_async(
                frontend_command=frontend.command,
                input_path=import_path,
                output_path=cpg_path,
                exclude_patterns=exclude_patterns,
                timeout=getattr(request, 'joern_timeout', 3600),
                progress_callback=self._report_progress,
            )

            if not success:
                raise RuntimeError(f"CPG creation failed for {source_path}")

        except Exception as e:
            logger.error(f"Joern import failed: {e}")
            raise RuntimeError(f"Joern import failed: {e}")

        # Verify CPG was created
        if not cpg_path.exists():
            # Check alternate extensions
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
            "joern_home": str(config.joern.home) if config.joern.home else None,
            "server_manager": server_manager,
            "import_stats": {
                "source_path": str(source_path),
                "cpg_size_mb": round(cpg_size_mb, 2),
                "frontend": frontend.command,
                "language_flag": frontend.language_flag,
            },
        }

    def _get_import_path(self, source_path: Path, request) -> Path:
        """
        Determine path for import based on mode.

        For selective mode, uses include paths.
        Otherwise uses the full source path.
        """
        from ..models import ImportMode

        if hasattr(request, 'mode') and request.mode == ImportMode.SELECTIVE:
            if hasattr(request, 'include_paths') and request.include_paths:
                first_include = source_path / request.include_paths[0]
                if first_include.exists():
                    return first_include
                logger.warning(f"Include path not found: {first_include}, using root")

        return source_path

    def _build_exclude_patterns(
        self,
        frontend: JoernFrontend,
        request,
        config: ProjectImportConfig,
    ) -> List[str]:
        """Build combined exclude patterns from all sources."""
        patterns = set()

        # Add frontend defaults
        patterns.update(frontend.exclude_patterns)

        # Add config defaults
        if config.default_excludes:
            patterns.update(config.default_excludes)

        # Add request-specific excludes
        if hasattr(request, 'exclude_paths') and request.exclude_paths:
            patterns.update(request.exclude_paths)

        return list(patterns)

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Joern import step: {progress}% - {message}")


# Legacy class for backward compatibility
class JoernImportStepLegacy:
    """
    Legacy Joern import step (backward compatibility).

    Uses direct subprocess calls instead of ServerManager.
    Prefer JoernImportStep for new code.
    """

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute legacy Joern import."""
        request = context["request"]
        source_path = Path(context["source_path"])
        frontend: JoernFrontend = context["joern_frontend"]

        # Determine Joern paths (uses JOERN_HOME env var or config.yaml)
        request_joern_home = getattr(request, 'joern_home', None)
        if request_joern_home:
            joern_home = Path(request_joern_home)
        else:
            config_home = get_joern_home()
            if config_home is None:
                raise ValueError(
                    "JOERN_HOME not configured. Set JOERN_HOME environment variable "
                    "or configure joern.home in config.yaml"
                )
            joern_home = config_home
        cpg_name = getattr(request, 'cpg_name', None) or f"{source_path.name}.cpg"
        workspace_path = Path(
            getattr(request, 'workspace_path', None) or joern_home / "workspace"
        )
        cpg_path = workspace_path / cpg_name

        workspace_path.mkdir(parents=True, exist_ok=True)

        self._report_progress(5, f"Starting {frontend.command}...")

        # Build command
        frontend_path = joern_home / "joern-cli" / frontend.command
        if not frontend_path.exists():
            frontend_path_bat = joern_home / "joern-cli" / f"{frontend.command}.bat"
            if frontend_path_bat.exists():
                frontend_path = frontend_path_bat

        cmd = [
            str(frontend_path),
            str(source_path),
            "-o",
            str(cpg_path),
        ]

        # Add excludes
        for pattern in frontend.exclude_patterns:
            cmd.extend(["--exclude", pattern])

        self._report_progress(10, "Parsing source files...")

        process = await asyncio.create_subprocess_exec(
            *[str(c) for c in cmd],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(joern_home),
            env={
                **os.environ,
                "JAVA_OPTS": f"-Xmx{getattr(request, 'joern_memory_gb', 16)}g"
            },
        )

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

        if process.returncode != 0:
            stderr = await process.stderr.read() if process.stderr else b""
            raise RuntimeError(
                f"Joern import failed (exit code {process.returncode}): "
                f"{stderr.decode(errors='ignore')}"
            )

        if not cpg_path.exists():
            raise RuntimeError(f"CPG file not created. Expected at: {cpg_path}")

        cpg_size_mb = cpg_path.stat().st_size / (1024 * 1024)
        self._report_progress(100, f"CPG created ({cpg_size_mb:.1f} MB)")

        return {
            "cpg_path": str(cpg_path),
            "joern_home": str(joern_home),
            "import_stats": {
                "source_path": str(source_path),
                "cpg_size_mb": round(cpg_size_mb, 2),
                "frontend": frontend.command,
                "language_flag": frontend.language_flag,
            },
        }

    def _report_progress(self, progress: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Joern import step: {progress}% - {message}")
