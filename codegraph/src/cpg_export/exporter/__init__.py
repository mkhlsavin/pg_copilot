"""CPG Exporter Package.

Exports Joern CPG to DuckDB with CPG Spec v1.1 schema.

Main components:
- JoernToDuckDB: Main orchestrator for full CPG export
- ProgressTracker: Export progress tracking and resumption
- BatchProcessor: Batched node/edge export logic
- SchemaManager: DuckDB schema initialization

Example usage:
    from src.cpg_export.exporter import JoernToDuckDB

    exporter = JoernToDuckDB(
        workspace="my_project.cpg",
        db_path="cpg.duckdb"
    )
    exporter.export_full_cpg()
"""

from .orchestrator import JoernToDuckDB
from .progress import ProgressTracker
from .batch_processor import BatchProcessor

__all__ = [
    "JoernToDuckDB",
    "ProgressTracker",
    "BatchProcessor",
]
