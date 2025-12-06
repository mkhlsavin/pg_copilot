# Security and Dead Code Pattern Reference

This document provides a comprehensive reference for all detection patterns available in the Code Review CLI.

## Security Patterns (30 Total)

### Summary by Severity

| Severity | Count | Patterns |
|----------|-------|----------|
| CRITICAL | 8 | SQL Injection, Command Injection, Buffer Overflow (strcpy), Use-After-Free, Double Free, Format String, Exec Path Injection, Privilege Escalation |
| HIGH | 17 | Buffer Overflow (sprintf), Uninitialized Var, Integer Overflow, Tainted Input, Weak Crypto, Hardcoded Secrets, Path Traversal, Array Bounds, Type Confusion, Deserialization, SSRF, XXE, File Race, Missing Auth, Improper Cert, Cleartext Storage, Insufficient Entropy |
| MEDIUM | 5 | Memory Leak, NULL Pointer, Race Condition, Log Injection, Resource Leak |

### Summary by Category

| Category | Patterns |
|----------|----------|
| Injection | SQL, Command, XXE, Log, Exec Path |
| Memory Safety | Buffer Overflow (2), UAF, Leak, NULL Ptr, Double Free, Uninitialized |
| Input Validation | Integer Overflow, Tainted Input, Format String, Deserialization, SSRF |
| Cryptography | Weak Crypto, Improper Cert, Cleartext Storage, Insufficient Entropy |
| Authentication | Hardcoded Secrets, Missing Auth |
| Access Control | Path Traversal, Privilege Escalation |
| Concurrency | Race Condition, File Race |
| Resource Management | Resource Leak |
| Type Safety | Array Bounds, Type Confusion |

---

### Original Patterns (11)

#### SQL_INJECTION (CRITICAL)
- **ID:** `SQL_INJECTION_001`
- **CWE:** CWE-89
- **Description:** SQL injection via dynamic query construction with string concatenation
- **Detects:** SPI_execute, SPI_exec with sprintf/strcat

#### COMMAND_INJECTION (CRITICAL)
- **ID:** `CMD_INJECTION_001`
- **CWE:** CWE-78, CWE-88
- **Description:** Command injection via system/exec calls
- **Detects:** system(), popen(), exec* with user input

#### BUFFER_OVERFLOW_STRCPY (CRITICAL)
- **ID:** `BUFFER_OVERFLOW_001`
- **CWE:** CWE-120, CWE-676
- **Description:** Buffer overflow via unsafe string functions
- **Detects:** strcpy, strcat, gets, sprintf, vsprintf

#### BUFFER_OVERFLOW_SPRINTF (HIGH)
- **ID:** `BUFFER_OVERFLOW_002`
- **CWE:** CWE-120, CWE-134
- **Description:** Buffer overflow via sprintf without bounds
- **Detects:** sprintf, vsprintf without size limits

#### USE_AFTER_FREE (CRITICAL)
- **ID:** `MEMORY_SAFETY_001`
- **CWE:** CWE-416
- **Description:** Accessing freed memory
- **Detects:** Memory access after free/pfree

#### MEMORY_LEAK (MEDIUM)
- **ID:** `MEMORY_SAFETY_002`
- **CWE:** CWE-401
- **Description:** Allocated memory not freed
- **Detects:** malloc/palloc without corresponding free

#### NULL_POINTER_DEREFERENCE (MEDIUM)
- **ID:** `MEMORY_SAFETY_003`
- **CWE:** CWE-476
- **Description:** Dereferencing NULL pointers
- **Detects:** Pointer use without NULL check

#### INTEGER_OVERFLOW (HIGH)
- **ID:** `INPUT_VALIDATION_001`
- **CWE:** CWE-190, CWE-680
- **Description:** Integer overflow in size calculations
- **Detects:** Unchecked arithmetic in allocations

#### TAINTED_INPUT (HIGH)
- **ID:** `INPUT_VALIDATION_002`
- **CWE:** CWE-20, CWE-129
- **Description:** User input without validation
- **Detects:** Input used in sensitive operations

#### WEAK_CRYPTO (HIGH)
- **ID:** `CRYPTO_001`
- **CWE:** CWE-327, CWE-328
- **Description:** Weak cryptographic algorithms
- **Detects:** MD5, SHA1, DES usage

#### RACE_CONDITION (MEDIUM)
- **ID:** `CONCURRENCY_001`
- **CWE:** CWE-367
- **Description:** Time-of-check time-of-use races
- **Detects:** TOCTOU patterns in shared resources

---

### Sprint 1 Patterns (7)

#### FORMAT_STRING (CRITICAL)
- **ID:** `FORMAT_STRING_001`
- **CWE:** CWE-134
- **Description:** User-controlled format string arguments
- **Detects:** printf family with user-controlled format

#### HARDCODED_SECRETS (HIGH)
- **ID:** `HARDCODED_SECRETS_001`
- **CWE:** CWE-798, CWE-259
- **Description:** Hardcoded passwords and API keys
- **Detects:** Literal strings containing password/key/token

#### DOUBLE_FREE (CRITICAL)
- **ID:** `DOUBLE_FREE_001`
- **CWE:** CWE-415
- **Description:** Freeing same memory twice
- **Detects:** Multiple free calls on same pointer

#### UNINITIALIZED_VAR (HIGH)
- **ID:** `UNINITIALIZED_VAR_001`
- **CWE:** CWE-457, CWE-908
- **Description:** Using uninitialized variables
- **Detects:** Variable use before assignment

#### PATH_TRAVERSAL (HIGH)
- **ID:** `PATH_TRAVERSAL_001`
- **CWE:** CWE-22, CWE-23
- **Description:** Path traversal via user input
- **Detects:** File paths with user-controlled components

#### ARRAY_BOUNDS (HIGH)
- **ID:** `ARRAY_BOUNDS_001`
- **CWE:** CWE-129, CWE-787
- **Description:** Array index out of bounds
- **Detects:** Array access without bounds checking

#### TYPE_CONFUSION (HIGH)
- **ID:** `TYPE_CONFUSION_001`
- **CWE:** CWE-843, CWE-704
- **Description:** Type confusion via unsafe casts
- **Detects:** Pointer casts without type validation

---

### Sprint 2 Patterns (12)

#### INSECURE_DESERIALIZATION (CRITICAL)
- **ID:** `DESERIALIZATION_001`
- **CWE:** CWE-502
- **Description:** Deserializing untrusted data leading to RCE
- **Detects:** deserialize, unserialize, readobject, pickle.load

#### SSRF (HIGH)
- **ID:** `SSRF_001`
- **CWE:** CWE-918
- **Description:** Server-side request forgery
- **Detects:** curl, urlopen, http_request with user URLs

#### XXE (HIGH)
- **ID:** `XXE_001`
- **CWE:** CWE-611
- **Description:** XML external entity injection
- **Detects:** XML parsing without entity restrictions

#### LOG_INJECTION (MEDIUM)
- **ID:** `LOG_INJECTION_001`
- **CWE:** CWE-117
- **Description:** Log forging via unsanitized input
- **Detects:** Logging with user-controlled content

#### FILE_RACE (HIGH)
- **ID:** `RACE_FILE_001`
- **CWE:** CWE-362, CWE-367
- **Description:** File operation race conditions
- **Detects:** access() followed by open/unlink

#### MISSING_AUTH (HIGH)
- **ID:** `MISSING_AUTH_001`
- **CWE:** CWE-306
- **Description:** Missing authentication for critical functions
- **Detects:** Sensitive operations without auth checks

#### IMPROPER_CERT (HIGH)
- **ID:** `IMPROPER_CERT_001`
- **CWE:** CWE-295
- **Description:** Improper SSL/TLS certificate validation
- **Detects:** SSL_VERIFY_NONE, disabled hostname check

#### CLEARTEXT_STORAGE (HIGH)
- **ID:** `CLEARTEXT_STORAGE_001`
- **CWE:** CWE-312, CWE-313
- **Description:** Storing sensitive data unencrypted
- **Detects:** Password/secret writes without encryption

#### INSUFFICIENT_ENTROPY (HIGH)
- **ID:** `INSUFFICIENT_ENTROPY_001`
- **CWE:** CWE-330, CWE-331, CWE-338
- **Description:** Weak random for security tokens
- **Detects:** rand()/time() for tokens instead of CSPRNG

#### RESOURCE_LEAK (MEDIUM)
- **ID:** `RESOURCE_LEAK_001`
- **CWE:** CWE-772, CWE-404, CWE-775
- **Description:** File descriptors/handles not closed
- **Detects:** fopen/open without corresponding close

#### EXEC_PATH_INJECTION (CRITICAL)
- **ID:** `EXEC_ENV_PATH_001`
- **CWE:** CWE-426, CWE-427
- **Description:** Executable path injection via PATH
- **Detects:** execvp, system without absolute paths

#### PRIV_ESCALATION (CRITICAL)
- **ID:** `PRIV_ESCALATION_001`
- **CWE:** CWE-269, CWE-250, CWE-273
- **Description:** Privilege escalation risks
- **Detects:** setuid/setgid without return value checks

---

## Dead Code Patterns (13 Total)

### Summary by Severity

| Severity | Count | Patterns |
|----------|-------|----------|
| HIGH | 1 | Orphan Component |
| MEDIUM | 8 | Deprecated Marker, Disabled Block, Error-Only, Unreachable, Dead Assignment, Invariant Dead, Dead Callback, Test-Only |
| LOW | 4 | Empty Stub, Unused Variable, Single-Caller |

---

### Original Pattern (1)

#### DEAD_CODE (MEDIUM)
- **ID:** `DEAD_CODE_001`
- **Description:** Uncalled functions in the codebase
- **Detects:** Methods never called via call_containment analysis

---

### Sprint 1 Patterns (6)

#### DEPRECATED_MARKER (MEDIUM)
- **ID:** `DEAD_CODE_002`
- **Description:** Code marked with deprecation markers
- **Detects:** pg_deprecated, DEPRECATED, __attribute__((deprecated))

#### DISABLED_CODE_BLOCK (MEDIUM)
- **ID:** `DEAD_CODE_003`
- **Description:** Preprocessor-disabled code blocks
- **Detects:** #if 0, #ifdef NOTUSED patterns

#### EMPTY_STUB (LOW)
- **ID:** `DEAD_CODE_005`
- **Description:** Functions with empty or trivial bodies
- **Detects:** Functions containing only {}, { return; }

#### ERROR_ONLY_FUNCTION (LOW)
- **ID:** `DEAD_CODE_006`
- **Description:** Functions that only report errors
- **Detects:** Functions with only ereport(ERROR)/elog(ERROR)

#### UNREACHABLE_AFTER_RETURN (MEDIUM)
- **ID:** `DEAD_CODE_007`
- **Description:** Code after return/exit statements
- **Detects:** Statements following return, exit(), elog(FATAL)

#### ORPHAN_COMPONENT (HIGH)
- **ID:** `DEAD_CODE_013`
- **Description:** Code isolated from entry points
- **Detects:** WCC analysis finds unreachable components

---

### Sprint 2 Patterns (6)

#### UNUSED_VARIABLE (LOW)
- **ID:** `DEAD_CODE_004`
- **Description:** Variables declared but never used
- **Detects:** Local variables without read references

#### DEAD_ASSIGNMENT (MEDIUM)
- **ID:** `DEAD_CODE_008`
- **Description:** Values overwritten before being read
- **Detects:** Consecutive assignments to same variable

#### INVARIANT_DEAD_CODE (MEDIUM)
- **ID:** `DEAD_CODE_009`
- **Description:** Unreachable due to constant conditions
- **Detects:** if(0), if(false), while(0) patterns

#### DEAD_CALLBACK (MEDIUM)
- **ID:** `DEAD_CODE_010`
- **Description:** Callback functions never registered
- **Detects:** *_hook, *_callback, *_handler never called/referenced

#### SINGLE_CALLER_FUNCTION (LOW)
- **ID:** `DEAD_CODE_011`
- **Description:** Small functions with exactly one caller
- **Detects:** Functions <15 lines called from one location

#### TEST_ONLY_FUNCTION (MEDIUM)
- **ID:** `DEAD_CODE_012`
- **Description:** Production code only called from tests
- **Detects:** Non-test functions only referenced by test code

---

## Using Patterns

### Filter by Pattern ID

```bash
# Single pattern
patch-review analyze --patterns SQL_INJECTION

# Multiple patterns
patch-review analyze --patterns SQL_INJECTION,BUFFER_OVERFLOW_STRCPY,USE_AFTER_FREE
```

### Filter by Severity

```bash
# Critical only
patch-review analyze --severity critical

# High and above
patch-review analyze --severity high
```

### Filter by Type

```bash
# Security patterns only
patch-review analyze --type security

# Dead code patterns only
patch-review analyze --type dead-code
```

## False Positives

### Reducing False Positives

1. **Test Files:** All patterns exclude functions starting with `test_`
2. **Severity Filter:** Use `--severity critical` for high-confidence findings
3. **Pattern Selection:** Use `--patterns` to run specific trusted patterns
4. **Confidence Scores:** Review findings with confidence < 0.7 more carefully

### Common False Positive Sources

| Pattern | False Positive Cause | Mitigation |
|---------|---------------------|------------|
| MEMORY_LEAK | Custom allocators | Check for wrapper functions |
| NULL_POINTER | Implicit guarantees | Verify call context |
| DEAD_CODE | Plugin/callback code | Check for function pointers |
| SINGLE_CALLER | Intentional helpers | Review if name documents intent |

## CWE Coverage

| CWE | Pattern | Description |
|-----|---------|-------------|
| CWE-20 | TAINTED_INPUT | Improper Input Validation |
| CWE-22 | PATH_TRAVERSAL | Path Traversal |
| CWE-78 | COMMAND_INJECTION | OS Command Injection |
| CWE-89 | SQL_INJECTION | SQL Injection |
| CWE-117 | LOG_INJECTION | Log Injection |
| CWE-120 | BUFFER_OVERFLOW | Buffer Overflow |
| CWE-134 | FORMAT_STRING | Format String |
| CWE-190 | INTEGER_OVERFLOW | Integer Overflow |
| CWE-250 | PRIV_ESCALATION | Excessive Privileges |
| CWE-269 | PRIV_ESCALATION | Improper Privilege Management |
| CWE-295 | IMPROPER_CERT | Certificate Validation |
| CWE-306 | MISSING_AUTH | Missing Authentication |
| CWE-312 | CLEARTEXT_STORAGE | Cleartext Storage |
| CWE-327 | WEAK_CRYPTO | Weak Crypto |
| CWE-330 | INSUFFICIENT_ENTROPY | Weak PRNG |
| CWE-362 | FILE_RACE | Race Condition |
| CWE-367 | RACE_CONDITION | TOCTOU |
| CWE-401 | MEMORY_LEAK | Memory Leak |
| CWE-415 | DOUBLE_FREE | Double Free |
| CWE-416 | USE_AFTER_FREE | Use After Free |
| CWE-426 | EXEC_PATH_INJECTION | Untrusted Search Path |
| CWE-457 | UNINITIALIZED_VAR | Uninitialized Variable |
| CWE-476 | NULL_POINTER | NULL Pointer Dereference |
| CWE-502 | DESERIALIZATION | Deserialization |
| CWE-611 | XXE | XXE |
| CWE-676 | BUFFER_OVERFLOW | Use of Dangerous Function |
| CWE-772 | RESOURCE_LEAK | Resource Leak |
| CWE-787 | ARRAY_BOUNDS | Out-of-bounds Write |
| CWE-798 | HARDCODED_SECRETS | Hardcoded Credentials |
| CWE-843 | TYPE_CONFUSION | Type Confusion |
| CWE-918 | SSRF | SSRF |
