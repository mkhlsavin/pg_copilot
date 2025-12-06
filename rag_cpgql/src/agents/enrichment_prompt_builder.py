"""Enrichment-Aware Prompt Builder for CPGQL Generation.

This module builds prompts that emphasize the use of CPG enrichment tags
to improve query accuracy and coverage.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.agents.tag_effectiveness_tracker import get_global_tracker
from src.validation.tag_validator import get_validator

from ._tag_query_patterns import TAG_QUERY_PATTERNS, COMPLEXITY_PATTERNS, INTENT_TAG_PRIORITY

logger = logging.getLogger(__name__)






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

        # Initialize tag validator
        try:
            self.validator = get_validator()
            self.logger.info("Tag validator initialized successfully")
        except Exception as e:
            self.logger.warning(f"Could not initialize tag validator: {e}")
            self.validator = None

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

    def _validate_and_filter_hints(self, hints: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Validate and filter enrichment hints to keep only valid CPG tags.

        Args:
            hints: Raw enrichment hints with potentially invalid tag values

        Returns:
            Filtered hints containing only valid tag values
        """
        if not self.validator or not hints:
            return hints

        filtered_hints = {}
        invalid_count = 0
        corrected_count = 0

        for category, values in hints.items():
            # Skip non-tag fields
            if category in ['tags', 'coverage_score', 'fallback_applied', 'coverage_improvement', 'hybrid_patterns']:
                filtered_hints[category] = values
                continue

            if not isinstance(values, list):
                filtered_hints[category] = values
                continue

            # Map category names to tag names (e.g., "function_purposes" -> "function-purpose")
            tag_name = category.replace('_', '-')
            if tag_name.endswith('ies'):
                tag_name = tag_name[:-3] + 'y'
            elif tag_name.endswith('s'):
                tag_name = tag_name[:-1]

            # Validate each value
            valid_values = []
            for value in values:
                if not isinstance(value, str):
                    valid_values.append(value)
                    continue

                is_valid, corrected = self.validator.validate_and_correct(tag_name, value)

                if is_valid:
                    if corrected:
                        # Use corrected value
                        valid_values.append(corrected)
                        corrected_count += 1
                        self.logger.info(f"Corrected tag: {category}='{value}' -> '{corrected}'")
                    else:
                        # Original value is valid
                        valid_values.append(value)
                else:
                    # Invalid and no correction available
                    invalid_count += 1
                    self.logger.warning(f"Filtered invalid tag: {category}='{value}' (not in CPG)")

                    # Try to suggest valid alternatives
                    valid_alternatives = self.validator.get_valid_values(tag_name)
                    if valid_alternatives:
                        self.logger.debug(f"  Valid {tag_name} values: {', '.join(valid_alternatives[:5])}")

            if valid_values:
                filtered_hints[category] = valid_values

        if invalid_count > 0 or corrected_count > 0:
            self.logger.info(f"Tag validation: {corrected_count} corrected, {invalid_count} removed")

        return filtered_hints

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

        # Validate and filter hints to keep only valid CPG tags
        hints = self._validate_and_filter_hints(hints)

        if not hints or all(not v for v in hints.values()):
            self.logger.warning("No valid tags remaining after validation")
            return ""

        # Score and select top tags
        scored_tags = self.scorer.score_tags(hints, question, analysis)
        top_tags = scored_tags[:max_tags]

        # Ensure control reasons surface when available (Category 7 linkage)
        control_values = hints.get('control_reasons', [])
        if control_values:
            control_index = next((idx for idx, tag in enumerate(top_tags) if tag.category == 'control_reasons'), None)
            if control_index is None:
                control_tag = TagRelevance(
                    category='control_reasons',
                    value=control_values[0],
                    score=1.0,
                    reason='Critical control rationale for flow analysis'
                )
            else:
                control_tag = top_tags.pop(control_index)
                control_tag.score = max(control_tag.score, 0.95)
            # Prepend control reason and trim to maintain max_tags limit
            top_tags = [control_tag] + top_tags[:max_tags - 1]

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
                # Category 1: Parameter & Return
                'param-roles': 'param-role',
                'return-kinds': 'return-kind',
                'return-outcomes': 'return-outcome',
                'validation-required': 'validation-required',
                # Category 2: Variable & Identifier
                'variable-roles': 'variable-role',
                'data-kinds': 'data-kind',
                'security-sensitivities': 'security-sensitivity',
                'lifetimes': 'lifetime',
                'mutabilities': 'mutability',
                'is-locks': 'is-lock',
                'is-pointer-to-structs': 'is-pointer-to-struct',
                # Category 3: Type & Member
                'type-categories': 'type-category',
                'type-domain-entities': 'type-domain-entity',
                'type-concurrency-primitives': 'type-concurrency-primitive',
                'type-ownership-models': 'type-ownership-model',
                'member-roles': 'member-role',
                'member-pointers': 'member-pointer',
                'member-length-fields': 'member-length-field',
                # Category 4: Literal & Constant
                'literal-kinds': 'literal-kind',
                'literal-domains': 'literal-domain',
                'literal-severities': 'literal-severity',
                'is-null-constants': 'is-null-constant',
                'is-bitmasks': 'is-bitmask',
                'literal-constants': 'literal-constant',
                'is-lock-constants': 'is-lock-constant',
                # Category 5: Control Flow & Jump
                'jump-kinds': 'jump-kind',
                'jump-domains': 'jump-domain',
                'jump-scopes': 'jump-scope',
                'modifier-concurrencies': 'modifier-concurrency',
                'modifier-attributes': 'modifier-attribute',
                # Category 6: Namespace & Reference
                'namespace-layers': 'namespace-layer',
                'namespace-domains': 'namespace-domain',
                'method-ref-kinds': 'method-ref-kind',
                'method-ref-usages': 'method-ref-usage',
                # Category 7: Data Flow & Edge
                'data-flow-kinds': 'data-flow-kind',
                'child-roles': 'child-role',
                'call-actions': 'call-action',
                'call-side-effects': 'call-side-effect',
                'call-receiver-roles': 'call-receiver-role',
                'argument-param-names': 'argument-param-name',
                'branch-kinds': 'branch-kind',
                'control-reasons': 'control-reason',
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
            # Lowered threshold from 0.25 to 0.10 to allow more documentation context
            if not result['documentation'] or result['stats']['avg_relevance'] < 0.10:
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
            # Lowered threshold from 0.25 to 0.10 to allow more CFG patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.10:
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
            # Lowered threshold from 0.25 to 0.10 to allow more DDG patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.10:
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
