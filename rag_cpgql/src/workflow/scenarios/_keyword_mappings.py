"""Keyword mappings for scenario workflows.

Maps user query keywords to vulnerability types and duplicate patterns.
These mappings are domain-agnostic - the actual function lists come from
the domain plugin.
"""

# Vulnerability type keywords for security analysis
VULNERABILITY_KEYWORDS = {
    'sql_injection': ['sql injection', 'dynamic query', 'sql', 'spi_execute', 'query construction'],
    'buffer_overflow': ['sprintf', 'strcpy', 'buffer overflow', 'strcat', 'memcpy'],
    'integer_overflow': ['integer overflow', 'size calculation', 'overflow', 'mul_size'],
    'null_pointer': ['null pointer', 'null dereference', 'allocation', 'null check'],
    'double_free': ['double free', 'double-free'],
    'use_after_free': ['use after free', 'use-after-free', 'dangling pointer'],
    'race_condition': ['race', 'shared memory', 'concurrent', 'toctou'],
    'privilege_escalation': ['privilege', 'escalation', 'superuser', 'permission'],
    'command_injection': ['command injection', 'shell', 'system', 'popen', 'exec'],
    'format_string': ['format string', 'printf', 'ereport'],
    'error_info_leak': ['error message', 'leak', 'information disclosure', 'errdetail'],
    'deserialization': ['deserialization', 'noderead', 'stringtonode'],
    'credentials': ['password', 'credential', 'hardcoded', 'authentication'],
    'path_traversal': ['path traversal', 'directory traversal', 'file access'],
    'crypto': ['crypto', 'ssl', 'tls', 'encryption', 'random'],
    'xxe': ['xxe', 'xml', 'entity'],
    'type_confusion': ['type confusion', 'cast', 'nodetag'],
    'dos': ['denial', 'exhaustion', 'dos', 'resource'],
    'weak_random': ['random', 'entropy', 'predictable'],
}

# Duplicate pattern keywords for refactoring analysis
DUPLICATE_PATTERN_KEYWORDS = {
    'error_handling': ['error', 'ereport', 'elog', 'exception'],
    'memory_allocation': ['memory', 'allocation', 'palloc', 'malloc'],
    'locking': ['lock', 'acquisition', 'lwlock', 'synchronization'],
    'node_init': ['node', 'initialization', 'makenode'],
    'tuple_processing': ['tuple', 'slot', 'heap'],
    'scan': ['scan', 'seqscan', 'indexscan'],
    'transaction': ['transaction', 'commit', 'abort'],
    'buffer': ['buffer', 'readbuffer', 'markbufferdirty'],
    'syscache': ['catalog', 'syscache', 'searchsyscache'],
    'guc': ['guc', 'variable', 'configuration'],
    'permission': ['permission', 'privilege', 'acl'],
    'hash': ['hash', 'hashcreate', 'hashsearch'],
    'try_catch': ['try', 'catch', 'pg_try'],
    'expression': ['expression', 'eval', 'execevalexpr'],
    'null_check': ['null check', 'validation', 'assert'],
    'list_iteration': ['list', 'foreach', 'iteration'],
}

# Concurrency-related keywords
CONCURRENCY_KEYWORDS = {
    'lwlock': ['lwlock', 'lightweight lock'],
    'spinlock': ['spinlock', 'spin lock', 'spin_lock'],
    'heavyweight_lock': ['heavyweight', 'lock manager', 'lockacquire'],
    'atomic': ['atomic', 'pg_atomic'],
    'latch': ['latch', 'waitlatch', 'setlatch'],
    'barrier': ['barrier', 'memory barrier', 'fence'],
    'condition_variable': ['condition variable', 'condvar', 'conditionvariable'],
    'semaphore': ['semaphore', 'pgsemaphore'],
}

# Memory-related keywords
MEMORY_KEYWORDS = {
    'allocation': ['palloc', 'allocation', 'memorycontext', 'alloc'],
    'deallocation': ['pfree', 'free', 'deallocation', 'release'],
    'context': ['memory context', 'memorycontext', 'mcxt', 'aset'],
    'leak': ['memory leak', 'leak detection'],
}


def get_matching_vulnerability_types(query: str) -> list:
    """
    Get vulnerability types that match keywords in the query.

    Args:
        query: User query string

    Returns:
        List of matching vulnerability type keys
    """
    query_lower = query.lower()
    matches = []
    for vuln_type, keywords in VULNERABILITY_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matches.append(vuln_type)
    return matches


def get_matching_duplicate_patterns(query: str) -> list:
    """
    Get duplicate pattern types that match keywords in the query.

    Args:
        query: User query string

    Returns:
        List of matching pattern type keys
    """
    query_lower = query.lower()
    matches = []
    for pattern_type, keywords in DUPLICATE_PATTERN_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matches.append(pattern_type)
    return matches


def get_matching_concurrency_categories(query: str) -> list:
    """
    Get concurrency categories that match keywords in the query.

    Args:
        query: User query string

    Returns:
        List of matching concurrency category keys
    """
    query_lower = query.lower()
    matches = []
    for category, keywords in CONCURRENCY_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matches.append(category)
    return matches


def get_matching_memory_categories(query: str) -> list:
    """
    Get memory categories that match keywords in the query.

    Args:
        query: User query string

    Returns:
        List of matching memory category keys
    """
    query_lower = query.lower()
    matches = []
    for category, keywords in MEMORY_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matches.append(category)
    return matches


__all__ = [
    'VULNERABILITY_KEYWORDS',
    'DUPLICATE_PATTERN_KEYWORDS',
    'CONCURRENCY_KEYWORDS',
    'MEMORY_KEYWORDS',
    'get_matching_vulnerability_types',
    'get_matching_duplicate_patterns',
    'get_matching_concurrency_categories',
    'get_matching_memory_categories',
]
