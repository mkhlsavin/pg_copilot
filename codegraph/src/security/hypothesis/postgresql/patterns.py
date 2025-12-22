"""
PostgreSQL-specific vulnerability patterns.

Contains sink/source patterns and CVE-specific detection patterns
for PostgreSQL source code analysis.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


# =============================================================================
# pg_dump Patterns (CVE-2025-8714, CVE-2025-8715)
# =============================================================================

PG_DUMP_SINKS: List[str] = [
    # String buffer operations
    "appendPQExpBuffer",
    "appendPQExpBufferStr",
    "appendPQExpBufferChar",
    "appendStringInfo",
    "appendStringInfoString",
    "appendStringInfoChar",
    # psql command generation
    "printfPQExpBuffer",
    "resetPQExpBuffer",
    # Output writers
    "ahprintf",
    "ahwrite",
]

PG_DUMP_SOURCES: List[str] = [
    # Database queries returning object names
    "PQgetvalue",
    "PQfname",
    # Table/schema retrieval
    "getTables",
    "getTableAttrs",
    "getSchemas",
    "getTypes",
    "getFuncs",
    "getAggregates",
    "getOperators",
    "getIndexes",
    "getConstraints",
    "getTriggers",
    "getRules",
    # Name retrieval functions
    "get_attname",
    "get_relname",
    "get_namespace_name",
    "get_func_name",
]

PG_DUMP_SANITIZERS: List[str] = [
    "fmtId",                    # Identifier quoting
    "fmtQualifiedId",           # Schema.identifier quoting
    "fmtQualifiedDumpable",     # Full qualified name quoting
    "appendStringLiteralConn",  # String literal quoting
]


# =============================================================================
# SPI (Server Programming Interface) Patterns
# =============================================================================

PG_SPI_SINKS: List[str] = [
    "SPI_execute",
    "SPI_exec",
    "SPI_execute_with_args",
    "SPI_execute_plan",
    "SPI_execp",
    "SPI_cursor_open",
    "SPI_cursor_open_with_args",
    "SPI_prepare",
    "SPI_prepare_params",
]

PG_SPI_SOURCES: List[str] = [
    "SPI_getvalue",
    "SPI_getbinval",
    "SPI_getrelname",
    "SPI_gettypeid",
    "SPI_getargtypeid",
    "SPI_gettype",
    "SPI_getnspname",
    "DatumGetCString",
    "TextDatumGetCString",
]

PG_SPI_SANITIZERS: List[str] = [
    "quote_literal",
    "quote_identifier",
    "quote_literal_cstr",
    "quote_nullable",
    "SPI_execute_with_args",  # Safe when using parameters
]


# =============================================================================
# libpq Patterns
# =============================================================================

PG_LIBPQ_SINKS: List[str] = [
    "PQexec",
    "PQexecParams",
    "PQprepare",
    "PQexecPrepared",
    "PQsendQuery",
    "PQsendQueryParams",
]

PG_LIBPQ_SOURCES: List[str] = [
    "PQgetvalue",
    "PQfname",
    "PQcmdTuples",
    "PQgetResult",
]

PG_LIBPQ_SANITIZERS: List[str] = [
    "PQescapeIdentifier",
    "PQescapeLiteral",
    "PQescapeString",
    "PQescapeByteaConn",
    "PQexecParams",  # Safe with parameters
]


# =============================================================================
# ACL (Access Control List) Functions
# =============================================================================

PG_ACL_FUNCTIONS: List[str] = [
    # Table-level checks
    "pg_class_aclcheck",
    "pg_class_aclmask",
    "has_table_privilege",
    "has_table_privilege_name",
    "has_table_privilege_id",
    # Column-level checks
    "pg_attribute_aclcheck",
    "pg_attribute_aclmask",
    "has_column_privilege",
    # Schema checks
    "pg_namespace_aclcheck",
    "has_schema_privilege",
    # Function checks
    "pg_proc_aclcheck",
    "has_function_privilege",
    # Type checks
    "pg_type_aclcheck",
    "has_type_privilege",
    # Sequence checks
    "pg_sequence_aclcheck",
    # Database checks
    "pg_database_aclcheck",
    "has_database_privilege",
    # Row-level security
    "check_enable_rls",
    "row_security_active",
]


# =============================================================================
# CVE-Specific Patterns
# =============================================================================

@dataclass
class CVEPattern:
    """Pattern for detecting a specific CVE."""
    cve_id: str
    description: str
    affected_versions: List[str]
    fixed_versions: List[str]
    cwes: List[str]
    sinks: List[str]
    sources: List[str]
    sanitizers: List[str]
    affected_files: List[str]
    detection_query: str
    fix_description: str = ""


POSTGRESQL_CVE_PATTERNS: Dict[str, CVEPattern] = {
    "CVE-2025-8713": CVEPattern(
        cve_id="CVE-2025-8713",
        description="Optimizer statistics data leakage - pg_statistic access without proper ACL checks allows unauthorized users to infer table data through statistics.",
        affected_versions=["17.0", "17.1", "17.2", "17.3", "17.4", "17.5"],
        fixed_versions=["17.6"],
        cwes=["CWE-200", "CWE-862"],
        sinks=["pg_statistic", "stavalues", "stanumbers", "RelationGetStatisticsRelation"],
        sources=["analyze_rel", "do_analyze_rel", "acquire_sample_rows", "compute_scalar_stats"],
        sanitizers=PG_ACL_FUNCTIONS,
        affected_files=[
            "src/backend/commands/analyze.c",
            "src/backend/optimizer/util/plancat.c",
            "src/backend/utils/adt/selfuncs.c",
        ],
        detection_query="""
            -- CVE-2025-8713: Statistics access without ACL check
            SELECT DISTINCT
                m.id,
                m.full_name,
                m.filename,
                m.line_number,
                'Statistics access without ACL check' AS issue
            FROM nodes_method m
            WHERE (
                m.name LIKE '%statistic%'
                OR m.name LIKE '%sample%'
                OR m.name LIKE '%analyze%'
            )
            AND NOT EXISTS (
                SELECT 1 FROM nodes_call acl_check
                JOIN edges_ast ea ON ea.src = m.id AND ea.dst = acl_check.id
                WHERE acl_check.name IN (
                    'pg_class_aclcheck', 'has_table_privilege',
                    'check_enable_rls', 'pg_attribute_aclcheck'
                )
            )
            ORDER BY m.filename, m.line_number;
        """,
        fix_description="Add ACL checks before accessing pg_statistic data",
    ),

    "CVE-2025-8714": CVEPattern(
        cve_id="CVE-2025-8714",
        description="pg_dump remote code execution - Untrusted database object names can inject arbitrary commands during pg_dump restore due to insufficient escaping.",
        affected_versions=["17.0", "17.1", "17.2", "17.3", "17.4", "17.5"],
        fixed_versions=["17.6"],
        cwes=["CWE-94", "CWE-78"],
        sinks=PG_DUMP_SINKS,
        sources=PG_DUMP_SOURCES,
        sanitizers=PG_DUMP_SANITIZERS,
        affected_files=[
            "src/bin/pg_dump/pg_dump.c",
            "src/bin/pg_dump/pg_backup_archiver.c",
            "src/bin/pg_dump/pg_backup_custom.c",
            "src/bin/pg_dump/pg_backup_tar.c",
        ],
        detection_query="""
            -- CVE-2025-8714: pg_dump injection via object names
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
            WHERE c.name IN ('appendPQExpBuffer', 'appendStringInfo', 'appendPQExpBufferStr')
            AND c.filename LIKE '%pg_dump%'
            AND src.name IN ('PQgetvalue', 'PQfname', 'getTables', 'getTableAttrs')
            AND c.code NOT LIKE '%fmtId%'
            AND c.code NOT LIKE '%fmtQualifiedId%'
            ORDER BY c.filename, c.line_number;
        """,
        fix_description="Use fmtId() or fmtQualifiedId() for all database object names",
    ),

    "CVE-2025-8715": CVEPattern(
        cve_id="CVE-2025-8715",
        description="pg_dump newline injection - Newlines in database object names can break psql meta-commands during restore, potentially leading to code injection.",
        affected_versions=["17.0", "17.1", "17.2", "17.3", "17.4", "17.5"],
        fixed_versions=["17.6"],
        cwes=["CWE-94", "CWE-93"],
        sinks=["appendPQExpBuffer", "ahprintf", "appendStringInfo"],
        sources=PG_DUMP_SOURCES,
        sanitizers=["replace_newline", "escape_newline"] + PG_DUMP_SANITIZERS,
        affected_files=[
            "src/bin/pg_dump/pg_dump.c",
            "src/bin/pg_dump/pg_backup_archiver.c",
        ],
        detection_query="""
            -- CVE-2025-8715: Newline injection in pg_dump
            SELECT DISTINCT
                c.id,
                c.name AS sink_function,
                c.code,
                c.filename,
                c.line_number
            FROM nodes_call c
            WHERE c.name IN ('appendPQExpBuffer', 'ahprintf')
            AND c.filename LIKE '%pg_dump%'
            -- Looking for patterns where identifiers are output without newline handling
            AND (
                c.code LIKE '%\\c %'      -- psql connect command
                OR c.code LIKE '%\\copy%'  -- psql copy command
                OR c.code LIKE '%\\set%'   -- psql set command
            )
            AND c.code NOT LIKE '%replace%newline%'
            ORDER BY c.filename, c.line_number;
        """,
        fix_description="Escape or reject newlines in object names used in psql meta-commands",
    ),
}


def get_pg_pattern_for_cve(cve_id: str) -> Optional[CVEPattern]:
    """Get PostgreSQL CVE pattern by ID.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2025-8714")

    Returns:
        CVEPattern if found, None otherwise
    """
    return POSTGRESQL_CVE_PATTERNS.get(cve_id)


def get_all_pg_sinks() -> List[str]:
    """Get all PostgreSQL sink functions."""
    sinks = set()
    sinks.update(PG_DUMP_SINKS)
    sinks.update(PG_SPI_SINKS)
    sinks.update(PG_LIBPQ_SINKS)
    return sorted(sinks)


def get_all_pg_sources() -> List[str]:
    """Get all PostgreSQL source functions."""
    sources = set()
    sources.update(PG_DUMP_SOURCES)
    sources.update(PG_SPI_SOURCES)
    sources.update(PG_LIBPQ_SOURCES)
    return sorted(sources)


def get_all_pg_sanitizers() -> List[str]:
    """Get all PostgreSQL sanitizer functions."""
    sanitizers = set()
    sanitizers.update(PG_DUMP_SANITIZERS)
    sanitizers.update(PG_SPI_SANITIZERS)
    sanitizers.update(PG_LIBPQ_SANITIZERS)
    sanitizers.update(PG_ACL_FUNCTIONS)
    return sorted(sanitizers)
