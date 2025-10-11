"""Enrichment Agent - Maps questions to CPG enrichment tags."""
import logging
from typing import Dict, List, Set
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """
    Enrichment Agent for CPG tag mapping.

    Maps question analysis to relevant enrichment tags from the
    12-layer CPG enrichment system.
    """

    def __init__(self):
        """Initialize Enrichment Agent with tag mappings."""

        # Load enrichment tag mappings
        # Based on the 12 enrichment layers from IMPLEMENTATION_PLAN.md
        self.tag_mappings = self._build_tag_mappings()

    def _build_tag_mappings(self) -> Dict:
        """
        Build comprehensive tag mappings.

        Maps domains/keywords to enrichment tags.
        """
        return {
            # Layer 1-2: Subsystem & Comments (file-level)
            'subsystem': {
                'vacuum': ['autovacuum', 'vacuum'],
                'wal': ['wal', 'xlog'],
                'mvcc': ['snapshot', 'visibility', 'procarray'],
                'query-planning': ['optimizer', 'planner', 'executor'],
                'memory': ['mem', 'aset', 'mcxt'],
                'replication': ['replication', 'walreceiver', 'walsender'],
                'storage': ['storage', 'smgr', 'md'],
                'indexes': ['nbtree', 'index', 'access'],
                'locking': ['lock', 'lmgr'],
                'parallel': ['parallel', 'shm_mq'],
                'jsonb': ['jsonb', 'json'],
                'background': ['bgworker', 'postmaster']
            },

            # Layer 3-4: API Usage & Security Patterns
            'api_category': {
                'memory': ['memory-management', 'allocation'],
                'locking': ['synchronization', 'concurrency'],
                'io': ['file-io', 'buffer-management'],
                'networking': ['connection-handling'],
                'error': ['error-handling']
            },

            # Layer 10: Semantic Classification (function-level)
            'function_purpose': {
                'vacuum': ['maintenance', 'garbage-collection'],
                'wal': ['logging', 'recovery'],
                'mvcc': ['transaction-management', 'concurrency-control'],
                'query-planning': ['query-optimization', 'planning'],
                'memory': ['memory-management', 'allocation'],
                'replication': ['replication', 'high-availability'],
                'storage': ['storage-management', 'persistence'],
                'indexes': ['indexing', 'search'],
                'locking': ['synchronization', 'locking'],
                'parallel': ['parallel-processing', 'multi-threading']
            },

            'data_structure': {
                'vacuum': ['heap', 'tuple'],
                'wal': ['buffer', 'circular-buffer'],
                'mvcc': ['snapshot', 'tuple'],
                'query-planning': ['tree', 'list'],
                'memory': ['memory-context', 'allocator'],
                'indexes': ['btree', 'hash-table', 'array'],
                'locking': ['lock-table', 'queue'],
                'parallel': ['shared-memory', 'queue']
            },

            'algorithm': {
                'vacuum': ['mark-sweep', 'reference-counting'],
                'query-planning': ['dynamic-programming', 'cost-based'],
                'indexes': ['binary-search', 'hashing'],
                'locking': ['two-phase-locking', 'deadlock-detection'],
                'parallel': ['producer-consumer', 'work-stealing']
            },

            'domain_concept': {
                'vacuum': ['vacuum', 'freeze'],
                'wal': ['wal', 'checkpoint'],
                'mvcc': ['mvcc', 'snapshot-isolation'],
                'query-planning': ['query-plan', 'selectivity'],
                'replication': ['streaming-replication', 'logical-replication'],
                'indexes': ['index-scan', 'bitmap-scan'],
                'locking': ['lock-modes', 'deadlock'],
                'parallel': ['parallel-query', 'worker-process']
            },

            # Layer 11: Architecture (file-level)
            'architectural_role': {
                'vacuum': ['maintenance-component'],
                'wal': ['logging-component'],
                'mvcc': ['concurrency-component'],
                'query-planning': ['execution-component'],
                'memory': ['resource-management'],
                'replication': ['replication-component'],
                'storage': ['storage-component'],
                'indexes': ['access-method'],
                'background': ['background-service']
            },

            # Layer 12: Feature Mapping
            'feature': {
                'vacuum': ['autovacuum'],
                'wal': ['WAL improvements'],
                'mvcc': ['MVCC'],
                'query-planning': ['JIT compilation', 'Parallel query'],
                'replication': ['Streaming replication', 'Logical replication'],
                'storage': ['TOAST'],
                'indexes': ['BRIN indexes'],
                'jsonb': ['JSONB data type'],
                'security': ['SCRAM authentication'],
                'partition': ['Partitioning']
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
            Dictionary with enrichment hints:
            - subsystems: Relevant subsystems
            - function_purposes: Relevant function purposes
            - data_structures: Relevant data structures
            - algorithms: Relevant algorithms
            - domain_concepts: Relevant domain concepts
            - features: Relevant PostgreSQL features
            - tags: Suggested CPGQL tag filters
        """
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])
        intent = analysis.get('intent', 'explain-concept')

        hints = {
            'subsystems': [],
            'function_purposes': [],
            'data_structures': [],
            'algorithms': [],
            'domain_concepts': [],
            'architectural_roles': [],
            'features': [],
            'api_categories': []
        }

        # Map domain to enrichment tags
        if domain != 'general':
            # Subsystems
            if domain in self.tag_mappings['subsystem']:
                hints['subsystems'] = self.tag_mappings['subsystem'][domain]

            # Function purposes
            if domain in self.tag_mappings['function_purpose']:
                hints['function_purposes'] = self.tag_mappings['function_purpose'][domain]

            # Data structures
            if domain in self.tag_mappings['data_structure']:
                hints['data_structures'] = self.tag_mappings['data_structure'][domain]

            # Algorithms
            if domain in self.tag_mappings['algorithm']:
                hints['algorithms'] = self.tag_mappings['algorithm'][domain]

            # Domain concepts
            if domain in self.tag_mappings['domain_concept']:
                hints['domain_concepts'] = self.tag_mappings['domain_concept'][domain]

            # Architectural roles
            if domain in self.tag_mappings['architectural_role']:
                hints['architectural_roles'] = self.tag_mappings['architectural_role'][domain]

            # Features
            if domain in self.tag_mappings['feature']:
                hints['features'] = self.tag_mappings['feature'][domain]

            # API categories
            if domain in self.tag_mappings['api_category']:
                hints['api_categories'] = self.tag_mappings['api_category'][domain]

        # Enhance with keyword-based matching
        hints = self._enhance_with_keywords(hints, keywords)

        # Generate CPGQL tag filter suggestions
        hints['tags'] = self._generate_tag_filters(hints)

        # Calculate coverage score
        hints['coverage_score'] = self._calculate_coverage(hints)

        logger.info(f"Generated enrichment hints for domain='{domain}': "
                   f"{len(hints['tags'])} tag filters, "
                   f"coverage={hints['coverage_score']:.2f}")

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

        return filters

    def _calculate_coverage(self, hints: Dict) -> float:
        """
        Calculate how well the hints cover different enrichment layers.

        Returns score 0-1.
        """
        layers_with_hints = 0
        total_layers = 8  # subsystems, function_purposes, data_structures, etc.

        if hints['subsystems']:
            layers_with_hints += 1
        if hints['function_purposes']:
            layers_with_hints += 1
        if hints['data_structures']:
            layers_with_hints += 1
        if hints['algorithms']:
            layers_with_hints += 1
        if hints['domain_concepts']:
            layers_with_hints += 1
        if hints['architectural_roles']:
            layers_with_hints += 1
        if hints['features']:
            layers_with_hints += 1
        if hints['api_categories']:
            layers_with_hints += 1

        return layers_with_hints / total_layers

    def format_for_prompt(self, hints: Dict) -> str:
        """
        Format enrichment hints for inclusion in LLM prompt.

        Returns formatted string for prompt context.
        """
        sections = []

        if hints['features']:
            sections.append(f"PostgreSQL Features: {', '.join(hints['features'])}")

        if hints['subsystems']:
            sections.append(f"Relevant Subsystems: {', '.join(hints['subsystems'])}")

        if hints['function_purposes']:
            sections.append(f"Function Purposes: {', '.join(hints['function_purposes'])}")

        if hints['data_structures']:
            sections.append(f"Data Structures: {', '.join(hints['data_structures'])}")

        if hints['domain_concepts']:
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
