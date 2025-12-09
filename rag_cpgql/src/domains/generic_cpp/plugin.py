"""
Generic C/C++ Domain Plugin.

Provides domain-specific configurations for analyzing generic C/C++ codebases.
This plugin covers common C/C++ patterns, security vulnerabilities, and subsystems.
Includes D3FEND Source Code Hardening patterns for C/C++ specific checks.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..base import DomainPlugin, SubsystemInfo, SecurityPattern, IntentPattern

logger = logging.getLogger(__name__)


class GenericCppDomainPlugin(DomainPlugin):
    """
    Domain plugin for generic C/C++ codebases.

    Covers common patterns found in C/C++ projects including:
    - Memory management (malloc, free, new, delete)
    - File I/O operations
    - String handling
    - Data structures
    - Concurrency primitives
    - Network operations
    - D3FEND Source Code Hardening checks
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the C/C++ domain plugin."""
        if config_dir is None:
            config_dir = Path(__file__).parent
        super().__init__(config_dir)

    @property
    def name(self) -> str:
        return "generic_cpp"

    @property
    def display_name(self) -> str:
        return "C/C++"

    @property
    def description(self) -> str:
        return "Generic C/C++ codebase analysis with D3FEND hardening checks"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load C/C++ subsystem definitions."""
        return {
            "memory_management": SubsystemInfo(
                name="Memory Management",
                description="Dynamic memory allocation and deallocation",
                key_functions=[
                    "malloc", "calloc", "realloc", "free",
                    "new", "delete", "new[]", "delete[]",
                    "memcpy", "memmove", "memset", "memcmp",
                    "aligned_alloc", "posix_memalign",
                ],
                patterns=[
                    r"^(m|c|re)alloc$",
                    r"^mem(cpy|move|set|cmp)$",
                    r"^operator\s*new",
                    r"^operator\s*delete",
                ],
                related_files=["memory.h", "cstdlib", "cstring"],
            ),
            "file_io": SubsystemInfo(
                name="File I/O",
                description="File and stream input/output operations",
                key_functions=[
                    "fopen", "fclose", "fread", "fwrite",
                    "fgets", "fputs", "fprintf", "fscanf",
                    "fseek", "ftell", "rewind", "fflush",
                    "open", "close", "read", "write",
                    "lseek", "stat", "fstat",
                ],
                patterns=[
                    r"^f(open|close|read|write|seek|tell)$",
                    r"^f(gets|puts|printf|scanf)$",
                    r"^(open|close|read|write|lseek)$",
                ],
                related_files=["stdio.h", "cstdio", "fcntl.h", "unistd.h"],
            ),
            "string_handling": SubsystemInfo(
                name="String Handling",
                description="String manipulation and processing",
                key_functions=[
                    "strlen", "strcpy", "strncpy", "strcat", "strncat",
                    "strcmp", "strncmp", "strchr", "strrchr", "strstr",
                    "sprintf", "snprintf", "sscanf",
                    "atoi", "atol", "atof", "strtol", "strtod",
                ],
                patterns=[
                    r"^str(len|cpy|cat|cmp|chr|str)$",
                    r"^strn(cpy|cat|cmp)$",
                    r"^s(printf|scanf)$",
                    r"^(a|str)to[ilfd]$",
                ],
                related_files=["string.h", "cstring", "stdlib.h"],
            ),
            "data_structures": SubsystemInfo(
                name="Data Structures",
                description="Common data structure operations",
                key_functions=[
                    "qsort", "bsearch",
                    "push_back", "pop_back", "push_front", "pop_front",
                    "insert", "erase", "find", "begin", "end",
                    "size", "empty", "clear", "resize",
                ],
                patterns=[
                    r"^(push|pop)_(back|front)$",
                    r"^(insert|erase|find|begin|end)$",
                    r"^(size|empty|clear|resize)$",
                ],
                related_files=["vector", "list", "map", "set", "algorithm"],
            ),
            "concurrency": SubsystemInfo(
                name="Concurrency",
                description="Threading and synchronization primitives",
                key_functions=[
                    "pthread_create", "pthread_join", "pthread_exit",
                    "pthread_mutex_init", "pthread_mutex_lock", "pthread_mutex_unlock",
                    "pthread_cond_wait", "pthread_cond_signal", "pthread_cond_broadcast",
                    "sem_init", "sem_wait", "sem_post",
                    "std::thread", "std::mutex", "std::lock_guard",
                    "std::condition_variable", "std::atomic",
                ],
                patterns=[
                    r"^pthread_(create|join|exit|mutex|cond|rwlock).*$",
                    r"^sem_(init|wait|post|destroy)$",
                    r"^std::(thread|mutex|lock_guard|unique_lock)$",
                ],
                related_files=["pthread.h", "semaphore.h", "thread", "mutex"],
            ),
            "network": SubsystemInfo(
                name="Network",
                description="Network and socket operations",
                key_functions=[
                    "socket", "bind", "listen", "accept", "connect",
                    "send", "recv", "sendto", "recvfrom",
                    "getaddrinfo", "gethostbyname", "inet_pton", "inet_ntop",
                    "select", "poll", "epoll_create", "epoll_ctl", "epoll_wait",
                ],
                patterns=[
                    r"^(socket|bind|listen|accept|connect)$",
                    r"^(send|recv)(to|from)?$",
                    r"^(get|set)sockopt$",
                    r"^epoll_(create|ctl|wait)$",
                ],
                related_files=["sys/socket.h", "netinet/in.h", "arpa/inet.h"],
            ),
            "error_handling": SubsystemInfo(
                name="Error Handling",
                description="Error handling and assertions",
                key_functions=[
                    "perror", "strerror", "errno",
                    "assert", "abort", "exit", "_exit",
                    "setjmp", "longjmp",
                    "atexit", "at_quick_exit",
                    "std::exception", "std::throw", "std::catch",
                ],
                patterns=[
                    r"^(perror|strerror)$",
                    r"^(assert|abort|exit)$",
                    r"^(set|long)jmp$",
                ],
                related_files=["errno.h", "assert.h", "setjmp.h", "exception"],
            ),
            "system_calls": SubsystemInfo(
                name="System Calls",
                description="Operating system interface",
                key_functions=[
                    "fork", "exec", "execv", "execve", "execvp",
                    "wait", "waitpid", "kill", "signal", "sigaction",
                    "getpid", "getppid", "getuid", "geteuid",
                    "mmap", "munmap", "mprotect",
                    "ioctl", "fcntl",
                ],
                patterns=[
                    r"^exec(v|ve|vp|l|le|lp)?$",
                    r"^(fork|wait|waitpid|kill)$",
                    r"^(m|un)?map$",
                    r"^(get|set)(uid|gid|pid)$",
                ],
                related_files=["unistd.h", "sys/types.h", "sys/wait.h", "signal.h"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load C/C++ specific LLM prompts."""
        return {
            "security": {
                "system": (
                    "You are a C/C++ security expert specializing in identifying "
                    "vulnerabilities such as buffer overflows, use-after-free, "
                    "integer overflows, and format string vulnerabilities. "
                    "Analyze code for OWASP and CWE-classified security issues."
                ),
                "user_template": (
                    "Analyze the following C/C++ code for security vulnerabilities:\n\n"
                    "{code}\n\n"
                    "Evidence from CPG analysis:\n{evidence}\n\n"
                    "Identify potential vulnerabilities, their severity, and "
                    "recommended mitigations."
                ),
            },
            "hardening": {
                "system": (
                    "You are a C/C++ security expert specializing in D3FEND Source Code "
                    "Hardening techniques. Analyze code for defensive coding practices "
                    "including variable initialization, pointer validation, memory safety, "
                    "and safe library function usage."
                ),
                "user_template": (
                    "Analyze the following C/C++ code for D3FEND hardening compliance:\n\n"
                    "{code}\n\n"
                    "Hardening findings:\n{evidence}\n\n"
                    "Identify missing defensive practices and recommend improvements."
                ),
            },
            "performance": {
                "system": (
                    "You are a C/C++ performance optimization expert. "
                    "Analyze code for performance issues including memory allocation "
                    "patterns, cache efficiency, algorithmic complexity, and "
                    "opportunities for parallelization."
                ),
                "user_template": (
                    "Analyze the following C/C++ code for performance issues:\n\n"
                    "{code}\n\n"
                    "Performance metrics:\n{evidence}\n\n"
                    "Identify performance bottlenecks and optimization opportunities."
                ),
            },
            "refactoring": {
                "system": (
                    "You are a C/C++ code quality expert. "
                    "Analyze code for refactoring opportunities, code smells, "
                    "and adherence to modern C++ best practices."
                ),
                "user_template": (
                    "Analyze the following C/C++ code for refactoring opportunities:\n\n"
                    "{code}\n\n"
                    "Code analysis:\n{evidence}\n\n"
                    "Suggest refactoring improvements and modernization opportunities."
                ),
            },
            "onboarding": {
                "system": (
                    "You are a C/C++ codebase expert helping developers understand "
                    "code structure, dependencies, and architecture."
                ),
                "user_template": (
                    "Explain the following C/C++ code and its role in the codebase:\n\n"
                    "{code}\n\n"
                    "Context:\n{evidence}\n\n"
                    "Provide a clear explanation suitable for onboarding new developers."
                ),
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load C/C++ specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=[
                    "buffer overflow", "memory leak", "use-after-free",
                    "double free", "null pointer", "format string",
                    "integer overflow", "stack overflow", "heap overflow",
                    "vulnerability", "exploit", "CVE", "CWE",
                    "injection", "unsafe", "insecure",
                ],
                patterns=[
                    r"buffer\s+overflow",
                    r"use[-\s]after[-\s]free",
                    r"memory\s+leak",
                    r"double\s+free",
                    r"null\s+pointer",
                    r"format\s+string",
                ],
                examples=[
                    "Find buffer overflow vulnerabilities",
                    "Check for memory leaks",
                    "Detect use-after-free bugs",
                ],
                priority=10,
            ),
            "hardening": IntentPattern(
                intent_id="hardening",
                keywords=[
                    "hardening", "d3fend", "defensive", "initialization",
                    "null check", "bounds check", "safe function",
                    "trusted library", "type validation", "reference nullification",
                ],
                patterns=[
                    r"hard(en|ening)",
                    r"d3fend",
                    r"defensive\s+(coding|practice)",
                    r"null\s+check",
                ],
                examples=[
                    "Check D3FEND hardening compliance",
                    "Find missing null checks",
                    "Detect unsafe function usage",
                ],
                priority=9,
            ),
            "performance": IntentPattern(
                intent_id="performance",
                keywords=[
                    "performance", "optimize", "slow", "fast", "speed",
                    "memory usage", "allocation", "cache", "hotspot",
                    "profiling", "benchmark", "latency", "throughput",
                    "complexity", "O(n)", "efficient",
                ],
                patterns=[
                    r"performance\s+(issue|problem|bottleneck)",
                    r"(memory|cpu)\s+usage",
                    r"cache\s+(miss|hit|efficiency)",
                ],
                examples=[
                    "Find performance hotspots",
                    "Analyze memory allocation patterns",
                    "Identify cache-inefficient code",
                ],
                priority=8,
            ),
            "refactoring": IntentPattern(
                intent_id="refactoring",
                keywords=[
                    "refactor", "clean", "improve", "modernize",
                    "code smell", "duplicate", "dead code",
                    "technical debt", "legacy", "deprecated",
                    "best practice", "idiom", "pattern",
                ],
                patterns=[
                    r"(code\s+)?smell",
                    r"refactor(ing)?",
                    r"dead\s+code",
                    r"duplicate\s+code",
                ],
                examples=[
                    "Find code that needs refactoring",
                    "Detect dead code",
                    "Identify duplicate implementations",
                ],
                priority=6,
            ),
            "onboarding": IntentPattern(
                intent_id="onboarding",
                keywords=[
                    "explain", "understand", "how does", "what is",
                    "overview", "architecture", "structure", "design",
                    "documentation", "guide", "tutorial",
                ],
                patterns=[
                    r"(explain|understand)\s+.*code",
                    r"how\s+does\s+.*work",
                    r"what\s+is\s+.*for",
                ],
                examples=[
                    "Explain how the memory allocator works",
                    "Give me an overview of the threading model",
                    "What does this function do?",
                ],
                priority=4,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load C/C++ security vulnerability patterns from YAML or defaults."""
        # Try to load from YAML first
        config = self._load_yaml_config("security_patterns.yaml")
        if config and "patterns" in config:
            patterns = []
            for data in config.get("patterns", []):
                patterns.append(SecurityPattern(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    description=data.get("description", ""),
                    severity=data.get("severity", "medium"),
                    cwe_id=data.get("cwe_id"),
                    indicators=data.get("indicators", []),
                    sinks=data.get("sinks", []),
                    sources=data.get("sources", []),
                    sanitizers=data.get("sanitizers", []),
                ))
            return patterns

        # Fallback to inline defaults
        return [
            SecurityPattern(
                id="buffer_overflow",
                name="Buffer Overflow",
                description="Writing beyond buffer boundaries can cause crashes or code execution",
                severity="critical",
                cwe_id="CWE-120",
                indicators=["strcpy", "strcat", "sprintf", "gets", "scanf"],
                sinks=["strcpy", "strcat", "sprintf", "memcpy", "gets"],
                sources=["user_input", "argv", "getenv", "read", "recv"],
                sanitizers=["strncpy", "strncat", "snprintf", "bounds_check"],
            ),
            SecurityPattern(
                id="use_after_free",
                name="Use After Free",
                description="Accessing memory after it has been freed leads to undefined behavior",
                severity="critical",
                cwe_id="CWE-416",
                indicators=["free", "delete", "realloc"],
                sinks=["dereference", "read", "write"],
                sources=["malloc", "calloc", "new"],
                sanitizers=["null_check", "smart_pointer"],
            ),
            SecurityPattern(
                id="double_free",
                name="Double Free",
                description="Freeing the same memory twice can corrupt heap metadata",
                severity="high",
                cwe_id="CWE-415",
                indicators=["free", "delete"],
                sinks=["free", "delete"],
                sources=["malloc", "calloc", "new"],
                sanitizers=["null_after_free", "smart_pointer"],
            ),
            SecurityPattern(
                id="null_pointer_deref",
                name="Null Pointer Dereference",
                description="Dereferencing null pointer causes crashes",
                severity="high",
                cwe_id="CWE-476",
                indicators=["*ptr", "ptr->", "ptr["],
                sinks=["dereference"],
                sources=["malloc", "calloc", "function_return"],
                sanitizers=["null_check", "assert"],
            ),
            SecurityPattern(
                id="format_string",
                name="Format String Vulnerability",
                description="User-controlled format strings can leak or modify memory",
                severity="critical",
                cwe_id="CWE-134",
                indicators=["printf", "sprintf", "fprintf", "syslog"],
                sinks=["printf", "sprintf", "fprintf", "syslog"],
                sources=["user_input", "argv", "getenv"],
                sanitizers=["static_format", "format_validation"],
            ),
            SecurityPattern(
                id="integer_overflow",
                name="Integer Overflow",
                description="Integer overflow can cause buffer overflows or logic errors",
                severity="high",
                cwe_id="CWE-190",
                indicators=["malloc", "calloc", "array_index", "size_calc"],
                sinks=["malloc", "array_access", "memcpy"],
                sources=["user_input", "arithmetic"],
                sanitizers=["bounds_check", "safe_math"],
            ),
            SecurityPattern(
                id="command_injection",
                name="Command Injection",
                description="User input in system commands allows arbitrary command execution",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["system", "popen", "exec"],
                sinks=["system", "popen", "execve", "execvp"],
                sources=["user_input", "argv", "getenv"],
                sanitizers=["input_validation", "whitelist", "escape"],
            ),
            SecurityPattern(
                id="path_traversal",
                name="Path Traversal",
                description="User-controlled paths can access unauthorized files",
                severity="high",
                cwe_id="CWE-22",
                indicators=["fopen", "open", "stat", "access"],
                sinks=["fopen", "open", "stat", "unlink"],
                sources=["user_input", "argv", "getenv"],
                sanitizers=["path_canonicalization", "chroot", "whitelist"],
            ),
            SecurityPattern(
                id="race_condition",
                name="Race Condition",
                description="Time-of-check to time-of-use vulnerabilities",
                severity="medium",
                cwe_id="CWE-362",
                indicators=["access", "open", "stat", "check"],
                sinks=["open", "fopen", "unlink", "chmod"],
                sources=["filesystem", "shared_memory"],
                sanitizers=["atomic_operation", "lock", "flock"],
            ),
            SecurityPattern(
                id="memory_leak",
                name="Memory Leak",
                description="Allocated memory not freed leads to resource exhaustion",
                severity="medium",
                cwe_id="CWE-401",
                indicators=["malloc", "calloc", "new", "strdup"],
                sinks=["return", "exit", "error_path"],
                sources=["malloc", "calloc", "new"],
                sanitizers=["free", "delete", "smart_pointer", "RAII"],
            ),
        ]

    def get_hardening_patterns(self) -> List[Dict[str, Any]]:
        """
        Get C/C++-specific D3FEND hardening patterns.

        Returns patterns that extend the generic D3FEND checks with
        C/C++-specific detection logic.

        Returns:
            List of hardening pattern definitions for HardeningScanner
        """
        # Try to load from YAML first
        config = self._load_yaml_config("hardening_patterns.yaml")
        if config and "patterns" in config:
            return config.get("patterns", [])

        # Fallback to inline patterns
        return [
            # D3-VI: Variable Initialization (C/C++ specific)
            {
                "id": "D3-VI-CPP-001",
                "d3fend_id": "D3-VI",
                "d3fend_name": "Variable Initialization",
                "category": "initialization",
                "severity": "high",
                "description": "Uninitialized stack variable in C/C++",
                "cpgql_query": """
                    SELECT DISTINCT
                        nm.id,
                        nm.name AS method_name,
                        nm.filename,
                        nm.line_number,
                        nm.code AS code_snippet,
                        'UNINITIALIZED_STACK_VAR' AS violation_type
                    FROM nodes_method nm
                    WHERE (
                        nm.code LIKE '%char %[%]%'
                        OR nm.code LIKE '%int %[%]%'
                        OR nm.code LIKE '%void *%[^=]*;%'
                    )
                    AND nm.code NOT LIKE '%=%'
                    AND nm.code NOT LIKE '%{%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-457"],
                "language_scope": ["c", "cpp"],
                "indicators": ["char buf[", "int arr[", "void *p;"],
                "good_patterns": ["= {0}", "= {}", "memset(", "= 0", "= NULL"],
                "remediation": "Initialize all stack variables at declaration.",
            },
            # D3-VI: calloc vs malloc
            {
                "id": "D3-VI-CPP-002",
                "d3fend_id": "D3-VI",
                "d3fend_name": "Variable Initialization",
                "category": "initialization",
                "severity": "medium",
                "description": "Using malloc without initialization (prefer calloc)",
                "cpgql_query": """
                    SELECT DISTINCT
                        nc.id,
                        nm.name AS method_name,
                        nm.filename,
                        nc.line_number,
                        nc.code AS code_snippet,
                        'MALLOC_WITHOUT_INIT' AS violation_type
                    FROM nodes_call nc
                    JOIN nodes_method nm ON nc.method_id = nm.id
                    WHERE nc.name = 'malloc'
                    AND nm.code NOT LIKE '%memset%'
                    AND nm.code NOT LIKE '%memcpy%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-457"],
                "language_scope": ["c", "cpp"],
                "indicators": ["malloc("],
                "good_patterns": ["calloc(", "memset(", "= {0}"],
                "remediation": "Use calloc() for zero-initialized memory or memset() after malloc().",
            },
            # D3-TL: Trusted Library - Unsafe function detection
            {
                "id": "D3-TL-CPP-001",
                "d3fend_id": "D3-TL",
                "d3fend_name": "Trusted Library",
                "category": "library_safety",
                "severity": "high",
                "description": "Use of deprecated/unsafe C library functions",
                "cpgql_query": """
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
                    WHERE nc.name IN ('strcpy', 'strcat', 'sprintf', 'vsprintf',
                                      'gets', 'scanf', 'strtok', 'tmpnam', 'mktemp')
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 100
                """,
                "cwe_ids": ["CWE-676", "CWE-242", "CWE-120"],
                "language_scope": ["c", "cpp"],
                "indicators": ["strcpy", "gets", "sprintf", "scanf", "strtok"],
                "good_patterns": ["strncpy", "strlcpy", "snprintf", "fgets", "strtok_r"],
                "remediation": "Replace with bounded/safe alternatives: strcpy->strncpy, sprintf->snprintf, gets->fgets.",
            },
            # D3-TL: Weak random number generators
            {
                "id": "D3-TL-CPP-002",
                "d3fend_id": "D3-TL",
                "d3fend_name": "Trusted Library",
                "category": "library_safety",
                "severity": "medium",
                "description": "Use of weak random number generator",
                "cpgql_query": """
                    SELECT DISTINCT
                        nc.id,
                        nc.name AS unsafe_function,
                        nm.name AS method_name,
                        nm.filename,
                        nc.line_number,
                        nc.code AS code_snippet,
                        'WEAK_RANDOM' AS violation_type
                    FROM nodes_call nc
                    JOIN nodes_method nm ON nc.method_id = nm.id
                    WHERE nc.name IN ('rand', 'srand', 'random', 'srandom')
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-338", "CWE-330"],
                "language_scope": ["c", "cpp"],
                "indicators": ["rand(", "srand(", "random("],
                "good_patterns": ["arc4random(", "getrandom(", "/dev/urandom", "RAND_bytes"],
                "remediation": "Use cryptographically secure random: arc4random(), getrandom(), or OpenSSL RAND_bytes().",
            },
            # D3-NPC: Null Pointer Checking
            {
                "id": "D3-NPC-CPP-001",
                "d3fend_id": "D3-NPC",
                "d3fend_name": "Null Pointer Checking",
                "category": "pointer_safety",
                "severity": "high",
                "description": "Pointer dereference without NULL check after allocation",
                "cpgql_query": """
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
                    WHERE nc.name IN ('malloc', 'calloc', 'realloc', 'strdup', 'strndup')
                    AND nm.code NOT LIKE '%if%NULL%'
                    AND nm.code NOT LIKE '%if%!%'
                    AND nm.code NOT LIKE '%assert%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-476", "CWE-690"],
                "language_scope": ["c", "cpp"],
                "indicators": ["malloc(", "calloc(", "realloc(", "strdup("],
                "good_patterns": ["if (ptr == NULL)", "if (!ptr)", "assert(ptr)"],
                "remediation": "Always check allocation results: if (ptr == NULL) { handle_error(); }",
            },
            # D3-RN: Reference Nullification
            {
                "id": "D3-RN-CPP-001",
                "d3fend_id": "D3-RN",
                "d3fend_name": "Reference Nullification",
                "category": "memory_safety",
                "severity": "high",
                "description": "free() without pointer nullification",
                "cpgql_query": """
                    SELECT DISTINCT
                        nc.id,
                        nm.name AS method_name,
                        nm.filename,
                        nc.line_number,
                        nc.code AS code_snippet,
                        'MISSING_NULLIFICATION' AS violation_type
                    FROM nodes_call nc
                    JOIN nodes_method nm ON nc.method_id = nm.id
                    WHERE nc.name IN ('free', 'delete')
                    AND nm.code NOT LIKE '%NULL%'
                    AND nm.code NOT LIKE '%nullptr%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-416"],
                "language_scope": ["c", "cpp"],
                "indicators": ["free(", "delete "],
                "good_patterns": ["ptr = NULL", "ptr = nullptr", "SAFE_FREE("],
                "remediation": "Set pointer to NULL after free: free(ptr); ptr = NULL;",
            },
            # D3-IRV: Integer Range Validation
            {
                "id": "D3-IRV-CPP-001",
                "d3fend_id": "D3-IRV",
                "d3fend_name": "Integer Range Validation",
                "category": "integer_safety",
                "severity": "high",
                "description": "Integer multiplication in allocation without overflow check",
                "cpgql_query": """
                    SELECT DISTINCT
                        nc.id,
                        nm.name AS method_name,
                        nm.filename,
                        nc.line_number,
                        nc.code AS code_snippet,
                        'INTEGER_OVERFLOW_RISK' AS violation_type
                    FROM nodes_call nc
                    JOIN nodes_method nm ON nc.method_id = nm.id
                    WHERE nc.name IN ('malloc', 'calloc', 'realloc')
                    AND nc.code LIKE '%*%'
                    AND nc.code NOT LIKE '%SIZE_MAX%'
                    AND nc.code NOT LIKE '%overflow%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-190", "CWE-680"],
                "language_scope": ["c", "cpp"],
                "indicators": ["malloc(n * ", "malloc(size * "],
                "good_patterns": ["SIZE_MAX / sizeof", "__builtin_mul_overflow", "safe_mul"],
                "remediation": "Check for overflow: if (n > SIZE_MAX / sizeof(item)) return NULL;",
            },
            # D3-MBSV: Memory Block Start Validation
            {
                "id": "D3-MBSV-CPP-001",
                "d3fend_id": "D3-MBSV",
                "d3fend_name": "Memory Block Start Validation",
                "category": "pointer_safety",
                "severity": "medium",
                "description": "Pointer arithmetic without bounds check",
                "cpgql_query": """
                    SELECT DISTINCT
                        nm.id,
                        nm.name AS method_name,
                        nm.filename,
                        nm.line_number,
                        nm.code AS code_snippet,
                        'UNSAFE_POINTER_ARITHMETIC' AS violation_type
                    FROM nodes_method nm
                    WHERE (
                        nm.code LIKE '%ptr + %'
                        OR nm.code LIKE '%ptr++%'
                        OR nm.code LIKE '%++ptr%'
                    )
                    AND nm.code NOT LIKE '%< end%'
                    AND nm.code NOT LIKE '%< size%'
                    AND nm.code NOT LIKE '%bounds%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-119", "CWE-787"],
                "language_scope": ["c", "cpp"],
                "indicators": ["ptr + ", "ptr++", "++ptr"],
                "good_patterns": ["< end", "< size", "< limit", "bounds_check"],
                "remediation": "Always check bounds before pointer arithmetic.",
            },
            # D3-VTV: Variable Type Validation
            {
                "id": "D3-VTV-CPP-001",
                "d3fend_id": "D3-VTV",
                "d3fend_name": "Variable Type Validation",
                "category": "type_safety",
                "severity": "medium",
                "description": "C-style cast without type verification",
                "cpgql_query": """
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
                    )
                    AND nm.code NOT LIKE '%assert%'
                    AND nm.code NOT LIKE '%sizeof%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-843", "CWE-704"],
                "language_scope": ["c", "cpp"],
                "indicators": ["(void *)", "(char *)", "reinterpret_cast"],
                "good_patterns": ["static_cast", "dynamic_cast", "assert("],
                "remediation": "Use type-safe casts in C++ or add runtime type checks in C.",
            },
            # D3-CS: Credential Scrubbing (C/C++ specific patterns)
            {
                "id": "D3-CS-CPP-001",
                "d3fend_id": "D3-CS",
                "d3fend_name": "Credential Scrubbing",
                "category": "credential_mgmt",
                "severity": "critical",
                "description": "Hardcoded credentials in C/C++ code",
                "cpgql_query": """
                    SELECT DISTINCT
                        nl.id,
                        nm.name AS method_name,
                        nm.filename,
                        nl.line_number,
                        nl.code AS code_snippet,
                        'HARDCODED_CREDENTIAL' AS violation_type
                    FROM nodes_literal nl
                    JOIN nodes_method nm ON nl.method_id = nm.id
                    WHERE (
                        LOWER(nl.code) LIKE '%password%'
                        OR LOWER(nl.code) LIKE '%api_key%'
                        OR LOWER(nl.code) LIKE '%secret%'
                        OR LOWER(nl.code) LIKE '%private_key%'
                    )
                    AND nl.code LIKE '%"%'
                    AND nl.code LIKE '%=%'
                    AND nm.name NOT LIKE 'test_%'
                    LIMIT 50
                """,
                "cwe_ids": ["CWE-798", "CWE-259"],
                "language_scope": ["c", "cpp"],
                "indicators": ["password =", "api_key =", "secret ="],
                "good_patterns": ["getenv(", "fgets(", "config_get("],
                "remediation": "Use environment variables or config files for credentials.",
            },
        ]

    def get_sanitization_patterns(self) -> List[Dict]:
        """
        Get C/C++ sanitization patterns for dataflow analysis.

        Returns:
            List of sanitization pattern definitions with name, pattern, and confidence
        """
        return [
            # Bounds checking
            {"name": "strncpy", "function": "strncpy", "confidence": 0.7,
             "description": "Bounded string copy"},
            {"name": "strncat", "function": "strncat", "confidence": 0.7,
             "description": "Bounded string concatenation"},
            {"name": "snprintf", "function": "snprintf", "confidence": 0.8,
             "description": "Bounded formatted print"},
            {"name": "memcpy_s", "function": "memcpy_s", "confidence": 0.9,
             "description": "Safe memory copy"},
            {"name": "strcpy_s", "function": "strcpy_s", "confidence": 0.9,
             "description": "Safe string copy"},

            # Input validation patterns
            {"name": "bounds_check", "pattern": r"if\s*\([^)]*<\s*\w+_(size|len|max)",
             "confidence": 0.6, "description": "Bounds checking condition"},
            {"name": "null_check", "pattern": r"if\s*\([^)]*!=\s*NULL",
             "confidence": 0.7, "description": "Null pointer check"},
            {"name": "length_check", "pattern": r"strlen\s*\([^)]+\)\s*[<>=]",
             "confidence": 0.6, "description": "String length validation"},

            # Integer overflow protection
            {"name": "safe_add", "function": "safe_add", "confidence": 0.9,
             "description": "Safe integer addition"},
            {"name": "safe_mul", "function": "safe_mul", "confidence": 0.9,
             "description": "Safe integer multiplication"},

            # Memory safety
            {"name": "free_null", "pattern": r"free\s*\([^)]+\)\s*;\s*\w+\s*=\s*NULL",
             "confidence": 0.8, "description": "Free with null assignment"},

            # Escape functions
            {"name": "escape_html", "function": "escape_html", "confidence": 0.8,
             "description": "HTML escaping"},
            {"name": "escape_sql", "function": "escape_sql", "confidence": 0.8,
             "description": "SQL escaping"},
        ]

    def get_memory_functions(self) -> Dict[str, List[str]]:
        """
        Get C/C++ memory management function mappings.

        Returns:
            Dictionary with allocate/free/copy categories
        """
        return {
            "allocate": ["malloc", "calloc", "realloc", "new", "new[]",
                        "aligned_alloc", "posix_memalign", "strdup", "strndup"],
            "free": ["free", "delete", "delete[]"],
            "copy": ["memcpy", "memmove", "memset", "strcpy", "strncpy"],
        }

    def get_lock_functions(self) -> List[str]:
        """
        Get C/C++ locking-related functions for concurrency analysis.

        Returns:
            List of lock/synchronization function names
        """
        return [
            # POSIX threads
            "pthread_mutex_lock", "pthread_mutex_unlock",
            "pthread_mutex_trylock", "pthread_mutex_timedlock",
            "pthread_rwlock_rdlock", "pthread_rwlock_wrlock",
            "pthread_rwlock_unlock", "pthread_spin_lock",
            "pthread_spin_unlock", "pthread_cond_wait",
            "pthread_cond_signal", "pthread_cond_broadcast",
            # Semaphores
            "sem_wait", "sem_post", "sem_trywait",
            # C++ std
            "std::mutex::lock", "std::mutex::unlock",
            "std::lock_guard", "std::unique_lock",
            "std::shared_lock", "std::atomic",
        ]

    def get_dangerous_functions(self) -> Dict[str, List[str]]:
        """
        Get C/C++ functions that are prone to security vulnerabilities.

        Returns:
            Dictionary mapping vulnerability type to dangerous function lists
        """
        return {
            "buffer_overflow": [
                "strcpy", "strcat", "sprintf", "vsprintf",
                "gets", "scanf", "sscanf", "fscanf",
                "stpcpy", "wcscpy", "wcscat", "swprintf",
            ],
            "format_string": [
                "printf", "fprintf", "sprintf", "snprintf",
                "vprintf", "vfprintf", "vsprintf", "vsnprintf",
                "syslog", "err", "warn",
            ],
            "command_injection": [
                "system", "popen", "exec", "execl", "execle",
                "execlp", "execv", "execve", "execvp", "execvpe",
                "ShellExecute", "WinExec", "CreateProcess",
            ],
            "path_traversal": [
                "fopen", "open", "access", "stat", "lstat",
                "unlink", "remove", "rename", "chmod", "chown",
                "mkdir", "rmdir", "opendir",
            ],
            "memory_corruption": [
                "memcpy", "memmove", "memset", "bcopy", "bzero",
                "realloc", "reallocarray",
            ],
            "integer_overflow": [
                "atoi", "atol", "atoll", "strtol", "strtoul",
                "strtoll", "strtoull",
            ],
        }

    def get_noise_functions(self) -> List[str]:
        """
        Get standard library functions that are usually noise in analysis.

        Returns:
            List of function names to filter as noise
        """
        return [
            "memcpy", "memset", "memmove", "memcmp", "memchr",
            "strcmp", "strncmp", "strcasecmp", "strncasecmp",
            "strlen", "strnlen", "strchr", "strrchr", "strstr",
            "strpbrk", "strspn", "strcspn",
            "isalpha", "isdigit", "isalnum", "isspace", "isupper",
            "islower", "ispunct", "isprint", "iscntrl", "isxdigit",
            "toupper", "tolower",
            "qsort", "bsearch",
            "abs", "labs", "llabs", "fabs", "floor", "ceil",
            "round", "sqrt", "pow", "log", "exp", "sin", "cos",
            "malloc", "calloc", "realloc", "free",
            "fflush", "feof", "ferror", "clearerr",
        ]

    def get_thread_functions(self) -> List[str]:
        """
        Get pthread/threading functions for concurrency analysis.

        Returns:
            List of thread-related function names
        """
        return [
            "pthread_create", "pthread_join", "pthread_exit",
            "pthread_detach", "pthread_cancel", "pthread_self",
            "pthread_equal", "pthread_once",
            "pthread_attr_init", "pthread_attr_destroy",
            "pthread_attr_setdetachstate", "pthread_attr_getdetachstate",
            "pthread_attr_setstacksize", "pthread_attr_getstacksize",
            "pthread_mutex_init", "pthread_mutex_destroy",
            "pthread_mutex_lock", "pthread_mutex_unlock",
            "pthread_mutex_trylock", "pthread_mutex_timedlock",
            "pthread_rwlock_init", "pthread_rwlock_destroy",
            "pthread_rwlock_rdlock", "pthread_rwlock_wrlock",
            "pthread_rwlock_unlock", "pthread_rwlock_tryrdlock",
            "pthread_rwlock_trywrlock",
            "pthread_cond_init", "pthread_cond_destroy",
            "pthread_cond_wait", "pthread_cond_timedwait",
            "pthread_cond_signal", "pthread_cond_broadcast",
            "pthread_spin_init", "pthread_spin_destroy",
            "pthread_spin_lock", "pthread_spin_unlock",
            "pthread_spin_trylock",
            "pthread_barrier_init", "pthread_barrier_destroy",
            "pthread_barrier_wait",
            "pthread_key_create", "pthread_key_delete",
            "pthread_setspecific", "pthread_getspecific",
            "sem_init", "sem_destroy", "sem_wait", "sem_trywait",
            "sem_timedwait", "sem_post", "sem_getvalue",
            "sem_open", "sem_close", "sem_unlink",
        ]

    def get_safe_alternatives(self) -> Dict[str, str]:
        """
        Get safe alternatives for dangerous functions.

        Returns:
            Dictionary mapping dangerous function to safe alternative
        """
        return {
            "strcpy": "strncpy or strlcpy",
            "strcat": "strncat or strlcat",
            "sprintf": "snprintf",
            "vsprintf": "vsnprintf",
            "gets": "fgets",
            "scanf": "fgets + sscanf with bounds",
            "memcpy": "memcpy_s (C11) or manual bounds check",
            "system": "execve with sanitized args",
            "popen": "fork + execve",
            "rand": "arc4random or getrandom",
        }


# Module-level instance for easy registration
generic_cpp_plugin = GenericCppDomainPlugin()


# Auto-register the plugin when module is imported
def _auto_register():
    """Auto-register C/C++ plugin with the registry."""
    try:
        from ..registry import DomainRegistry
        DomainRegistry.register(generic_cpp_plugin)
        logger.debug(f"Auto-registered {generic_cpp_plugin.name} domain plugin")
    except ImportError:
        pass


_auto_register()
