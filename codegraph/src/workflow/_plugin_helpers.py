# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module provides helper functions to retrieve domain-specific data from
# the active domain plugin. All domain-specific logic MUST come from plugins.
#
# DO NOT add:
#   - Hardcoded function names (pg_*, elog, palloc, etc.)
#   - Hardcoded SQL patterns with domain-specific terms
#   - Domain-specific default values (use empty lists/dicts as fallback)
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""Plugin Helper Functions for Multi-Scenario Workflow

Provides functions to get domain-specific data from the active domain plugin.
These helpers centralize access to plugin data for consistency across scenarios.
"""

import logging
from typing import Dict, List
from src.domains import DomainRegistry

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.debug(f"Could not get memory keywords from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get lock keywords from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get memory functions from plugin: {e}")
    return default


def get_lock_functions_from_plugin() -> List[str]:
    """Get lock functions from active domain plugin."""
    default = ['LWLockAcquire', 'LWLockRelease', 'LockAcquire', 'LockRelease',
               'SpinLockAcquire', 'SpinLockRelease']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_lock_functions'):
            return domain.get_lock_functions()
    except Exception as e:
        logger.debug(f"Could not get lock functions from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get debug functions from plugin: {e}")
    return default


def get_entry_points_from_plugin() -> List[str]:
    """Get entry point functions from active domain plugin."""
    default = ['PostgresMain', 'PostmasterMain', 'PG_FUNCTION_INFO_V1',
               'exec_simple_query', 'ProcessUtility']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_entry_points'):
            return domain.get_entry_points()
    except Exception as e:
        logger.debug(f"Could not get entry points from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get subsystem functions from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get DML functions from plugin: {e}")
    return default


def get_error_levels_from_plugin() -> List[str]:
    """Get error levels from active domain plugin."""
    default = ['DEBUG5', 'DEBUG4', 'DEBUG3', 'DEBUG2', 'DEBUG1',
               'LOG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'FATAL', 'PANIC']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_error_levels'):
            return domain.get_error_levels()
    except Exception as e:
        logger.debug(f"Could not get error levels from plugin: {e}")
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
    except Exception as e:
        logger.debug(f"Could not get noise functions from generic_cpp: {e}")
    return base_set


def get_vulnerability_functions_from_plugin() -> Dict[str, List[str]]:
    """Get vulnerability type → function mappings from active domain plugin."""
    default = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_vulnerability_function_mappings'):
            return domain.get_vulnerability_function_mappings()
    except Exception as e:
        logger.debug(f"Could not get vulnerability functions from plugin: {e}")
    return default


def get_duplicate_functions_from_plugin() -> Dict[str, List[str]]:
    """Get duplicate pattern → function mappings from active domain plugin."""
    default = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_duplicate_pattern_functions'):
            return domain.get_duplicate_pattern_functions()
    except Exception as e:
        logger.debug(f"Could not get duplicate functions from plugin: {e}")
    return default


def get_taint_sources_from_plugin() -> List[str]:
    """Get taint source functions from active domain plugin."""
    default = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_taint_sources'):
            return domain.get_taint_sources()
    except Exception as e:
        logger.debug(f"Could not get taint sources from plugin: {e}")
    return default


def get_taint_sinks_from_plugin() -> List[str]:
    """Get taint sink functions from active domain plugin."""
    default = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_taint_sinks'):
            return domain.get_taint_sinks()
    except Exception as e:
        logger.debug(f"Could not get taint sinks from plugin: {e}")
    return default


def get_concurrency_functions_from_plugin() -> Dict[str, List[str]]:
    """Get concurrency functions organized by category from active domain plugin."""
    default = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_concurrency_functions'):
            return domain.get_concurrency_functions()
    except Exception as e:
        logger.debug(f"Could not get concurrency functions from plugin: {e}")
    return default


def get_breakpoint_functions_from_plugin() -> Dict[str, List[str]]:
    """
    Get debugging breakpoint functions organized by context from active domain plugin.

    Used by debugging.py scenario to build dynamic SQL queries.

    Returns:
        Dictionary mapping debugging context to function lists
    """
    default: Dict[str, List[str]] = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_breakpoint_functions'):
            return domain.get_breakpoint_functions()
    except Exception as e:
        logger.debug(f"Could not get breakpoint functions from plugin: {e}")
    return default


# ============================================================================
# NEW HELPERS FOR DOMAIN ABSTRACTION (Phase 2)
# ============================================================================

def get_compliance_patterns_from_plugin() -> Dict[str, List[str]]:
    """
    Get compliance/coding style patterns from active domain plugin.

    Used by compliance.py scenario to avoid hardcoded function names.

    Returns:
        Dictionary mapping compliance category to function/pattern lists
    """
    default: Dict[str, List[str]] = {
        'naming_prefixes': [],
        'error_functions': [],
        'memory_functions': [],
        'assert_macros': [],
        'locking_patterns': [],
        'transaction_patterns': [],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_compliance_patterns'):
            return domain.get_compliance_patterns()
    except Exception as e:
        logger.debug(f"Could not get compliance patterns from plugin: {e}")
    return default


def get_refactoring_patterns_from_plugin() -> Dict[str, str]:
    """
    Get SQL LIKE patterns for refactoring queries from active domain plugin.

    Used by refactoring.py scenario to build dynamic SQL queries.

    Returns:
        Dictionary mapping pattern name to SQL LIKE pattern (e.g., 'palloc%')
    """
    default: Dict[str, str] = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_refactoring_patterns'):
            return domain.get_refactoring_patterns()
    except Exception as e:
        logger.debug(f"Could not get refactoring patterns from plugin: {e}")
    return default


def get_sql_query_patterns_from_plugin() -> Dict[str, List[str]]:
    """
    Get function lists for building SQL IN clauses from active domain plugin.

    Used by security.py and other scenarios to avoid hardcoded SQL.

    Returns:
        Dictionary mapping pattern category to list of function names
    """
    default: Dict[str, List[str]] = {
        'file_operations': [],
        'permission_checks': [],
        'query_execution': [],
        'acl_checks': [],
        'memory_operations': [],
        'wal_operations': [],
        'extension_entry': [],
        'parser_functions': [],
    }
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_sql_query_patterns'):
            return domain.get_sql_query_patterns()
    except Exception as e:
        logger.debug(f"Could not get SQL query patterns from plugin: {e}")
    return default


def get_documentation_patterns_from_plugin() -> List[str]:
    """
    Get regex patterns for documentation extraction from active domain plugin.

    Used by documentation.py scenario.

    Returns:
        List of regex patterns for matching domain-specific code
    """
    default: List[str] = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_documentation_patterns'):
            return domain.get_documentation_patterns()
    except Exception as e:
        logger.debug(f"Could not get documentation patterns from plugin: {e}")
    return default


def get_domain_keywords_from_plugin() -> Dict[str, List[str]]:
    """
    Get domain-specific keywords for retrieval and analysis from active domain plugin.

    Used by analyzer_agent.py to replace hardcoded domain_keywords.

    Returns:
        Dictionary mapping domain area to relevant keywords
    """
    default: Dict[str, List[str]] = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_domain_keywords'):
            return domain.get_domain_keywords()
    except Exception as e:
        logger.debug(f"Could not get domain keywords from plugin: {e}")
    return default


def get_keyword_mappings_from_plugin() -> Dict[str, List[str]]:
    """
    Get keyword to function/pattern mappings from active domain plugin.

    Used by _keyword_mappings.py to replace hardcoded mappings.

    Returns:
        Dictionary mapping keyword category to related terms
    """
    default: Dict[str, List[str]] = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_keyword_mappings'):
            return domain.get_keyword_mappings()
    except Exception as e:
        logger.debug(f"Could not get keyword mappings from plugin: {e}")
    return default


def get_noise_functions_from_plugin() -> List[str]:
    """
    Get list of noise/utility functions to filter out from active domain plugin.

    Used to filter common utility functions that add noise to analysis results.

    Returns:
        List of function names to filter
    """
    default: List[str] = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_noise_functions'):
            return domain.get_noise_functions()
    except Exception as e:
        logger.debug(f"Could not get noise functions from plugin: {e}")
    return default


def get_sanitization_patterns_from_plugin() -> List[Dict]:
    """
    Get sanitization patterns for dataflow analysis from active domain plugin.

    Returns:
        List of sanitization pattern definitions
    """
    default: List[Dict] = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_sanitization_patterns'):
            return domain.get_sanitization_patterns()
    except Exception as e:
        logger.debug(f"Could not get sanitization patterns from plugin: {e}")
    return default


def get_sanitization_confidence_from_plugin() -> Dict[str, float]:
    """
    Get sanitization confidence scores from active domain plugin.

    Returns:
        Dictionary mapping pattern names to confidence scores (0.0-1.0)
    """
    default: Dict[str, float] = {}
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_sanitization_confidence'):
            return domain.get_sanitization_confidence()
    except Exception as e:
        logger.debug(f"Could not get sanitization confidence from plugin: {e}")
    return default


def get_hardening_patterns_from_plugin() -> List[Dict]:
    """
    Get D3FEND Source Code Hardening patterns from active domain plugin.

    Used by HardeningScanner to get domain-specific hardening checks.

    Returns:
        List of hardening pattern dictionaries with keys:
        - id: Unique pattern identifier
        - d3fend_id: D3FEND technique ID (e.g., "D3-VI", "D3-NPC")
        - d3fend_name: D3FEND technique name
        - category: Category (initialization, pointer_safety, etc.)
        - severity: critical/high/medium/low/info
        - description: Pattern description
        - cpgql_query: CPGQL query to find violations
        - cwe_ids: List of related CWE IDs
        - language_scope: List of applicable languages or ["*"]
        - indicators: Code patterns indicating violations
        - good_patterns: Recommended patterns
        - remediation: How to fix
    """
    default: List[Dict] = []
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_hardening_patterns'):
            return domain.get_hardening_patterns()
    except Exception as e:
        logger.debug(f"Could not get hardening patterns from plugin: {e}")
    return default


def build_sql_in_clause(function_list: List[str]) -> str:
    """
    Build a SQL IN clause from a list of function names.

    Args:
        function_list: List of function names

    Returns:
        SQL IN clause string, e.g., "('func1', 'func2', 'func3')"
    """
    if not function_list:
        return "('')"
    names = ', '.join(f"'{name}'" for name in function_list)
    return f"({names})"


def build_sql_like_clause(patterns: Dict[str, str], column: str = 'name') -> str:
    """
    Build a SQL OR clause with LIKE patterns.

    Args:
        patterns: Dictionary mapping pattern name to LIKE pattern
        column: Column name to apply LIKE to (default: 'name')

    Returns:
        SQL clause string, e.g., "name LIKE 'palloc%' OR name LIKE 'pfree%'"
    """
    if not patterns:
        return "1=0"  # Always false if no patterns
    clauses = [f"{column} LIKE '{pattern}'" for pattern in patterns.values()]
    return ' OR '.join(clauses)


def get_domain_display_name_from_plugin() -> str:
    """
    Get the display name of the active domain plugin.

    Used to replace hardcoded "PostgreSQL" strings in prompts and UI.

    Returns:
        Domain display name (e.g., "PostgreSQL", "Linux Kernel", etc.)
        Falls back to "the codebase" if no domain is active.
    """
    default = "the codebase"
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'display_name'):
            return domain.display_name
    except Exception as e:
        logger.debug(f"Could not get domain display name from plugin: {e}")
    return default


__all__ = [
    # Core helpers
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
    'get_vulnerability_functions_from_plugin',
    'get_duplicate_functions_from_plugin',
    'get_taint_sources_from_plugin',
    'get_taint_sinks_from_plugin',
    'get_concurrency_functions_from_plugin',
    'get_breakpoint_functions_from_plugin',
    # New helpers for domain abstraction (Phase 2)
    'get_compliance_patterns_from_plugin',
    'get_refactoring_patterns_from_plugin',
    'get_sql_query_patterns_from_plugin',
    'get_documentation_patterns_from_plugin',
    'get_domain_keywords_from_plugin',
    'get_keyword_mappings_from_plugin',
    'get_noise_functions_from_plugin',
    'get_sanitization_patterns_from_plugin',
    'get_sanitization_confidence_from_plugin',
    # D3FEND hardening helpers
    'get_hardening_patterns_from_plugin',
    # SQL building utilities
    'build_sql_in_clause',
    'build_sql_like_clause',
    # Domain display name
    'get_domain_display_name_from_plugin',
]
