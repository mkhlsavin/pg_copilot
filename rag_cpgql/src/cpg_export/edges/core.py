"""Core edge exporters for CPG export.

Contains exporters for the most common edge types:
- AST, CFG, CALL, REF, ARGUMENT, RECEIVER, CONDITION
"""
from typing import Optional
from .base import EdgeExporter


class AstEdgeExporter(EdgeExporter):
    """Exporter for AST edges (Abstract Syntax Tree)."""

    @property
    def entity_type(self) -> str:
        return 'edges_ast'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.astChildren.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_ast VALUES (?, ?)"


class CfgEdgeExporter(EdgeExporter):
    """Exporter for CFG edges (Control Flow Graph)."""

    @property
    def entity_type(self) -> str:
        return 'edges_cfg'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.cfgNext.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_cfg VALUES (?, ?)"


class CallEdgeExporter(EdgeExporter):
    """Exporter for CALL edges (call site to method)."""

    @property
    def entity_type(self) -> str:
        return 'edges_call'

    @property
    def count_query(self) -> str:
        return "cpg.call.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.call.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.callee.map(m => s"${{c.id}}\\t${{m.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_call VALUES (?, ?)"


class RefEdgeExporter(EdgeExporter):
    """Exporter for REF edges (identifier to declaration)."""

    @property
    def entity_type(self) -> str:
        return 'edges_ref'

    @property
    def count_query(self) -> str:
        return "cpg.identifier.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.identifier.drop({offset}).take({batch_size}).flatMap {{ i =>
  i.refOut.map(r => s"${{i.id}}\\t${{r.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_ref VALUES (?, ?)"


class ArgumentEdgeExporter(EdgeExporter):
    """Exporter for ARGUMENT edges (call to arguments)."""

    @property
    def entity_type(self) -> str:
        return 'edges_argument'

    @property
    def count_query(self) -> str:
        return "cpg.call.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.call.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.argument.map(a => s"${{c.id}}\\t${{a.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_argument VALUES (?, ?)"


class ReceiverEdgeExporter(EdgeExporter):
    """Exporter for RECEIVER edges (call to receiver object)."""

    @property
    def entity_type(self) -> str:
        return 'edges_receiver'

    @property
    def count_query(self) -> str:
        return "cpg.call.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.call.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.receiver.map(r => s"${{c.id}}\\t${{r.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_receiver VALUES (?, ?)"


class ConditionEdgeExporter(EdgeExporter):
    """Exporter for CONDITION edges (control structure to condition expression)."""

    @property
    def entity_type(self) -> str:
        return 'edges_condition'

    @property
    def count_query(self) -> str:
        return "cpg.controlStructure.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.controlStructure.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.condition.map(cond => s"${{c.id}}\\t${{cond.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_condition VALUES (?, ?)"


class SourceFileEdgeExporter(EdgeExporter):
    """Exporter for SOURCE_FILE edges (node to file)."""

    @property
    def entity_type(self) -> str:
        return 'edges_source_file'

    @property
    def count_query(self) -> str:
        return "cpg.comment.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.comment.drop({offset}).take({batch_size}).flatMap {{ c =>
  c.file.map(f => s"${{c.id}}\\t${{f.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_source_file VALUES (?, ?)"


# Export all core edge exporters
CORE_EDGE_EXPORTERS = [
    AstEdgeExporter,
    CfgEdgeExporter,
    CallEdgeExporter,
    RefEdgeExporter,
    ArgumentEdgeExporter,
    ReceiverEdgeExporter,
    ConditionEdgeExporter,
    SourceFileEdgeExporter,
]
