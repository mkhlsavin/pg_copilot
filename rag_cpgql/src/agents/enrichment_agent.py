"""Enrichment Agent - Maps questions to CPG enrichment tags."""
import logging
from typing import Dict, List, Set
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Phase 4: Import fallback strategies
try:
    from src.agents.fallback_strategies import get_fallback_selector
    FALLBACK_AVAILABLE = True
except ImportError:
    logger.warning("Fallback strategies not available, Phase 4 features disabled")
    FALLBACK_AVAILABLE = False


class EnrichmentAgent:
    """
    Enrichment Agent for CPG tag mapping.

    Maps question analysis to relevant enrichment tags from the
    12-layer CPG enrichment system.
    """

    def __init__(self, enable_fallback: bool = True):
        """
        Initialize Enrichment Agent with tag mappings.

        Args:
            enable_fallback: Enable Phase 4 fallback strategies for low coverage
        """
        # Load enrichment tag mappings
        # Based on the 12 enrichment layers from IMPLEMENTATION_PLAN.md
        self.tag_mappings = self._build_tag_mappings()

        # Phase 4: Fallback strategy selector
        self.enable_fallback = enable_fallback and FALLBACK_AVAILABLE
        self.fallback_selector = get_fallback_selector() if self.enable_fallback else None

    def _build_tag_mappings(self) -> Dict:
        """
        Build comprehensive tag mappings.

        Maps domains/keywords to enrichment tags.
        """
        return {
            # REMOVED: 'subsystem' - not a valid CPG tag category
            # REMOVED: 'api_category' - not a valid CPG tag category

            # ==================================================================
            # CATEGORY 1: PARAMETER & RETURN SEMANTIC INTEGRATION
            # ==================================================================
            # Coverage: 84,037 parameters (39% with role), 37,087 returns (78% with kind)

            'param_role': {
                # Maps domains to relevant parameter roles
                'vacuum': ['buffer', 'relation', 'snapshot'],
                'wal': ['buffer', 'wal-record', 'transaction-context'],
                'mvcc': ['snapshot', 'transaction-context', 'visibility-map'],
                'memory': ['memory-context', 'buffer', 'state-pointer'],
                'replication': ['buffer', 'wal-record', 'transaction-context'],
                'indexes': ['buffer', 'relation', 'index-page'],
                'locking': ['lock-mode', 'buffer', 'relation'],
                'parallel': ['state-pointer', 'buffer', 'iterator'],
                'query-planning': ['relation', 'iterator', 'state-pointer'],
                'catalog': ['relation', 'catalog-cache', 'buffer'],
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
                'vacuum': ['utilities', 'storage-access'],
                'wal': ['wal-logging', 'storage-access'],
                'mvcc': ['transaction-control', 'concurrency-control'],
                'query-planning': ['query-planning', 'query-execution'],
                'memory': ['memory-management', 'utilities'],
                'replication': ['networking', 'wal-logging'],
                'storage': ['storage-access', 'utilities'],
                'indexes': ['query-execution', 'storage-access'],
                'locking': ['concurrency-control', 'transaction-control'],
                'parallel': ['query-execution', 'utilities'],
                'security': ['networking', 'utilities'],
                'partition': ['query-planning', 'storage-access'],
                'error': ['error-handling', 'utilities'],
                'catalog': ['catalog-access', 'utilities']
            },

            # Real CPG values: array, relation, bitmap, hash-table, buffer, linked-list, binary-tree, queue
            'data_structure': {
                'vacuum': ['relation', 'buffer'],
                'wal': ['buffer', 'queue'],
                'mvcc': ['relation', 'buffer'],
                'query-planning': ['binary-tree', 'array'],
                'memory': ['array', 'linked-list'],
                'indexes': ['binary-tree', 'hash-table', 'array'],
                'locking': ['hash-table', 'queue'],
                'parallel': ['queue', 'array'],
                'security': ['hash-table', 'array'],
                'partition': ['array', 'relation']
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
                'vacuum': ['vacuum'],
                'wal': ['vacuum'],  # No direct wal concept, use vacuum for maintenance
                'mvcc': ['mvcc'],
                'query-planning': ['jit', 'parallelism'],
                'replication': ['replication'],
                'indexes': ['mvcc'],  # Indexes relate to MVCC visibility
                'locking': ['mvcc'],  # Locking is part of MVCC
                'parallel': ['parallelism'],
                'security': ['extension'],  # Security often via extensions
                'partition': ['partitioning'],
                'extension': ['extension'],
                'foreign-data': ['foreign-data']
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

    def get_enrichment_hints(
        self,
        question: str,
        analysis: Dict
    ) -> Dict:
        """
        Get enrichment tag hints based on question analysis.

        Args:
            question: Original question
            analysis: Analysis from AnalyzerAgent

        Returns:
            Dictionary with enrichment hints (ONLY valid CPG tag categories):
            - function_purposes: Relevant function purposes (PRIMARY - 100% coverage)
            - data_structures: Relevant data structures (SECONDARY - 20% coverage)
            - algorithms: Relevant algorithms
            - domain_concepts: Relevant domain concepts (TERTIARY - <20% coverage)
            - features: Relevant PostgreSQL features (disabled - too specific)
            - tags: Suggested CPGQL tag filters
        """
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])
        intent = analysis.get('intent', 'explain-concept')

        hints = {
            # Existing categories
            'function_purposes': [],
            'data_structures': [],
            'algorithms': [],
            'domain_concepts': [],
            'features': [],
            # Category 1: Parameter & Return Semantic Integration
            'param_roles': [],
            'return_kinds': [],
            'return_outcomes': [],
            'validation_required': [],
            # Category 2: Variable & Identifier Semantic Enhancement
            'variable_roles': [],
            'data_kinds': [],
            'security_sensitivities': [],
            'lifetimes': [],
            'mutabilities': [],
            'is_locks': [],
            'is_pointer_to_structs': [],
            # Category 3: Type & Member Semantic Classification
            'type_categories': [],
            'type_domain_entities': [],
            'type_concurrency_primitives': [],
            'type_ownership_models': [],
            'member_roles': [],
            'member_pointers': [],
            'member_length_fields': [],
            # Category 4: Literal & Constant Semantic Understanding
            'literal_kinds': [],
            'literal_domains': [],
            'literal_severities': [],
            'is_null_constants': [],
            'is_bitmasks': [],
            'literal_constants': [],
            'is_lock_constants': [],
            # Category 5: Control Flow & Jump Semantics
            'jump_kinds': [],
            'jump_domains': [],
            'jump_scopes': [],
            'modifier_concurrencies': [],
            'modifier_attributes': [],
            # Category 6: Namespace & Reference
            'namespace_layers': [],
            'namespace_domains': [],
            'method_ref_kinds': [],
            'method_ref_usages': [],
            # Category 7: Data Flow & Edge Semantic Enrichment
            'data_flow_kinds': [],
            'child_roles': [],
            'call_actions': [],
            'call_side_effects': [],
            'call_receiver_roles': [],
            'argument_param_names': [],
            'branch_kinds': [],
            'control_reasons': [],
        }

        # Map domain to enrichment tags (ONLY valid CPG tag categories)
        if domain != 'general':
            # Function purposes - PRIMARY tag (100% coverage)
            if domain in self.tag_mappings['function_purpose']:
                hints['function_purposes'] = self.tag_mappings['function_purpose'][domain]

            # Data structures - SECONDARY tag (20% coverage)
            if domain in self.tag_mappings['data_structure']:
                hints['data_structures'] = self.tag_mappings['data_structure'][domain]

            # Algorithms
            if domain in self.tag_mappings['algorithm']:
                hints['algorithms'] = self.tag_mappings['algorithm'][domain]

            # Domain concepts - TERTIARY tag (<20% coverage)
            if domain in self.tag_mappings['domain_concept']:
                hints['domain_concepts'] = self.tag_mappings['domain_concept'][domain]

            # Features (disabled - too specific)
            if domain in self.tag_mappings['feature']:
                hints['features'] = self.tag_mappings['feature'][domain]

            # Category 1: Parameter & Return Semantic Integration
            if domain in self.tag_mappings['param_role']:
                hints['param_roles'] = self.tag_mappings['param_role'][domain]

            if domain in self.tag_mappings['return_kind']:
                hints['return_kinds'] = self.tag_mappings['return_kind'][domain]

            if domain in self.tag_mappings['return_outcome']:
                hints['return_outcomes'] = self.tag_mappings['return_outcome'][domain]

            if domain in self.tag_mappings['validation_required']:
                hints['validation_required'] = self.tag_mappings['validation_required'][domain]

            # Category 2: Variable & Identifier Semantic Enhancement
            if domain in self.tag_mappings['variable_role']:
                hints['variable_roles'] = self.tag_mappings['variable_role'][domain]

            if domain in self.tag_mappings['data_kind']:
                hints['data_kinds'] = self.tag_mappings['data_kind'][domain]

            if domain in self.tag_mappings['security_sensitivity']:
                hints['security_sensitivities'] = self.tag_mappings['security_sensitivity'][domain]

            if domain in self.tag_mappings['lifetime']:
                hints['lifetimes'] = self.tag_mappings['lifetime'][domain]

            if domain in self.tag_mappings['mutability']:
                hints['mutabilities'] = self.tag_mappings['mutability'][domain]

            if domain in self.tag_mappings['is_lock']:
                hints['is_locks'] = self.tag_mappings['is_lock'][domain]

            if domain in self.tag_mappings['is_pointer_to_struct']:
                hints['is_pointer_to_structs'] = self.tag_mappings['is_pointer_to_struct'][domain]

            # Category 3: Type & Member Semantic Classification
            if domain in self.tag_mappings['type_category']:
                hints['type_categories'] = self.tag_mappings['type_category'][domain]

            if domain in self.tag_mappings['type_domain_entity']:
                hints['type_domain_entities'] = self.tag_mappings['type_domain_entity'][domain]

            if domain in self.tag_mappings['type_concurrency_primitive']:
                hints['type_concurrency_primitives'] = self.tag_mappings['type_concurrency_primitive'][domain]

            if domain in self.tag_mappings['type_ownership_model']:
                hints['type_ownership_models'] = self.tag_mappings['type_ownership_model'][domain]

            if domain in self.tag_mappings['member_role']:
                hints['member_roles'] = self.tag_mappings['member_role'][domain]

            if domain in self.tag_mappings['member_pointer']:
                hints['member_pointers'] = self.tag_mappings['member_pointer'][domain]

            if domain in self.tag_mappings['member_length_field']:
                hints['member_length_fields'] = self.tag_mappings['member_length_field'][domain]

            # Category 4: Literal & Constant Semantic Understanding
            if domain in self.tag_mappings['literal_kind']:
                hints['literal_kinds'] = self.tag_mappings['literal_kind'][domain]

            if domain in self.tag_mappings['literal_domain']:
                hints['literal_domains'] = self.tag_mappings['literal_domain'][domain]

            if domain in self.tag_mappings['literal_severity']:
                hints['literal_severities'] = self.tag_mappings['literal_severity'][domain]

            if domain in self.tag_mappings['is_null_constant']:
                hints['is_null_constants'] = self.tag_mappings['is_null_constant'][domain]

            if domain in self.tag_mappings['is_bitmask']:
                hints['is_bitmasks'] = self.tag_mappings['is_bitmask'][domain]

            if domain in self.tag_mappings['literal_constant']:
                hints['literal_constants'] = self.tag_mappings['literal_constant'][domain]

            if domain in self.tag_mappings['is_lock_constant']:
                hints['is_lock_constants'] = self.tag_mappings['is_lock_constant'][domain]

            # Category 5: Control Flow & Jump Semantics
            if domain in self.tag_mappings['jump_kind']:
                hints['jump_kinds'] = self.tag_mappings['jump_kind'][domain]
            if domain in self.tag_mappings['jump_domain']:
                hints['jump_domains'] = self.tag_mappings['jump_domain'][domain]
            if domain in self.tag_mappings['jump_scope']:
                hints['jump_scopes'] = self.tag_mappings['jump_scope'][domain]
            if domain in self.tag_mappings['modifier_concurrency']:
                hints['modifier_concurrencies'] = self.tag_mappings['modifier_concurrency'][domain]
            if domain in self.tag_mappings['modifier_attribute']:
                hints['modifier_attributes'] = self.tag_mappings['modifier_attribute'][domain]

            # Category 6: Namespace & Reference
            if domain in self.tag_mappings['namespace_layer']:
                hints['namespace_layers'] = self.tag_mappings['namespace_layer'][domain]
            if domain in self.tag_mappings['namespace_domain']:
                hints['namespace_domains'] = self.tag_mappings['namespace_domain'][domain]
            if domain in self.tag_mappings['method_ref_kind']:
                hints['method_ref_kinds'] = self.tag_mappings['method_ref_kind'][domain]
            if domain in self.tag_mappings['method_ref_usage']:
                hints['method_ref_usages'] = self.tag_mappings['method_ref_usage'][domain]

            # Category 7: Data Flow & Edge
            if domain in self.tag_mappings['data_flow_kind']:
                hints['data_flow_kinds'] = self.tag_mappings['data_flow_kind'][domain]
            if domain in self.tag_mappings['child_role']:
                hints['child_roles'] = self.tag_mappings['child_role'][domain]
            if domain in self.tag_mappings['call_action']:
                hints['call_actions'] = self.tag_mappings['call_action'][domain]
            if domain in self.tag_mappings['call_side_effect']:
                hints['call_side_effects'] = self.tag_mappings['call_side_effect'][domain]
            if domain in self.tag_mappings['call_receiver_role']:
                hints['call_receiver_roles'] = self.tag_mappings['call_receiver_role'][domain]
            if domain in self.tag_mappings['argument_param_name']:
                hints['argument_param_names'] = self.tag_mappings['argument_param_name'][domain]
            if domain in self.tag_mappings['branch_kind']:
                hints['branch_kinds'] = self.tag_mappings['branch_kind'][domain]
            if domain in self.tag_mappings['control_reason']:
                hints['control_reasons'] = self.tag_mappings['control_reason'][domain]

        # Enhance with keyword-based matching
        hints = self._enhance_with_keywords(hints, keywords)

        # Fallback for general domain - use keywords to infer enrichment
        if domain == 'general' and not any(hints.values()):
            hints = self._general_domain_fallback(hints, keywords)

        # Generate CPGQL tag filter suggestions
        hints['tags'] = self._generate_tag_filters(hints)

        # Calculate coverage score
        hints['coverage_score'] = self._calculate_coverage(hints)

        logger.info(f"Generated enrichment hints for domain='{domain}': "
                   f"{len(hints['tags'])} tag filters, "
                   f"coverage={hints['coverage_score']:.2f}")

        # Phase 4: Apply fallback strategies if coverage is low
        if self.enable_fallback and self.fallback_selector:
            if hints['coverage_score'] < 0.4:
                logger.info(f"Coverage {hints['coverage_score']:.2f} is low, applying fallback strategies")
                hints = self.fallback_selector.apply_fallback(hints, question, analysis)

        return hints

    def _enhance_with_keywords(
        self,
        hints: Dict,
        keywords: List[str]
    ) -> Dict:
        """Enhance hints with keyword-based matching."""

        # Match keywords to known terms
        keyword_lower = [k.lower() for k in keywords]

        # Check for specific data structures in keywords
        known_structures = ['btree', 'hash', 'list', 'array', 'tree', 'queue']
        for structure in known_structures:
            if any(structure in kw for kw in keyword_lower):
                if structure not in hints['data_structures']:
                    hints['data_structures'].append(structure)

        # Check for specific features
        known_features = ['mvcc', 'wal', 'vacuum', 'toast', 'jsonb', 'parallel', 'partition']
        for feature in known_features:
            if any(feature in kw for kw in keyword_lower):
                if feature.upper() not in hints['features']:
                    hints['features'].append(feature.upper())

        # Type classification keywords
        type_keywords = {
            'struct': 'struct',
            'enum': 'enum',
            'typedef': 'typedef',
            'union': 'union'
        }
        for key, value in type_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['type_categories']:
                    hints['type_categories'].append(value)

        # Type domain entities
        entity_keywords = {
            'relation': 'relation',
            'tuple': 'heap-tuple',
            'heap': 'heap-tuple',
            'buffer': 'buffer-desc',
            'wal': 'wal-record',
            'catalog': 'catalog-entry',
            'executor': 'executor-state',
            'index': 'index'
        }
        for key, value in entity_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['type_domain_entities']:
                    hints['type_domain_entities'].append(value)

        # Concurrency primitive keywords
        primitive_keywords = {
            'lock': 'lwlock',
            'spinlock': 'spinlock',
            'mutex': 'mutex',
            'semaphore': 'semaphore',
            'condition': 'condition-variable'
        }
        for key, value in primitive_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['type_concurrency_primitives']:
                    hints['type_concurrency_primitives'].append(value)

        # Ownership keywords
        ownership_keywords = {
            'reference': 'reference-counted',
            'arena': 'arena-managed',
            'pinned': 'pinned-buffer',
            'copy-on-write': 'copy-on-write'
        }
        for key, value in ownership_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['type_ownership_models']:
                    hints['type_ownership_models'].append(value)

        # Member role keywords
        member_keywords = {
            'metadata': 'metadata',
            'counter': 'count',
            'flag': 'flag',
            'state': 'state',
            'reference': 'reference'
        }
        for key, value in member_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['member_roles']:
                    hints['member_roles'].append(value)

        # is-lock indicators
        lock_keywords = ['lock', 'mutex', 'spinlock', 'semaphore', 'lwlock']
        if any(any(lock_kw in kw for lock_kw in lock_keywords) for kw in keyword_lower):
            if 'true' not in hints['is_locks']:
                hints['is_locks'].append('true')

        # pointer-to-struct indicators
        pointer_keywords = ['pointer', 'ptr', 'struct pointer', 'struct*']
        if any(any(ptr_kw in kw for ptr_kw in pointer_keywords) for kw in keyword_lower):
            if 'true' not in hints['is_pointer_to_structs']:
                hints['is_pointer_to_structs'].append('true')
            if 'true' not in hints['member_pointers']:
                hints['member_pointers'].append('true')

        length_keywords = ['length', 'size', 'count', 'capacity']
        if any(any(length_kw in kw for length_kw in length_keywords) for kw in keyword_lower):
            if 'true' not in hints['member_length_fields']:
                hints['member_length_fields'].append('true')

        # Literal patterns
        literal_kind_keywords = {
            'error': 'error-code',
            'mask': 'bit-mask',
            'flag': 'boolean-flag',
            'timeout': 'timeout',
            'magic': 'magic-number',
            'null': 'null-constant',
            'size': 'size-constant'
        }
        for key, value in literal_kind_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['literal_kinds']:
                    hints['literal_kinds'].append(value)

        literal_domain_keywords = {
            'transaction': 'transaction',
            'visibility': 'visibility',
            'buffer': 'buffer',
            'lock': 'lock',
            'wal': 'wal',
            'catalog': 'catalog',
            'error': 'error'
        }
        for key, value in literal_domain_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['literal_domains']:
                    hints['literal_domains'].append(value)

        severity_keywords = ['warning', 'error', 'notice']
        for sev in severity_keywords:
            if any(sev in kw for kw in keyword_lower):
                if sev not in hints['literal_severities']:
                    hints['literal_severities'].append(sev)

        if any('null' in kw for kw in keyword_lower):
            if 'true' not in hints['is_null_constants']:
                hints['is_null_constants'].append('true')

        if any('mask' in kw for kw in keyword_lower):
            if 'true' not in hints['is_bitmasks']:
                hints['is_bitmasks'].append('true')

        constant_keywords = {
            'errcode': 'ERRCODE_SYNTAX_ERROR',
            'invalidblocknumber': 'InvalidBlockNumber',
            'locktag': 'LOCKTAG_RELATION'
        }
        for key, value in constant_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['literal_constants']:
                    hints['literal_constants'].append(value)

        if any('lock constant' in kw or 'locktag' in kw for kw in keyword_lower):
            if 'true' not in hints['is_lock_constants']:
                hints['is_lock_constants'].append('true')

        # Jump-related keywords
        jump_kind_keywords = {
            'retry': 'retry',
            'cleanup': 'cleanup',
            'dispatch': 'dispatch',
            'error handler': 'error-handler',
            'break': 'loop-break',
            'continue': 'loop-continue'
        }
        for key, value in jump_kind_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['jump_kinds']:
                    hints['jump_kinds'].append(value)

        jump_domain_keywords = {
            'executor': 'executor',
            'storage': 'storage',
            'transaction': 'transaction',
            'planner': 'planner',
            'buffer': 'buffer'
        }
        for key, value in jump_domain_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['jump_domains']:
                    hints['jump_domains'].append(value)

        if any('loop' in kw for kw in keyword_lower):
            if 'loop' not in hints['jump_scopes']:
                hints['jump_scopes'].append('loop')

        modifier_concurrency_keywords = {
            'atomic': 'atomic-access',
            'volatile': 'volatile-access',
            'synchronized': 'synchronized',
            'thread local': 'thread-local'
        }
        for key, value in modifier_concurrency_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['modifier_concurrencies']:
                    hints['modifier_concurrencies'].append(value)

        modifier_attribute_keywords = {
            'inline': 'inline',
            'noinline': 'noinline',
            'constexpr': 'constexpr',
            'readonly': 'readonly',
            'const ': 'const'
        }
        for key, value in modifier_attribute_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['modifier_attributes']:
                    hints['modifier_attributes'].append(value)

        # Namespace & reference keywords
        namespace_layer_keywords = {
            'executor': 'executor',
            'planner': 'planner',
            'storage': 'storage',
            'catalog': 'catalog',
            'buffer': 'buffer',
        }
        for key, value in namespace_layer_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['namespace_layers']:
                    hints['namespace_layers'].append(value)

        namespace_domain_keywords = {
            'extension': 'extension',
            'client': 'client',
            'server': 'server',
            'tools': 'tools',
            'config': 'configuration',
        }
        for key, value in namespace_domain_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['namespace_domains']:
                    hints['namespace_domains'].append(value)

        method_ref_kind_keywords = {
            'callback': 'callback',
            'function pointer': 'function-pointer',
            'virtual': 'virtual-dispatch',
        }
        for key, value in method_ref_kind_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['method_ref_kinds']:
                    hints['method_ref_kinds'].append(value)

        method_ref_usage_keywords = {
            'initializer': 'initializer',
            'cleanup': 'cleanup',
            'predicate': 'predicate',
            'comparator': 'comparator',
            'allocator': 'allocator',
        }
        for key, value in method_ref_usage_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['method_ref_usages']:
                    hints['method_ref_usages'].append(value)

        data_flow_keywords = {
            'lock': 'lock-propagation',
            'buffer': 'buffer-flow',
            'result': 'result-flow',
            'transaction': 'transaction-flow',
            'cost': 'cost-flow'
        }
        for key, value in data_flow_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['data_flow_kinds']:
                    hints['data_flow_kinds'].append(value)

        child_role_keywords = {
            'condition': 'condition',
            'body': 'body',
            'return': 'return'
        }
        for key, value in child_role_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['child_roles']:
                    hints['child_roles'].append(value)

        call_action_keywords = {
            'dispatch': 'dispatch',
            'initialize': 'initialize',
            'read': 'read',
            'write': 'write'
        }
        for key, value in call_action_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['call_actions']:
                    hints['call_actions'].append(value)

        call_side_effect_keywords = {
            'state': 'state-change',
            'lock': 'lock-state',
            'io': 'io'
        }
        for key, value in call_side_effect_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['call_side_effects']:
                    hints['call_side_effects'].append(value)

        call_receiver_keywords = {
            'handler': 'handler',
            'strategy': 'strategy',
            'manager': 'buffer-manager'
        }
        for key, value in call_receiver_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['call_receiver_roles']:
                    hints['call_receiver_roles'].append(value)

        argument_keywords = {
            'callback': 'callback',
            'state': 'state',
            'context': 'context',
            'buffer': 'buffer',
            'block': 'blockNumber'
        }
        for key, value in argument_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['argument_param_names']:
                    hints['argument_param_names'].append(value)

        branch_keywords = {
            'retry': 'retry',
            'cleanup': 'cleanup',
            'error': 'error'
        }
        for key, value in branch_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['branch_kinds']:
                    hints['branch_kinds'].append(value)

        control_reason_keywords = {
            'deadlock': 'deadlock-avoidance',
            'validation': 'result-validation',
            'consistency': 'consistency-check'
        }
        for key, value in control_reason_keywords.items():
            if any(key in kw for kw in keyword_lower):
                if value not in hints['control_reasons']:
                    hints['control_reasons'].append(value)

        return hints

    def _general_domain_fallback(
        self,
        hints: Dict,
        keywords: List[str]
    ) -> Dict:
        """Fallback enrichment for general domain using aggressive keyword matching."""

        keyword_lower = [k.lower() for k in keywords]

        # Map common keywords to function purposes
        purpose_mapping = {
            'manage': 'management',
            'allocate': 'allocation',
            'store': 'storage',
            'retrieve': 'retrieval',
            'process': 'processing',
            'execute': 'execution',
            'optimize': 'optimization',
            'maintain': 'maintenance',
            'track': 'tracking',
            'monitor': 'monitoring'
        }

        for keyword in keyword_lower:
            for key, purpose in purpose_mapping.items():
                if key in keyword:
                    if purpose not in hints['function_purposes']:
                        hints['function_purposes'].append(purpose)

        # Generic domain concepts
        concept_keywords = ['transaction', 'buffer', 'cache', 'connection', 'session', 'tuple', 'table', 'index']
        for concept in concept_keywords:
            if any(concept in kw for kw in keyword_lower):
                if concept not in hints['domain_concepts']:
                    hints['domain_concepts'].append(concept)

        # Add generic data structures
        structure_keywords = ['buffer', 'list', 'array', 'hash', 'tree']
        for structure in structure_keywords:
            if any(structure in kw for kw in keyword_lower):
                if structure not in hints['data_structures']:
                    hints['data_structures'].append(structure)

        return hints

    def _generate_tag_filters(self, hints: Dict) -> List[Dict]:
        """
        Generate CPGQL tag filter suggestions.

        Returns list of tag filters for use in queries like:
        cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management"))
        """
        filters = []

        # Function purpose filters
        for purpose in hints['function_purposes']:
            filters.append({
                'tag_name': 'function-purpose',
                'tag_value': purpose,
                'query_fragment': f'_.tag.nameExact("function-purpose").valueExact("{purpose}")'
            })

        # Data structure filters
        for ds in hints['data_structures']:
            filters.append({
                'tag_name': 'data-structure',
                'tag_value': ds,
                'query_fragment': f'_.tag.nameExact("data-structure").valueExact("{ds}")'
            })

        # Domain concept filters
        for concept in hints['domain_concepts']:
            filters.append({
                'tag_name': 'domain-concept',
                'tag_value': concept,
                'query_fragment': f'_.tag.nameExact("domain-concept").valueExact("{concept}")'
            })

        # Feature filters
        for feature in hints['features']:
            filters.append({
                'tag_name': 'Feature',
                'tag_value': feature,
                'query_fragment': f'_.tag.nameExact("Feature").valueExact("{feature}")'
            })

        # Category 1: Parameter & Return filters
        for role in hints.get('param_roles', []):
            filters.append({
                'tag_name': 'param-role',
                'tag_value': role,
                'query_fragment': f'_.tag.nameExact("param-role").valueExact("{role}")'
            })

        for kind in hints.get('return_kinds', []):
            filters.append({
                'tag_name': 'return-kind',
                'tag_value': kind,
                'query_fragment': f'_.tag.nameExact("return-kind").valueExact("{kind}")'
            })

        for outcome in hints.get('return_outcomes', []):
            filters.append({
                'tag_name': 'return-outcome',
                'tag_value': outcome,
                'query_fragment': f'_.tag.nameExact("return-outcome").valueExact("{outcome}")'
            })

        # Category 2: Variable & Identifier filters
        for role in hints.get('variable_roles', []):
            filters.append({
                'tag_name': 'variable-role',
                'tag_value': role,
                'query_fragment': f'_.tag.nameExact("variable-role").valueExact("{role}")'
            })

        for kind in hints.get('data_kinds', []):
            filters.append({
                'tag_name': 'data-kind',
                'tag_value': kind,
                'query_fragment': f'_.tag.nameExact("data-kind").valueExact("{kind}")'
            })

        for sensitivity in hints.get('security_sensitivities', []):
            filters.append({
                'tag_name': 'security-sensitivity',
                'tag_value': sensitivity,
                'query_fragment': f'_.tag.nameExact("security-sensitivity").valueExact("{sensitivity}")'
            })

        for lock_flag in hints.get('is_locks', []):
            filters.append({
                'tag_name': 'is-lock',
                'tag_value': lock_flag,
                'query_fragment': f'_.tag.nameExact("is-lock").valueExact("{lock_flag}")'
            })

        for pointer_flag in hints.get('is_pointer_to_structs', []):
            filters.append({
                'tag_name': 'is-pointer-to-struct',
                'tag_value': pointer_flag,
                'query_fragment': f'_.tag.nameExact("is-pointer-to-struct").valueExact("{pointer_flag}")'
            })

        # Category 3: Type & Member filters
        for category in hints.get('type_categories', []):
            filters.append({
                'tag_name': 'type-category',
                'tag_value': category,
                'query_fragment': f'_.tag.nameExact("type-category").valueExact("{category}")'
            })

        for entity in hints.get('type_domain_entities', []):
            filters.append({
                'tag_name': 'type-domain-entity',
                'tag_value': entity,
                'query_fragment': f'_.tag.nameExact("type-domain-entity").valueExact("{entity}")'
            })

        for primitive in hints.get('type_concurrency_primitives', []):
            filters.append({
                'tag_name': 'type-concurrency-primitive',
                'tag_value': primitive,
                'query_fragment': f'_.tag.nameExact("type-concurrency-primitive").valueExact("{primitive}")'
            })

        for ownership in hints.get('type_ownership_models', []):
            filters.append({
                'tag_name': 'type-ownership-model',
                'tag_value': ownership,
                'query_fragment': f'_.tag.nameExact("type-ownership-model").valueExact("{ownership}")'
            })

        for member_role in hints.get('member_roles', []):
            filters.append({
                'tag_name': 'member-role',
                'tag_value': member_role,
                'query_fragment': f'_.tag.nameExact("member-role").valueExact("{member_role}")'
            })

        for member_pointer in hints.get('member_pointers', []):
            filters.append({
                'tag_name': 'member-pointer',
                'tag_value': member_pointer,
                'query_fragment': f'_.tag.nameExact("member-pointer").valueExact("{member_pointer}")'
            })

        for member_length in hints.get('member_length_fields', []):
            filters.append({
                'tag_name': 'member-length-field',
                'tag_value': member_length,
                'query_fragment': f'_.tag.nameExact("member-length-field").valueExact("{member_length}")'
            })

        # Category 4: Literal & Constant filters
        for literal_kind in hints.get('literal_kinds', []):
            filters.append({
                'tag_name': 'literal-kind',
                'tag_value': literal_kind,
                'query_fragment': f'_.tag.nameExact("literal-kind").valueExact("{literal_kind}")'
            })

        for literal_domain in hints.get('literal_domains', []):
            filters.append({
                'tag_name': 'literal-domain',
                'tag_value': literal_domain,
                'query_fragment': f'_.tag.nameExact("literal-domain").valueExact("{literal_domain}")'
            })

        for literal_severity in hints.get('literal_severities', []):
            filters.append({
                'tag_name': 'literal-severity',
                'tag_value': literal_severity,
                'query_fragment': f'_.tag.nameExact("literal-severity").valueExact("{literal_severity}")'
            })

        for null_flag in hints.get('is_null_constants', []):
            filters.append({
                'tag_name': 'is-null-constant',
                'tag_value': null_flag,
                'query_fragment': f'_.tag.nameExact("is-null-constant").valueExact("{null_flag}")'
            })

        for bitmask_flag in hints.get('is_bitmasks', []):
            filters.append({
                'tag_name': 'is-bitmask',
                'tag_value': bitmask_flag,
                'query_fragment': f'_.tag.nameExact("is-bitmask").valueExact("{bitmask_flag}")'
            })

        for literal_constant in hints.get('literal_constants', []):
            filters.append({
                'tag_name': 'literal-constant',
                'tag_value': literal_constant,
                'query_fragment': f'_.tag.nameExact("literal-constant").valueExact("{literal_constant}")'
            })

        for lock_constant_flag in hints.get('is_lock_constants', []):
            filters.append({
                'tag_name': 'is-lock-constant',
                'tag_value': lock_constant_flag,
                'query_fragment': f'_.tag.nameExact("is-lock-constant").valueExact("{lock_constant_flag}")'
            })

        # Category 5: Control Flow & Jump
        for jump_kind in hints.get('jump_kinds', []):
            filters.append({
                'tag_name': 'jump-kind',
                'tag_value': jump_kind,
                'query_fragment': f'_.tag.nameExact("jump-kind").valueExact("{jump_kind}")'
            })

        for jump_domain in hints.get('jump_domains', []):
            filters.append({
                'tag_name': 'jump-domain',
                'tag_value': jump_domain,
                'query_fragment': f'_.tag.nameExact("jump-domain").valueExact("{jump_domain}")'
            })

        for jump_scope in hints.get('jump_scopes', []):
            filters.append({
                'tag_name': 'jump-scope',
                'tag_value': jump_scope,
                'query_fragment': f'_.tag.nameExact("jump-scope").valueExact("{jump_scope}")'
            })

        for modifier_concurrency in hints.get('modifier_concurrencies', []):
            filters.append({
                'tag_name': 'modifier-concurrency',
                'tag_value': modifier_concurrency,
                'query_fragment': f'_.tag.nameExact("modifier-concurrency").valueExact("{modifier_concurrency}")'
            })

        for modifier_attribute in hints.get('modifier_attributes', []):
            filters.append({
                'tag_name': 'modifier-attribute',
                'tag_value': modifier_attribute,
                'query_fragment': f'_.tag.nameExact("modifier-attribute").valueExact("{modifier_attribute}")'
            })
        # Category 6: Namespace & Reference
        for namespace_layer in hints.get('namespace_layers', []):
            filters.append({
                'tag_name': 'namespace-layer',
                'tag_value': namespace_layer,
                'query_fragment': f'_.tag.nameExact("namespace-layer").valueExact("{namespace_layer}")'
            })
        for namespace_domain in hints.get('namespace_domains', []):
            filters.append({
                'tag_name': 'namespace-domain',
                'tag_value': namespace_domain,
                'query_fragment': f'_.tag.nameExact("namespace-domain").valueExact("{namespace_domain}")'
            })
        for ref_kind in hints.get('method_ref_kinds', []):
            filters.append({
                'tag_name': 'method-ref-kind',
                'tag_value': ref_kind,
                'query_fragment': f'_.tag.nameExact("method-ref-kind").valueExact("{ref_kind}")'
            })
        for ref_usage in hints.get('method_ref_usages', []):
            filters.append({
                'tag_name': 'method-ref-usage',
                'tag_value': ref_usage,
                'query_fragment': f'_.tag.nameExact("method-ref-usage").valueExact("{ref_usage}")'
            })
        for data_flow in hints.get('data_flow_kinds', []):
            filters.append({
                'tag_name': 'data-flow-kind',
                'tag_value': data_flow,
                'query_fragment': f'_.tag.nameExact("data-flow-kind").valueExact("{data_flow}")'
            })
        for child_role in hints.get('child_roles', []):
            filters.append({
                'tag_name': 'child-role',
                'tag_value': child_role,
                'query_fragment': f'_.tag.nameExact("child-role").valueExact("{child_role}")'
            })
        for call_action in hints.get('call_actions', []):
            filters.append({
                'tag_name': 'call-action',
                'tag_value': call_action,
                'query_fragment': f'_.tag.nameExact("call-action").valueExact("{call_action}")'
            })
        for call_side in hints.get('call_side_effects', []):
            filters.append({
                'tag_name': 'call-side-effect',
                'tag_value': call_side,
                'query_fragment': f'_.tag.nameExact("call-side-effect").valueExact("{call_side}")'
            })
        for receiver_role in hints.get('call_receiver_roles', []):
            filters.append({
                'tag_name': 'call-receiver-role',
                'tag_value': receiver_role,
                'query_fragment': f'_.tag.nameExact("call-receiver-role").valueExact("{receiver_role}")'
            })
        for arg in hints.get('argument_param_names', []):
            filters.append({
                'tag_name': 'argument-param-name',
                'tag_value': arg,
                'query_fragment': f'_.tag.nameExact("argument-param-name").valueExact("{arg}")'
            })
        for branch_kind in hints.get('branch_kinds', []):
            filters.append({
                'tag_name': 'branch-kind',
                'tag_value': branch_kind,
                'query_fragment': f'_.tag.nameExact("branch-kind").valueExact("{branch_kind}")'
            })
        for control_reason in hints.get('control_reasons', []):
            filters.append({
                'tag_name': 'control-reason',
                'tag_value': control_reason,
                'query_fragment': f'_.tag.nameExact("control-reason").valueExact("{control_reason}")'
            })

        return filters

    def _calculate_coverage(self, hints: Dict) -> float:
        """
        Calculate how well the hints cover different enrichment layers.

        Returns score 0-1 based on VALID CPG tag categories only.
        """
        layers_with_hints = 0
        total_layers = 47  # Updated: 5 base + 4 param/return + 7 variable/identifier + 7 type/member + 7 literal + 5 jump/control + 4 namespace/reference + 8 data-flow/edge

        if hints.get('function_purposes'):
            layers_with_hints += 1
        if hints.get('data_structures'):
            layers_with_hints += 1
        if hints.get('algorithms'):
            layers_with_hints += 1
        if hints.get('domain_concepts'):
            layers_with_hints += 1
        if hints.get('features'):
            layers_with_hints += 1
        # Category 1: Parameter & Return
        if hints.get('param_roles'):
            layers_with_hints += 1
        if hints.get('return_kinds'):
            layers_with_hints += 1
        if hints.get('return_outcomes'):
            layers_with_hints += 1
        if hints.get('validation_required'):
            layers_with_hints += 1
        # Category 2: Variable & Identifier
        if hints.get('variable_roles'):
            layers_with_hints += 1
        if hints.get('data_kinds'):
            layers_with_hints += 1
        if hints.get('security_sensitivities'):
            layers_with_hints += 1
        if hints.get('lifetimes'):
            layers_with_hints += 1
        if hints.get('mutabilities'):
            layers_with_hints += 1
        if hints.get('is_locks'):
            layers_with_hints += 1
        if hints.get('is_pointer_to_structs'):
            layers_with_hints += 1
        # Category 3: Type & Member
        if hints.get('type_categories'):
            layers_with_hints += 1
        if hints.get('type_domain_entities'):
            layers_with_hints += 1
        if hints.get('type_concurrency_primitives'):
            layers_with_hints += 1
        if hints.get('type_ownership_models'):
            layers_with_hints += 1
        if hints.get('member_roles'):
            layers_with_hints += 1
        if hints.get('member_pointers'):
            layers_with_hints += 1
        if hints.get('member_length_fields'):
            layers_with_hints += 1
        # Category 4: Literal & Constant
        if hints.get('literal_kinds'):
            layers_with_hints += 1
        if hints.get('literal_domains'):
            layers_with_hints += 1
        if hints.get('literal_severities'):
            layers_with_hints += 1
        if hints.get('is_null_constants'):
            layers_with_hints += 1
        if hints.get('is_bitmasks'):
            layers_with_hints += 1
        if hints.get('literal_constants'):
            layers_with_hints += 1
        if hints.get('is_lock_constants'):
            layers_with_hints += 1
        # Category 5: Control Flow & Jump
        if hints.get('jump_kinds'):
            layers_with_hints += 1
        if hints.get('jump_domains'):
            layers_with_hints += 1
        if hints.get('jump_scopes'):
            layers_with_hints += 1
        if hints.get('modifier_concurrencies'):
            layers_with_hints += 1
        if hints.get('modifier_attributes'):
            layers_with_hints += 1
        # Category 6: Namespace & Reference
        if hints.get('namespace_layers'):
            layers_with_hints += 1
        if hints.get('namespace_domains'):
            layers_with_hints += 1
        if hints.get('method_ref_kinds'):
            layers_with_hints += 1
        if hints.get('method_ref_usages'):
            layers_with_hints += 1
        # Category 7: Data Flow & Edge
        if hints.get('data_flow_kinds'):
            layers_with_hints += 1
        if hints.get('child_roles'):
            layers_with_hints += 1
        if hints.get('call_actions'):
            layers_with_hints += 1
        if hints.get('call_side_effects'):
            layers_with_hints += 1
        if hints.get('call_receiver_roles'):
            layers_with_hints += 1
        if hints.get('argument_param_names'):
            layers_with_hints += 1
        if hints.get('branch_kinds'):
            layers_with_hints += 1
        if hints.get('control_reasons'):
            layers_with_hints += 1

        return layers_with_hints / total_layers

    def format_for_prompt(self, hints: Dict) -> str:
        """
        Format enrichment hints for inclusion in LLM prompt.

        Returns formatted string for prompt context (ONLY valid CPG tag categories).
        """
        sections = []

        if hints.get('features'):
            sections.append(f"PostgreSQL Features: {', '.join(hints['features'])}")

        if hints.get('function_purposes'):
            sections.append(f"Function Purposes: {', '.join(hints['function_purposes'])}")

        if hints.get('data_structures'):
            sections.append(f"Data Structures: {', '.join(hints['data_structures'])}")

        if hints.get('domain_concepts'):
            sections.append(f"Domain Concepts: {', '.join(hints['domain_concepts'])}")

        if hints.get('member_pointers'):
            sections.append(f"Member Pointers: {', '.join(hints['member_pointers'])}")

        if hints.get('member_length_fields'):
            sections.append(f"Member Length Fields: {', '.join(hints['member_length_fields'])}")

        if hints.get('literal_kinds'):
            sections.append(f"Literal Kinds: {', '.join(hints['literal_kinds'])}")

        if hints.get('literal_domains'):
            sections.append(f"Literal Domains: {', '.join(hints['literal_domains'])}")

        if hints.get('literal_severities'):
            sections.append(f"Literal Severities: {', '.join(hints['literal_severities'])}")
        if hints.get('literal_constants'):
            sections.append(f"Literal Constants: {', '.join(hints['literal_constants'])}")
        if hints.get('is_lock_constants'):
            sections.append(f"Lock Constants: {', '.join(hints['is_lock_constants'])}")
        if hints.get('data_flow_kinds'):
            sections.append(f"Data Flow: {', '.join(hints['data_flow_kinds'])}")
        if hints.get('child_roles'):
            sections.append(f"Child Roles: {', '.join(hints['child_roles'])}")
        if hints.get('call_actions'):
            sections.append(f"Call Actions: {', '.join(hints['call_actions'])}")
        if hints.get('call_side_effects'):
            sections.append(f"Call Side Effects: {', '.join(hints['call_side_effects'])}")
        if hints.get('call_receiver_roles'):
            sections.append(f"Call Receiver Roles: {', '.join(hints['call_receiver_roles'])}")
        if hints.get('argument_param_names'):
            sections.append(f"Argument to Param: {', '.join(hints['argument_param_names'])}")
        if hints.get('branch_kinds'):
            sections.append(f"Branch Kinds: {', '.join(hints['branch_kinds'])}")
        if hints.get('control_reasons'):
            sections.append(f"Control Reasons: {', '.join(hints['control_reasons'])}")
        if hints.get('jump_kinds'):
            sections.append(f"Jump Kinds: {', '.join(hints['jump_kinds'])}")
        if hints.get('jump_domains'):
            sections.append(f"Jump Domains: {', '.join(hints['jump_domains'])}")
        if hints.get('jump_scopes'):
            sections.append(f"Jump Scopes: {', '.join(hints['jump_scopes'])}")
        if hints.get('modifier_concurrencies'):
            sections.append(f"Concurrency Modifiers: {', '.join(hints['modifier_concurrencies'])}")
        if hints.get('modifier_attributes'):
            sections.append(f"Attributes: {', '.join(hints['modifier_attributes'])}")
        if hints.get('namespace_layers'):
            sections.append(f"Namespace Layers: {', '.join(hints['namespace_layers'])}")
        if hints.get('namespace_domains'):
            sections.append(f"Namespace Domains: {', '.join(hints['namespace_domains'])}")
        if hints.get('method_ref_kinds'):
            sections.append(f"Method Ref Kinds: {', '.join(hints['method_ref_kinds'])}")
        if hints.get('method_ref_usages'):
            sections.append(f"Method Ref Usage: {', '.join(hints['method_ref_usages'])}")

        # Add example tag usage
        if hints['tags']:
            sections.append("\nExample tag-based queries:")
            for i, tag in enumerate(hints['tags'][:3], 1):  # Show top 3
                example = f"cpg.method.where({tag['query_fragment']}).name.l"
                sections.append(f"  {i}. {example}")

        return '\n'.join(sections)

    def get_example_queries(self, hints: Dict, limit: int = 5) -> List[str]:
        """
        Generate example CPGQL queries using enrichment tags.

        Args:
            hints: Enrichment hints
            limit: Maximum number of examples

        Returns:
            List of example CPGQL queries
        """
        examples = []

        # Generate queries for each tag type
        for tag in hints['tags'][:limit]:
            tag_name = tag['tag_name']
            tag_value = tag['tag_value']

            # Different query patterns based on tag type
            if tag_name == 'function-purpose':
                query = f'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l.take(10)'
            elif tag_name == 'data-structure':
                query = f'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l.take(10)'
            elif tag_name == 'Feature':
                query = f'cpg.file.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l.take(10)'
            else:
                query = f'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).l.take(10)'

            examples.append(query)

        return examples
