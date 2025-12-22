"""
Go Security Patterns

Patterns for detecting vulnerabilities specific to Go:
- SQL injection in database/sql
- Command injection via os/exec
- Race conditions in goroutines
- Path traversal
- Insecure TLS configuration

CWE-78, CWE-89, CWE-362, CWE-22, CWE-295
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_GO_PATTERN = SecurityPattern(
    id="GO_SQL_001",
    name="SQL Injection in Go database/sql",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection via string concatenation in database/sql queries. "
        "Go's database/sql supports parameterized queries that should be used."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SQL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Query', 'QueryRow', 'Exec', 'QueryContext', 'ExecContext')
          AND (nc.code LIKE '%fmt.Sprintf%'
               OR nc.code LIKE '%+%'
               OR nc.code LIKE '%string(%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use parameterized queries with $1, $2 placeholders\n"
        "2. Use Query/Exec with variadic arguments\n"
        "3. Use sqlx or GORM with prepared statements\n"
        "4. Validate and escape user input"
    ),
    example_code="""
        // VULNERABLE
        query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", id)
        db.Query(query)

        // SECURE
        db.Query("SELECT * FROM users WHERE id = $1", id)
        db.QueryContext(ctx, "SELECT * FROM users WHERE name = ?", name)
    """,
    test_cases=[
        {"name": "fmt.Sprintf in query", "method": "getUser", "expected": True, "contains": ["Sprintf", "Query"]}
    ]
)


COMMAND_INJECTION_GO_PATTERN = SecurityPattern(
    id="GO_CMD_001",
    name="Command Injection via os/exec",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Command injection when user input is passed to os/exec.Command or "
        "similar functions without validation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'COMMAND_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Command', 'CommandContext')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-78"],
    remediation=(
        "1. Avoid shell execution when possible\n"
        "2. Use exec.Command with argument array, not shell strings\n"
        "3. Validate input against strict whitelist\n"
        "4. Never use bash -c with user input"
    ),
    example_code="""
        // VULNERABLE
        cmd := exec.Command("bash", "-c", userInput)
        cmd.Run()

        // SECURE
        cmd := exec.Command("/usr/bin/ls", "-la", sanitizedPath)
        cmd.Run()
    """,
    test_cases=[
        {"name": "Command with user input", "method": "runCommand", "expected": True, "contains": ["Command"]}
    ]
)


RACE_CONDITION_GO_PATTERN = SecurityPattern(
    id="GO_RACE_001",
    name="Race Condition in Goroutines",
    category=VulnerabilityCategory.CONCURRENCY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Data race when multiple goroutines access shared data without proper "
        "synchronization using mutexes, channels, or atomic operations."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'RACE_CONDITION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.code LIKE '%go func%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-362", "CWE-367"],
    remediation=(
        "1. Use sync.Mutex or sync.RWMutex for shared data\n"
        "2. Use channels for communication between goroutines\n"
        "3. Use sync/atomic for simple counters\n"
        "4. Run go test -race to detect races"
    ),
    example_code="""
        // VULNERABLE
        var counter int
        go func() { counter++ }()  // Race condition

        // SECURE
        var counter int64
        go func() { atomic.AddInt64(&counter, 1) }()

        // OR with mutex
        var mu sync.Mutex
        go func() {
            mu.Lock()
            counter++
            mu.Unlock()
        }()
    """,
    test_cases=[
        {"name": "Goroutine without sync", "method": "processItems", "expected": True, "contains": ["go func"]}
    ]
)


PATH_TRAVERSAL_GO_PATTERN = SecurityPattern(
    id="GO_PATH_001",
    name="Path Traversal in File Operations",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Path traversal vulnerability when user input is used in file paths "
        "without proper validation or canonicalization."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'PATH_TRAVERSAL' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Open', 'ReadFile', 'WriteFile', 'Create', 'OpenFile')
          AND (nc.code LIKE '%filepath.Join%' OR nc.code LIKE '%+%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22", "CWE-23"],
    remediation=(
        "1. Use filepath.Clean to canonicalize paths\n"
        "2. Verify path starts with expected prefix after Clean\n"
        "3. Use filepath.Rel to check relative position\n"
        "4. Block paths containing .."
    ),
    example_code="""
        // VULNERABLE
        path := filepath.Join(baseDir, userInput)
        data, _ := os.ReadFile(path)

        // SECURE
        cleanPath := filepath.Clean(userInput)
        fullPath := filepath.Join(baseDir, cleanPath)
        if !strings.HasPrefix(fullPath, baseDir) {
            return errors.New("path traversal attempt")
        }
        data, _ := os.ReadFile(fullPath)
    """,
    test_cases=[
        {"name": "File open with user path", "method": "readFile", "expected": True, "contains": ["Open", "Join"]}
    ]
)


INSECURE_TLS_GO_PATTERN = SecurityPattern(
    id="GO_TLS_001",
    name="Insecure TLS Configuration",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Insecure TLS configuration such as skipping certificate verification, "
        "using deprecated TLS versions, or weak cipher suites."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_TLS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.code LIKE '%InsecureSkipVerify%'
           OR nc.code LIKE '%MinVersion%TLS10%'
           OR nc.code LIKE '%MinVersion%TLS11%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-295", "CWE-327"],
    remediation=(
        "1. Never set InsecureSkipVerify: true in production\n"
        "2. Use TLS 1.2 or higher (MinVersion: tls.VersionTLS12)\n"
        "3. Configure proper certificate chains\n"
        "4. Use secure cipher suites"
    ),
    example_code="""
        // VULNERABLE
        client := &http.Client{
            Transport: &http.Transport{
                TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
            },
        }

        // SECURE
        client := &http.Client{
            Transport: &http.Transport{
                TLSClientConfig: &tls.Config{
                    MinVersion: tls.VersionTLS12,
                },
            },
        }
    """,
    test_cases=[
        {"name": "Skip TLS verify", "method": "createClient", "expected": True, "contains": ["InsecureSkipVerify"]}
    ]
)


SSRF_GO_PATTERN = SecurityPattern(
    id="GO_SSRF_001",
    name="Server-Side Request Forgery",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "SSRF vulnerability when user-provided URLs are used in HTTP requests "
        "without proper validation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SSRF' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Get', 'Post', 'Do', 'Head', 'NewRequest')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-918"],
    remediation=(
        "1. Validate URLs against allowlist\n"
        "2. Block internal IP ranges and localhost\n"
        "3. Disable HTTP redirects or validate targets\n"
        "4. Use network policies to restrict outbound traffic"
    ),
    example_code="""
        // VULNERABLE
        resp, _ := http.Get(userProvidedURL)

        // SECURE
        parsedURL, err := url.Parse(userProvidedURL)
        if !isAllowedHost(parsedURL.Host) {
            return errors.New("host not allowed")
        }
        resp, _ := http.Get(parsedURL.String())
    """,
    test_cases=[
        {"name": "HTTP Get with user URL", "method": "fetchURL", "expected": True, "contains": ["Get"]}
    ]
)


# Registry of Go patterns
GO_PATTERNS: Dict[str, SecurityPattern] = {
    "SQL_INJECTION": SQL_INJECTION_GO_PATTERN,
    "COMMAND_INJECTION": COMMAND_INJECTION_GO_PATTERN,
    "RACE_CONDITION": RACE_CONDITION_GO_PATTERN,
    "PATH_TRAVERSAL": PATH_TRAVERSAL_GO_PATTERN,
    "INSECURE_TLS": INSECURE_TLS_GO_PATTERN,
    "SSRF": SSRF_GO_PATTERN,
}
