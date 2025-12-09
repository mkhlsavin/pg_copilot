"""
Intent taxonomy for 14 enterprise scenarios.

Each intent includes:
- id: Unique scenario identifier
- name: Human-readable name
- keywords: List of trigger keywords/phrases
- examples: Sample user queries
- priority: Routing priority (higher = check first)
"""

INTENT_TAXONOMY = {
    "onboarding": {
        "id": "scenario_01_onboarding",
        "name": "Codebase Onboarding",
        "keywords": [
            "onboard", "overview", "introduction", "getting started",
            "explain codebase", "architecture overview", "how does it work",
            "subsystem", "module structure", "main components",
            # Code navigation keywords
            "where is", "defined", "definition", "find function",
            "locate", "signature", "which file",
            # Call graph keywords
            "call", "caller", "callee", "calls", "called by",
            "who calls", "what calls", "functions call",
            # Dataflow keywords
            "trace", "dataflow", "data flow", "variable",
            "assigned", "used by", "flows to",
            # Subsystem explanation keywords (Scenario 13)
            "explain subsystem", "subsystem overview", "what does the subsystem",
            "how does the subsystem", "subsystem architecture", "subsystem components",
            "main functions", "key functions", "important functions",
            # Business logic keywords (Scenario 16)
            "business logic", "workflow", "what happens when",
            "query processing", "query execution", "how queries",
            "transaction flow", "data modification", "insert workflow",
            "update workflow", "delete workflow", "select workflow",
            "explain the process", "step by step", "flow of",
            # NOTE: Debug keywords REMOVED - moved to dedicated debugging scenario (priority 9)
            # PostgreSQL subsystem names (Scenario 13 - higher priority than documentation)
            "executor", "optimizer", "parser", "planner", "buffer manager",
            "buffer pool", "WAL", "write-ahead log", "transaction log",
            "lock manager", "catalog", "rewriter", "postmaster",
            "shared memory", "storage manager", "MVCC", "vacuum",
            "checkpoint", "recovery", "replication", "SPI"
        ],
        "examples": [
            "Give me an overview of the PostgreSQL codebase",
            "What are the main subsystems?",
            "Explain how the executor works",
            "Where is the function heap_insert defined?",
            "Which functions call heap_insert?",
            "Trace the variable slot in ExecScan",
            "Explain the planner subsystem",
            "What are the key functions in the optimizer?",
            "How does query processing work step by step?",
            "What happens when a user runs an INSERT query?",
            "How to trace execution through the executor?",
            "What are good breakpoints for debugging query execution?"
        ],
        "priority": 5
    },

    "security_audit": {
        "id": "scenario_02_security_audit",
        "name": "Security Audit",
        "keywords": [
            "security", "vulnerability", "vulnerabilities", "exploit", "cve",
            "sql injection", "buffer overflow", "privilege escalation",
            "unsafe", "taint", "sanitize", "validate input",
            "untrusted", "handle input",
            # Unsafe C functions that indicate security concerns
            "sprintf", "strcpy", "strcat", "gets", "scanf",
            "bounds", "bounds checking", "unbounded",
            # Memory safety keywords
            "memory corruption", "heap overflow", "stack overflow",
            "use after free", "double free", "null pointer",
            # Additional vulnerability detection keywords
            "password", "credential", "plaintext", "authentication",
            "injection", "overflow", "TOCTOU", "race condition",
            "path traversal", "sensitive information", "info leak",
            "error message", "leak", "deserialization", "integer overflow",
            "dynamic query", "potential",
            # Security-specific audit keywords (NOT entry_points - those have own scenario)
            "privilege escalation", "bypass", "authentication bypass",
            "lateral movement", "exfiltration"
            # NOTE: entry_point, attack_surface, network-facing moved to entry_points scenario
        ],
        "examples": [
            "Find all SQL injection vulnerabilities",
            "Which functions handle untrusted input?",
            "Show me buffer overflow risks",
            "Find functions handling passwords in plaintext",
            "Find potential path traversal vulnerabilities",
            "List network-facing functions that handle client input",
            "Find all external entry points"
        ],
        "priority": 10
    },

    "documentation": {
        "id": "scenario_03_documentation",
        "name": "Documentation Generation",
        "keywords": [
            "document", "documentation", "generate docs", "explain function",
            "what does", "how does", "describe", "api doc",
            "comment", "javadoc", "generate"
        ],
        "examples": [
            "Generate documentation for the planner module",
            "What does ExecInitNode do?",
            "Document all functions in executor"
        ],
        "priority": 3
    },

    "feature_development": {
        "id": "scenario_04_feature_dev",
        "name": "Feature Development",
        "keywords": [
            # Multi-word discriminators (check FIRST for higher precision)
            # These distinguish from security_audit which has "injection" for SQL injection
            "hook injection", "injection point", "hook injection point",
            "planner hook injection", "executor hook injection",
            # Multi-word for specific question patterns
            "process utility hooks", "utility hooks for", "DDL extension",
            "authentication hook", "hook points", "extension hooks",
            # Feature implementation
            "implement", "add feature", "create", "build",
            "develop", "where to add", "how to extend",
            "where should i add", "integration point",
            # Extension and hook specific
            "hook", "extension hook", "executor hook",
            "planner hook", "ProcessUtility_hook", "ExecutorStart_hook",
            "ExecutorRun_hook", "post_parse_analyze_hook",
            # Extension points
            "extension point", "plugin", "add algorithm",
            "new join", "new scan", "custom plan", "custom node",
            "add path", "create path",
            # Custom access methods
            "access method", "table access", "index access",
            "foreign data wrapper", "fdw", "custom aggregate"
        ],
        "examples": [
            "Where should I add a new join algorithm?",
            "How to implement custom index type?",
            "Find extension points for query optimizer",
            "Find extension hooks in the executor",
            "Where can I add custom plan nodes?"
        ],
        "priority": 7
    },

    "refactoring": {
        "id": "scenario_05_refactoring",
        "name": "Refactoring Assistance",
        "keywords": [
            "refactor", "clean up", "simplify", "improve",
            "code smell", "duplicate", "complexity", "technical debt",
            "long function", "god class", "complex", "too complex",
            # Dead code detection keywords
            "dead code", "deprecated", "never called", "unused", "obsolete",
            "unreachable", "static function", "#if 0", "disabled code",
            "commented out", "commented function", "dead function",
            "TODO:REMOVE", "TODO remove", "FIXME remove", "remove function",
            # Code duplicates keywords (Scenario 07)
            "clone", "copy-paste", "copy-pasted", "copied code",
            "similar code", "identical code", "duplicate function",
            "similar pattern", "code duplication", "merge", "extract"
        ],
        "examples": [
            "Find duplicate code in the planner",
            "Which functions are too complex?",
            "Suggest refactoring for parse_relation.c",
            "Find functions marked as deprecated",
            "List static functions that are never called",
            "Find copy-pasted code blocks",
            "Find similar code patterns"
        ],
        "priority": 6
    },

    "performance": {
        "id": "scenario_06_performance",
        "name": "Performance Optimization",
        "keywords": [
            "performance", "optimize", "slow", "bottleneck",
            "hotspot", "profiling", "cache", "memory leak",
            "allocate", "cpu intensive", "allocation", "memory",
            # Complexity analysis keywords (Scenario 06) - S06 FIX: Added missing keywords
            "cyclomatic", "complexity", "in-degree", "out-degree",
            "pagerank", "betweenness", "centrality", "closeness",
            "nesting depth", "nesting level", "deeply nested",
            "cognitive complexity", "most called", "frequently called",
            "high complexity", "performance analysis", "scaling",
            # S06 FIX: Function size and complexity metrics
            "lines of code", "LOC", "function length", "function size",
            "parameter count", "too many parameters", "long function",
            "most complex", "highest complexity", "complexity metric",
            "function metrics", "code metrics", "metric analysis",
            # Memory analysis keywords (Scenario 10)
            "palloc", "pfree", "repalloc", "MemoryContext",
            "AllocSetContextCreate", "memory accounting", "memory context",
            "shared memory", "ShmemAlloc", "DSM", "work_mem",
            "slab allocator", "bump allocator", "memory limit",
            "fragmentation", "unbounded growth", "double-free",
            # Concurrency analysis keywords (Scenario 09)
            "LWLock", "SpinLock", "concurrency", "race condition",
            "synchronization", "atomic", "volatile", "barrier",
            "deadlock", "lock contention", "TOCTOU", "signal handler",
            "parallel", "worker", "condition variable", "latch",
            "lock-free", "compare-and-swap", "CAS", "IPC",
            "ProcArray", "thundering herd", "starvation", "false sharing"
        ],
        "examples": [
            "Find performance hotspots in the executor",
            "Which functions allocate the most memory?",
            "Optimize query planning performance",
            "Find functions with highest cyclomatic complexity",
            "What are the most called functions (highest in-degree)?",
            "Find performance hotspots using PageRank analysis",
            "Find all palloc calls in the executor module",
            "Find potential memory leak patterns",
            "Analyze memory context hierarchy",
            "Find all functions that use LWLock for synchronization",
            "Find race conditions in buffer management",
            "Analyze lock ordering issues"
        ],
        "priority": 8
    },

    "test_coverage": {
        "id": "scenario_07_test_coverage",
        "name": "Test Coverage Analysis",
        "keywords": [
            # Test generation keywords (Scenario 17) - MUST be first for multi-word priority
            "generate test", "unit test", "tests for", "test for",
            "create test", "write test", "generate unit test",
            "test generation", "integration test",
            # Original keywords
            "test", "coverage", "untested", "test case",
            "regression", "missing tests", "test gap"
        ],
        "examples": [
            "Which functions lack test coverage?",
            "Generate test cases for the parser",
            "Find untested error paths",
            "Generate unit tests for the palloc function",
            "Create tests for heap_insert"
        ],
        "priority": 9
    },

    "compliance": {
        "id": "scenario_08_compliance",
        "name": "Compliance Checking",
        "keywords": [
            # Multi-word discriminators (check FIRST for higher precision)
            "naming convention violation", "check naming convention", "naming convention check",
            "violating memory allocation", "memory allocation pattern", "allocation patterns",
            "proper error handling", "error handling violation", "without proper error",
            "proper locking pattern", "locking pattern violation", "improper locking",
            "proper transaction handling", "transaction handling pattern", "transaction pattern",
            "error reporting standard", "ereport violation", "error reporting violation",
            "proper use of assert", "assert macro usage", "check assert",
            "deprecated function usage", "check for deprecated", "deprecated usage",
            "coding style violation", "style violation check", "check coding style",
            "license header check", "missing license header", "check for license",
            # Core compliance keywords
            "compliance", "standard", "coding style", "convention",
            "naming", "license", "copyright", "policy violation",
            # Expanded compliance keywords for scenario 08
            "violating", "violation", "improper", "proper use",
            "error handling", "memory pattern", "locking pattern",
            "transaction pattern", "ereport", "errcode", "errmsg",
            "assert", "assertmacro", "assertarg"
        ],
        "examples": [
            "Check coding style violations",
            "Find functions violating naming conventions",
            "Verify license headers",
            "Find functions violating memory allocation patterns",
            "Find functions without proper error handling",
            "Check for proper use of Assert macros",
            "Find functions with improper locking patterns",
            "Check for proper transaction handling patterns",
            "Find functions violating error reporting standards"
        ],
        "priority": 9
    },

    "code_review": {
        "id": "scenario_09_code_review",
        "name": "Code Review Assistance",
        "keywords": [
            "review", "pull request", "pr", "diff",
            "change impact", "what changed", "breaking change"
        ],
        "examples": [
            "Review changes in this PR",
            "What's the impact of modifying ExecProcNode?",
            "Find breaking API changes"
        ],
        "priority": 9
    },

    "cross_repo_impact": {
        "id": "scenario_10_cross_repo",
        "name": "Cross-Repository Impact",
        "keywords": [
            "cross repo", "dependency", "upstream", "downstream",
            "affected projects", "breaking change", "api change"
        ],
        "examples": [
            "Which extensions depend on this function?",
            "Impact of changing the executor API",
            "Find all callers across repositories"
        ],
        "priority": 6
    },

    "architecture_violations": {
        "id": "scenario_11_architecture",
        "name": "Architecture Violation Detection",
        "keywords": [
            "architecture", "layering", "dependency violation",
            "circular dependency", "coupling", "shouldn't call",
            "wrong layer",
            # Module dependencies keywords (Scenario 11)
            "module dependency", "dependencies", "depend on",
            "import graph", "include", "header dependencies",
            "upstream", "downstream", "transitive dependency",
            "dependency tree", "dependency analysis"
        ],
        "examples": [
            "Find circular dependencies",
            "Check for layering violations",
            "Should the parser call executor functions?",
            "What modules does the executor depend on?",
            "Find all dependencies of the planner"
        ],
        "priority": 5
    },

    "tech_debt": {
        "id": "scenario_12_tech_debt",
        "name": "Technical Debt Quantification",
        "keywords": [
            "technical debt", "debt", "todo", "fixme", "hack",
            "workaround", "temporary", "legacy code"
        ],
        "examples": [
            "Quantify technical debt in the planner",
            "Find all TODO comments",
            "Which modules have the most legacy code?"
        ],
        "priority": 3
    },

    "mass_refactoring": {
        "id": "scenario_13_mass_refactoring",
        "name": "Mass Refactoring Automation",
        "keywords": [
            # Core rename/refactor keywords
            "rename", "replace all", "bulk change", "mass update",
            "global refactor", "rename function", "change signature",
            # CRITICAL: Pattern for "find all X for Y" questions
            "find all references", "find all usages", "find all calls",
            "all instances", "all occurrences",
            # Migration/modernization patterns
            "api migration", "api transition", "modernization",
            "standardization", "migrate api", "transition api",
            # Function/pattern finding for refactoring
            "for renaming", "for migration", "for refactoring",
            "for standardization", "for modernization", "for update",
            # Specific function patterns from questions
            "palloc", "heap_open", "elog", "ereport", "LWLock",
            "SearchSysCache", "Assert", "slot", "tuple", "FunctionCall"
        ],
        "examples": [
            "Rename all instances of ExecProcNode",
            "Change function signature across codebase",
            "Replace deprecated API calls",
            "Find all references to ExecProcNode for renaming",
            "Find all palloc usages for memory API migration",
            "Find all Assert macro usages for standardization"
        ],
        "priority": 8  # HIGHER than refactoring (6) to catch "find all X for refactoring"
    },

    "security_incident": {
        "id": "scenario_14_security_incident",
        "name": "Security Incident Response",
        "keywords": [
            # Multi-word discriminators for CVE/COPY patterns (check FIRST)
            "affected by cve", "cve in copy", "functions affected by cve",
            "copy command", "vulnerability in copy",
            # Emergency/incident response specific - HIGHEST PRIORITY
            "incident response", "emergency patch", "emergency response",
            "hotfix", "zero day", "0day", "active exploit",
            # CVE and vulnerability tracing (including without hyphen)
            "cve-", "CVE-", "cve", "cve tracking", "vulnerability trace",
            "trace vulnerability", "trace data flow", "taint trace",
            "user input to", "input to sql", "input to execution",
            # Attack tracing
            "attack path", "exploit chain", "breach", "compromise",
            "impact analysis", "affected paths",
            # CRITICAL: These patterns distinguish from security_audit
            # security_incident = TRACING paths, security_audit = FINDING vulns
            "trace from", "trace to", "paths from", "paths to",
            "find paths", "find all paths", "data flow from",
            "memory corruption paths", "privilege escalation paths",
            "authentication bypass", "bypass vulnerabilities",
            "denial of service", "dos", "extension loading",
            "replication security", "information disclosure",
            "error message", "disclosure through"
        ],
        "examples": [
            "Find all uses of vulnerable function strcpy",
            "Trace data flow from user input to SQL execution",
            "Emergency patch for CVE-2024-XXXX",
            "Find all paths from network input to file access",
            "Trace authentication bypass vulnerabilities"
        ],
        "priority": 11  # HIGHER than security_audit (10)
    },

    "debugging": {
        "id": "scenario_15_debugging",
        "name": "Debugging Support",
        "keywords": [
            # Multi-word discriminators (checked FIRST for higher precision)
            "trace parallel query", "parallel query execution", "parallel query flow",
            "debug checkpoint timing", "checkpoint timing issues", "checkpoint debug",
            "debug vacuum", "vacuum debugging", "vacuum breakpoint",
            "debug memory context", "memory context issues", "debug alloc",
            "signal handler debug", "debug signal handler", "debug interrupt",
            "index scan debug", "debug index scan", "step-through points for index",
            "wal exception", "exception in wal", "wal subsystem debug",
            "heap insert trace", "trace heap_insert", "call stack for heap",
            "lock debug", "debug lock", "gdb breakpoints for lock",
            "buffer debug", "debug buffer", "watch buffer management",
            "transaction debug", "debug transaction", "debug points for transaction",
            "query execution debug", "debug query execution", "breakpoints for query",
            "logging points in parser", "parser logging", "error paths in planner",
            "trace execution through", "trace through executor",
            # Core debugging keywords
            "debug", "debugger", "breakpoint", "step through",
            "gdb", "lldb", "backtrace", "core dump",
            "stack trace", "step into", "step over", "watch",
            "debug symbols", "debug point", "debug session",
            # Execution tracing for debugging
            "set breakpoint", "where to set breakpoint", "good breakpoints",
            "debug execution", "debug query",
            "debug points for", "trace through", "trace the",
            # Logging and error tracing
            "logging point", "error path",
            "exception handling", "error handler", "elog", "ereport",
            # Specific debug targets
            "debug memory", "debug wal"
        ],
        "examples": [
            "How to trace execution through the executor?",
            "What are good breakpoints for debugging query execution?",
            "Where should I set debug points for transaction handling?",
            "Trace the call stack for heap_insert",
            "Find logging points in the parser"
        ],
        "priority": 9
    },

    "entry_points": {
        "id": "scenario_16_entry_points",
        "name": "Entry Points and Attack Surface",
        "keywords": [
            # Multi-word discriminators (check FIRST for higher precision)
            "authentication entry", "entry points for", "handle authentication entry",
            "replication entry", "file access entry", "command execution entry",
            "COPY command entry", "connection handler entry",
            # Original keywords
            "entry point", "attack surface", "network-facing",
            "external entry", "client input", "PG_FUNCTION_INFO",
            "exposed", "exposure", "trust boundary",
            "external interface", "public API", "exposed function",
            "network handler", "protocol handler", "connection handler",
            "listen", "accept", "socket", "bind"
        ],
        "examples": [
            "List network-facing functions that handle client input",
            "Find all external entry points",
            "What functions are exposed to network clients?",
            "Find all PG_FUNCTION_INFO declarations",
            "Identify attack surface in the backend"
        ],
        "priority": 10
    }
}


def get_all_intents():
    """Get list of all intent IDs"""
    return list(INTENT_TAXONOMY.keys())


def get_intent_by_id(intent_id: str):
    """Get intent details by ID"""
    return INTENT_TAXONOMY.get(intent_id)


def get_high_priority_intents():
    """Get intents with priority >= 8 (security, performance, code review)"""
    return {k: v for k, v in INTENT_TAXONOMY.items() if v['priority'] >= 8}
