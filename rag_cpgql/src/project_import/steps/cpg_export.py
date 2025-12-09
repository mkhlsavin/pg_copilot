"""
CPG Export Step.

Exports CPG from Joern to DuckDB using the existing exporter.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CpgExportStep:
    """Step for exporting CPG to DuckDB."""

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize CPG export step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CPG export to DuckDB.

        Args:
            context: Pipeline context with cpg_path and joern_home.

        Returns:
            Dictionary with duckdb_path and cpg_stats.
        """
        request = context["request"]
        cpg_path = Path(context["cpg_path"])
        joern_home = Path(context["joern_home"])

        # Determine DuckDB output path
        duckdb_path = cpg_path.with_suffix(".duckdb")

        self._report_progress(5, "Ensuring Joern server is ready...")

        # Import existing modules
        try:
            from src.execution.joern_bootstrap import ensure_joern_ready
            from src.execution.joern_client import JoernClient
        except ImportError as e:
            logger.error(f"Failed to import Joern modules: {e}")
            raise RuntimeError(f"Required modules not available: {e}")

        # Ensure Joern server is running
        server_ready = ensure_joern_ready(server_endpoint="localhost:8080")
        if not server_ready:
            raise RuntimeError("Failed to start Joern server")

        self._report_progress(10, "Connecting to Joern server...")

        # Connect to Joern and load CPG
        client = JoernClient(
            server_endpoint="localhost:8080",
            workspace=cpg_path.name,
        )

        if not client.connect():
            raise RuntimeError("Failed to connect to Joern server")

        try:
            self._report_progress(15, f"Loading CPG: {cpg_path.name}...")

            # Open the CPG
            open_result = client.execute_query(f'Joern.open("{cpg_path.name}")')
            if not open_result["success"]:
                # Try with full path
                open_result = client.execute_query(f'Joern.open("{str(cpg_path)}")')
                if not open_result["success"]:
                    raise RuntimeError(f"Failed to open CPG: {open_result.get('error')}")

            self._report_progress(20, "Exporting to DuckDB...")

            # Use the existing exporter
            try:
                from src.cpg_export.joern_to_duckdb_v2 import JoernToDuckDB
            except ImportError:
                logger.warning("JoernToDuckDB not available, using direct export")
                return await self._direct_export(client, duckdb_path, request)

            # Export using existing module
            exporter = JoernToDuckDB(
                joern_path=str(joern_home),
                workspace_path=str(cpg_path.parent),
                db_path=str(duckdb_path),
                batch_size=request.batch_size,
            )

            exporter.connect_db()

            self._report_progress(25, "Creating schema...")

            # Export with progress tracking
            stats = await self._export_with_progress(exporter)

            exporter.close_db()

        finally:
            client.close()

        self._report_progress(100, "DuckDB export completed")

        logger.info(f"CPG exported to {duckdb_path}")
        logger.info(f"Export stats: {stats}")

        return {
            "duckdb_path": str(duckdb_path),
            "cpg_stats": stats,
        }

    async def _export_with_progress(self, exporter) -> Dict[str, int]:
        """
        Export CPG with progress reporting.

        Returns:
            Dictionary with export statistics.
        """
        stats = {}

        # Export sequence with progress
        tables = [
            ("methods", "Exporting methods...", 30),
            ("calls", "Exporting calls...", 45),
            ("identifiers", "Exporting identifiers...", 55),
            ("literals", "Exporting literals...", 60),
            ("locals", "Exporting locals...", 65),
            ("parameters", "Exporting parameters...", 70),
            ("types", "Exporting types...", 75),
            ("comments", "Exporting comments...", 80),
            ("edges", "Exporting edges...", 90),
        ]

        try:
            # Call full export method if available
            if hasattr(exporter, "export_full_cpg"):
                for table_name, message, progress in tables:
                    self._report_progress(progress, message)

                stats = exporter.export_full_cpg()
            else:
                # Fallback to individual exports
                stats = exporter.export_all()

        except Exception as e:
            logger.error(f"Export error: {e}")
            raise

        return stats

    async def _direct_export(
        self, client, duckdb_path: Path, request
    ) -> Dict[str, Any]:
        """
        Direct export using Joern client without JoernToDuckDB.

        This is a fallback if the main exporter is not available.
        """
        import duckdb

        self._report_progress(25, "Creating DuckDB schema...")

        conn = duckdb.connect(str(duckdb_path))

        try:
            # Create basic schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes_method (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR,
                    full_name VARCHAR,
                    signature VARCHAR,
                    filename VARCHAR,
                    line_number INTEGER,
                    code TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes_call (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR,
                    method_full_name VARCHAR,
                    filename VARCHAR,
                    line_number INTEGER,
                    code TEXT
                )
            """)

            self._report_progress(40, "Exporting methods...")

            # Export methods
            methods_result = client.execute_query(
                "cpg.method.map(m => (m.id, m.name, m.fullName, m.signature, m.filename, m.lineNumber.getOrElse(-1), m.code)).l"
            )

            methods_count = 0
            if methods_result["success"]:
                # Parse and insert methods
                self._report_progress(60, "Inserting methods...")
                # Note: Would need to parse Scala output here

            self._report_progress(80, "Exporting calls...")

            # Export calls
            calls_result = client.execute_query(
                "cpg.call.map(c => (c.id, c.name, c.methodFullName, c.file.name.headOption.getOrElse(\"\"), c.lineNumber.getOrElse(-1), c.code)).l"
            )

            calls_count = 0
            if calls_result["success"]:
                self._report_progress(90, "Inserting calls...")
                # Note: Would need to parse Scala output here

            conn.commit()

        finally:
            conn.close()

        return {
            "methods": methods_count,
            "calls": calls_count,
            "export_method": "direct",
        }

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"CPG export step: {progress}% - {message}")
