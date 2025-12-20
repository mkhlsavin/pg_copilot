"""
Go Domain Plugin for CodeGraph.

Provides domain-specific configurations for Go applications
including security patterns for common backend vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class GoPlugin(DomainPlugin):
    """
    Domain plugin for Go applications.

    Provides security patterns for:
    - SQL injection in database/sql
    - Command injection via os/exec
    - Race conditions in goroutines
    - Path traversal
    - Insecure TLS configuration
    - SSRF vulnerabilities
    """

    @property
    def name(self) -> str:
        return "go"

    @property
    def display_name(self) -> str:
        return "Go"

    @property
    def description(self) -> str:
        return "Go backend application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Go subsystem definitions."""
        return {
            "net_http": SubsystemInfo(
                name="HTTP Server",
                description="net/http handlers and middleware",
                key_functions=[
                    "http.HandleFunc", "http.Handle", "http.ListenAndServe",
                    "ServeHTTP", "http.NewRequest", "http.Get", "http.Post",
                ],
                patterns=[r".*Handler$", r".*Middleware$"],
            ),
            "database": SubsystemInfo(
                name="Database",
                description="database/sql and ORM operations",
                key_functions=[
                    "sql.Open", "db.Query", "db.QueryRow", "db.Exec",
                    "db.QueryContext", "db.ExecContext", "db.Prepare",
                ],
                patterns=[r".*Repository$", r".*Store$"],
            ),
            "goroutines": SubsystemInfo(
                name="Concurrency",
                description="Goroutines, channels, and synchronization",
                key_functions=[
                    "go", "make(chan", "sync.Mutex", "sync.RWMutex",
                    "sync.WaitGroup", "atomic.", "select",
                ],
                patterns=[r".*Worker$", r".*Pool$"],
            ),
            "io": SubsystemInfo(
                name="I/O Operations",
                description="File and stream I/O",
                key_functions=[
                    "os.Open", "os.Create", "os.ReadFile", "os.WriteFile",
                    "io.Copy", "ioutil.ReadAll", "bufio.NewReader",
                ],
                patterns=[r".*Reader$", r".*Writer$"],
            ),
            "crypto": SubsystemInfo(
                name="Cryptography",
                description="crypto package operations",
                key_functions=[
                    "crypto/tls", "crypto/sha256", "crypto/aes",
                    "bcrypt.GenerateFromPassword", "rand.Read",
                ],
                patterns=[r".*Cipher$", r".*Hash$"],
            ),
            "exec": SubsystemInfo(
                name="Command Execution",
                description="os/exec command execution",
                key_functions=[
                    "exec.Command", "exec.CommandContext", "cmd.Run",
                    "cmd.Output", "cmd.CombinedOutput", "cmd.Start",
                ],
                patterns=[],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Go-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Go security expert specializing in backend security.
Focus on injection vulnerabilities, race conditions, improper error handling, and insecure configurations.
Analyze Go code for SQL injection, command injection, path traversal, and TLS issues.""",
                "user_template": "Analyze the following Go code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Go expert reviewing code for best practices.
Focus on idiomatic Go patterns, error handling, goroutine safety, and performance considerations.""",
                "user_template": "Review this Go code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Go-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["sql", "injection", "race", "tls", "security", "vulnerability"],
                examples=["Find SQL injection", "Check for race conditions"],
                priority=10,
            ),
            "concurrency": IntentPattern(
                intent_id="concurrency",
                keywords=["goroutine", "channel", "mutex", "sync", "race", "deadlock"],
                examples=["Find race conditions", "Check mutex usage"],
                priority=8,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Go security vulnerability patterns."""
        return [
            SecurityPattern(
                id="GO_SQL_INJECTION",
                name="SQL Injection",
                description="SQL injection via string formatting in database queries",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["fmt.Sprintf", "Query", "Exec", "+"],
                sinks=["Query", "QueryRow", "Exec", "QueryContext", "ExecContext"],
                sources=["r.FormValue", "r.URL.Query", "r.PostForm"],
                sanitizers=["$1", "?"],
            ),
            SecurityPattern(
                id="GO_COMMAND_INJECTION",
                name="Command Injection",
                description="OS command injection via exec.Command",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["exec.Command", "exec.CommandContext", "bash", "-c"],
                sinks=["Command", "CommandContext"],
                sources=["r.FormValue", "r.URL.Query", "os.Args"],
            ),
            SecurityPattern(
                id="GO_RACE_CONDITION",
                name="Race Condition",
                description="Data race in goroutines without proper synchronization",
                severity="high",
                cwe_id="CWE-362",
                indicators=["go func", "go ", "goroutine"],
            ),
            SecurityPattern(
                id="GO_PATH_TRAVERSAL",
                name="Path Traversal",
                description="Path traversal via user input in file operations",
                severity="high",
                cwe_id="CWE-22",
                indicators=["filepath.Join", "os.Open", "os.ReadFile", "os.WriteFile"],
                sinks=["Open", "ReadFile", "WriteFile", "Create"],
                sources=["r.FormValue", "r.URL.Query"],
                sanitizers=["filepath.Clean", "strings.HasPrefix"],
            ),
            SecurityPattern(
                id="GO_INSECURE_TLS",
                name="Insecure TLS Configuration",
                description="Disabled certificate verification or weak TLS",
                severity="high",
                cwe_id="CWE-295",
                indicators=["InsecureSkipVerify", "MinVersion", "TLS10", "TLS11"],
            ),
            SecurityPattern(
                id="GO_SSRF",
                name="Server-Side Request Forgery",
                description="SSRF via user-controlled URLs",
                severity="high",
                cwe_id="CWE-918",
                indicators=["http.Get", "http.Post", "http.NewRequest", "http.Do"],
                sinks=["Get", "Post", "Do", "NewRequest"],
                sources=["r.FormValue", "r.URL.Query"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Go taint source functions."""
        return [
            # HTTP request sources
            "r.FormValue",
            "r.PostFormValue",
            "r.URL.Query",
            "r.PostForm",
            "r.Body",
            "r.Header.Get",
            "r.Cookie",
            # Environment
            "os.Getenv",
            "os.Args",
            # File/Network
            "ioutil.ReadAll",
            "io.ReadAll",
            "bufio.NewReader",
            "json.Unmarshal",
            "xml.Unmarshal",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Go taint sink functions."""
        return [
            # SQL sinks
            "db.Query",
            "db.QueryRow",
            "db.Exec",
            "db.QueryContext",
            "db.ExecContext",
            # Command injection
            "exec.Command",
            "exec.CommandContext",
            "cmd.Run",
            # File operations
            "os.Open",
            "os.Create",
            "os.ReadFile",
            "os.WriteFile",
            "ioutil.WriteFile",
            # Network
            "http.Get",
            "http.Post",
            "http.NewRequest",
            # Response
            "w.Write",
            "fmt.Fprintf",
            "template.HTML",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Go vulnerability function mappings."""
        return {
            "SQL_INJECTION": ["Query", "QueryRow", "Exec", "QueryContext", "ExecContext"],
            "COMMAND_INJECTION": ["Command", "CommandContext", "Run", "Output"],
            "PATH_TRAVERSAL": ["Open", "Create", "ReadFile", "WriteFile", "Remove"],
            "SSRF": ["Get", "Post", "Do", "NewRequest"],
            "RACE_CONDITION": ["go", "goroutine"],
            "INSECURE_TLS": ["InsecureSkipVerify", "MinVersion"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Go concurrency functions."""
        return {
            "goroutine": ["go"],
            "channel": ["make(chan", "<-", "close"],
            "mutex": ["Lock", "Unlock", "RLock", "RUnlock"],
            "waitgroup": ["Add", "Done", "Wait"],
            "atomic": ["AddInt64", "LoadInt64", "StoreInt64", "CompareAndSwap"],
            "once": ["Do"],
            "cond": ["Wait", "Signal", "Broadcast"],
        }
