"""Query validation module for validating generated CPGQL queries.

This module validates generated queries to ensure they only use valid tag values,
catching LLM hallucinations that bypass enrichment validation.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

from src.validation.tag_validator import get_validator

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validates generated CPGQL queries for invalid tag values."""

    def __init__(self):
        """Initialize query validator with tag validator."""
        self.tag_validator = get_validator()
        logger.info("QueryValidator initialized")

    def _find_most_similar_tag(self, invalid_value: str, valid_values: List[str]) -> str:
        """Find the most semantically similar valid tag value.

        Uses string similarity to find the best match instead of just using the first value.

        Args:
            invalid_value: The invalid tag value to match
            valid_values: List of valid tag values

        Returns:
            The most similar valid tag value
        """
        if not valid_values:
            return None

        # Calculate similarity scores for all valid values
        similarities = []
        for valid_value in valid_values:
            # Use SequenceMatcher for string similarity
            similarity = SequenceMatcher(None, invalid_value.lower(), valid_value.lower()).ratio()

            # Boost score if invalid value is substring of valid value or vice versa
            if invalid_value.lower() in valid_value.lower() or valid_value.lower() in invalid_value.lower():
                similarity += 0.3

            # Boost score for word overlap
            invalid_words = set(invalid_value.lower().replace('-', ' ').split())
            valid_words = set(valid_value.lower().replace('-', ' ').split())
            word_overlap = len(invalid_words & valid_words) / max(len(invalid_words), len(valid_words)) if invalid_words or valid_words else 0
            similarity += word_overlap * 0.2

            similarities.append((valid_value, similarity))

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)

        best_match = similarities[0][0]
        best_score = similarities[0][1]

        logger.debug(f"Semantic fallback: '{invalid_value}' -> '{best_match}' (similarity: {best_score:.2f})")

        return best_match

    def extract_tag_filters(self, query: str) -> List[Tuple[str, str]]:
        """Extract all tag filters from a CPGQL query.

        Args:
            query: CPGQL query string

        Returns:
            List of (tag_name, tag_value) tuples found in the query
        """
        # Pattern: .where(_.tag.name("X").value("Y"))
        # Also matches: .where(_.tag.nameExact("X").valueExact("Y"))
        pattern = r'\.tag\.(?:name|nameExact)\(["\']([^"\']+)["\']\)\.(?:value|valueExact)\(["\']([^"\']+)["\']\)'

        matches = re.findall(pattern, query)
        return matches

    def validate_query(self, query: str) -> Dict:
        """Validate all tag filters in a query.

        Args:
            query: CPGQL query string

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "invalid_tags": List[Tuple[str, str]],
                "corrected_query": str,
                "corrections": List[str],
                "warnings": List[str]
            }
        """
        # Extract all tag filters
        tag_filters = self.extract_tag_filters(query)

        if not tag_filters:
            logger.debug("No tag filters found in query")
            return {
                "valid": True,
                "invalid_tags": [],
                "corrected_query": query,
                "corrections": [],
                "warnings": []
            }

        logger.debug(f"Found {len(tag_filters)} tag filters to validate")

        invalid_tags = []
        corrections = []
        warnings = []
        corrected_query = query

        for tag_name, tag_value in tag_filters:
            # Validate the tag
            is_valid, corrected_value = self.tag_validator.validate_and_correct(tag_name, tag_value)

            if not is_valid:
                invalid_tags.append((tag_name, tag_value))

                # Try to find valid alternatives
                valid_values = self.tag_validator.get_valid_values(tag_name)

                if valid_values:
                    # Use the first valid value as a fallback
                    # Note: Tested semantic similarity (see SEMANTIC_FALLBACK_ANALYSIS.md)
                    # but first-value fallback performs better (76.7% vs 53.3%) because
                    # the first value ('catalog-access') returns more results in the CPG.
                    fallback_value = valid_values[0]

                    # Replace in query
                    old_pattern = f'.tag.name("{tag_name}").value("{tag_value}")'
                    new_pattern = f'.tag.name("{tag_name}").value("{fallback_value}")'

                    if old_pattern in corrected_query:
                        corrected_query = corrected_query.replace(old_pattern, new_pattern)
                        corrections.append(f"Replaced {tag_name}='{tag_value}' with '{fallback_value}'")
                        logger.warning(f"Corrected invalid tag: {tag_name}='{tag_value}' -> '{fallback_value}'")
                    else:
                        # Try exact matching pattern
                        old_pattern_exact = f'.tag.nameExact("{tag_name}").valueExact("{tag_value}")'
                        new_pattern_exact = f'.tag.nameExact("{tag_name}").valueExact("{fallback_value}")'

                        if old_pattern_exact in corrected_query:
                            corrected_query = corrected_query.replace(old_pattern_exact, new_pattern_exact)
                            corrections.append(f"Replaced {tag_name}='{tag_value}' with '{fallback_value}'")
                            logger.warning(f"Corrected invalid tag: {tag_name}='{tag_value}' -> '{fallback_value}'")
                        else:
                            warnings.append(
                                f"Invalid tag {tag_name}='{tag_value}' could not be replaced. "
                                f"Valid values: {', '.join(valid_values[:5])}"
                            )
                else:
                    warnings.append(
                        f"Invalid tag {tag_name}='{tag_value}' with no valid alternatives"
                    )

            elif corrected_value:
                # Tag was corrected (common mismatch)
                old_pattern = f'.tag.name("{tag_name}").value("{tag_value}")'
                new_pattern = f'.tag.name("{tag_name}").value("{corrected_value}")'

                if old_pattern in corrected_query:
                    corrected_query = corrected_query.replace(old_pattern, new_pattern)
                    corrections.append(f"Auto-corrected {tag_name}='{tag_value}' to '{corrected_value}'")
                    logger.info(f"Auto-corrected tag: {tag_name}='{tag_value}' -> '{corrected_value}'")

        # Determine overall validity
        all_valid = len(invalid_tags) == 0 or len(corrections) > 0

        if corrections:
            logger.info(f"Query validation: {len(corrections)} corrections applied, {len(warnings)} warnings")
        elif warnings:
            logger.warning(f"Query validation: {len(warnings)} warnings, no corrections possible")

        return {
            "valid": all_valid,
            "invalid_tags": invalid_tags,
            "corrected_query": corrected_query,
            "corrections": corrections,
            "warnings": warnings
        }

    def validate_and_fix(self, query: str) -> Tuple[str, bool, List[str]]:
        """Validate query and return corrected version.

        Args:
            query: CPGQL query string

        Returns:
            Tuple of (corrected_query, was_modified, warnings)
        """
        validation_result = self.validate_query(query)

        was_modified = len(validation_result["corrections"]) > 0

        return (
            validation_result["corrected_query"],
            was_modified,
            validation_result["warnings"]
        )


# Global validator instance
_query_validator_instance: Optional[QueryValidator] = None


def get_query_validator() -> QueryValidator:
    """Get singleton QueryValidator instance."""
    global _query_validator_instance
    if _query_validator_instance is None:
        _query_validator_instance = QueryValidator()
    return _query_validator_instance


def validate_query(query: str) -> Dict:
    """Convenience function to validate a query.

    Args:
        query: CPGQL query string

    Returns:
        Validation results dict
    """
    validator = get_query_validator()
    return validator.validate_query(query)


def validate_and_fix_query(query: str) -> Tuple[str, bool, List[str]]:
    """Convenience function to validate and fix a query.

    Args:
        query: CPGQL query string

    Returns:
        Tuple of (corrected_query, was_modified, warnings)
    """
    validator = get_query_validator()
    return validator.validate_and_fix(query)


def generate_tag_relaxation_variants(query: str) -> List[Dict[str, str]]:
    """Generate progressive tag relaxation variants for a query.

    Creates fallback queries by systematically removing tag filters to combat
    overly restrictive queries that return 0 results.

    Strategy:
    1. Original query (all tags)
    2. Remove lowest priority tag (domain-concept)
    3. Remove next lowest (data-structure)
    4. Keep only highest priority (function-purpose)

    Args:
        query: CPGQL query string with tag filters

    Returns:
        List of variant dicts with keys:
        - query: str (relaxed CPGQL query)
        - tags_removed: str (description of what was removed)
        - priority: int (1=highest priority, lower number = try first)

    Example:
        Original: cpg.method.where(_.tag.name("function-purpose").value("storage"))
                             .where(_.tag.name("data-structure").value("array"))
                             .where(_.tag.name("domain-concept").value("extension"))

        Variant 1: Remove domain-concept tag
        Variant 2: Remove data-structure tag
        Variant 3: Keep only function-purpose tag
    """
    import re

    # Tag priority order (highest to lowest)
    # Keep function-purpose longest, remove domain-concept first
    TAG_PRIORITY = {
        'function-purpose': 3,   # KEEP (highest priority)
        'data-structure': 2,     # Remove second
        'domain-concept': 1,     # Remove first (lowest priority)
        'algorithm': 1,          # Same as domain-concept
        'feature': 1             # Same as domain-concept
    }

    # Extract all tag filters
    validator = get_query_validator()
    tag_filters = validator.extract_tag_filters(query)

    if len(tag_filters) <= 1:
        # Can't relax a query with 0 or 1 tags
        return []

    logger.info(f"Generating tag relaxation variants for query with {len(tag_filters)} tags")

    variants = []

    # Sort tags by priority (lowest first, so we remove them in order)
    sorted_tags = sorted(tag_filters, key=lambda t: TAG_PRIORITY.get(t[0], 0))

    # Generate variants by progressively removing low-priority tags
    for i in range(len(sorted_tags) - 1):  # Keep at least 1 tag
        # Remove tags from index 0 to i (inclusive)
        tags_to_keep = sorted_tags[i+1:]

        # Build relaxed query by removing the low-priority tag filters
        relaxed_query = query

        for tag_name, tag_value in sorted_tags[:i+1]:
            # Remove this tag filter from the query
            # Pattern: .where(_.tag.name("X").value("Y"))
            pattern1 = f'.where(_.tag.name("{tag_name}").value("{tag_value}"))'
            pattern2 = f'.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}"))'

            if pattern1 in relaxed_query:
                relaxed_query = relaxed_query.replace(pattern1, '')
            elif pattern2 in relaxed_query:
                relaxed_query = relaxed_query.replace(pattern2, '')

        # Clean up any double newlines or spaces
        relaxed_query = re.sub(r'\n\s*\n', '\n', relaxed_query)
        relaxed_query = re.sub(r'  +', ' ', relaxed_query)

        removed_tags = sorted_tags[:i+1]
        removed_names = [tag[0] for tag in removed_tags]

        variants.append({
            'query': relaxed_query,
            'tags_removed': f"Removed {', '.join(removed_names)}",
            'tags_kept': len(tags_to_keep),
            'priority': i + 1  # Lower number = higher priority
        })

        logger.debug(f"Relaxation variant {i+1}: Removed {removed_names}, kept {len(tags_to_keep)} tags")

    logger.info(f"Generated {len(variants)} tag relaxation variants")
    return variants


def apply_fuzzy_method_name_matching(query: str) -> str:
    """Convert exact method name filters to fuzzy pattern matching.

    Transforms queries with exact .name("method_name") filters to use
    wildcard patterns .name(".*method.*") for broader matching.

    This helps when the exact method name doesn't exist but similar methods do.

    Args:
        query: CPGQL query string

    Returns:
        Modified query with fuzzy method name patterns

    Example:
        Input:  cpg.method.name("timestamp2time_t").l
        Output: cpg.method.name(".*timestamp.*").l

        Input:  cpg.method.where(...).name("get_page").l
        Output: cpg.method.where(...).name(".*get_page.*").l
    """
    import re

    # Pattern: .name("exact_method_name")
    # Don't match: .name(".*already_fuzzy.*")
    pattern = r'\.name\("([^"*]+)"\)'

    def make_fuzzy(match):
        method_name = match.group(1)

        # If already has wildcards, don't modify
        if '.*' in method_name or '*' in method_name:
            return match.group(0)

        # Extract core keyword from method name
        # For "timestamp2time_t" -> "timestamp"
        # For "get_page_buffer" -> "page"
        # Simple heuristic: use the longest word-like segment
        parts = re.split(r'[_\d]+', method_name)
        core_keyword = max(parts, key=len) if parts else method_name

        # Create fuzzy pattern
        fuzzy_pattern = f'.*{core_keyword}.*'

        logger.debug(f"Fuzzy match: '{method_name}' -> '{fuzzy_pattern}'")

        return f'.name("{fuzzy_pattern}")'

    fuzzy_query = re.sub(pattern, make_fuzzy, query)

    if fuzzy_query != query:
        logger.info(f"Applied fuzzy method name matching to query")

    return fuzzy_query
