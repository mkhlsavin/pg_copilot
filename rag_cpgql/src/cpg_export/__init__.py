"""CPG Export Package - Export Joern CPG to DuckDB.

This package provides tools for exporting Code Property Graphs from Joern
to DuckDB with full CPG Spec v1.1 compliance.

Main components:
- JoernToDuckDBExporter: Main exporter class (recommended entry point)
- schema: Table and index definitions
- nodes: Node exporter classes
- edges: Edge exporter classes
- progress: Checkpoint/resume functionality
- validation: Export validation

Example usage:
    from src.cpg_export import JoernToDuckDBExporter

    # Uses JOERN_ENDPOINT env var or config.yaml joern.endpoint
    exporter = JoernToDuckDBExporter(
        workspace="myproject.cpg",
        db_path="cpg.duckdb"
    )
    results = exporter.export_full_cpg()

For backward compatibility, the original JoernToDuckDB class from
joern_to_duckdb_v2.py is still available.
"""

# Main exporter (recommended)
from .exporter import JoernToDuckDBExporter

# Schema
from .schema import (
    NODE_TABLES,
    EDGE_TABLES,
    INDEXES,
    ALL_NODE_TABLES,
    ALL_EDGE_TABLES,
    ALL_TABLES,
    initialize_schema,
    get_all_tables_to_drop,
)

# Progress tracking
from .progress import (
    ExportProgress,
    ProgressTracker,
)

# Validation
from .validation import (
    ValidationResult,
    ExportValidator,
    validate_export,
    NODE_TYPE_MAPPING,
)

# Node exporters
from . import nodes
from . import edges

__all__ = [
    # Main exporter
    'JoernToDuckDBExporter',
    # Schema
    'NODE_TABLES',
    'EDGE_TABLES',
    'INDEXES',
    'ALL_NODE_TABLES',
    'ALL_EDGE_TABLES',
    'ALL_TABLES',
    'initialize_schema',
    'get_all_tables_to_drop',
    # Progress
    'ExportProgress',
    'ProgressTracker',
    # Validation
    'ValidationResult',
    'ExportValidator',
    'validate_export',
    'NODE_TYPE_MAPPING',
    # Subpackages
    'nodes',
    'edges',
]
