"""
PostgreSQL Domain Plugin Implementation.

Provides PostgreSQL-specific configurations for the RAG-CPGQL Copilot.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..base import DomainPlugin, SubsystemInfo, SecurityPattern, IntentPattern

logger = logging.getLogger(__name__)


class PostgreSQLDomainPlugin(DomainPlugin):
    """
    Domain plugin for PostgreSQL source code analysis.

    Provides:
    - PostgreSQL subsystem definitions (executor, parser, planner, etc.)
    - Security vulnerability patterns specific to PostgreSQL
    - Intent classification patterns with PostgreSQL-specific keywords
    - LLM prompts tailored for PostgreSQL expertise
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the PostgreSQL domain plugin.

        Args:
            config_dir: Optional path to configuration files.
                       Defaults to the directory containing this plugin.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        super().__init__(config_dir)

    @property
    def name(self) -> str:
        return "postgresql"

    @property
    def display_name(self) -> str:
        return "PostgreSQL"

    @property
    def description(self) -> str:
        return (
            "PostgreSQL is an advanced open-source relational database management system. "
            "This plugin provides analysis capabilities for PostgreSQL's C codebase, "
            "including the executor, parser, optimizer, storage, and replication subsystems."
        )

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load PostgreSQL subsystem definitions from YAML."""
        config = self._load_yaml_config("subsystems.yaml")

        subsystems = {}
        for name, data in config.get("subsystems", {}).items():
            subsystems[name] = SubsystemInfo(
                name=name,
                description=data.get("description", ""),
                key_functions=data.get("key_functions", []),
                patterns=data.get("patterns", []),
                related_files=data.get("related_files", []),
            )

        # If no config file, use fallback defaults
        if not subsystems:
            subsystems = self._get_default_subsystems()

        return subsystems

    def _get_default_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Fallback subsystem definitions if YAML not available."""
        return {
            "executor": SubsystemInfo(
                name="executor",
                description="Query execution engine - executes query plans",
                key_functions=["ExecProcNode", "ExecInitNode", "ExecEndNode"],
                patterns=["backend/executor", "execMain", "execProc"],
            ),
            "parser": SubsystemInfo(
                name="parser",
                description="SQL parser and analyzer - converts SQL to parse tree",
                key_functions=["raw_parser", "pg_parse_query", "transformStmt"],
                patterns=["backend/parser", "gram.y", "scan.l"],
            ),
            "optimizer": SubsystemInfo(
                name="optimizer",
                description="Query optimizer/planner - generates query plans",
                key_functions=["standard_planner", "subquery_planner", "query_planner"],
                patterns=["backend/optimizer", "planner", "path", "cost"],
            ),
            "storage": SubsystemInfo(
                name="storage",
                description="Storage manager - handles file and buffer I/O",
                key_functions=["BufferAlloc", "ReadBuffer", "WriteBuffer"],
                patterns=["backend/storage", "smgr", "bufmgr"],
            ),
            "access": SubsystemInfo(
                name="access",
                description="Access methods - heap tables and index implementations",
                key_functions=["heap_insert", "heap_fetch", "index_insert"],
                patterns=["backend/access", "heap", "index", "nbtree"],
            ),
            "catalog": SubsystemInfo(
                name="catalog",
                description="System catalogs - metadata about database objects",
                key_functions=["SearchSysCache", "heap_open", "relation_open"],
                patterns=["backend/catalog", "pg_class", "syscache"],
            ),
            "commands": SubsystemInfo(
                name="commands",
                description="SQL commands - DDL and utility command implementations",
                key_functions=["ProcessUtility", "DefineRelation", "AlterTable"],
                patterns=["backend/commands", "tablecmds", "vacuum"],
            ),
            "utils": SubsystemInfo(
                name="utils",
                description="Utilities - memory management, error handling",
                key_functions=["palloc", "pfree", "elog", "ereport"],
                patterns=["backend/utils", "memutils", "palloc"],
            ),
            "replication": SubsystemInfo(
                name="replication",
                description="Replication - WAL shipping and logical replication",
                key_functions=["WalSndLoop", "WalReceiverMain"],
                patterns=["backend/replication", "walsender", "walreceiver"],
            ),
            "transactions": SubsystemInfo(
                name="transactions",
                description="Transaction management - ACID properties and WAL",
                key_functions=["StartTransaction", "CommitTransaction", "XLogInsert"],
                patterns=["backend/access/transam", "xact", "xlog"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load PostgreSQL-specific prompt templates."""
        config = self._load_yaml_config("prompts.yaml")

        if config:
            return config.get("prompts", {})

        # Default prompts
        return {
            "security_audit": {
                "system": (
                    "You are a PostgreSQL security expert specializing in "
                    "identifying vulnerabilities in database system source code. "
                    "Focus on SQL injection, buffer overflows, privilege escalation, "
                    "and memory safety issues specific to PostgreSQL's architecture."
                ),
                "user_template": (
                    "Analyze the following PostgreSQL code for security vulnerabilities:\n\n"
                    "{code}\n\n"
                    "Consider PostgreSQL-specific attack vectors including:\n"
                    "- SPI interface abuse\n"
                    "- Extension loading attacks\n"
                    "- COPY command injection\n"
                    "- Privilege escalation via superuser functions"
                ),
            },
            "performance": {
                "system": (
                    "You are a PostgreSQL performance expert with deep knowledge of "
                    "query execution, memory management, and I/O optimization. "
                    "Focus on identifying bottlenecks in the executor, planner, "
                    "and storage subsystems."
                ),
                "user_template": (
                    "Analyze the following PostgreSQL code for performance issues:\n\n"
                    "{code}\n\n"
                    "Consider:\n"
                    "- Memory allocation patterns (palloc/pfree)\n"
                    "- Lock contention\n"
                    "- Buffer management\n"
                    "- Query plan efficiency"
                ),
            },
            "onboarding": {
                "system": (
                    "You are a PostgreSQL internals expert helping developers understand "
                    "the codebase architecture. Explain concepts clearly with references "
                    "to specific subsystems and their interactions."
                ),
                "user_template": (
                    "Explain the following aspect of PostgreSQL:\n\n"
                    "{query}\n\n"
                    "Provide context about which subsystems are involved and "
                    "how they interact. Reference specific functions where helpful."
                ),
            },
            "documentation": {
                "system": (
                    "You are a PostgreSQL documentation expert. Generate clear, "
                    "comprehensive documentation for PostgreSQL internal functions "
                    "and modules following PostgreSQL's documentation style."
                ),
                "user_template": (
                    "Generate documentation for:\n\n"
                    "{code}\n\n"
                    "Include:\n"
                    "- Function purpose and behavior\n"
                    "- Parameters and return values\n"
                    "- Error conditions\n"
                    "- Related functions"
                ),
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load PostgreSQL-specific intent classification patterns."""
        config = self._load_yaml_config("intent_patterns.yaml")

        patterns = {}
        for intent_id, data in config.get("intents", {}).items():
            patterns[intent_id] = IntentPattern(
                intent_id=intent_id,
                keywords=data.get("keywords", []),
                patterns=data.get("patterns", []),
                examples=data.get("examples", []),
                priority=data.get("priority", 0),
            )

        return patterns

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load PostgreSQL-specific security vulnerability patterns."""
        config = self._load_yaml_config("security_patterns.yaml")

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

    def get_expert_role(self) -> str:
        """Get the PostgreSQL expert role for LLM prompts."""
        return "PostgreSQL database internals expert"

    def get_domain_context(self) -> str:
        """Get PostgreSQL-specific context for LLM prompts."""
        return "analyzing PostgreSQL database system source code (C language)"

    def get_entry_point_patterns(self) -> List[str]:
        """Get patterns for identifying entry points in PostgreSQL."""
        return [
            "PG_FUNCTION_INFO_V1",
            "PostgresMain",
            "exec_simple_query",
            "ProcessUtility",
            "pq_getmsg",
            "recv_password_packet",
            "ClientAuthentication",
        ]

    def get_sensitive_functions(self) -> List[str]:
        """Get functions that handle sensitive operations."""
        return [
            "pg_read_file",
            "pg_ls_dir",
            "pg_write_file",
            "SPI_execute",
            "SPI_exec",
            "system",
            "popen",
            "exec_command",
        ]

    def get_memory_functions(self) -> Dict[str, str]:
        """Get memory management function mappings."""
        return {
            "allocate": ["palloc", "palloc0", "palloc_extended", "repalloc", "MemoryContextAlloc"],
            "free": ["pfree", "MemoryContextDelete", "MemoryContextReset"],
            "copy": ["pstrdup", "pnstrdup", "memcpy", "memmove"],
        }

    def get_lock_functions(self) -> List[str]:
        """Get locking-related functions for concurrency analysis."""
        return [
            # LWLock operations (lightweight locks)
            "LWLockAcquire",
            "LWLockRelease",
            "LWLockConditionalAcquire",
            "LWLockAcquireOrWait",
            "LWLockHeldByMe",
            "LWLockHeldByMeInMode",
            "LWLockWaitForVar",
            "LWLockUpdateVar",
            "LWLockRegisterTranche",

            # SpinLock operations
            "SpinLockAcquire",
            "SpinLockRelease",
            "SpinLockInit",
            "SpinLockFree",

            # Regular lock operations (heavyweight locks)
            "LockAcquire",
            "LockRelease",
            "LockAcquireExtended",
            "ConditionalLockAcquire",
            "LockHasWaiters",
            "LockCheckConflicts",
            "UnlockTuple",
            "LockTuple",
            "LockPage",
            "UnlockPage",

            # Advisory locks
            "pg_advisory_lock",
            "pg_advisory_lock_shared",
            "pg_advisory_unlock",
            "pg_advisory_unlock_shared",
            "pg_advisory_unlock_all",
            "pg_try_advisory_lock",
            "pg_try_advisory_lock_shared",
            "pg_try_advisory_xact_lock",
            "pg_try_advisory_xact_lock_shared",

            # Semaphore operations
            "PGSemaphoreCreate",
            "PGSemaphoreLock",
            "PGSemaphoreUnlock",
            "PGSemaphoreReset",
            "PGSemaphoreTryLock",

            # Mutex/condition variable operations (POSIX)
            "pthread_mutex_lock",
            "pthread_mutex_unlock",
            "pthread_mutex_init",
            "pthread_mutex_destroy",
            "pthread_mutex_trylock",
            "pthread_cond_wait",
            "pthread_cond_signal",
            "pthread_cond_broadcast",
            "pthread_cond_timedwait",
            "pthread_rwlock_rdlock",
            "pthread_rwlock_wrlock",
            "pthread_rwlock_unlock",

            # PG exception handling (often used with locks)
            "PG_TRY",
            "PG_CATCH",
            "PG_FINALLY",
            "PG_END_TRY",
            "PG_RE_THROW",

            # Condition variable operations (PostgreSQL)
            "ConditionVariableInit",
            "ConditionVariableSleep",
            "ConditionVariableSignal",
            "ConditionVariableBroadcast",
            "ConditionVariableCancelSleep",
            "ConditionVariablePrepareToSleep",

            # Relation locks
            "relation_open",
            "relation_close",
            "LockRelation",
            "UnlockRelation",
            "LockRelationOid",
            "UnlockRelationOid",
            "LockRelationForExtension",
            "UnlockRelationForExtension",
            "LockRelationId",
            "UnlockRelationId",
            "ConditionalLockRelation",
            "ConditionalLockRelationOid",

            # Buffer locks
            "LockBuffer",
            "LockBufferForCleanup",
            "ConditionalLockBuffer",
            "UnlockBuffers",
            "LockBufHdr",
            "UnlockBufHdr",

            # Table/partition locks
            "AcquireExecutorLocks",
            "AcquireRewriteLocks",
            "CheckRelationLockedByMe",
            "RelationLockIndexes",

            # Transaction locks
            "XactLockTableWait",
            "XactLockTableDelete",
            "XactLockTableInsert",
            "ConditionalXactLockTableWait",

            # Speculative insertion locks
            "SpeculativeInsertionLockAcquire",
            "SpeculativeInsertionLockRelease",
            "SpeculativeInsertionWait",

            # Predicate locks (serializable isolation)
            "PredicateLockPage",
            "PredicateLockTuple",
            "PredicateLockRelation",
            "CheckForSerializableConflictIn",
            "CheckForSerializableConflictOut",

            # Deadlock detection
            "DeadLockCheck",
            "InitDeadLockChecking",

            # Atomic operations
            "pg_atomic_init_flag",
            "pg_atomic_test_set_flag",
            "pg_atomic_clear_flag",
            "pg_atomic_init_u32",
            "pg_atomic_read_u32",
            "pg_atomic_write_u32",
            "pg_atomic_exchange_u32",
            "pg_atomic_compare_exchange_u32",
            "pg_atomic_fetch_add_u32",
            "pg_atomic_fetch_sub_u32",
            "pg_atomic_fetch_and_u32",
            "pg_atomic_fetch_or_u32",
            "pg_atomic_add_fetch_u32",
            "pg_atomic_sub_fetch_u32",
            "pg_atomic_init_u64",
            "pg_atomic_read_u64",
            "pg_atomic_write_u64",
        ]

    def get_error_handling_patterns(self) -> Dict[str, Any]:
        """Get error handling patterns for PostgreSQL."""
        return {
            "error_macros": ["elog", "ereport", "PG_TRY", "PG_CATCH", "PG_END_TRY"],
            "error_levels": ["DEBUG", "LOG", "INFO", "NOTICE", "WARNING", "ERROR", "FATAL", "PANIC"],
            "cleanup_patterns": ["PG_FINALLY", "PG_END_TRY"],
        }

    def get_error_levels(self) -> List[str]:
        """Get PostgreSQL error/log levels."""
        return [
            "DEBUG5", "DEBUG4", "DEBUG3", "DEBUG2", "DEBUG1",
            "LOG", "LOG_SERVER_ONLY",
            "INFO", "NOTICE", "WARNING",
            "ERROR", "FATAL", "PANIC",
        ]

    def get_debug_functions(self) -> Dict[str, List[str]]:
        """
        Get debugging-related functions organized by category.

        Returns:
            Dictionary mapping debug category to function lists
        """
        return {
            "logging": [
                "elog", "ereport", "errcode", "errmsg", "errdetail",
                "errhint", "errcontext", "errposition", "errtable",
                "errtablecol", "errtableconstraint", "errdomainconstraint",
                "internalerrquery", "internalerrposition", "geterrcode",
            ],
            "assertion": [
                "Assert", "AssertMacro", "AssertArg", "AssertState",
                "Insist", "StaticAssertStmt", "StaticAssertExpr",
                "AssertVariableIsOfType", "AssertVariableIsOfTypeMacro",
            ],
            "trace": [
                "trace_recovery", "trace_sort", "trace_notify",
                "TraceFlags", "TRACE_POSTGRESQL_BUFFER_FLUSH_DONE",
                "TRACE_POSTGRESQL_BUFFER_FLUSH_START",
                "TRACE_POSTGRESQL_BUFFER_READ_DONE",
                "TRACE_POSTGRESQL_BUFFER_READ_START",
                "pg_trace", "MemoryContextStats", "MemoryContextStatsDetail",
            ],
            "explain": [
                "ExplainQuery", "ExplainState", "ExplainPrintPlan",
                "ExplainProperty", "ExplainPropertyText", "ExplainPropertyInteger",
                "ExplainPropertyFloat", "ExplainPropertyBool",
                "ExplainOpenGroup", "ExplainCloseGroup", "ExplainBeginOutput",
                "ExplainEndOutput", "ExplainOnePlan", "ExplainQueryText",
            ],
            "debug_output": [
                "DEBUG1", "DEBUG2", "DEBUG3", "DEBUG4", "DEBUG5",
                "LOG", "WARNING", "NOTICE", "INFO",
            ],
            "stack_trace": [
                "errbacktrace", "pg_backtrace", "stack_base_ptr",
                "set_stack_base", "check_stack_depth", "stack_is_too_deep",
            ],
            "breakpoint": [
                "set_debug_options", "pg_wait_until_terminated",
            ],
            "timing": [
                "INSTR_TIME_SET_CURRENT", "INSTR_TIME_ADD", "INSTR_TIME_SUBTRACT",
                "INSTR_TIME_GET_MILLISEC", "INSTR_TIME_GET_MICROSEC",
                "InstrStartNode", "InstrStopNode", "InstrEndLoop",
            ],
        }

    def get_assertion_functions(self) -> List[str]:
        """Get PostgreSQL assertion macros."""
        return [
            "Assert", "AssertMacro", "AssertArg", "AssertState",
            "Insist", "StaticAssertStmt", "StaticAssertExpr",
            "AssertVariableIsOfType", "AssertVariableIsOfTypeMacro",
            "Trap", "TrapMacro", "ExceptionalCondition",
        ]

    def get_trace_functions(self) -> List[str]:
        """Get PostgreSQL trace/instrumentation functions."""
        return [
            "trace_recovery", "trace_sort", "trace_notify",
            "TraceFlags", "pg_trace",
            "MemoryContextStats", "MemoryContextStatsDetail",
            "TRACE_POSTGRESQL_BUFFER_FLUSH_DONE",
            "TRACE_POSTGRESQL_BUFFER_FLUSH_START",
            "TRACE_POSTGRESQL_BUFFER_READ_DONE",
            "TRACE_POSTGRESQL_BUFFER_READ_START",
            "TRACE_POSTGRESQL_TRANSACTION_COMMIT",
            "TRACE_POSTGRESQL_TRANSACTION_ABORT",
            "TRACE_POSTGRESQL_LOCK_WAIT_START",
            "TRACE_POSTGRESQL_LOCK_WAIT_DONE",
        ]

    def get_dml_functions(self) -> Dict[str, List[str]]:
        """
        Get DML (Data Manipulation Language) operation functions.

        Returns:
            Dictionary mapping DML operation type to function lists
        """
        return {
            "insert": [
                "ExecInsert", "ExecInsertIndexTuples", "heap_insert",
                "heap_multi_insert", "simple_heap_insert", "toast_insert_or_update",
                "CatalogTupleInsert", "CatalogTupleInsertWithInfo",
            ],
            "update": [
                "ExecUpdate", "heap_update", "simple_heap_update",
                "heap_inplace_update", "CatalogTupleUpdate",
                "CatalogTupleUpdateWithInfo", "ExecUpdatePrologue",
            ],
            "delete": [
                "ExecDelete", "heap_delete", "simple_heap_delete",
                "CatalogTupleDelete", "ExecDeletePrologue",
            ],
            "select": [
                "ExecSelect", "ExecScan", "SeqNext", "IndexNext",
                "BitmapHeapNext", "heap_fetch", "heap_getnext",
                "index_getnext_tid", "index_fetch_heap",
            ],
            "merge": [
                "ExecMerge", "ExecMergeMatched", "ExecMergeNotMatched",
            ],
        }

    def get_entry_points(self) -> List[str]:
        """
        Get comprehensive list of PostgreSQL entry points.

        Returns:
            List of function names that serve as entry points
        """
        return [
            # Main entry points
            "PostgresMain", "PostmasterMain", "BackendRun",
            "BackendStartup", "InitPostgres",

            # Network/connection entry points
            "SocketBackend", "ProcessStartupPacket", "ClientAuthentication",
            "ProcessClientRead", "ProcessClientWrite",
            "pq_getmsgstring", "pq_getmsgint", "pq_getmsgbyte",

            # Query processing entry points
            "exec_simple_query", "exec_parse_message", "exec_bind_message",
            "exec_execute_message", "exec_describe_message",

            # Extension entry points
            "PG_FUNCTION_INFO_V1", "pg_finfo_",
            "_PG_init", "_PG_fini", "_PG_output_plugin_init",

            # Utility entry points
            "ProcessUtility", "standard_ProcessUtility",

            # Background worker entry points
            "BackgroundWorkerMain", "RegisterBackgroundWorker",

            # Replication entry points
            "WalSndLoop", "WalReceiverMain", "StartReplication",

            # Vacuum/maintenance entry points
            "vacuum", "lazy_vacuum_rel", "analyze_rel",
        ]

    def get_subsystem_functions(self) -> Dict[str, List[str]]:
        """
        Get functions organized by PostgreSQL subsystem.

        Returns:
            Dictionary mapping subsystem name to key function lists
        """
        return {
            "executor": [
                "ExecutorStart", "ExecutorRun", "ExecutorFinish", "ExecutorEnd",
                "ExecProcNode", "ExecInitNode", "ExecEndNode", "ExecReScan",
                "ExecScan", "ExecProject", "ExecQual", "ExecEvalExpr",
            ],
            "parser": [
                "raw_parser", "pg_parse_query", "base_yyparse",
                "transformStmt", "parse_analyze", "parse_analyze_fixedparams",
                "transformSelectStmt", "transformInsertStmt", "transformUpdateStmt",
            ],
            "optimizer": [
                "standard_planner", "subquery_planner", "query_planner",
                "create_plan", "set_plan_references", "SS_process_ctes",
                "build_simple_rel", "make_one_rel", "set_cheapest",
            ],
            "buffer": [
                "ReadBuffer", "ReadBufferExtended", "ReleaseBuffer",
                "MarkBufferDirty", "BufferGetPage", "LockBuffer",
                "UnlockBuffers", "FlushBuffer", "DropRelFileNodesAllBuffers",
            ],
            "wal": [
                "XLogInsert", "XLogBeginInsert", "XLogRegisterData",
                "XLogFlush", "XLogWrite", "StartupXLOG", "ShutdownXLOG",
                "RecoveryInProgress", "XLogReadRecord", "XLogCheckpointNeeded",
            ],
            "catalog": [
                "SearchSysCache", "SearchSysCacheCopy", "GetSysCacheOid",
                "RelationIdGetRelation", "relation_open", "relation_close",
                "heap_open", "heap_close", "table_open", "table_close",
            ],
            "transaction": [
                "StartTransaction", "CommitTransaction", "AbortTransaction",
                "BeginTransactionBlock", "EndTransactionBlock", "UserAbortTransactionBlock",
                "StartTransactionCommand", "CommitTransactionCommand",
            ],
            "storage": [
                "smgropen", "smgrclose", "smgrcreate", "smgrdounlink",
                "smgrread", "smgrwrite", "smgrextend", "smgrtruncate",
                "mdopen", "mdread", "mdwrite", "mdextend",
            ],
        }

    def get_concurrency_keywords(self) -> List[str]:
        """Get keywords related to concurrency/locking analysis."""
        return [
            "lock", "latch", "mutex", "spinlock", "semaphore",
            "atomic", "barrier", "shared memory", "shmem",
            "lwlock", "heavyweight", "lightweight", "exclusive",
            "shared", "access exclusive", "row exclusive",
            "deadlock", "wait", "contention", "race",
        ]

    def get_memory_keywords(self) -> List[str]:
        """Get keywords related to memory management analysis."""
        return [
            "palloc", "pfree", "repalloc", "memory context",
            "memorycontext", "allocset", "generation", "slab",
            "bump", "aset", "memory leak", "out of memory",
            "oom", "allocation", "deallocation",
        ]

    def get_sanitization_confidence(self) -> Dict[str, float]:
        """
        Get PostgreSQL-specific sanitization confidence patterns.

        Returns confidence scores (0.0-1.0) for sanitization function patterns.
        Higher confidence = more reliable sanitization.

        Returns:
            Dictionary mapping pattern names to confidence scores
        """
        return {
            # PostgreSQL-specific escaping (high confidence)
            'pg_escape_string': 0.9,      # PostgreSQL string escaping
            'pg_escape_bytea': 0.9,       # PostgreSQL bytea escaping
            'pg_escape_identifier': 0.9,  # PostgreSQL identifier escaping
            'pg_escape_literal': 0.9,     # PostgreSQL literal escaping
            'PQescapeString': 0.9,        # libpq escaping
            'PQescapeLiteral': 0.9,       # libpq literal escaping
            'PQescapeIdentifier': 0.9,    # libpq identifier escaping
            'PQescapeBytea': 0.9,         # libpq bytea escaping

            # PostgreSQL prepared statements (highest confidence)
            'SPI_prepare': 1.0,           # Server-side prepared statements
            'SPI_execute_plan': 1.0,      # Execute prepared plan
            'PQprepare': 1.0,             # libpq prepared statements
            'PQexecPrepared': 1.0,        # libpq execute prepared

            # PostgreSQL parameterized queries
            'SPI_execute_with_args': 0.95,  # Parameterized SPI
            'PQexecParams': 0.95,           # libpq parameterized query

            # PostgreSQL input validation
            'check_stack_depth': 0.7,     # Stack overflow protection
            'CheckRequiredParameterValues': 0.8,  # Parameter validation
            'aclcheck_error': 0.8,        # ACL validation

            # PostgreSQL type checking
            'get_typlenbyvalalign': 0.6,  # Type validation
            'typenameType': 0.6,          # Type name validation
            'LookupTypeName': 0.6,        # Type lookup validation
        }

    def get_sanitization_patterns(self) -> List[Dict]:
        """
        Get PostgreSQL-specific sanitization patterns for dataflow analysis.

        Returns:
            List of sanitization pattern definitions
        """
        return [
            # Escaping functions
            {"name": "pg_escape_string", "function": "pg_escape_string", "confidence": 0.9,
             "description": "PostgreSQL string escaping"},
            {"name": "pg_escape_bytea", "function": "pg_escape_bytea", "confidence": 0.9,
             "description": "PostgreSQL bytea escaping"},
            {"name": "PQescapeString", "function": "PQescapeString", "confidence": 0.9,
             "description": "libpq string escaping"},
            {"name": "PQescapeLiteral", "function": "PQescapeLiteral", "confidence": 0.9,
             "description": "libpq literal escaping"},

            # Prepared statements
            {"name": "SPI_prepare", "function": "SPI_prepare", "confidence": 1.0,
             "description": "Server-side prepared statement"},
            {"name": "PQprepare", "function": "PQprepare", "confidence": 1.0,
             "description": "libpq prepared statement"},

            # Input validation patterns
            {"name": "acl_check", "pattern": r"aclcheck.*ERROR", "confidence": 0.8,
             "description": "Access control check"},
            {"name": "stack_check", "pattern": r"check_stack_depth", "confidence": 0.7,
             "description": "Stack depth protection"},
        ]


# Auto-register the plugin when module is imported
def _auto_register():
    """Auto-register PostgreSQL plugin with the registry."""
    try:
        from ..registry import DomainRegistry
        plugin = PostgreSQLDomainPlugin()
        DomainRegistry.register(plugin)
        logger.debug(f"Auto-registered {plugin.name} domain plugin")
    except ImportError:
        # Registry not available yet, skip auto-registration
        pass


_auto_register()
