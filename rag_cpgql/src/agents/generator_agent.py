"""Generator Agent - Generates CPGQL queries with enriched context."""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """
    Generator Agent for CPGQL query generation.

    Generates queries using:
    - Grammar constraints (mandatory)
    - Retrieved Q&A examples
    - Retrieved CPGQL examples
    - Enrichment tag context
    """

    def __init__(self, cpgql_generator, use_grammar: bool = True):
        """
        Initialize Generator Agent.

        Args:
            cpgql_generator: CPGQLGenerator instance
            use_grammar: Whether to use grammar constraints
        """
        self.generator = cpgql_generator
        self.use_grammar = use_grammar

    def generate(
        self,
        question: str,
        context: Dict
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Generate CPGQL query with full RAG context.

        Args:
            question: Natural language question
            context: Retrieved context with:
                - similar_qa: Similar Q&A pairs
                - cpgql_examples: CPGQL examples
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

        # 1. System context
        prompt_parts.append(
            "You are a CPGQL expert generating queries for PostgreSQL code analysis.\n"
            "The Code Property Graph has been enriched with semantic tags.\n"
        )

        # 2. Enrichment context
        if 'enrichment_hints' in context:
            enrichment_text = self._format_enrichment_context(context['enrichment_hints'])
            if enrichment_text:
                prompt_parts.append(f"\n=== Enrichment Context ===\n{enrichment_text}\n")

        # 3. Similar Q&A examples
        if context.get('similar_qa'):
            qa_text = self._format_qa_examples(context['similar_qa'])
            prompt_parts.append(f"\n=== Similar Questions ===\n{qa_text}\n")

        # 4. CPGQL examples
        if context.get('cpgql_examples'):
            cpgql_text = self._format_cpgql_examples(context['cpgql_examples'])
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
        """Format enrichment hints for prompt."""
        lines = []

        if hints.get('features'):
            lines.append(f"PostgreSQL Features: {', '.join(hints['features'][:5])}")

        if hints.get('function_purposes'):
            lines.append(f"Function Purposes: {', '.join(hints['function_purposes'][:5])}")

        if hints.get('data_structures'):
            lines.append(f"Data Structures: {', '.join(hints['data_structures'][:5])}")

        if hints.get('domain_concepts'):
            lines.append(f"Domain Concepts: {', '.join(hints['domain_concepts'][:5])}")

        # Show example tag-based queries
        if hints.get('tags'):
            lines.append("\nExample tag usage:")
            for i, tag in enumerate(hints['tags'][:3], 1):
                example = f"  {i}. cpg.method.where({tag['query_fragment']}).name.l"
                lines.append(example)

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

    def _format_cpgql_examples(self, examples: List[Dict]) -> str:
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

        # System instruction
        prompt_parts.append(
            "You are a CPGQL query generator for PostgreSQL code analysis.\n"
            "Generate a single, concise CPGQL query.\n"
        )

        # Add top CPGQL examples
        if context.get('cpgql_examples'):
            examples_text = []
            for i, ex in enumerate(context['cpgql_examples'][:3], 1):
                q = ex.get('question', '')[:60]
                query = ex.get('query', '')[:100]
                if q and query:
                    examples_text.append(f"Example {i}: {q}... → {query}")

            if examples_text:
                prompt_parts.append("\nExamples:\n" + '\n'.join(examples_text))

        # Add enrichment hints
        if context.get('enrichment_hints'):
            hints = context['enrichment_hints']
            if hints.get('tags'):
                tag = hints['tags'][0]
                prompt_parts.append(
                    f"\nHint: Use enrichment tag: {tag['query_fragment']}"
                )

        # Task
        prompt_parts.append(
            f"\nGenerate CPGQL query for:\n{question}\n\n"
            "Output only the CPGQL query (one line, starting with 'cpg.'):\n"
        )

        return '\n'.join(prompt_parts)

    def _extract_query(self, raw_output: str) -> str:
        """
        Extract CPGQL query from raw LLM output.

        Handles cases where LLM adds explanations.
        Auto-appends missing execution directives.
        """
        import re

        # Split by lines
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
            # Fallback
            logger.warning(f"Could not extract query from output: {raw_output[:100]}")
            return "cpg.method.name.l"

        # Auto-append execution directive if missing
        execution_directives = ['.l', '.toList', '.toJson', '.p', '.size', '.count', '.head']
        has_directive = any(query.endswith(directive) for directive in execution_directives)

        if not has_directive:
            # Check if query ends with a closing paren (method call) or quote (string arg)
            if query.endswith(')') or query.endswith('"'):
                query += '.l'
                logger.debug(f"Auto-appended .l to query: {query}")

        return query
