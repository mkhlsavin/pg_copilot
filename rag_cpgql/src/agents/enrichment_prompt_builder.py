"""Enrichment-Aware Prompt Builder for CPGQL Generation.

This module builds prompts that emphasize the use of CPG enrichment tags
to improve query accuracy and coverage.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.agents.tag_effectiveness_tracker import get_global_tracker

logger = logging.getLogger(__name__)


# Comprehensive tag query patterns extracted from export_tags.sc
TAG_QUERY_PATTERNS = {
    'function-purpose': [
        # Find all methods with specific purpose
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).name.l',
        # Find callers of methods with specific purpose
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).callIn.name.dedup.l',
        # Find files containing methods with specific purpose
        'cpg.file.where(_.method.tag.nameExact("function-purpose").valueExact("{value}")).name.l',
        # Find methods with specific purpose in specific subsystem
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).where(_.tag.nameExact("subsystem-name")).name.l',
    ],

    'data-structure': [
        # Find methods operating on specific data structure
        'cpg.method.where(_.tag.nameExact("data-structure").valueExact("{value}")).name.l',
        # Find type definitions for data structure
        'cpg.typeDecl.name(".*{value}.*").l',
        # Find methods accessing specific data structure via tags
        'cpg.method.where(_.tag.nameExact("data-structure").valueExact("{value}")).file.name.dedup.l',
    ],

    'domain-concept': [
        # Find methods related to domain concept
        'cpg.method.where(_.tag.nameExact("domain-concept").valueExact("{value}")).name.l',
        # Find calls involving domain concept
        'cpg.call.where(_.method.tag.nameExact("domain-concept").valueExact("{value}")).name.dedup.l',
        # Combine name search with domain-concept tag
        'cpg.method.name(".*{value}.*").where(_.tag.nameExact("domain-concept").valueExact("{value}")).l',
    ],

    'algorithm-class': [
        # Find methods implementing specific algorithm
        'cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("{value}")).name.l',
        # Find complex algorithm implementations
        'cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("{value}")).where(_.tag.nameExact("cyclomatic-complexity")).name.l',
    ],

    'subsystem-name': [
        # Find all methods in subsystem
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{value}")).name.l',
        # Find subsystem entry points (public APIs)
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{value}")).where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find files in subsystem
        'cpg.file.where(_.method.tag.nameExact("subsystem-name").valueExact("{value}")).name.dedup.l',
    ],

    'Feature': [
        # Find files implementing feature
        'cpg.file.where(_.tag.nameExact("Feature").valueExact("{value}")).name.l',
        # Find methods implementing feature
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{value}")).name.l',
        # Find feature entry points
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{value}")).where(_.tag.nameExact("api-public")).name.l',
    ],

    'security-risk': [
        # Find high-risk functions
        'cpg.method.where(_.tag.nameExact("security-risk").valueExact("high")).name.l',
        # Find security-sensitive calls
        'cpg.call.where(_.method.tag.nameExact("security-risk")).name.dedup.l',
        # Combine security risk with domain
        'cpg.method.where(_.tag.nameExact("security-risk").valueExact("{value}")).where(_.tag.nameExact("domain-concept")).name.l',
    ],

    'api-category': [
        # Find methods by API category
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).name.l',
        # Find public APIs in category
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find typical usage patterns
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).where(_.tag.nameExact("api-typical-usage")).name.l',
    ],

    'architectural-role': [
        # Find components by architectural role
        'cpg.method.where(_.tag.nameExact("architectural-role").valueExact("{value}")).name.l',
        # Find role interactions
        'cpg.method.where(_.tag.nameExact("architectural-role").valueExact("{value}")).callIn.method.tag.nameExact("architectural-role").value.dedup.l',
    ],

    # New categories for Phase 3 expansion

    'cyclomatic-complexity': [
        # Find simple functions (low complexity)
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt <= 5).name.l',
        # Find complex functions requiring refactoring
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).name.l',
        # Find functions with specific complexity
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").valueExact("{value}")).name.l',
    ],

    'test-coverage': [
        # Find untested functions
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l',
        # Find well-tested functions
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("full")).name.l',
        # Combine untested with high complexity (high risk!)
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 10).name.l',
    ],

    'refactor-priority': [
        # Find high-priority refactor candidates
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("high")).name.l',
        # Find code needing attention
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("medium")).name.l',
        # Combine refactor priority with test coverage
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("high")).where(_.tag.nameExact("test-coverage")).name.l',
    ],

    'lines-of-code': [
        # Find very small functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").value.toInt <= 5).name.l',
        # Find large functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").value.toInt > 100).name.l',
        # Find single-line functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").valueExact("1")).name.l',
    ],

    'api-public': [
        # Find all public APIs
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find public APIs in specific file
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).file.name.dedup.l',
        # Combine public APIs with typical usage
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).where(_.tag.nameExact("api-typical-usage")).name.l',
    ],

    'api-typical-usage': [
        # Find functions with usage patterns
        'cpg.method.where(_.tag.nameExact("api-typical-usage").valueExact("{value}")).name.l',
        # Find frequently called APIs
        'cpg.method.where(_.tag.nameExact("api-typical-usage")).where(_.tag.nameExact("api-caller-count")).name.l',
    ],

    'loop-depth': [
        # Find nested loop structures
        'cpg.method.where(_.tag.nameExact("loop-depth").value.toInt > 2).name.l',
        # Find simple single-loop functions
        'cpg.method.where(_.tag.nameExact("loop-depth").valueExact("1")).name.l',
        # Combine loop depth with complexity
        'cpg.method.where(_.tag.nameExact("loop-depth").value.toInt > 2).where(_.tag.nameExact("cyclomatic-complexity")).name.l',
    ],

    # Hybrid patterns combining multiple tags
    'hybrid': [
        # Combine purpose + data-structure
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{purpose}")).where(_.tag.nameExact("data-structure").valueExact("{structure}")).name.l',
        # Combine domain + complexity filter
        'cpg.method.where(_.tag.nameExact("domain-concept").valueExact("{domain}")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt < 10).name.l',
        # Combine feature + security
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{feature}")).where(_.tag.nameExact("security-risk")).name.l',
        # Combine subsystem + test coverage (high-value pattern!)
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{subsystem}")).where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l',
        # Find complex, untested, high-refactor-priority code (technical debt!)
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).where(_.tag.nameExact("test-coverage").valueExact("untested")).where(_.tag.nameExact("refactor-priority").valueExact("high")).name.l',
        # Find public APIs with no usage documentation
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).whereNot(_.tag.nameExact("api-typical-usage")).name.l',
    ],
}


# Complexity-aware pattern selection (Phase 3)
COMPLEXITY_PATTERNS = {
    'simple': [
        # Simple patterns for straightforward queries
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).name.l',
        'cpg.file.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).name.l',
        'cpg.call.where(_.method.tag.nameExact("{tag_name}").valueExact("{value}")).name.dedup.l',
    ],
    'moderate': [
        # Moderate patterns with some filtering
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).callIn.name.dedup.l',
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).file.name.dedup.l',
        'cpg.method.where(_.tag.nameExact("{tag_name1}").valueExact("{value1}")).where(_.tag.nameExact("{tag_name2}")).name.l',
    ],
    'complex': [
        # Complex patterns with multiple filters and traversals
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt < 10).callIn.method.name.dedup.l',
        'cpg.file.where(_.method.tag.nameExact("{tag_name}").valueExact("{value}")).method.where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).where(_.tag.nameExact("test-coverage").valueExact("untested")).file.name.dedup.l',
    ]
}


# Intent-specific tag priority mappings
INTENT_TAG_PRIORITY = {
    'find-function': ['function-purpose', 'subsystem-name', 'api-category', 'domain-concept'],
    'explain-concept': ['domain-concept', 'function-purpose', 'algorithm-class', 'data-structure'],
    'trace-flow': ['function-purpose', 'subsystem-name', 'architectural-role', 'api-category'],
    'security-check': ['security-risk', 'function-purpose', 'api-category', 'domain-concept'],
    'find-bug': ['test-coverage', 'cyclomatic-complexity', 'security-risk', 'refactor-priority'],
    'analyze-component': ['subsystem-name', 'Feature', 'architectural-role', 'domain-concept'],
    'api-usage': ['api-category', 'api-public', 'api-typical-usage', 'function-purpose'],
}


@dataclass
class TagRelevance:
    """Scored tag with relevance information."""
    category: str
    value: str
    score: float
    reason: str  # Why this tag is relevant


class TagRelevanceScorer:
    """Scores enrichment tags by relevance to question and analysis."""

    def __init__(self, use_effectiveness: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_effectiveness = use_effectiveness
        self.tracker = get_global_tracker() if use_effectiveness else None

    def score_tags(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict
    ) -> List[TagRelevance]:
        """
        Score all enrichment tags by relevance.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output

        Returns:
            List of TagRelevance objects sorted by score (descending)
        """
        scored_tags = []

        intent = analysis.get('intent', 'explain-concept')
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])

        # Get intent-based priority tags
        priority_categories = INTENT_TAG_PRIORITY.get(intent, [])

        # Score each tag category
        for category, values in hints.items():
            if not values or category in ['tags', 'coverage_score']:
                # Skip tags (already processed) and coverage_score
                continue

            if not isinstance(values, list):
                # Skip non-list values
                continue

            # Base score from intent alignment
            base_score = 0.5
            if category.replace('_', '-') in priority_categories:
                base_score = 0.8
                reason = f"High-priority for {intent} intent"
            else:
                reason = f"Available tag"

            # Boost for keyword overlap
            for value in values[:5]:  # Limit to top 5 per category
                # Skip non-string values
                if not isinstance(value, str):
                    continue

                keyword_boost = 0.0
                for keyword in keywords:
                    if keyword.lower() in value.lower() or value.lower() in keyword.lower():
                        keyword_boost = 0.2
                        reason = f"Matches keyword '{keyword}'"
                        break

                # Domain alignment boost
                domain_boost = 0.0
                if domain != 'general' and domain.lower() in value.lower():
                    domain_boost = 0.1
                    reason = f"Matches domain '{domain}'"

                # Historical effectiveness boost (Phase 2 enhancement)
                effectiveness_boost = 0.0
                if self.use_effectiveness and self.tracker:
                    # Map category to tag name format
                    tag_name = category.replace('_', '-')
                    if tag_name.endswith('s'):  # Remove plural
                        tag_name = tag_name[:-1]

                    effectiveness = self.tracker.get_tag_effectiveness(tag_name, value)

                    # If effectiveness is significantly different from neutral (0.5):
                    # Boost for high-performing tags (>0.6)
                    # Penalize for low-performing tags (<0.4)
                    if effectiveness > 0.6:
                        effectiveness_boost = 0.15 * (effectiveness - 0.5)
                        reason = f"High-performing tag (score={effectiveness:.2f})"
                    elif effectiveness < 0.4:
                        effectiveness_boost = -0.1 * (0.5 - effectiveness)
                        # Keep original reason but note low performance

                final_score = min(1.0, max(0.0, base_score + keyword_boost + domain_boost + effectiveness_boost))

                scored_tags.append(TagRelevance(
                    category=category,
                    value=value,
                    score=final_score,
                    reason=reason
                ))

        # Sort by score
        scored_tags.sort(key=lambda t: t.score, reverse=True)

        return scored_tags


class EnrichmentPromptBuilder:
    """Builds enrichment-focused prompts for CPGQL generation."""

    def __init__(self, enable_documentation: bool = True, enable_cfg: bool = True, enable_ddg: bool = True):
        self.scorer = TagRelevanceScorer()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enable_documentation = enable_documentation
        self.enable_cfg = enable_cfg
        self.enable_ddg = enable_ddg

        # Initialize documentation retriever if enabled
        self.doc_retriever = None
        if enable_documentation:
            try:
                from src.retrieval.documentation_retriever import DocumentationRetriever
                self.doc_retriever = DocumentationRetriever()
                self.logger.info("Documentation retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize documentation retriever: {e}")
                self.enable_documentation = False

        # Initialize CFG pattern retriever if enabled
        self.cfg_retriever = None
        if enable_cfg:
            try:
                from src.retrieval.cfg_retriever import CFGRetriever
                self.cfg_retriever = CFGRetriever()
                self.logger.info("CFG pattern retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize CFG retriever: {e}")
                self.enable_cfg = False

        # Initialize DDG pattern retriever if enabled
        self.ddg_retriever = None
        if enable_ddg:
            try:
                from src.retrieval.ddg_retriever import DDGRetriever
                self.ddg_retriever = DDGRetriever()
                self.logger.info("DDG pattern retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize DDG retriever: {e}")
                self.enable_ddg = False

    def build_enrichment_context(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict,
        max_tags: int = 7,
        max_patterns: int = 5
    ) -> str:
        """
        Build enrichment context section for CPGQL generation prompt.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output
            max_tags: Maximum number of tags to show
            max_patterns: Maximum number of query patterns to show

        Returns:
            Formatted enrichment context string
        """
        if not hints or all(not v for v in hints.values()):
            return ""

        # Score and select top tags
        scored_tags = self.scorer.score_tags(hints, question, analysis)
        top_tags = scored_tags[:max_tags]

        if not top_tags:
            return ""

        intent = analysis.get('intent', 'explain-concept')

        # Determine query complexity (Phase 3 enhancement)
        complexity = self._determine_query_complexity(question, analysis, len(top_tags))

        # Build context
        lines = []
        lines.append("🏷️  **ENRICHMENT TAGS** (Use these in your CPGQL query!):")
        lines.append("")

        # Group tags by category
        by_category = {}
        for tag in top_tags:
            if tag.category not in by_category:
                by_category[tag.category] = []
            by_category[tag.category].append(tag)

        # Show tags by category
        for category, tags in list(by_category.items())[:5]:  # Max 5 categories
            category_name = category.replace('_', '-')
            tag_values = [f'"{t.value}"' for t in tags[:3]]  # Max 3 values per category

            lines.append(f"• {category_name}: {', '.join(tag_values)}")

        lines.append("")
        lines.append(f"**Tag Query Patterns** ({complexity} complexity):")

        # Generate specific patterns for top tags
        patterns_shown = 0
        for tag in top_tags[:3]:  # Use top 3 tags for patterns
            category_key = tag.category.replace('_', '-')

            # Map plural forms to singular forms for TAG_QUERY_PATTERNS lookup
            category_mapping = {
                'function-purposes': 'function-purpose',
                'domain-concepts': 'domain-concept',
                'data-structures': 'data-structure',
                'subsystems': 'subsystem-name',
                'features': 'Feature',
                'api-categories': 'api-category',
                'architectural-roles': 'architectural-role',
                'algorithms': 'algorithm-class',
            }

            lookup_key = category_mapping.get(category_key, category_key)

            if lookup_key in TAG_QUERY_PATTERNS:
                templates = TAG_QUERY_PATTERNS[lookup_key]

                # Pick best template for intent and complexity (Phase 3)
                template = self._select_template_for_intent(templates, intent, complexity)
                pattern = template.replace('{value}', tag.value)

                lines.append(f"• {pattern}")
                patterns_shown += 1

                if patterns_shown >= max_patterns:
                    break

        # Add complexity-appropriate fallback patterns if needed
        if patterns_shown < max_patterns and complexity in COMPLEXITY_PATTERNS:
            lines.append("")
            lines.append(f"**General {complexity} patterns:**")

            fallback_patterns = COMPLEXITY_PATTERNS[complexity][:max_patterns - patterns_shown]
            for pattern in fallback_patterns:
                lines.append(f"• {pattern}")

        # Phase 4: Show hybrid patterns from fallback strategies if available
        if hints.get('hybrid_patterns'):
            lines.append("")
            lines.append("**Hybrid Patterns** (name + tag matching):")
            for pattern in hints['hybrid_patterns'][:3]:  # Show top 3
                lines.append(f"• {pattern}")

        # Add hybrid pattern hint if multiple tags available
        if len(top_tags) >= 2:
            lines.append("")
            lines.append("**Combine tags for precise queries:**")
            lines.append("• Use .where() multiple times to combine tag filters")
            lines.append(f'  Example: cpg.method.where(_.tag.nameExact(...)).where(_.tag.nameExact(...)).name.l')

        # Phase 4: Show fallback status if applied
        if hints.get('fallback_applied'):
            lines.append("")
            improvement = hints.get('coverage_improvement', 0.0)
            lines.append(f"📈 Fallback strategies applied (+{improvement:.3f} coverage boost)")

        return '\n'.join(lines)

    def _determine_query_complexity(self, question: str, analysis: Dict, num_tags: int) -> str:
        """
        Determine appropriate query complexity level based on question characteristics.

        Returns: 'simple', 'moderate', or 'complex'
        """
        intent = analysis.get('intent', 'explain-concept')
        keywords = analysis.get('keywords', [])

        # Simple queries: single keyword, find-function intent
        if intent == 'find-function' and len(keywords) <= 2 and num_tags <= 2:
            return 'simple'

        # Complex queries: multiple tags, trace-flow, security-check
        if intent in ['trace-flow', 'security-check', 'find-bug']:
            return 'complex'

        # Complex queries: many keywords or tags
        if len(keywords) >= 4 or num_tags >= 4:
            return 'complex'

        # Long questions tend to be more complex
        if len(question) > 100:
            return 'moderate'

        # Default: moderate complexity
        return 'moderate'

    def _select_template_for_intent(self, templates: List[str], intent: str, complexity: str = 'moderate') -> str:
        """
        Select most appropriate template for given intent and complexity.

        Args:
            templates: Available template patterns
            intent: Query intent (find-function, trace-flow, etc.)
            complexity: Query complexity level (simple, moderate, complex)

        Returns:
            Selected template string
        """
        # First, filter by complexity if we have enough templates
        complexity_filtered = []

        if complexity == 'simple':
            # Simple queries: prefer single-filter patterns
            complexity_filtered = [t for t in templates if t.count('.where(') <= 1 and 'callIn' not in t]
        elif complexity == 'complex':
            # Complex queries: prefer multi-filter or traversal patterns
            complexity_filtered = [t for t in templates if t.count('.where(') >= 2 or 'callIn' in t or 'callOut' in t]

        # If complexity filtering yielded results, use those; otherwise use all
        search_pool = complexity_filtered if complexity_filtered else templates

        # Intent-based template selection heuristics
        if intent == 'find-function':
            # Prefer patterns that return method names
            for t in search_pool:
                if '.method.' in t and '.name.l' in t and 'callIn' not in t:
                    return t

        elif intent == 'trace-flow':
            # Prefer patterns with callIn/callOut
            for t in search_pool:
                if 'callIn' in t or 'callOut' in t:
                    return t

        elif intent == 'security-check':
            # Prefer patterns with security context
            for t in search_pool:
                if 'security' in t or 'risk' in t:
                    return t

        elif intent == 'explain-concept':
            # Prefer patterns that show relationships
            for t in search_pool:
                if 'file' in t or 'callIn' in t:
                    return t

        elif intent == 'find-bug':
            # Prefer patterns with quality metrics
            for t in search_pool:
                if 'test-coverage' in t or 'cyclomatic-complexity' in t:
                    return t

        elif intent == 'api-usage':
            # Prefer patterns with API tags
            for t in search_pool:
                if 'api-public' in t or 'api-category' in t:
                    return t

        # Fallback: return first from search pool or first from templates
        return search_pool[0] if search_pool else templates[0]

    def get_tag_usage_guidance(self, intent: str) -> str:
        """Get intent-specific guidance for using tags."""
        guidance = {
            'find-function': (
                "Focus on function-purpose and subsystem-name tags. "
                "Use .where(_.tag.nameExact(...)) to filter by semantic purpose."
            ),
            'explain-concept': (
                "Use domain-concept and function-purpose tags. "
                "Combine tags with .callIn to show how concept is used."
            ),
            'trace-flow': (
                "Use function-purpose and architectural-role tags. "
                "Chain .callIn and .callOut to trace execution paths."
            ),
            'security-check': (
                "Prioritize security-risk tags. "
                "Filter by risk level: .where(_.tag.nameExact('security-risk').valueExact('high'))"
            ),
            'find-bug': (
                "Use test-coverage and cyclomatic-complexity tags. "
                "Find untested complex code: .where(_.tag.nameExact('test-coverage').valueExact('untested'))"
            ),
            'analyze-component': (
                "Use subsystem-name and Feature tags. "
                "Find component boundaries with .file.where(_.tag.nameExact('Feature'))"
            ),
            'api-usage': (
                "Use api-category and api-public tags. "
                "Find public APIs: .where(_.tag.nameExact('api-public').valueExact('true'))"
            ),
        }

        return guidance.get(intent, "Use enrichment tags with .where(_.tag.nameExact(...).valueExact(...)) to filter results.")

    def build_documentation_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build documentation context from code comments.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of documentation entries to retrieve

        Returns:
            Formatted documentation context string
        """
        if not self.enable_documentation or not self.doc_retriever:
            return ""

        try:
            # Retrieve relevant documentation
            result = self.doc_retriever.retrieve_relevant_documentation(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant documentation
            if not result['documentation'] or result['stats']['avg_relevance'] < 0.25:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving documentation: {e}")
            return ""

    def build_cfg_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build CFG pattern context for execution flow understanding.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of CFG patterns to retrieve

        Returns:
            Formatted CFG pattern context string
        """
        if not self.enable_cfg or not self.cfg_retriever:
            return ""

        try:
            # Retrieve relevant CFG patterns
            result = self.cfg_retriever.retrieve_relevant_patterns(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.25:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving CFG patterns: {e}")
            return ""

    def build_ddg_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build DDG pattern context for data flow understanding.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of DDG patterns to retrieve

        Returns:
            Formatted DDG pattern context string
        """
        if not self.enable_ddg or not self.ddg_retriever:
            return ""

        try:
            # Retrieve relevant DDG patterns
            result = self.ddg_retriever.retrieve_relevant_patterns(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.25:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving DDG patterns: {e}")
            return ""

    def build_full_enrichment_prompt(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict,
        max_tags: int = 7,
        max_patterns: int = 5,
        include_documentation: bool = True,
        include_cfg: bool = True,
        include_ddg: bool = True
    ) -> str:
        """
        Build complete enrichment prompt including tags, documentation, CFG patterns, and DDG patterns.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output
            max_tags: Maximum number of tags to show
            max_patterns: Maximum number of query patterns to show
            include_documentation: Whether to include code documentation
            include_cfg: Whether to include CFG execution flow patterns
            include_ddg: Whether to include DDG data flow patterns

        Returns:
            Complete formatted enrichment prompt
        """
        sections = []

        # 1. Documentation context (WHAT functions do)
        if include_documentation:
            doc_context = self.build_documentation_context(question, analysis, top_k=3)
            if doc_context:
                sections.append(doc_context)

        # 2. CFG pattern context (HOW functions execute)
        if include_cfg:
            cfg_context = self.build_cfg_context(question, analysis, top_k=3)
            if cfg_context:
                sections.append(cfg_context)

        # 3. DDG pattern context (WHERE data flows) - Phase 3
        if include_ddg:
            ddg_context = self.build_ddg_context(question, analysis, top_k=3)
            if ddg_context:
                sections.append(ddg_context)

        # 4. Enrichment tags context (semantic search)
        tag_context = self.build_enrichment_context(
            hints, question, analysis, max_tags, max_patterns
        )
        if tag_context:
            sections.append(tag_context)

        # 5. Intent-specific guidance
        intent = analysis.get('intent', 'explain-concept')
        guidance = self.get_tag_usage_guidance(intent)
        if guidance:
            sections.append("")
            sections.append(f"**Guidance**: {guidance}")

        return '\n\n'.join(sections)
