"""
Memory Safety Vulnerability Patterns

Patterns for detecting buffer overflows, use-after-free, memory leaks,
null pointer dereferences, double-free, uninitialized variables, and
array bounds violations.

CWE-120 (Buffer Overflow), CWE-416 (Use After Free), CWE-401 (Memory Leak),
CWE-476 (NULL Pointer Dereference), CWE-415 (Double Free), CWE-457 (Uninitialized)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


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
        {"name": "strcpy usage", "method": "copy_string", "expected": True, "contains": ["strcpy"]},
        {"name": "strncpy usage", "method": "safe_copy_string", "expected": False, "contains": ["strncpy"]}
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
        {"name": "sprintf usage", "method": "format_message", "expected": True, "contains": ["sprintf"]}
    ]
)


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
        {"name": "free without NULL assignment", "method": "cleanup_node", "expected": True, "contains": ["pfree"]}
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
        {"name": "malloc without free", "method": "allocate_buffer", "expected": True, "contains": ["palloc"]}
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
    """,
    test_cases=[
        {"name": "malloc without NULL check", "method": "create_node", "expected": True, "contains": ["malloc"]}
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
    """,
    test_cases=[
        {"name": "multiple free calls", "method": "cleanup_resources", "expected": True, "contains": ["free", "free"]}
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
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'UNINITIALIZED_VAR' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_method nm
        WHERE nm.code LIKE '%char %[%]%'
           OR nm.code LIKE '%int %*%'
           OR nm.code LIKE '%struct %*%'
        AND nm.code NOT LIKE '%=%'
        AND nm.code NOT LIKE '%{%'
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
        {"name": "uninitialized buffer", "method": "process_request", "expected": True, "contains": ["char", "["]}
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
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'ARRAY_OUT_OF_BOUNDS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_method nm
        WHERE nm.code LIKE '%[%]%'
          AND (nm.code LIKE '%[i]%'
            OR nm.code LIKE '%[index]%'
            OR nm.code LIKE '%[idx]%'
            OR nm.code LIKE '%[n]%')
          AND nm.code NOT LIKE '%if%<%'
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
        {"name": "array access without bounds check", "method": "get_element", "expected": True, "contains": ["[", "]"]}
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
        {"name": "file not closed on error", "method": "read_config_file", "expected": True, "contains": ["fopen"]}
    ]
)


# Registry of memory safety patterns
MEMORY_PATTERNS: Dict[str, SecurityPattern] = {
    "BUFFER_OVERFLOW_STRCPY": BUFFER_OVERFLOW_STRCPY_PATTERN,
    "BUFFER_OVERFLOW_SPRINTF": BUFFER_OVERFLOW_SPRINTF_PATTERN,
    "USE_AFTER_FREE": USE_AFTER_FREE_PATTERN,
    "MEMORY_LEAK": MEMORY_LEAK_PATTERN,
    "NULL_POINTER_DEREFERENCE": NULL_POINTER_DEREFERENCE_PATTERN,
    "DOUBLE_FREE": DOUBLE_FREE_PATTERN,
    "UNINITIALIZED_VAR": UNINITIALIZED_VAR_PATTERN,
    "ARRAY_BOUNDS": ARRAY_BOUNDS_PATTERN,
    "RESOURCE_LEAK": RESOURCE_LEAK_PATTERN,
}
