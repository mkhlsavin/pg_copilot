"""
Injection Vulnerability Patterns

Patterns for detecting SQL injection, command injection, and related vulnerabilities.
CWE-78 (OS Command Injection), CWE-89 (SQL Injection)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_PATTERN = SecurityPattern(
    id="SQL_INJECTION_001",
    name="SQL Injection via Dynamic Query Execution",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL queries constructed using string concatenation with user input "
        "without proper sanitization or parameterization. Allows attackers to "
        "inject malicious SQL code. Includes SPI functions for dynamic SQL."
    ),
    cpgql_query="""
        -- Find dynamic SQL execution points (SPI functions) and string concat with SQL
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            nm.code,
            'SQL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_method nm
        WHERE nm.name IN ('SPI_execute', 'SPI_exec', 'SPI_execute_with_args',
                          'SPI_execute_plan', 'SPI_execp', 'SPI_execute_extended',
                          'exec_simple_query', 'pg_parse_query')
        UNION
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SQL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('strcat', 'strncat', 'sprintf', 'snprintf', 'strdup')
          AND (nc.code LIKE '%SELECT%'
            OR nc.code LIKE '%INSERT%'
            OR nc.code LIKE '%UPDATE%'
            OR nc.code LIKE '%DELETE%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use parameterized queries (prepared statements)\n"
        "2. Use ORM with built-in sanitization\n"
        "3. Validate and sanitize all user inputs\n"
        "4. Apply principle of least privilege to database accounts"
    ),
    example_code="""
        // VULNERABLE
        char query[256];
        sprintf(query, "SELECT * FROM users WHERE name='%s'", user_input);
        exec_simple_query(query);

        // SECURE
        const char *values[1] = {user_input};
        exec_params_query("SELECT * FROM users WHERE name=$1", 1, values);
    """,
    test_cases=[
        {
            "name": "SQL concatenation with SELECT",
            "method": "build_user_query",
            "expected": True,
            "contains": ["sprintf", "SELECT"]
        },
        {
            "name": "Parameterized query",
            "method": "safe_user_query",
            "expected": False,
            "contains": ["exec_params"]
        }
    ]
)


COMMAND_INJECTION_PATTERN = SecurityPattern(
    id="CMD_INJECTION_001",
    name="Command Injection via system/exec",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Execution of shell commands constructed from user input without proper "
        "validation. Allows attackers to execute arbitrary system commands."
    ),
    cpgql_query="""
        -- Find call sites to system/exec functions with string operations
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'COMMAND_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('system', 'popen', 'exec', 'execl', 'execlp',
                          'execle', 'execv', 'execvp', 'execvpe')
          AND (nc.code LIKE '%strcat%'
            OR nc.code LIKE '%sprintf%'
            OR nc.code LIKE '%strcpy%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-78", "CWE-88"],
    remediation=(
        "1. Avoid shell command execution when possible\n"
        "2. Use language APIs instead of system calls\n"
        "3. Validate input against strict whitelist\n"
        "4. Use execve() with argument arrays instead of system()\n"
        "5. Never pass user input directly to shell"
    ),
    example_code="""
        // VULNERABLE
        char cmd[256];
        sprintf(cmd, "pg_dump %s", database_name);
        system(cmd);

        // SECURE
        char *args[] = {"pg_dump", database_name, NULL};
        execve("/usr/bin/pg_dump", args, NULL);
    """,
    test_cases=[
        {
            "name": "system() with concatenation",
            "method": "backup_database",
            "expected": True,
            "contains": ["system", "sprintf"]
        }
    ]
)


# Registry of injection patterns
INJECTION_PATTERNS: Dict[str, SecurityPattern] = {
    "SQL_INJECTION": SQL_INJECTION_PATTERN,
    "COMMAND_INJECTION": COMMAND_INJECTION_PATTERN,
}
