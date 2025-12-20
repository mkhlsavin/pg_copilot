"""
PHP Domain Plugin for CodeGraph.

Provides domain-specific configurations for PHP applications
including security patterns for common web vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class PhpPlugin(DomainPlugin):
    """
    Domain plugin for PHP applications.

    Provides security patterns for:
    - SQL injection
    - Command injection via eval/exec
    - Remote/Local file inclusion (RFI/LFI)
    - Unsafe deserialization (unserialize)
    - XSS (Cross-Site Scripting)
    - Path traversal
    - SSRF
    """

    @property
    def name(self) -> str:
        return "php"

    @property
    def display_name(self) -> str:
        return "PHP"

    @property
    def description(self) -> str:
        return "PHP web application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load PHP subsystem definitions."""
        return {
            "controllers": SubsystemInfo(
                name="Controllers",
                description="MVC controllers (Laravel, Symfony, etc.)",
                key_functions=[
                    "Controller", "extends Controller", "Route::",
                    "public function", "return view", "return response",
                ],
                patterns=[r".*Controller\.php$"],
            ),
            "models": SubsystemInfo(
                name="Models",
                description="Eloquent/Doctrine models",
                key_functions=[
                    "extends Model", "extends Eloquent", "use HasFactory",
                    "fillable", "guarded", "casts",
                ],
                patterns=[r"app/Models/.*\.php$"],
            ),
            "middleware": SubsystemInfo(
                name="Middleware",
                description="HTTP middleware",
                key_functions=[
                    "Middleware", "handle", "$next", "$request",
                ],
                patterns=[r".*Middleware\.php$"],
            ),
            "services": SubsystemInfo(
                name="Services",
                description="Business logic services",
                key_functions=[
                    "Service", "__construct", "public function",
                ],
                patterns=[r".*Service\.php$"],
            ),
            "repositories": SubsystemInfo(
                name="Repositories",
                description="Data access repositories",
                key_functions=[
                    "Repository", "find", "findAll", "save", "delete",
                ],
                patterns=[r".*Repository\.php$"],
            ),
            "commands": SubsystemInfo(
                name="Commands",
                description="CLI commands (Artisan, Symfony Console)",
                key_functions=[
                    "extends Command", "handle", "signature", "execute",
                ],
                patterns=[r".*Command\.php$"],
            ),
            "api": SubsystemInfo(
                name="API",
                description="API endpoints and resources",
                key_functions=[
                    "Resource", "JsonResource", "toArray", "api/",
                ],
                patterns=[r".*Resource\.php$", r".*Api.*\.php$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load PHP-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a PHP security expert specializing in web application security.
Focus on OWASP Top 10 including SQL injection, XSS, command injection, and file inclusion.
Analyze Laravel, Symfony, WordPress code for security vulnerabilities.""",
                "user_template": "Analyze the following PHP code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a PHP expert reviewing code for best practices.
Focus on PSR standards, Laravel/Symfony patterns, and security considerations.""",
                "user_template": "Review this PHP code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load PHP-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "injection", "xss", "eval", "include"],
                examples=["Find SQL injection", "Check for eval usage"],
                priority=10,
            ),
            "laravel": IntentPattern(
                intent_id="laravel",
                keywords=["laravel", "eloquent", "blade", "artisan", "controller", "middleware"],
                examples=["Find Laravel routes", "Analyze Eloquent queries"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load PHP security vulnerability patterns."""
        return [
            SecurityPattern(
                id="PHP_SQL_INJECTION",
                name="SQL Injection",
                description="SQL injection via string concatenation in raw queries",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["mysql_query", "mysqli_query", "->query", "->exec", "DB::raw", "."],
                sinks=["query", "exec", "mysql_query", "mysqli_query", "pg_query"],
                sources=["$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "request->input"],
                sanitizers=["prepare", "bindParam", "bindValue", "escape", "quote"],
            ),
            SecurityPattern(
                id="PHP_COMMAND_INJECTION",
                name="Command Injection",
                description="OS command execution via exec/system/passthru with user input",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["exec", "system", "passthru", "shell_exec", "popen", "proc_open", "`"],
                sinks=["exec", "system", "passthru", "shell_exec", "popen"],
                sources=["$_GET", "$_POST", "$_REQUEST"],
                sanitizers=["escapeshellarg", "escapeshellcmd"],
            ),
            SecurityPattern(
                id="PHP_CODE_INJECTION",
                name="Code Injection (eval)",
                description="Dynamic code execution via eval/assert/create_function",
                severity="critical",
                cwe_id="CWE-94",
                indicators=["eval", "assert", "create_function", "preg_replace /e"],
                sinks=["eval", "assert", "create_function"],
                sources=["$_GET", "$_POST", "$_REQUEST", "file_get_contents"],
            ),
            SecurityPattern(
                id="PHP_FILE_INCLUSION",
                name="Remote/Local File Inclusion (RFI/LFI)",
                description="Dynamic file inclusion with user-controlled paths",
                severity="critical",
                cwe_id="CWE-98",
                indicators=["include", "include_once", "require", "require_once", ".."],
                sinks=["include", "include_once", "require", "require_once"],
                sources=["$_GET", "$_POST", "$_REQUEST"],
                sanitizers=["basename", "realpath"],
            ),
            SecurityPattern(
                id="PHP_DESERIALIZATION",
                name="Unsafe Deserialization",
                description="unserialize() with untrusted data can lead to RCE",
                severity="critical",
                cwe_id="CWE-502",
                indicators=["unserialize", "maybe_unserialize"],
                sinks=["unserialize"],
                sources=["$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "file_get_contents"],
                sanitizers=["json_decode", "allowed_classes"],
            ),
            SecurityPattern(
                id="PHP_XSS",
                name="Cross-Site Scripting (XSS)",
                description="Unescaped output of user input in HTML",
                severity="high",
                cwe_id="CWE-79",
                indicators=["echo", "print", "{!!", "<?="],
                sinks=["echo", "print", "printf"],
                sources=["$_GET", "$_POST", "$_REQUEST"],
                sanitizers=["htmlspecialchars", "htmlentities", "strip_tags", "e()"],
            ),
            SecurityPattern(
                id="PHP_PATH_TRAVERSAL",
                name="Path Traversal",
                description="File operations with user-controlled paths",
                severity="high",
                cwe_id="CWE-22",
                indicators=["file_get_contents", "file_put_contents", "fopen", "readfile", ".."],
                sinks=["file_get_contents", "file_put_contents", "fopen", "readfile", "unlink"],
                sources=["$_GET", "$_POST", "$_REQUEST"],
                sanitizers=["basename", "realpath"],
            ),
            SecurityPattern(
                id="PHP_SSRF",
                name="Server-Side Request Forgery",
                description="HTTP requests with user-controlled URLs",
                severity="high",
                cwe_id="CWE-918",
                indicators=["file_get_contents", "curl_exec", "fopen", "http://", "https://"],
                sinks=["file_get_contents", "curl_exec", "fopen"],
                sources=["$_GET", "$_POST", "$_REQUEST"],
            ),
            SecurityPattern(
                id="PHP_HARDCODED_SECRETS",
                name="Hardcoded Secrets",
                description="Passwords, API keys, or secrets in source code",
                severity="critical",
                cwe_id="CWE-798",
                indicators=["password", "secret", "api_key", "apiKey", "token"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get PHP taint source functions."""
        return [
            # Superglobals
            "$_GET",
            "$_POST",
            "$_REQUEST",
            "$_COOKIE",
            "$_SERVER",
            "$_FILES",
            # Input functions
            "file_get_contents('php://input')",
            "fgets(STDIN)",
            # Framework input
            "$request->input",
            "$request->get",
            "$request->post",
            "$request->query",
            "Input::get",
            "Request::input",
            # Database results
            "fetch",
            "fetch_assoc",
            "fetchAll",
            "fetchColumn",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get PHP taint sink functions."""
        return [
            # SQL sinks
            "query",
            "exec",
            "mysql_query",
            "mysqli_query",
            "pg_query",
            "sqlite_query",
            "DB::raw",
            "DB::select",
            "DB::statement",
            # Command execution
            "exec",
            "system",
            "passthru",
            "shell_exec",
            "popen",
            "proc_open",
            # Code execution
            "eval",
            "assert",
            "create_function",
            "preg_replace",  # with /e modifier
            # File inclusion
            "include",
            "include_once",
            "require",
            "require_once",
            # File operations
            "file_get_contents",
            "file_put_contents",
            "fopen",
            "fwrite",
            "readfile",
            "unlink",
            "copy",
            "rename",
            # Deserialization
            "unserialize",
            # Output (XSS)
            "echo",
            "print",
            "printf",
            # HTTP
            "header",
            "setcookie",
            "curl_exec",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get PHP vulnerability function mappings."""
        return {
            "SQL_INJECTION": [
                "query", "exec", "mysql_query", "mysqli_query",
                "pg_query", "DB::raw", "DB::select",
            ],
            "COMMAND_INJECTION": [
                "exec", "system", "passthru", "shell_exec",
                "popen", "proc_open",
            ],
            "CODE_INJECTION": ["eval", "assert", "create_function", "preg_replace"],
            "FILE_INCLUSION": ["include", "include_once", "require", "require_once"],
            "DESERIALIZATION": ["unserialize"],
            "PATH_TRAVERSAL": [
                "file_get_contents", "file_put_contents", "fopen",
                "readfile", "unlink",
            ],
            "XSS": ["echo", "print", "printf"],
            "SSRF": ["file_get_contents", "curl_exec", "fopen"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get PHP concurrency functions (limited in PHP)."""
        return {
            "pcntl": ["pcntl_fork", "pcntl_wait", "pcntl_signal"],
            "parallel": ["parallel\\run", "parallel\\Future"],
            "async": ["Amp\\async", "React\\Promise", "Swoole\\Coroutine"],
            "queue": ["dispatch", "Queue::push", "Bus::dispatch"],
        }
