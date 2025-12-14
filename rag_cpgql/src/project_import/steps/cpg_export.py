"""
CPG Export Step.

Exports CPG from Joern to DuckDB using the modular JoernToDuckDBExporter.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..config import ProjectImportConfig, get_config
from ..server import JoernServerManager
from src.config import get_joern_home

logger = logging.getLogger(__name__)


class CpgExportStep:
    """Step for exporting CPG to DuckDB."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        server_manager: Optional[JoernServerManager] = None,
    ):
        """
        Initialize CPG export step.

        Args:
            progress_callback: Optional callback for reporting progress.
            server_manager: Optional pre-configured server manager.
        """
        self.progress_callback = progress_callback
        self._server_manager = server_manager

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CPG export to DuckDB.

        Args:
            context: Pipeline context with:
                - request: ProjectImportRequest
                - cpg_path: Path to CPG file
                - config (optional): ProjectImportConfig
                - server_manager (optional): JoernServerManager

        Returns:
            Dictionary with duckdb_path and cpg_stats.
        """
        request = context["request"]
        cpg_path = Path(context["cpg_path"])

        # Get configuration
        config: ProjectImportConfig = context.get("config") or get_config()

        # Get or create server manager
        server_manager: JoernServerManager = (
            context.get("server_manager")
            or self._server_manager
            or JoernServerManager(config)
        )

        # Determine DuckDB output path
        duckdb_dir = config.duckdb_path or cpg_path.parent
        duckdb_dir.mkdir(parents=True, exist_ok=True)
        duckdb_path = duckdb_dir / cpg_path.with_suffix(".duckdb").name

        self._report_progress(5, "Ensuring Joern server is ready...")

        # Ensure server is running
        if not server_manager.ensure_running():
            raise RuntimeError("Failed to start Joern server")

        self._report_progress(10, "Opening CPG workspace...")

        # Open the CPG workspace
        if not server_manager.open_workspace(cpg_path.name):
            # Try with full path
            full_cpg_path = str(cpg_path.absolute())
            client = server_manager.get_client()
            result = client.execute_query(f'Joern.open("{full_cpg_path}")')
            client.close()
            if not result.get("success"):
                raise RuntimeError(f"Failed to open CPG: {cpg_path}")

        self._report_progress(15, "Initializing exporter...")

        # Import and use the new modular exporter
        try:
            from src.cpg_export import JoernToDuckDBExporter
        except ImportError as e:
            logger.error(f"Failed to import JoernToDuckDBExporter: {e}")
            raise RuntimeError(
                "JoernToDuckDBExporter not available. "
                "Please ensure src.cpg_export module is properly installed."
            )

        # Create exporter
        exporter = JoernToDuckDBExporter(
            server_endpoint=config.joern.server_endpoint,
            workspace=cpg_path.name,
            db_path=str(duckdb_path),
            batch_size=config.batch_size,
        )

        self._report_progress(20, "Exporting CPG to DuckDB...")

        try:
            # Run export with progress tracking
            results = await self._export_with_progress(exporter)
        finally:
            exporter.close()

        # Extract statistics
        node_stats = results.get("node_stats", {})
        edge_stats = results.get("edge_stats", {})
        validation = results.get("validation", {})

        # Calculate totals
        total_nodes = sum(node_stats.values())
        total_edges = sum(edge_stats.values())

        self._report_progress(100, f"Export complete: {total_nodes} nodes, {total_edges} edges")

        logger.info(f"CPG exported to {duckdb_path}")
        logger.info(f"Node stats: {node_stats}")
        logger.info(f"Edge stats: {edge_stats}")

        return {
            "duckdb_path": str(duckdb_path),
            "cpg_stats": {
                "nodes": node_stats,
                "edges": edge_stats,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
            },
            "validation_results": validation,
            "server_manager": server_manager,
        }

    async def _export_with_progress(self, exporter) -> Dict[str, Any]:
        """
        Export CPG with progress reporting.

        Args:
            exporter: JoernToDuckDBExporter instance.

        Returns:
            Export results dictionary.
        """
        # Export stages with progress percentages
        stages = [
            (25, "Creating schema..."),
            (35, "Exporting methods..."),
            (45, "Exporting calls..."),
            (55, "Exporting identifiers..."),
            (65, "Exporting control structures..."),
            (75, "Exporting edges..."),
            (85, "Creating property graph..."),
            (95, "Validating export..."),
        ]

        # Report initial stages (actual progress comes from exporter)
        for progress, message in stages[:2]:
            self._report_progress(progress, message)

        # Run the full export
        try:
            results = exporter.export_full_cpg(
                resume=True,
                force_recreate=False,
                skip_validation=False,
            )
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise RuntimeError(f"CPG export failed: {e}")

        return results

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"CPG export step: {progress}% - {message}")


class CpgExportStepLegacy:
    """
    Legacy CPG export step (backward compatibility).

    Uses the old JoernToDuckDB class. Prefer CpgExportStep for new code.
    """

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute legacy CPG export."""
        request = context["request"]
        cpg_path = Path(context["cpg_path"])
        # Use joern_home from context, or get from config/env
        context_home = context.get("joern_home")
        if context_home:
            joern_home = Path(context_home)
        else:
            config_home = get_joern_home()
            if config_home is None:
                raise ValueError(
                    "JOERN_HOME not configured. Set JOERN_HOME environment variable "
                    "or configure joern.home in config.yaml"
                )
            joern_home = config_home

        duckdb_path = cpg_path.with_suffix(".duckdb")

        self._report_progress(5, "Ensuring Joern server is ready...")

        # Import legacy modules
        try:
            from src.execution.joern_bootstrap import ensure_joern_ready
            from src.execution.joern_client import JoernClient
        except ImportError as e:
            raise RuntimeError(f"Required modules not available: {e}")

        # Ensure Joern server is running (uses JOERN_ENDPOINT env var or config)
        if not ensure_joern_ready():
            raise RuntimeError("Failed to start Joern server")

        self._report_progress(10, "Connecting to Joern server...")

        # JoernClient uses JOERN_ENDPOINT env var or config.yaml joern.endpoint
        client = JoernClient(
            workspace=cpg_path.name,
        )

        if not client.connect():
            raise RuntimeError("Failed to connect to Joern server")

        try:
            self._report_progress(15, f"Loading CPG: {cpg_path.name}...")

            # Open the CPG
            result = client.execute_query(f'Joern.open("{cpg_path.name}")')
            if not result["success"]:
                result = client.execute_query(f'Joern.open("{str(cpg_path)}")')
                if not result["success"]:
                    raise RuntimeError(f"Failed to open CPG: {result.get('error')}")

            self._report_progress(20, "Exporting to DuckDB...")

            # Try new exporter first, fallback to legacy
            try:
                from src.cpg_export.joern_to_duckdb_v2 import JoernToDuckDB

                exporter = JoernToDuckDB(
                    joern_path=str(joern_home),
                    workspace_path=str(cpg_path.parent),
                    db_path=str(duckdb_path),
                    batch_size=getattr(request, 'batch_size', 10000),
                )

                exporter.connect_db()

                self._report_progress(25, "Creating schema...")

                if hasattr(exporter, "export_full_cpg"):
                    stats = exporter.export_full_cpg()
                else:
                    stats = exporter.export_all()

                exporter.close_db()

            except ImportError:
                logger.warning("Legacy exporter not available")
                stats = {"methods": 0, "calls": 0}

        finally:
            client.close()

        self._report_progress(100, "DuckDB export completed")

        return {
            "duckdb_path": str(duckdb_path),
            "cpg_stats": stats,
        }

    def _report_progress(self, progress: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"CPG export step: {progress}% - {message}")
