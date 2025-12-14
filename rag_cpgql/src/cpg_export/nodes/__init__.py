"""Node exporters for CPG export.

This package contains exporters for all CPG node types organized by category:
- core.py: METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE
- structure.py: FILE, NAMESPACE, NAMESPACE_BLOCK, MEMBER, TYPE, TYPE_DECL, COMMENT
- supplementary.py: P1/P2/P3 node types (METHOD_REF, MODIFIER, ANNOTATION, etc.)
"""
from .base import NodeExporter, parse_int, parse_bool, escape_code

from .core import (
    MethodExporter,
    CallExporter,
    IdentifierExporter,
    LiteralExporter,
    LocalExporter,
    ParamExporter,
    ReturnExporter,
    BlockExporter,
    ControlStructureExporter,
    CORE_EXPORTERS,
)

from .structure import (
    FileExporter,
    NamespaceExporter,
    NamespaceBlockExporter,
    MemberExporter,
    TypeExporter,
    TypeDeclExporter,
    CommentExporter,
    STRUCTURE_EXPORTERS,
)

from .supplementary import (
    MethodParameterOutExporter,
    MethodReturnExporter,
    FieldIdentifierExporter,
    TypeArgumentExporter,
    TypeParameterExporter,
    JumpLabelExporter,
    JumpTargetExporter,
    MethodRefExporter,
    ModifierExporter,
    TypeRefExporter,
    UnknownExporter,
    BindingExporter,
    AnnotationExporter,
    SUPPLEMENTARY_EXPORTERS,
)


# All node exporter classes in export order
ALL_NODE_EXPORTERS = CORE_EXPORTERS + STRUCTURE_EXPORTERS + SUPPLEMENTARY_EXPORTERS


def get_all_exporters(joern_client, conn, batch_size: int = 10000) -> list:
    """Create instances of all node exporters.

    Args:
        joern_client: JoernClient instance
        conn: DuckDB connection
        batch_size: Batch size for export

    Returns:
        List of instantiated NodeExporter objects
    """
    return [
        exporter_class(joern_client, conn, batch_size)
        for exporter_class in ALL_NODE_EXPORTERS
    ]


__all__ = [
    # Base
    'NodeExporter',
    'parse_int',
    'parse_bool',
    'escape_code',
    # Core
    'MethodExporter',
    'CallExporter',
    'IdentifierExporter',
    'LiteralExporter',
    'LocalExporter',
    'ParamExporter',
    'ReturnExporter',
    'BlockExporter',
    'ControlStructureExporter',
    'CORE_EXPORTERS',
    # Structure
    'FileExporter',
    'NamespaceExporter',
    'NamespaceBlockExporter',
    'MemberExporter',
    'TypeExporter',
    'TypeDeclExporter',
    'CommentExporter',
    'STRUCTURE_EXPORTERS',
    # Supplementary
    'MethodParameterOutExporter',
    'MethodReturnExporter',
    'FieldIdentifierExporter',
    'TypeArgumentExporter',
    'TypeParameterExporter',
    'JumpLabelExporter',
    'JumpTargetExporter',
    'MethodRefExporter',
    'ModifierExporter',
    'TypeRefExporter',
    'UnknownExporter',
    'BindingExporter',
    'AnnotationExporter',
    'SUPPLEMENTARY_EXPORTERS',
    # All
    'ALL_NODE_EXPORTERS',
    'get_all_exporters',
]
