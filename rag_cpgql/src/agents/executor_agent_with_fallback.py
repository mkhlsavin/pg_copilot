"""Executor Agent with Fallback - Execute queries with automatic fallback to broader variants."""
import logging
from typing import Dict, List, Any, Optional
from src.execution.joern_client import JoernClient

logger = logging.getLogger(__name__)


class ExecutorAgentWithFallback:
    """
    Execute CPGQL queries with automatic fallback to broader variants.

    This is the core execution component of the Query Funnel approach.
    It tries query variants in order of specificity until sufficient results are found.
    """

    def __init__(self, joern_client: JoernClient, min_results_threshold: int = 5):
        """
        Initialize Executor Agent with Fallback.

        Args:
            joern_client: JoernClient instance (should be persistent)
            min_results_threshold: Minimum number of results to consider success (default 5)
        """
        self.joern = joern_client
        self.min_results_threshold = min_results_threshold

    def execute_with_fallback(
        self,
        query_variants: List[Dict],
        question: str
    ) -> Dict[str, Any]:
        """
        Execute queries in order of specificity until results found.

        Strategy:
        1. Try PRECISE query first (high precision, low recall)
        2. If empty or too few results, try BALANCED query
        3. If still empty, try BROAD query (low precision, high recall)
        4. Return first variant with sufficient results (≥ min_results_threshold)

        Args:
            query_variants: List of query variant dicts from generator_agent.generate_query_variants()
            question: Original question (for logging)

        Returns:
            {
                "results": List[Any],  # Parsed results
                "raw_result": str,     # Raw Joern output
                "query_used": str,     # Actual query that succeeded
                "specificity": str,    # Level used (precise/balanced/broad)
                "fallback_count": int, # Number of fallbacks (0 = first query worked)
                "total_attempts": int, # Total queries tried
                "success": bool        # Whether any query returned sufficient results
            }
        """
        logger.info(f"Executing with fallback: {len(query_variants)} variants available")

        for i, variant in enumerate(query_variants):
            specificity = variant.get('specificity', 'unknown')
            query = variant.get('query', '')

            if not query or query == '':
                logger.warning(f"Attempt {i+1}: Empty query for {specificity} variant, skipping")
                continue

            logger.info(f"Attempt {i+1}/{len(query_variants)}: Trying {specificity.upper()} query")
            logger.debug(f"  Query: {query}")

            # Execute query
            result = self.joern.execute_query(query)

            if result.get('success'):
                raw_result = result.get('result', '')
                result_data = self._parse_result(raw_result)
                num_results = len(result_data)

                logger.info(f"  → {num_results} results returned")

                # Success if we have enough results
                if num_results >= self.min_results_threshold:
                    logger.info(f"SUCCESS: {specificity.upper()} query returned {num_results} results (threshold: {self.min_results_threshold})")
                    return {
                        "results": result_data,
                        "raw_result": raw_result,
                        "query_used": query,
                        "specificity": specificity,
                        "fallback_count": i,
                        "total_attempts": i + 1,
                        "success": True
                    }
                else:
                    logger.info(f"  → Insufficient results ({num_results} < {self.min_results_threshold}), trying next variant")
            else:
                error = result.get('error', 'Unknown error')
                logger.warning(f"  → Query execution failed: {error}")
                # Continue to next variant

        # All variants failed or returned insufficient results
        logger.warning(f"All {len(query_variants)} query variants returned insufficient results")

        # Return last attempt
        if query_variants:
            last_variant = query_variants[-1]
            last_query = last_variant.get('query', 'cpg.method.name.l')
            last_result = self.joern.execute_query(last_query)

            return {
                "results": [],
                "raw_result": last_result.get('result', ''),
                "query_used": last_query,
                "specificity": last_variant.get('specificity', 'broad'),
                "fallback_count": len(query_variants),
                "total_attempts": len(query_variants),
                "success": False
            }
        else:
            # No variants at all - emergency fallback
            logger.error("No query variants provided, using emergency fallback")
            fallback_query = "cpg.method.name.l"
            fallback_result = self.joern.execute_query(fallback_query)

            return {
                "results": [],
                "raw_result": fallback_result.get('result', ''),
                "query_used": fallback_query,
                "specificity": "emergency",
                "fallback_count": 0,
                "total_attempts": 1,
                "success": False
            }

    def _parse_result(self, raw_result: str) -> List[Any]:
        """
        Parse raw Joern result into structured data.

        Joern returns results in formats like:
        - List(method1, method2, method3)
        - List()
        - "result1", "result2", "result3"

        Args:
            raw_result: Raw string from Joern

        Returns:
            List of parsed result items
        """
        if not raw_result or raw_result.strip() == '':
            return []

        # Check for empty List()
        if 'List()' in raw_result:
            return []

        # Try to extract items from List(...)
        import re

        # Pattern: List(item1, item2, item3)
        list_match = re.search(r'List\((.*?)\)', raw_result, re.DOTALL)
        if list_match:
            content = list_match.group(1).strip()
            if content == '':
                return []

            # Split by comma, but be careful with nested structures
            items = self._smart_split(content)
            return [item.strip() for item in items if item.strip()]

        # If not in List() format, try splitting by newlines
        lines = raw_result.strip().split('\n')

        # Filter out Scala REPL prompts and metadata
        filtered_lines = []
        for line in lines:
            line = line.strip()
            # Skip REPL prompts and metadata
            if line.startswith('joern>') or line.startswith('res') or line.startswith('val res') or line == '':
                continue
            filtered_lines.append(line)

        return filtered_lines if filtered_lines else []

    def _smart_split(self, content: str) -> List[str]:
        """
        Smart split of comma-separated values, handling nested structures.

        Examples:
        - "a, b, c" → ["a", "b", "c"]
        - "func(x, y), func2(a, b)" → ["func(x, y)", "func2(a, b)"]
        """
        items = []
        current = []
        depth = 0
        in_quotes = False
        quote_char = None

        for char in content:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current.append(char)
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current.append(char)
            elif char == '(' and not in_quotes:
                depth += 1
                current.append(char)
            elif char == ')' and not in_quotes:
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0 and not in_quotes:
                # Split here
                items.append(''.join(current))
                current = []
            else:
                current.append(char)

        # Add last item
        if current:
            items.append(''.join(current))

        return items

    def get_result_summary(self, execution_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of execution result.

        Args:
            execution_result: Result from execute_with_fallback()

        Returns:
            Summary string for logging/display
        """
        specificity = execution_result.get('specificity', 'unknown')
        fallback_count = execution_result.get('fallback_count', 0)
        num_results = len(execution_result.get('results', []))
        success = execution_result.get('success', False)

        if success:
            if fallback_count == 0:
                return f"[OK] {specificity.upper()} query succeeded on first try ({num_results} results)"
            else:
                return f"[OK] {specificity.upper()} query succeeded after {fallback_count} fallback(s) ({num_results} results)"
        else:
            return f"[FAILED] All variants failed (tried {execution_result.get('total_attempts', 0)} queries)"

    def set_min_results_threshold(self, threshold: int):
        """Update the minimum results threshold."""
        self.min_results_threshold = threshold
        logger.info(f"Updated min_results_threshold to {threshold}")
