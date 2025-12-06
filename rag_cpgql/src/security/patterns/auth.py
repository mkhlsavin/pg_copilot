"""
Authentication and Authorization Vulnerability Patterns

Patterns for detecting missing authentication, hardcoded credentials,
and privilege escalation vulnerabilities.

CWE-306 (Missing Auth), CWE-798 (Hardcoded Credentials), CWE-269 (Privilege Escalation)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


MISSING_AUTH_PATTERN = SecurityPattern(
    id="MISSING_AUTH_001",
    name="Missing Authentication for Critical Function",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Sensitive operations performed without authentication checks "
        "allow unauthorized access to privileged functionality."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'MISSING_AUTH' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('CreateRole', 'DropRole', 'AlterRole', 'GrantRole',
                          'delete_database', 'truncate_table', 'drop_table',
                          'modify_config', 'set_config', 'pg_reload_conf',
                          'setuid', 'seteuid', 'setgid')
          AND nc.method_full_name NOT LIKE 'test_%'
          AND nc.method_full_name NOT LIKE '%check%'
          AND nc.method_full_name NOT LIKE '%auth%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-306"],
    remediation=(
        "1. Add authentication checks before sensitive operations\n"
        "2. Implement role-based access control (RBAC)\n"
        "3. Use centralized authentication middleware\n"
        "4. Log all access to sensitive functions\n"
        "5. Implement principle of least privilege"
    ),
    example_code="""
        // VULNERABLE
        void drop_database(const char *dbname) {
            // No auth check!
            execute_sql("DROP DATABASE %s", dbname);
        }

        // SECURE
        void drop_database(const char *dbname, User *user) {
            if (!has_permission(user, PERM_DROP_DB))
                ereport(ERROR, "Permission denied");
            execute_sql("DROP DATABASE %s", dbname);
        }
    """,
    test_cases=[
        {"name": "drop without auth", "method": "drop_user_table", "expected": True, "contains": ["drop", "table"]}
    ]
)


HARDCODED_SECRETS_PATTERN = SecurityPattern(
    id="HARDCODED_SECRETS_001",
    name="Hardcoded Credentials/Secrets",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Hardcoded passwords, API keys, or other secrets in source code. These can be "
        "extracted from binaries or repositories, leading to unauthorized access."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nl.id,
            COALESCE(nm.name, 'unknown') AS method_name,
            COALESCE(nm.filename, 'unknown') AS filename,
            nl.line_number,
            nl.code,
            'HARDCODED_SECRET' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_literal nl
        LEFT JOIN edges_ast ea ON nl.id = ea.dst
        LEFT JOIN nodes_method nm ON ea.src = nm.id
        WHERE (LOWER(nl.code) LIKE '%password%'
            OR LOWER(nl.code) LIKE '%passwd%'
            OR LOWER(nl.code) LIKE '%secret%'
            OR LOWER(nl.code) LIKE '%api_key%'
            OR LOWER(nl.code) LIKE '%apikey%'
            OR LOWER(nl.code) LIKE '%private_key%'
            OR LOWER(nl.code) LIKE '%token%'
            OR LOWER(nl.code) LIKE '%credential%')
          AND nl.code LIKE '%=%'
          AND nl.code LIKE '%"%'
          AND COALESCE(nm.name, '') NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798", "CWE-259"],
    remediation=(
        "1. Use environment variables for secrets\n"
        "2. Use secure vault services (HashiCorp Vault, AWS Secrets Manager)\n"
        "3. Use configuration files with proper permissions (not in VCS)\n"
        "4. Implement credential rotation policies"
    ),
    example_code="""
        // VULNERABLE
        const char *password = "admin123";
        const char *api_key = "sk-1234567890abcdef";

        // SECURE
        const char *password = getenv("DB_PASSWORD");
        const char *api_key = getenv("API_KEY");
    """,
    test_cases=[
        {"name": "hardcoded password string", "method": "connect_database", "expected": True, "contains": ["password", "="]}
    ]
)


PRIV_ESCALATION_PATTERN = SecurityPattern(
    id="PRIV_ESCALATION_001",
    name="Privilege Escalation Risk",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Improper handling of privilege changes can lead to privilege escalation "
        "or failure to drop privileges properly."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'PRIVILEGE_ESCALATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('setuid', 'seteuid', 'setreuid', 'setresuid',
                          'setgid', 'setegid', 'setregid', 'setresgid',
                          'setgroups', 'initgroups', 'setfsuid', 'setfsgid')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-269", "CWE-250", "CWE-273"],
    remediation=(
        "1. Check return values of all setuid/setgid calls\n"
        "2. Drop privileges in correct order (groups, gid, uid)\n"
        "3. Verify privilege drop was successful\n"
        "4. Use setresuid/setresgid for atomic privilege changes\n"
        "5. Apply principle of least privilege"
    ),
    example_code="""
        // VULNERABLE
        setuid(user_id);  // Return value ignored!

        // SECURE
        if (setgroups(0, NULL) != 0)
            fatal("setgroups failed");
        if (setgid(gid) != 0)
            fatal("setgid failed");
        if (setuid(uid) != 0)
            fatal("setuid failed");
    """,
    test_cases=[
        {"name": "setuid without check", "method": "drop_privileges", "expected": True, "contains": ["setuid"]}
    ]
)


# Registry of auth patterns
AUTH_PATTERNS: Dict[str, SecurityPattern] = {
    "MISSING_AUTH": MISSING_AUTH_PATTERN,
    "HARDCODED_SECRETS": HARDCODED_SECRETS_PATTERN,
    "PRIV_ESCALATION": PRIV_ESCALATION_PATTERN,
}
