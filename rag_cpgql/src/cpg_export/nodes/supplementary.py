"""Supplementary node exporters for CPG export.

Contains exporters for P1-P3 priority node types:
- METHOD_PARAMETER_OUT, METHOD_RETURN, FIELD_IDENTIFIER, TYPE_ARGUMENT, TYPE_PARAMETER
- JUMP_LABEL, JUMP_TARGET, METHOD_REF, MODIFIER, TYPE_REF, UNKNOWN
- BINDING, ANNOTATION, ANNOTATION_LITERAL, ANNOTATION_PARAMETER, ANNOTATION_PARAMETER_ASSIGN
"""
from typing import Optional
from .base import NodeExporter, parse_int, parse_bool


# =============================================================================
# P1 Nodes - Important for analysis
# =============================================================================

class MethodParameterOutExporter(NodeExporter):
    """Exporter for METHOD_PARAMETER_OUT nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_method_parameter_out'

    @property
    def cpg_type(self) -> str:
        return 'methodParameterOut'

    @property
    def query_template(self) -> str:
        return """
cpg.methodParameterOut.drop({offset}).take({batch_size}).map {{ p =>
  List(
    p.id,
    p.name,
    p.typeFullName,
    p.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    p.lineNumber.getOrElse(-1),
    p.columnNumber.getOrElse(-1),
    p.order,
    p.index,
    p.isVariadic.toString,
    p.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_method_parameter_out VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 10

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
            parse_bool(parts[8]),
            parts[9] if len(parts) > 9 else None,
        )


class MethodReturnExporter(NodeExporter):
    """Exporter for METHOD_RETURN nodes (formal return type)."""

    @property
    def entity_type(self) -> str:
        return 'nodes_method_return'

    @property
    def cpg_type(self) -> str:
        return 'methodReturn'

    @property
    def query_template(self) -> str:
        return """
cpg.methodReturn.drop({offset}).take({batch_size}).map {{ r =>
  List(
    r.id,
    r.typeFullName,
    r.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    r.lineNumber.getOrElse(-1),
    r.columnNumber.getOrElse(-1),
    r.order,
    r.evaluationStrategy
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_method_return VALUES (?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 7

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
            parts[6] if len(parts) > 6 else None,
        )


class FieldIdentifierExporter(NodeExporter):
    """Exporter for FIELD_IDENTIFIER nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_field_identifier'

    @property
    def cpg_type(self) -> str:
        return 'fieldAccess'

    @property
    def query_template(self) -> str:
        return """
cpg.fieldAccess.drop({offset}).take({batch_size}).map {{ f =>
  List(
    f.id,
    f.canonicalName,
    f.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    f.lineNumber.getOrElse(-1),
    f.columnNumber.getOrElse(-1),
    f.order,
    f.argumentIndex,
    f.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_field_identifier VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
            parts[7] if len(parts) > 7 and parts[7] else None,
        )


class TypeArgumentExporter(NodeExporter):
    """Exporter for TYPE_ARGUMENT nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_type_argument'

    @property
    def cpg_type(self) -> str:
        return 'typeArgument'

    @property
    def query_template(self) -> str:
        return """
cpg.typeArgument.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_type_argument VALUES (?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 5

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parse_int(parts[2]),
            parse_int(parts[3]),
            parse_int(parts[4]),
        )


class TypeParameterExporter(NodeExporter):
    """Exporter for TYPE_PARAMETER nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_type_parameter'

    @property
    def cpg_type(self) -> str:
        return 'typeParameter'

    @property
    def query_template(self) -> str:
        return """
cpg.typeParameter.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_type_parameter VALUES (?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 6

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
        )


# =============================================================================
# P2 Nodes - Supplementary
# =============================================================================

class JumpLabelExporter(NodeExporter):
    """Exporter for JUMP_LABEL nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_jump_label'

    @property
    def cpg_type(self) -> str:
        return 'jumpLabel'

    @property
    def query_template(self) -> str:
        return """
cpg.jumpLabel.drop({offset}).take({batch_size}).map {{ j =>
  List(
    j.id,
    j.name,
    j.parserTypeName,
    j.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    j.lineNumber.getOrElse(-1),
    j.columnNumber.getOrElse(-1),
    j.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_jump_label VALUES (?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 7

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
        )


class JumpTargetExporter(NodeExporter):
    """Exporter for JUMP_TARGET nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_jump_target'

    @property
    def cpg_type(self) -> str:
        return 'jumpTarget'

    @property
    def query_template(self) -> str:
        return """
cpg.jumpTarget.drop({offset}).take({batch_size}).map {{ j =>
  List(
    j.id,
    j.name,
    j.parserTypeName,
    j.argumentIndex,
    j.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    j.lineNumber.getOrElse(-1),
    j.columnNumber.getOrElse(-1),
    j.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_jump_target VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parts[4],
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
        )


class MethodRefExporter(NodeExporter):
    """Exporter for METHOD_REF nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_method_ref'

    @property
    def cpg_type(self) -> str:
        return 'methodRef'

    @property
    def query_template(self) -> str:
        return """
cpg.methodRef.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.methodFullName,
    m.typeFullName,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order,
    m.argumentIndex,
    m.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_method_ref VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 9

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
            parts[8] if len(parts) > 8 and parts[8] else None,
        )


class ModifierExporter(NodeExporter):
    """Exporter for MODIFIER nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_modifier'

    @property
    def cpg_type(self) -> str:
        return 'modifier'

    @property
    def query_template(self) -> str:
        return """
cpg.modifier.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.modifierType,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_modifier VALUES (?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 6

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
        )


class TypeRefExporter(NodeExporter):
    """Exporter for TYPE_REF nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_type_ref'

    @property
    def cpg_type(self) -> str:
        return 'typeRef'

    @property
    def query_template(self) -> str:
        return """
cpg.typeRef.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.typeFullName,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.lineNumber.getOrElse(-1),
    t.columnNumber.getOrElse(-1),
    t.order,
    t.argumentIndex,
    t.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_type_ref VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
            parts[7] if len(parts) > 7 and parts[7] else None,
        )


class UnknownExporter(NodeExporter):
    """Exporter for UNKNOWN nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_unknown'

    @property
    def cpg_type(self) -> str:
        return 'unknown'

    @property
    def query_template(self) -> str:
        return """
cpg.unknown.drop({offset}).take({batch_size}).map {{ u =>
  List(
    u.id,
    u.containedRef,
    u.parserTypeName,
    u.typeFullName,
    u.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    u.lineNumber.getOrElse(-1),
    u.columnNumber.getOrElse(-1),
    u.order,
    u.argumentIndex,
    u.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_unknown VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 10

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1] if parts[1] else None,
            parts[2],
            parts[3],
            parts[4],
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
            parse_int(parts[8]),
            parts[9] if len(parts) > 9 and parts[9] else None,
        )


# =============================================================================
# P3 Nodes - Low priority
# =============================================================================

class BindingExporter(NodeExporter):
    """Exporter for BINDING nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_binding'

    @property
    def cpg_type(self) -> str:
        return 'binding'

    @property
    def query_template(self) -> str:
        return """
cpg.binding.drop({offset}).take({batch_size}).map {{ b =>
  List(
    b.id,
    b.name,
    b.signature,
    b.methodFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_binding VALUES (?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 4

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3] if len(parts) > 3 else None,
        )


class AnnotationExporter(NodeExporter):
    """Exporter for ANNOTATION nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_annotation'

    @property
    def cpg_type(self) -> str:
        return 'annotation'

    @property
    def query_template(self) -> str:
        return """
cpg.annotation.drop({offset}).take({batch_size}).map {{ a =>
  List(
    a.id,
    a.name,
    a.fullName,
    a.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    a.lineNumber.getOrElse(-1),
    a.columnNumber.getOrElse(-1),
    a.order,
    a.argumentIndex,
    a.argumentName.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_annotation VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 9

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            parse_int(parts[4]),
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
            parts[8] if len(parts) > 8 and parts[8] else None,
        )


# Export all supplementary node exporters
SUPPLEMENTARY_EXPORTERS = [
    # P1
    MethodParameterOutExporter,
    MethodReturnExporter,
    FieldIdentifierExporter,
    TypeArgumentExporter,
    TypeParameterExporter,
    # P2
    JumpLabelExporter,
    JumpTargetExporter,
    MethodRefExporter,
    ModifierExporter,
    TypeRefExporter,
    UnknownExporter,
    # P3
    BindingExporter,
    AnnotationExporter,
]
