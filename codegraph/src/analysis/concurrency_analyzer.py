"""
Concurrency Analyzer - Graph Method for Scenario 09

Implements concurrency analysis for detecting synchronization issues,
race conditions, and lock-related problems in C codebases.

**Core Features:**
- Lock usage analysis (LWLock, SpinLock, regular locks)
- Race condition detection patterns
- Shared memory access analysis
- Synchronization primitive detection
- Lock ordering analysis (deadlock patterns)

**Key Algorithms:**
1. **Lock Pattern Detection**: Find acquire/release pairs
2. **Shared Access Analysis**: Track variables accessed by multiple functions
3. **TOCTOU Detection**: Time-of-check to time-of-use patterns
4. **Lock Graph Analysis**: Build lock acquisition order graph

**Use Cases:**
- Scenario 9: Concurrency Analysis
- Security: Race condition vulnerabilities
- Reliability: Deadlock detection

Based on: "Graph methods for RAG copilot.md"
Used in scenarios: 9 (primary), 4 (security), 15 (new vulnerabilities)
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LockUsage:
    """Represents a lock usage pattern"""
    function_name: str
    lock_type: str  # LWLock, SpinLock, LockAcquire, etc.
    lock_name: Optional[str]
    operation: str  # acquire, release, try_acquire
    file_name: str
    line_number: int


@dataclass
class RaceConditionPattern:
    """Represents a potential race condition"""
    pattern_id: str
    pattern_type: str  # TOCTOU, unprotected_access, signal_handler, etc.
    affected_functions: List[str]
    shared_resource: str
    severity: str  # high, medium, low
    description: str


@dataclass
class SharedAccess:
    """Represents shared memory/variable access"""
    variable_name: str
    accessor_functions: List[str]
    access_type: str  # read, write, read_write
    is_protected: bool
    protecting_lock: Optional[str]


@dataclass
class LockOrderViolation:
    """Represents a potential lock ordering issue (deadlock risk)"""
    violation_id: str
    lock_a: str
    lock_b: str
    function_acquiring_a_then_b: str
    function_acquiring_b_then_a: str
    risk_level: str  # high, medium, low


class ConcurrencyAnalyzer:
    """
    Concurrency analysis for detecting synchronization issues.

    **Core Methods:**
    - find_lock_usage: Find all lock acquisition/release patterns
    - detect_race_conditions: Identify potential race condition patterns
    - analyze_shared_access: Find shared variable access patterns
    - detect_lock_ordering_issues: Find potential deadlock patterns
    - find_atomic_operations: Find atomic/barrier operations
    - find_signal_handlers: Analyze signal handler safety

    **Lock Types Supported:**
    - LWLock (PostgreSQL lightweight locks)
    - SpinLock (busy-wait locks)
    - Regular locks (LockAcquire/LockRelease)
    - Condition variables
    - Latches

    **Race Condition Patterns:**
    - TOCTOU (Time-of-check to time-of-use)
    - Unprotected shared access
    - Signal handler issues
    - Double-checked locking
    """

    # Lock-related function patterns
    LOCK_PATTERNS = {
        'lwlock': {
            'acquire': ['LWLockAcquire', 'LWLockConditionalAcquire', 'LWLockAcquireOrWait'],
            'release': ['LWLockRelease', 'LWLockReleaseAll'],
            'check': ['LWLockHeldByMe', 'LWLockHeldByMeInMode'],
        },
        'spinlock': {
            'acquire': ['SpinLockAcquire', 'SpinLockInit'],
            'release': ['SpinLockRelease'],
        },
        'regular_lock': {
            'acquire': ['LockAcquire', 'LockAcquireExtended', 'ConditionalLockRelation'],
            'release': ['LockRelease', 'LockReleaseAll'],
        },
        'condvar': {
            'wait': ['ConditionVariableSleep', 'ConditionVariablePrepareToSleep'],
            'signal': ['ConditionVariableBroadcast', 'ConditionVariableSignal'],
        },
        'latch': {
            'wait': ['WaitLatch', 'WaitLatchOrSocket'],
            'signal': ['SetLatch', 'ResetLatch'],
        },
        'atomic': {
            'read': ['pg_atomic_read_u32', 'pg_atomic_read_u64'],
            'write': ['pg_atomic_write_u32', 'pg_atomic_write_u64'],
            'cas': ['pg_atomic_compare_exchange_u32', 'pg_atomic_compare_exchange_u64'],
            'barrier': ['pg_memory_barrier', 'pg_read_barrier', 'pg_write_barrier'],
        },
    }

    # Shared memory patterns
    SHARED_MEMORY_PATTERNS = [
        'ShmemAlloc', 'ShmemInitStruct', 'ShmemInitHash',
        'dsm_create', 'dsm_attach', 'dsm_segment_address',
        'shm_mq_send', 'shm_mq_receive',
    ]

    def __init__(self, cpg_service):
        """
        Initialize analyzer with CPG service

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        self.cpg = cpg_service
        # Support both execute_query and execute_sql_dict methods
        if hasattr(cpg_service, 'execute_query'):
            self._execute_base = cpg_service.execute_query
            self._use_inline_params = False
        elif hasattr(cpg_service, 'execute_sql_dict'):
            self._execute_base = cpg_service.execute_sql_dict
            self._use_inline_params = True
        else:
            raise ValueError("CPG service must have execute_query or execute_sql_dict method")
        logger.info("ConcurrencyAnalyzer initialized")

    def _run_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query with proper parameter handling"""
        if self._use_inline_params:
            # Inline parameters for execute_sql_dict (no param support)
            if params:
                for p in params:
                    if isinstance(p, str):
                        query = query.replace('?', f"'{p}'", 1)
                    else:
                        query = query.replace('?', str(p), 1)
            return self._execute_base(query)
        else:
            # Use parameterized query
            if params:
                return self._execute_base(query, params)
            else:
                return self._execute_base(query)

    def find_lock_usage(
        self,
        lock_type: Optional[str] = None,
        function_name: Optional[str] = None,
        limit: int = 100
    ) -> List[LockUsage]:
        """
        Find lock acquisition and release patterns in the codebase.

        Args:
            lock_type: Filter by lock type (lwlock, spinlock, regular_lock, etc.)
            function_name: Filter by specific function
            limit: Maximum results to return

        Returns:
            List of LockUsage objects

        Example:
            usages = analyzer.find_lock_usage(lock_type='lwlock')
            # Returns all LWLock acquisitions and releases
        """
        # Build list of lock function names to search for
        lock_functions = []

        if lock_type:
            patterns = self.LOCK_PATTERNS.get(lock_type, {})
            for operation, funcs in patterns.items():
                lock_functions.extend(funcs)
        else:
            # Search all lock types
            for patterns in self.LOCK_PATTERNS.values():
                for funcs in patterns.values():
                    lock_functions.extend(funcs)

        if not lock_functions:
            return []

        # Build SQL query
        func_patterns = ' OR '.join([f"nc.name LIKE '%{f}%'" for f in lock_functions])

        query = f"""
            SELECT DISTINCT
                m.name AS caller_function,
                nc.name AS lock_function,
                m.filename,
                nc.line_number
            FROM nodes_call nc
            JOIN nodes_method m ON nc.method_full_name = m.full_name
            WHERE ({func_patterns})
        """

        if function_name:
            query += f" AND m.name = ?"
            params = (function_name,)
        else:
            params = ()

        query += f" ORDER BY m.filename, nc.line_number LIMIT {limit}"

        try:
            results = self._run_query(query, params)

            usages = []
            for row in results:
                lock_func = row.get('lock_function', '')

                # Determine lock type and operation
                detected_type = 'unknown'
                detected_op = 'unknown'

                for ltype, patterns in self.LOCK_PATTERNS.items():
                    for op, funcs in patterns.items():
                        if any(f in lock_func for f in funcs):
                            detected_type = ltype
                            detected_op = op
                            break

                usages.append(LockUsage(
                    function_name=row.get('caller_function', ''),
                    lock_type=detected_type,
                    lock_name=None,  # Would need deeper analysis
                    operation=detected_op,
                    file_name=row.get('filename', ''),
                    line_number=row.get('line_number', 0)
                ))

            logger.info(f"Found {len(usages)} lock usages")
            return usages

        except Exception as e:
            logger.error(f"Error finding lock usage: {e}")
            return []

    def detect_race_conditions(
        self,
        pattern_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[RaceConditionPattern]:
        """
        Detect potential race condition patterns.

        Pattern Types:
        - toctou: Time-of-check to time-of-use (stat/open, access/open)
        - unprotected_access: Shared access without locking
        - signal_handler: Unsafe signal handler operations
        - double_check: Double-checked locking anti-pattern

        Args:
            pattern_types: List of patterns to check (None = all)
            limit: Maximum results

        Returns:
            List of RaceConditionPattern objects
        """
        patterns = []

        # Check each pattern type
        if not pattern_types or 'toctou' in pattern_types:
            patterns.extend(self._detect_toctou_patterns(limit))

        if not pattern_types or 'signal_handler' in pattern_types:
            patterns.extend(self._detect_signal_handler_issues(limit))

        if not pattern_types or 'unprotected_access' in pattern_types:
            patterns.extend(self._detect_unprotected_shared_access(limit))

        logger.info(f"Detected {len(patterns)} potential race condition patterns")
        return patterns[:limit]

    def _detect_toctou_patterns(self, limit: int) -> List[RaceConditionPattern]:
        """Detect Time-of-Check to Time-of-Use patterns"""
        # Find functions that call both check and use operations
        # Pattern: stat/lstat followed by open, access followed by open

        query = """
            SELECT DISTINCT
                m.name AS function_name,
                m.filename
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE (
                nc.name LIKE '%stat%'
                OR nc.name LIKE '%access%'
                OR nc.name LIKE '%open%'
                OR nc.name LIKE '%unlink%'
            )
            GROUP BY m.name, m.filename
            HAVING COUNT(DISTINCT nc.name) >= 2
            LIMIT ?
        """

        patterns = []
        try:
            results = self._run_query(query, (limit * 2,))

            for idx, row in enumerate(results[:limit]):
                patterns.append(RaceConditionPattern(
                    pattern_id=f"TOCTOU_{idx:03d}",
                    pattern_type='toctou',
                    affected_functions=[row.get('function_name', '')],
                    shared_resource='file_system',
                    severity='medium',
                    description=f"Potential TOCTOU in {row.get('function_name')} - "
                               f"check and use operations on file system"
                ))
        except Exception as e:
            logger.error(f"Error detecting TOCTOU: {e}")

        return patterns

    def _detect_signal_handler_issues(self, limit: int) -> List[RaceConditionPattern]:
        """Detect potentially unsafe signal handler operations"""
        # Find signal handlers that call non-async-safe functions

        unsafe_functions = ['malloc', 'free', 'printf', 'ereport', 'elog']

        query = """
            SELECT DISTINCT
                m.name AS function_name,
                m.filename,
                nc.name AS called_function
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE (
                m.name LIKE '%handler%'
                OR m.name LIKE '%signal%'
                OR m.name LIKE '%die%'
                OR m.name LIKE '%quickdie%'
            )
            LIMIT ?
        """

        patterns = []
        try:
            results = self._run_query(query, (limit * 3,))

            seen_handlers = set()
            for row in results:
                handler = row.get('function_name', '')
                if handler in seen_handlers:
                    continue
                seen_handlers.add(handler)

                called = row.get('called_function', '')
                is_unsafe = any(uf in called.lower() for uf in unsafe_functions)

                if is_unsafe:
                    patterns.append(RaceConditionPattern(
                        pattern_id=f"SIGNAL_{len(patterns):03d}",
                        pattern_type='signal_handler',
                        affected_functions=[handler],
                        shared_resource='async_signal_safety',
                        severity='high' if 'malloc' in called or 'free' in called else 'medium',
                        description=f"Signal handler {handler} may call non-async-safe function"
                    ))

                if len(patterns) >= limit:
                    break

        except Exception as e:
            logger.error(f"Error detecting signal handler issues: {e}")

        return patterns

    def _detect_unprotected_shared_access(self, limit: int) -> List[RaceConditionPattern]:
        """Detect shared memory access without apparent locking"""
        # Find functions accessing shared memory without calling lock functions

        query = """
            WITH shared_accessors AS (
                SELECT DISTINCT m.name AS function_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.method_full_name = m.full_name
                WHERE nc.name IN ('ShmemAlloc', 'ShmemInitStruct', 'dsm_segment_address')
            ),
            lock_callers AS (
                SELECT DISTINCT m.name AS function_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.method_full_name = m.full_name
                WHERE nc.name LIKE '%Lock%Acquire%'
                   OR nc.name LIKE '%SpinLock%'
            )
            SELECT sa.function_name
            FROM shared_accessors sa
            LEFT JOIN lock_callers lc ON sa.function_name = lc.function_name
            WHERE lc.function_name IS NULL
            LIMIT ?
        """

        patterns = []
        try:
            results = self._run_query(query, (limit,))

            for idx, row in enumerate(results):
                patterns.append(RaceConditionPattern(
                    pattern_id=f"UNPROTECTED_{idx:03d}",
                    pattern_type='unprotected_access',
                    affected_functions=[row.get('function_name', '')],
                    shared_resource='shared_memory',
                    severity='medium',
                    description=f"Function {row.get('function_name')} accesses shared memory "
                               f"without apparent lock acquisition"
                ))

        except Exception as e:
            logger.error(f"Error detecting unprotected access: {e}")

        return patterns

    def analyze_shared_access(
        self,
        variable_pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[SharedAccess]:
        """
        Analyze shared memory/variable access patterns.

        Args:
            variable_pattern: Filter by variable name pattern
            limit: Maximum results

        Returns:
            List of SharedAccess objects
        """
        # Find global/shared variables and their accessors
        query = """
            SELECT DISTINCT
                m.name AS function_name,
                nc.name AS access_function
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE nc.name LIKE '%Shmem%'
               OR nc.name LIKE '%dsm_%'
               OR nc.name LIKE '%shm_mq%'
               OR nc.name LIKE '%pg_atomic%'
            LIMIT ?
        """

        try:
            results = self._run_query(query, (limit * 2,))

            # Group by access type
            access_map = defaultdict(set)
            for row in results:
                access_func = row.get('access_function', '')
                caller = row.get('function_name', '')
                access_map[access_func].add(caller)

            shared_accesses = []
            for access_func, callers in access_map.items():
                # Determine if atomic (protected)
                is_atomic = 'atomic' in access_func.lower()

                shared_accesses.append(SharedAccess(
                    variable_name=access_func,
                    accessor_functions=list(callers),
                    access_type='read_write',
                    is_protected=is_atomic,
                    protecting_lock='atomic' if is_atomic else None
                ))

            logger.info(f"Found {len(shared_accesses)} shared access patterns")
            return shared_accesses[:limit]

        except Exception as e:
            logger.error(f"Error analyzing shared access: {e}")
            return []

    def detect_lock_ordering_issues(self, limit: int = 20) -> List[LockOrderViolation]:
        """
        Detect potential lock ordering issues (deadlock risks).

        Finds cases where:
        - Function A acquires Lock1 then Lock2
        - Function B acquires Lock2 then Lock1

        This is a classic deadlock pattern.

        Args:
            limit: Maximum violations to return

        Returns:
            List of LockOrderViolation objects
        """
        # Find functions that acquire multiple locks
        query = """
            SELECT
                m.name AS function_name,
                nc.name AS lock_call,
                nc.line_number
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE nc.name LIKE '%LockAcquire%'
               OR nc.name LIKE '%LWLockAcquire%'
            ORDER BY m.name, nc.line_number
        """

        try:
            results = self._run_query(query)

            # Group lock calls by function
            func_locks = defaultdict(list)
            for row in results:
                func = row.get('function_name', '')
                lock = row.get('lock_call', '')
                line = row.get('line_number', 0)
                func_locks[func].append((lock, line))

            # Find functions with multiple lock acquisitions
            violations = []
            multi_lock_funcs = {f: locks for f, locks in func_locks.items() if len(locks) >= 2}

            # Check for ordering conflicts (simplified - would need deeper analysis for real conflicts)
            for func, locks in multi_lock_funcs.items():
                if len(locks) >= 2:
                    lock_types = [l[0] for l in locks]
                    has_lwlock = any('LWLock' in l for l in lock_types)
                    has_regular = any('LockAcquire' in l for l in lock_types)

                    if has_lwlock and has_regular:
                        violations.append(LockOrderViolation(
                            violation_id=f"ORDER_{len(violations):03d}",
                            lock_a='LWLock',
                            lock_b='RegularLock',
                            function_acquiring_a_then_b=func,
                            function_acquiring_b_then_a='unknown',
                            risk_level='medium'
                        ))

                if len(violations) >= limit:
                    break

            logger.info(f"Found {len(violations)} potential lock ordering issues")
            return violations

        except Exception as e:
            logger.error(f"Error detecting lock ordering: {e}")
            return []

    def find_atomic_operations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find atomic operations and memory barriers.

        Returns:
            List of {function_name, operation_type, atomic_func, file_name}
        """
        atomic_funcs = []
        for op_type, funcs in self.LOCK_PATTERNS['atomic'].items():
            atomic_funcs.extend([(f, op_type) for f in funcs])

        func_patterns = ' OR '.join([f"nc.name LIKE '%{f}%'" for f, _ in atomic_funcs])

        query = f"""
            SELECT DISTINCT
                m.name AS function_name,
                nc.name AS atomic_func,
                m.filename
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE ({func_patterns})
            LIMIT ?
        """

        try:
            results = self._run_query(query, (limit,))

            atomic_ops = []
            for row in results:
                atomic_func = row.get('atomic_func', '')
                op_type = 'unknown'

                for func, op in atomic_funcs:
                    if func in atomic_func:
                        op_type = op
                        break

                atomic_ops.append({
                    'function_name': row.get('function_name', ''),
                    'operation_type': op_type,
                    'atomic_func': atomic_func,
                    'file_name': row.get('filename', '')
                })

            logger.info(f"Found {len(atomic_ops)} atomic operations")
            return atomic_ops

        except Exception as e:
            logger.error(f"Error finding atomic operations: {e}")
            return []

    def find_condition_variables(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find condition variable usage patterns.

        Returns:
            List of {function_name, cv_operation, file_name}
        """
        cv_funcs = []
        for op_type, funcs in self.LOCK_PATTERNS['condvar'].items():
            cv_funcs.extend([(f, op_type) for f in funcs])

        func_patterns = ' OR '.join([f"nc.name LIKE '%{f}%'" for f, _ in cv_funcs])

        query = f"""
            SELECT DISTINCT
                m.name AS function_name,
                nc.name AS cv_func,
                m.filename
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE ({func_patterns})
            LIMIT ?
        """

        try:
            results = self._run_query(query, (limit,))

            cv_usages = []
            for row in results:
                cv_func = row.get('cv_func', '')
                op_type = 'wait' if 'Sleep' in cv_func or 'Prepare' in cv_func else 'signal'

                cv_usages.append({
                    'function_name': row.get('function_name', ''),
                    'cv_operation': op_type,
                    'cv_func': cv_func,
                    'file_name': row.get('filename', '')
                })

            logger.info(f"Found {len(cv_usages)} condition variable usages")
            return cv_usages

        except Exception as e:
            logger.error(f"Error finding condition variables: {e}")
            return []

    def find_latch_usage(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find latch synchronization usage.

        Returns:
            List of {function_name, latch_operation, file_name}
        """
        latch_funcs = []
        for op_type, funcs in self.LOCK_PATTERNS['latch'].items():
            latch_funcs.extend([(f, op_type) for f in funcs])

        func_patterns = ' OR '.join([f"nc.name LIKE '%{f}%'" for f, _ in latch_funcs])

        query = f"""
            SELECT DISTINCT
                m.name AS function_name,
                nc.name AS latch_func,
                m.filename
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE ({func_patterns})
            LIMIT ?
        """

        try:
            results = self._run_query(query, (limit,))

            latch_usages = []
            for row in results:
                latch_func = row.get('latch_func', '')
                op_type = 'wait' if 'Wait' in latch_func else 'signal'

                latch_usages.append({
                    'function_name': row.get('function_name', ''),
                    'latch_operation': op_type,
                    'latch_func': latch_func,
                    'file_name': row.get('filename', '')
                })

            logger.info(f"Found {len(latch_usages)} latch usages")
            return latch_usages

        except Exception as e:
            logger.error(f"Error finding latch usage: {e}")
            return []

    def get_concurrency_statistics(self) -> Dict[str, Any]:
        """
        Get overall concurrency-related statistics.

        Returns:
            Dictionary with concurrency metrics
        """
        stats_query = """
            SELECT
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%LWLock%') AS lwlock_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%SpinLock%') AS spinlock_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%LockAcquire%') AS lock_acquire_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%pg_atomic%') AS atomic_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%ConditionVariable%') AS condvar_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%Latch%') AS latch_calls,
                (SELECT COUNT(*) FROM nodes_call WHERE name LIKE '%Shmem%') AS shmem_calls,
                (SELECT COUNT(DISTINCT m.name) FROM nodes_method m
                 JOIN nodes_call nc ON nc.method_full_name = m.full_name
                 WHERE nc.name LIKE '%Lock%') AS functions_using_locks
        """

        try:
            results = self._run_query(stats_query)

            if results:
                stats = results[0]
                return {
                    'lwlock_calls': stats.get('lwlock_calls', 0),
                    'spinlock_calls': stats.get('spinlock_calls', 0),
                    'lock_acquire_calls': stats.get('lock_acquire_calls', 0),
                    'atomic_calls': stats.get('atomic_calls', 0),
                    'condvar_calls': stats.get('condvar_calls', 0),
                    'latch_calls': stats.get('latch_calls', 0),
                    'shmem_calls': stats.get('shmem_calls', 0),
                    'functions_using_locks': stats.get('functions_using_locks', 0),
                }

            return {}

        except Exception as e:
            logger.error(f"Error getting concurrency statistics: {e}")
            return {}

    def analyze_function_concurrency(self, function_name: str) -> Dict[str, Any]:
        """
        Analyze concurrency characteristics of a specific function.

        Args:
            function_name: Name of function to analyze

        Returns:
            Dictionary with concurrency analysis results
        """
        query = """
            SELECT nc.name AS call_name
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE m.name = ?
        """

        try:
            results = self._run_query(query, (function_name,))

            calls = [r.get('call_name', '') for r in results]

            # Categorize calls
            analysis = {
                'function_name': function_name,
                'uses_lwlock': any('LWLock' in c for c in calls),
                'uses_spinlock': any('SpinLock' in c for c in calls),
                'uses_regular_lock': any('LockAcquire' in c for c in calls),
                'uses_atomics': any('pg_atomic' in c for c in calls),
                'uses_condvar': any('ConditionVariable' in c for c in calls),
                'uses_latch': any('Latch' in c for c in calls),
                'accesses_shmem': any('Shmem' in c or 'dsm_' in c for c in calls),
                'lock_related_calls': [c for c in calls if 'Lock' in c or 'atomic' in c.lower()],
                'total_sync_calls': len([c for c in calls if any(p in c for p in
                    ['Lock', 'Shmem', 'atomic', 'Latch', 'Condition'])])
            }

            # Risk assessment
            if analysis['accesses_shmem'] and not any([
                analysis['uses_lwlock'],
                analysis['uses_spinlock'],
                analysis['uses_regular_lock'],
                analysis['uses_atomics']
            ]):
                analysis['risk_level'] = 'high'
                analysis['risk_reason'] = 'Shared memory access without apparent synchronization'
            elif analysis['uses_spinlock']:
                analysis['risk_level'] = 'medium'
                analysis['risk_reason'] = 'Uses spinlocks (busy-wait)'
            else:
                analysis['risk_level'] = 'low'
                analysis['risk_reason'] = 'Appears properly synchronized'

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing function concurrency: {e}")
            return {'function_name': function_name, 'error': str(e)}

    def analyze_lock_pairing(
        self,
        function_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Analyze if lock acquire/release calls are properly paired.

        Detects potential lock leaks where a function acquires a lock
        but may not release it (missing release, early return, exception path).

        Args:
            function_name: Optional specific function to analyze
            limit: Maximum results to return

        Returns:
            List of functions with potential lock pairing issues
        """
        # Find all lock acquire and release calls per function
        query = """
            SELECT
                m.name AS function_name,
                m.filename,
                nc.name AS lock_call,
                nc.line_number,
                CASE
                    WHEN nc.name LIKE '%Acquire%' OR nc.name LIKE '%Lock%'
                         OR nc.name = 'PGSemaphoreLock'
                         OR nc.name LIKE '%pthread_mutex_lock%'
                    THEN 'acquire'
                    WHEN nc.name LIKE '%Release%' OR nc.name LIKE '%Unlock%'
                         OR nc.name = 'PGSemaphoreUnlock'
                         OR nc.name LIKE '%pthread_mutex_unlock%'
                    THEN 'release'
                    ELSE 'other'
                END AS lock_type
            FROM nodes_method m
            JOIN nodes_call nc ON nc.method_full_name = m.full_name
            WHERE (
                nc.name LIKE '%LWLock%'
                OR nc.name LIKE '%SpinLock%'
                OR nc.name LIKE '%LockAcquire%'
                OR nc.name LIKE '%LockRelease%'
                OR nc.name LIKE '%Semaphore%'
                OR nc.name LIKE '%pthread_mutex%'
                OR nc.name LIKE '%pthread_rwlock%'
            )
        """

        if function_name:
            query += f" AND m.name = '{function_name}'"

        query += " ORDER BY m.name, nc.line_number"

        try:
            results = self._run_query(query)

            # Group by function and count acquire vs release
            func_analysis = defaultdict(lambda: {
                'acquires': 0,
                'releases': 0,
                'acquire_calls': [],
                'release_calls': [],
                'filename': ''
            })

            for row in results:
                func = row.get('function_name', '')
                lock_type = row.get('lock_type', 'other')
                lock_call = row.get('lock_call', '')

                if lock_type == 'acquire':
                    func_analysis[func]['acquires'] += 1
                    func_analysis[func]['acquire_calls'].append(lock_call)
                elif lock_type == 'release':
                    func_analysis[func]['releases'] += 1
                    func_analysis[func]['release_calls'].append(lock_call)

                if not func_analysis[func]['filename']:
                    func_analysis[func]['filename'] = row.get('filename', '')

            # Find functions with potential issues
            issues = []
            for func, data in func_analysis.items():
                acquires = data['acquires']
                releases = data['releases']

                # Potential lock leak: more acquires than releases
                if acquires > releases:
                    issues.append({
                        'function_name': func,
                        'filename': data['filename'],
                        'acquires': acquires,
                        'releases': releases,
                        'potential_leak': True,
                        'missing_releases': acquires - releases,
                        'acquire_calls': data['acquire_calls'][:5],
                        'release_calls': data['release_calls'][:5],
                        'issue_type': 'potential_lock_leak',
                        'severity': 'high' if (acquires - releases) > 1 else 'medium'
                    })
                # Could also have release without acquire (less common)
                elif releases > acquires and acquires == 0:
                    issues.append({
                        'function_name': func,
                        'filename': data['filename'],
                        'acquires': acquires,
                        'releases': releases,
                        'potential_leak': False,
                        'missing_releases': 0,
                        'acquire_calls': data['acquire_calls'][:5],
                        'release_calls': data['release_calls'][:5],
                        'issue_type': 'release_without_acquire',
                        'severity': 'low'
                    })

            # Sort by severity
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            issues.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 2))

            logger.info(f"Found {len(issues)} potential lock pairing issues")
            return issues[:limit]

        except Exception as e:
            logger.error(f"Error analyzing lock pairing: {e}")
            return []

    def detect_toctou_detailed(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Detect Time-of-Check to Time-of-Use vulnerabilities with more detail.

        Patterns detected:
        - stat/lstat/fstat followed by open/fopen/unlink/rename
        - access() followed by open()
        - Check + use without locking

        Args:
            limit: Maximum results to return

        Returns:
            List of TOCTOU vulnerability details
        """
        query = """
            SELECT DISTINCT
                m.id AS method_id,
                m.name AS function_name,
                m.filename,
                m.line_number AS func_start,
                check_call.name AS check_func,
                check_call.line_number AS check_line,
                use_call.name AS use_func,
                use_call.line_number AS use_line
            FROM nodes_method m
            JOIN nodes_call check_call ON check_call.method_full_name = m.full_name
            JOIN nodes_call use_call ON use_call.method_full_name = m.full_name
            WHERE check_call.name IN ('access', 'stat', 'lstat', 'fstat', 'PathIsValid', 'FileExists')
              AND use_call.name IN ('open', 'fopen', 'unlink', 'rename', 'remove', 'mkdir', 'rmdir')
              AND use_call.line_number > check_call.line_number
              AND (use_call.line_number - check_call.line_number) < 30
            ORDER BY m.filename, m.line_number
            LIMIT ?
        """

        try:
            results = self._run_query(query, (limit * 2,))

            vulnerabilities = []
            seen = set()

            for row in results:
                func = row.get('function_name', '')
                check_func = row.get('check_func', '')
                use_func = row.get('use_func', '')

                # Deduplicate
                key = (func, check_func, use_func)
                if key in seen:
                    continue
                seen.add(key)

                check_line = row.get('check_line', 0)
                use_line = row.get('use_line', 0)
                gap = use_line - check_line if use_line and check_line else 0

                vulnerabilities.append({
                    'function_name': func,
                    'filename': row.get('filename', ''),
                    'check_function': check_func,
                    'check_line': check_line,
                    'use_function': use_func,
                    'use_line': use_line,
                    'line_gap': gap,
                    'vulnerability_type': 'TOCTOU',
                    'severity': 'high' if gap <= 5 else 'medium',
                    'description': f"Check ({check_func}) at line {check_line} followed by "
                                   f"use ({use_func}) at line {use_line} without synchronization"
                })

                if len(vulnerabilities) >= limit:
                    break

            logger.info(f"Found {len(vulnerabilities)} potential TOCTOU vulnerabilities")
            return vulnerabilities

        except Exception as e:
            logger.error(f"Error detecting TOCTOU: {e}")
            return []

    def get_lock_statistics_by_type(self) -> Dict[str, Dict[str, int]]:
        """
        Get detailed lock usage statistics grouped by lock type.

        Returns:
            Dictionary with lock type -> {acquires, releases, functions_using}
        """
        query = """
            SELECT
                CASE
                    WHEN nc.name LIKE '%LWLock%' THEN 'LWLock'
                    WHEN nc.name LIKE '%SpinLock%' THEN 'SpinLock'
                    WHEN nc.name LIKE '%pg_advisory%' THEN 'AdvisoryLock'
                    WHEN nc.name LIKE '%Semaphore%' THEN 'Semaphore'
                    WHEN nc.name LIKE '%pthread_mutex%' THEN 'PthreadMutex'
                    WHEN nc.name LIKE '%pthread_rwlock%' THEN 'PthreadRWLock'
                    WHEN nc.name LIKE '%LockBuffer%' THEN 'BufferLock'
                    WHEN nc.name LIKE '%LockRelation%' OR nc.name LIKE '%UnlockRelation%' THEN 'RelationLock'
                    WHEN nc.name LIKE '%LockAcquire%' OR nc.name LIKE '%LockRelease%' THEN 'HeavyweightLock'
                    ELSE 'Other'
                END AS lock_category,
                CASE
                    WHEN nc.name LIKE '%Acquire%' OR nc.name LIKE '%Lock%' THEN 'acquire'
                    WHEN nc.name LIKE '%Release%' OR nc.name LIKE '%Unlock%' THEN 'release'
                    ELSE 'other'
                END AS operation,
                COUNT(*) AS call_count,
                COUNT(DISTINCT m.name) AS function_count
            FROM nodes_call nc
            JOIN nodes_method m ON nc.method_full_name = m.full_name
            WHERE (
                nc.name LIKE '%Lock%'
                OR nc.name LIKE '%Unlock%'
                OR nc.name LIKE '%Semaphore%'
                OR nc.name LIKE '%pthread_mutex%'
                OR nc.name LIKE '%pthread_rwlock%'
            )
            GROUP BY lock_category, operation
            ORDER BY lock_category, operation
        """

        try:
            results = self._run_query(query)

            stats = defaultdict(lambda: {'acquires': 0, 'releases': 0, 'other': 0, 'functions': 0})

            for row in results:
                category = row.get('lock_category', 'Other')
                operation = row.get('operation', 'other')
                count = row.get('call_count', 0)
                func_count = row.get('function_count', 0)

                if operation == 'acquire':
                    stats[category]['acquires'] += count
                elif operation == 'release':
                    stats[category]['releases'] += count
                else:
                    stats[category]['other'] += count

                stats[category]['functions'] = max(stats[category]['functions'], func_count)

            logger.info(f"Computed lock statistics for {len(stats)} lock categories")
            return dict(stats)

        except Exception as e:
            logger.error(f"Error getting lock statistics: {e}")
            return {}
