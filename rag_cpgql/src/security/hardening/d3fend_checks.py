"""
D3FEND Source Code Hardening Checks

Implements checks for all MITRE D3FEND Source Code Hardening techniques:
- D3-VI: Variable Initialization
- D3-CS: Credential Scrubbing
- D3-IRV: Integer Range Validation
- D3-PV: Pointer Validation (parent)
- D3-RN: Reference Nullification
- D3-TL: Trusted Library
- D3-VTV: Variable Type Validation
- D3-MBSV: Memory Block Start Validation
- D3-NPC: Null Pointer Checking
- D3-DLV: Domain Logic Validation
- D3-OLV: Operational Logic Validation
"""

from typing import Dict, List, Optional

from .base import (
    HardeningCheck,
    HardeningCategory,
    HardeningSeverity,
)


# =============================================================================
# D3-VI: Variable Initialization
# =============================================================================

VARIABLE_INITIALIZATION_CHECK = HardeningCheck(
    id="D3-VI-001",
    d3fend_id="D3-VI",
    d3fend_name="Variable Initialization",
    category=HardeningCategory.INITIALIZATION,
    severity=HardeningSeverity.HIGH,
    description="Detect variables that may be used before initialization",
    cpgql_query="""
        -- Find local variables that may be used uninitialized
        -- Uses CPG to find identifiers without reaching definitions
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.filename,
            nm.line_number,
            nm.code AS code_snippet,
            'UNINITIALIZED_VARIABLE' AS violation_type
        FROM nodes_method nm
        WHERE (
            -- C/C++ style: declarations without initializers
            nm.code LIKE '%int %[^=;]*;%'
            OR nm.code LIKE '%char %[^=;]*;%'
            OR nm.code LIKE '%void *%[^=;]*;%'
            OR nm.code LIKE '%size_t %[^=;]*;%'
        )
        AND nm.code NOT LIKE '%test%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-457", "CWE-908"],
    language_scope=["c", "cpp"],
    indicators=[
        "int x;", "char c;", "void *p;", "size_t n;",
        "uninitialized", "garbage value"
    ],
    good_patterns=[
        "= 0", "= NULL", "= {}", "= {0}",
        "memset(", "palloc0(", "calloc("
    ],
    remediation="""
Always initialize variables at declaration:
- Use = 0 for integers
- Use = NULL for pointers
- Use = {} or = {0} for structs/arrays
- Use calloc() or palloc0() for zero-initialized allocation
""",
    example_code="""
// VIOLATION
int count;
char *ptr;
process(count);  // Uses uninitialized value!

// COMPLIANT
int count = 0;
char *ptr = NULL;
process(count);
""",
    confidence_weight=0.7,
)


# =============================================================================
# D3-CS: Credential Scrubbing
# =============================================================================

CREDENTIAL_SCRUBBING_CHECK = HardeningCheck(
    id="D3-CS-001",
    d3fend_id="D3-CS",
    d3fend_name="Credential Scrubbing",
    category=HardeningCategory.CREDENTIAL_MANAGEMENT,
    severity=HardeningSeverity.CRITICAL,
    description="Detect hardcoded credentials in source code",
    cpgql_query="""
        -- Find hardcoded credentials using recursive AST traversal
        -- Searches in nodes_call (for os.environ.get with fallback) and nodes_literal
        WITH RECURSIVE ast_ancestry AS (
            -- Base case 1: CALL nodes with hardcoded fallback credentials
            -- Pattern: os.environ.get('SECRET_KEY', 'hardcoded_value')
            SELECT
                nc.":ID" as node_id,
                nc."CODE:string" as code,
                nc."LINE_NUMBER:int" as line_number,
                e.":START_ID" as parent_id,
                1 as depth
            FROM nodes_call nc
            LEFT JOIN edges_ast e ON e.":END_ID" = nc.":ID"
            WHERE (
                -- .get() call with fallback value for sensitive keys
                nc."NAME:string" = 'get'
                AND (
                    nc."CODE:string" LIKE '%SECRET_KEY%'
                    OR nc."CODE:string" LIKE '%API_KEY%'
                    OR nc."CODE:string" LIKE '%POSTGRES_PASS%'
                    OR nc."CODE:string" LIKE '%DB_PASSWORD%'
                    OR nc."CODE:string" LIKE '%PRIVATE_KEY%'
                    OR nc."CODE:string" LIKE '%ACCESS_KEY%'
                )
                -- Must have a fallback value (contains comma and quotes)
                AND nc."CODE:string" LIKE '%,%'
            )
            -- Exclude validation patterns
            AND nc."CODE:string" NOT LIKE '%AUTH_PASSWORD_VALIDATORS%'

            UNION ALL

            -- Base case 2: LITERAL nodes with actual embedded secrets
            SELECT
                nl.":ID" as node_id,
                nl."CODE:string" as code,
                nl."LINE_NUMBER:int" as line_number,
                e.":START_ID" as parent_id,
                1 as depth
            FROM nodes_literal nl
            LEFT JOIN edges_ast e ON e.":END_ID" = nl.":ID"
            WHERE (
                -- PEM keys / JWT tokens / API keys with known prefixes
                nl."CODE:string" LIKE '%-----BEGIN%KEY-----%'
                OR nl."CODE:string" LIKE '%sk-proj-%'
                OR nl."CODE:string" LIKE '%sk_live_%'
                OR nl."CODE:string" LIKE '%Bearer eyJ%'
                OR nl."CODE:string" LIKE '%ghp_%'  -- GitHub tokens
                OR nl."CODE:string" LIKE '%gho_%'
                OR nl."CODE:string" LIKE '%AKIA%'  -- AWS keys
            )

            UNION ALL

            -- Recursive case: traverse up the AST tree
            SELECT
                a.node_id,
                a.code,
                a.line_number,
                e.":START_ID",
                a.depth + 1
            FROM ast_ancestry a
            INNER JOIN edges_ast e ON e.":END_ID" = a.parent_id
            WHERE a.depth < 30 AND a.parent_id IS NOT NULL
        ),
        -- Find the first method in the chain (minimum depth)
        method_depth AS (
            SELECT
                node_id,
                MIN(depth) as min_depth
            FROM ast_ancestry
            WHERE parent_id IN (SELECT ":ID" FROM nodes_method)
            GROUP BY node_id
        )
        -- Final result with resolved context
        SELECT DISTINCT
            a.node_id as id,
            m."NAME:string" AS method_name,
            m."FILENAME:string" AS filename,
            a.line_number,
            a.code AS code_snippet,
            'HARDCODED_CREDENTIAL' AS violation_type
        FROM ast_ancestry a
        INNER JOIN method_depth md ON a.node_id = md.node_id AND a.depth = md.min_depth
        INNER JOIN nodes_method m ON m.":ID" = a.parent_id
        WHERE m."FILENAME:string" NOT LIKE '%test%'
          AND m."NAME:string" NOT LIKE 'test_%'
        ORDER BY m."FILENAME:string", a.line_number
        LIMIT 100
    """,
    cwe_ids=["CWE-798", "CWE-259", "CWE-321"],
    language_scope=["*"],  # Applies to all languages
    indicators=[
        "password =", "passwd =", "api_key =", "secret =",
        "token =", "private_key =", "auth_token =",
        '"password"', "'secret'"
    ],
    good_patterns=[
        "getenv(", "GetConfigOption(", "os.environ",
        "secrets.get", "vault.read", "config.get"
    ],
    remediation="""
Never hardcode credentials in source code:
- Use environment variables: getenv("PASSWORD")
- Use configuration files (not committed to VCS)
- Use secret management services (Vault, AWS Secrets Manager)
- Use credential injection at deployment time
""",
    example_code="""
// VIOLATION
const char *password = "mysecretpassword";
const char *api_key = "sk-1234567890abcdef";

// COMPLIANT
const char *password = getenv("DB_PASSWORD");
const char *api_key = GetConfigOption("api.key");
""",
    confidence_weight=0.9,
)


# =============================================================================
# D3-IRV: Integer Range Validation
# =============================================================================

INTEGER_RANGE_VALIDATION_CHECK = HardeningCheck(
    id="D3-IRV-001",
    d3fend_id="D3-IRV",
    d3fend_name="Integer Range Validation",
    category=HardeningCategory.INTEGER_SAFETY,
    severity=HardeningSeverity.HIGH,
    description="Detect integer operations that may overflow without validation",
    cpgql_query="""
        -- Find size calculations in allocations without overflow checks
        SELECT DISTINCT
            nc.id,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'INTEGER_OVERFLOW_RISK' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN ('malloc', 'calloc', 'realloc', 'palloc', 'repalloc',
                          'MemoryContextAlloc', 'kmalloc', 'vmalloc')
        AND (nc.code LIKE '%*%' OR nc.code LIKE '%+%')
        AND nc.code NOT LIKE '%overflow%'
        AND nc.code NOT LIKE '%SIZE_MAX%'
        AND nc.code NOT LIKE '%safe_mul%'
        AND nc.code NOT LIKE '%pg_mul_s%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-190", "CWE-191", "CWE-680"],
    language_scope=["c", "cpp"],
    indicators=[
        "malloc(n * size)", "palloc(count * sizeof)",
        "size_t + size_t", "unsigned * unsigned"
    ],
    good_patterns=[
        "pg_add_s32_overflow", "pg_mul_s32_overflow",
        "__builtin_mul_overflow", "safe_mul",
        "SIZE_MAX / sizeof", "mul_size"
    ],
    remediation="""
Validate integer operations before use in allocations:
- Check for overflow before multiplication: if (n > SIZE_MAX / sizeof(x))
- Use safe math functions: pg_mul_s32_overflow(), __builtin_mul_overflow()
- Use dedicated size calculation functions: mul_size()
- Validate input ranges before arithmetic operations
""",
    example_code="""
// VIOLATION
void *p = malloc(n * sizeof(struct item));  // Overflow if n is large!

// COMPLIANT
if (n > SIZE_MAX / sizeof(struct item))
    return NULL;
void *p = malloc(n * sizeof(struct item));

// Or using safe functions
size_t total;
if (pg_mul_s64_overflow(n, sizeof(struct item), &total))
    return NULL;
void *p = malloc(total);
""",
    confidence_weight=0.8,
)


# =============================================================================
# D3-RN: Reference Nullification
# =============================================================================

REFERENCE_NULLIFICATION_CHECK = HardeningCheck(
    id="D3-RN-001",
    d3fend_id="D3-RN",
    d3fend_name="Reference Nullification",
    category=HardeningCategory.MEMORY_SAFETY,
    severity=HardeningSeverity.HIGH,
    description="Detect freed pointers that are not nullified (use-after-free risk)",
    cpgql_query="""
        -- Find free() calls without subsequent pointer nullification
        SELECT DISTINCT
            nc.id,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'MISSING_NULLIFICATION' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN ('free', 'pfree', 'delete', 'kfree',
                          'MemoryContextDelete', 'FreeFile')
        AND nm.code NOT LIKE '%NULL%'
        AND nm.code NOT LIKE '%nullptr%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-416", "CWE-825"],
    language_scope=["c", "cpp"],
    indicators=[
        "free(ptr);", "pfree(p);", "delete obj;",
        "MemoryContextDelete(ctx);"
    ],
    good_patterns=[
        "ptr = NULL;", "p = nullptr;",
        "free(ptr); ptr = NULL;",
        "SAFE_FREE(", "pfree_and_null("
    ],
    remediation="""
Always nullify pointers after freeing:
- Set pointer to NULL immediately after free()
- Use macros that combine free and nullification
- Consider using smart pointers in C++
- Document ownership clearly in APIs
""",
    example_code="""
// VIOLATION
free(ptr);
// ptr still contains old address - use-after-free risk!
if (ptr != NULL) use(ptr);  // BUG: still enters!

// COMPLIANT
free(ptr);
ptr = NULL;  // Safe: subsequent NULL check works

// Or use a macro
#define SAFE_FREE(p) do { free(p); (p) = NULL; } while(0)
SAFE_FREE(ptr);
""",
    confidence_weight=0.75,
)


# =============================================================================
# D3-TL: Trusted Library
# =============================================================================

TRUSTED_LIBRARY_CHECK = HardeningCheck(
    id="D3-TL-001",
    d3fend_id="D3-TL",
    d3fend_name="Trusted Library",
    category=HardeningCategory.LIBRARY_SAFETY,
    severity=HardeningSeverity.HIGH,
    description="Detect use of deprecated/unsafe library functions",
    cpgql_query="""
        -- Find calls to known unsafe/deprecated functions
        SELECT DISTINCT
            nc.id,
            nc.name AS unsafe_function,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'UNSAFE_FUNCTION' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN (
            -- Unsafe string functions
            'strcpy', 'strcat', 'sprintf', 'vsprintf', 'gets',
            'scanf', 'sscanf', 'fscanf',
            -- Deprecated/unsafe functions
            'strtok', 'tmpnam', 'mktemp', 'tempnam',
            -- Unsafe random
            'rand', 'srand', 'random',
            -- Wide char unsafe
            'wcscpy', 'wcscat', 'swprintf'
        )
        AND nm.name NOT LIKE 'test_%'
        AND nm.filename NOT LIKE '%test%'
        LIMIT 100
    """,
    cwe_ids=["CWE-676", "CWE-242", "CWE-120"],
    language_scope=["c", "cpp"],
    indicators=[
        "strcpy(", "strcat(", "sprintf(", "gets(",
        "scanf(", "strtok(", "tmpnam(", "rand("
    ],
    good_patterns=[
        "strncpy(", "strlcpy(", "snprintf(",
        "fgets(", "strtok_r(", "mkstemp(",
        "arc4random(", "getrandom("
    ],
    remediation="""
Replace unsafe functions with safe alternatives:
- strcpy → strncpy, strlcpy, or snprintf
- strcat → strncat, strlcat
- sprintf → snprintf
- gets → fgets
- scanf → fgets + sscanf with length limits
- strtok → strtok_r (thread-safe)
- tmpnam → mkstemp (secure temp files)
- rand → arc4random, getrandom, /dev/urandom
""",
    example_code="""
// VIOLATION
char buf[100];
strcpy(buf, user_input);    // Buffer overflow!
sprintf(buf, "%s", data);   // No bounds checking!
gets(buf);                  // Always unsafe!

// COMPLIANT
char buf[100];
strncpy(buf, user_input, sizeof(buf) - 1);
buf[sizeof(buf) - 1] = '\\0';
snprintf(buf, sizeof(buf), "%s", data);
fgets(buf, sizeof(buf), stdin);
""",
    confidence_weight=0.95,
)


# =============================================================================
# D3-VTV: Variable Type Validation
# =============================================================================

VARIABLE_TYPE_VALIDATION_CHECK = HardeningCheck(
    id="D3-VTV-001",
    d3fend_id="D3-VTV",
    d3fend_name="Variable Type Validation",
    category=HardeningCategory.TYPE_SAFETY,
    severity=HardeningSeverity.MEDIUM,
    description="Detect potentially unsafe type casts without validation",
    cpgql_query="""
        -- Find suspicious casts that may indicate type confusion
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.filename,
            nm.line_number,
            nm.code AS code_snippet,
            'UNSAFE_CAST' AS violation_type
        FROM nodes_method nm
        WHERE (
            nm.code LIKE '%(void *)%'
            OR nm.code LIKE '%(void*)%'
            OR nm.code LIKE '%(char *)%'
            OR nm.code LIKE '%(char*)%'
            OR nm.code LIKE '%reinterpret_cast%'
            OR nm.code LIKE '%(int *)%'
            OR nm.code LIKE '%(int*)%'
        )
        AND nm.code NOT LIKE '%sizeof%'
        AND nm.code NOT LIKE '%Assert%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-843", "CWE-704", "CWE-588"],
    language_scope=["c", "cpp"],
    indicators=[
        "(void *)", "(char *)", "reinterpret_cast",
        "(int *)", "C-style cast"
    ],
    good_patterns=[
        "static_cast<>", "dynamic_cast<>",
        "IsA(", "nodeTag(", "castNode(",
        "Assert(", "CHECK_TYPE("
    ],
    remediation="""
Validate types before casting:
- Use runtime type checks where available
- In C++, prefer static_cast/dynamic_cast over C-style casts
- Add assertions to verify expected types
- Use tagged unions with type discriminators
- Document type expectations in comments
""",
    example_code="""
// VIOLATION
void process(void *data) {
    struct MyStruct *s = (struct MyStruct *)data;  // Type not verified!
    s->field = 42;
}

// COMPLIANT (with type tag)
void process(Tagged *data) {
    Assert(data->type == TYPE_MYSTRUCT);
    struct MyStruct *s = (struct MyStruct *)data;
    s->field = 42;
}

// COMPLIANT (C++ with RTTI)
void process(Base *data) {
    MyStruct *s = dynamic_cast<MyStruct*>(data);
    if (s) s->field = 42;
}
""",
    confidence_weight=0.6,
)


# =============================================================================
# D3-MBSV: Memory Block Start Validation
# =============================================================================

MEMORY_BLOCK_START_VALIDATION_CHECK = HardeningCheck(
    id="D3-MBSV-001",
    d3fend_id="D3-MBSV",
    d3fend_name="Memory Block Start Validation",
    category=HardeningCategory.POINTER_SAFETY,
    severity=HardeningSeverity.MEDIUM,
    description="Detect pointer arithmetic that may result in invalid memory references",
    cpgql_query="""
        -- Find pointer arithmetic operations
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.filename,
            nm.line_number,
            nm.code AS code_snippet,
            'POINTER_ARITHMETIC' AS violation_type
        FROM nodes_method nm
        WHERE (
            nm.code LIKE '%ptr + %'
            OR nm.code LIKE '%ptr - %'
            OR nm.code LIKE '%ptr++%'
            OR nm.code LIKE '%ptr--%'
            OR nm.code LIKE '%++ptr%'
            OR nm.code LIKE '%--ptr%'
            OR nm.code LIKE '%p + %'
            OR nm.code LIKE '%p - %'
        )
        AND nm.code NOT LIKE '%sizeof%'
        AND nm.code NOT LIKE '%bounds%'
        AND nm.code NOT LIKE '%limit%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-119", "CWE-787", "CWE-823"],
    language_scope=["c", "cpp"],
    indicators=[
        "ptr + offset", "ptr - offset", "ptr++", "ptr--",
        "array + n", "p += n"
    ],
    good_patterns=[
        "< end", "<= limit", "< size",
        "bounds_check", "ARRAY_SIZE",
        "offsetof(", "container_of("
    ],
    remediation="""
Validate pointer arithmetic results:
- Always check bounds before dereferencing
- Track start and end pointers for arrays
- Use offsetof() for struct member access
- Consider using container_of() for type-safe access
- Use array indexing with bounds checks instead of pointer arithmetic
""",
    example_code="""
// VIOLATION
char *p = buffer;
p += user_offset;  // May go out of bounds!
*p = value;

// COMPLIANT
char *p = buffer;
if (user_offset < buffer_size) {
    p += user_offset;
    *p = value;
}

// Or using end pointer
char *p = buffer;
char *end = buffer + buffer_size;
if (p + user_offset < end) {
    p += user_offset;
    *p = value;
}
""",
    confidence_weight=0.5,
)


# =============================================================================
# D3-NPC: Null Pointer Checking
# =============================================================================

NULL_POINTER_CHECKING = HardeningCheck(
    id="D3-NPC-001",
    d3fend_id="D3-NPC",
    d3fend_name="Null Pointer Checking",
    category=HardeningCategory.POINTER_SAFETY,
    severity=HardeningSeverity.HIGH,
    description="Detect allocation results used without NULL checking",
    cpgql_query="""
        -- Find allocation calls without subsequent NULL checks
        SELECT DISTINCT
            nc.id,
            nc.name AS alloc_function,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'MISSING_NULL_CHECK' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN ('malloc', 'calloc', 'realloc', 'palloc',
                          'repalloc', 'MemoryContextAlloc', 'strdup',
                          'kmalloc', 'vmalloc', 'kzalloc')
        AND nm.code NOT LIKE '%if%NULL%'
        AND nm.code NOT LIKE '%if%!%'
        AND nm.code NOT LIKE '%Assert%'
        AND nm.code NOT LIKE '%elog%ERROR%'
        AND nm.code NOT LIKE '%ereport%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-476", "CWE-690"],
    language_scope=["c", "cpp"],
    indicators=[
        "malloc(", "calloc(", "realloc(",
        "palloc(", "strdup(", "kmalloc("
    ],
    good_patterns=[
        "if (ptr == NULL)", "if (!ptr)",
        "if (ptr != NULL)", "Assert(ptr)",
        "ereport(ERROR", "elog(ERROR"
    ],
    remediation="""
Always check allocation results before use:
- Check for NULL immediately after allocation
- Handle allocation failures appropriately
- Use palloc() in PostgreSQL (auto-raises error on failure)
- Consider using non-failing allocator wrappers
""",
    example_code="""
// VIOLATION
char *buf = malloc(size);
strcpy(buf, data);  // Crash if malloc returned NULL!

// COMPLIANT
char *buf = malloc(size);
if (buf == NULL) {
    return ERROR_OUT_OF_MEMORY;
}
strcpy(buf, data);

// PostgreSQL style (palloc never returns NULL)
char *buf = palloc(size);  // Raises ERROR on failure
strcpy(buf, data);
""",
    confidence_weight=0.85,
)


# =============================================================================
# D3-DLV: Domain Logic Validation
# =============================================================================

DOMAIN_LOGIC_VALIDATION_CHECK = HardeningCheck(
    id="D3-DLV-001",
    d3fend_id="D3-DLV",
    d3fend_name="Domain Logic Validation",
    category=HardeningCategory.DOMAIN_VALIDATION,
    severity=HardeningSeverity.MEDIUM,
    description="Detect operations on domain-sensitive data without validation",
    cpgql_query="""
        -- Find domain-sensitive function calls without validation context
        -- This is a placeholder - domain plugins should provide specific patterns
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'MISSING_DOMAIN_VALIDATION' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN (
            -- Database operations
            'SPI_execute', 'PQexec', 'mysql_query', 'sqlite3_exec',
            -- File operations with user paths
            'fopen', 'open', 'unlink', 'remove',
            -- Network operations
            'connect', 'bind', 'sendto'
        )
        AND nm.code NOT LIKE '%valid%'
        AND nm.code NOT LIKE '%check%'
        AND nm.code NOT LIKE '%sanitize%'
        AND nm.code NOT LIKE '%escape%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-20", "CWE-1287"],
    language_scope=["*"],  # Applies to all languages
    indicators=[
        "SPI_execute(", "fopen(user_path",
        "connect(", "query(user_input"
    ],
    good_patterns=[
        "validate(", "check(", "sanitize(",
        "escape(", "is_valid(", "verify("
    ],
    remediation="""
Validate domain-specific inputs and state:
- Validate user inputs against domain rules
- Check preconditions before sensitive operations
- Sanitize/escape data appropriately for the context
- Verify object state before operations
- Implement proper input validation functions
""",
    example_code="""
// VIOLATION
void process_file(const char *path) {
    FILE *f = fopen(path, "r");  // Path not validated!
}

// COMPLIANT
void process_file(const char *path) {
    if (!is_valid_path(path)) {
        return ERROR_INVALID_PATH;
    }
    if (!path_is_allowed(path)) {
        return ERROR_ACCESS_DENIED;
    }
    FILE *f = fopen(path, "r");
}
""",
    confidence_weight=0.5,
)


# =============================================================================
# D3-OLV: Operational Logic Validation
# =============================================================================

OPERATIONAL_LOGIC_VALIDATION_CHECK = HardeningCheck(
    id="D3-OLV-001",
    d3fend_id="D3-OLV",
    d3fend_name="Operational Logic Validation",
    category=HardeningCategory.OPERATIONAL_VALIDATION,
    severity=HardeningSeverity.MEDIUM,
    description="Detect state-changing operations without operational state validation",
    cpgql_query="""
        -- Find state-changing operations without state checks
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nm.name AS method_name,
            nm.filename,
            nc.line_number,
            nc.code AS code_snippet,
            'MISSING_STATE_VALIDATION' AS violation_type
        FROM nodes_call nc
        JOIN nodes_method nm ON nc.method_id = nm.id
        WHERE nc.name IN (
            -- State transitions
            'SetState', 'ChangeMode', 'StartTransaction', 'CommitTransaction',
            -- Resource state changes
            'Acquire', 'Release', 'Lock', 'Unlock',
            -- Lifecycle operations
            'Initialize', 'Shutdown', 'Reset', 'Close'
        )
        AND nm.code NOT LIKE '%state%'
        AND nm.code NOT LIKE '%mode%'
        AND nm.code NOT LIKE '%status%'
        AND nm.code NOT LIKE '%Assert%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 100
    """,
    cwe_ids=["CWE-754", "CWE-1265"],
    language_scope=["*"],  # Applies to all languages
    indicators=[
        "SetState(", "ChangeMode(", "StartTransaction(",
        "Lock(", "Initialize("
    ],
    good_patterns=[
        "if (state ==", "Assert(state",
        "CHECK_STATE(", "verify_state(",
        "current_state ==", "mode =="
    ],
    remediation="""
Validate operational state before transitions:
- Check current state before state changes
- Verify preconditions for lifecycle operations
- Assert expected states in debug builds
- Implement state machine validation
- Log state transitions for debugging
""",
    example_code="""
// VIOLATION
void close_connection(Connection *conn) {
    conn->state = CLOSED;  // What if already closed?
    free(conn->buffer);
}

// COMPLIANT
void close_connection(Connection *conn) {
    Assert(conn->state == OPEN || conn->state == ERROR);
    if (conn->state == CLOSED) {
        elog(WARNING, "Connection already closed");
        return;
    }
    conn->state = CLOSING;
    free(conn->buffer);
    conn->buffer = NULL;
    conn->state = CLOSED;
}
""",
    confidence_weight=0.5,
)


# =============================================================================
# D3-PV: Pointer Validation (Parent Technique)
# =============================================================================

POINTER_VALIDATION_CHECK = HardeningCheck(
    id="D3-PV-001",
    d3fend_id="D3-PV",
    d3fend_name="Pointer Validation",
    category=HardeningCategory.POINTER_SAFETY,
    severity=HardeningSeverity.HIGH,
    description="Detect pointer dereferences without validation (combines NPC and MBSV)",
    cpgql_query="""
        -- Find pointer dereferences without validation
        -- This is a general check; D3-NPC and D3-MBSV provide specific checks
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.filename,
            nm.line_number,
            nm.code AS code_snippet,
            'UNVALIDATED_POINTER' AS violation_type
        FROM nodes_method nm
        WHERE (
            nm.code LIKE '%->%'
            OR nm.code LIKE '%*ptr%'
            OR nm.code LIKE '%*p %'
        )
        AND nm.code NOT LIKE '%if%'
        AND nm.code NOT LIKE '%NULL%'
        AND nm.code NOT LIKE '%Assert%'
        AND nm.name NOT LIKE 'test_%'
        LIMIT 50
    """,
    cwe_ids=["CWE-476", "CWE-119", "CWE-824"],
    language_scope=["c", "cpp"],
    indicators=[
        "ptr->", "*ptr", "p->member"
    ],
    good_patterns=[
        "if (ptr)", "if (ptr != NULL)",
        "Assert(ptr)", "PointerIsValid("
    ],
    remediation="""
Validate pointers before use:
- Check for NULL before dereferencing
- Validate pointer is within expected bounds
- Use defensive macros like PointerIsValid()
- Consider using references in C++ where appropriate
""",
    example_code="""
// VIOLATION
int get_value(struct Item *item) {
    return item->value;  // Crash if item is NULL!
}

// COMPLIANT
int get_value(struct Item *item) {
    if (item == NULL) {
        return -1;
    }
    return item->value;
}
""",
    confidence_weight=0.6,
)


# =============================================================================
# Registry of all checks
# =============================================================================

HARDENING_CHECKS: Dict[str, HardeningCheck] = {
    # D3-VI: Variable Initialization
    "D3-VI": VARIABLE_INITIALIZATION_CHECK,
    "D3-VI-001": VARIABLE_INITIALIZATION_CHECK,

    # D3-CS: Credential Scrubbing
    "D3-CS": CREDENTIAL_SCRUBBING_CHECK,
    "D3-CS-001": CREDENTIAL_SCRUBBING_CHECK,

    # D3-IRV: Integer Range Validation
    "D3-IRV": INTEGER_RANGE_VALIDATION_CHECK,
    "D3-IRV-001": INTEGER_RANGE_VALIDATION_CHECK,

    # D3-RN: Reference Nullification
    "D3-RN": REFERENCE_NULLIFICATION_CHECK,
    "D3-RN-001": REFERENCE_NULLIFICATION_CHECK,

    # D3-TL: Trusted Library
    "D3-TL": TRUSTED_LIBRARY_CHECK,
    "D3-TL-001": TRUSTED_LIBRARY_CHECK,

    # D3-VTV: Variable Type Validation
    "D3-VTV": VARIABLE_TYPE_VALIDATION_CHECK,
    "D3-VTV-001": VARIABLE_TYPE_VALIDATION_CHECK,

    # D3-MBSV: Memory Block Start Validation
    "D3-MBSV": MEMORY_BLOCK_START_VALIDATION_CHECK,
    "D3-MBSV-001": MEMORY_BLOCK_START_VALIDATION_CHECK,

    # D3-NPC: Null Pointer Checking
    "D3-NPC": NULL_POINTER_CHECKING,
    "D3-NPC-001": NULL_POINTER_CHECKING,

    # D3-DLV: Domain Logic Validation
    "D3-DLV": DOMAIN_LOGIC_VALIDATION_CHECK,
    "D3-DLV-001": DOMAIN_LOGIC_VALIDATION_CHECK,

    # D3-OLV: Operational Logic Validation
    "D3-OLV": OPERATIONAL_LOGIC_VALIDATION_CHECK,
    "D3-OLV-001": OPERATIONAL_LOGIC_VALIDATION_CHECK,

    # D3-PV: Pointer Validation (parent)
    "D3-PV": POINTER_VALIDATION_CHECK,
    "D3-PV-001": POINTER_VALIDATION_CHECK,
}


# List of all D3FEND technique IDs
D3FEND_TECHNIQUE_IDS = [
    "D3-VI", "D3-CS", "D3-IRV", "D3-PV", "D3-RN",
    "D3-TL", "D3-VTV", "D3-MBSV", "D3-NPC", "D3-DLV", "D3-OLV"
]


def get_check_by_id(check_id: str) -> Optional[HardeningCheck]:
    """Get a hardening check by its ID."""
    return HARDENING_CHECKS.get(check_id)


def get_checks_by_d3fend_id(d3fend_id: str) -> List[HardeningCheck]:
    """Get all checks for a D3FEND technique ID."""
    return [c for c in HARDENING_CHECKS.values() if c.d3fend_id == d3fend_id]


def get_checks_by_category(category: HardeningCategory) -> List[HardeningCheck]:
    """Get all checks for a category."""
    seen = set()
    result = []
    for check in HARDENING_CHECKS.values():
        if check.category == category and check.id not in seen:
            seen.add(check.id)
            result.append(check)
    return result


def get_all_checks() -> List[HardeningCheck]:
    """Get all unique hardening checks."""
    seen = set()
    result = []
    for check in HARDENING_CHECKS.values():
        if check.id not in seen:
            seen.add(check.id)
            result.append(check)
    return result


def get_checks_for_language(language: str) -> List[HardeningCheck]:
    """Get all checks applicable to a specific language."""
    return [c for c in get_all_checks() if c.applies_to_language(language)]
