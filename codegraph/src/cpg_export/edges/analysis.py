"""Analysis edge exporters for CPG export.

Contains exporters for analysis-related edge types:
- REACHING_DEF, DOMINATE, POST_DOMINATE, CDG
- CONTAINS, EVAL_TYPE, INHERITS_FROM, ALIAS_OF
- BINDS_TO, PARAMETER_LINK, TAGGED_BY, BINDS
"""
from typing import Optional
from .base import EdgeExporter


class ReachingDefEdgeExporter(EdgeExporter):
    """Exporter for REACHING_DEF edges (data flow)."""

    @property
    def entity_type(self) -> str:
        return 'edges_reaching_def'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.reachingDefOut.map(r => s"${{n.id}}\\t${{r.id}}\\t")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_reaching_def VALUES (?, ?, ?)"

    def parse_edge(self, parts: list) -> tuple:
        """Parse edge with variable field."""
        return (
            int(parts[0]),
            int(parts[1]),
            parts[2] if len(parts) > 2 and parts[2] else None
        )


class DominateEdgeExporter(EdgeExporter):
    """Exporter for DOMINATE edges (dominance tree)."""

    @property
    def entity_type(self) -> str:
        return 'edges_dominate'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.dominates.map(d => s"${{n.id}}\\t${{d.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_dominate VALUES (?, ?)"


class PostDominateEdgeExporter(EdgeExporter):
    """Exporter for POST_DOMINATE edges (post-dominance tree)."""

    @property
    def entity_type(self) -> str:
        return 'edges_post_dominate'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.postDominates.map(d => s"${{n.id}}\\t${{d.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_post_dominate VALUES (?, ?)"


class CdgEdgeExporter(EdgeExporter):
    """Exporter for CDG edges (Control Dependence Graph)."""

    @property
    def entity_type(self) -> str:
        return 'edges_cdg'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.cdgOut.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_cdg VALUES (?, ?)"


class ContainsEdgeExporter(EdgeExporter):
    """Exporter for CONTAINS edges (containment relationship)."""

    @property
    def entity_type(self) -> str:
        return 'edges_contains'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.containsOut.map(c => s"${{n.id}}\\t${{c.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_contains VALUES (?, ?)"


class EvalTypeEdgeExporter(EdgeExporter):
    """Exporter for EVAL_TYPE edges (expression to type)."""

    @property
    def entity_type(self) -> str:
        return 'edges_eval_type'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.evalTypeOut.map(t => s"${{n.id}}\\t${{t.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_eval_type VALUES (?, ?)"


class InheritsFromEdgeExporter(EdgeExporter):
    """Exporter for INHERITS_FROM edges (type inheritance)."""

    @property
    def entity_type(self) -> str:
        return 'edges_inherits_from'

    @property
    def count_query(self) -> str:
        return "cpg.typeDecl.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.typeDecl.drop({offset}).take({batch_size}).flatMap {{ t =>
  t.inheritsFromTypeFullName.flatMap {{ name =>
    cpg.typ.fullNameExact(name).map(parent => s"${{t.id}}\\t${{parent.id}}")
  }}
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_inherits_from VALUES (?, ?)"


class AliasOfEdgeExporter(EdgeExporter):
    """Exporter for ALIAS_OF edges (type aliasing)."""

    @property
    def entity_type(self) -> str:
        return 'edges_alias_of'

    @property
    def count_query(self) -> str:
        return "cpg.typ.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.typ.drop({offset}).take({batch_size}).flatMap {{ t =>
  t.aliasTypeFullName.flatMap {{ name =>
    cpg.typeDecl.fullNameExact(name).map(decl => s"${{t.id}}\\t${{decl.id}}")
  }}
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_alias_of VALUES (?, ?)"


class BindsToEdgeExporter(EdgeExporter):
    """Exporter for BINDS_TO edges (type argument to type parameter)."""

    @property
    def entity_type(self) -> str:
        return 'edges_binds_to'

    @property
    def count_query(self) -> str:
        return "cpg.typeArgument.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.typeArgument.drop({offset}).take({batch_size}).flatMap {{ ta =>
  ta.bindsToTypeParameter.map(tp => s"${{ta.id}}\\t${{tp.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_binds_to VALUES (?, ?)"


class ParameterLinkEdgeExporter(EdgeExporter):
    """Exporter for PARAMETER_LINK edges (input to output parameter)."""

    @property
    def entity_type(self) -> str:
        return 'edges_parameter_link'

    @property
    def count_query(self) -> str:
        return "cpg.parameter.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.parameter.drop({offset}).take({batch_size}).flatMap {{ p =>
  p.parameterLinkOut.map(po => s"${{p.id}}\\t${{po.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_parameter_link VALUES (?, ?)"


class TaggedByEdgeExporter(EdgeExporter):
    """Exporter for TAGGED_BY edges (node to tag)."""

    @property
    def entity_type(self) -> str:
        return 'edges_tagged_by'

    @property
    def edge_query_template(self) -> str:
        return """
cpg.all.drop({offset}).take({batch_size}).flatMap {{ n =>
  n.taggedByOut.map(t => s"${{n.id}}\\t${{t.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_tagged_by VALUES (?, ?)"


class BindsEdgeExporter(EdgeExporter):
    """Exporter for BINDS edges (type decl to binding)."""

    @property
    def entity_type(self) -> str:
        return 'edges_binds'

    @property
    def count_query(self) -> str:
        return "cpg.typeDecl.size"

    @property
    def edge_query_template(self) -> str:
        return """
cpg.typeDecl.drop({offset}).take({batch_size}).flatMap {{ t =>
  t.bindsOut.map(b => s"${{t.id}}\\t${{b.id}}")
}}.l.mkString("\\n")
"""

    @property
    def insert_sql(self) -> str:
        return "INSERT OR IGNORE INTO edges_binds VALUES (?, ?)"


# Export all analysis edge exporters
ANALYSIS_EDGE_EXPORTERS = [
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
]
