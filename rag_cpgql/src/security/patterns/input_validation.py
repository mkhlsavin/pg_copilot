"""
Input Validation Vulnerability Patterns

Patterns for detecting integer overflow, tainted input, format string,
path traversal, insecure deserialization, and SSRF vulnerabilities.

CWE-190 (Integer Overflow), CWE-20 (Input Validation), CWE-134 (Format String),
CWE-22 (Path Traversal), CWE-502 (Deserialization), CWE-918 (SSRF)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


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
    """,
    test_cases=[
        {"name": "multiplication before malloc", "method": "allocate_array", "expected": True, "contains": ["malloc", "*"]}
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
            for (const char *p = input; *p; p++) {
                if (!isdigit(*p))
                    elog(ERROR, "invalid input: not a number");
            }
            // ...
        }
    """,
    test_cases=[
        {"name": "input handler without validation", "method": "handle_user_request", "expected": True, "contains": ["input"]}
    ]
)


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
          AND nc.code NOT LIKE '%"%'
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

        // SECURE
        printf("%s", user_input);     // User input treated as data
    """,
    test_cases=[
        {"name": "printf with variable format", "method": "log_message", "expected": True, "contains": ["printf"]}
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
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'PATH_TRAVERSAL' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('fopen', 'open', 'stat', 'access', 'unlink', 'remove',
                          'rename', 'chmod', 'chown', 'readdir', 'opendir')
          AND (nc.code LIKE '%sprintf%'
            OR nc.code LIKE '%strcat%'
            OR nc.code LIKE '%snprintf%')
          AND nc.code NOT LIKE '%realpath%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22"],
    remediation=(
        "1. Use realpath() to resolve canonical path\n"
        "2. Validate path doesn't contain .. sequences\n"
        "3. Check resolved path is within allowed directory\n"
        "4. Use allowlist of permitted files/directories\n"
        "5. Implement chroot jails for sensitive operations"
    ),
    example_code="""
        // VULNERABLE
        char path[256];
        sprintf(path, "/data/%s", user_file);
        FILE *f = fopen(path, "r");  // ../../../etc/passwd

        // SECURE
        char resolved[PATH_MAX];
        if (realpath(path, resolved) == NULL)
            elog(ERROR, "invalid path");
        if (strncmp(resolved, "/data/", 6) != 0)
            elog(ERROR, "path traversal detected");
    """,
    test_cases=[
        {"name": "sprintf path without validation", "method": "read_user_file", "expected": True, "contains": ["sprintf", "fopen"]}
    ]
)


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
        {"name": "pickle deserialization", "method": "load_user_data", "expected": True, "contains": ["pickle", "load"]}
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
        {"name": "curl with user URL", "method": "fetch_remote_data", "expected": True, "contains": ["curl"]}
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
        WHERE (nc.code LIKE '%(%*)%'
            OR nc.code LIKE '%reinterpret%'
            OR nc.code LIKE '%(void *)%'
            OR nc.code LIKE '%(char *)%')
          AND nc.code NOT LIKE '%sizeof%'
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
    """,
    test_cases=[
        {"name": "unsafe pointer cast", "method": "process_node", "expected": True, "contains": ["(", "*)", ")"]}
    ]
)


# Registry of input validation patterns
INPUT_VALIDATION_PATTERNS: Dict[str, SecurityPattern] = {
    "INTEGER_OVERFLOW": INTEGER_OVERFLOW_PATTERN,
    "TAINTED_INPUT": TAINTED_INPUT_PATTERN,
    "FORMAT_STRING": FORMAT_STRING_PATTERN,
    "PATH_TRAVERSAL": PATH_TRAVERSAL_PATTERN,
    "INSECURE_DESERIALIZATION": INSECURE_DESERIALIZATION_PATTERN,
    "SSRF": SSRF_PATTERN,
    "TYPE_CONFUSION": TYPE_CONFUSION_PATTERN,
}
