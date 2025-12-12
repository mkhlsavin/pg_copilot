"""
DuckDB SQL/PGQ Query Templates for Security Analysis.

Contains parameterized query templates for detecting various vulnerability
patterns in Code Property Graphs stored in DuckDB.

IMPORTANT: All queries are in DuckDB SQL/PGQ syntax.
Joern is only used for CPG export, not for queries.
"""

from typing import Dict


# =============================================================================
# SQL Templates (Standard DuckDB SQL)
# =============================================================================

SQL_TEMPLATES: Dict[str, str] = {
    "buffer_overflow": """
        -- CWE-120: Buffer Copy without Checking Size of Input
        -- Find dangerous memory copy functions receiving tainted data without bounds check
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            m.full_name AS containing_method
        FROM nodes_call c
        JOIN edges_ast ea ON ea.dst = c.id
        JOIN nodes_method m ON ea.src = m.id
        WHERE c.name IN ({sinks})
        -- Check if tainted by external input via reaching definitions
        AND EXISTS (
            SELECT 1 FROM edges_reaching_def rd
            JOIN nodes_call src ON rd.src = src.id
            WHERE rd.dst = c.id
            AND src.name IN ({sources})
        )
        -- Exclude if bounds check exists in parent control structure
        AND NOT EXISTS (
            SELECT 1 FROM nodes_control_structure cs
            JOIN edges_ast a ON a.src = cs.id
            WHERE a.dst = c.id
            AND ({sanitizer_conditions})
        )
        ORDER BY c.filename, c.line_number;
    """,

    "command_injection": """
        -- CWE-78: OS Command Injection
        -- Find command execution with user-controlled input
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            src.name AS taint_source
        FROM nodes_call c
        JOIN edges_reaching_def rd ON rd.dst = c.id
        JOIN nodes_call src ON rd.src = src.id
        WHERE c.name IN ({sinks})
        AND src.name IN ({sources})
        -- Exclude if sanitization is present
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call san
            JOIN edges_reaching_def rd2 ON rd2.src = san.id AND rd2.dst = c.id
            WHERE san.name IN ({sanitizers})
        )
        ORDER BY c.filename, c.line_number;
    """,

    "format_string": """
        -- CWE-134: Use of Externally-Controlled Format String
        -- Find printf-family calls with user-controlled format argument
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ({sinks})
        -- First argument comes from external source
        AND EXISTS (
            SELECT 1 FROM edges_argument arg
            JOIN edges_reaching_def rd ON rd.dst = arg.dst
            JOIN nodes_call src ON rd.src = src.id
            WHERE arg.src = c.id
            AND src.name IN ({sources})
        )
        ORDER BY c.filename, c.line_number;
    """,

    "sql_injection": """
        -- CWE-89: SQL Injection
        -- Find SQL execution with dynamically constructed queries
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ({sinks})
        -- Query string appears to be dynamically constructed
        AND (c.code LIKE '%+%' OR c.code LIKE '%format%' OR c.code LIKE '%psprintf%')
        -- Not using proper quoting functions
        AND NOT ({sanitizer_conditions})
        ORDER BY c.filename, c.line_number;
    """,

    "code_injection": """
        -- CWE-94: Improper Control of Generation of Code
        -- Find code generation from untrusted input
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
        AND src.name IN ({sources})
        -- Not properly escaped
        AND NOT ({sanitizer_conditions})
        ORDER BY c.filename, c.line_number;
    """,

    "information_disclosure": """
        -- CWE-200: Exposure of Sensitive Information
        -- Find data access without authorization checks
        SELECT DISTINCT
            m.id,
            m.full_name,
            m.filename,
            m.line_number,
            'Missing ACL check' AS issue
        FROM nodes_method m
        WHERE ({sink_conditions})
        -- Method accesses data but doesn't check ACL
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call acl_check
            JOIN edges_ast ea ON ea.src = m.id AND ea.dst = acl_check.id
            WHERE acl_check.name IN ({sanitizers})
        )
        ORDER BY m.filename, m.line_number;
    """,

    "use_after_free": """
        -- CWE-416: Use After Free
        -- Find memory use after free operation
        SELECT DISTINCT
            use_call.id,
            use_call.code,
            use_call.filename,
            use_call.line_number,
            free_call.name AS free_function,
            free_call.line_number AS free_line
        FROM nodes_call free_call
        JOIN nodes_call use_call ON use_call.filename = free_call.filename
        WHERE free_call.name IN ({sinks})
        AND use_call.line_number > free_call.line_number
        -- Same variable used after free
        AND EXISTS (
            SELECT 1 FROM edges_reaching_def rd1, edges_reaching_def rd2
            WHERE rd1.dst = free_call.id
            AND rd2.dst = use_call.id
            AND rd1.variable = rd2.variable
        )
        ORDER BY use_call.filename, free_call.line_number;
    """,

    "integer_overflow": """
        -- CWE-190: Integer Overflow or Wraparound
        -- Find size calculations that may overflow
        SELECT DISTINCT
            c.id,
            c.name AS allocation_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ({sinks})
        -- Size argument involves multiplication without overflow check
        AND (c.code LIKE '%*%' OR c.code LIKE '%sizeof%*%')
        -- No overflow check nearby
        AND NOT EXISTS (
            SELECT 1 FROM nodes_control_structure cs
            JOIN edges_cfg cfg ON cfg.src = cs.id AND cfg.dst = c.id
            WHERE ({sanitizer_conditions})
        )
        ORDER BY c.filename, c.line_number;
    """,

    "null_pointer_deref": """
        -- CWE-476: NULL Pointer Dereference
        -- Find pointer dereference without null check
        SELECT DISTINCT
            c.id,
            c.code,
            c.filename,
            c.line_number,
            m.full_name AS containing_method
        FROM nodes_call c
        JOIN edges_ast ea ON ea.dst = c.id
        JOIN nodes_method m ON ea.src = m.id
        WHERE c.name IN ({sinks})
        -- No null check before dereference
        AND NOT EXISTS (
            SELECT 1 FROM nodes_control_structure cs
            JOIN edges_cfg cfg ON cfg.dst = c.id
            WHERE cs.code LIKE '%NULL%' OR cs.code LIKE '%!%'
        )
        ORDER BY c.filename, c.line_number;
    """,

    # PostgreSQL-specific templates moved to postgresql/provider.py
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
    # Universal C/C++ patterns - project-specific patterns from providers
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
        "default_sinks": [],  # Populated from providers
        "default_sources": ["getenv"],
        "default_sanitizers": [],  # Populated from providers
    },
    "code_injection": {
        "template": "code_injection",
        "default_sinks": [],  # Populated from providers
        "default_sources": [],
        "default_sanitizers": [],  # Populated from providers
    },
    "information_disclosure": {
        "template": "information_disclosure",
        "default_sinks": [],  # Uses sink_conditions
        "default_sources": [],
        "default_sanitizers": [],  # Populated from providers
    },
    "use_after_free": {
        "template": "use_after_free",
        "default_sinks": ["free"],  # Project-specific (pfree) from providers
        "default_sources": [],
        "default_sanitizers": ["= NULL"],
    },
    "integer_overflow": {
        "template": "integer_overflow",
        "default_sinks": ["malloc", "calloc", "realloc"],  # Project-specific (palloc) from providers
        "default_sources": [],
        "default_sanitizers": ["overflow", "> MAX"],
    },
    # PostgreSQL-specific categories moved to postgresql/provider.py
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
