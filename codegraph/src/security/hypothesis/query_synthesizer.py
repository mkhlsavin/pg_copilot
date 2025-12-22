"""
Query Synthesizer for Hypothesis Validation.

Generates DuckDB SQL/PGQ queries from security hypotheses.
All queries are designed for execution against a CPG stored in DuckDB.

IMPORTANT: Joern is only used for CPG export, not for queries.
"""

from typing import Dict, List, Optional, Tuple

from .models import SecurityHypothesis
from .query_templates import (
    SQL_TEMPLATES,
    PGQ_TEMPLATES,
    TEMPLATE_CATEGORIES,
    get_template,
    get_category_defaults,
)


class QuerySynthesizer:
    """Generates DuckDB SQL/PGQ queries from security hypotheses.

    Takes a hypothesis with source/sink/sanitizer patterns and produces
    executable SQL queries for validation against a CPG database.

    Templates are loaded from core templates and extended by providers.
    """

    def __init__(self):
        """Initialize query synthesizer."""
        # Start with core templates
        self.templates = dict(SQL_TEMPLATES)
        self.pgq_templates = dict(PGQ_TEMPLATES)
        self._template_categories = dict(TEMPLATE_CATEGORIES)

        # Load templates from registered providers
        self._load_provider_templates()

    def _load_provider_templates(self) -> None:
        """Load query templates from registered providers."""
        from .providers.registry import ProviderRegistry

        for provider in ProviderRegistry.all():
            # Merge SQL templates
            self.templates.update(provider.get_query_templates())

            # Merge template categories
            self._template_categories.update(provider.get_template_categories())

    def synthesize_query(
        self,
        hypothesis: SecurityHypothesis,
        use_pgq: bool = False,
    ) -> str:
        """Generate SQL/PGQ query from hypothesis.

        Args:
            hypothesis: Security hypothesis with patterns
            use_pgq: If True, use PGQ graph query instead of SQL

        Returns:
            Executable SQL/PGQ query string
        """
        if use_pgq:
            return self._synthesize_pgq_query(hypothesis)

        # Select appropriate template
        template = self._select_template(hypothesis.category)

        # Get defaults for this category
        defaults = get_category_defaults(hypothesis.category)

        # Use hypothesis patterns or defaults
        sinks = hypothesis.sink_patterns or defaults.get("default_sinks", [])
        sources = hypothesis.source_patterns or defaults.get("default_sources", [])
        sanitizers = hypothesis.sanitizer_patterns or defaults.get("default_sanitizers", [])

        # Format the query
        query = self._format_query(
            template=template,
            sinks=sinks,
            sources=sources,
            sanitizers=sanitizers,
            category=hypothesis.category,
        )

        # Store in hypothesis
        hypothesis.sql_query = query

        return query

    def synthesize_batch(
        self,
        hypotheses: List[SecurityHypothesis],
    ) -> List[Tuple[SecurityHypothesis, str]]:
        """Generate queries for a batch of hypotheses.

        Args:
            hypotheses: List of hypotheses

        Returns:
            List of (hypothesis, query) tuples
        """
        results = []
        for h in hypotheses:
            query = self.synthesize_query(h)
            results.append((h, query))
        return results

    def _select_template(self, category: str) -> str:
        """Select the appropriate SQL template for a category."""
        # First try exact category match
        if category in self.templates:
            return self.templates[category]

        # Try category config
        config = TEMPLATE_CATEGORIES.get(category)
        if config:
            template_name = config.get("template", "buffer_overflow")
            return self.templates.get(template_name, self.templates["buffer_overflow"])

        # Default to buffer_overflow
        return self.templates["buffer_overflow"]

    def _format_query(
        self,
        template: str,
        sinks: List[str],
        sources: List[str],
        sanitizers: List[str],
        category: str,
    ) -> str:
        """Format query template with actual values."""
        # Format sink list
        sinks_sql = ", ".join(f"'{s}'" for s in sinks) if sinks else "''"

        # Format source list
        sources_sql = ", ".join(f"'{s}'" for s in sources) if sources else "''"

        # Format sanitizer list
        sanitizers_sql = ", ".join(f"'{s}'" for s in sanitizers) if sanitizers else "''"

        # Build sanitizer conditions (for LIKE patterns)
        sanitizer_conditions = self._build_sanitizer_conditions(sanitizers)

        # Build sink conditions (for method name LIKE patterns)
        sink_conditions = self._build_sink_conditions(sinks, category)

        # Replace placeholders
        query = template.format(
            sinks=sinks_sql,
            sources=sources_sql,
            sanitizers=sanitizers_sql,
            sanitizer_conditions=sanitizer_conditions,
            sink_conditions=sink_conditions,
        )

        return query.strip()

    def _build_sanitizer_conditions(self, sanitizers: List[str]) -> str:
        """Build SQL conditions for sanitizer checks."""
        if not sanitizers:
            return "1=0"  # Never match if no sanitizers

        conditions = []
        for san in sanitizers:
            # Handle both function names and pattern matches
            if san.startswith('%') or san.endswith('%'):
                conditions.append(f"cs.code LIKE '{san}'")
            elif '=' in san or '<' in san or '>' in san:
                # Comparison patterns like "= NULL", "> MAX"
                conditions.append(f"cs.code LIKE '%{san}%'")
            else:
                # Function name
                conditions.append(f"cs.code LIKE '%{san}%'")

        return " OR ".join(conditions)

    def _build_sink_conditions(self, sinks: List[str], category: str) -> str:
        """Build SQL conditions for sink matching."""
        if not sinks:
            # Category-specific default patterns
            if category == "information_disclosure":
                return "m.name LIKE '%statistic%' OR m.name LIKE '%sample%' OR m.name LIKE '%analyze%'"
            return "1=1"

        conditions = []
        for sink in sinks:
            if '%' in sink:
                conditions.append(f"m.name LIKE '{sink}'")
            else:
                conditions.append(f"m.name = '{sink}'")

        return " OR ".join(conditions)

    def _synthesize_pgq_query(self, hypothesis: SecurityHypothesis) -> str:
        """Generate PGQ graph query for hypothesis."""
        # Use taint_flow_path template by default
        template = self.pgq_templates.get("taint_flow_path", "")

        sinks = hypothesis.sink_patterns or []
        sources = hypothesis.source_patterns or []
        sanitizers = hypothesis.sanitizer_patterns or []

        sinks_sql = ", ".join(f"'{s}'" for s in sinks) if sinks else "''"
        sources_sql = ", ".join(f"'{s}'" for s in sources) if sources else "''"
        sanitizers_sql = ", ".join(f"'{s}'" for s in sanitizers) if sanitizers else "''"

        query = template.format(
            sinks=sinks_sql,
            sources=sources_sql,
            sanitizers=sanitizers_sql,
        )

        return query.strip()

    def create_custom_query(
        self,
        template_name: str,
        sinks: List[str],
        sources: List[str],
        sanitizers: Optional[List[str]] = None,
        extra_conditions: Optional[str] = None,
    ) -> str:
        """Create a custom query from a specific template.

        Args:
            template_name: Name of SQL or PGQ template
            sinks: List of sink function names
            sources: List of source function names
            sanitizers: Optional list of sanitizer function names
            extra_conditions: Optional additional WHERE conditions

        Returns:
            Formatted SQL query
        """
        # Try SQL template first
        template = self.templates.get(template_name)
        if not template:
            # Try PGQ template
            template = self.pgq_templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        sanitizers = sanitizers or []

        query = self._format_query(
            template=template,
            sinks=sinks,
            sources=sources,
            sanitizers=sanitizers,
            category=template_name,
        )

        # Add extra conditions if provided
        if extra_conditions:
            # Insert before ORDER BY if present
            if "ORDER BY" in query:
                parts = query.split("ORDER BY")
                query = f"{parts[0]}AND ({extra_conditions})\nORDER BY{parts[1]}"
            else:
                query = f"{query}\nAND ({extra_conditions})"

        return query


def synthesize_queries_for_batch(
    hypotheses: List[SecurityHypothesis],
) -> List[SecurityHypothesis]:
    """Convenience function to synthesize queries for a batch of hypotheses.

    Args:
        hypotheses: List of hypotheses

    Returns:
        Same list with sql_query field populated
    """
    synthesizer = QuerySynthesizer()
    for h in hypotheses:
        if not h.sql_query:  # Don't overwrite CVE-specific queries
            synthesizer.synthesize_query(h)
    return hypotheses
