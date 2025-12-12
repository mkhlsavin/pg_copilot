"""
PostgreSQL Pattern Provider for Hypothesis Generation.

Provides PostgreSQL-specific security patterns, sinks, sources,
sanitizers, and SQL query templates for vulnerability detection.
"""

from typing import Any, Dict, List

from ..providers import PatternProvider, ProviderRegistry
from ..models import LanguagePattern

from .patterns import (
    PG_DUMP_SINKS,
    PG_DUMP_SOURCES,
    PG_DUMP_SANITIZERS,
    PG_SPI_SINKS,
    PG_SPI_SOURCES,
    PG_SPI_SANITIZERS,
    PG_LIBPQ_SINKS,
    PG_LIBPQ_SOURCES,
    PG_LIBPQ_SANITIZERS,
    PG_ACL_FUNCTIONS,
    POSTGRESQL_CVE_PATTERNS,
    CVEPattern,
)


class PostgreSQLPatternProvider(PatternProvider):
    """PostgreSQL-specific security pattern provider.

    Provides patterns for detecting vulnerabilities in PostgreSQL source code,
    including pg_dump injection, SPI SQL injection, libpq injection, and
    statistics disclosure vulnerabilities.
    """

    @property
    def name(self) -> str:
        """Provider name."""
        return "postgresql"

    @property
    def languages(self) -> List[str]:
        """Supported languages."""
        return ["C"]

    def get_sinks(self) -> Dict[str, List[str]]:
        """Return PostgreSQL-specific sink functions."""
        return {
            "memory_alloc": ["palloc", "palloc0", "repalloc", "pfree"],
            "pg_dump": list(PG_DUMP_SINKS),
            "spi": list(PG_SPI_SINKS),
            "libpq": list(PG_LIBPQ_SINKS),
        }

    def get_sources(self) -> Dict[str, List[str]]:
        """Return PostgreSQL-specific source functions."""
        return {
            "database": [
                "PQgetvalue", "PQfname", "PQgetlength",
                "SPI_getvalue", "SPI_getbinval",
                "DirectFunctionCall",
            ],
            "external_data": [
                "GetTableAttrs", "getTables", "getSchemas",
                "get_attname", "get_relname", "get_namespace_name",
            ],
            "spi": list(PG_SPI_SOURCES),
            "pg_dump": list(PG_DUMP_SOURCES),
        }

    def get_sanitizers(self) -> Dict[str, List[str]]:
        """Return PostgreSQL-specific sanitizer functions."""
        return {
            "safe_string": ["pstrdup"],
            "escaping": [
                "quote_identifier", "quote_literal",
                "fmtId", "fmtQualifiedId",
                "PQescapeIdentifier", "PQescapeLiteral",
            ],
            "acl_check": list(PG_ACL_FUNCTIONS),
            "spi": list(PG_SPI_SANITIZERS),
            "pg_dump": list(PG_DUMP_SANITIZERS),
        }

    def get_language_patterns(self) -> List[LanguagePattern]:
        """Return PostgreSQL-specific vulnerability patterns."""
        sources = self.get_sources()
        database_sources = sources["database"] + sources["external_data"]

        return [
            LanguagePattern(
                language="C",
                category="pg_dump_injection",
                sinks=list(PG_DUMP_SINKS),
                sources=database_sources,
                sanitizers=list(PG_DUMP_SANITIZERS),
                related_cwes=["CWE-94", "CWE-78"],
                description="Code injection via untrusted database object names in pg_dump",
            ),
            LanguagePattern(
                language="C",
                category="spi_sql_injection",
                sinks=list(PG_SPI_SINKS),
                sources=sources["database"] + sources["spi"],
                sanitizers=list(PG_SPI_SANITIZERS),
                related_cwes=["CWE-89"],
                description="SQL injection in SPI (Server Programming Interface) calls",
            ),
            LanguagePattern(
                language="C",
                category="statistics_disclosure",
                sinks=["pg_statistic", "stavalues", "stanumbers"],
                sources=["analyze_rel", "do_analyze_rel", "acquire_sample_rows"],
                sanitizers=list(PG_ACL_FUNCTIONS),
                related_cwes=["CWE-200", "CWE-862"],
                description="Information disclosure via optimizer statistics bypassing ACL",
            ),
            LanguagePattern(
                language="C",
                category="libpq_injection",
                sinks=list(PG_LIBPQ_SINKS),
                sources=sources["database"] + sources["external_data"],
                sanitizers=list(PG_LIBPQ_SANITIZERS),
                related_cwes=["CWE-89"],
                description="SQL injection via libpq client calls",
            ),
        ]

    def get_query_templates(self) -> Dict[str, str]:
        """Return PostgreSQL-specific SQL query templates."""
        return {
            "pg_dump_injection": """
        -- CVE-2025-8714/CVE-2025-8715: pg_dump injection
        -- Find object names flowing to output without proper escaping
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            src.name AS data_source
        FROM nodes_call c
        JOIN edges_reaching_def rd ON rd.dst = c.id
        JOIN nodes_call src ON rd.src = src.id
        WHERE c.name IN ({sinks})
        AND c.filename LIKE '%pg_dump%'
        AND src.name IN ({sources})
        -- Not properly escaped
        AND c.code NOT LIKE '%fmtId%'
        AND c.code NOT LIKE '%fmtQualifiedId%'
        AND c.code NOT LIKE '%quote_identifier%'
        ORDER BY c.filename, c.line_number;
    """,
            "spi_sql_injection": """
        -- PostgreSQL SPI SQL Injection
        -- Find SPI calls with dynamically constructed queries
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ({sinks})
        AND (c.code LIKE '%+%' OR c.code LIKE '%psprintf%' OR c.code LIKE '%appendStringInfo%')
        AND c.code NOT LIKE '%quote_literal%'
        AND c.code NOT LIKE '%quote_identifier%'
        AND c.code NOT LIKE '%SPI_execute_with_args%'
        ORDER BY c.filename, c.line_number;
    """,
            "statistics_disclosure": """
        -- CVE-2025-8713: Statistics data leakage
        -- Find statistics access without proper ACL checks
        SELECT DISTINCT
            m.id,
            m.full_name,
            m.filename,
            m.line_number,
            'Statistics access without ACL' AS issue
        FROM nodes_method m
        WHERE (m.name LIKE '%statistic%' OR m.name LIKE '%sample%' OR m.name LIKE '%analyze%')
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call acl_check
            JOIN edges_ast ea ON ea.src = m.id AND ea.dst = acl_check.id
            WHERE acl_check.name IN (
                'pg_class_aclcheck', 'has_table_privilege', 'check_enable_rls',
                'pg_attribute_aclcheck', 'has_column_privilege'
            )
        )
        ORDER BY m.filename, m.line_number;
    """,
        }

    def get_template_categories(self) -> Dict[str, Dict[str, Any]]:
        """Return PostgreSQL-specific template category configurations."""
        return {
            "pg_dump_injection": {
                "template": "pg_dump_injection",
                "default_sinks": list(PG_DUMP_SINKS)[:5],
                "default_sources": list(PG_DUMP_SOURCES)[:5],
                "default_sanitizers": list(PG_DUMP_SANITIZERS),
            },
            "spi_sql_injection": {
                "template": "spi_sql_injection",
                "default_sinks": list(PG_SPI_SINKS)[:5],
                "default_sources": list(PG_SPI_SOURCES)[:5],
                "default_sanitizers": list(PG_SPI_SANITIZERS),
            },
            "statistics_disclosure": {
                "template": "statistics_disclosure",
                "default_sinks": [],
                "default_sources": [],
                "default_sanitizers": list(PG_ACL_FUNCTIONS)[:5],
            },
        }

    def get_cve_patterns(self) -> Dict[str, CVEPattern]:
        """Return PostgreSQL CVE-specific detection patterns."""
        return POSTGRESQL_CVE_PATTERNS


# Auto-register the provider when this module is imported
_provider_instance = PostgreSQLPatternProvider()
ProviderRegistry.register(_provider_instance)
