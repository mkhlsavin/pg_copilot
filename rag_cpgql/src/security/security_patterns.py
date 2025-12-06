"""
Security Pattern Library for Code Property Graph Analysis

This module contains security vulnerability patterns, CPGQL queries for detection,
and metadata for security analysis workflows. Supports PostgreSQL C codebase analysis.

Week 5, Task 2.1: Security Pattern Library
Phase 2: Quality & Security Enhancement
"""

from typing import Dict, List, Any

# Import base types from _base module
from ._base import (
    VulnerabilitySeverity,
    VulnerabilityCategory,
    SecurityPattern,
)


# ============================================================================
# INJECTION VULNERABILITIES
# ============================================================================

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


# ============================================================================
# BUFFER OVERFLOW VULNERABILITIES
# ============================================================================

BUFFER_OVERFLOW_STRCPY_PATTERN = SecurityPattern(
    id="BUFFER_OVERFLOW_001",
    name="Buffer Overflow via strcpy/strcat",
    category=VulnerabilityCategory.BUFFER_OVERFLOW,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Use of unsafe string functions (strcpy, strcat, gets) that don't perform "
        "bounds checking, leading to buffer overflows and potential code execution."
    ),
    cpgql_query="""
        -- Find call sites to unsafe string functions
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS unsafe_function,
            'BUFFER_OVERFLOW' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('strcpy', 'strcat', 'gets', 'sprintf', 'vsprintf')
          AND nc.method_full_name NOT LIKE 'test_%'
        ORDER BY nc.filename, nc.line_number
        LIMIT 100;
    """,
    cwe_ids=["CWE-120", "CWE-676"],
    remediation=(
        "1. Replace strcpy with strncpy or strlcpy\n"
        "2. Replace strcat with strncat or strlcat\n"
        "3. Replace gets with fgets\n"
        "4. Replace sprintf with snprintf\n"
        "5. Always validate buffer sizes before operations"
    ),
    example_code="""
        // VULNERABLE
        char buffer[64];
        strcpy(buffer, user_input);

        // SECURE
        char buffer[64];
        strncpy(buffer, user_input, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\\0';
    """,
    test_cases=[
        {
            "name": "strcpy usage",
            "method": "copy_string",
            "expected": True,
            "contains": ["strcpy"]
        },
        {
            "name": "strncpy usage",
            "method": "safe_copy_string",
            "expected": False,
            "contains": ["strncpy"]
        }
    ]
)


BUFFER_OVERFLOW_SPRINTF_PATTERN = SecurityPattern(
    id="BUFFER_OVERFLOW_002",
    name="Buffer Overflow via sprintf/vsprintf",
    category=VulnerabilityCategory.BUFFER_OVERFLOW,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Use of sprintf/vsprintf without bounds checking can overflow destination "
        "buffer when formatted string exceeds buffer size."
    ),
    cpgql_query="""
        -- Find call sites to sprintf/vsprintf
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'BUFFER_OVERFLOW_FORMAT' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('sprintf', 'vsprintf')
          AND nc.method_full_name NOT LIKE 'test_%'
        ORDER BY nc.filename, nc.line_number
        LIMIT 100;
    """,
    cwe_ids=["CWE-120", "CWE-134"],
    remediation=(
        "1. Replace sprintf with snprintf\n"
        "2. Replace vsprintf with vsnprintf\n"
        "3. Always specify maximum buffer size\n"
        "4. Check return value to detect truncation"
    ),
    example_code="""
        // VULNERABLE
        char msg[128];
        sprintf(msg, "Error: %s", error_string);

        // SECURE
        char msg[128];
        snprintf(msg, sizeof(msg), "Error: %s", error_string);
    """,
    test_cases=[
        {
            "name": "sprintf usage",
            "method": "format_message",
            "expected": True,
            "contains": ["sprintf"]
        }
    ]
)


# ============================================================================
# MEMORY SAFETY VULNERABILITIES
# ============================================================================

USE_AFTER_FREE_PATTERN = SecurityPattern(
    id="MEMORY_SAFETY_001",
    name="Use-After-Free Vulnerability",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Access to memory after it has been freed, leading to undefined behavior, "
        "crashes, or potential code execution."
    ),
    cpgql_query="""
        -- Find call sites to free/pfree that might have use-after-free
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            'USE_AFTER_FREE' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('free', 'pfree')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-416"],
    remediation=(
        "1. Set pointers to NULL after freeing\n"
        "2. Use reference counting or smart pointers\n"
        "3. Employ memory safety tools (AddressSanitizer, Valgrind)\n"
        "4. Follow strict memory ownership patterns\n"
        "5. Use PostgreSQL's memory context system properly"
    ),
    example_code="""
        // VULNERABLE
        void process_data(Node *node) {
            pfree(node);
            if (node->type == T_OpExpr)  // Use after free!
                return;
        }

        // SECURE
        void process_data(Node *node) {
            NodeTag type = node->type;
            pfree(node);
            node = NULL;
            if (type == T_OpExpr)
                return;
        }
    """,
    test_cases=[
        {
            "name": "free without NULL assignment",
            "method": "cleanup_node",
            "expected": True,
            "contains": ["pfree"]
        }
    ]
)


MEMORY_LEAK_PATTERN = SecurityPattern(
    id="MEMORY_SAFETY_002",
    name="Memory Leak - Missing Free",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Allocated memory not properly freed, leading to memory exhaustion over time. "
        "Particularly critical in long-running server processes like PostgreSQL."
    ),
    cpgql_query="""
        -- Find call sites to memory allocation functions
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS alloc_function,
            'MEMORY_LEAK' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('malloc', 'calloc', 'palloc', 'palloc0', 'MemoryContextAlloc')
          AND nc.method_full_name NOT LIKE 'test_%'
        ORDER BY nc.line_number DESC
        LIMIT 50;
    """,
    cwe_ids=["CWE-401"],
    remediation=(
        "1. Ensure every allocation has a corresponding free\n"
        "2. Use PostgreSQL memory contexts for automatic cleanup\n"
        "3. Implement RAII-like patterns with cleanup functions\n"
        "4. Use static analysis tools to detect leaks\n"
        "5. Add memory leak tests in test suite"
    ),
    example_code="""
        // VULNERABLE
        char *process_string(const char *input) {
            char *result = palloc(strlen(input) + 10);
            sprintf(result, "<%s>", input);
            return result;  // Caller might not know to free
        }

        // SECURE
        char *process_string(const char *input) {
            MemoryContext oldctx = MemoryContextSwitchTo(query_context);
            char *result = palloc(strlen(input) + 10);
            sprintf(result, "<%s>", input);
            MemoryContextSwitchTo(oldctx);
            return result;  // Freed with memory context
        }
    """,
    test_cases=[
        {
            "name": "malloc without free",
            "method": "allocate_buffer",
            "expected": True,
            "contains": ["palloc"]
        }
    ]
)


NULL_POINTER_DEREFERENCE_PATTERN = SecurityPattern(
    id="MEMORY_SAFETY_003",
    name="NULL Pointer Dereference",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Dereferencing a pointer without checking if it's NULL, leading to crashes "
        "or potential security issues."
    ),
    cpgql_query="""
        -- Find call sites to malloc/palloc that may lack NULL checks
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            'NULL_POINTER_DEREFERENCE' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('malloc', 'calloc', 'palloc', 'palloc0')
          AND nc.code NOT LIKE '%if%'
          AND nc.code NOT LIKE '%NULL%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-476"],
    remediation=(
        "1. Always check return values of allocation functions\n"
        "2. Use palloc() which errors on failure (PostgreSQL convention)\n"
        "3. Add NULL checks before pointer dereferences\n"
        "4. Use static analysis to detect missing checks"
    ),
    example_code="""
        // VULNERABLE
        Node *node = malloc(sizeof(Node));
        node->type = T_Var;  // Crash if malloc failed

        // SECURE
        Node *node = palloc(sizeof(Node));  // Errors on failure
        node->type = T_Var;

        // OR with malloc
        Node *node = malloc(sizeof(Node));
        if (node == NULL)
            elog(ERROR, "out of memory");
        node->type = T_Var;
    """,
    test_cases=[
        {
            "name": "malloc without NULL check",
            "method": "create_node",
            "expected": True,
            "contains": ["malloc"]
        }
    ]
)


# ============================================================================
# INPUT VALIDATION VULNERABILITIES
# ============================================================================

INTEGER_OVERFLOW_PATTERN = SecurityPattern(
    id="INPUT_VALIDATION_001",
    name="Integer Overflow in Size Calculation",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Integer overflow in size calculations leading to undersized buffer "
        "allocations and subsequent buffer overflows."
    ),
    cpgql_query="""
        -- Find allocation call sites with size calculations
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            'INTEGER_OVERFLOW' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('malloc', 'calloc', 'palloc', 'palloc0')
          AND (nc.code LIKE '%*%' OR nc.code LIKE '%+%')
          AND nc.code NOT LIKE '%check%overflow%'
          AND nc.code NOT LIKE '%SIZE_MAX%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-190", "CWE-680"],
    remediation=(
        "1. Check for overflow before arithmetic operations\n"
        "2. Use SIZE_MAX for bounds checking\n"
        "3. Use safe math libraries or compiler builtins\n"
        "4. Validate input sizes before calculations"
    ),
    example_code="""
        // VULNERABLE
        size_t size = num_elements * element_size;
        void *buffer = malloc(size);  // Overflow if num_elements too large

        // SECURE
        if (num_elements > SIZE_MAX / element_size)
            elog(ERROR, "allocation size overflow");
        size_t size = num_elements * element_size;
        void *buffer = malloc(size);
    """,
    test_cases=[
        {
            "name": "multiplication before malloc",
            "method": "allocate_array",
            "expected": True,
            "contains": ["malloc", "*"]
        }
    ]
)


TAINTED_INPUT_PATTERN = SecurityPattern(
    id="INPUT_VALIDATION_002",
    name="Untrusted Input Without Validation",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "User-controllable input used in sensitive operations without proper "
        "validation or sanitization."
    ),
    cpgql_query="""
        -- Find call sites to input functions (simplified)
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            2 AS category,
            'TAINTED_INPUT' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('recv', 'read', 'fgets', 'scanf', 'getenv', 'getchar')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-20", "CWE-129"],
    remediation=(
        "1. Validate all input against expected format\n"
        "2. Use whitelist validation when possible\n"
        "3. Sanitize input before use in sensitive operations\n"
        "4. Apply proper encoding/escaping for output context"
    ),
    example_code="""
        // VULNERABLE
        void process_user_input(const char *input) {
            char query[256];
            sprintf(query, "SELECT * FROM data WHERE id=%s", input);
            exec_query(query);
        }

        // SECURE
        void process_user_input(const char *input) {
            // Validate input is numeric
            for (const char *p = input; *p; p++) {
                if (!isdigit(*p))
                    elog(ERROR, "invalid input: not a number");
            }
            char query[256];
            snprintf(query, sizeof(query), "SELECT * FROM data WHERE id=%s", input);
            exec_query(query);
        }
    """,
    test_cases=[
        {
            "name": "input handler without validation",
            "method": "handle_user_request",
            "expected": True,
            "contains": ["input"]
        }
    ]
)


# ============================================================================
# CRYPTOGRAPHY VULNERABILITIES
# ============================================================================

WEAK_CRYPTO_PATTERN = SecurityPattern(
    id="CRYPTO_001",
    name="Weak Cryptographic Algorithm",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Use of weak or broken cryptographic algorithms (MD5, SHA1, DES) "
        "that don't provide adequate security."
    ),
    cpgql_query="""
        -- Find call sites to weak crypto functions
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS weak_function,
            'WEAK_CRYPTOGRAPHY' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.name LIKE '%md5%'
            OR nc.name LIKE '%sha1%'
            OR nc.name LIKE '%des%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-327", "CWE-328"],
    remediation=(
        "1. Replace MD5 with SHA-256 or SHA-3\n"
        "2. Replace SHA1 with SHA-256 for signatures\n"
        "3. Replace DES with AES-256\n"
        "4. Use modern crypto libraries (OpenSSL 1.1+, libsodium)\n"
        "5. Follow NIST or OWASP cryptography guidelines"
    ),
    example_code="""
        // VULNERABLE
        unsigned char hash[16];
        MD5(password, strlen(password), hash);

        // SECURE
        unsigned char hash[32];
        SHA256(password, strlen(password), hash);
    """,
    test_cases=[
        {
            "name": "MD5 usage",
            "method": "hash_password",
            "expected": True,
            "contains": ["MD5"]
        }
    ]
)


# ============================================================================
# CONCURRENCY VULNERABILITIES
# ============================================================================

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
        -- Find methods with potential TOCTOU (simplified - find access/stat calls)
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
            // ...
        }

        // SECURE
        int fd = open(filename, O_RDONLY | O_EXCL);
        if (fd >= 0) {
            FILE *f = fdopen(fd, "r");
            // ...
        }
    """,
    test_cases=[
        {
            "name": "access then open",
            "method": "check_file_exists",
            "expected": True,
            "contains": ["access", "open"]
        }
    ]
)


# ============================================================================
# FORMAT STRING VULNERABILITIES (Sprint 1 - Scenario 15 Enhancement)
# ============================================================================

FORMAT_STRING_PATTERN = SecurityPattern(
    id="FORMAT_STRING_001",
    name="Format String Vulnerability",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Format string vulnerability where user-controlled input is passed directly "
        "as the format argument to printf-family functions, allowing attackers to "
        "read/write memory and potentially execute arbitrary code."
    ),
    cpgql_query="""
        -- Find printf-family calls where format is not a literal string
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS function_name,
            nc.code,
            'FORMAT_STRING' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('printf', 'sprintf', 'fprintf', 'snprintf', 'vprintf',
                          'vsprintf', 'vfprintf', 'vsnprintf', 'syslog', 'ereport')
          AND (nc.code NOT LIKE '%"%'  -- Format is not a string literal
            OR nc.code LIKE '%printf(%' || chr(37) || 's%')  -- printf(var) pattern
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-134"],
    remediation=(
        "1. Never pass user input as the format string argument\n"
        "2. Always use literal format strings: printf(\"%s\", user_input)\n"
        "3. Use %s to print user data, not the data directly\n"
        "4. Use compiler warnings: -Wformat -Wformat-security"
    ),
    example_code="""
        // VULNERABLE
        printf(user_input);           // User controls format string
        sprintf(buf, user_input);     // Same issue

        // SECURE
        printf("%s", user_input);     // User input treated as data
        sprintf(buf, "%s", user_input);
    """,
    test_cases=[
        {
            "name": "printf with variable format",
            "method": "log_message",
            "expected": True,
            "contains": ["printf"]
        }
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
        -- Find hardcoded secrets in string literals and assignments
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
          AND nl.code LIKE '%"%'  -- Contains a string literal
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
        {
            "name": "hardcoded password string",
            "method": "connect_database",
            "expected": True,
            "contains": ["password", "="]
        }
    ]
)


DOUBLE_FREE_PATTERN = SecurityPattern(
    id="DOUBLE_FREE_001",
    name="Double Free Vulnerability",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Freeing the same memory twice leads to heap corruption, crashes, or "
        "potential arbitrary code execution through heap exploitation."
    ),
    cpgql_query="""
        -- Find methods with multiple free/pfree calls on same variable
        WITH free_calls AS (
            SELECT
                nc.method_full_name,
                nc.filename,
                nc.line_number,
                nc.code,
                REGEXP_EXTRACT(nc.code, '(free|pfree)\\s*\\(\\s*(\\w+)', 2) AS freed_var
            FROM nodes_call nc
            WHERE nc.name IN ('free', 'pfree')
              AND nc.method_full_name NOT LIKE 'test_%'
        )
        SELECT DISTINCT
            fc1.method_full_name AS method_name,
            fc1.filename,
            fc1.line_number,
            fc1.code,
            fc1.freed_var,
            'DOUBLE_FREE' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM free_calls fc1
        JOIN free_calls fc2 ON fc1.method_full_name = fc2.method_full_name
                           AND fc1.freed_var = fc2.freed_var
                           AND fc1.line_number < fc2.line_number
        LIMIT 50;
    """,
    cwe_ids=["CWE-415"],
    remediation=(
        "1. Set pointer to NULL immediately after freeing\n"
        "2. Use ownership patterns - clear owner frees\n"
        "3. Use reference counting for shared memory\n"
        "4. Run AddressSanitizer to detect double-frees"
    ),
    example_code="""
        // VULNERABLE
        free(ptr);
        // ... code ...
        free(ptr);  // Double free!

        // SECURE
        free(ptr);
        ptr = NULL;
        // ... code ...
        if (ptr != NULL)
            free(ptr);
    """,
    test_cases=[
        {
            "name": "multiple free calls",
            "method": "cleanup_resources",
            "expected": True,
            "contains": ["free", "free"]
        }
    ]
)


UNINITIALIZED_VAR_PATTERN = SecurityPattern(
    id="UNINITIALIZED_VAR_001",
    name="Uninitialized Variable Use",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Using variables before they are initialized can expose sensitive data "
        "from previous stack/heap contents or cause undefined behavior."
    ),
    cpgql_query="""
        -- Find local variables that may be used uninitialized
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'UNINITIALIZED_VAR' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_method nm
        WHERE nm.code LIKE '%char %[%]%'  -- Char arrays often uninitialized
           OR nm.code LIKE '%int %*%'      -- Pointer declarations
           OR nm.code LIKE '%struct %*%'
        AND nm.code NOT LIKE '%=%'         -- No initialization
        AND nm.code NOT LIKE '%{%'         -- No struct initialization
        AND nm.full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-457", "CWE-908"],
    remediation=(
        "1. Always initialize variables at declaration\n"
        "2. Use memset/memset_s for arrays and structs\n"
        "3. Enable compiler warnings: -Wuninitialized\n"
        "4. Use static analysis tools"
    ),
    example_code="""
        // VULNERABLE
        char buffer[256];
        int *ptr;
        process(buffer);  // Contains garbage

        // SECURE
        char buffer[256] = {0};
        int *ptr = NULL;
        process(buffer);
    """,
    test_cases=[
        {
            "name": "uninitialized buffer",
            "method": "process_request",
            "expected": True,
            "contains": ["char", "["]
        }
    ]
)


PATH_TRAVERSAL_PATTERN = SecurityPattern(
    id="PATH_TRAVERSAL_001",
    name="Path Traversal (Directory Traversal)",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "File paths constructed from user input without proper sanitization, "
        "allowing attackers to access files outside intended directories using ../ sequences."
    ),
    cpgql_query="""
        -- Find file operations with potential path traversal
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS file_function,
            nc.code,
            'PATH_TRAVERSAL' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('fopen', 'open', 'stat', 'access', 'unlink', 'remove',
                          'rename', 'mkdir', 'rmdir', 'opendir', 'realpath')
          AND (nc.code LIKE '%strcat%'
            OR nc.code LIKE '%sprintf%'
            OR nc.code LIKE '%snprintf%'
            OR nc.code NOT LIKE '%"/%')  -- Path not starting with literal /
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22", "CWE-23"],
    remediation=(
        "1. Use realpath() to resolve and validate paths\n"
        "2. Check that resolved path is within allowed directory\n"
        "3. Reject paths containing .. or starting with /\n"
        "4. Use chroot or containerization for isolation"
    ),
    example_code="""
        // VULNERABLE
        char filepath[256];
        snprintf(filepath, sizeof(filepath), "/data/%s", user_input);
        FILE *f = fopen(filepath, "r");  // ../../../etc/passwd attack

        // SECURE
        char filepath[256];
        snprintf(filepath, sizeof(filepath), "/data/%s", user_input);
        char *resolved = realpath(filepath, NULL);
        if (resolved && strncmp(resolved, "/data/", 6) == 0)
            FILE *f = fopen(resolved, "r");
    """,
    test_cases=[
        {
            "name": "fopen with user input path",
            "method": "read_user_file",
            "expected": True,
            "contains": ["fopen", "sprintf"]
        }
    ]
)


ARRAY_BOUNDS_PATTERN = SecurityPattern(
    id="ARRAY_BOUNDS_001",
    name="Array Index Out of Bounds",
    category=VulnerabilityCategory.BUFFER_OVERFLOW,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Accessing arrays with indices derived from user input without bounds checking, "
        "leading to buffer overflows or information disclosure."
    ),
    cpgql_query="""
        -- Find array accesses that may be out of bounds
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'ARRAY_OUT_OF_BOUNDS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_method nm
        WHERE nm.code LIKE '%[%]%'  -- Contains array access
          AND (nm.code LIKE '%[i]%'
            OR nm.code LIKE '%[index]%'
            OR nm.code LIKE '%[idx]%'
            OR nm.code LIKE '%[n]%')
          AND nm.code NOT LIKE '%if%<%'  -- No bounds check
          AND nm.code NOT LIKE '%assert%'
          AND nm.full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-129", "CWE-787"],
    remediation=(
        "1. Always validate array indices before use\n"
        "2. Use assert() for debug builds\n"
        "3. Use safe array abstractions with bounds checking\n"
        "4. Enable compiler options: -fbounds-check"
    ),
    example_code="""
        // VULNERABLE
        int value = array[user_index];  // No bounds check

        // SECURE
        if (user_index >= 0 && user_index < ARRAY_SIZE)
            int value = array[user_index];
        else
            elog(ERROR, "array index out of bounds");
    """,
    test_cases=[
        {
            "name": "array access without bounds check",
            "method": "get_element",
            "expected": True,
            "contains": ["[", "]"]
        }
    ]
)


TYPE_CONFUSION_PATTERN = SecurityPattern(
    id="TYPE_CONFUSION_001",
    name="Type Confusion Vulnerability",
    category=VulnerabilityCategory.MEMORY_SAFETY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Accessing memory through a pointer of incompatible type, or casting objects "
        "to wrong types, leading to memory corruption or code execution."
    ),
    cpgql_query="""
        -- Find suspicious type casts
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'TYPE_CONFUSION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.code LIKE '%(%*)%'          -- Pointer cast pattern
            OR nc.code LIKE '%reinterpret%'
            OR nc.code LIKE '%(void *)%'
            OR nc.code LIKE '%(char *)%')
          AND nc.code NOT LIKE '%sizeof%'     -- Not size calculation
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-843", "CWE-704"],
    remediation=(
        "1. Use proper type checking before casts\n"
        "2. Implement tagged unions with type discriminator\n"
        "3. Use static_cast in C++ instead of reinterpret_cast\n"
        "4. Use nodeTag() checks in PostgreSQL before casting nodes"
    ),
    example_code="""
        // VULNERABLE (PostgreSQL example)
        Var *var = (Var *)node;  // No type check

        // SECURE
        if (IsA(node, Var))
            Var *var = (Var *)node;
        else
            elog(ERROR, "expected Var node");
    """,
    test_cases=[
        {
            "name": "unsafe pointer cast",
            "method": "process_node",
            "expected": True,
            "contains": ["(", "*)", ")"]
        }
    ]
)


# ============================================================================
# SPRINT 2 - 12 NEW SECURITY PATTERNS
# ============================================================================

INSECURE_DESERIALIZATION_PATTERN = SecurityPattern(
    id="DESERIALIZATION_001",
    name="Insecure Deserialization",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Deserialization of untrusted data can lead to remote code execution, "
        "denial of service, or authentication bypass attacks."
    ),
    cpgql_query="""
        -- Find deserialization function calls
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_DESERIALIZATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('deserialize', 'unserialize', 'readobject', 'unmarshal',
                          'fromstring', 'loads', 'pickle_load', 'yaml_load',
                          'ObjectInputStream', 'unpack')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-502"],
    remediation=(
        "1. Use safe serialization formats like JSON instead of binary formats\n"
        "2. Validate and sanitize input before deserialization\n"
        "3. Implement integrity checks (signatures/HMAC)\n"
        "4. Use allowlists for permitted classes\n"
        "5. Run deserialization in sandboxed environment"
    ),
    example_code="""
        // VULNERABLE
        ObjectInputStream ois = new ObjectInputStream(userInput);
        Object obj = ois.readObject();  // RCE risk

        // SECURE
        // Use JSON with schema validation
        JsonParser parser = new JsonParser();
        UserData data = parser.parseAs(UserData.class, userInput);
    """,
    test_cases=[
        {
            "name": "pickle deserialization",
            "method": "load_user_data",
            "expected": True,
            "contains": ["pickle", "load"]
        }
    ]
)


SSRF_PATTERN = SecurityPattern(
    id="SSRF_001",
    name="Server-Side Request Forgery (SSRF)",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "User-controlled URLs in server-side requests can be exploited to access "
        "internal services, cloud metadata, or perform port scanning."
    ),
    cpgql_query="""
        -- Find URL fetching with potential user input
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SSRF' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('curl_exec', 'curl_init', 'file_get_contents', 'urlopen',
                          'http_request', 'fetch', 'wget', 'HttpClient', 'urlretrieve',
                          'request', 'get', 'post', 'libcurl')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-918"],
    remediation=(
        "1. Implement allowlist of permitted domains/IPs\n"
        "2. Block requests to internal network ranges (10.x, 192.168.x, 169.254.x)\n"
        "3. Disable redirects or validate redirect targets\n"
        "4. Use DNS rebinding protections\n"
        "5. Implement request timeouts"
    ),
    example_code="""
        // VULNERABLE
        url = user_input;
        response = curl_fetch(url);  // Can access internal services

        // SECURE
        if (is_allowed_domain(url) && !is_internal_ip(url)) {
            response = curl_fetch(url);
        }
    """,
    test_cases=[
        {
            "name": "curl with user URL",
            "method": "fetch_remote_data",
            "expected": True,
            "contains": ["curl"]
        }
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
        -- Find XML parsing without entity restrictions
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
        xmlDocPtr doc = xmlCtxtReadFile(ctxt, userFile, NULL, 0);
    """,
    test_cases=[
        {
            "name": "XML parsing without protection",
            "method": "parse_config",
            "expected": True,
            "contains": ["xmlParse"]
        }
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
        -- Find logging with potential unsanitized input
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
        {
            "name": "elog with user input",
            "method": "log_user_action",
            "expected": True,
            "contains": ["elog", "sprintf"]
        }
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
        -- Find file check followed by file operation
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
            // verify ownership/permissions
        }
    """,
    test_cases=[
        {
            "name": "access then fopen",
            "method": "safe_open_file",
            "expected": True,
            "contains": ["access", "fopen"]
        }
    ]
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
        -- Find sensitive operations that may lack auth checks
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
        {
            "name": "drop without auth",
            "method": "drop_user_table",
            "expected": True,
            "contains": ["drop", "table"]
        }
    ]
)


IMPROPER_CERT_PATTERN = SecurityPattern(
    id="IMPROPER_CERT_001",
    name="Improper SSL/TLS Certificate Validation",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "SSL/TLS connections that skip or weaken certificate validation "
        "are vulnerable to man-in-the-middle attacks."
    ),
    cpgql_query="""
        -- Find SSL/TLS with disabled verification
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'IMPROPER_CERT_VALIDATION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.code LIKE '%VERIFY_NONE%'
            OR nc.code LIKE '%verify_mode%0%'
            OR nc.code LIKE '%SSL_CTX_set_verify%NULL%'
            OR nc.code LIKE '%verify%false%'
            OR nc.code LIKE '%check_hostname%False%'
            OR nc.code LIKE '%CURLOPT_SSL_VERIFYPEER%0%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-295"],
    remediation=(
        "1. Always verify SSL certificates\n"
        "2. Use system CA certificate bundle\n"
        "3. Enable hostname verification\n"
        "4. Pin certificates for critical services\n"
        "5. Keep certificate stores updated"
    ),
    example_code="""
        // VULNERABLE
        SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);  // MITM risk

        // SECURE
        SSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, verify_callback);
        SSL_CTX_load_verify_locations(ctx, "/etc/ssl/certs/ca-bundle.crt", NULL);
    """,
    test_cases=[
        {
            "name": "SSL verify disabled",
            "method": "create_ssl_connection",
            "expected": True,
            "contains": ["VERIFY_NONE"]
        }
    ]
)


CLEARTEXT_STORAGE_PATTERN = SecurityPattern(
    id="CLEARTEXT_STORAGE_001",
    name="Cleartext Storage of Sensitive Data",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Sensitive data stored without encryption can be exposed through "
        "file access, backups, or data breaches."
    ),
    cpgql_query="""
        -- Find storage of sensitive data without encryption
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'CLEARTEXT_STORAGE' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('fwrite', 'write', 'fputs', 'fprintf', 'fputc',
                          'PQexec', 'SPI_execute', 'insert_row')
          AND (LOWER(nc.code) LIKE '%password%'
            OR LOWER(nc.code) LIKE '%secret%'
            OR LOWER(nc.code) LIKE '%api_key%'
            OR LOWER(nc.code) LIKE '%token%'
            OR LOWER(nc.code) LIKE '%credit_card%'
            OR LOWER(nc.code) LIKE '%ssn%')
          AND nc.code NOT LIKE '%encrypt%'
          AND nc.code NOT LIKE '%hash%'
          AND nc.code NOT LIKE '%crypt%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-312", "CWE-313"],
    remediation=(
        "1. Encrypt sensitive data before storage\n"
        "2. Use strong encryption (AES-256)\n"
        "3. Store encryption keys separately\n"
        "4. Hash passwords with bcrypt/argon2\n"
        "5. Implement key rotation"
    ),
    example_code="""
        // VULNERABLE
        fwrite(user_password, 1, strlen(user_password), file);  // Plaintext

        // SECURE
        char *hashed = bcrypt_hash(user_password);
        fwrite(hashed, 1, strlen(hashed), file);
    """,
    test_cases=[
        {
            "name": "password written plaintext",
            "method": "save_user_credentials",
            "expected": True,
            "contains": ["password", "write"]
        }
    ]
)


INSUFFICIENT_ENTROPY_PATTERN = SecurityPattern(
    id="INSUFFICIENT_ENTROPY_001",
    name="Insufficient Entropy for Security Tokens",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Security tokens generated with insufficient randomness can be "
        "predicted or brute-forced by attackers."
    ),
    cpgql_query="""
        -- Find weak random generation for security purposes
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSUFFICIENT_ENTROPY' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (LOWER(nc.code) LIKE '%token%'
            OR LOWER(nc.code) LIKE '%session%'
            OR LOWER(nc.code) LIKE '%nonce%'
            OR LOWER(nc.code) LIKE '%salt%')
          AND (nc.name IN ('rand', 'random', 'srand', 'rand_r')
               OR nc.code LIKE '%time(%'
               OR nc.code LIKE '%clock(%'
               OR nc.code LIKE '%getpid(%')
          AND nc.code NOT LIKE '%/dev/urandom%'
          AND nc.code NOT LIKE '%RAND_bytes%'
          AND nc.code NOT LIKE '%getrandom%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-330", "CWE-331", "CWE-338"],
    remediation=(
        "1. Use cryptographically secure PRNG (CSPRNG)\n"
        "2. Use /dev/urandom or getrandom() on Linux\n"
        "3. Use RAND_bytes() from OpenSSL\n"
        "4. Never seed with predictable values (time, PID)\n"
        "5. Use sufficient token length (128+ bits)"
    ),
    example_code="""
        // VULNERABLE
        srand(time(NULL));
        int token = rand();  // Predictable!

        // SECURE
        unsigned char token[32];
        RAND_bytes(token, sizeof(token));  // Crypto-secure
    """,
    test_cases=[
        {
            "name": "weak random for token",
            "method": "generate_session_token",
            "expected": True,
            "contains": ["rand", "token"]
        }
    ]
)


RESOURCE_LEAK_PATTERN = SecurityPattern(
    id="RESOURCE_LEAK_001",
    name="Resource Leak (File Descriptor / Handle)",
    category=VulnerabilityCategory.RESOURCE_MANAGEMENT,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Resources (file descriptors, sockets, handles) not properly closed "
        "lead to resource exhaustion and denial of service."
    ),
    cpgql_query="""
        -- Find functions that open but may not close resources
        WITH opens AS (
            SELECT nm.id, nm.name, nm.full_name, nm.filename, nm.line_number
            FROM nodes_method nm
            WHERE nm.code LIKE '%fopen(%'
               OR nm.code LIKE '% open(%'
               OR nm.code LIKE '%socket(%'
               OR nm.code LIKE '%CreateFile%'
        ),
        closes AS (
            SELECT nm.id
            FROM nodes_method nm
            WHERE nm.code LIKE '%fclose(%'
               OR nm.code LIKE '%close(%'
               OR nm.code LIKE '%closesocket(%'
               OR nm.code LIKE '%CloseHandle%'
        )
        SELECT DISTINCT
            o.id,
            o.name AS method_name,
            o.full_name,
            o.filename,
            o.line_number,
            'RESOURCE_LEAK' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM opens o
        LEFT JOIN closes c ON o.id = c.id
        WHERE c.id IS NULL
          AND o.full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-772", "CWE-404", "CWE-775"],
    remediation=(
        "1. Always close resources in finally/cleanup blocks\n"
        "2. Use RAII patterns (C++) or defer (Go)\n"
        "3. Use try-with-resources (Java) or with statement (Python)\n"
        "4. Set resource limits with ulimit\n"
        "5. Implement resource tracking and cleanup on error paths"
    ),
    example_code="""
        // VULNERABLE
        FILE *f = fopen(filename, "r");
        if (error_condition)
            return -1;  // Leak!
        fclose(f);

        // SECURE
        FILE *f = fopen(filename, "r");
        if (!f) return -1;

        int result = process_file(f);
        fclose(f);  // Always close
        return result;
    """,
    test_cases=[
        {
            "name": "file not closed on error",
            "method": "read_config_file",
            "expected": True,
            "contains": ["fopen"]
        }
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
        -- Find exec calls without absolute paths
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
        {
            "name": "system without absolute path",
            "method": "backup_database",
            "expected": True,
            "contains": ["system"]
        }
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
        -- Find privilege manipulation functions
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
        // Verify privileges were dropped
        if (getuid() != uid || geteuid() != uid)
            fatal("privilege drop failed");
    """,
    test_cases=[
        {
            "name": "setuid without check",
            "method": "drop_privileges",
            "expected": True,
            "contains": ["setuid"]
        }
    ]
)


# ============================================================================
# PATTERN REGISTRY
# ============================================================================

# All available security patterns
SECURITY_PATTERNS: Dict[str, SecurityPattern] = {
    # Original 11 patterns
    "SQL_INJECTION": SQL_INJECTION_PATTERN,
    "COMMAND_INJECTION": COMMAND_INJECTION_PATTERN,
    "BUFFER_OVERFLOW_STRCPY": BUFFER_OVERFLOW_STRCPY_PATTERN,
    "BUFFER_OVERFLOW_SPRINTF": BUFFER_OVERFLOW_SPRINTF_PATTERN,
    "USE_AFTER_FREE": USE_AFTER_FREE_PATTERN,
    "MEMORY_LEAK": MEMORY_LEAK_PATTERN,
    "NULL_POINTER_DEREFERENCE": NULL_POINTER_DEREFERENCE_PATTERN,
    "INTEGER_OVERFLOW": INTEGER_OVERFLOW_PATTERN,
    "TAINTED_INPUT": TAINTED_INPUT_PATTERN,
    "WEAK_CRYPTO": WEAK_CRYPTO_PATTERN,
    "RACE_CONDITION": RACE_CONDITION_PATTERN,
    # Sprint 1 - 7 new high-priority patterns for Scenario 15
    "FORMAT_STRING": FORMAT_STRING_PATTERN,
    "HARDCODED_SECRETS": HARDCODED_SECRETS_PATTERN,
    "DOUBLE_FREE": DOUBLE_FREE_PATTERN,
    "UNINITIALIZED_VAR": UNINITIALIZED_VAR_PATTERN,
    "PATH_TRAVERSAL": PATH_TRAVERSAL_PATTERN,
    "ARRAY_BOUNDS": ARRAY_BOUNDS_PATTERN,
    "TYPE_CONFUSION": TYPE_CONFUSION_PATTERN,
    # Sprint 2 - 12 additional security patterns
    "INSECURE_DESERIALIZATION": INSECURE_DESERIALIZATION_PATTERN,
    "SSRF": SSRF_PATTERN,
    "XXE": XXE_PATTERN,
    "LOG_INJECTION": LOG_INJECTION_PATTERN,
    "FILE_RACE": FILE_RACE_PATTERN,
    "MISSING_AUTH": MISSING_AUTH_PATTERN,
    "IMPROPER_CERT": IMPROPER_CERT_PATTERN,
    "CLEARTEXT_STORAGE": CLEARTEXT_STORAGE_PATTERN,
    "INSUFFICIENT_ENTROPY": INSUFFICIENT_ENTROPY_PATTERN,
    "RESOURCE_LEAK": RESOURCE_LEAK_PATTERN,
    "EXEC_PATH_INJECTION": EXEC_PATH_INJECTION_PATTERN,
    "PRIV_ESCALATION": PRIV_ESCALATION_PATTERN,
}


# Import utility functions from _base module
from ._base import (
    get_pattern_by_id as _get_pattern_by_id,
    get_patterns_by_category as _get_patterns_by_category,
    get_patterns_by_severity as _get_patterns_by_severity,
    get_critical_patterns as _get_critical_patterns,
    get_all_cpgql_queries as _get_all_cpgql_queries,
    get_pattern_summary as _get_pattern_summary,
    validate_pattern,
    validate_all_patterns as _validate_all_patterns,
)


def get_pattern_by_id(pattern_id: str) -> SecurityPattern:
    """Get security pattern by ID"""
    return _get_pattern_by_id(SECURITY_PATTERNS, pattern_id)


def get_patterns_by_category(category: VulnerabilityCategory) -> List[SecurityPattern]:
    """Get all patterns in a specific category"""
    return _get_patterns_by_category(SECURITY_PATTERNS, category)


def get_patterns_by_severity(severity: VulnerabilitySeverity) -> List[SecurityPattern]:
    """Get all patterns with specific severity"""
    return _get_patterns_by_severity(SECURITY_PATTERNS, severity)


def get_critical_patterns() -> List[SecurityPattern]:
    """Get all critical severity patterns"""
    return _get_critical_patterns(SECURITY_PATTERNS)


def get_all_cpgql_queries() -> Dict[str, str]:
    """Get all CPGQL queries indexed by pattern name"""
    return _get_all_cpgql_queries(SECURITY_PATTERNS)


def get_pattern_summary() -> Dict[str, Any]:
    """Get summary statistics of security patterns"""
    return _get_pattern_summary(SECURITY_PATTERNS)


def validate_all_patterns() -> Dict[str, List[str]]:
    """Validate all patterns and return errors by pattern name"""
    return _validate_all_patterns(SECURITY_PATTERNS)


if __name__ == "__main__":
    # Print pattern summary
    summary = get_pattern_summary()
    print("Security Pattern Library Summary")
    print("=" * 50)
    print(f"Total Patterns: {summary['total_patterns']}")
    print(f"\nBy Category:")
    for cat, count in summary['by_category'].items():
        if count > 0:
            print(f"  {cat}: {count}")
    print(f"\nBy Severity:")
    for sev, count in summary['by_severity'].items():
        if count > 0:
            print(f"  {sev}: {count}")

    # Validate all patterns
    validation_results = validate_all_patterns()
    invalid = {k: v for k, v in validation_results.items() if v}
    if invalid:
        print(f"\n{len(invalid)} patterns have validation errors:")
        for name, errors in invalid.items():
            print(f"  {name}: {', '.join(errors)}")
    else:
        print(f"\nAll {len(SECURITY_PATTERNS)} patterns validated successfully!")
