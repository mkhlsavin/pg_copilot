# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
#
# DO NOT add:
#   - Hardcoded function names (pg_*, elog, palloc, etc.)
#   - Hardcoded SQL patterns with domain-specific terms
#   - Inline LLM prompts (use PromptRegistry)
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""Generator Agent - Generates SQL queries with enriched context."""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from src.agents.enrichment_prompt_builder import EnrichmentPromptBuilder
from src.workflow._plugin_helpers import get_domain_display_name_from_plugin
from src.agents.tag_effectiveness_tracker import get_global_tracker

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """
    Generator Agent for SQL query generation.

    Generates queries using:
    - SQLQueryGenerator with pattern matching
    - Retrieved Q&A examples
    - Retrieved SQL examples
    - Enrichment tag context
    """

    def __init__(self, sql_generator, enable_feedback: bool = True, use_semantic: bool = False):
        """
        Initialize Generator Agent.

        Args:
            sql_generator: SQLQueryGenerator instance
            enable_feedback: Whether to record tag effectiveness feedback
            use_semantic: Whether to use semantic prompts (comment-based Q&A) instead of tag-search
        """
        self.generator = sql_generator
        self.enrichment_builder = EnrichmentPromptBuilder()
        self.enable_feedback = enable_feedback
        self.tracker = get_global_tracker() if enable_feedback else None
        self.use_semantic = use_semantic

        # Import semantic prompts if enabled
        if self.use_semantic:
            # Use SIMPLIFIED semantic prompts for better LLM compliance
            from src.generation.prompts_semantic_simple import (
                CPGQL_SEMANTIC_SIMPLE_SYSTEM_PROMPT,
                CPGQL_SEMANTIC_SIMPLE_USER_PROMPT
            )
            self.semantic_system_prompt = CPGQL_SEMANTIC_SIMPLE_SYSTEM_PROMPT
            self.semantic_user_prompt = CPGQL_SEMANTIC_SIMPLE_USER_PROMPT
            logger.info("Semantic mode ENABLED - using SIMPLIFIED comment-based prompts")

    def generate(
        self,
        question: str,
        context: Dict
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Generate SQL query with full RAG context.

        Args:
            question: Natural language question
            context: Retrieved context with:
                - similar_qa: Similar Q&A pairs
                - sql_examples: SQL examples
                - analysis: Question analysis
                - enrichment_hints: Enrichment tags

        Returns:
            (query, is_valid, error_message)
        """
        # Build enriched prompt
        prompt = self._build_enriched_prompt(question, context)

        logger.debug(f"Generated prompt length: {len(prompt)} chars")

        # Generate query
        try:
            # Choose prompt based on mode
            if self.use_semantic:
                # SEMANTIC MODE: Use comment-based question answering prompts
                semantic_prompt = self._build_semantic_prompt(question, context)
                raw_output = self.generator.llm.generate_simple(
                    prompt=semantic_prompt,
                    max_tokens=500,  # Longer for structured Map() queries
                    temperature=0.3,
                    grammar=None  # No grammar for semantic queries (more flexible)
                )
                # Log raw output for debugging
                logger.debug(f"Raw LLM output (first 300 chars): {raw_output[:300]}")
                query = self._extract_query(raw_output)
                logger.info(f"Generated SEMANTIC query: {query[:150]}...")

            else:
                # STANDARD MODE: Use tag-based prompts
                # Build simplified prompt for better output
                simple_prompt = self._build_simple_prompt(question, context)

                # Generate with or without grammar
                if self.use_grammar:
                    query = self.generator.generate_query(
                        question=question,
                        enrichment_hints=self._format_enrichment_hints(context),
                        max_tokens=300,
                        temperature=0.6
                    )
                else:
                    # Direct generation without grammar
                    raw_output = self.generator.llm.generate_simple(
                        prompt=simple_prompt,
                        max_tokens=300,
                        temperature=0.3
                    )
                    # Extract query from output
                    query = self._extract_query(raw_output)

            # Validate
            is_valid, error = self.generator.validate_query(query)

            if is_valid:
                logger.info(f"Generated valid query: {query}")
            else:
                logger.warning(f"Generated invalid query: {error}")

            # Record tag effectiveness feedback (Phase 2)
            if self.enable_feedback and 'enrichment_hints' in context:
                self._record_tag_feedback(context, is_valid)

            return query, is_valid, error

        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            return "cpg.method.name.l", False, str(e)

    def _build_enriched_prompt(self, question: str, context: Dict) -> str:
        """
        Build enriched prompt with RAG context.

        Includes:
        - Enrichment tag context
        - Similar Q&A examples
        - Relevant CPGQL examples
        - Domain-specific guidance
        """
        prompt_parts = []

        # 1. System context - domain-agnostic
        domain_name = get_domain_display_name_from_plugin()
        prompt_parts.append(
            f"You are a CPGQL expert generating queries for {domain_name} code analysis.\n"
            "The Code Property Graph has been enriched with semantic tags.\n"
        )

        # 2. Enrichment context (Phase 3 enhanced with three-dimensional code context)
        if 'enrichment_hints' in context:
            # Use full enrichment prompt builder with Phase 3 DDG integration
            # This includes:
            #   - Documentation context (WHAT functions do)
            #   - CFG patterns (HOW functions execute)
            #   - DDG patterns (WHERE data flows) <- Phase 3!
            #   - Enrichment tags (semantic search)
            enrichment_text = self.enrichment_builder.build_full_enrichment_prompt(
                hints=context['enrichment_hints'],
                question=question,
                analysis=context.get('analysis', {}),
                max_tags=7,
                max_patterns=5,
                include_documentation=True,
                include_cfg=True,
                include_ddg=True  # Enable Phase 3 DDG integration!
            )
            if enrichment_text:
                prompt_parts.append(f"\n=== Enrichment Context ===\n{enrichment_text}\n")

        # 3. Similar Q&A examples
        if context.get('similar_qa'):
            qa_text = self._format_qa_examples(context['similar_qa'])
            prompt_parts.append(f"\n=== Similar Questions ===\n{qa_text}\n")

        # 4. CPGQL examples
        if context.get('sql_examples'):
            cpgql_text = self._format_sql_examples(context['sql_examples'])
            prompt_parts.append(f"\n=== CPGQL Examples ===\n{cpgql_text}\n")

        # 5. Domain-specific guidance
        if context.get('analysis'):
            guidance = self._get_domain_guidance(context['analysis'])
            if guidance:
                prompt_parts.append(f"\n=== Domain Guidance ===\n{guidance}\n")

        # 6. Query generation instruction
        prompt_parts.append(
            f"\n=== Task ===\n"
            f"Generate a CPGQL query to answer:\n\n"
            f"Question: {question}\n\n"
            f"CPGQL Query:"
        )

        return '\n'.join(prompt_parts)

    def _format_enrichment_context(self, hints: Dict) -> str:
        """Format enrichment hints for prompt using enhanced prompt builder."""
        # Extract question and analysis from context if available
        # For now, use hints directly - full context integration comes from _build_enriched_prompt
        lines = []

        # Use new enrichment builder for better tag presentation
        domain_name = get_domain_display_name_from_plugin()
        if hints.get('features'):
            lines.append(f"🎯 {domain_name} Features: {', '.join(hints['features'][:5])}")

        if hints.get('function_purposes'):
            lines.append(f"🔧 Function Purposes: {', '.join(hints['function_purposes'][:7])}")

        if hints.get('data_structures'):
            lines.append(f"📊 Data Structures: {', '.join(hints['data_structures'][:7])}")

        if hints.get('domain_concepts'):
            lines.append(f"🏛️  Domain Concepts: {', '.join(hints['domain_concepts'][:7])}")

        if hints.get('subsystems'):
            lines.append(f"⚙️  Subsystems: {', '.join(hints['subsystems'][:5])}")

        if hints.get('algorithms'):
            lines.append(f"📐 Algorithms: {', '.join(hints['algorithms'][:5])}")

        # Show MORE tag-based query examples (increased from 3 to 7)
        if hints.get('tags'):
            lines.append("\n🏷️  **IMPORTANT: Use enrichment tags in your query!**")
            lines.append("Tag-based query patterns:")
            for i, tag in enumerate(hints['tags'][:7], 1):
                example = f"  {i}. cpg.method.where({tag['query_fragment']}).name.l"
                lines.append(example)

            lines.append("\n💡 Combine multiple tags with multiple .where() calls for precise filtering")

        return '\n'.join(lines)

    def _format_qa_examples(self, qa_pairs: List[Dict]) -> str:
        """Format similar Q&A pairs for prompt."""
        lines = []

        for i, qa in enumerate(qa_pairs[:3], 1):  # Top 3
            question = qa['question'][:100]  # Truncate
            answer = qa['answer'][:200]  # Truncate

            lines.append(f"{i}. Q: {question}...")
            lines.append(f"   A: {answer}...")
            lines.append("")

        return '\n'.join(lines)

    def _format_sql_examples(self, examples: List[Dict]) -> str:
        """Format CPGQL examples for prompt."""
        lines = []

        for i, ex in enumerate(examples[:5], 1):  # Top 5
            question = ex.get('question', '')[:80]
            query = ex.get('query', '')[:150]

            if question and query:
                lines.append(f"{i}. Q: {question}...")
                lines.append(f"   Query: {query}")
                lines.append("")

        return '\n'.join(lines)

    def _get_domain_guidance(self, analysis: Dict) -> str:
        """Get domain-specific query guidance."""
        domain = analysis.get('domain', 'general')
        intent = analysis.get('intent', 'explain-concept')

        # CRITICAL: Detect conceptual questions that need rich CPGQL traversals
        # These questions ask "how/why/what" and need comments, AST, CFG, DDG - not just tags!
        conceptual_keywords_ru = ['как устроено', 'как работает', 'как реализовано', 'как выполняется',
                                  'зачем', 'почему', 'что делает', 'объясни']
        conceptual_keywords_en = ['how does', 'how is', 'how are', 'why does', 'why is',
                                  'what does', 'what is', 'explain', 'describe']
        conceptual_intents = ['explain-concept', 'trace-flow', 'understand-implementation']

        question = analysis.get('question', '').lower() if isinstance(analysis.get('question'), str) else ''

        is_conceptual = (
            intent in conceptual_intents or
            any(keyword in question for keyword in conceptual_keywords_ru) or
            any(keyword in question for keyword in conceptual_keywords_en)
        )

        if is_conceptual:
            return (
                "\n" + "="*80 + "\n"
                "⚠️  CONCEPTUAL QUESTION DETECTED!\n"
                "="*80 + "\n"
                "DO NOT generate tag-only queries that return just method names!\n"
                "Use RICH CPGQL traversals to provide meaningful answers:\n\n"
                "1. **Access Documentation**: cpg.comment.code('.*keyword.*').method.name.l\n"
                "   - Start with comments to find documented functions\n"
                "   - Example: cpg.comment.code('.*visibility.*').method.where(_.tag.nameExact('domain-concept').valueExact('mvcc')).name.l\n\n"
                "2. **Examine Control Flow**: .ast.isControlStructure.code.l\n"
                "   - Get if/while/for statements to understand logic\n"
                "   - Example: cpg.method.name('.*snapshot.*').ast.isControlStructure.code.l\n\n"
                "3. **Trace Data Flow**: .reachableBy(...)\n"
                "   - Follow parameter usage and variable flow\n"
                "   - Example: cpg.method.name('heap_fetch').parameter.reachableBy(cpg.identifier).code.l\n\n"
                "4. **Get Method Bodies**: .body.l or .ast.code.l\n"
                "   - Retrieve actual implementation code\n"
                "   - Example: cpg.method.name('.*transaction.*').where(_.tag.nameExact('domain-concept').valueExact('acid')).body.l\n\n"
                "5. **Combine Tags with Traversals**:\n"
                "   - Use tags for filtering, then traverse for rich context\n"
                "   - Example: cpg.method.where(_.tag.nameExact('function-purpose').valueExact('transaction-control')).ast.isControlStructure.code.l\n\n"
                "REMEMBER: For 'how/why/what' questions, tags alone are NOT enough!\n"
                "="*80 + "\n"
            )

        guidance_map = {
            'vacuum': (
                "For vacuum queries:\n"
                "- Look for autovacuum* files and functions\n"
                "- Check for freeze, analyze, and maintenance operations\n"
                "- Consider heap, tuple, and page-level operations"
            ),
            'wal': (
                "For WAL queries:\n"
                "- Look for xlog* files and wal* functions\n"
                "- Consider checkpoint, recovery, and replay operations\n"
                "- Check buffer management and log writing"
            ),
            'mvcc': (
                "For MVCC queries:\n"
                "- Look for snapshot, visibility, and transaction functions\n"
                "- Consider procarray, tqual, and visibility checks\n"
                "- Check TransactionId and snapshot management"
            ),
            'query-planning': (
                "For query planning queries:\n"
                "- Look for planner, optimizer, and executor files\n"
                "- Consider cost estimation and path generation\n"
                "- Check plan nodes and execution strategies"
            ),
            'indexes': (
                "For index queries:\n"
                "- Look for nbtree, gin, gist, brin, hash access methods\n"
                "- Consider index scan and bitmap operations\n"
                "- Check index maintenance and build operations"
            )
        }

        # Intent-specific guidance
        intent_guidance = {
            'find-function': (
                "\nFocus on: Use .name patterns to find specific functions\n"
                "Example: cpg.method.name(\".*vacuum.*\").l"
            ),
            'security-check': (
                "\nFocus on: Use security-pattern tags and risk classifications\n"
                "Example: cpg.method.where(_.tag.nameExact(\"risk-level\").valueExact(\"high\")).l"
            )
        }

        guidance_parts = []

        if domain in guidance_map:
            guidance_parts.append(guidance_map[domain])

        if intent in intent_guidance:
            guidance_parts.append(intent_guidance[intent])

        return '\n'.join(guidance_parts)

    def _format_enrichment_hints(self, context: Dict) -> Optional[str]:
        """Format enrichment hints for generator interface."""
        if 'enrichment_hints' not in context:
            return None

        hints = context['enrichment_hints']

        # Format as simple string for backward compatibility
        parts = []

        if hints.get('features'):
            parts.append(f"Features: {', '.join(hints['features'][:3])}")

        if hints.get('function_purposes'):
            parts.append(f"Purposes: {', '.join(hints['function_purposes'][:3])}")

        if hints.get('tags'):
            top_tag = hints['tags'][0] if hints['tags'] else None
            if top_tag:
                parts.append(f"Top tag: {top_tag['query_fragment']}")

        return ' | '.join(parts) if parts else None

    def generate_with_retries(
        self,
        question: str,
        context: Dict,
        max_retries: int = 2
    ) -> Tuple[str, bool, Optional[str], int]:
        """
        Generate query with automatic retries on validation failure.

        Args:
            question: Natural language question
            context: Retrieved context
            max_retries: Maximum retry attempts

        Returns:
            (query, is_valid, error_message, attempts)
        """
        for attempt in range(max_retries + 1):
            query, is_valid, error = self.generate(question, context)

            if is_valid:
                logger.info(f"Generated valid query on attempt {attempt + 1}")
                return query, is_valid, error, attempt + 1

            logger.warning(f"Attempt {attempt + 1} failed: {error}")

            # On retry, add error feedback to context
            if attempt < max_retries:
                context['previous_error'] = error
                context['previous_query'] = query

        # All retries exhausted
        logger.error(f"Failed to generate valid query after {max_retries + 1} attempts")
        return query, False, error, max_retries + 1

    def generate_batch(
        self,
        questions: List[str],
        contexts: List[Dict]
    ) -> List[Dict]:
        """
        Generate queries for multiple questions.

        Args:
            questions: List of questions
            contexts: List of contexts (one per question)

        Returns:
            List of results with query, validity, error
        """
        results = []

        for i, (question, context) in enumerate(zip(questions, contexts)):
            logger.info(f"Generating query {i+1}/{len(questions)}")

            query, is_valid, error = self.generate(question, context)

            results.append({
                'question': question,
                'query': query,
                'valid': is_valid,
                'error': error
            })

        valid_count = sum(1 for r in results if r['valid'])
        logger.info(f"Batch generation: {valid_count}/{len(results)} valid queries")

        return results

    def explain_query(self, query: str, context: Dict) -> str:
        """
        Generate natural language explanation of a CPGQL query.

        Args:
            query: CPGQL query
            context: Original question context

        Returns:
            Natural language explanation
        """
        # Parse query components
        explanation_parts = []

        if 'cpg.method' in query:
            explanation_parts.append("This query searches for methods/functions")

        if 'cpg.call' in query:
            explanation_parts.append("This query searches for function calls")

        if 'cpg.file' in query:
            explanation_parts.append("This query searches for files")

        if '.where(' in query or 'filter(' in query:
            explanation_parts.append("with specific filtering criteria")

        if '.tag.' in query:
            explanation_parts.append("using enrichment tags for semantic filtering")

        if '.name(' in query:
            name_match = query.split('.name(')[1].split(')')[0] if '.name(' in query else None
            if name_match:
                explanation_parts.append(f"matching name pattern: {name_match}")

        if '.take(' in query:
            explanation_parts.append("limiting results for performance")

        explanation = ' '.join(explanation_parts)

        return explanation if explanation else "Query retrieves code elements from the CPG"

    def _build_simple_prompt(self, question: str, context: Dict) -> str:
        """Build simplified prompt without grammar (for better readability)."""
        prompt_parts = []

        # System instruction with STRONG tag emphasis - domain-agnostic
        domain_name = get_domain_display_name_from_plugin()
        prompt_parts.append(
            f"You are a CPGQL query generator for {domain_name} code analysis.\n"
            "IMPORTANT: The CPG has semantic enrichment tags. ALWAYS use tag-based filtering!\n\n"
            "Single-Tag Query Pattern:\n"
            "cpg.method.where(_.tag.nameExact(\"tag-name\").valueExact(\"value\")).name.l\n\n"
            "Multi-Tag Query Pattern (PREFERRED for precision):\n"
            "cpg.method.where(_.tag.nameExact(\"function-purpose\").valueExact(\"storage-access\"))"
            ".where(_.tag.nameExact(\"data-structure\").valueExact(\"buffer\")).name.l\n"
        )

        # Add enrichment hints with CONCRETE EXAMPLES including multi-tag
        if context.get('enrichment_hints'):
            hints = context['enrichment_hints']
            if hints.get('tags'):
                prompt_parts.append("\nAvailable Enrichment Tags for this question:")
                # Show top 5 tags with full query examples
                for i, tag in enumerate(hints['tags'][:5], 1):
                    tag_name = tag.get('tag_name', '')
                    tag_value = tag.get('tag_value', '')
                    example = f'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l'
                    prompt_parts.append(f"{i}. {example}")

                # Add multi-tag combination examples if we have multiple tags
                if len(hints['tags']) >= 2:
                    prompt_parts.append("\n💡 COMBINE TAGS FOR PRECISION:")
                    tag1 = hints['tags'][0]
                    tag2 = hints['tags'][1]
                    multi_example = (
                        f'cpg.method.where(_.tag.nameExact("{tag1.get("tag_name", "")}").valueExact("{tag1.get("tag_value", "")}"))'
                        f'.where(_.tag.nameExact("{tag2.get("tag_name", "")}").valueExact("{tag2.get("tag_value", "")}")).name.l'
                    )
                    prompt_parts.append(f"Multi-tag: {multi_example}")

                if len(hints['tags']) >= 3:
                    tag3 = hints['tags'][2]
                    triple_example = (
                        f'cpg.method.where(_.tag.nameExact("{tag1.get("tag_name", "")}").valueExact("{tag1.get("tag_value", "")}"))'
                        f'.where(_.tag.nameExact("{tag2.get("tag_name", "")}").valueExact("{tag2.get("tag_value", "")}"))'
                        f'.where(_.tag.nameExact("{tag3.get("tag_name", "")}").valueExact("{tag3.get("tag_value", "")}")).name.l'
                    )
                    prompt_parts.append(f"Triple-tag: {triple_example}")

                prompt_parts.append("\n✅ USE MULTIPLE TAGS when available for better precision!")

        # Add top CPGQL examples
        if context.get('sql_examples'):
            examples_text = []
            for i, ex in enumerate(context['sql_examples'][:3], 1):
                q = ex.get('question', '')[:60]
                query = ex.get('query', '')[:100]
                if q and query:
                    examples_text.append(f"Example {i}: {q}... → {query}")

            if examples_text:
                prompt_parts.append("\nSimilar Query Examples:\n" + '\n'.join(examples_text))

        # Task
        prompt_parts.append(
            f"\nGenerate CPGQL query with TAGS for:\n{question}\n\n"
            "INSTRUCTION: Combine 2-3 tags with multiple .where() clauses for precision.\n"
            "Output only the CPGQL query (one line, starting with 'cpg.' and using .where(_.tag.nameExact...)):\n"
        )

        return '\n'.join(prompt_parts)

    def _record_tag_feedback(self, context: Dict, query_valid: bool):
        """
        Record feedback about tag usage effectiveness (Phase 2).

        Args:
            context: Query generation context with enrichment hints
            query_valid: Whether the generated query was valid
        """
        if not self.tracker:
            return

        hints = context.get('enrichment_hints', {})
        analysis = context.get('analysis', {})

        domain = analysis.get('domain', 'general')
        intent = analysis.get('intent', 'explain-concept')
        coverage_score = hints.get('coverage_score', 0.0)

        # Record feedback for all tags used
        tags = hints.get('tags', [])

        for tag in tags[:7]:  # Only top 7 tags shown to user
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')

            if tag_name and tag_value:
                self.tracker.record_tag_usage(
                    tag_name=tag_name,
                    tag_value=tag_value,
                    domain=domain,
                    intent=intent,
                    query_valid=query_valid,
                    query_executed=False,  # Don't know yet
                    execution_successful=False,  # Don't know yet
                    coverage_score=coverage_score
                )

        # Persist tracker state periodically (every 10th call)
        import random
        if random.random() < 0.1:  # 10% chance
            self.tracker.persist()

    def generate_query_variants(
        self,
        question: str,
        context: Dict,
        num_variants: int = 3
    ) -> List[Dict]:
        """
        Generate multiple query variants with different specificity levels.

        This is the core of the Query Funnel approach to combat empty results.

        Args:
            question: Natural language question
            context: Retrieved context with enrichment hints
            num_variants: Number of variants (default 3: PRECISE, BALANCED, BROAD)

        Returns:
            List of dicts with keys:
            - query: str (CPGQL query)
            - specificity: str ("precise", "balanced", "broad")
            - confidence: float (0.0-1.0)
            - strategy: str (description of approach)
        """
        logger.info("Generating query variants with Query Funnel approach")

        variants = []

        # Variant 1: PRECISE (all available tags + exact name matching)
        try:
            precise_query = self._generate_precise_query(question, context)
            variants.append({
                "query": precise_query,
                "specificity": "precise",
                "confidence": 0.9,
                "strategy": "Exact tag combinations + name patterns"
            })
            logger.debug(f"PRECISE variant: {precise_query}")
        except Exception as e:
            logger.warning(f"Failed to generate PRECISE variant: {e}")

        # Variant 2: BALANCED (top 2 tags + relaxed name matching)
        try:
            balanced_query = self._generate_balanced_query(question, context)
            variants.append({
                "query": balanced_query,
                "specificity": "balanced",
                "confidence": 0.7,
                "strategy": "Key tags + relaxed name matching"
            })
            logger.debug(f"BALANCED variant: {balanced_query}")
        except Exception as e:
            logger.warning(f"Failed to generate BALANCED variant: {e}")

        # Variant 3: BROAD (domain concept + graph traversal)
        try:
            broad_query = self._generate_broad_query(question, context)
            variants.append({
                "query": broad_query,
                "specificity": "broad",
                "confidence": 0.5,
                "strategy": "Name patterns + graph traversal"
            })
            logger.debug(f"BROAD variant: {broad_query}")
        except Exception as e:
            logger.warning(f"Failed to generate BROAD variant: {e}")

        # Generate progressive tag relaxation variants from PRECISE query
        # This helps when PRECISE has multiple tags that are too restrictive
        if variants and variants[0].get("specificity") == "precise":
            try:
                from src.validation import generate_tag_relaxation_variants

                precise_query = variants[0]["query"]
                relaxation_variants = generate_tag_relaxation_variants(precise_query)

                if relaxation_variants:
                    logger.info(f"Generated {len(relaxation_variants)} tag relaxation variants")

                    # Insert relaxation variants between PRECISE and BALANCED
                    # They have intermediate specificity between fully precise and balanced
                    for relax_variant in relaxation_variants:
                        # Map to our variant format
                        # Higher tags_kept = more specific = higher priority
                        tags_kept = relax_variant.get('tags_kept', 1)

                        # Confidence decreases as we remove more tags
                        confidence = 0.85 - (0.05 * relax_variant.get('priority', 1))

                        variants.insert(
                            relax_variant.get('priority', 1),  # Insert at appropriate position
                            {
                                "query": relax_variant["query"],
                                "specificity": f"relaxed-{tags_kept}-tags",
                                "confidence": confidence,
                                "strategy": f"Tag relaxation: {relax_variant['tags_removed']}"
                            }
                        )
                        logger.debug(f"Added relaxation variant: {relax_variant['tags_removed']}")
            except Exception as e:
                logger.warning(f"Failed to generate tag relaxation variants: {e}")

        # Generate fuzzy method name matching variants
        # Apply to queries that have method name filters to create broader alternatives
        try:
            from src.validation import apply_fuzzy_method_name_matching

            # Apply fuzzy matching to all variants that have .name() filters
            fuzzy_variants_added = 0
            for i, variant in enumerate(list(variants)):  # Use list() to avoid modification during iteration
                query = variant.get("query", "")

                # Only create fuzzy variant if query has a .name() filter
                if ".name(" in query:
                    fuzzy_query = apply_fuzzy_method_name_matching(query)

                    # Only add if it's different from original
                    if fuzzy_query != query:
                        # Add fuzzy variant after the original
                        variants.insert(i + fuzzy_variants_added + 1, {
                            "query": fuzzy_query,
                            "specificity": variant.get("specificity", "unknown") + "-fuzzy",
                            "confidence": variant.get("confidence", 0.5) - 0.1,  # Slightly lower confidence
                            "strategy": f"Fuzzy name matching: {variant.get('strategy', 'N/A')}"
                        })
                        fuzzy_variants_added += 1
                        logger.debug(f"Added fuzzy variant for {variant.get('specificity')} query")

            if fuzzy_variants_added > 0:
                logger.info(f"Generated {fuzzy_variants_added} fuzzy method name matching variants")
        except Exception as e:
            logger.warning(f"Failed to generate fuzzy method name variants: {e}")

        if not variants:
            # Fallback if all failed
            logger.error("All variant generation failed, using fallback")
            variants.append({
                "query": "cpg.method.name.l",
                "specificity": "fallback",
                "confidence": 0.1,
                "strategy": "Emergency fallback query"
            })

        logger.info(f"Generated {len(variants)} query variants")
        return variants

    def _generate_precise_query(self, question: str, context: Dict) -> str:
        """
        Generate PRECISE query (high precision, low recall).

        TUNED: Uses top 2 tags (reduced from 3) + relaxed name pattern.
        More balanced between precision and recall.
        """
        hints = context.get('enrichment_hints', {})
        tags = hints.get('tags', [])

        # TUNED: Use only top 2 tags instead of 3 (less restrictive)
        query = "cpg.method"
        for tag in tags[:2]:
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')
            if tag_name and tag_value:
                query += f'.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}"))'

        # TUNED: Add pattern match instead of exact name
        method_name = self._extract_method_name(question)
        if method_name:
            # Use broader pattern matching
            pattern = f".*{method_name}.*"
            query += f'.name("{pattern}")'

        # TUNED: Get more results (20 instead of all)
        query += ".name.take(20).l"
        return query

    def _generate_balanced_query(self, question: str, context: Dict) -> str:
        """
        Generate BALANCED query (medium precision, medium recall).

        TUNED: Uses top 1 tag (reduced from 2) + domain concept fallback.
        More inclusive while still maintaining some filtering.
        """
        hints = context.get('enrichment_hints', {})
        tags = hints.get('tags', [])
        analysis = context.get('analysis', {})

        # TUNED: Use only top 1 tag for better recall
        query = "cpg.method"
        tag_applied = False
        for tag in tags[:1]:
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')
            if tag_name and tag_value:
                query += f'.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}"))'
                tag_applied = True
                break

        # TUNED: If no tag applied, use domain concept as fallback
        if not tag_applied:
            domain = analysis.get('domain', '')
            if domain and domain != 'unknown':
                query += f'.where(_.tag.nameExact("domain-concept").valueExact("{domain}"))'

        # TUNED: More relaxed name pattern matching
        method_name = self._extract_method_name(question)
        if method_name:
            # Use even broader pattern (3 chars minimum)
            partial_name = method_name[:3] if len(method_name) >= 3 else method_name
            pattern = f".*{partial_name}.*"
            query += f'.name("{pattern}")'

        # TUNED: Get more results (30 instead of all)
        query += ".name.take(30).l"
        return query

    def _generate_broad_query(self, question: str, context: Dict) -> str:
        """
        Generate BROAD query (low precision, high recall).

        Uses general patterns + graph features (CFG/DDG).
        Almost always returns results, then ranked by relevance.
        """
        hints = context.get('enrichment_hints', {})
        analysis = context.get('analysis', {})

        domain = analysis.get('domain', 'unknown')

        # Use only domain concept tag (most general)
        query = "cpg.method"

        # Try to find domain-concept tag
        domain_tag = None
        for tag in hints.get('tags', []):
            if tag.get('tag_name') == 'domain-concept':
                domain_tag = tag.get('tag_value')
                break

        if domain_tag:
            query += f'.where(_.tag.nameExact("domain-concept").valueExact("{domain_tag}"))'
        elif domain and domain != 'unknown':
            # Use domain from analysis
            query += f'.where(_.tag.nameExact("domain-concept").valueExact("{domain}"))'

        # Add graph traversal for richer context
        if self._is_data_flow_question(question):
            # Data flow question - use DDG
            query += ".parameter.reachableBy(cpg.identifier).code.take(20)"
        elif self._is_control_flow_question(question):
            # Control flow question - use CFG
            query += ".ast.isControlStructure.code.take(20)"
        else:
            # General - just get method names
            query += ".name.take(50)"

        query += ".l"
        return query

    def _extract_method_name(self, question: str) -> Optional[str]:
        """
        Extract method/function name from question if present.

        Examples:
        - "How does heap_insert work?" -> "heap_insert"
        - "What is the purpose of XLogInsert?" -> "XLogInsert"
        """
        import re

        # Look for common patterns
        patterns = [
            r'\b([a-zA-Z_][a-zA-Z0-9_]{3,})\(\)',  # function()
            r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]+)',  # "function funcname"
            r'\bметод\s+([a-zA-Z_][a-zA-Z0-9_]+)',  # Russian "метод funcname"
            r'\b([A-Z][a-zA-Z0-9_]{3,})\b',  # CamelCase
            r'\b([a-z]+_[a-z_]+)\b',  # snake_case (2+ parts)
        ]

        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                return match.group(1)

        return None

    def _is_data_flow_question(self, question: str) -> bool:
        """Check if question is about data flow."""
        keywords = ['data flow', 'parameter', 'variable', 'value', 'pass', 'передач', 'данных']
        question_lower = question.lower()
        return any(kw in question_lower for kw in keywords)

    def _is_control_flow_question(self, question: str) -> bool:
        """Check if question is about control flow."""
        keywords = ['control flow', 'if', 'loop', 'condition', 'branch', 'условие', 'цикл', 'ветв']
        question_lower = question.lower()
        return any(kw in question_lower for kw in keywords)

    def _build_semantic_prompt(self, question: str, context: Dict) -> str:
        """
        Build semantic prompt for comment-based question answering.

        Uses the semantic prompts that emphasize:
        - Comments as primary source of information
        - Structured Map() results with explanations
        - Control flow and call graph analysis
        - Answer synthesis, not just code search

        Args:
            question: Natural language question
            context: Retrieved context INCLUDING sql_examples to show as templates

        Returns:
            Formatted prompt for semantic query generation
        """
        # Format retrieved CPGQL examples to show REAL methods
        retrieved_examples = self._format_retrieved_sql_examples(context.get('sql_examples', []))

        # Use the semantic user prompt template with retrieved examples
        prompt = self.semantic_user_prompt.format(
            question=question,
            retrieved_examples=retrieved_examples
        )

        # Prepend system prompt for full context
        full_prompt = self.semantic_system_prompt + "\n\n" + prompt

        logger.debug(f"Built semantic prompt ({len(full_prompt)} chars, {len(context.get('sql_examples', []))} examples)")
        return full_prompt

    def _format_retrieved_sql_examples(self, examples: List[Dict]) -> str:
        """
        Format retrieved CPGQL examples to show as templates.

        Shows REAL method names that exist in the codebase.
        """
        if not examples:
            return ""

        lines = [
            "====================================================================================",
            "RETRIEVED EXAMPLES - These show REAL methods that exist in the codebase:",
            "====================================================================================",
            ""
        ]

        for i, ex in enumerate(examples[:5], 1):  # Top 5
            question = ex.get('question', '')[:80]
            query = ex.get('query', '')

            # Extract method name pattern from query
            import re
            method_match = re.search(r'method\.name\(["\']([^"\']+)["\']\)', query)
            method_pattern = method_match.group(1) if method_match else "N/A"

            if question and query:
                lines.append(f"{i}. Similar Q: {question}...")
                lines.append(f"   Method pattern: {method_pattern}")
                lines.append(f"   Query: {query[:150]}...")
                lines.append("")

        lines.append("👉 STUDY THESE EXAMPLES - Use similar patterns for your query!")
        lines.append("👉 Notice they use FUZZY patterns like '.*timestamp.*' not exact names")
        lines.append("")

        return '\n'.join(lines)

    def _extract_query(self, raw_output: str) -> str:
        """
        Extract CPGQL query from raw LLM output.

        Handles cases where LLM adds explanations.
        Supports multiline .map/.flatMap queries.
        Auto-appends missing execution directives.
        """
        import re

        # IMPROVED: Handle multiline .map queries first
        # Pattern: cpg....map { ... } or cpg....flatMap { ... }
        multiline_pattern = r'(cpg\.[\s\S]*?\.(?:map|flatMap|headOption\.map)\s*\{[\s\S]*?\})'
        multiline_match = re.search(multiline_pattern, raw_output, re.MULTILINE)

        if multiline_match:
            query = multiline_match.group(1).strip()
            # Clean up whitespace but preserve structure
            query = re.sub(r'\s+', ' ', query)  # Collapse whitespace
            query = query.replace('{ ', '{').replace(' }', '}')  # Tighten braces
            logger.debug(f"Extracted multiline query: {query[:100]}...")
            return query

        # Split by lines for single-line extraction
        lines = raw_output.strip().split('\n')

        query = None

        # Find line starting with cpg.
        for line in lines:
            line = line.strip()
            if line.startswith('cpg.'):
                # Clean up
                # Remove trailing explanations
                if '//' in line:
                    line = line.split('//')[0].strip()
                if '#' in line:
                    line = line.split('#')[0].strip()

                # Remove escaped quotes
                line = line.replace('\\"', '"')

                # Remove trailing brackets/quotes that may be from JSON
                line = line.rstrip('"]')

                query = line
                break

        # If no cpg. line found, try to find it in text
        if not query:
            cpg_match = re.search(r'(cpg\.[^\n]+)', raw_output)
            if cpg_match:
                query = cpg_match.group(1).strip()

        if not query:
            # IMPROVED FALLBACK: Try to generate basic semantic query from question
            logger.warning(f"Could not extract query from output: {raw_output[:100]}")

            # Extract potential method name from question
            import re
            method_name_match = re.search(r'(?:does|is|what|how)\s+(\w+)', raw_output.lower())
            if not method_name_match:
                method_name_match = re.search(r'(\w+)\s+do\??', raw_output.lower())

            if method_name_match:
                method_name = method_name_match.group(1)
                fallback_query = f'cpg.method.name(".*{method_name}.*").name.l.take(10)'
                logger.info(f"Generated fallback query with method pattern: {fallback_query}")
                return fallback_query
            else:
                # Last resort fallback
                logger.warning("Falling back to generic method list query")
                return "cpg.method.name.l.take(20)"

        # Auto-append execution directive if missing (for non-map queries)
        execution_directives = ['.l', '.toList', '.toJson', '.p', '.size', '.count', '.head']
        has_directive = any(query.endswith(directive) for directive in execution_directives)
        is_map_query = '.map' in query or '.flatMap' in query

        if not has_directive and not is_map_query:
            # Check if query ends with a closing paren (method call) or quote (string arg)
            if query.endswith(')') or query.endswith('"'):
                query += '.l'
                logger.debug(f"Auto-appended .l to query: {query}")

        return query
