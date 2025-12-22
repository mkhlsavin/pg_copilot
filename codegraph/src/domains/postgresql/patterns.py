"""PostgreSQL Pattern Definitions.

Contains entry points, security patterns, compliance patterns,
sanitization patterns, and other pattern-related data.
"""
from typing import Dict, List, Any


def get_entry_point_patterns() -> List[str]:
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


def get_entry_points() -> List[str]:
    """Get comprehensive list of PostgreSQL entry points."""
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


def get_sensitive_functions() -> List[str]:
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


def get_error_handling_patterns() -> Dict[str, Any]:
    """Get error handling patterns for PostgreSQL."""
    return {
        "error_macros": ["elog", "ereport", "PG_TRY", "PG_CATCH", "PG_END_TRY"],
        "error_levels": [
            "DEBUG", "LOG", "INFO", "NOTICE", "WARNING", "ERROR", "FATAL", "PANIC"
        ],
        "cleanup_patterns": ["PG_FINALLY", "PG_END_TRY"],
    }


def get_concurrency_keywords() -> List[str]:
    """Get keywords related to concurrency/locking analysis."""
    return [
        "lock", "latch", "mutex", "spinlock", "semaphore",
        "atomic", "barrier", "shared memory", "shmem",
        "lwlock", "heavyweight", "lightweight", "exclusive",
        "shared", "access exclusive", "row exclusive",
        "deadlock", "wait", "contention", "race",
    ]


def get_memory_keywords() -> List[str]:
    """Get keywords related to memory management analysis."""
    return [
        "palloc", "pfree", "repalloc", "memory context",
        "memorycontext", "allocset", "generation", "slab",
        "bump", "aset", "memory leak", "out of memory",
        "oom", "allocation", "deallocation",
    ]


def get_sanitization_confidence() -> Dict[str, float]:
    """Get PostgreSQL-specific sanitization confidence patterns."""
    return {
        # PostgreSQL-specific escaping (high confidence)
        'pg_escape_string': 0.9,
        'pg_escape_bytea': 0.9,
        'pg_escape_identifier': 0.9,
        'pg_escape_literal': 0.9,
        'PQescapeString': 0.9,
        'PQescapeLiteral': 0.9,
        'PQescapeIdentifier': 0.9,
        'PQescapeBytea': 0.9,

        # PostgreSQL prepared statements (highest confidence)
        'SPI_prepare': 1.0,
        'SPI_execute_plan': 1.0,
        'PQprepare': 1.0,
        'PQexecPrepared': 1.0,

        # PostgreSQL parameterized queries
        'SPI_execute_with_args': 0.95,
        'PQexecParams': 0.95,

        # PostgreSQL input validation
        'check_stack_depth': 0.7,
        'CheckRequiredParameterValues': 0.8,
        'aclcheck_error': 0.8,

        # PostgreSQL type checking
        'get_typlenbyvalalign': 0.6,
        'typenameType': 0.6,
        'LookupTypeName': 0.6,
    }


def get_sanitization_patterns() -> List[Dict]:
    """Get PostgreSQL-specific sanitization patterns for dataflow analysis."""
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


def get_taint_sources() -> List[str]:
    """Get taint source functions for dataflow analysis."""
    return [
        # Generic C input
        'readLine', 'recv', 'recvfrom', 'getenv', 'read', 'fgets',
        'fread', 'fscanf', 'scanf', 'gets',

        # PostgreSQL network input
        'socket_read', 'pq_getbyte', 'pq_getmessage', 'pq_getmsgstring',
        'pq_getmsgint', 'pq_getmsgbytes', 'pq_getstring', 'pq_peekbyte',
        'pq_getbytes', 'ProcessStartupPacket',

        # PostgreSQL query input
        'pg_parse_query', 'raw_parser', 'pg_get_userbyid', 'plpgsql_parse_word',
        'plpgsql_parse_dblword', 'defGetString', 'defGetNumeric',

        # PostgreSQL function arguments
        'PG_GETARG_TEXT_P', 'PG_GETARG_VARCHAR_P', 'PG_GETARG_CSTRING',
        'PG_GETARG_NAME', 'PG_GETARG_BYTEA_P', 'PG_GETARG_DATUM',

        # Environment and configuration
        'getenv', 'GetConfigOption', 'GetConfigOptionByName',
    ]


def get_taint_sinks() -> List[str]:
    """Get taint sink functions for dataflow analysis."""
    return [
        # SQL execution
        'exec_simple_query', 'SPI_execute', 'SPI_exec', 'SPI_execute_extended',
        'SPI_cursor_open', 'plpgsql_exec_function', 'ExecutorRun',

        # Command execution
        'system', 'popen', 'exec', 'execl', 'execv', 'execle', 'execve',
        'fork', 'vfork', 'shell_quote_literal',

        # File operations
        'fopen', 'open', 'write', 'fwrite', 'unlink', 'remove',
        'PathNameOpenFile', 'AllocateFile', 'pg_read_file',

        # Buffer overflow prone
        'strcpy', 'strcat', 'sprintf', 'vsprintf', 'gets',
        'memcpy', 'memmove',

        # Network output
        'pq_sendstring', 'pq_sendbytes', 'pq_sendint', 'pq_sendint64',
        'pq_putmessage', 'socket_write',
    ]


def get_vulnerability_function_mappings() -> Dict[str, List[str]]:
    """Get vulnerability type to function mappings for retrieval."""
    return {
        'sql_injection': [
            'SPI_execute', 'SPI_exec', 'SPI_execute_plan', 'SPI_execute_extended',
            'exec_simple_query', 'pg_parse_query', 'raw_parser', 'plpgsql_exec_function',
            'SPI_prepare', 'SPI_cursor_open', 'PQexec', 'PQexecParams',
        ],
        'buffer_overflow': [
            'strcpy', 'strcat', 'sprintf', 'vsprintf', 'gets', 'scanf',
            'memcpy', 'memmove', 'strncpy', 'strncat', 'snprintf', 'vsnprintf',
            'pg_sprintf', 'appendStringInfo', 'appendBinaryStringInfo',
        ],
        'integer_overflow': [
            'palloc', 'malloc', 'calloc', 'repalloc', 'realloc',
            'pg_malloc', 'pg_realloc', 'MemoryContextAlloc', 'MemoryContextAllocZero',
            'mul_size', 'add_size',
        ],
        'null_pointer': [
            'palloc', 'malloc', 'calloc', 'pfree', 'free',
            'PointerIsValid', 'OidIsValid', 'RelationIsValid',
            'HeapTupleIsValid', 'BufferIsValid', 'ItemPointerIsValid',
        ],
        'double_free': [
            'pfree', 'free', 'MemoryContextDelete', 'MemoryContextReset',
            'ResourceOwnerRelease', 'AtEOXact_cleanup', 'FreeExecutorState',
        ],
        'use_after_free': [
            'pfree', 'free', 'MemoryContextDelete', 'AtEOXact_cleanup',
            'ResourceOwnerRelease', 'MemoryContextReset', 'FreeExecutorState',
        ],
        'race_condition': [
            'LWLockAcquire', 'SpinLockAcquire', 'LockAcquire',
            'LWLockRelease', 'SpinLockRelease', 'LockRelease',
            'pg_atomic_read_u32', 'pg_atomic_write_u32', 'pg_memory_barrier',
        ],
        'privilege_escalation': [
            'superuser', 'pg_has_role', 'has_privs_of_role', 'is_member_of_role',
            'check_is_member_of_role', 'has_table_privilege', 'has_function_privilege',
            'pg_class_aclcheck', 'pg_proc_aclcheck', 'object_aclcheck',
        ],
        'command_injection': [
            'system', 'popen', 'exec', 'execl', 'execv', 'execle', 'execve',
            'fork', 'vfork', 'shell_quote_literal', 'run_command',
        ],
        'format_string': [
            'ereport', 'printf', 'fprintf', 'sprintf', 'snprintf',
            'elog', 'errmsg', 'errdetail', 'errhint', 'appendStringInfo',
        ],
        'error_info_leak': [
            'ereport', 'errdetail', 'errmsg', 'elog', 'errhint',
            'errcontext', 'internalerrposition', 'geterrcode',
        ],
        'deserialization': [
            'stringToNode', 'readNodesBinaryString', 'nodeRead',
            'parseNodeString', 'readDatum', 'OidInputFunctionCall',
        ],
        'credentials': [
            'CheckPassword', 'md5_crypt_verify', 'scram_verify_plain_password',
            'plain_crypt_verify', 'get_password_type', 'encrypt_password',
            'pg_be_scram_exchange', 'auth_peer', 'auth_password',
        ],
        'path_traversal': [
            'pg_read_file', 'PathNameOpenFile', 'AllocateFile', 'OpenTransientFile',
            'pg_ls_dir', 'pg_stat_file', 'pathname', 'PathNameDeleteTemporaryFile',
        ],
        'crypto': [
            'SSL_CTX_set', 'SSL_connect', 'SSL_read', 'SSL_write',
            'pg_strong_random', 'RAND_bytes', 'EVP_EncryptInit',
            'be_tls_init', 'secure_read', 'secure_write',
        ],
        'xxe': [
            'xml_parse', 'xmlParseDoc', 'xmlReadFile', 'xmlReadMemory',
            'xmlCtxtReadDoc', 'xpath', 'xml_in', 'xmlelement',
        ],
        'type_confusion': [
            'nodeTag', 'IsA', 'castNode', 'AssertMacro',
            'CheckNodeType', 'copyObjectImpl', 'makeNode',
        ],
        'dos': [
            'palloc', 'MemoryContextAlloc', 'repalloc', 'palloc_extended',
            'AllocSetContextCreate', 'MemoryContextCreate', 'aset_alloc',
        ],
        'weak_random': [
            'random', 'rand', 'srand', 'pg_strong_random', 'pg_backend_random',
            'arc4random', 'RAND_bytes', 'drandom',
        ],
    }


def get_duplicate_pattern_functions() -> Dict[str, List[str]]:
    """Get duplicate pattern to expected function mappings."""
    return {
        'error_handling': [
            'ereport', 'elog', 'errdetail', 'errmsg', 'errhint',
            'errcode', 'errcontext', 'PG_TRY', 'PG_CATCH', 'PG_END_TRY',
        ],
        'memory_allocation': [
            'palloc', 'palloc0', 'repalloc', 'pfree', 'palloc_extended',
            'MemoryContextAlloc', 'MemoryContextAllocZero', 'pstrdup',
        ],
        'locking': [
            'LWLockAcquire', 'LockAcquire', 'LWLockRelease', 'LockRelease',
            'SpinLockAcquire', 'SpinLockRelease', 'ConditionalLockAcquire',
        ],
        'node_init': [
            'makeNode', 'newNode', 'copyObject', 'palloc0fast',
            'NodeSetTag', 'nodeTag', 'IsA',
        ],
        'tuple_processing': [
            'heap_gettuple', 'ExecStoreTuple', 'slot_getattr',
            'heap_getattr', 'fastgetattr', 'slot_getsomeattrs',
            'ExecStoreVirtualTuple', 'ExecClearTuple',
        ],
        'scan': [
            'ExecSeqScan', 'ExecIndexScan', 'ExecScan', 'ExecProcNode',
            'ExecBitmapHeapScan', 'ExecIndexOnlyScan', 'ExecTidScan',
        ],
        'transaction': [
            'StartTransaction', 'CommitTransaction', 'AbortTransaction',
            'BeginTransactionBlock', 'EndTransactionBlock',
            'StartTransactionCommand', 'CommitTransactionCommand',
        ],
        'buffer': [
            'ReadBuffer', 'ReleaseBuffer', 'MarkBufferDirty',
            'LockBuffer', 'UnlockBuffers', 'BufferGetPage',
            'ReadBufferExtended', 'FlushBuffer',
        ],
        'syscache': [
            'SearchSysCache', 'ReleaseSysCache', 'SearchSysCacheCopy',
            'GetSysCacheOid', 'SearchSysCache1', 'SearchSysCache2',
        ],
        'guc': [
            'DefineCustomIntVariable', 'DefineCustomBoolVariable',
            'DefineCustomStringVariable', 'DefineCustomRealVariable',
            'DefineCustomEnumVariable', 'GetConfigOption',
        ],
        'permission': [
            'pg_has_role', 'has_table_privilege', 'has_function_privilege',
            'pg_class_aclcheck', 'object_aclcheck', 'check_is_member_of_role',
        ],
        'hash': [
            'hash_create', 'hash_search', 'hash_seq_search',
            'hash_seq_init', 'hash_destroy', 'hash_update_hash_key',
        ],
        'try_catch': [
            'PG_TRY', 'PG_CATCH', 'PG_END_TRY', 'PG_FINALLY',
            'PG_RE_THROW', 'FlushErrorState',
        ],
        'expression': [
            'ExecEvalExpr', 'ExecEvalExprSwitchContext', 'ExecInitExpr',
            'ExecInitExprRec', 'ExecInitQual', 'ExecQual',
        ],
        'null_check': [
            'PointerIsValid', 'OidIsValid', 'RelationIsValid',
            'Assert', 'AssertArg', 'HeapTupleIsValid',
        ],
        'list_iteration': [
            'foreach', 'list_head', 'list_length', 'lnext',
            'lfirst', 'linitial', 'lsecond', 'llast',
        ],
    }


def get_compliance_patterns() -> Dict[str, List[str]]:
    """Get patterns for compliance/coding style checking."""
    return {
        'naming_prefixes': ['pg_', 'Pg', 'PG_'],
        'error_functions': [
            'ereport', 'elog', 'errcode', 'errmsg', 'errdetail',
            'errhint', 'errcontext', 'errposition',
        ],
        'memory_functions': [
            'palloc', 'palloc0', 'pfree', 'repalloc',
            'MemoryContextAlloc', 'MemoryContextAllocZero',
            'MemoryContextDelete', 'MemoryContextReset',
        ],
        'assert_macros': [
            'Assert', 'AssertMacro', 'AssertArg', 'AssertState',
            'Insist', 'StaticAssertStmt', 'StaticAssertExpr',
        ],
        'locking_patterns': [
            'LWLockAcquire', 'LWLockRelease', 'SpinLockAcquire',
            'SpinLockRelease', 'LockAcquire', 'LockRelease',
        ],
        'transaction_patterns': [
            'StartTransaction', 'CommitTransaction', 'AbortTransaction',
            'BeginTransactionBlock', 'EndTransactionBlock',
        ],
    }


def get_refactoring_patterns() -> Dict[str, str]:
    """Get SQL LIKE patterns for refactoring queries."""
    return {
        'palloc': 'palloc%',
        'pfree': 'pfree%',
        'repalloc': 'repalloc%',
        'elog': 'elog%',
        'ereport': 'ereport%',
        'memory_context': 'MemoryContext%',
        'lwlock': 'LWLock%',
        'spinlock': 'SpinLock%',
        'pg_prefix': 'pg_%',
        'exec_prefix': 'Exec%',
        'spi_prefix': 'SPI_%',
    }


def get_sql_query_patterns() -> Dict[str, List[str]]:
    """Get function lists for building SQL IN clauses."""
    return {
        'file_operations': [
            'copy_file', 'pg_file_read', 'FileRead', 'FileWrite',
            'pg_file_write', 'PathNameOpenFile', 'OpenTransientFile',
            'AllocateFile', 'FreeFile', 'pg_read_file', 'pg_read_binary_file',
        ],
        'permission_checks': [
            'check_conn_params', 'pg_permission_denied', 'has_table_privilege',
            'has_schema_privilege', 'has_database_privilege', 'pg_has_role',
            'has_function_privilege', 'has_sequence_privilege',
        ],
        'query_execution': [
            'exec_simple_query', 'pg_parse_query', 'ProcessUtility',
            'standard_ProcessUtility', 'pg_analyze_and_rewrite', 'pg_plan_query',
            'ExecutorStart', 'ExecutorRun', 'ExecutorEnd',
        ],
        'acl_checks': [
            'aclcheck_error', 'aclmask', 'pg_attribute_aclcheck',
            'pg_attribute_aclcheck_all', 'acldefault', 'pg_class_aclcheck',
            'has_table_privilege', 'pg_permission_denied', 'check_is_member_of_role',
            'object_aclcheck', 'pg_proc_aclcheck',
        ],
        'memory_operations': [
            'ReadBuffer', 'BufferAlloc', 'palloc', 'repalloc',
            'MemoryContextAlloc', 'pfree', 'MemoryContextDelete',
        ],
        'wal_operations': [
            'XLogInsert', 'XLogFlush', 'XLogWrite', 'XLogBeginInsert',
            'XLogRegisterData', 'XLogReadRecord', 'StartupXLOG',
        ],
        'extension_entry': [
            'pg_finfo_', 'PG_FUNCTION_INFO_V1', '_PG_init', '_PG_fini',
        ],
        'parser_functions': [
            'raw_parser', 'pg_parse_query', 'transformStmt', 'base_yyparse',
        ],
    }


def get_documentation_patterns() -> List[str]:
    """Get regex patterns for extracting documentation-relevant code."""
    return [
        r'\b(ereport)\b', r'\b(elog)\b', r'\b(palloc)\b', r'\b(pfree)\b',
        r'\b(repalloc)\b', r'\b(pstrdup)\b', r'\b(errcode)\b', r'\b(errmsg)\b',
        r'\b(errdetail)\b', r'\b(errhint)\b', r'\b(errcontext)\b',
        r'\b(PG_TRY)\b', r'\b(PG_CATCH)\b', r'\b(PG_END_TRY)\b',
        r'\b(Assert)\b', r'\b(AssertMacro)\b',
    ]


def get_domain_keywords() -> Dict[str, List[str]]:
    """Get domain-specific keywords for retrieval and analysis."""
    return {
        'memory': [
            'shared_buffers', 'memory', 'cache', 'buffer', 'palloc',
            'malloc', 'shmem', 'shared memory', 'memory context', 'allocation',
        ],
        'vacuum': [
            'vacuum', 'autovacuum', 'analyze', 'dead tuple', 'bloat',
            'free space', 'visibility map', 'freeze',
        ],
        'wal': [
            'wal', 'xlog', 'checkpoint', 'recovery', 'archive',
            'write-ahead log', 'replication', 'pg_wal',
        ],
        'mvcc': [
            'mvcc', 'snapshot', 'visibility', 'transaction', 'xid',
            'xmin', 'xmax', 'clog', 'commit log',
        ],
        'query-planning': [
            'planner', 'optimizer', 'plan', 'cost', 'selectivity',
            'statistics', 'index scan', 'seq scan', 'join',
        ],
        'replication': [
            'replication', 'streaming', 'logical', 'wal sender', 'wal receiver',
            'primary', 'standby', 'slot', 'publication', 'subscription',
        ],
        'storage': [
            'storage', 'heap', 'toast', 'fsm', 'visibility map',
            'page', 'tuple', 'block', 'relation', 'file',
        ],
        'indexes': [
            'index', 'btree', 'hash', 'gist', 'gin', 'brin',
            'index scan', 'index only scan', 'bitmap',
        ],
        'locking': [
            'lock', 'lwlock', 'spinlock', 'deadlock', 'wait',
            'contention', 'heavyweight', 'lightweight', 'advisory',
        ],
        'parallel': [
            'parallel', 'worker', 'gather', 'parallel query',
            'background worker', 'dynamic shared memory',
        ],
        'partition': [
            'partition', 'partitioning', 'range', 'list', 'hash',
            'partition pruning', 'inheritance',
        ],
        'jsonb': [
            'json', 'jsonb', 'jsonpath', 'gin', 'containment',
            'json operator', 'json function',
        ],
        'security': [
            'security', 'permission', 'acl', 'role', 'privilege',
            'row level security', 'rls', 'policy', 'grant',
        ],
        'background': [
            'background', 'bgworker', 'autovacuum', 'checkpointer',
            'wal writer', 'stats collector', 'archiver',
        ],
        'extension': [
            'extension', 'contrib', 'hook', 'plugin', 'module',
            'pg_config', 'create extension',
        ],
        'performance': [
            'performance', 'slow', 'bottleneck', 'optimization',
            'tuning', 'benchmark', 'explain', 'analyze',
        ],
        'catalog': [
            'catalog', 'pg_class', 'pg_attribute', 'system table',
            'metadata', 'schema', 'pg_catalog',
        ],
        'error-handling': [
            'error', 'exception', 'elog', 'ereport', 'warning',
            'notice', 'panic', 'fatal',
        ],
    }


def get_keyword_mappings() -> Dict[str, List[str]]:
    """Get keyword to function/pattern mappings for scenario workflows."""
    return {
        'format_string': ['format string', 'printf', 'ereport', 'sprintf', 'snprintf'],
        'error_handling': ['error', 'ereport', 'elog', 'exception', 'errcode', 'errmsg'],
        'memory_allocation': ['memory', 'allocation', 'palloc', 'malloc', 'repalloc', 'pfree'],
        'try_catch': ['try', 'catch', 'PG_TRY', 'PG_CATCH', 'PG_END_TRY', 'PG_FINALLY'],
        'atomic': ['atomic', 'pg_atomic', 'pg_atomic_read', 'pg_atomic_write'],
        'allocation': ['palloc', 'allocation', 'MemoryContext', 'alloc', 'palloc0'],
        'deallocation': ['pfree', 'free', 'deallocation', 'release', 'MemoryContextDelete'],
        'lock': ['lock', 'LWLock', 'SpinLock', 'mutex', 'semaphore'],
        'trace': ['trace', 'trace_recovery', 'trace_sort', 'trace_notify', 'pg_trace'],
        'stack_trace': ['errbacktrace', 'pg_backtrace', 'check_stack_depth', 'stack_base'],
        'parser': ['raw_parser', 'pg_parse_query', 'transformStmt', 'gram.y'],
    }
