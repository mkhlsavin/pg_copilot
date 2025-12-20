"""
PHP Security Patterns

Patterns for detecting vulnerabilities specific to PHP applications:
- SQL injection
- Command injection (exec/system/passthru)
- Code injection (eval/assert)
- Remote/Local file inclusion (RFI/LFI)
- Unsafe deserialization (unserialize)
- XSS (Cross-Site Scripting)
- Path traversal
- SSRF (Server-Side Request Forgery)

CWE-22, CWE-78, CWE-79, CWE-89, CWE-94, CWE-98, CWE-502, CWE-798, CWE-918
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_PHP_PATTERN = SecurityPattern(
    id="PHP_SQL_001",
    name="SQL Injection in PHP",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection via string concatenation in raw queries. "
        "Use prepared statements with parameterized queries."
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
        WHERE nc.name IN ('query', 'exec', 'mysql_query', 'mysqli_query',
                          'pg_query', 'sqlite_query')
          AND (nc.code LIKE '%$_%' OR nc.code LIKE '%.$%' OR nc.code LIKE '%"%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use PDO with prepared statements\n"
        "2. Use mysqli_prepare() and bind_param()\n"
        "3. Use ORM query builders (Eloquent, Doctrine)\n"
        "4. Never concatenate user input in SQL"
    ),
    example_code="""
        // VULNERABLE
        $query = "SELECT * FROM users WHERE id = " . $_GET['id'];
        mysqli_query($conn, $query);

        // SECURE
        $stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
        $stmt->execute([$_GET['id']]);

        // Laravel Eloquent
        User::where('id', $request->input('id'))->first();
    """,
    test_cases=[
        {"name": "mysqli_query with GET", "method": "getUser", "expected": True, "contains": ["mysqli_query", "$_GET"]}
    ]
)


COMMAND_INJECTION_PHP_PATTERN = SecurityPattern(
    id="PHP_CMD_001",
    name="Command Injection in PHP",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "OS command execution with user-controlled input via exec, system, "
        "passthru, shell_exec, or backticks."
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
        WHERE nc.name IN ('exec', 'system', 'passthru', 'shell_exec',
                          'popen', 'proc_open')
          AND (nc.code LIKE '%$_%' OR nc.code LIKE '%.$%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-78"],
    remediation=(
        "1. Avoid shell commands with user input\n"
        "2. Use escapeshellarg() and escapeshellcmd()\n"
        "3. Use allowlist for allowed commands\n"
        "4. Use specific PHP functions instead (copy, unlink, etc.)"
    ),
    example_code="""
        // VULNERABLE
        exec("ping " . $_GET['host']);
        system("cat " . $userFile);
        $output = `ls $userDir`;

        // SECURE
        $host = escapeshellarg($_GET['host']);
        exec("ping -c 1 " . $host);
    """,
    test_cases=[
        {"name": "exec with GET", "method": "pingHost", "expected": True, "contains": ["exec", "$_GET"]}
    ]
)


CODE_INJECTION_PHP_PATTERN = SecurityPattern(
    id="PHP_EVAL_001",
    name="Code Injection (eval)",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Dynamic code execution via eval(), assert(), or create_function() "
        "with user-controlled input leads to RCE."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'CODE_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('eval', 'assert', 'create_function')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-94"],
    remediation=(
        "1. Never use eval() with user input\n"
        "2. Replace eval() with structured alternatives\n"
        "3. Use anonymous functions instead of create_function()\n"
        "4. Disable eval in php.ini if not needed"
    ),
    example_code="""
        // VULNERABLE
        eval($_GET['code']);
        eval('$result = ' . $userExpression . ';');
        assert($_POST['condition']);

        // SECURE - avoid eval entirely
        // Use switch/case or array mapping instead
        $operations = ['add' => fn($a, $b) => $a + $b];
        $result = $operations[$operation]($a, $b);
    """,
    test_cases=[
        {"name": "eval call", "method": "executeCode", "expected": True, "contains": ["eval"]}
    ]
)


FILE_INCLUSION_PATTERN = SecurityPattern(
    id="PHP_LFI_001",
    name="Remote/Local File Inclusion (RFI/LFI)",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Dynamic file inclusion with user-controlled paths can lead to "
        "remote code execution or sensitive file disclosure."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'FILE_INCLUSION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('include', 'include_once', 'require', 'require_once')
          AND (nc.code LIKE '%$_%' OR nc.code LIKE '%.$%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-98"],
    remediation=(
        "1. Never use user input in include/require paths\n"
        "2. Use allowlist for allowed files\n"
        "3. Use basename() to strip directory components\n"
        "4. Set allow_url_include = Off in php.ini\n"
        "5. Use open_basedir restriction"
    ),
    example_code="""
        // VULNERABLE
        include($_GET['page'] . '.php');
        require("templates/" . $template);

        // SECURE
        $allowed = ['home', 'about', 'contact'];
        $page = in_array($_GET['page'], $allowed) ? $_GET['page'] : 'home';
        include($page . '.php');
    """,
    test_cases=[
        {"name": "include with variable", "method": "loadPage", "expected": True, "contains": ["include", "$"]}
    ]
)


DESERIALIZATION_PHP_PATTERN = SecurityPattern(
    id="PHP_DESER_001",
    name="Unsafe Deserialization",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "unserialize() with untrusted data can lead to object injection "
        "and remote code execution via magic methods."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'DESERIALIZATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name = 'unserialize'
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-502"],
    remediation=(
        "1. Use JSON instead of PHP serialization\n"
        "2. Use allowed_classes option: unserialize($data, ['allowed_classes' => false])\n"
        "3. Validate and sign serialized data with HMAC\n"
        "4. Audit __wakeup(), __destruct(), __toString() methods"
    ),
    example_code="""
        // VULNERABLE
        $data = unserialize($_COOKIE['session']);
        $obj = unserialize(base64_decode($_POST['data']));

        // SECURE
        $data = json_decode($_COOKIE['session'], true);
        // Or with restricted classes
        $obj = unserialize($data, ['allowed_classes' => ['SafeClass']]);
    """,
    test_cases=[
        {"name": "unserialize call", "method": "loadSession", "expected": True, "contains": ["unserialize"]}
    ]
)


XSS_PHP_PATTERN = SecurityPattern(
    id="PHP_XSS_001",
    name="Cross-Site Scripting (XSS)",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Unescaped output of user input in HTML context. "
        "Use htmlspecialchars() or template engine escaping."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XSS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('echo', 'print', 'printf')
          AND (nc.code LIKE '%$_GET%' OR nc.code LIKE '%$_POST%'
               OR nc.code LIKE '%$_REQUEST%')
          AND nc.code NOT LIKE '%htmlspecialchars%'
          AND nc.code NOT LIKE '%htmlentities%'
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79"],
    remediation=(
        "1. Use htmlspecialchars($var, ENT_QUOTES, 'UTF-8')\n"
        "2. Use template engines with auto-escaping (Blade, Twig)\n"
        "3. Use Content-Security-Policy headers\n"
        "4. Validate and sanitize input"
    ),
    example_code="""
        // VULNERABLE
        echo "Hello " . $_GET['name'];
        <?= $userInput ?>

        // SECURE
        echo "Hello " . htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8');
        // Blade template
        {{ $userInput }}  // Auto-escaped
    """,
    test_cases=[
        {"name": "echo with GET", "method": "displayName", "expected": True, "contains": ["echo", "$_GET"]}
    ]
)


PATH_TRAVERSAL_PHP_PATTERN = SecurityPattern(
    id="PHP_PATH_001",
    name="Path Traversal",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "File operations with user-controlled paths can lead to "
        "reading/writing arbitrary files on the server."
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
        WHERE nc.name IN ('file_get_contents', 'file_put_contents', 'fopen',
                          'readfile', 'unlink', 'copy', 'rename')
          AND (nc.code LIKE '%$_%' OR nc.code LIKE '%.$%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22"],
    remediation=(
        "1. Use basename() to strip directory components\n"
        "2. Use realpath() and validate against base directory\n"
        "3. Reject paths containing '..'\n"
        "4. Use open_basedir restriction"
    ),
    example_code="""
        // VULNERABLE
        $content = file_get_contents("uploads/" . $_GET['file']);
        unlink("data/" . $userPath);

        // SECURE
        $filename = basename($_GET['file']);
        $fullPath = realpath("uploads/" . $filename);
        if (strpos($fullPath, realpath("uploads/")) !== 0) {
            die("Path traversal attempt");
        }
        $content = file_get_contents($fullPath);
    """,
    test_cases=[
        {"name": "file_get_contents with variable", "method": "readFile", "expected": True, "contains": ["file_get_contents", "$"]}
    ]
)


SSRF_PHP_PATTERN = SecurityPattern(
    id="PHP_SSRF_001",
    name="Server-Side Request Forgery",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "HTTP requests with user-controlled URLs can access internal services "
        "or cloud metadata endpoints."
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
        WHERE nc.name IN ('file_get_contents', 'curl_exec', 'fopen')
          AND (nc.code LIKE '%http%' OR nc.code LIKE '%$_%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-918"],
    remediation=(
        "1. Use allowlist for allowed hosts\n"
        "2. Block private IP ranges and localhost\n"
        "3. Disable redirects or validate redirect targets\n"
        "4. Use network segmentation"
    ),
    example_code="""
        // VULNERABLE
        $url = $_GET['url'];
        $content = file_get_contents($url);

        // SECURE
        $url = filter_var($_GET['url'], FILTER_VALIDATE_URL);
        $parsed = parse_url($url);
        if (!in_array($parsed['host'], $allowedHosts)) {
            die("Host not allowed");
        }
        if (isPrivateIP($parsed['host'])) {
            die("Private IP not allowed");
        }
    """,
    test_cases=[
        {"name": "file_get_contents with URL", "method": "fetchUrl", "expected": True, "contains": ["file_get_contents", "http"]}
    ]
)


HARDCODED_SECRETS_PHP_PATTERN = SecurityPattern(
    id="PHP_SECRETS_001",
    name="Hardcoded Secrets",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Passwords, API keys, or database credentials hardcoded in source code."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nl.id,
            nl.code,
            nl.filename,
            nl.line_number,
            'HARDCODED_SECRET' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_literal nl
        WHERE (nl.code LIKE '%password%' OR nl.code LIKE '%secret%'
               OR nl.code LIKE '%api_key%' OR nl.code LIKE '%apiKey%'
               OR nl.code LIKE '%db_pass%' OR nl.code LIKE '%mysql_pass%')
          AND nl.code NOT LIKE '%env(%'
          AND nl.code NOT LIKE '%getenv%'
          AND nl.filename NOT LIKE '%Test%'
          AND nl.filename NOT LIKE '%.example%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798"],
    remediation=(
        "1. Use environment variables: getenv('DB_PASSWORD')\n"
        "2. Use .env files with phpdotenv (not in version control)\n"
        "3. Use Laravel config with env()\n"
        "4. Use secrets management (Vault, AWS Secrets Manager)"
    ),
    example_code="""
        // VULNERABLE
        $password = "admin123";
        define('DB_PASSWORD', 'supersecret');
        $apiKey = 'sk-1234567890abcdef';

        // SECURE
        $password = getenv('DB_PASSWORD');
        $apiKey = env('API_KEY');  // Laravel
    """,
    test_cases=[
        {"name": "hardcoded password", "method": "connect", "expected": True, "contains": ["password", "="]}
    ]
)


# Aggregate all PHP patterns
PHP_PATTERNS: Dict[str, SecurityPattern] = {
    "PHP_SQL_001": SQL_INJECTION_PHP_PATTERN,
    "PHP_CMD_001": COMMAND_INJECTION_PHP_PATTERN,
    "PHP_EVAL_001": CODE_INJECTION_PHP_PATTERN,
    "PHP_LFI_001": FILE_INCLUSION_PATTERN,
    "PHP_DESER_001": DESERIALIZATION_PHP_PATTERN,
    "PHP_XSS_001": XSS_PHP_PATTERN,
    "PHP_PATH_001": PATH_TRAVERSAL_PHP_PATTERN,
    "PHP_SSRF_001": SSRF_PHP_PATTERN,
    "PHP_SECRETS_001": HARDCODED_SECRETS_PHP_PATTERN,
}
