"""
Validate Step.

Validates the exported CPG in DuckDB.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class ValidateStep:
    """Step for validating CPG export."""

    # Validation queries to run
    VALIDATION_QUERIES = {
        "methods_exist": "SELECT COUNT(*) FROM nodes_method WHERE name IS NOT NULL",
        "calls_exist": "SELECT COUNT(*) FROM nodes_call",
        "identifiers_exist": "SELECT COUNT(*) FROM nodes_identifier",
        "edges_ast": "SELECT COUNT(*) FROM edges_ast",
        "edges_cfg": "SELECT COUNT(*) FROM edges_cfg",
        "edges_call": "SELECT COUNT(*) FROM edges_call",
        "methods_with_files": (
            "SELECT COUNT(*) FROM nodes_method "
            "WHERE filename IS NOT NULL AND filename != ''"
        ),
        "methods_with_lines": (
            "SELECT COUNT(*) FROM nodes_method WHERE line_number > 0"
        ),
    }

    # Minimum requirements for a valid CPG
    MINIMUM_REQUIREMENTS = {
        "methods_exist": 1,  # At least 1 method
        "edges_ast": 0,  # AST edges (can be 0 for small projects)
    }

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize validate step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CPG validation.

        Args:
            context: Pipeline context with duckdb_path.

        Returns:
            Dictionary with validation_report.
        """
        duckdb_path = context["duckdb_path"]

        self._report_progress(10, "Connecting to DuckDB...")

        conn = duckdb.connect(duckdb_path, read_only=True)

        validation_results: Dict[str, Any] = {}
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Check what tables exist
            self._report_progress(15, "Checking tables...")
            tables = self._get_existing_tables(conn)
            validation_results["tables_found"] = tables

            # Run validation queries
            total_queries = len(self.VALIDATION_QUERIES)
            for i, (name, query) in enumerate(self.VALIDATION_QUERIES.items()):
                progress = 20 + int((i / total_queries) * 60)
                self._report_progress(progress, f"Checking {name}...")

                try:
                    # Check if required table exists
                    table_name = self._extract_table_name(query)
                    if table_name and table_name not in tables:
                        validation_results[name] = 0
                        warnings.append(f"Table not found: {table_name}")
                        continue

                    result = conn.execute(query).fetchone()
                    count = result[0] if result else 0
                    validation_results[name] = count

                    # Check minimum requirements
                    if name in self.MINIMUM_REQUIREMENTS:
                        min_required = self.MINIMUM_REQUIREMENTS[name]
                        if count < min_required:
                            errors.append(
                                f"{name}: expected >= {min_required}, got {count}"
                            )

                except Exception as e:
                    validation_results[name] = f"Error: {e}"
                    errors.append(f"{name}: {e}")

            # Calculate statistics
            self._report_progress(85, "Calculating statistics...")

            stats = self._calculate_statistics(conn, tables)
            validation_results["statistics"] = stats

        finally:
            conn.close()

        self._report_progress(95, "Generating report...")

        # Calculate quality score
        quality_score = self._calculate_quality_score(validation_results, errors)

        report = {
            "status": "passed" if not errors else "failed",
            "results": validation_results,
            "errors": errors,
            "warnings": warnings,
            "quality_score": quality_score,
            "duckdb_path": duckdb_path,
            "duckdb_size_mb": round(Path(duckdb_path).stat().st_size / (1024 * 1024), 2),
        }

        if errors:
            logger.warning(f"Validation errors: {errors}")
        if warnings:
            logger.info(f"Validation warnings: {warnings}")

        self._report_progress(100, f"Validation {report['status']} (score: {quality_score})")

        return {"validation_report": report}

    def _get_existing_tables(self, conn) -> List[str]:
        """Get list of existing tables in database."""
        result = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        return [row[0] for row in result]

    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from query."""
        query_lower = query.lower()
        if "from" in query_lower:
            parts = query_lower.split("from")
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.strip()
        return None

    def _calculate_statistics(self, conn, tables: List[str]) -> Dict[str, Any]:
        """Calculate additional statistics about the CPG."""
        stats = {}

        # Count total nodes and edges
        node_tables = [t for t in tables if t.startswith("nodes_")]
        edge_tables = [t for t in tables if t.startswith("edges_")]

        total_nodes = 0
        total_edges = 0

        for table in node_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[f"{table}_count"] = count
                total_nodes += count
            except Exception:
                pass

        for table in edge_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[f"{table}_count"] = count
                total_edges += count
            except Exception:
                pass

        stats["total_nodes"] = total_nodes
        stats["total_edges"] = total_edges
        stats["node_tables"] = len(node_tables)
        stats["edge_tables"] = len(edge_tables)

        return stats

    def _calculate_quality_score(
        self, results: Dict[str, Any], errors: List[str]
    ) -> int:
        """
        Calculate quality score (0-100).

        Scoring criteria:
        - 50 points base if methods exist
        - 20 points for file coverage
        - 15 points for edges
        - 15 points for no errors
        """
        score = 0

        # Methods exist (50 points)
        methods_count = results.get("methods_exist", 0)
        if isinstance(methods_count, int) and methods_count > 0:
            score += 50

        # File coverage (20 points)
        if isinstance(methods_count, int) and methods_count > 0:
            methods_with_files = results.get("methods_with_files", 0)
            if isinstance(methods_with_files, int):
                coverage = methods_with_files / methods_count
                score += int(coverage * 20)

        # Edges (15 points)
        ast_edges = results.get("edges_ast", 0)
        cfg_edges = results.get("edges_cfg", 0)
        if isinstance(ast_edges, int) and ast_edges > 0:
            score += 8
        if isinstance(cfg_edges, int) and cfg_edges > 0:
            score += 7

        # No errors (15 points)
        if not errors:
            score += 15

        return min(100, score)

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Validate step: {progress}% - {message}")
