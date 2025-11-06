"""Interpreter Agent - Converts CPGQL execution results to natural language answers."""
import logging
import json
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class InterpreterAgent:
    """
    Interpreter Agent for result synthesis.

    Converts raw CPGQL execution results into coherent natural language answers by:
    - Parsing and grouping function lists by purpose/tags
    - Generating LLM-based summaries explaining findings
    - Providing context about why results are relevant
    - Handling edge cases (empty results, errors, large result sets)
    """

    def __init__(self, llm_interface=None, use_semantic: bool = False):
        """
        Initialize Interpreter Agent.

        Args:
            llm_interface: LLM interface for answer synthesis (optional, falls back to templates)
            use_semantic: Whether to use semantic mode (extract comments from Map results)
        """
        self.llm = llm_interface
        self.use_semantic = use_semantic

        # Import semantic interpreter prompt if enabled
        if self.use_semantic:
            from src.generation.prompts_semantic import INTERPRETER_SEMANTIC_PROMPT
            self.semantic_prompt_template = INTERPRETER_SEMANTIC_PROMPT
            logger.info("Semantic interpreter mode ENABLED - will extract comments and synthesize answers")

    def interpret(
        self,
        question: str,
        query: str,
        execution_success: bool,
        execution_result: Dict,
        execution_error: Optional[str] = None,
        enrichment_hints: Optional[Dict] = None,
        used_fallback: bool = False,
        fallback_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert query results to natural language answer.

        Args:
            question: Original user question
            query: Executed CPGQL query
            execution_success: Whether execution succeeded
            execution_result: Query execution results
            execution_error: Error message if execution failed
            enrichment_hints: Enrichment context used in generation
            used_fallback: Whether a fallback query was used
            fallback_query: The fallback query if used

        Returns:
            Dictionary with:
            - answer: Natural language answer
            - confidence: Answer confidence (0-1)
            - summary_type: Type of summary generated
        """
        try:
            # Handle execution failure
            if not execution_success:
                return self._handle_error(question, query, execution_error)

            # Get result data
            result_data = execution_result.get("result", "")

            # Check for empty results
            if self._is_empty_result(result_data):
                return self._handle_empty_result(
                    question, query, used_fallback, fallback_query
                )

            # SEMANTIC MODE: Handle structured Map results with comments
            if self.use_semantic:
                semantic_data = self._parse_semantic_result(result_data)
                if semantic_data:
                    # Successfully parsed semantic Map() results
                    return self._generate_semantic_answer(
                        question, query, semantic_data, execution_result
                    )
                # If parsing failed, fall through to standard mode

            # STANDARD MODE: Parse function list
            functions = self._parse_function_list(result_data)

            if not functions:
                # Raw data, not a function list
                return self._handle_raw_result(
                    question, query, result_data, enrichment_hints
                )

            # Group by tags if enrichment hints available
            if enrichment_hints:
                grouped = self._group_by_tags(functions, enrichment_hints)
            else:
                grouped = {"all": functions}

            # Generate summary
            answer = self._generate_summary(
                question, query, grouped, enrichment_hints, used_fallback, fallback_query
            )

            # Calculate confidence
            confidence = self._calculate_confidence(
                len(functions), execution_success, used_fallback, enrichment_hints
            )

            return {
                "answer": answer,
                "confidence": confidence,
                "summary_type": "llm" if self.llm else "template",
                "function_count": len(functions)
            }

        except Exception as e:
            logger.error(f"Interpreter error: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while interpreting the results: {str(e)}",
                "confidence": 0.0,
                "summary_type": "error"
            }

    def _is_empty_result(self, result_data: Any) -> bool:
        """Check if result is empty."""
        if not result_data:
            return True

        if isinstance(result_data, str):
            result_str = result_data.strip()
            return (
                not result_str or
                result_str in ["[]", "{}", "List()", "Set()", "null", "None"] or
                result_str.startswith("List()") or
                result_str.startswith("Set()")
            )

        if isinstance(result_data, (list, dict)):
            return len(result_data) == 0

        return False

    def _parse_function_list(self, result_data: Any) -> List[str]:
        """
        Parse function names from result data.

        Handles formats like:
        - List(func1, func2, func3)
        - ["func1", "func2", "func3"]
        - Plain comma-separated list
        """
        functions = []

        if isinstance(result_data, list):
            # Already a list
            functions = [str(f).strip() for f in result_data]
        elif isinstance(result_data, str):
            result_str = result_data.strip()

            # Try to parse List(...) format
            list_match = re.search(r'List\((.*)\)', result_str, re.DOTALL)
            if list_match:
                content = list_match.group(1)
                # Split by comma and clean
                functions = [f.strip() for f in content.split(',') if f.strip()]
            else:
                # Try JSON array
                try:
                    parsed = json.loads(result_str)
                    if isinstance(parsed, list):
                        functions = [str(f).strip() for f in parsed]
                except json.JSONDecodeError:
                    # Try comma-separated
                    if ',' in result_str:
                        functions = [f.strip() for f in result_str.split(',') if f.strip()]

        # Filter out empty strings and clean up
        functions = [f for f in functions if f and f not in ["null", "None", ""]]

        return functions

    def _group_by_tags(
        self, functions: List[str], enrichment_hints: Dict
    ) -> Dict[str, List[str]]:
        """
        Group functions by their enrichment tag categories.

        Args:
            functions: List of function names
            enrichment_hints: Enrichment context with tag information

        Returns:
            Dictionary mapping tag values to function lists
        """
        grouped = {}

        # Extract tag information from hints
        tags = enrichment_hints.get('tags', [])

        if not tags:
            # No tags, return all functions in one group
            return {"all": functions}

        # Group by tag categories
        for tag in tags:
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')

            if tag_value:
                category = f"{tag_name}: {tag_value}"
                if category not in grouped:
                    grouped[category] = []

        # For now, assign all functions to first category
        # (In a more advanced version, we'd query CPG for each function's actual tags)
        if grouped:
            first_category = list(grouped.keys())[0]
            grouped[first_category] = functions
        else:
            grouped["all"] = functions

        return grouped

    def _generate_summary(
        self,
        question: str,
        query: str,
        grouped_functions: Dict[str, List[str]],
        enrichment_hints: Optional[Dict],
        used_fallback: bool,
        fallback_query: Optional[str]
    ) -> str:
        """
        Generate natural language summary of findings.

        Uses LLM if available, otherwise uses template-based approach.
        """
        if self.llm:
            return self._generate_llm_summary(
                question, query, grouped_functions, enrichment_hints,
                used_fallback, fallback_query
            )
        else:
            return self._generate_template_summary(
                question, query, grouped_functions, enrichment_hints,
                used_fallback, fallback_query
            )

    def _generate_llm_summary(
        self,
        question: str,
        query: str,
        grouped_functions: Dict[str, List[str]],
        enrichment_hints: Optional[Dict],
        used_fallback: bool,
        fallback_query: Optional[str]
    ) -> str:
        """Generate summary using LLM."""
        # Count total functions
        total_funcs = sum(len(funcs) for funcs in grouped_functions.values())

        # Build context for LLM
        context_parts = []

        # Add question
        context_parts.append(f"User Question: {question}")

        # Add query info
        context_parts.append(f"\nCPGQL Query: {query}")
        if used_fallback and fallback_query:
            context_parts.append(f"(Used fallback strategy: {fallback_query})")

        # Add grouped results
        context_parts.append(f"\nFound {total_funcs} function(s):\n")

        for category, funcs in grouped_functions.items():
            if category != "all":
                context_parts.append(f"\n{category}:")
            else:
                context_parts.append("\nFunctions:")

            # Limit to first 20 per category to avoid token overflow
            display_funcs = funcs[:20]
            for func in display_funcs:
                context_parts.append(f"  - {func}")

            if len(funcs) > 20:
                context_parts.append(f"  ... and {len(funcs) - 20} more")

        # Build prompt
        prompt = f"""You are an expert PostgreSQL code analyst. Convert the CPGQL query results into a clear, informative answer.

{chr(10).join(context_parts)}

Instructions:
1. Explain WHAT was found (high-level summary)
2. Explain WHY these functions are relevant to the question
3. Group findings by purpose/category if multiple groups exist
4. If there are many functions, summarize patterns rather than listing all
5. Keep the answer concise but informative (2-4 sentences)

Answer:"""

        try:
            # Generate with LLM
            response = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=300,
                temperature=0.5
            )

            # Clean up response
            answer = response.strip()

            # Add fallback note if used
            if used_fallback and fallback_query:
                answer += f"\n\n(Note: Used fallback query strategy to find these results)"

            return answer

        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            # Fall back to template
            return self._generate_template_summary(
                question, query, grouped_functions, enrichment_hints,
                used_fallback, fallback_query
            )

    def _generate_template_summary(
        self,
        question: str,
        query: str,
        grouped_functions: Dict[str, List[str]],
        enrichment_hints: Optional[Dict],
        used_fallback: bool,
        fallback_query: Optional[str]
    ) -> str:
        """Generate summary using templates (fallback when no LLM)."""
        # Count total functions
        total_funcs = sum(len(funcs) for funcs in grouped_functions.values())

        # Build answer parts
        answer_parts = []

        # Opening summary
        if total_funcs == 1:
            answer_parts.append(f"Found 1 function matching your query.")
        else:
            answer_parts.append(f"Found {total_funcs} functions matching your query.")

        # Add category breakdown if multiple categories
        if len(grouped_functions) > 1:
            answer_parts.append("\n\nBreakdown by category:")
            for category, funcs in grouped_functions.items():
                answer_parts.append(f"\n- {category}: {len(funcs)} function(s)")

        # Add function listings
        answer_parts.append("\n\nFunctions found:")

        for category, funcs in grouped_functions.items():
            if len(grouped_functions) > 1 and category != "all":
                answer_parts.append(f"\n\n{category}:")

            # Limit display to first 15 functions
            display_funcs = funcs[:15]
            for func in display_funcs:
                answer_parts.append(f"\n  - {func}")

            if len(funcs) > 15:
                answer_parts.append(f"\n  ... and {len(funcs) - 15} more")

        # Add query info
        answer_parts.append(f"\n\nQuery used: {query}")

        # Add fallback note if applicable
        if used_fallback and fallback_query:
            answer_parts.append(
                f"\n\n(Note: Initial query returned no results; "
                f"used fallback strategy: {fallback_query})"
            )

        return "".join(answer_parts)

    def _handle_error(
        self, question: str, query: str, error: Optional[str]
    ) -> Dict[str, Any]:
        """Handle execution error."""
        error_msg = error or "Unknown error"

        return {
            "answer": (
                f"I couldn't answer the question because the query execution failed.\n\n"
                f"Error: {error_msg}\n\n"
                f"Query attempted: {query}"
            ),
            "confidence": 0.0,
            "summary_type": "error"
        }

    def _handle_empty_result(
        self,
        question: str,
        query: str,
        used_fallback: bool,
        fallback_query: Optional[str]
    ) -> Dict[str, Any]:
        """Handle empty results."""
        if used_fallback:
            answer = (
                f"The query executed successfully but returned no results even after "
                f"applying fallback strategies.\n\n"
                f"Final query: {fallback_query or query}\n\n"
                f"This might mean:\n"
                f"  - The specific combination of tags/filters has no matches\n"
                f"  - The question asks about functionality not present in this codebase\n"
                f"  - Try rephrasing with different terms"
            )
        else:
            answer = (
                f"The query executed successfully but returned no results.\n\n"
                f"Query: {query}\n\n"
                f"This might mean:\n"
                f"  - The enrichment tags don't match any functions\n"
                f"  - Try a broader or differently phrased question"
            )

        return {
            "answer": answer,
            "confidence": 0.5,
            "summary_type": "empty"
        }

    def _handle_raw_result(
        self,
        question: str,
        query: str,
        result_data: Any,
        enrichment_hints: Optional[Dict]
    ) -> Dict[str, Any]:
        """Handle raw (non-function-list) results."""
        # Convert to string and truncate
        result_str = str(result_data)

        if len(result_str) > 1000:
            result_display = result_str[:1000] + "\n\n(Results truncated for brevity)"
        else:
            result_display = result_str

        answer = (
            f"Based on the CPGQL query, here are the results:\n\n"
            f"{result_display}\n\n"
            f"Query: {query}"
        )

        return {
            "answer": answer,
            "confidence": 0.6,
            "summary_type": "raw"
        }

    def _parse_semantic_result(self, result_data: Any) -> Optional[List[Dict]]:
        """
        Parse semantic Map() results from CPGQL query.

        Semantic queries return structured data like:
        List(
          Map("method" -> "ReadBuffer", "explanation" -> List("comment1", "comment2"), ...),
          Map("method" -> "heap_insert", "explanation" -> List(...), ...)
        )

        Returns:
            List of dictionaries with parsed Map data, or None if not semantic format
        """
        if not isinstance(result_data, str):
            return None

        result_str = result_data.strip()

        # Check if it looks like it contains Maps
        if "Map(" not in result_str:
            return None

        try:
            # Try to extract Map structures using regex
            # Pattern: Map(key1 -> value1, key2 -> value2, ...)
            map_pattern = r'Map\((.*?)\)'

            # For now, do simple extraction
            # Look for presence of semantic fields
            has_explanation = "explanation" in result_str.lower()
            has_context = "context" in result_str.lower()
            has_comments = "comment" in result_str.lower()

            if has_explanation or has_context or has_comments:
                # This looks like semantic data
                # Return the raw string for LLM to parse
                return [{"raw_result": result_str}]

            return None

        except Exception as e:
            logger.debug(f"Failed to parse semantic result: {e}")
            return None

    def _generate_semantic_answer(
        self,
        question: str,
        query: str,
        semantic_data: List[Dict],
        execution_result: Dict
    ) -> Dict[str, Any]:
        """
        Generate answer from semantic Map() results using LLM.

        Uses INTERPRETER_SEMANTIC_PROMPT to synthesize answer with:
        - Direct answer to question
        - Evidence from comments
        - Function names and locations
        - Structured explanation
        """
        if not self.llm:
            # Fall back to raw result display
            raw_result = semantic_data[0].get("raw_result", str(semantic_data))
            return {
                "answer": (
                    f"Query returned semantic information:\n\n{raw_result[:1000]}\n\n"
                    "(Note: LLM not available for answer synthesis)"
                ),
                "confidence": 0.6,
                "summary_type": "semantic_raw"
            }

        try:
            # Get raw result string
            result_str = execution_result.get("result", "")

            # Build prompt using semantic template
            prompt = self.semantic_prompt_template.format(
                question=question,
                results=result_str[:3000]  # Limit to avoid token overflow
            )

            # Generate answer with LLM
            answer = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=500,  # Longer for semantic answers
                temperature=0.5
            )

            answer = answer.strip()

            # Calculate semantic confidence
            # Higher because we have rich context from comments
            confidence = 0.85

            # Check if answer seems complete
            if len(answer) > 100 and any(word in answer.lower() for word in ["according", "comment", "function", "file"]):
                confidence = 0.9
            elif len(answer) < 50:
                confidence = 0.7

            return {
                "answer": answer,
                "confidence": confidence,
                "summary_type": "semantic"
            }

        except Exception as e:
            logger.error(f"Semantic answer generation failed: {e}", exc_info=True)
            # Fall back to raw display
            raw_result = semantic_data[0].get("raw_result", str(semantic_data))
            return {
                "answer": (
                    f"Query returned semantic information but answer synthesis failed.\n\n"
                    f"Raw results:\n{raw_result[:1000]}"
                ),
                "confidence": 0.5,
                "summary_type": "semantic_error"
            }

    def _calculate_confidence(
        self,
        function_count: int,
        execution_success: bool,
        used_fallback: bool,
        enrichment_hints: Optional[Dict]
    ) -> float:
        """
        Calculate answer confidence.

        Factors:
        - Execution success
        - Number of results (too few or too many reduces confidence)
        - Whether fallback was needed
        - Presence of enrichment context
        """
        if not execution_success:
            return 0.0

        # Base confidence
        confidence = 0.7

        # Adjust for result count
        if function_count == 0:
            confidence = 0.3
        elif 1 <= function_count <= 10:
            confidence = 0.9  # Good, specific results
        elif 11 <= function_count <= 50:
            confidence = 0.8  # Many results but reasonable
        else:
            confidence = 0.6  # Too many results, less specific

        # Penalize fallback usage
        if used_fallback:
            confidence *= 0.9

        # Boost if enrichment hints were used
        if enrichment_hints and enrichment_hints.get('tags'):
            confidence = min(confidence + 0.1, 1.0)

        return round(confidence, 2)
