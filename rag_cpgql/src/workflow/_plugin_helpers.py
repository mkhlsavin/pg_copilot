"""Plugin Helper Functions for Multi-Scenario Workflow

Provides functions to get domain-specific data from the active domain plugin.
These helpers centralize access to plugin data for consistency across scenarios.
"""

from typing import Dict, List
from src.domains import DomainRegistry


def get_memory_keywords() -> List[str]:
    """Get memory-related keywords from active domain plugin."""
    base_keywords = ['memory', 'allocation', 'memory leak', 'mcxt', 'aset', 'mctx']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_memory_functions'):
            mem_funcs = domain.get_memory_functions()
            # Add function names as keywords (lowercased)
            for category in mem_funcs.values():
                if isinstance(category, list):
                    base_keywords.extend([f.lower() for f in category])
        return list(set(base_keywords))
    except Exception:
        return base_keywords + ['palloc', 'pfree', 'repalloc', 'memorycontext']


def get_lock_keywords() -> List[str]:
    """Get lock-related keywords from active domain plugin."""
    # Base keywords include all common lock-related terms
    base_keywords = ['synchronization', 'concurrency', 'thread', 'atomic',
                     'race condition', 'latch', 'barrier', 'lock manager',
                     'mutex', 'semaphore',
                     # PostgreSQL-specific lock keywords (must be present for high precision)
                     'lwlock', 'spinlock', 'spin_lock', 'shmem', 'shared memory',
                     'advisory lock', 'relation lock', 'pg_advisory']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_lock_functions'):
            lock_funcs = domain.get_lock_functions()
            # Add function names as keywords (lowercased)
            base_keywords.extend([f.lower() for f in lock_funcs])
        return list(set(base_keywords))
    except Exception:
        return base_keywords


def get_memory_functions_from_plugin() -> Dict[str, List[str]]:
    """Get memory functions from active domain plugin."""
    default = {
        'allocate': ['palloc', 'palloc0', 'palloc_extended', 'repalloc', 'MemoryContextAlloc'],
        'free': ['pfree', 'MemoryContextDelete', 'MemoryContextReset'],
        'copy': ['pstrdup', 'pnstrdup', 'memcpy', 'memmove'],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_memory_functions'):
            return domain.get_memory_functions()
    except Exception:
        pass
    return default


def get_lock_functions_from_plugin() -> List[str]:
    """Get lock functions from active domain plugin."""
    default = ['LWLockAcquire', 'LWLockRelease', 'LockAcquire', 'LockRelease',
               'SpinLockAcquire', 'SpinLockRelease']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_lock_functions'):
            return domain.get_lock_functions()
    except Exception:
        pass
    return default


def get_debug_functions_from_plugin() -> Dict[str, List[str]]:
    """Get debugging-related functions from active domain plugin."""
    default = {
        'logging': ['elog', 'ereport', 'errcode', 'errmsg', 'errdetail', 'errhint'],
        'assertion': ['Assert', 'AssertMacro', 'AssertArg', 'AssertState'],
        'trace': ['trace_recovery', 'trace_sort', 'trace_notify', 'pg_trace'],
        'explain': ['ExplainQuery', 'ExplainState', 'ExplainPrintPlan'],
        'debug_output': ['DEBUG1', 'DEBUG2', 'DEBUG3', 'DEBUG4', 'DEBUG5'],
        'stack_trace': ['errbacktrace', 'pg_backtrace', 'check_stack_depth'],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_debug_functions'):
            return domain.get_debug_functions()
    except Exception:
        pass
    return default


def get_entry_points_from_plugin() -> List[str]:
    """Get entry point functions from active domain plugin."""
    default = ['PostgresMain', 'PostmasterMain', 'PG_FUNCTION_INFO_V1',
               'exec_simple_query', 'ProcessUtility']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_entry_points'):
            return domain.get_entry_points()
    except Exception:
        pass
    return default


def get_subsystem_functions_from_plugin() -> Dict[str, List[str]]:
    """Get subsystem-organized functions from active domain plugin."""
    default = {
        'executor': ['ExecutorStart', 'ExecutorRun', 'ExecutorEnd', 'ExecProcNode'],
        'parser': ['raw_parser', 'pg_parse_query', 'transformStmt'],
        'optimizer': ['standard_planner', 'subquery_planner', 'create_plan'],
        'buffer': ['ReadBuffer', 'ReleaseBuffer', 'MarkBufferDirty'],
        'wal': ['XLogInsert', 'XLogFlush', 'StartupXLOG'],
        'catalog': ['SearchSysCache', 'RelationIdGetRelation', 'heap_open'],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_subsystem_functions'):
            return domain.get_subsystem_functions()
    except Exception:
        pass
    return default


def get_dml_functions_from_plugin() -> Dict[str, List[str]]:
    """Get DML operation functions from active domain plugin."""
    default = {
        'insert': ['ExecInsert', 'heap_insert', 'simple_heap_insert'],
        'update': ['ExecUpdate', 'heap_update', 'simple_heap_update'],
        'delete': ['ExecDelete', 'heap_delete', 'simple_heap_delete'],
        'select': ['ExecScan', 'SeqNext', 'IndexNext', 'heap_fetch'],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_dml_functions'):
            return domain.get_dml_functions()
    except Exception:
        pass
    return default


def get_error_levels_from_plugin() -> List[str]:
    """Get error levels from active domain plugin."""
    default = ['DEBUG5', 'DEBUG4', 'DEBUG3', 'DEBUG2', 'DEBUG1',
               'LOG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'FATAL', 'PANIC']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_error_levels'):
            return domain.get_error_levels()
    except Exception:
        pass
    return default


def get_utility_noise_functions() -> set:
    """Get utility functions that are typically noise in analysis."""
    # These are common functions that appear frequently but aren't usually
    # the target of analysis queries
    base_set = {'lappend', 'list_make1', 'list_make2', 'list_make3',
                'list_length', 'linitial', 'lsecond', 'lfirst',
                'NIL', 'InvalidOid', 'NULL'}
    try:
        # Add generic C/C++ noise functions if available
        from src.domains.generic_cpp import generic_cpp_plugin
        if hasattr(generic_cpp_plugin, 'get_noise_functions'):
            base_set.update(generic_cpp_plugin.get_noise_functions())
    except Exception:
        pass
    return base_set


__all__ = [
    'get_memory_keywords',
    'get_lock_keywords',
    'get_memory_functions_from_plugin',
    'get_lock_functions_from_plugin',
    'get_debug_functions_from_plugin',
    'get_entry_points_from_plugin',
    'get_subsystem_functions_from_plugin',
    'get_dml_functions_from_plugin',
    'get_error_levels_from_plugin',
    'get_utility_noise_functions',
]
