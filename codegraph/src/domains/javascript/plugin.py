"""
JavaScript/TypeScript Domain Plugin for CodeGraph.

Provides domain-specific configurations for JavaScript and TypeScript applications
including security patterns for common web and Node.js vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class JavaScriptPlugin(DomainPlugin):
    """
    Domain plugin for JavaScript/TypeScript applications.

    Provides security patterns for:
    - XSS via DOM manipulation
    - Prototype pollution
    - Eval/Function injection
    - SSRF via fetch/axios
    - Hardcoded secrets
    - Insecure cryptography
    """

    @property
    def name(self) -> str:
        return "javascript"

    @property
    def display_name(self) -> str:
        return "JavaScript/TypeScript"

    @property
    def description(self) -> str:
        return "JavaScript and TypeScript application analysis (Node.js, React, Vue, etc.)"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load JavaScript/TypeScript subsystem definitions."""
        return {
            "frontend": SubsystemInfo(
                name="Frontend",
                description="Browser-side JavaScript and DOM manipulation",
                key_functions=[
                    "document.getElementById", "querySelector", "addEventListener",
                    "innerHTML", "outerHTML", "document.write",
                ],
                patterns=[r".*Component$", r".*Controller$"],
            ),
            "backend_node": SubsystemInfo(
                name="Node.js Backend",
                description="Server-side Node.js application logic",
                key_functions=[
                    "require", "module.exports", "process.env",
                    "fs.readFile", "fs.writeFile", "child_process.exec",
                ],
                patterns=[r".*Router$", r".*Handler$", r".*Service$"],
            ),
            "express": SubsystemInfo(
                name="Express.js",
                description="Express web framework routes and middleware",
                key_functions=[
                    "app.get", "app.post", "app.use", "router.get",
                    "req.body", "req.params", "req.query", "res.send", "res.json",
                ],
                patterns=[r".*Middleware$", r".*Route$"],
            ),
            "react": SubsystemInfo(
                name="React",
                description="React components and hooks",
                key_functions=[
                    "useState", "useEffect", "useContext", "render",
                    "dangerouslySetInnerHTML", "componentDidMount",
                ],
                patterns=[r".*Component$", r"use[A-Z].*"],
            ),
            "vue": SubsystemInfo(
                name="Vue.js",
                description="Vue components and composition API",
                key_functions=[
                    "ref", "reactive", "computed", "watch",
                    "v-html", "mounted", "created",
                ],
                patterns=[r".*View$", r".*Store$"],
            ),
            "database": SubsystemInfo(
                name="Database",
                description="Database connections and ORM",
                key_functions=[
                    "query", "findOne", "findMany", "create", "update",
                    "mongoose.connect", "sequelize.query", "prisma",
                ],
                patterns=[r".*Repository$", r".*Model$"],
            ),
            "testing": SubsystemInfo(
                name="Testing",
                description="Test frameworks and utilities",
                key_functions=[
                    "describe", "it", "test", "expect", "beforeEach", "afterEach",
                    "jest.mock", "sinon.stub",
                ],
                patterns=[r".*\.test\.", r".*\.spec\."],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load JavaScript-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a JavaScript/TypeScript security expert specializing in web and Node.js security.
Focus on OWASP Top 10 vulnerabilities including XSS, injection, prototype pollution, and insecure dependencies.
Analyze frontend code, Node.js backends, and npm packages for security vulnerabilities.""",
                "user_template": "Analyze the following JavaScript/TypeScript code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a JavaScript/TypeScript expert reviewing code for best practices.
Focus on modern ES6+ patterns, async/await usage, proper error handling, and security considerations.""",
                "user_template": "Review this JavaScript/TypeScript code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load JavaScript-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["xss", "injection", "prototype", "eval", "security", "vulnerability"],
                examples=["Find XSS vulnerabilities", "Check for prototype pollution"],
                priority=10,
            ),
            "async": IntentPattern(
                intent_id="async",
                keywords=["async", "await", "promise", "callback", "then"],
                examples=["Find async patterns", "Check promise handling"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load JavaScript security vulnerability patterns."""
        return [
            SecurityPattern(
                id="JS_XSS_DOM",
                name="XSS via DOM Manipulation",
                description="Cross-Site Scripting via innerHTML, outerHTML, document.write",
                severity="high",
                cwe_id="CWE-79",
                indicators=["innerHTML", "outerHTML", "document.write", "insertAdjacentHTML"],
                sinks=["innerHTML", "outerHTML", "document.write"],
                sources=["location.search", "location.hash", "document.URL"],
                sanitizers=["DOMPurify.sanitize", "textContent"],
            ),
            SecurityPattern(
                id="JS_EVAL_INJECTION",
                name="Code Injection via eval/Function",
                description="Dynamic code execution with user input",
                severity="critical",
                cwe_id="CWE-94",
                indicators=["eval(", "new Function(", "setTimeout(", "setInterval("],
                sinks=["eval", "Function", "setTimeout", "setInterval"],
                sources=["req.body", "req.query", "req.params"],
            ),
            SecurityPattern(
                id="JS_PROTOTYPE_POLLUTION",
                name="Prototype Pollution",
                description="Object prototype modification via unsafe merge operations",
                severity="high",
                cwe_id="CWE-1321",
                indicators=["__proto__", "constructor", "prototype", "merge(", "extend("],
            ),
            SecurityPattern(
                id="JS_SSRF",
                name="Server-Side Request Forgery",
                description="SSRF via fetch/axios with user-controlled URLs",
                severity="high",
                cwe_id="CWE-918",
                indicators=["fetch(", "axios(", "axios.get(", "http.get(", "https.get("],
                sinks=["fetch", "axios", "got", "request"],
                sources=["req.body", "req.query", "req.params"],
            ),
            SecurityPattern(
                id="JS_HARDCODED_SECRETS",
                name="Hardcoded Secrets",
                description="API keys, passwords, tokens in source code",
                severity="critical",
                cwe_id="CWE-798",
                indicators=["api_key", "apiKey", "API_KEY", "secret", "password", "token"],
            ),
            SecurityPattern(
                id="JS_WEAK_CRYPTO",
                name="Weak Cryptographic Algorithm",
                description="Use of MD5, SHA1, or other weak crypto",
                severity="high",
                cwe_id="CWE-327",
                indicators=["createHash('md5')", "createHash('sha1')", "MD5(", "SHA1("],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get JavaScript taint source functions."""
        return [
            # Express/Node.js request sources
            "req.body",
            "req.query",
            "req.params",
            "req.headers",
            "req.cookies",
            # Browser sources
            "location.search",
            "location.hash",
            "location.href",
            "document.URL",
            "document.referrer",
            "window.name",
            # Form inputs
            "document.getElementById",
            "document.querySelector",
            "FormData",
            # Environment
            "process.env",
            "process.argv",
            # File/Network
            "fs.readFile",
            "fetch",
            "XMLHttpRequest",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get JavaScript taint sink functions."""
        return [
            # XSS sinks
            "innerHTML",
            "outerHTML",
            "document.write",
            "document.writeln",
            "insertAdjacentHTML",
            "dangerouslySetInnerHTML",
            # Code execution
            "eval",
            "Function",
            "setTimeout",
            "setInterval",
            # Command injection
            "child_process.exec",
            "child_process.spawn",
            "execSync",
            # SQL injection
            "query",
            "execute",
            "raw",
            # File operations
            "fs.writeFile",
            "fs.appendFile",
            "fs.unlink",
            # Network
            "fetch",
            "axios",
            "http.request",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get JavaScript vulnerability function mappings."""
        return {
            "XSS": ["innerHTML", "outerHTML", "document.write", "dangerouslySetInnerHTML"],
            "CODE_INJECTION": ["eval", "Function", "setTimeout", "setInterval"],
            "COMMAND_INJECTION": ["exec", "spawn", "execSync", "execFile"],
            "SQL_INJECTION": ["query", "execute", "raw", "knex.raw"],
            "PATH_TRAVERSAL": ["readFile", "writeFile", "createReadStream", "join"],
            "SSRF": ["fetch", "axios", "got", "request", "http.get"],
            "PROTOTYPE_POLLUTION": ["merge", "extend", "assign", "defaultsDeep"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get JavaScript async/concurrency functions."""
        return {
            "promises": ["then", "catch", "finally", "Promise.all", "Promise.race"],
            "async_await": ["async", "await"],
            "callbacks": ["setTimeout", "setInterval", "setImmediate", "nextTick"],
            "workers": ["Worker", "postMessage", "onmessage"],
            "streams": ["pipe", "on", "emit", "createReadStream", "createWriteStream"],
        }
