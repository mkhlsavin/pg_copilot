"""Core node exporters for CPG export.

Contains exporters for the most common node types:
- METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE
"""
from typing import Optional
from .base import NodeExporter, parse_int, parse_bool, escape_code


class MethodExporter(NodeExporter):
    """Exporter for METHOD nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_method'

    @property
    def cpg_type(self) -> str:
        return 'method'

    @property
    def query_template(self) -> str:
        return """
cpg.method.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.name,
    m.fullName,
    m.signature,
    m.filename,
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.lineNumberEnd.getOrElse(-1),
    m.columnNumberEnd.getOrElse(-1),
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.isExternal.toString,
    m.astParentType,
    m.astParentFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_method VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 13

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),   # id
            parts[1],        # name
            parts[2],        # full_name
            parts[3],        # signature
            parts[4],        # filename
            parse_int(parts[5]),   # line_number
            parse_int(parts[6]),   # column_number
            parse_int(parts[7]),   # line_number_end
            parse_int(parts[8]),   # column_number_end
            parts[9],        # code
            parse_bool(parts[10]), # is_external
            parts[11],       # ast_parent_type
            parts[12],       # ast_parent_full_name
            None,            # order_index
            None             # hash
        )


class CallExporter(NodeExporter):
    """Exporter for CALL nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_call'

    @property
    def cpg_type(self) -> str:
        return 'call'

    @property
    def query_template(self) -> str:
        return """
cpg.call.drop({offset}).take({batch_size}).map {{ c =>
  List(
    c.id,
    c.methodFullName,
    c.name,
    c.signature,
    c.typeFullName,
    c.dispatchType,
    c.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.order,
    c.argumentIndex,
    c.file.name.headOption.getOrElse("")
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_call VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 12

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),        # id
            parts[1],             # method_full_name
            parts[2],             # name
            parts[3],             # signature
            parts[4],             # type_full_name
            parts[5],             # dispatch_type
            parts[6],             # code
            parse_int(parts[7]),  # line_number
            parse_int(parts[8]),  # column_number
            parse_int(parts[9]),  # order_index
            parse_int(parts[10]), # argument_index
            parts[11] if len(parts) > 11 and parts[11] else None  # filename
        )


class IdentifierExporter(NodeExporter):
    """Exporter for IDENTIFIER nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_identifier'

    @property
    def cpg_type(self) -> str:
        return 'identifier'

    @property
    def query_template(self) -> str:
        return """
cpg.identifier.drop({offset}).take({batch_size}).map {{ i =>
  List(
    i.id,
    i.name,
    i.typeFullName,
    i.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    i.lineNumber.getOrElse(-1),
    i.columnNumber.getOrElse(-1),
    i.order,
    i.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_identifier VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

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
        )


class LiteralExporter(NodeExporter):
    """Exporter for LITERAL nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_literal'

    @property
    def cpg_type(self) -> str:
        return 'literal'

    @property
    def query_template(self) -> str:
        return """
cpg.literal.drop({offset}).take({batch_size}).map {{ l =>
  List(
    l.id,
    l.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    l.typeFullName,
    l.lineNumber.getOrElse(-1),
    l.columnNumber.getOrElse(-1),
    l.order,
    l.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_literal VALUES (?, ?, ?, ?, ?, ?, ?)"

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
            parse_int(parts[6]),
        )


class LocalExporter(NodeExporter):
    """Exporter for LOCAL nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_local'

    @property
    def cpg_type(self) -> str:
        return 'local'

    @property
    def query_template(self) -> str:
        return """
cpg.local.drop({offset}).take({batch_size}).map {{ l =>
  List(
    l.id,
    l.name,
    l.typeFullName,
    l.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    l.lineNumber.getOrElse(-1),
    l.columnNumber.getOrElse(-1),
    l.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_local VALUES (?, ?, ?, ?, ?, ?, ?)"

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


class ParamExporter(NodeExporter):
    """Exporter for METHOD_PARAMETER_IN nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_param'

    @property
    def cpg_type(self) -> str:
        return 'parameter'

    @property
    def query_template(self) -> str:
        return """
cpg.parameter.drop({offset}).take({batch_size}).map {{ p =>
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
        return "INSERT OR IGNORE INTO nodes_param VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

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


class ReturnExporter(NodeExporter):
    """Exporter for RETURN nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_return'

    @property
    def cpg_type(self) -> str:
        return 'ret'

    @property
    def query_template(self) -> str:
        return """
cpg.ret.drop({offset}).take({batch_size}).map {{ r =>
  List(
    r.id,
    r.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    r.lineNumber.getOrElse(-1),
    r.columnNumber.getOrElse(-1),
    r.order,
    r.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_return VALUES (?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 6

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parse_int(parts[2]),
            parse_int(parts[3]),
            parse_int(parts[4]),
            parse_int(parts[5]),
        )


class BlockExporter(NodeExporter):
    """Exporter for BLOCK nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_block'

    @property
    def cpg_type(self) -> str:
        return 'block'

    @property
    def query_template(self) -> str:
        return """
cpg.block.drop({offset}).take({batch_size}).map {{ b =>
  List(
    b.id,
    b.typeFullName,
    b.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    b.lineNumber.getOrElse(-1),
    b.columnNumber.getOrElse(-1),
    b.order,
    b.argumentIndex
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_block VALUES (?, ?, ?, ?, ?, ?, ?)"

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
            parse_int(parts[6]),
        )


class ControlStructureExporter(NodeExporter):
    """Exporter for CONTROL_STRUCTURE nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_control_structure'

    @property
    def cpg_type(self) -> str:
        return 'controlStructure'

    @property
    def query_template(self) -> str:
        return """
cpg.controlStructure.drop({offset}).take({batch_size}).map {{ c =>
  List(
    c.id,
    c.controlStructureType,
    c.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.order,
    c.parserTypeName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_control_structure VALUES (?, ?, ?, ?, ?, ?, ?)"

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


# Export all core node exporters
CORE_EXPORTERS = [
    MethodExporter,
    CallExporter,
    IdentifierExporter,
    LiteralExporter,
    LocalExporter,
    ParamExporter,
    ReturnExporter,
    BlockExporter,
    ControlStructureExporter,
]
