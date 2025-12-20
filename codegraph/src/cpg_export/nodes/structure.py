"""Structure node exporters for CPG export.

Contains exporters for code structure nodes:
- FILE, NAMESPACE, NAMESPACE_BLOCK, MEMBER, TYPE, TYPE_DECL
"""
from typing import Optional
from .base import NodeExporter, parse_int, parse_bool


class FileExporter(NodeExporter):
    """Exporter for FILE nodes.

    Note: content is exported as empty string from Joern.
    Full file content is imported later by SourceContentStep.
    """

    @property
    def entity_type(self) -> str:
        return 'nodes_file'

    @property
    def cpg_type(self) -> str:
        return 'file'

    @property
    def query_template(self) -> str:
        return """
cpg.file.drop({offset}).take({batch_size}).map {{ f =>
  List(
    f.id,
    f.name,
    f.hash,
    "",
    f.lineNumber.getOrElse(-1),
    f.columnNumber.getOrElse(-1),
    f.order,
    0,
    ""
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_file VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 9

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),           # id
            parts[1],                 # name
            parts[2] if parts[2] else None,  # hash
            parts[3] if parts[3] else None,  # content (empty from Joern)
            parse_int(parts[4]),      # line_number
            parse_int(parts[5]),      # column_number
            parse_int(parts[6]),      # order_index
            parse_int(parts[7]) if len(parts) > 7 else None,  # size_bytes
            parts[8] if len(parts) > 8 and parts[8] else None,  # language
        )


class NamespaceExporter(NodeExporter):
    """Exporter for NAMESPACE nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_namespace'

    @property
    def cpg_type(self) -> str:
        return 'namespace'

    @property
    def query_template(self) -> str:
        return """
cpg.namespace.drop({offset}).take({batch_size}).map {{ n =>
  List(
    n.id,
    n.name,
    n.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    n.lineNumber.getOrElse(-1),
    n.columnNumber.getOrElse(-1),
    n.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_namespace VALUES (?, ?, ?, ?, ?, ?)"

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


class NamespaceBlockExporter(NodeExporter):
    """Exporter for NAMESPACE_BLOCK nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_namespace_block'

    @property
    def cpg_type(self) -> str:
        return 'namespaceBlock'

    @property
    def query_template(self) -> str:
        return """
cpg.namespaceBlock.drop({offset}).take({batch_size}).map {{ n =>
  List(
    n.id,
    n.name,
    n.fullName,
    n.filename,
    n.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    n.lineNumber.getOrElse(-1),
    n.columnNumber.getOrElse(-1),
    n.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_namespace_block VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parse_int(parts[5]),
            parse_int(parts[6]),
            parse_int(parts[7]),
        )


class MemberExporter(NodeExporter):
    """Exporter for MEMBER nodes (struct/class fields)."""

    @property
    def entity_type(self) -> str:
        return 'nodes_member'

    @property
    def cpg_type(self) -> str:
        return 'member'

    @property
    def query_template(self) -> str:
        return """
cpg.member.drop({offset}).take({batch_size}).map {{ m =>
  List(
    m.id,
    m.name,
    m.typeFullName,
    m.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    m.lineNumber.getOrElse(-1),
    m.columnNumber.getOrElse(-1),
    m.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_member VALUES (?, ?, ?, ?, ?, ?, ?)"

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


class TypeExporter(NodeExporter):
    """Exporter for TYPE nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_type'

    @property
    def cpg_type(self) -> str:
        return 'typ'

    @property
    def query_template(self) -> str:
        return """
cpg.typ.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.fullName,
    t.typeDeclFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_type VALUES (?, ?, ?, ?)"

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


class TypeDeclExporter(NodeExporter):
    """Exporter for TYPE_DECL nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_type_decl'

    @property
    def cpg_type(self) -> str:
        return 'typeDecl'

    @property
    def query_template(self) -> str:
        return """
cpg.typeDecl.drop({offset}).take({batch_size}).map {{ t =>
  List(
    t.id,
    t.name,
    t.fullName,
    t.isExternal.toString,
    "",
    t.aliasTypeFullName.getOrElse(""),
    t.filename,
    t.code.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t"),
    t.astParentType,
    t.astParentFullName
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_type_decl VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 10

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),
            parts[1],
            parts[2],
            parse_bool(parts[3]),
            None,  # inherits_from_type_full_name (complex array, skip for now)
            parts[5] if parts[5] else None,
            parts[6],
            parts[7],
            parts[8],
            parts[9] if len(parts) > 9 else None,
        )


class CommentExporter(NodeExporter):
    """Exporter for COMMENT nodes."""

    @property
    def entity_type(self) -> str:
        return 'nodes_comment'

    @property
    def cpg_type(self) -> str:
        return 'comment'

    @property
    def query_template(self) -> str:
        return """
cpg.comment.drop({offset}).take({batch_size}).map {{ c =>
  List(
    c.id,
    c.code,
    c.filename.getOrElse("unknown"),
    c.lineNumber.getOrElse(-1),
    c.columnNumber.getOrElse(-1),
    c.offset.getOrElse(-1),
    c.offsetEnd.getOrElse(-1),
    c.order
  ).mkString("\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO nodes_comment VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    @property
    def field_count(self) -> int:
        return 8

    def parse_row(self, parts: list) -> tuple:
        return (
            int(parts[0]),   # id
            parts[1],        # code (comment text)
            parts[2],        # filename
            parse_int(parts[3]),  # line_number
            parse_int(parts[4]),  # column_number
            parse_int(parts[5]),  # offset
            parse_int(parts[6]),  # offset_end
            parse_int(parts[7]),  # order_index
        )


# Export all structure node exporters
STRUCTURE_EXPORTERS = [
    FileExporter,
    NamespaceExporter,
    NamespaceBlockExporter,
    MemberExporter,
    TypeExporter,
    TypeDeclExporter,
    CommentExporter,
]
