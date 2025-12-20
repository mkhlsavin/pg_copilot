"""
Ruby/Rails Domain Plugin for CodeGraph.

Provides domain-specific configurations for Ruby and Rails applications
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


class RubyPlugin(DomainPlugin):
    """
    Domain plugin for Ruby/Rails applications.

    Provides security patterns for:
    - Eval/system injection
    - YAML deserialization (CVE-2013-0156)
    - Mass assignment
    - SQL injection via ActiveRecord
    - XSS in ERB templates
    - Command injection
    """

    @property
    def name(self) -> str:
        return "ruby"

    @property
    def display_name(self) -> str:
        return "Ruby/Rails"

    @property
    def description(self) -> str:
        return "Ruby and Ruby on Rails application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Ruby/Rails subsystem definitions."""
        return {
            "controllers": SubsystemInfo(
                name="Controllers",
                description="Rails controllers and action handling",
                key_functions=[
                    "render", "redirect_to", "params", "respond_to",
                    "before_action", "after_action", "around_action",
                ],
                patterns=[r".*Controller$"],
            ),
            "models": SubsystemInfo(
                name="Models",
                description="ActiveRecord models and database access",
                key_functions=[
                    "save", "create", "update", "destroy", "find", "where",
                    "find_by_sql", "connection.execute", "validate",
                ],
                patterns=[r".*Model$", r"[A-Z][a-z]+$"],
            ),
            "views": SubsystemInfo(
                name="Views",
                description="ERB templates and view helpers",
                key_functions=[
                    "render", "partial", "raw", "html_safe", "sanitize",
                    "link_to", "form_for", "form_with",
                ],
                patterns=[r".*\.erb$", r".*\.haml$"],
            ),
            "mailers": SubsystemInfo(
                name="Mailers",
                description="ActionMailer email handling",
                key_functions=[
                    "mail", "deliver_now", "deliver_later",
                ],
                patterns=[r".*Mailer$"],
            ),
            "jobs": SubsystemInfo(
                name="Background Jobs",
                description="ActiveJob and Sidekiq workers",
                key_functions=[
                    "perform", "perform_later", "perform_now", "perform_async",
                ],
                patterns=[r".*Job$", r".*Worker$"],
            ),
            "services": SubsystemInfo(
                name="Services",
                description="Service objects and business logic",
                key_functions=[
                    "call", "execute", "run",
                ],
                patterns=[r".*Service$", r".*Interactor$"],
            ),
            "serializers": SubsystemInfo(
                name="Serializers",
                description="API serializers (ActiveModelSerializers, Jbuilder)",
                key_functions=[
                    "attributes", "has_many", "belongs_to", "json.array!",
                ],
                patterns=[r".*Serializer$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Ruby-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Ruby/Rails security expert specializing in web application security.
Focus on OWASP Top 10 vulnerabilities including SQL injection, XSS, CSRF, mass assignment, and deserialization.
Analyze Rails controllers, models, and views for security vulnerabilities.""",
                "user_template": "Analyze the following Ruby/Rails code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Ruby/Rails expert reviewing code for best practices.
Focus on Rails conventions, DRY principles, proper ActiveRecord usage, and security considerations.""",
                "user_template": "Review this Ruby code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Ruby-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "injection", "xss", "csrf", "mass assignment"],
                examples=["Find SQL injection vulnerabilities", "Check for XSS issues"],
                priority=10,
            ),
            "activerecord": IntentPattern(
                intent_id="activerecord",
                keywords=["model", "query", "association", "validation", "scope"],
                examples=["Find N+1 queries", "Show model associations"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Ruby/Rails security vulnerability patterns."""
        return [
            SecurityPattern(
                id="RUBY_EVAL_INJECTION",
                name="Code Injection via eval",
                description="Dynamic code execution with user input",
                severity="critical",
                cwe_id="CWE-94",
                indicators=["eval(", "instance_eval(", "class_eval(", "module_eval(", "send("],
                sinks=["eval", "instance_eval", "class_eval", "module_eval"],
                sources=["params", "request.body"],
            ),
            SecurityPattern(
                id="RUBY_COMMAND_INJECTION",
                name="Command Injection",
                description="OS command injection via system/exec/backticks",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["system(", "exec(", "`", "%x{", "Open3", "IO.popen"],
                sinks=["system", "exec", "spawn", "popen"],
                sources=["params", "request"],
            ),
            SecurityPattern(
                id="RUBY_YAML_DESERIALIZATION",
                name="Unsafe YAML Deserialization",
                description="YAML.load allows arbitrary object instantiation (CVE-2013-0156)",
                severity="critical",
                cwe_id="CWE-502",
                indicators=["YAML.load(", "Psych.load("],
                sanitizers=["YAML.safe_load", "permitted_classes"],
            ),
            SecurityPattern(
                id="RUBY_SQL_INJECTION",
                name="SQL Injection in ActiveRecord",
                description="SQL injection via string interpolation in queries",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["where(\"", "find_by_sql(", "execute(", "order(", "group("],
                sinks=["where", "find_by_sql", "execute", "order", "group"],
                sources=["params"],
                sanitizers=["?", "sanitize_sql"],
            ),
            SecurityPattern(
                id="RUBY_MASS_ASSIGNMENT",
                name="Mass Assignment Vulnerability",
                description="Uncontrolled model updates from user input",
                severity="high",
                cwe_id="CWE-915",
                indicators=["params.permit!", "update(params", "create(params"],
            ),
            SecurityPattern(
                id="RUBY_XSS",
                name="XSS in ERB Templates",
                description="Unescaped output via raw() or html_safe",
                severity="high",
                cwe_id="CWE-79",
                indicators=["raw(", ".html_safe", "safe_concat"],
                sinks=["raw", "html_safe"],
                sanitizers=["sanitize", "strip_tags"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Ruby taint source functions."""
        return [
            # Rails params
            "params",
            "params[]",
            "request.body",
            "request.raw_post",
            "request.query_string",
            # Environment
            "ENV",
            "ENV[]",
            # File input
            "File.read",
            "IO.read",
            "gets",
            # User input
            "ARGV",
            "STDIN",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Ruby taint sink functions."""
        return [
            # Code execution
            "eval",
            "instance_eval",
            "class_eval",
            "module_eval",
            "send",
            "public_send",
            # Command injection
            "system",
            "exec",
            "spawn",
            "popen",
            "`",
            "%x",
            # SQL
            "where",
            "find_by_sql",
            "execute",
            "connection.execute",
            # XSS
            "raw",
            "html_safe",
            "safe_concat",
            # File
            "File.open",
            "File.write",
            "File.delete",
            # Deserialization
            "YAML.load",
            "Marshal.load",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Ruby vulnerability function mappings."""
        return {
            "EVAL_INJECTION": ["eval", "instance_eval", "class_eval", "send", "public_send"],
            "COMMAND_INJECTION": ["system", "exec", "spawn", "popen", "`"],
            "SQL_INJECTION": ["where", "find_by_sql", "execute", "order", "group"],
            "XSS": ["raw", "html_safe", "safe_concat"],
            "DESERIALIZATION": ["YAML.load", "Marshal.load"],
            "MASS_ASSIGNMENT": ["update", "create", "assign_attributes", "permit!"],
            "PATH_TRAVERSAL": ["File.read", "File.open", "send_file"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Ruby concurrency functions."""
        return {
            "threads": ["Thread.new", "Thread.start", "join", "value"],
            "mutex": ["Mutex", "synchronize", "lock", "unlock"],
            "queues": ["Queue", "SizedQueue", "push", "pop"],
            "async": ["Concurrent::Future", "Concurrent::Promise", "async"],
            "sidekiq": ["perform_async", "perform_in", "perform_at"],
        }
