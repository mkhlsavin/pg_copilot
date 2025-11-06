"""CPGQL query generator with grammar-constrained generation."""
from llama_cpp import LlamaGrammar
from pathlib import Path
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class CPGQLGenerator:
    """Generate CPGQL queries using LLM with optional grammar constraints."""

    def __init__(self, llm, use_grammar: bool = True, use_semantic: bool = False):
        """
        Initialize CPGQL generator.

        Args:
            llm: LLMInterface instance
            use_grammar: Use grammar constraints (100% valid queries)
            use_semantic: Use semantic comment-based prompts
        """
        self.llm = llm
        self.use_grammar = use_grammar
        self.use_semantic = use_semantic
        self.grammar = None

        if use_grammar:
            # Load CPGQL grammar
            grammar_path = Path(__file__).parent.parent.parent / "cpgql_gbnf" / "cpgql_llama_cpp_v2.gbnf"

            if not grammar_path.exists():
                logger.warning(f"Grammar file not found: {grammar_path}")
                logger.warning("Grammar-constrained generation disabled")
                self.use_grammar = False
            else:
                try:
                    grammar_text = grammar_path.read_text(encoding='utf-8')
                    self.grammar = LlamaGrammar.from_string(grammar_text)
                    logger.info(f"Loaded CPGQL grammar from {grammar_path}")
                except Exception as e:
                    logger.error(f"Failed to load grammar: {e}")
                    logger.warning("Grammar-constrained generation disabled")
                    self.use_grammar = False

    def generate_query(
        self,
        question: str,
        enrichment_hints: Optional[str] = None,
        max_tokens: int = 300,
        temperature: float = 0.6
    ) -> str:
        """
        Generate CPGQL query from natural language question.

        Args:
            question: Natural language security question
            enrichment_hints: Optional hints from enriched CPG
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.6 = balanced)

        Returns:
            Valid CPGQL query string
        """
        # Build prompt
        prompt = self._build_prompt(question, enrichment_hints)

        logger.debug(f"Generating query for: {question}")
        logger.debug(f"Grammar: {'enabled' if self.use_grammar else 'disabled'}")

        # Generate with grammar constraints
        try:
            raw_query = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                grammar=self.grammar if self.use_grammar else None
            )

            logger.debug(f"Raw generated query: {raw_query}")

            # Post-processing cleanup
            cleaned_query = self._cleanup_query(raw_query)

            logger.info(f"Generated query: {cleaned_query}")
            return cleaned_query

        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            # Fallback to basic query
            return "cpg.method.name.l"

    def _build_prompt(self, question: str, enrichment_hints: Optional[str] = None) -> str:
        """
        Build prompt for CPGQL generation with few-shot examples.

        Args:
            question: Natural language question
            enrichment_hints: Optional enrichment context

        Returns:
            Formatted prompt with CPGQL examples
        """
        # Use semantic prompts if enabled
        if self.use_semantic:
            from src.generation.prompts_semantic import (
                CPGQL_SEMANTIC_SYSTEM_PROMPT,
                CPGQL_SEMANTIC_USER_PROMPT
            )
            logger.info("Using SEMANTIC prompts for comment-based query generation")
            return CPGQL_SEMANTIC_SYSTEM_PROMPT + "\n\n" + CPGQL_SEMANTIC_USER_PROMPT.format(question=question)

        # Original tag-based prompt
        prompt = """You are a CPGQL expert for PostgreSQL code analysis. Generate queries using semantic enrichment tags.

IMPORTANT: The CPG has been enriched with semantic tags. ALWAYS prefer tag-based filtering over name-based filtering!

Tag-Based Query Examples (RECOMMENDED):
- Find memory management functions: cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management")).name.l
- Find MVCC-related functions: cpg.method.where(_.tag.nameExact("domain-concept").valueExact("mvcc")).name.l
- Find transaction control functions: cpg.method.where(_.tag.nameExact("function-purpose").valueExact("transaction-control")).name.l
- Find functions using binary-tree: cpg.method.where(_.tag.nameExact("data-structure").valueExact("binary-tree")).name.l
- Find WAL logging functions: cpg.method.where(_.tag.nameExact("function-purpose").valueExact("wal-logging")).name.l
- Find vacuum-related functions: cpg.method.where(_.tag.nameExact("domain-concept").valueExact("vacuum")).name.l
- Combine multiple tags: cpg.method.where(_.tag.nameExact("function-purpose").valueExact("storage-access")).where(_.tag.nameExact("data-structure").valueExact("buffer")).name.l

Name-Based Query Examples (FALLBACK ONLY):
- Find all methods: cpg.method.name.l
- Find specific function: cpg.method.name("heap_page_prune").l
- Find by pattern: cpg.method.name(".*vacuum.*").l

"""

        if enrichment_hints:
            prompt += f"Enrichment Tags Available:\n{enrichment_hints}\n\n"
            prompt += "INSTRUCTION: Use the tags provided above in your query with .where(_.tag.nameExact(...).valueExact(...)) filtering!\n\n"

        prompt += f"""Question: {question}

CPGQL Query (USE TAGS):
"""

        return prompt

    def _cleanup_query(self, query: str) -> str:
        """
        Post-process generated query to fix common issues.

        Args:
            query: Raw generated query

        Returns:
            Cleaned query
        """
        # Remove extra whitespace around dots
        cleaned = re.sub(r'\s*\.\s*', '.', query)

        # Remove extra whitespace around parentheses
        cleaned = re.sub(r'\s*\(\s*', '(', cleaned)
        cleaned = re.sub(r'\s*\)\s*', ')', cleaned)

        # Remove trailing/leading whitespace
        cleaned = cleaned.strip()

        # Fix incomplete string literals BEFORE checking execution directive
        # Pattern 1: (" or ("c or ("any_incomplete → remove entire incomplete call
        cleaned = re.sub(r'\.name\("(?:[^"]*)$', '', cleaned)  # Remove incomplete .name("...
        cleaned = re.sub(r'\.language\([^)]*$', '', cleaned)  # Remove incomplete .language(...

        # Pattern 2: Empty parentheses → remove
        cleaned = re.sub(r'\(\)', '', cleaned)

        # Pattern 3: Unclosed parentheses at end → remove
        if '(' in cleaned and cleaned.count('(') > cleaned.count(')'):
            # Find last unclosed (
            last_open = cleaned.rfind('(')
            # Remove from that point to end
            cleaned = cleaned[:last_open]

        # Pattern 4: Unclosed quotes → remove everything after last quote
        if cleaned.count('"') % 2 != 0:
            # Odd number of quotes - remove incomplete string
            last_quote = cleaned.rfind('"')
            # Check if it's part of incomplete call
            if '.name("' in cleaned[last_quote-10:last_quote+1]:
                # Remove the incomplete .name(" part
                cleaned = cleaned[:last_quote-6]

        # Ensure query ends with execution directive
        if not cleaned.endswith(('.l', '.toList', '.head', '.size', '.count')):
            # Add .l if missing
            cleaned += '.l'

        # Final cleanup: remove trailing dots before execution
        cleaned = re.sub(r'\.+l$', '.l', cleaned)
        cleaned = re.sub(r'\.+toList$', '.toList', cleaned)

        return cleaned

    def generate_with_examples(
        self,
        question: str,
        few_shot_examples: list[tuple[str, str]],
        enrichment_hints: Optional[str] = None,
        max_tokens: int = 300,
        temperature: float = 0.6
    ) -> str:
        """
        Generate query using few-shot learning.

        Args:
            question: Natural language question
            few_shot_examples: List of (question, query) pairs
            enrichment_hints: Optional enrichment context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated CPGQL query
        """
        # Build few-shot prompt
        prompt = "Here are examples of CPGQL queries:\n\n"

        for i, (example_q, example_query) in enumerate(few_shot_examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {example_q}\n"
            prompt += f"Query: {example_query}\n\n"

        prompt += f"Now generate a query for:\n"
        prompt += f"Question: {question}\n"

        if enrichment_hints:
            prompt += f"\nContext from code analysis:\n{enrichment_hints}\n"

        prompt += "\nQuery: "

        # Generate
        try:
            raw_query = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                grammar=self.grammar if self.use_grammar else None
            )

            cleaned_query = self._cleanup_query(raw_query)
            logger.info(f"Generated query (few-shot): {cleaned_query}")
            return cleaned_query

        except Exception as e:
            logger.error(f"Few-shot generation failed: {e}")
            # Fallback to zero-shot
            return self.generate_query(question, enrichment_hints, max_tokens, temperature)

    def validate_query(self, query: str) -> tuple[bool, str]:
        """
        Basic validation of generated query.

        Args:
            query: CPGQL query to validate

        Returns:
            (is_valid, error_message)
        """
        # Check starts with cpg
        if not query.startswith('cpg'):
            return False, "Query must start with 'cpg'"

        # Check has execution directive OR is semantic Map-based query
        # Semantic queries use .map { } or .flatMap { } to return structured data
        is_semantic_query = '.map {' in query or '.flatMap {' in query or '.headOption.map' in query
        has_execution_directive = any(query.endswith(d) for d in ['.l', '.toList', '.head', '.size', '.count'])

        if not (has_execution_directive or is_semantic_query):
            return False, "Query must end with execution directive (.l, .toList, etc.) or use semantic Map structure"

        # Check balanced parentheses
        if query.count('(') != query.count(')'):
            return False, "Unbalanced parentheses"

        # Check balanced quotes
        if query.count('"') % 2 != 0:
            return False, "Unbalanced quotes"

        return True, ""
