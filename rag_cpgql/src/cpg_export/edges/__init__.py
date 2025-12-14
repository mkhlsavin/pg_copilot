"""Edge exporters for CPG export.

This package contains exporters for all CPG edge types organized by category:
- core.py: AST, CFG, CALL, REF, ARGUMENT, RECEIVER, CONDITION, SOURCE_FILE
- analysis.py: REACHING_DEF, DOMINATE, POST_DOMINATE, CDG, CONTAINS, EVAL_TYPE, etc.
"""
from .base import EdgeExporter

from .core import (
    AstEdgeExporter,
    CfgEdgeExporter,
    CallEdgeExporter,
    RefEdgeExporter,
    ArgumentEdgeExporter,
    ReceiverEdgeExporter,
    ConditionEdgeExporter,
    SourceFileEdgeExporter,
    CORE_EDGE_EXPORTERS,
)

from .analysis import (
    ReachingDefEdgeExporter,
    DominateEdgeExporter,
    PostDominateEdgeExporter,
    CdgEdgeExporter,
    ContainsEdgeExporter,
    EvalTypeEdgeExporter,
    InheritsFromEdgeExporter,
    AliasOfEdgeExporter,
    BindsToEdgeExporter,
    ParameterLinkEdgeExporter,
    TaggedByEdgeExporter,
    BindsEdgeExporter,
    ANALYSIS_EDGE_EXPORTERS,
)


# All edge exporter classes in export order
ALL_EDGE_EXPORTERS = CORE_EDGE_EXPORTERS + ANALYSIS_EDGE_EXPORTERS


def get_all_exporters(joern_client, conn, batch_size: int = 10000) -> list:
    """Create instances of all edge exporters.

    Args:
        joern_client: JoernClient instance
        conn: DuckDB connection
        batch_size: Batch size for export

    Returns:
        List of instantiated EdgeExporter objects
    """
    return [
        exporter_class(joern_client, conn, batch_size)
        for exporter_class in ALL_EDGE_EXPORTERS
    ]


__all__ = [
    # Base
    'EdgeExporter',
    # Core
    'AstEdgeExporter',
    'CfgEdgeExporter',
    'CallEdgeExporter',
    'RefEdgeExporter',
    'ArgumentEdgeExporter',
    'ReceiverEdgeExporter',
    'ConditionEdgeExporter',
    'SourceFileEdgeExporter',
    'CORE_EDGE_EXPORTERS',
    # Analysis
    'ReachingDefEdgeExporter',
    'DominateEdgeExporter',
    'PostDominateEdgeExporter',
    'CdgEdgeExporter',
    'ContainsEdgeExporter',
    'EvalTypeEdgeExporter',
    'InheritsFromEdgeExporter',
    'AliasOfEdgeExporter',
    'BindsToEdgeExporter',
    'ParameterLinkEdgeExporter',
    'TaggedByEdgeExporter',
    'BindsEdgeExporter',
    'ANALYSIS_EDGE_EXPORTERS',
    # All
    'ALL_EDGE_EXPORTERS',
    'get_all_exporters',
]
