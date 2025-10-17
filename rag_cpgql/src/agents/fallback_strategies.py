"""Fallback Strategies for Low-Coverage Enrichment (Phase 4)

When enrichment coverage is low, apply intelligent fallback strategies:
1. Hybrid queries (name + tag matching)
2. Fuzzy keyword-to-tag mapping
3. Generic domain enhancement
4. Aggressive keyword extraction
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class KeywordToTagMapper:
    """Maps keywords to likely tag values using fuzzy matching."""

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize mapper.

        Args:
            similarity_threshold: Minimum similarity score (0-1) for fuzzy match
        """
        self.similarity_threshold = similarity_threshold

        # Common keyword patterns to tag mappings
        self.keyword_patterns = {
            # Function purposes
            r'\b(allocat|alloc|malloc)\w*': ('function-purpose', 'memory-management'),
            r'\b(free|dealloc)\w*': ('function-purpose', 'memory-management'),
            r'\b(lock|unlock|mutex|spinlock)\w*': ('function-purpose', 'locking'),
            r'\b(read|write|io)\w*': ('function-purpose', 'io-operations'),
            r'\b(parse|parsing)\w*': ('function-purpose', 'parsing'),
            r'\b(hash|hashing)\w*': ('function-purpose', 'hashing'),
            r'\b(search|find|lookup)\w*': ('function-purpose', 'search'),
            r'\b(insert|add|append)\w*': ('function-purpose', 'insertion'),
            r'\b(delete|remove)\w*': ('function-purpose', 'deletion'),
            r'\b(update|modify)\w*': ('function-purpose', 'update'),
            r'\b(init|initialize)\w*': ('function-purpose', 'initialization'),
            r'\b(cleanup|clean)\w*': ('function-purpose', 'cleanup'),
            r'\b(validate|check)\w*': ('function-purpose', 'validation'),

            # Domain concepts
            r'\b(vacuum|autovacuum)\w*': ('domain-concept', 'vacuum'),
            r'\b(wal|xlog)\w*': ('domain-concept', 'wal'),
            r'\b(transaction|xact)\w*': ('domain-concept', 'transaction'),
            r'\b(snapshot|visibility)\w*': ('domain-concept', 'mvcc'),
            r'\b(buffer|page)\w*': ('domain-concept', 'buffer-management'),
            r'\b(index|btree|gin|gist)\w*': ('domain-concept', 'indexing'),
            r'\b(planner|optimizer)\w*': ('domain-concept', 'query-planning'),
            r'\b(executor|execution)\w*': ('domain-concept', 'execution'),
            r'\b(checkpoint|checkpointing)\w*': ('domain-concept', 'checkpoint'),
            r'\b(recovery|replay)\w*': ('domain-concept', 'recovery'),

            # Subsystems
            r'\bautovacuum\b': ('subsystem-name', 'autovacuum'),
            r'\bvacuum\b': ('subsystem-name', 'vacuum'),
            r'\bstorage\b': ('subsystem-name', 'storage'),
            r'\bwal\b': ('subsystem-name', 'wal'),
            r'\bbuffer\b': ('subsystem-name', 'buffer'),

            # Data structures
            r'\b(heap|tuple)\w*': ('data-structure', 'heap-tuple'),
            r'\b(buffer|page)\w*': ('data-structure', 'buffer-page'),
            r'\b(hash\s*table)\w*': ('data-structure', 'hash-table'),
            r'\b(list|array)\w*': ('data-structure', 'list'),
            r'\b(tree|btree)\w*': ('data-structure', 'tree'),
        }

    def map_keywords_to_tags(
        self,
        keywords: List[str],
        existing_tags: List[Dict]
    ) -> List[Dict]:
        """
        Map keywords to additional tags using pattern matching.

        Args:
            keywords: Keywords extracted from question
            existing_tags: Tags already found by EnrichmentAgent

        Returns:
            List of additional tag candidates
        """
        additional_tags = []
        existing_tag_values = {(t.get('tag_name'), t.get('tag_value')) for t in existing_tags}

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Try pattern matching
            for pattern, (tag_name, tag_value) in self.keyword_patterns.items():
                if re.search(pattern, keyword_lower):
                    tag_key = (tag_name, tag_value)

                    if tag_key not in existing_tag_values:
                        additional_tags.append({
                            'tag_name': tag_name,
                            'tag_value': tag_value,
                            'query_fragment': f'_.tag.nameExact("{tag_name}").valueExact("{tag_value}")',
                            'source': 'keyword-pattern-match',
                            'confidence': 0.8
                        })
                        existing_tag_values.add(tag_key)

        return additional_tags

    def fuzzy_match_to_tag_values(
        self,
        keyword: str,
        candidate_values: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Find tag values similar to keyword using fuzzy matching.

        Args:
            keyword: Keyword to match
            candidate_values: Available tag values

        Returns:
            List of (value, similarity_score) tuples above threshold
        """
        matches = []

        keyword_lower = keyword.lower()

        for candidate in candidate_values:
            candidate_lower = candidate.lower()

            # Calculate similarity
            similarity = SequenceMatcher(None, keyword_lower, candidate_lower).ratio()

            # Also check if keyword is substring of candidate or vice versa
            if keyword_lower in candidate_lower or candidate_lower in keyword_lower:
                similarity = max(similarity, 0.7)  # Boost substring matches

            if similarity >= self.similarity_threshold:
                matches.append((candidate, similarity))

        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches


class HybridQueryBuilder:
    """Builds hybrid queries combining name-based and tag-based matching."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_hybrid_patterns(
        self,
        keywords: List[str],
        tags: List[Dict],
        domain: str
    ) -> List[str]:
        """
        Build hybrid query patterns combining name and tag matching.

        Args:
            keywords: Keywords from question
            tags: Available enrichment tags
            domain: Question domain

        Returns:
            List of hybrid query patterns
        """
        patterns = []

        # Pattern 1: Name filter + tag filter
        if keywords and tags:
            keyword = keywords[0]
            tag = tags[0]

            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')

            if tag_name and tag_value:
                patterns.append(
                    f'cpg.method.name(".*{keyword}.*")'
                    f'.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l'
                )

        # Pattern 2: File filter + tag filter
        if domain != 'general' and tags:
            tag = tags[0]
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')

            if tag_name and tag_value:
                patterns.append(
                    f'cpg.file.name(".*{domain}.*")'
                    f'.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l'
                )

        # Pattern 3: Broad tag search + name contains
        if keywords and tags:
            keyword = keywords[0]
            tag = tags[0]
            tag_name = tag.get('tag_name', '')

            if tag_name:
                patterns.append(
                    f'cpg.method.where(_.tag.nameExact("{tag_name}"))'
                    f'.where(_.name(".*{keyword}.*")).name.l'
                )

        return patterns


class FallbackStrategySelector:
    """Selects appropriate fallback strategy based on coverage and context."""

    def __init__(self):
        self.mapper = KeywordToTagMapper()
        self.hybrid_builder = HybridQueryBuilder()
        self.logger = logging.getLogger(self.__class__.__name__)

    def apply_fallback(
        self,
        hints: Dict,
        question: str,
        analysis: Dict
    ) -> Dict:
        """
        Apply fallback strategies when coverage is low.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: Question analysis

        Returns:
            Enhanced hints with fallback strategies applied
        """
        coverage = hints.get('coverage_score', 0.0)

        # Only apply fallback if coverage is low
        if coverage >= 0.4:
            self.logger.debug(f"Coverage {coverage:.2f} is acceptable, no fallback needed")
            return hints

        self.logger.info(f"Applying fallback strategies for low coverage ({coverage:.2f})")

        keywords = analysis.get('keywords', [])
        domain = analysis.get('domain', 'general')
        tags = hints.get('tags', [])

        # Strategy 1: Keyword-to-tag mapping
        additional_tags = self.mapper.map_keywords_to_tags(keywords, tags)

        if additional_tags:
            self.logger.info(f"Found {len(additional_tags)} additional tags via keyword mapping")
            tags.extend(additional_tags)
            hints['tags'] = tags

        # Strategy 2: Hybrid query patterns
        hybrid_patterns = self.hybrid_builder.build_hybrid_patterns(keywords, tags, domain)

        if hybrid_patterns:
            self.logger.info(f"Generated {len(hybrid_patterns)} hybrid patterns")
            hints['hybrid_patterns'] = hybrid_patterns

        # Strategy 3: Generic domain enhancement
        if domain == 'general':
            self.logger.info("Applying generic domain enhancement")
            hints = self._enhance_generic_domain(hints, keywords, analysis)

        # Recalculate coverage
        original_coverage = coverage
        new_coverage = self._recalculate_coverage(hints)
        hints['coverage_score'] = new_coverage
        hints['fallback_applied'] = True
        hints['coverage_improvement'] = new_coverage - original_coverage

        self.logger.info(
            f"Fallback improved coverage: {original_coverage:.3f} → {new_coverage:.3f} "
            f"(+{hints['coverage_improvement']:.3f})"
        )

        return hints

    def _enhance_generic_domain(
        self,
        hints: Dict,
        keywords: List[str],
        analysis: Dict
    ) -> Dict:
        """
        Enhance hints for generic domain questions.

        Generic domain questions get:
        - Broad tag categories (api-category, function-purpose)
        - Subsystem tags inferred from keywords
        - File-level patterns
        """
        tags = hints.get('tags', [])

        # Add broad function-purpose tags
        broad_purposes = ['initialization', 'cleanup', 'validation', 'processing']
        for purpose in broad_purposes:
            if len(tags) < 10:  # Don't overwhelm with tags
                tags.append({
                    'tag_name': 'function-purpose',
                    'tag_value': purpose,
                    'query_fragment': f'_.tag.nameExact("function-purpose").valueExact("{purpose}")',
                    'source': 'generic-domain-fallback',
                    'confidence': 0.5
                })

        hints['tags'] = tags

        return hints

    def _recalculate_coverage(self, hints: Dict) -> float:
        """
        Recalculate coverage score after fallback.

        Coverage is proportion of enrichment layers with data.
        """
        layers = [
            'subsystems', 'function_purposes', 'data_structures',
            'algorithms', 'domain_concepts', 'architectural_roles',
            'features', 'api_categories', 'tags'
        ]

        filled_layers = sum(1 for layer in layers if hints.get(layer))

        # Also count hybrid_patterns as a layer
        if hints.get('hybrid_patterns'):
            filled_layers += 1
            layers.append('hybrid_patterns')

        return filled_layers / len(layers) if layers else 0.0


def get_fallback_selector() -> FallbackStrategySelector:
    """Get singleton fallback strategy selector."""
    global _fallback_selector

    if '_fallback_selector' not in globals():
        _fallback_selector = FallbackStrategySelector()

    return _fallback_selector
