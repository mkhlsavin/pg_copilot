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

        return filters

    def _calculate_coverage(self, hints: Dict) -> float:
        """
        Calculate how well the hints cover different enrichment layers.

        Returns score 0-1 based on VALID CPG tag categories only.
        """
        layers_with_hints = 0
        total_layers = 14  # Updated: 5 base + 4 param/return + 5 variable/identifier

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
