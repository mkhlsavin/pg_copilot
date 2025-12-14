"""
DuckDB SQL/PGQ Query Templates for Security Analysis.

Contains parameterized query templates for detecting various vulnerability
patterns in Code Property Graphs stored in DuckDB.

IMPORTANT: All queries are in DuckDB SQL/PGQ syntax.
Joern is only used for CPG export, not for queries.

SCHEMA NOTES (cpg.duckdb):
- nodes_method: id, name, full_name, filename, line_number, line_number_end
- nodes_call: id, name, code, filename, line_number, containing_method_id, containing_method_name
- call_graph: caller_id, callee_id, caller_name, callee_name, call_line, call_file
- call_containment: outer_method_id, inner_call_id, inner_name, depth
- edges_reaching_def: src, dst, variable (limited - 945 records)
- edges_tagged_by: src, dst (751K records for metrics)

Empty tables (not used): edges_ast, edges_cfg, nodes_control_structure
"""

from typing import Dict


# =============================================================================
# SQL Templates (Adapted for cpg.duckdb schema)
# =============================================================================

SQL_TEMPLATES: Dict[str, str] = {
    "buffer_overflow": """
        -- CWE-120: Buffer Copy without Checking Size of Input
        -- Find dangerous memory copy functions in methods that receive external data
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
        -- Method calls a source function (receives external data)
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        -- No sanitizer function called in the same method
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "command_injection": """
        -- CWE-78: OS Command Injection
        -- Find command execution in methods with external input
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
        -- Method receives data from source
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        -- No sanitization in the method
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "format_string": """
        -- CWE-134: Use of Externally-Controlled Format String
        -- Find printf-family calls in methods with user input
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
        -- Method has external input source
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "sql_injection": """
        -- CWE-89: SQL Injection
        -- Find SQL execution with dynamically constructed queries
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
        -- Query appears to be dynamically constructed
        AND (nc.code LIKE '%+%' OR nc.code LIKE '%format%' OR nc.code LIKE '%psprintf%')
        -- Not using proper quoting functions
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "code_injection": """
        -- CWE-94: Improper Control of Generation of Code
        -- Find code output functions receiving unescaped database data
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
        -- Method receives data from source (e.g., database)
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        -- Not properly escaped
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "information_disclosure": """
        -- CWE-200: Exposure of Sensitive Information
        -- Find data access methods without authorization checks
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'Missing ACL check' AS issue
        FROM nodes_method nm
        WHERE ({sink_conditions})
        -- Method does NOT call ACL check functions
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nm.filename, nm.line_number;
    """,

    "use_after_free": """
        -- CWE-416: Use After Free
        -- Find memory use after free in the same file
        SELECT DISTINCT
            use_call.id,
            use_call.code,
            use_call.filename,
            use_call.line_number,
            free_call.name AS free_function,
            free_call.line_number AS free_line
        FROM nodes_call free_call
        JOIN nodes_call use_call ON use_call.filename = free_call.filename
            AND use_call.containing_method_id = free_call.containing_method_id
        WHERE free_call.name IN ({sinks})
        AND use_call.line_number > free_call.line_number
        AND use_call.line_number < free_call.line_number + 50
        ORDER BY use_call.filename, free_call.line_number;
    """,

    "integer_overflow": """
        -- CWE-190: Integer Overflow or Wraparound
        -- Find size calculations that may overflow
        SELECT DISTINCT
            nc.id,
            nc.name AS allocation_function,
            nc.code,
            nc.filename,
            nc.line_number,
            nm.name AS containing_method
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.containing_method_id = nm.id
        WHERE nc.name IN ({sinks})
        -- Size argument involves multiplication
        AND (nc.code LIKE '%*%' OR nc.code LIKE '%sizeof%*%')
        -- No overflow check in the method
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND (cc.inner_name LIKE '%overflow%' OR cc.inner_name LIKE '%check%size%')
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "null_pointer_deref": """
        -- CWE-476: NULL Pointer Dereference
        -- Find pointer operations without null checks in the method
        SELECT DISTINCT
            nc.id,
            nc.code,
            nc.filename,
            nc.line_number,
            nm.name AS containing_method
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.containing_method_id = nm.id
        WHERE nc.name IN ({sinks})
        ORDER BY nc.filename, nc.line_number;
    """,

    # ==========================================================================
    # PostgreSQL-specific templates (for direct use with cpg.duckdb)
    # ==========================================================================

    "pg_dump_injection": """
        -- CVE-2025-8714, CVE-2025-8715: pg_dump code injection
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
        -- Method receives data from database
        AND EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sources})
        )
        -- Not properly escaped with fmtId or similar
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "spi_sql_injection": """
        -- SPI SQL Injection in PostgreSQL
        -- Find SPI execution without proper quoting
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
        -- Dynamic query construction detected
        AND (nc.code LIKE '%+%' OR nc.code LIKE '%psprintf%' OR nc.code LIKE '%appendStringInfo%')
        -- Not using quote functions
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nc.filename, nc.line_number;
    """,

    "statistics_disclosure": """
        -- CVE-2025-8713: Statistics data leakage
        -- Find analyze/statistics methods without ACL checks
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'Missing ACL check for statistics access' AS issue
        FROM nodes_method nm
        WHERE nm.filename LIKE '%analyze%'
        AND (
            nm.name LIKE '%statistic%'
            OR nm.name LIKE '%sample%'
            OR nm.name LIKE '%analyze%'
            OR nm.name LIKE '%compute%stats%'
        )
        -- No ACL check in the method
        AND NOT EXISTS (
            SELECT 1 FROM call_containment cc
            WHERE cc.outer_method_id = nm.id
            AND cc.inner_name IN ({sanitizers})
        )
        ORDER BY nm.filename, nm.line_number;
    """,

    # ==========================================================================
    # Simplified fallback templates (when complex queries fail)
    # ==========================================================================

    "simple_sink_search": """
        -- Simple: Find all calls to sink functions
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nc.code,
            nc.filename,
            nc.line_number,
            nc.containing_method_name
        FROM nodes_call nc
        WHERE nc.name IN ({sinks})
        ORDER BY nc.filename, nc.line_number
        LIMIT 500;
    """,

    "simple_file_functions": """
        -- Simple: Find all methods in a specific file
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            nm.line_number_end
        FROM nodes_method nm
        WHERE nm.filename LIKE {file_pattern}
        ORDER BY nm.line_number;
    """,

    "call_graph_analysis": """
        -- Find call relationships for specific functions
        SELECT DISTINCT
            cg.caller_name,
            cg.callee_name,
            cg.call_line,
            cg.call_file
        FROM call_graph cg
        WHERE cg.caller_name IN ({functions})
           OR cg.callee_name IN ({functions})
        ORDER BY cg.call_file, cg.call_line
        LIMIT 500;
    """,

    "method_calls_in_function": """
        -- Find all calls within a specific method
        SELECT DISTINCT
            cc.inner_name AS called_function,
            cc.depth,
            nm.name AS in_method,
            nm.filename
        FROM call_containment cc
        JOIN nodes_method nm ON cc.outer_method_id = nm.id
        WHERE nm.name = {method_name}
        ORDER BY cc.depth, cc.inner_name;
    """,

    # ==========================================================================
    # Method-based templates (for incomplete nodes_call coverage)
    # These use nodes_method when nodes_call is not available for certain files
    # ==========================================================================

    "method_cve_8713_statistics": """
        -- CVE-2025-8713: Find methods accessing statistics without ACL
        -- Works with nodes_method when nodes_call unavailable
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'Statistics/analyze method - potential data leakage' AS issue
        FROM nodes_method nm
        WHERE (
            nm.filename LIKE '%analyze.c'
            OR nm.filename LIKE '%selfuncs.c'
            OR nm.filename LIKE '%plancat.c'
        )
        AND (
            nm.name LIKE '%statistic%'
            OR nm.name LIKE '%sample%'
            OR nm.name LIKE '%analyze%'
            OR nm.name LIKE '%estimate%'
            OR nm.name LIKE '%selectivity%'
        )
        ORDER BY nm.filename, nm.line_number;
    """,

    "method_cve_8714_pg_dump": """
        -- CVE-2025-8714: Find pg_dump methods that may handle identifiers
        -- Works with nodes_method when nodes_call unavailable
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'pg_dump method - check for identifier escaping' AS issue
        FROM nodes_method nm
        WHERE (
            nm.filename LIKE '%pg_dump.c'
            OR nm.filename LIKE '%pg_backup%'
            OR nm.filename LIKE '%dumputils%'
        )
        AND (
            nm.name LIKE '%dump%'
            OR nm.name LIKE '%write%'
            OR nm.name LIKE '%output%'
            OR nm.name LIKE '%print%'
            OR nm.name LIKE '%append%'
        )
        ORDER BY nm.filename, nm.line_number;
    """,

    "method_cve_8715_newline": """
        -- CVE-2025-8715: Find pg_dump methods generating psql commands
        -- Works with nodes_method when nodes_call unavailable
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'pg_dump command generation - check newline handling' AS issue
        FROM nodes_method nm
        WHERE (
            nm.filename LIKE '%pg_dump.c'
            OR nm.filename LIKE '%pg_backup_archiver.c'
        )
        AND (
            nm.name LIKE '%cmd%'
            OR nm.name LIKE '%Cmd%'
            OR nm.name LIKE '%connect%'
            OR nm.name LIKE '%copy%'
            OR nm.name LIKE '%restore%'
        )
        ORDER BY nm.filename, nm.line_number;
    """,

    "method_dangerous_patterns": """
        -- Find methods with dangerous patterns in code (if code field available)
        SELECT DISTINCT
            nm.id,
            nm.name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'Dangerous pattern in method code' AS issue
        FROM nodes_method nm
        WHERE nm.filename LIKE {file_pattern}
        AND nm.code IS NOT NULL
        AND (
            nm.code LIKE '%strcpy%'
            OR nm.code LIKE '%sprintf%'
            OR nm.code LIKE '%system(%'
            OR nm.code LIKE '%PQgetvalue%'
        )
        ORDER BY nm.filename, nm.line_number;
    """,
}


# =============================================================================
# PGQ Templates (DuckDB Graph Queries)
# =============================================================================

PGQ_TEMPLATES: Dict[str, str] = {
    "taint_flow_path": """
        -- Find complete taint flow paths from source to sink
        -- Requires duckpgq extension and cpg property graph
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (source:CALL_NODE)-[:REACHING_DEF*1..10]->(sink:CALL_NODE)
            WHERE source.name IN ({sources})
              AND sink.name IN ({sinks})
            COLUMNS (
                source.name AS source_func,
                source.filename AS source_file,
                source.line_number AS source_line,
                sink.name AS sink_func,
                sink.filename AS sink_file,
                sink.line_number AS sink_line
            )
        )
        LIMIT 100;
    """,

    "call_chain_to_sink": """
        -- Find call chains leading to dangerous functions
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (caller:METHOD)-[:AST]->(call:CALL_NODE)-[:CALLS]->(callee:METHOD)
                  -[:AST]->(nested:CALL_NODE)
            WHERE nested.name IN ({sinks})
            COLUMNS (
                caller.full_name AS entry_method,
                callee.full_name AS intermediate_method,
                nested.name AS sink_function,
                nested.filename AS file,
                nested.line_number AS line
            )
        );
    """,

    "control_dependent_flow": """
        -- Find data flows that are control-dependent on conditions
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (cond:CONTROL_STRUCTURE)-[:CDG]->(stmt:CPG_NODE)
                  -[:REACHING_DEF]->(sink:CALL_NODE)
            WHERE sink.name IN ({sinks})
            COLUMNS (
                cond.code AS condition,
                sink.name AS sink_func,
                sink.line_number AS line
            )
        );
    """,

    "unsanitized_path": """
        -- Find taint paths that bypass sanitizers
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH path = (source:CALL_NODE)-[:REACHING_DEF*1..8]->(sink:CALL_NODE)
            WHERE source.name IN ({sources})
              AND sink.name IN ({sinks})
              -- No sanitizer on the path
              AND NOT EXISTS {{
                  MATCH (source)-[:REACHING_DEF*]->(san:CALL_NODE)-[:REACHING_DEF*]->(sink)
                  WHERE san.name IN ({sanitizers})
              }}
            COLUMNS (
                source.name AS source,
                sink.name AS sink,
                source.filename AS file,
                source.line_number AS start_line,
                sink.line_number AS end_line
            )
        )
        LIMIT 50;
    """,
}


# =============================================================================
# Template Categories and Defaults
# =============================================================================

TEMPLATE_CATEGORIES = {
    # Universal C/C++ patterns
    "buffer_overflow": {
        "template": "buffer_overflow",
        "default_sinks": ["strcpy", "strcat", "memcpy", "sprintf", "gets"],
        "default_sources": ["recv", "read", "fgets", "getenv"],
        "default_sanitizers": ["strlcpy", "snprintf", "sizeof"],
    },
    "command_injection": {
        "template": "command_injection",
        "default_sinks": ["system", "popen", "execl", "execv", "execve", "execvp"],
        "default_sources": ["getenv", "fgets"],
        "default_sanitizers": ["sanitize", "escape_shell", "quote_argument"],
    },
    "format_string": {
        "template": "format_string",
        "default_sinks": ["printf", "fprintf", "sprintf", "snprintf", "syslog"],
        "default_sources": ["fgets", "read", "getenv"],
        "default_sanitizers": [],  # Format strings must be literals
    },
    "sql_injection": {
        "template": "sql_injection",
        "default_sinks": ["SPI_execute", "SPI_exec", "PQexec"],
        "default_sources": ["getenv", "SPI_getvalue"],
        "default_sanitizers": ["quote_literal", "quote_identifier"],
    },
    "code_injection": {
        "template": "code_injection",
        "default_sinks": ["appendPQExpBuffer", "appendStringInfo"],
        "default_sources": ["PQgetvalue", "SPI_getvalue"],
        "default_sanitizers": ["fmtId", "quote_identifier"],
    },
    "information_disclosure": {
        "template": "information_disclosure",
        "default_sinks": [],  # Uses sink_conditions
        "default_sources": [],
        "default_sanitizers": ["pg_class_aclcheck", "has_table_privilege"],
    },
    "use_after_free": {
        "template": "use_after_free",
        "default_sinks": ["pfree", "free", "ReleaseSysCache"],
        "default_sources": [],
        "default_sanitizers": [],
    },
    "integer_overflow": {
        "template": "integer_overflow",
        "default_sinks": ["palloc", "palloc0", "malloc", "calloc", "realloc", "repalloc"],
        "default_sources": [],
        "default_sanitizers": [],
    },

    # ==========================================================================
    # PostgreSQL-specific categories (CVE detection)
    # ==========================================================================
    "pg_dump_injection": {
        "template": "pg_dump_injection",
        "default_sinks": [
            "appendPQExpBuffer", "appendPQExpBufferStr", "appendPQExpBufferChar",
            "appendStringInfo", "appendStringInfoString", "appendStringInfoChar",
            "ahprintf", "ahwrite", "printfPQExpBuffer",
        ],
        "default_sources": [
            "PQgetvalue", "PQfname", "getTables", "getTableAttrs",
            "getSchemas", "getTypes", "getFuncs", "get_attname", "get_relname",
        ],
        "default_sanitizers": [
            "fmtId", "fmtQualifiedId", "fmtQualifiedDumpable",
            "appendStringLiteralConn", "quote_identifier",
        ],
    },
    "spi_sql_injection": {
        "template": "spi_sql_injection",
        "default_sinks": [
            "SPI_execute", "SPI_exec", "SPI_execute_plan",
            "SPI_execp", "SPI_execute_with_args",
        ],
        "default_sources": [
            "SPI_getvalue", "SPI_getbinval", "SPI_gettype", "SPI_gettypeid",
        ],
        "default_sanitizers": [
            "quote_literal", "quote_literal_cstr", "quote_identifier",
            "quote_qualified_identifier",
        ],
    },
    "statistics_disclosure": {
        "template": "statistics_disclosure",
        "default_sinks": [],  # Uses method name matching
        "default_sources": [],
        "default_sanitizers": [
            "pg_class_aclcheck", "pg_attribute_aclcheck",
            "has_table_privilege", "has_column_privilege",
            "check_enable_rls", "pg_class_aclmask",
        ],
    },

    # Fallback templates
    "simple_sink_search": {
        "template": "simple_sink_search",
        "default_sinks": [],
        "default_sources": [],
        "default_sanitizers": [],
    },
}


def get_template(category: str) -> str:
    """Get SQL template for a category."""
    config = TEMPLATE_CATEGORIES.get(category)
    if config:
        return SQL_TEMPLATES.get(config["template"], SQL_TEMPLATES["buffer_overflow"])
    return SQL_TEMPLATES.get(category, SQL_TEMPLATES["buffer_overflow"])


def get_pgq_template(name: str) -> str:
    """Get PGQ template by name."""
    return PGQ_TEMPLATES.get(name, "")


def get_category_defaults(category: str) -> Dict:
    """Get default sinks/sources/sanitizers for a category."""
    return TEMPLATE_CATEGORIES.get(category, {
        "template": "buffer_overflow",
        "default_sinks": [],
        "default_sources": [],
        "default_sanitizers": [],
    })
