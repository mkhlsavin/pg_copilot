"""
Workflow Helper Functions

Utility functions for query processing, result checking, and fallback generation.
"""

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# Patterns indicating empty Scala output
EMPTY_RESULT_PATTERNS = [
    r"^\s*\[\s*\]\s*$",
    r"List\(\)\s*$",
    r"Vector\(\)\s*$",
    r"ArrayBuffer\(\)\s*$",
    r"=\s*List\(\)\s*$",
    r"=\s*Vector\(\)\s*$",
    r"=\s*None\s*$",
    r"No CPG loaded",
    r"No results",
]


def is_empty_result(raw_result: Optional[str]) -> bool:
    """Check if Scala output represents an empty result."""
    if raw_result is None:
        return True
    stripped = raw_result.strip()
    if not stripped:
        return True
    for pattern in EMPTY_RESULT_PATTERNS:
        if re.search(pattern, stripped):
            # Ensure we do not misclassify non-empty lists like List(Call(...))
            if "List(" in stripped and not re.search(r"List\(\)", stripped):
                continue
            return True
    return False


def count_scala_results(result_str: str) -> int:
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
    # Example: val res1: List[String] = List("item1", "item2", ...)
    if "List(" in result_str:
        # Extract all quoted strings within List(...)
        # Match the List(...) portion
        list_match = re.search(r'List\s*\((.*)\)', result_str, re.DOTALL)
        if list_match:
            list_content = list_match.group(1)
            # Count quoted strings (handles escaped quotes)
            quoted_items = re.findall(r'"(?:[^"\\]|\\.)*"', list_content)
            count = len(quoted_items)
            if count > 0:
                return count

    # Pattern 2: Newline-separated output (fallback)
    # Count non-empty lines that look like method names or values
    lines = [line.strip() for line in result_str.split('\n') if line.strip()]
    # Filter out Scala REPL output lines (val res, type definitions, etc.)
    data_lines = [
        line for line in lines
        if not line.startswith('val res')
        and not line.startswith('[')  # ANSI color codes
        and not line.startswith('defined')
        and not line.endswith('=')
    ]

    if data_lines:
        return len(data_lines)

    # Pattern 3: If we have substantial content but couldn't parse it, estimate
    # This prevents false negatives when format is unexpected
    if len(result_str) > 100:
        # Rough estimate: 50 chars per result on average
        estimated_count = max(1, len(result_str) // 50)
        logger.warning(f"Could not parse Scala output format, estimating {estimated_count} results from {len(result_str)} chars")
        return estimated_count

    return 0


def post_process_query(query: str) -> tuple:
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
        modifications.append("exact→pattern matching")

    # 2. Validate and fix invalid tag values (catches LLM hallucinations)
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
    # Pattern: .where(_.tag.name("X").value("Y"))...where(_.tag.name("X").value("Z"))
    # This is impossible - a method can't have tag X with both values Y and Z
    tag_where_pattern = r'\.where\(_\.tag\.name\(["\']([^"\']+)["\']\)\.value\(["\']([^"\']+)["\']\)\)'
    matches = list(re.finditer(tag_where_pattern, query))

    if len(matches) > 1:
        # Track which tag names we've seen
        seen_tags = {}
        indices_to_remove = []

        for i, match in enumerate(matches):
            tag_name = match.group(1)
            tag_value = match.group(2)

            if tag_name in seen_tags:
                # Duplicate tag name found! This creates an impossible AND condition
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

        # Remove duplicate tag filters (in reverse order to preserve indices)
        if indices_to_remove:
            # Build new query by removing duplicate .where() clauses
            parts = []
            last_end = 0

            for i, match in enumerate(matches):
                if i not in indices_to_remove:
                    # Keep this match - add everything up to it
                    parts.append(query[last_end:match.end()])
                    last_end = match.end()
                else:
                    # Remove this match - skip to after it
                    parts.append(query[last_end:match.start()])
                    last_end = match.end()

            # Add remainder
            parts.append(query[last_end:])
            query = ''.join(parts)

    was_modified = (query != original_query)

    if was_modified:
        logger.info(f"Post-processing: Applied {', '.join(modifications)}")
        logger.debug(f"Original: {original_query[:150]}...")
        logger.debug(f"Modified: {query[:150]}...")

    return query, was_modified


def generate_query_fallbacks(query: str) -> List[str]:
    """Generate fallback query variants for when primary query returns no results."""
    fallbacks: List[str] = []

    def _normalize(candidate: str) -> Optional[str]:
        candidate = candidate.strip().rstrip(";")
        candidate = re.sub(r"\.\.", ".", candidate)
        candidate = re.sub(r"\.l\.l", ".l", candidate)
        candidate = re.sub(r"\.l\.(take|head|size)", r".l.\1", candidate)
        if not candidate:
            return None
        return candidate

    if ".tag." in query:
        fallbacks.append(re.sub(r"\.tag\.[^\.]+\(\".*?\"\)", "", query))

    loosened = re.sub(r"\.valueExact\(\".*?\"\)", "", query)
    loosened = re.sub(r"\.tag\.[^\.]+\(\".*?\"\)", "", loosened)
    fallbacks.append(loosened)

    if ".argument." in query:
        fallbacks.append(re.sub(r"\.argument[^\.]*", "", query))

    if "cpg.call" in query:
        fallbacks.append(query.replace("cpg.call", "cpg.method"))

    for match in re.findall(r'\.name\("([^"]+)"\)', query):
        if not match:
            continue
        base = match.replace("*", "")
        if match and "*" not in match and len(match) >= 3:
            fallbacks.append(query.replace(f'.name("{match}")', f'.name("{match}*")'))
        if base and len(base) >= 3:
            regex_variant = f'.name(".*{re.escape(base)}.*")'
            fallbacks.append(query.replace(f'.name("{match}")', regex_variant))

    for match in re.findall(r'\.nameExact\("([^"]+)"\)', query):
        if not match:
            continue
        base = match.replace("*", "")
        if match and "*" not in match and len(match) >= 3:
            fallbacks.append(query.replace(f'.nameExact("{match}")', f'.name("{match}*")'))
        if base and len(base) >= 3:
            regex_variant = f'.name(".*{re.escape(base)}.*")'
            fallbacks.append(query.replace(f'.nameExact("{match}")', regex_variant))

    normalized = _normalize(query)
    if normalized and normalized.endswith(".l"):
        fallbacks.append(f"{normalized}.take(20)")

    cleaned: List[str] = []
    seen = set()
    for candidate in fallbacks:
        candidate = _normalize(candidate)
        if not candidate:
            continue
        if not candidate.endswith(".l") and not candidate.endswith(".take(20)"):
            candidate = re.sub(r"\.l$", "", candidate)
            candidate += ".l"
        candidate = candidate.replace("..", ".")
        if candidate not in seen and candidate != query:
            seen.add(candidate)
            cleaned.append(candidate)

    expanded: List[str] = []
    for candidate in cleaned:
        expanded.append(candidate)
        if "cpg.call" in candidate:
            expanded.append(candidate.replace("cpg.call", "cpg.method", 1))

    final: List[str] = []
    final_seen = set()
    for candidate in expanded:
        candidate = _normalize(candidate)
        if not candidate:
            continue
        if not candidate.endswith(".l") and not candidate.endswith(".take(20)"):
            candidate = re.sub(r"\.l$", "", candidate)
            candidate += ".l"
        candidate = candidate.replace("..", ".")
        if candidate not in final_seen and candidate != query:
            final_seen.add(candidate)
            final.append(candidate)

    return final


def build_keyword_fallback_query(state: dict) -> Optional[str]:
    """Build a keyword-based fallback query from state keywords."""
    keywords = state.get("keywords") or []
    for keyword in keywords:
        token = re.sub(r"[^A-Za-z0-9_]", "", keyword)
        if token and len(token) >= 3:
            pattern = re.escape(token)
            return f'cpg.method.name(".*{pattern}.*").l.take(20)'
    return None
