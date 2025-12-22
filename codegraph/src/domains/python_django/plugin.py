"""
Python/Django Domain Plugin for CodeGraph.

Provides domain-specific configurations for Django web applications
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


class PythonDjangoPlugin(DomainPlugin):
    """
    Domain plugin for Python/Django web applications.

    Provides security patterns for:
    - SQL Injection (ORM bypass, raw queries)
    - XSS (Cross-Site Scripting)
    - CSRF vulnerabilities
    - Authentication/Authorization issues
    - Insecure deserialization
    - Path traversal
    - Command injection
    """

    @property
    def name(self) -> str:
        return "python_django"

    @property
    def display_name(self) -> str:
        return "Python/Django"

    @property
    def description(self) -> str:
        return "Django web application framework analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Django subsystem definitions."""
        return {
            "views": SubsystemInfo(
                name="Views",
                description="Django view handlers and request processing",
                key_functions=[
                    "get", "post", "put", "delete", "patch",
                    "dispatch", "get_object", "get_queryset",
                ],
                patterns=[r".*View$", r".*ViewSet$", r".*APIView$"],
            ),
            "models": SubsystemInfo(
                name="Models",
                description="Django ORM models and database access",
                key_functions=[
                    "save", "delete", "create", "update",
                    "objects.get", "objects.filter", "objects.raw",
                ],
                patterns=[r".*Model$", r".*Manager$"],
            ),
            "forms": SubsystemInfo(
                name="Forms",
                description="Django form handling and validation",
                key_functions=[
                    "clean", "is_valid", "save", "clean_data",
                ],
                patterns=[r".*Form$", r".*FormSet$"],
            ),
            "serializers": SubsystemInfo(
                name="Serializers",
                description="DRF serializers for API data",
                key_functions=[
                    "validate", "create", "update", "to_representation",
                ],
                patterns=[r".*Serializer$"],
            ),
            "authentication": SubsystemInfo(
                name="Authentication",
                description="User authentication and session handling",
                key_functions=[
                    "authenticate", "login", "logout",
                    "has_permission", "check_password",
                ],
                patterns=[r".*Backend$", r".*Permission$"],
            ),
            "middleware": SubsystemInfo(
                name="Middleware",
                description="Request/response middleware processing",
                key_functions=[
                    "__call__", "process_request", "process_response",
                    "process_view", "process_exception",
                ],
                patterns=[r".*Middleware$"],
            ),
            "celery": SubsystemInfo(
                name="Celery Tasks",
                description="Async task processing with Celery",
                key_functions=[
                    "apply_async", "delay", "run",
                ],
                patterns=[r".*Task$", r"@task", r"@shared_task"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Django-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Python/Django security expert specializing in web application security.
Focus on OWASP Top 10 vulnerabilities including SQL injection, XSS, CSRF, and authentication issues.
Analyze Django views, models, serializers, and middleware for security vulnerabilities.""",
                "user_template": "Analyze the following Django code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Django developer expert reviewing code for best practices.
Focus on Django conventions, DRY principles, proper ORM usage, and security considerations.""",
                "user_template": "Review this Django code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Django-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "injection", "xss", "csrf", "auth"],
                examples=["Find SQL injection vulnerabilities", "Check for XSS issues"],
                priority=10,
            ),
            "orm": IntentPattern(
                intent_id="orm",
                keywords=["queryset", "filter", "objects", "model", "database"],
                examples=["Find all database queries", "Show model relationships"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Django security vulnerability patterns."""
        return [
            SecurityPattern(
                id="DJANGO_SQL_INJECTION",
                name="SQL Injection via Raw Query",
                description="Raw SQL query with unsanitized user input",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["raw(", "extra(", "RawSQL(", "cursor.execute("],
                sinks=["raw", "extra", "execute", "RawSQL"],
                sources=["request.GET", "request.POST", "request.data"],
                sanitizers=["params=", "quote_name"],
            ),
            SecurityPattern(
                id="DJANGO_XSS",
                name="Cross-Site Scripting (XSS)",
                description="Unescaped user input in templates or responses",
                severity="high",
                cwe_id="CWE-79",
                indicators=["mark_safe(", "|safe", "autoescape off", "HttpResponse("],
                sinks=["mark_safe", "HttpResponse"],
                sources=["request.GET", "request.POST", "request.data"],
                sanitizers=["escape", "strip_tags"],
            ),
            SecurityPattern(
                id="DJANGO_CSRF",
                name="CSRF Vulnerability",
                description="Missing CSRF protection on state-changing endpoints",
                severity="high",
                cwe_id="CWE-352",
                indicators=["@csrf_exempt", "csrf_exempt"],
            ),
            SecurityPattern(
                id="DJANGO_AUTH_BYPASS",
                name="Authentication Bypass",
                description="Improper authentication checks",
                severity="critical",
                cwe_id="CWE-287",
                indicators=["@permission_classes([])", "AllowAny", "is_authenticated"],
            ),
            SecurityPattern(
                id="DJANGO_INSECURE_DESERIALIZE",
                name="Insecure Deserialization",
                description="Unsafe deserialization of user data",
                severity="critical",
                cwe_id="CWE-502",
                indicators=["pickle.loads", "yaml.load", "eval(", "exec("],
                sinks=["pickle.loads", "yaml.load", "eval", "exec"],
            ),
            SecurityPattern(
                id="DJANGO_PATH_TRAVERSAL",
                name="Path Traversal",
                description="Unvalidated file paths allowing directory traversal",
                severity="high",
                cwe_id="CWE-22",
                indicators=["open(", "os.path.join(", "send_file("],
                sinks=["open", "send_file", "FileResponse"],
                sources=["request.GET", "request.POST"],
            ),
            SecurityPattern(
                id="DJANGO_CMD_INJECTION",
                name="Command Injection",
                description="OS command execution with user input",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["subprocess.", "os.system(", "os.popen(", "shell=True"],
                sinks=["subprocess.call", "subprocess.run", "os.system", "os.popen"],
                sources=["request.GET", "request.POST", "request.data"],
            ),
            SecurityPattern(
                id="DJANGO_MASS_ASSIGNMENT",
                name="Mass Assignment",
                description="Uncontrolled model field updates from user input",
                severity="medium",
                cwe_id="CWE-915",
                indicators=["**request.data", "**request.POST", "update(**"],
            ),
            SecurityPattern(
                id="DJANGO_HARDCODED_SECRET",
                name="Hardcoded Secret",
                description="Secrets or credentials in source code",
                severity="high",
                cwe_id="CWE-798",
                indicators=["SECRET_KEY", "password=", "api_key=", "token="],
            ),
            SecurityPattern(
                id="DJANGO_DEBUG_ENABLED",
                name="Debug Mode in Production",
                description="DEBUG=True in production settings",
                severity="medium",
                cwe_id="CWE-489",
                indicators=["DEBUG = True", "DEBUG=True"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Django taint source functions."""
        return [
            # Request data sources
            "request.GET.get",
            "request.POST.get",
            "request.data.get",
            "request.FILES",
            "request.body",
            "request.path",
            "request.META.get",
            # Form data
            "cleaned_data.get",
            "form.cleaned_data",
            # Serializer data
            "validated_data.get",
            "serializer.validated_data",
            # URL parameters
            "kwargs.get",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Django taint sink functions."""
        return [
            # SQL sinks
            "raw",
            "extra",
            "execute",
            "RawSQL",
            # XSS sinks
            "mark_safe",
            "HttpResponse",
            "JsonResponse",
            # Command injection sinks
            "subprocess.call",
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "os.popen",
            # File sinks
            "open",
            "send_file",
            "FileResponse",
            # Deserialization sinks
            "pickle.loads",
            "yaml.load",
            "eval",
            "exec",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Django vulnerability function mappings."""
        return {
            "SQL_INJECTION": ["raw", "extra", "execute", "RawSQL", "cursor"],
            "XSS": ["mark_safe", "HttpResponse", "render_to_string"],
            "COMMAND_INJECTION": ["subprocess", "os.system", "os.popen", "shell"],
            "PATH_TRAVERSAL": ["open", "os.path.join", "send_file", "FileResponse"],
            "INSECURE_DESERIALIZATION": ["pickle", "yaml.load", "eval", "exec"],
            "CSRF": ["csrf_exempt"],
            "AUTH_BYPASS": ["AllowAny", "permission_classes"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Django/Celery concurrency functions."""
        return {
            "async_tasks": ["delay", "apply_async", "send_task"],
            "locks": ["Lock", "RLock", "select_for_update"],
            "transactions": [
                "atomic",
                "transaction.atomic",
                "savepoint",
                "commit",
                "rollback",
            ],
            "signals": ["send", "send_robust"],
        }
