"""
Enrichment Agent - Tag Mappings

Contains the comprehensive tag mappings for the 12-layer CPG enrichment system.
Extracted from enrichment_agent.py for maintainability.
"""

from typing import Dict, List, Any


def build_tag_mappings() -> Dict[str, Dict[str, List[str]]]:
    """
    Build comprehensive tag mappings.

    Maps domains/keywords to enrichment tags for the 12-layer
    CPG enrichment system.

    Returns:
        Dictionary mapping tag categories to domain-value mappings.
    """
    return {
        # REMOVED: 'subsystem' - not a valid CPG tag category
        # REMOVED: 'api_category' - not a valid CPG tag category

        # ==================================================================
        # CATEGORY 1: PARAMETER & RETURN SEMANTIC INTEGRATION
        # ==================================================================
        # Coverage: 84,037 parameters (39% with role), 37,087 returns (78% with kind)

        'param_role': {
            # Maps domains to relevant parameter roles (Phase 2: Enhanced)
            'vacuum': ['buffer', 'relation', 'snapshot', 'heap-page', 'state-pointer'],
            'wal': ['buffer', 'wal-record', 'transaction-context', 'lsn', 'state-pointer'],
            'mvcc': ['snapshot', 'transaction-context', 'visibility-map', 'transaction-id', 'buffer'],
            'memory': ['memory-context', 'buffer', 'state-pointer', 'size', 'allocation-size'],
            'replication': ['buffer', 'wal-record', 'transaction-context', 'slot', 'lsn', 'state-pointer', 'snapshot'],
            'indexes': ['buffer', 'relation', 'index-page', 'scan-key', 'tuple', 'iterator'],
            'locking': ['lock-mode', 'buffer', 'relation', 'lock-id', 'wait-queue'],
            'parallel': ['state-pointer', 'buffer', 'iterator', 'worker-id', 'shared-state'],
            'query-planning': ['relation', 'iterator', 'state-pointer', 'cost-estimate', 'statistics'],
            'catalog': ['relation', 'catalog-cache', 'buffer', 'object-id', 'metadata'],
            'executor': ['state-pointer', 'tuple', 'scan-state', 'relation', 'buffer'],
            'storage': ['buffer', 'relation', 'block-number', 'page-header', 'tuple'],
            'error-handling': ['error-code', 'state-pointer', 'message', 'context'],
            'networking': ['connection', 'buffer', 'socket', 'state-pointer'],
            'timestamp': ['timestamp', 'timezone', 'interval', 'precision'],
        },

        'return_kind': {
            # Maps domains to common return types
            'vacuum': ['status-code', 'error-code', 'boolean'],
            'wal': ['status-code', 'pointer', 'error-code'],
            'mvcc': ['boolean', 'snapshot', 'status-code'],
            'memory': ['allocated-pointer', 'status-code', 'error-code'],
            'indexes': ['status-code', 'iterator', 'boolean'],
            'locking': ['boolean', 'status-code', 'lock-mode'],
            'parallel': ['status-code', 'boolean', 'iterator'],
            'error-handling': ['error-code', 'status-code', 'boolean'],
        },

        'return_outcome': {
            # Maps intents to return outcomes
            'error-handling': ['failure', 'partial-success', 'retry'],
            'validation': ['success', 'failure'],
            'recovery': ['retry', 'partial-success', 'not-applicable'],
        },

        'validation_required': {
            # Maps security/validation contexts to validation types
            'security': ['security-check', 'sanitise'],
            'input-validation': ['null-check', 'bounds-check', 'sanitise'],
            'memory': ['null-check', 'bounds-check'],
            'buffer': ['bounds-check', 'null-check'],
        },

        # ==================================================================
        # CATEGORY 2: VARIABLE & IDENTIFIER SEMANTIC ENHANCEMENT
        # ==================================================================
        # Coverage: 847,669 identifiers, 193,442 locals

        'variable_role': {
            # Maps domains to variable roles
            'memory': ['buffer-manager', 'context-pointer', 'temporary'],
            'wal': ['buffer-manager', 'state', 'iterator'],
            'mvcc': ['snapshot', 'state', 'transaction-id'],
            'parallel': ['iterator', 'counter', 'state'],
            'locking': ['lock', 'flag', 'state'],
            'indexes': ['iterator', 'buffer-manager', 'state'],
            'query-planning': ['iterator', 'state', 'temporary'],
        },

        'data_kind': {
            # Maps domains to data kinds
            'vacuum': ['relation', 'buffer', 'tuple'],
            'wal': ['wal-pointer', 'lsn', 'buffer'],
            'mvcc': ['transaction-id', 'snapshot', 'tuple'],
            'memory': ['buffer', 'relation'],
            'replication': ['wal-pointer', 'lsn', 'snapshot'],
            'indexes': ['relation', 'buffer', 'tuple'],
            'locking': ['lock', 'buffer', 'relation'],
            'parallel': ['query', 'relation', 'buffer'],
            'query-planning': ['query', 'relation'],
        },

        'security_sensitivity': {
            # Security-sensitive variable types
            'security': ['credential', 'auth-token', 'secret'],
            'authentication': ['credential', 'auth-token'],
            'encryption': ['secret', 'auth-token'],
        },

        'lifetime': {
            # Variable lifetime mappings
            'memory': ['auto', 'static'],
            'global': ['static'],
            'local': ['auto'],
        },

        'mutability': {
            # Variable mutability
            'const': ['immutable'],
            'mutable': ['mutable'],
        },

        'is_lock': {
            # Lock-related variable indicators
            'locking': ['true'],
            'parallel': ['true'],
            'executor': ['true'],
        },

        'is_pointer_to_struct': {
            # Pointer-heavy domains
            'memory': ['true'],
            'storage': ['true'],
            'indexes': ['true'],
        },

        # ==================================================================
        # CATEGORY 3: TYPE & MEMBER SEMANTIC CLASSIFICATION
        # ==================================================================

        'type_category': {
            # Maps domains to type classifications
            'memory': ['struct', 'typedef'],
            'storage': ['struct', 'union'],
            'indexes': ['struct', 'enum'],
            'locking': ['struct', 'enum'],
            'query-planning': ['struct', 'typedef'],
        },

        'type_domain_entity': {
            # Maps domains to domain-oriented type entities
            'storage': ['relation', 'heap-tuple'],
            'indexes': ['index'],
            'mvcc': ['heap-tuple'],
            'wal': ['wal-record'],
            'catalog': ['catalog-entry'],
            'executor': ['executor-state'],
        },

        'type_concurrency_primitive': {
            # Domains with concurrency primitive types
            'locking': ['lwlock', 'spinlock', 'semaphore'],
            'parallel': ['mutex', 'condition-variable'],
            'executor': ['lwlock', 'mutex'],
        },

        'type_ownership_model': {
            # Ownership semantics relevant to domains
            'memory': ['reference-counted', 'arena-managed'],
            'storage': ['pinned-buffer', 'copy-on-write'],
            'mvcc': ['copy-on-write', 'reference-counted'],
        },

        'member_role': {
            # Member-level semantics
            'storage': ['data', 'state'],
            'indexes': ['metadata', 'reference'],
            'memory': ['state', 'count'],
            'locking': ['flag', 'state'],
        },

        'member_pointer': {
            # Pointer-heavy member indicators
            'storage': ['true'],
            'indexes': ['true'],
            'memory': ['true'],
        },

        'member_length_field': {
            # Length/size field markers
            'storage': ['true'],
            'memory': ['true'],
            'executor': ['true'],
            'indexes': ['true'],
        },

        # ==================================================================
        # CATEGORY 4: LITERAL & CONSTANT SEMANTIC UNDERSTANDING
        # ==================================================================

        'literal_kind': {
            'error-handling': ['error-code', 'special-value'],
            'locking': ['bit-mask', 'boolean-flag'],
            'memory': ['magic-number', 'null-constant', 'size-constant'],
            'storage': ['size-constant', 'path-string'],
            'transaction': ['timeout', 'error-code'],
        },

        'literal_domain': {
            'transaction': ['transaction', 'visibility'],
            'storage': ['buffer', 'lock'],
            'locking': ['lock'],
            'memory': ['buffer', 'error'],
            'error-handling': ['error'],
        },

        'literal_severity': {
            'error-handling': ['error', 'warning', 'notice'],
            'logging': ['warning', 'notice'],
        },

        'is_null_constant': {
            'memory': ['true'],
            'storage': ['true'],
            'executor': ['true'],
        },

        'is_bitmask': {
            'locking': ['true'],
            'storage': ['true'],
        },

        'literal_constant': {
            'error-handling': ['ERRCODE_SYNTAX_ERROR', 'ERRCODE_INTERNAL_ERROR'],
            'locking': ['LOCKTAG_RELATION', 'LOCKTAG_ADVISORY'],
            'storage': ['InvalidBlockNumber', 'MAIN_FORKNUM'],
        },

        'is_lock_constant': {
            'locking': ['true'],
            'executor': ['true'],
        },

        # ==================================================================
        # CATEGORY 6: NAMESPACE & REFERENCE SEMANTIC CONTEXT
        # ==================================================================
        'namespace_layer': {
            'planner': ['planner'],
            'executor': ['executor'],
            'storage': ['storage'],
            'catalog': ['catalog'],
            'buffer': ['buffer'],
            'replication': ['replication'],
        },

        'namespace_domain': {
            'plugins': ['extension'],
            'client': ['client'],
            'server': ['server'],
            'tools': ['tools'],
            'configuration': ['configuration'],
        },

        'method_ref_kind': {
            'executor': ['callback', 'function-pointer'],
            'planner': ['virtual-dispatch'],
            'storage': ['callback'],
        },

        'method_ref_usage': {
            'executor': ['initializer', 'cleanup'],
            'planner': ['predicate', 'comparator'],
            'storage': ['allocator'],
        },

        # ==================================================================
        # CATEGORY 7: DATA FLOW & EDGE SEMANTIC ENRICHMENT
        # ==================================================================
        'data_flow_kind': {
            'locking': ['lock-propagation'],
            'executor': ['result-flow'],
            'storage': ['buffer-flow'],
            'planner': ['cost-flow'],
            'transaction': ['transaction-flow'],
        },

        'child_role': {
            'executor': ['condition', 'body'],
            'planner': ['condition', 'return'],
            'storage': ['body'],
        },

        'call_action': {
            'executor': ['dispatch', 'initialize'],
            'locking': ['acquire', 'release'],
            'storage': ['read', 'write'],
        },

        'call_side_effect': {
            'executor': ['state-change'],
            'locking': ['lock-state'],
            'storage': ['io'],
        },

        'call_receiver_role': {
            'executor': ['handler'],
            'planner': ['strategy'],
            'storage': ['buffer-manager'],
        },

        'argument_param_name': {
            'executor': ['callback', 'state'],
            'planner': ['predicate', 'context'],
            'storage': ['buffer', 'blockNumber'],
        },

        'branch_kind': {
            'executor': ['error', 'cleanup'],
            'planner': ['decision'],
            'locking': ['retry'],
        },

        'control_reason': {
            'locking': ['deadlock-avoidance'],
            'executor': ['result-validation'],
            'storage': ['consistency-check'],
        },

        # ==================================================================
        # CATEGORY 5: CONTROL FLOW & JUMP SEMANTICS
        # ==================================================================
        'jump_kind': {
            'error-handling': ['error-handler', 'cleanup'],
            'locking': ['retry', 'loop-break'],
            'executor': ['dispatch'],
            'planner': ['loop-continue'],
            'storage': ['cleanup'],
        },

        'jump_domain': {
            'executor': ['executor'],
            'storage': ['storage'],
            'transaction': ['transaction'],
            'buffer': ['buffer'],
            'planner': ['planner'],
        },

        'jump_scope': {
            'executor': ['loop', 'function'],
            'locking': ['loop'],
            'planner': ['loop'],
            'storage': ['function'],
        },

        'modifier_concurrency': {
            'locking': ['atomic-access', 'synchronized', 'volatile-access'],
            'executor': ['thread-local', 'volatile-access'],
            'storage': ['static-volatile-global'],
        },

        'modifier_attribute': {
            'executor': ['inline', 'noinline'],
            'planner': ['constexpr'],
            'storage': ['const', 'readonly'],
        },

        # ==================================================================
        # Layer 10: Semantic Classification (function-level)
        # ==================================================================
        # IMPORTANT: Use ONLY actual CPG tag values from data/cpg_actual_tags.json
        # Real values: general, statistics, utilities, memory-management, parsing,
        #              storage-access, wal-logging, concurrency-control, catalog-access,
        #              error-handling, networking, type-system, transaction-control,
        #              query-execution, query-planning
        'function_purpose': {
            # Phase 2: Enhanced - PRIMARY tag with 100% coverage
            'vacuum': ['utilities', 'storage-access', 'memory-management'],
            'wal': ['wal-logging', 'storage-access', 'transaction-control'],
            'mvcc': ['transaction-control', 'concurrency-control', 'storage-access'],
            'query-planning': ['query-planning', 'query-execution', 'statistics'],
            'memory': ['memory-management', 'utilities', 'storage-access'],
            'replication': ['networking', 'wal-logging', 'transaction-control', 'concurrency-control'],
            'storage': ['storage-access', 'utilities', 'memory-management'],
            'indexes': ['query-execution', 'storage-access', 'query-planning'],
            'locking': ['concurrency-control', 'transaction-control', 'utilities'],
            'parallel': ['query-execution', 'utilities', 'concurrency-control'],
            'security': ['networking', 'utilities', 'error-handling'],
            'partition': ['query-planning', 'storage-access', 'query-execution'],
            'error': ['error-handling', 'utilities', 'networking'],
            'error-handling': ['error-handling', 'utilities', 'transaction-control'],
            'catalog': ['catalog-access', 'utilities', 'query-planning'],
            'executor': ['query-execution', 'query-planning', 'utilities'],
            'networking': ['networking', 'utilities', 'error-handling'],
            'timestamp': ['utilities', 'type-system', 'parsing'],
            'general': ['utilities', 'general']  # Fallback for general domain
        },

        # Real CPG values: array, relation, bitmap, hash-table, buffer, linked-list, binary-tree, queue
        'data_structure': {
            # Phase 2: Enhanced - SECONDARY tag with 20% coverage
            'vacuum': ['relation', 'buffer', 'array', 'linked-list'],
            'wal': ['buffer', 'queue', 'array', 'linked-list'],
            'mvcc': ['relation', 'buffer', 'hash-table', 'bitmap'],
            'query-planning': ['binary-tree', 'array', 'hash-table', 'relation'],
            'memory': ['array', 'linked-list', 'hash-table', 'buffer'],
            'replication': ['buffer', 'queue', 'linked-list', 'array'],
            'storage': ['relation', 'buffer', 'array', 'bitmap'],
            'indexes': ['binary-tree', 'hash-table', 'array', 'bitmap', 'relation'],
            'locking': ['hash-table', 'queue', 'array', 'linked-list'],
            'parallel': ['queue', 'array', 'hash-table', 'buffer'],
            'security': ['hash-table', 'array', 'buffer'],
            'partition': ['array', 'relation', 'binary-tree'],
            'executor': ['array', 'buffer', 'hash-table', 'binary-tree'],
            'catalog': ['hash-table', 'array', 'relation'],
            'general': ['array', 'hash-table', 'buffer']  # Fallback for general
        },

        'algorithm': {
            'vacuum': ['mark-sweep', 'reference-counting'],
            'query-planning': ['dynamic-programming', 'cost-based'],
            'indexes': ['binary-search', 'hashing'],
            'locking': ['two-phase-locking', 'deadlock-detection'],
            'parallel': ['producer-consumer', 'work-stealing']
        },

        # Real CPG values: vacuum, parallelism, extension, replication, mvcc, partitioning, foreign-data, jit
        'domain_concept': {
            # Phase 2: Enhanced - TERTIARY tag with <20% coverage
            'vacuum': ['vacuum', 'mvcc'],
            'wal': ['replication', 'mvcc'],  # WAL relates to replication and MVCC
            'mvcc': ['mvcc', 'vacuum'],
            'query-planning': ['jit', 'parallelism', 'partitioning'],
            'memory': ['mvcc'],  # Memory management relates to MVCC
            'replication': ['replication', 'mvcc'],
            'storage': ['mvcc', 'vacuum'],
            'indexes': ['mvcc', 'parallelism'],  # Indexes relate to MVCC visibility
            'locking': ['mvcc'],  # Locking is part of MVCC
            'parallel': ['parallelism', 'jit'],
            'security': ['extension'],  # Security often via extensions
            'partition': ['partitioning', 'parallelism'],
            'extension': ['extension'],
            'foreign-data': ['foreign-data', 'extension'],
            'executor': ['parallelism', 'jit'],
            'catalog': ['mvcc', 'extension'],
            'general': ['mvcc', 'extension']  # Fallback for general domain
        },

        # REMOVED: 'architectural_role' - not a valid CPG tag category

        # Layer 12: Feature Mapping
        # DISABLED: Feature tags in CPG are too specific (e.g., "Parallelized CREATE INDEX for BRIN indexes")
        # They don't match generated short names like "MVCC" or "autovacuum"
        # Better to use domain-concept tags instead
        'feature': {
            # 'vacuum': ['Vacuum "emergency mode"', 'Visibility Map for Vacuuming'],
            # 'indexes': ['Block-range (BRIN) indexes', 'In-memory Bitmap Indexes'],
            # 'parallel': ['Parallel query execution on remote databases'],
            # ... (disabled - too specific for tag generation)
        },

        # Add missing domains
        'security_concepts': {
            'security': ['authentication', 'authorization', 'encryption']
        },

        'partition_concepts': {
            'partition': ['table-partitioning', 'partition-pruning', 'partition-management']
        }
    }


__all__ = ['build_tag_mappings']
