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
        """Return PostgreSQL-specific SQL query templates.

        SCHEMA: Uses call_graph, call_containment, nodes_method, nodes_call
        (NOT edges_ast/edges_cfg which are empty in cpg.duckdb)
        """
        return {
            "pg_dump_injection": """
        -- CVE-2025-8714/CVE-2025-8715: pg_dump injection
        -- Find output functions in pg_dump receiving database data without escaping
        SELECT DISTINCT
            nc.id,
            nc.name AS sink_function,
            nc.code,
            nc.filename,
            nc.line_number,
            nm.name AS containing_method
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.containing_method_id = nm.id
        WHERE nc.filename LIKE '%pg_dump%'
        AND nc.name IN ({sinks})
        -- Method receives data from database source
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        -- Not properly escaped with fmtId or similar
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ('fmtId', 'fmtQualifiedId', 'quote_identifier', 'appendStringLiteralConn')
        )
        ORDER BY nc.filename, nc.line_number;
    """,
            "spi_sql_injection": """
        -- PostgreSQL SPI SQL Injection
        -- Find SPI calls with dynamically constructed queries
        SELECT DISTINCT
            nc.id,
            nc.name AS sink_function,
            nc.code,
            nc.filename,
            nc.line_number,
            nm.name AS containing_method
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.containing_method_id = nm.id
        WHERE nc.name IN ({sinks})
        -- Dynamic query construction
        AND (nc.code LIKE '%+%' OR nc.code LIKE '%psprintf%' OR nc.code LIKE '%appendStringInfo%')
        -- Not using quote functions
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ('quote_literal', 'quote_identifier', 'SPI_execute_with_args')
        )
        ORDER BY nc.filename, nc.line_number;
    """,
            "statistics_disclosure": """
        -- CVE-2025-8713: Statistics data leakage
        -- Find statistics/analyze functions without ACL checks
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'Statistics access without ACL' AS issue
        FROM nodes_method nm
        WHERE nm.filename LIKE '%analyze%'
        AND (nm.name LIKE '%statistic%' OR nm.name LIKE '%sample%' OR nm.name LIKE '%analyze%')
        -- No ACL check in the method
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN (
                'pg_class_aclcheck', 'has_table_privilege', 'check_enable_rls',
                'pg_attribute_aclcheck', 'has_column_privilege', 'pg_class_aclmask'
            )
        )
        ORDER BY nm.filename, nm.line_number;
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
