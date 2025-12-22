"""PostgreSQL Function Lists.

Contains lists of PostgreSQL functions organized by category for analysis.
"""
from typing import Dict, List


def get_memory_functions() -> Dict[str, List[str]]:
    """Get memory management function mappings."""
    return {
        "allocate": [
            "palloc", "palloc0", "palloc_extended", "repalloc", "MemoryContextAlloc"
        ],
        "free": ["pfree", "MemoryContextDelete", "MemoryContextReset"],
        "copy": ["pstrdup", "pnstrdup", "memcpy", "memmove"],
    }


def get_lock_functions() -> List[str]:
    """Get locking-related functions for concurrency analysis."""
    return [
        # LWLock operations (lightweight locks)
        "LWLockAcquire", "LWLockRelease", "LWLockConditionalAcquire",
        "LWLockAcquireOrWait", "LWLockHeldByMe", "LWLockHeldByMeInMode",
        "LWLockWaitForVar", "LWLockUpdateVar", "LWLockRegisterTranche",

        # SpinLock operations
        "SpinLockAcquire", "SpinLockRelease", "SpinLockInit", "SpinLockFree",

        # Regular lock operations (heavyweight locks)
        "LockAcquire", "LockRelease", "LockAcquireExtended",
        "ConditionalLockAcquire", "LockHasWaiters", "LockCheckConflicts",
        "UnlockTuple", "LockTuple", "LockPage", "UnlockPage",

        # Advisory locks
        "pg_advisory_lock", "pg_advisory_lock_shared", "pg_advisory_unlock",
        "pg_advisory_unlock_shared", "pg_advisory_unlock_all",
        "pg_try_advisory_lock", "pg_try_advisory_lock_shared",
        "pg_try_advisory_xact_lock", "pg_try_advisory_xact_lock_shared",

        # Semaphore operations
        "PGSemaphoreCreate", "PGSemaphoreLock", "PGSemaphoreUnlock",
        "PGSemaphoreReset", "PGSemaphoreTryLock",

        # Mutex/condition variable operations (POSIX)
        "pthread_mutex_lock", "pthread_mutex_unlock", "pthread_mutex_init",
        "pthread_mutex_destroy", "pthread_mutex_trylock",
        "pthread_cond_wait", "pthread_cond_signal", "pthread_cond_broadcast",
        "pthread_cond_timedwait", "pthread_rwlock_rdlock", "pthread_rwlock_wrlock",
        "pthread_rwlock_unlock",

        # PG exception handling (often used with locks)
        "PG_TRY", "PG_CATCH", "PG_FINALLY", "PG_END_TRY", "PG_RE_THROW",

        # Condition variable operations (PostgreSQL)
        "ConditionVariableInit", "ConditionVariableSleep",
        "ConditionVariableSignal", "ConditionVariableBroadcast",
        "ConditionVariableCancelSleep", "ConditionVariablePrepareToSleep",

        # Relation locks
        "relation_open", "relation_close", "LockRelation", "UnlockRelation",
        "LockRelationOid", "UnlockRelationOid", "LockRelationForExtension",
        "UnlockRelationForExtension", "LockRelationId", "UnlockRelationId",
        "ConditionalLockRelation", "ConditionalLockRelationOid",

        # Buffer locks
        "LockBuffer", "LockBufferForCleanup", "ConditionalLockBuffer",
        "UnlockBuffers", "LockBufHdr", "UnlockBufHdr",

        # Table/partition locks
        "AcquireExecutorLocks", "AcquireRewriteLocks",
        "CheckRelationLockedByMe", "RelationLockIndexes",

        # Transaction locks
        "XactLockTableWait", "XactLockTableDelete", "XactLockTableInsert",
        "ConditionalXactLockTableWait",

        # Speculative insertion locks
        "SpeculativeInsertionLockAcquire", "SpeculativeInsertionLockRelease",
        "SpeculativeInsertionWait",

        # Predicate locks (serializable isolation)
        "PredicateLockPage", "PredicateLockTuple", "PredicateLockRelation",
        "CheckForSerializableConflictIn", "CheckForSerializableConflictOut",

        # Deadlock detection
        "DeadLockCheck", "InitDeadLockChecking",

        # Atomic operations
        "pg_atomic_init_flag", "pg_atomic_test_set_flag", "pg_atomic_clear_flag",
        "pg_atomic_init_u32", "pg_atomic_read_u32", "pg_atomic_write_u32",
        "pg_atomic_exchange_u32", "pg_atomic_compare_exchange_u32",
        "pg_atomic_fetch_add_u32", "pg_atomic_fetch_sub_u32",
        "pg_atomic_fetch_and_u32", "pg_atomic_fetch_or_u32",
        "pg_atomic_add_fetch_u32", "pg_atomic_sub_fetch_u32",
        "pg_atomic_init_u64", "pg_atomic_read_u64", "pg_atomic_write_u64",
    ]


def get_debug_functions() -> Dict[str, List[str]]:
    """Get debugging-related functions organized by category."""
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


def get_dml_functions() -> Dict[str, List[str]]:
    """Get DML (Data Manipulation Language) operation functions."""
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


def get_subsystem_functions() -> Dict[str, List[str]]:
    """Get functions organized by PostgreSQL subsystem."""
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


def get_breakpoint_functions() -> Dict[str, List[str]]:
    """Get debugging breakpoint functions organized by debugging context."""
    return {
        "transaction": [
            "StartTransaction", "CommitTransaction", "AbortTransaction",
            "BeginTransactionBlock", "EndTransactionBlock",
            "UserAbortTransactionBlock", "standard_ExecutorRun",
        ],
        "heap": [
            "heap_insert", "heap_update", "heap_delete",
            "heap_vacuum_rel", "heap_fetch", "heap_getnext",
            "simple_heap_insert", "simple_heap_update", "simple_heap_delete",
        ],
        "buffer": [
            "ReadBuffer", "ReleaseBuffer", "BufferAlloc",
            "MarkBufferDirty", "FlushBuffer", "ReadBufferExtended",
            "LockBuffer", "UnlockBuffers",
        ],
        "lock": [
            "LWLockAcquire", "LWLockRelease", "LockAcquire", "LockRelease",
            "SpinLockAcquire", "SpinLockRelease", "deadlock_check",
        ],
        "wal": [
            "XLogInsert", "XLogFlush", "XLogWrite", "CreateCheckPoint",
            "XLogBeginInsert", "XLogRegisterData", "XLogRecPtr",
            "StartupXLOG", "ShutdownXLOG",
        ],
        "index": [
            "ExecIndexScan", "IndexNext", "index_getnext",
            "ExecIndexOnlyScan", "index_getnext_slot", "index_beginscan",
            "index_insert", "index_delete",
        ],
        "memory": [
            "MemoryContextCreate", "MemoryContextDelete", "AllocSetAlloc",
            "MemoryContextReset", "MemoryContextAlloc", "palloc", "pfree",
            "repalloc", "MemoryContextSwitchTo",
        ],
        "signal": [
            "die", "quickdie", "ProcessInterrupts",
            "StatementCancelHandler", "FloatExceptionHandler",
            "SigHupHandler", "handle_sig_alarm",
        ],
        "parallel": [
            "ParallelQueryMain", "ExecParallelInitializeDSM", "LaunchParallelWorkers",
            "ParallelWorkerMain", "ExecInitParallelPlan", "ExecParallelReportInstrumentation",
        ],
        "vacuum": [
            "lazy_vacuum_rel", "vacuum_rel", "heap_vacuum_rel",
            "lazy_vacuum_heap", "lazy_scan_heap", "vacuum",
        ],
        "checkpoint": [
            "CreateCheckPoint", "CheckpointMain", "RequestCheckpoint",
            "XLogFlush", "smgrsync", "FlushBuffer",
        ],
        "executor": [
            "ExecutorRun", "ExecProcNode", "ExecInitNode",
            "ExecEndNode", "ExecScan", "ExecProject",
        ],
        "query": [
            "exec_simple_query", "pg_parse_query", "pg_plan_query",
            "standard_planner", "raw_parser",
        ],
    }


def get_concurrency_functions() -> Dict[str, List[str]]:
    """Get concurrency-related functions organized by category."""
    return {
        "lwlock": [
            "LWLockAcquire", "LWLockRelease", "LWLockConditionalAcquire",
            "LWLockAcquireOrWait", "LWLockHeldByMe", "LWLockHeldByMeInMode",
            "LWLockWaitForVar", "LWLockUpdateVar", "LWLockRegisterTranche",
        ],
        "spinlock": [
            "SpinLockAcquire", "SpinLockRelease", "SpinLockInit", "SpinLockFree",
            "S_LOCK", "S_UNLOCK", "S_INIT_LOCK",
        ],
        "heavyweight_lock": [
            "LockAcquire", "LockRelease", "LockAcquireExtended",
            "ConditionalLockAcquire", "LockHasWaiters", "LockCheckConflicts",
        ],
        "atomic": [
            "pg_atomic_read_u32", "pg_atomic_write_u32", "pg_atomic_exchange_u32",
            "pg_atomic_compare_exchange_u32", "pg_atomic_fetch_add_u32",
            "pg_atomic_fetch_sub_u32", "pg_atomic_fetch_and_u32",
            "pg_atomic_fetch_or_u32", "pg_atomic_add_fetch_u32",
            "pg_atomic_read_u64", "pg_atomic_write_u64",
        ],
        "latch": [
            "SetLatch", "WaitLatch", "ResetLatch", "OwnLatch",
            "WaitLatchOrSocket", "InitLatch", "DisownLatch",
        ],
        "barrier": [
            "pg_memory_barrier", "pg_read_barrier", "pg_write_barrier",
            "pg_spin_delay", "pg_compiler_barrier",
        ],
        "condition_variable": [
            "ConditionVariableInit", "ConditionVariableSleep",
            "ConditionVariableSignal", "ConditionVariableBroadcast",
            "ConditionVariableCancelSleep", "ConditionVariablePrepareToSleep",
        ],
        "semaphore": [
            "PGSemaphoreCreate", "PGSemaphoreLock", "PGSemaphoreUnlock",
            "PGSemaphoreReset", "PGSemaphoreTryLock",
        ],
    }


def get_assertion_functions() -> List[str]:
    """Get PostgreSQL assertion macros."""
    return [
        "Assert", "AssertMacro", "AssertArg", "AssertState",
        "Insist", "StaticAssertStmt", "StaticAssertExpr",
        "AssertVariableIsOfType", "AssertVariableIsOfTypeMacro",
        "Trap", "TrapMacro", "ExceptionalCondition",
    ]


def get_trace_functions() -> List[str]:
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


def get_error_levels() -> List[str]:
    """Get PostgreSQL error/log levels."""
    return [
        "DEBUG5", "DEBUG4", "DEBUG3", "DEBUG2", "DEBUG1",
        "LOG", "LOG_SERVER_ONLY",
        "INFO", "NOTICE", "WARNING",
        "ERROR", "FATAL", "PANIC",
    ]


def get_noise_functions() -> List[str]:
    """Get list of noise/utility functions to filter out from results."""
    return [
        # Generic utility functions
        "memset", "memcpy", "memmove", "strlen", "strcmp", "strncmp",
        "strcpy", "strncpy", "strcat", "strncat", "sprintf", "snprintf",

        # PostgreSQL common utilities
        "pfree", "palloc", "palloc0", "repalloc",
        "NameStr", "TextDatumGetCString", "CStringGetDatum",

        # Assert/debug (usually not interesting for analysis)
        "Assert", "AssertMacro", "elog",

        # Common macros
        "PointerIsValid", "OidIsValid", "RelationIsValid",
    ]
