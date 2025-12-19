"""
Helper functions for LangGraph CodeGraph Workflow.

This module contains utility functions for:
- RAGAS metric computation
- Query post-processing
- Result counting
"""

import re
import logging
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.workflow._state import RAGCPGQLState

# Optional RAGAS imports
try:
    from datasets import Dataset
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import (
        context_precision as ragas_context_precision,
        context_recall as ragas_context_recall,
        answer_relevancy as ragas_answer_relevancy,
        faithfulness as ragas_faithfulness,
    )
    _RAGAS_AVAILABLE = True
    _RAGAS_METRICS = [
        ragas_context_precision,
        ragas_context_recall,
        ragas_answer_relevancy,
        ragas_faithfulness,
    ]
except Exception:
    _RAGAS_AVAILABLE = False
    _RAGAS_METRICS = []

logger = logging.getLogger(__name__)


def _build_context_strings(state: "RAGCPGQLState") -> List[str]:
    """Construct textual contexts for RAGAS evaluation."""
    contexts: List[str] = []

    similar_qa = state.get("similar_qa") or []
    for qa in similar_qa:
        question = qa.get("question", "").strip()
        answer = qa.get("answer", "").strip()
        if question or answer:
            segment = "Q: " + question if question else ""
            if answer:
                segment += ("\nA: " if question else "A: ") + answer
            contexts.append(segment.strip())

    cpgql_examples = state.get("cpgql_examples") or []
    for example in cpgql_examples:
        sample_q = example.get("question", "").strip()
        query = example.get("query", "").strip()
        if sample_q or query:
            contexts.append(
                f"Example Question: {sample_q}\nExample Query: {query}".strip()
            )

    enrichment_hints = state.get("enrichment_hints") or {}
    if enrichment_hints:
        formatted_hints: List[str] = []
        for key in [
            "features",
            "subsystems",
            "function_purposes",
            "data_structures",
            "domain_concepts",
            "architectural_roles",
        ]:
            values = enrichment_hints.get(key)
            if values:
                formatted_hints.append(f"{key}: {', '.join(values)}")
        if formatted_hints:
            contexts.append("Enrichment hints: " + " | ".join(formatted_hints))

    if not contexts:
        contexts.append("No retrieved context")

    return contexts


def _compute_ragas_scores(state: "RAGCPGQLState") -> Dict[str, float]:
    """Compute RAGAS metrics for the current workflow state."""
    if not _RAGAS_AVAILABLE:
        raise RuntimeError("RAGAS dependencies are not available")

    contexts = _build_context_strings(state)
    answer_text = state.get("answer") or state.get("cpgql_query") or ""
    ground_truth = state.get("cpgql_query") or answer_text or "N/A"

    dataset = Dataset.from_dict(
        {
            "question": [state.get("question", "")],
            "contexts": [contexts],
            "answer": [answer_text],
            "ground_truth": [ground_truth],
        }
    )

    ragas_result = ragas_evaluate(dataset, metrics=_RAGAS_METRICS)
    scores_row = ragas_result.to_pandas().iloc[0].to_dict()

    return {
        "context_precision": float(scores_row.get("context_precision", 0.0)),
        "context_recall": float(scores_row.get("context_recall", 0.0)),
        "answer_relevancy": float(scores_row.get("answer_relevancy", 0.0)),
        "faithfulness": float(scores_row.get("faithfulness", 0.0)),
    }


def _count_scala_results(result_str: str) -> int:
    """Count results in Scala output using proper parsing.

    Supports multiple Scala output formats:
    - List("item1", "item2", ...) - Count quoted strings
    - Newline-separated items - Count non-empty lines
    - Empty or error messages - Return 0

    Args:
        result_str: Raw Scala output string

    Returns:
        Number of results found
    """
    if not result_str or result_str == "No results found for the specified criteria":
        return 0

    # Pattern 1: Scala List with quoted strings
    if "List(" in result_str:
        list_match = re.search(r'List\s*\((.*)\)', result_str, re.DOTALL)
        if list_match:
            list_content = list_match.group(1)
            quoted_items = re.findall(r'"(?:[^"\\]|\\.)*"', list_content)
            count = len(quoted_items)
            if count > 0:
                return count

    # Pattern 2: Newline-separated output (fallback)
    lines = [line.strip() for line in result_str.split('\n') if line.strip()]
    data_lines = [
        line for line in lines
        if not line.startswith('val res')
        and not line.startswith('[')
        and not line.startswith('defined')
        and not line.endswith('=')
    ]

    if data_lines:
        return len(data_lines)

    # Pattern 3: Estimate from content length
    if len(result_str) > 100:
        estimated_count = max(1, len(result_str) // 50)
        logger.warning(f"Could not parse Scala output format, estimating {estimated_count} results")
        return estimated_count

    return 0


def post_process_query(query: str) -> tuple[str, bool]:
    """Post-process generated query to fix common issues that cause empty results.

    This function:
    1. Replaces exact matching with pattern matching for flexibility
    2. Validates and fixes invalid tag values (catches LLM hallucinations)
    3. Detects and fixes impossible AND combinations (same tag name, different values)

    Args:
        query: The generated CPGQL query

    Returns:
        Tuple of (processed_query, was_modified)
    """
    if not query:
        return query, False

    original_query = query
    modifications = []

    # 1. Replace exact matching with pattern matching
    query = query.replace(".nameExact(", ".name(")
    query = query.replace(".valueExact(", ".value(")

    if query != original_query:
        modifications.append("exact->pattern matching")

    # 2. Validate and fix invalid tag values
    try:
        from src.validation.query_validator import get_query_validator
        query_validator = get_query_validator()
        validation_result = query_validator.validate_query(query)

        if validation_result["corrections"]:
            query = validation_result["corrected_query"]
            for correction in validation_result["corrections"]:
                modifications.append(f"tag: {correction}")
                logger.info(f"Post-processing tag fix: {correction}")

        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"Post-processing tag warning: {warning}")
    except Exception as e:
        logger.warning(f"Tag validation failed: {e}", exc_info=True)

    # 3. Detect and fix impossible AND combinations
    tag_where_pattern = r'\.where\(_\.tag\.name\(["\']([^"\']+)["\']\)\.value\(["\']([^"\']+)["\']\)\)'
    matches = list(re.finditer(tag_where_pattern, query))

    if len(matches) > 1:
        seen_tags = {}
        indices_to_remove = []

        for i, match in enumerate(matches):
            tag_name = match.group(1)
            tag_value = match.group(2)

            if tag_name in seen_tags:
                first_value = seen_tags[tag_name]['value']
                logger.warning(
                    f"Detected impossible AND combination: "
                    f"tag '{tag_name}' with values '{first_value}' AND '{tag_value}'. "
                    f"Keeping first value '{first_value}', removing second."
                )
                indices_to_remove.append(i)
                modifications.append(f"removed duplicate tag '{tag_name}'")
            else:
                seen_tags[tag_name] = {'value': tag_value, 'index': i}

        if indices_to_remove:
            parts = []
            last_end = 0

            for i, match in enumerate(matches):
                if i not in indices_to_remove:
                    parts.append(query[last_end:match.end()])
                    last_end = match.end()
                else:
                    parts.append(query[last_end:match.start()])
                    last_end = match.end()

            parts.append(query[last_end:])
            query = ''.join(parts)

    was_modified = (query != original_query)

    if was_modified:
        logger.info(f"Post-processing: Applied {', '.join(modifications)}")
        logger.debug(f"Original: {original_query[:150]}...")
        logger.debug(f"Modified: {query[:150]}...")

    return query, was_modified


def is_empty_result(raw_result: str | None) -> bool:
    """Check if query result is empty or contains no meaningful data."""
    if not raw_result:
        return True

    raw_result = raw_result.strip()

    empty_indicators = [
        "List()",
        "No results",
        "Empty",
        "Nothing found",
        "0 results",
    ]

    for indicator in empty_indicators:
        if indicator.lower() in raw_result.lower():
            return True

    if len(raw_result) < 10:
        return True

    return False


__all__ = [
    '_build_context_strings',
    '_compute_ragas_scores',
    '_count_scala_results',
    'post_process_query',
    'is_empty_result',
    '_RAGAS_AVAILABLE',
    '_RAGAS_METRICS',
]
