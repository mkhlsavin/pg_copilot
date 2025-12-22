"""
Concurrency Vulnerability Patterns

Patterns for detecting race conditions, TOCTOU, and file race vulnerabilities.

CWE-362 (Race Condition), CWE-367 (TOCTOU)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


RACE_CONDITION_PATTERN = SecurityPattern(
    id="CONCURRENCY_001",
    name="Time-of-Check Time-of-Use (TOCTOU)",
    category=VulnerabilityCategory.CONCURRENCY,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Race condition between checking a condition and using the result, "
        "allowing state changes between check and use."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            'RACE_CONDITION' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('access', 'stat', 'lstat', 'fstat')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-367"],
    remediation=(
        "1. Use atomic operations when possible\n"
        "2. Open files with O_EXCL flag\n"
        "3. Use proper locking mechanisms\n"
        "4. Avoid check-then-use patterns"
    ),
    example_code="""
        // VULNERABLE
        if (access(filename, F_OK) == 0) {
            FILE *f = fopen(filename, "r");  // File might change between calls
        }

        // SECURE
        int fd = open(filename, O_RDONLY | O_EXCL);
        if (fd >= 0) {
            FILE *f = fdopen(fd, "r");
        }
    """,
    test_cases=[
        {"name": "access then open", "method": "check_file_exists", "expected": True, "contains": ["access", "open"]}
    ]
)


FILE_RACE_PATTERN = SecurityPattern(
    id="RACE_FILE_001",
    name="File Operation Race Condition",
    category=VulnerabilityCategory.CONCURRENCY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Non-atomic file operations with check-then-operate patterns are vulnerable "
        "to time-of-check time-of-use (TOCTOU) race conditions."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'FILE_RACE_CONDITION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_method nm
        WHERE nm.code LIKE '%access(%'
          AND (nm.code LIKE '%fopen(%'
            OR nm.code LIKE '%open(%'
            OR nm.code LIKE '%unlink(%'
            OR nm.code LIKE '%chmod(%')
          AND nm.full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-362", "CWE-367"],
    remediation=(
        "1. Use atomic operations (O_CREAT|O_EXCL flag)\n"
        "2. Use file locks (flock, fcntl)\n"
        "3. Operate on file descriptors instead of paths\n"
        "4. Use safe directory with restricted permissions\n"
        "5. Check ownership after opening"
    ),
    example_code="""
        // VULNERABLE (TOCTOU)
        if (access(filename, F_OK) == 0) {
            FILE *f = fopen(filename, "r");  // Race window
        }

        // SECURE
        int fd = open(filename, O_RDONLY);
        if (fd >= 0) {
            struct stat st;
            fstat(fd, &st);  // Check after open
        }
    """,
    test_cases=[
        {"name": "access then fopen", "method": "safe_open_file", "expected": True, "contains": ["access", "fopen"]}
    ]
)


XXE_PATTERN = SecurityPattern(
    id="XXE_001",
    name="XML External Entity (XXE) Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "XML parsing with external entities enabled allows attackers to read local files, "
        "perform SSRF attacks, or cause denial of service."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XXE' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('xmlparse', 'parsexml', 'loadxml', 'read_xml',
                          'xmldocument', 'saxparser', 'domparser', 'xmlreader',
                          'etree_parse', 'xml_parse', 'xmlParseFile', 'xmlReadFile')
          AND nc.code NOT LIKE '%disable%entity%'
          AND nc.code NOT LIKE '%XXE%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-611"],
    remediation=(
        "1. Disable DTD processing entirely\n"
        "2. Disable external entity resolution\n"
        "3. Use defusedxml or similar safe parsers\n"
        "4. Validate XML against schema before parsing\n"
        "5. Consider using JSON instead of XML"
    ),
    example_code="""
        // VULNERABLE
        xmlDocPtr doc = xmlParseFile(userFile);  // XXE possible

        // SECURE
        xmlParserCtxtPtr ctxt = xmlNewParserCtxt();
        xmlCtxtUseOptions(ctxt, XML_PARSE_NOENT | XML_PARSE_NONET);
    """,
    test_cases=[
        {"name": "XML parsing without protection", "method": "parse_config", "expected": True, "contains": ["xmlParse"]}
    ]
)


LOG_INJECTION_PATTERN = SecurityPattern(
    id="LOG_INJECTION_001",
    name="Log Injection / Log Forging",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "User input in log messages without sanitization allows log forging, "
        "which can hide attacks, inject false entries, or exploit log viewers."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'LOG_INJECTION' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('elog', 'ereport', 'syslog', 'openlog',
                          'fprintf', 'fputs', 'fwrite', 'write_log')
          AND (nc.code LIKE '%sprintf%'
            OR nc.code LIKE '%strcat%'
            OR nc.code LIKE '%snprintf%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-117"],
    remediation=(
        "1. Encode/escape user input before logging\n"
        "2. Remove newlines and control characters\n"
        "3. Use structured logging (JSON format)\n"
        "4. Implement input length limits\n"
        "5. Consider using parameterized logging"
    ),
    example_code="""
        // VULNERABLE
        elog(LOG, "User %s logged in", username);  // Can inject newlines

        // SECURE
        char *safe_username = escape_log_string(username);
        elog(LOG, "User %s logged in", safe_username);
    """,
    test_cases=[
        {"name": "elog with user input", "method": "log_user_action", "expected": True, "contains": ["elog", "sprintf"]}
    ]
)


EXEC_PATH_INJECTION_PATTERN = SecurityPattern(
    id="EXEC_ENV_PATH_001",
    name="Executable Path Injection via Environment",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Executing programs without absolute paths allows attackers to inject "
        "malicious executables through PATH manipulation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'EXEC_PATH_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('execvp', 'execlp', 'system', 'popen', 'spawnlp', 'spawnvp')
          AND nc.code NOT LIKE '%/usr/%'
          AND nc.code NOT LIKE '%/bin/%'
          AND nc.code NOT LIKE '%/sbin/%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-426", "CWE-427"],
    remediation=(
        "1. Always use absolute paths for executables\n"
        "2. Clear or sanitize PATH environment variable\n"
        "3. Use execve/execv instead of execvp/execlp\n"
        "4. Validate program paths before execution\n"
        "5. Run with minimal privileges"
    ),
    example_code="""
        // VULNERABLE
        system("pg_dump database");  // Uses PATH

        // SECURE
        execv("/usr/bin/pg_dump", args);  // Absolute path
    """,
    test_cases=[
        {"name": "system without absolute path", "method": "backup_database", "expected": True, "contains": ["system"]}
    ]
)


# Registry of concurrency patterns
CONCURRENCY_PATTERNS: Dict[str, SecurityPattern] = {
    "RACE_CONDITION": RACE_CONDITION_PATTERN,
    "FILE_RACE": FILE_RACE_PATTERN,
    "XXE": XXE_PATTERN,
    "LOG_INJECTION": LOG_INJECTION_PATTERN,
    "EXEC_PATH_INJECTION": EXEC_PATH_INJECTION_PATTERN,
}
