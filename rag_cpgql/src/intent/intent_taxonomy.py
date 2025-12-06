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
        "id": "scenario_1",
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
            # Debugging & tracing keywords (Scenario 14)
            "debug", "debugger", "breakpoint", "step through",
            "trace execution", "execution trace", "call stack",
            "gdb", "lldb", "backtrace", "core dump",
            "error path", "exception handling", "log", "logging",
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
        "id": "scenario_2",
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
            # Entry points and attack surface keywords (Scenario 08)
            "entry point", "attack surface", "network-facing", "external entry",
            "client input", "PG_FUNCTION_INFO", "exposed", "exposure",
            "trust boundary", "lateral movement", "exfiltration",
            "privilege escalation", "bypass", "authentication entry"
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
        "id": "scenario_3",
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
        "id": "scenario_4",
        "name": "Feature Development",
        "keywords": [
            "implement", "add feature", "create", "build",
            "develop", "where to add", "how to extend",
            "integration point", "hook", "where should", "add"
        ],
        "examples": [
            "Where should I add a new join algorithm?",
            "How to implement custom index type?",
            "Find extension points for query optimizer"
        ],
        "priority": 7
    },

    "refactoring": {
        "id": "scenario_5",
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
        "id": "scenario_6",
        "name": "Performance Optimization",
        "keywords": [
            "performance", "optimize", "slow", "bottleneck",
            "hotspot", "profiling", "cache", "memory leak",
            "allocate", "cpu intensive", "allocation", "memory",
            # Complexity analysis keywords (Scenario 06)
            "cyclomatic", "complexity", "in-degree", "out-degree",
            "pagerank", "betweenness", "centrality", "closeness",
            "nesting depth", "cognitive complexity", "most called",
            "high complexity", "performance analysis", "scaling",
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
        "id": "scenario_7",
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
        "id": "scenario_8",
        "name": "Compliance Checking",
        "keywords": [
            "compliance", "standard", "coding style", "convention",
            "naming", "license", "copyright", "policy violation"
        ],
        "examples": [
            "Check coding style violations",
            "Find functions violating naming conventions",
            "Verify license headers"
        ],
        "priority": 2
    },

    "code_review": {
        "id": "scenario_9",
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
        "id": "scenario_10",
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
        "id": "scenario_11",
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
        "id": "scenario_12",
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
        "id": "scenario_13",
        "name": "Mass Refactoring Automation",
        "keywords": [
            "rename", "replace all", "bulk change", "mass update",
            "global refactor", "rename function", "change signature"
        ],
        "examples": [
            "Rename all instances of ExecProcNode",
            "Change function signature across codebase",
            "Replace deprecated API calls"
        ],
        "priority": 7
    },

    "security_incident": {
        "id": "scenario_14",
        "name": "Security Incident Response",
        "keywords": [
            "incident", "exploit", "attack", "breach",
            "cve", "patch", "hotfix", "emergency",
            "zero day"
        ],
        "examples": [
            "Find all uses of vulnerable function strcpy",
            "Trace data flow from user input to SQL execution",
            "Emergency patch for CVE-2024-XXXX"
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
