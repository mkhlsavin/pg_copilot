"""Tag validation module for ensuring enrichment uses only valid CPG tag values.

This module provides validation and correction for enrichment tags to prevent
queries from failing due to non-existent tag values in the CPG.
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TagValidator:
    """Validates enrichment tags against actual CPG tag values."""

    def __init__(self, cpg_tags_file: Optional[str] = None):
        """Initialize validator with CPG tag data.

        Args:
            cpg_tags_file: Path to cpg_actual_tags.json file.
                          If None, uses default location.
        """
        if cpg_tags_file is None:
            cpg_tags_file = Path(__file__).parent.parent.parent / "data" / "cpg_actual_tags.json"
        else:
            cpg_tags_file = Path(cpg_tags_file)

        if not cpg_tags_file.exists():
            raise FileNotFoundError(f"CPG tags file not found: {cpg_tags_file}")

        with open(cpg_tags_file, 'r') as f:
            self.cpg_tags_data = json.load(f)

        # Build lookup structures
        self._build_tag_lookups()

        logger.info(f"TagValidator initialized with {len(self.valid_tags)} tag categories")

    def _build_tag_lookups(self):
        """Build efficient lookup structures from CPG tags data."""
        tag_categories = self.cpg_tags_data.get("tag_categories", {})

        # Valid tag name -> set of valid values
        self.valid_tags: Dict[str, Set[str]] = {}
        # Some tags allow arbitrary string values (e.g., literal constants)
        self.open_value_tags: Set[str] = {
            "literal-constant",
            "is-lock-constant",
            "data-flow-kind",
            "child-role",
            "call-action",
            "call-side-effect",
            "call-receiver-role",
            "argument-param-name",
            "branch-kind",
            "control-reason"
        }

        for tag_name, tag_info in tag_categories.items():
            if "values" in tag_info:
                self.valid_tags[tag_name] = set(tag_info["values"])
            else:
                # Feature tags have no fixed values (too specific)
                self.valid_tags[tag_name] = set()

        # Common mismatches for corrections
        self.common_mismatches = self.cpg_tags_data.get("common_mismatches", {})

        # Reverse lookup: wrong value -> correct value
        self.corrections: Dict[str, str] = {}
        for wrong, correct in self.common_mismatches.items():
            if " or " not in correct and "NOT IN" not in correct:
                self.corrections[wrong] = correct

        logger.debug(f"Built lookups: {len(self.valid_tags)} tag types, {len(self.corrections)} corrections")

    def is_valid_tag(self, tag_name: str, tag_value: str) -> bool:
        """Check if a tag name/value pair is valid.

        Args:
            tag_name: Tag name (e.g., "function-purpose")
            tag_value: Tag value (e.g., "wal-logging")

        Returns:
            True if the tag value exists in the CPG for this tag name
        """
        if tag_name not in self.valid_tags:
            logger.warning(f"Unknown tag name: {tag_name}")
            return False

        # Feature tags have no fixed values (always skip)
        if tag_name == "Feature":
            logger.debug(f"Skipping Feature tag validation (too specific)")
            return False

        if tag_name in self.open_value_tags:
            return True

        valid_values = self.valid_tags[tag_name]
        is_valid = tag_value in valid_values

        if not is_valid:
            logger.debug(f"Invalid tag value: {tag_name}={tag_value} (not in {valid_values})")

        return is_valid

    def correct_tag_value(self, tag_value: str) -> Optional[str]:
        """Attempt to correct a common mismatch.

        Args:
            tag_value: Potentially incorrect tag value

        Returns:
            Corrected value if known, None otherwise
        """
        return self.corrections.get(tag_value)

    def validate_and_correct(self, tag_name: str, tag_value: str) -> Tuple[bool, Optional[str]]:
        """Validate a tag and attempt correction if invalid.

        Args:
            tag_name: Tag name (e.g., "function-purpose")
            tag_value: Tag value (e.g., "transaction-management")

        Returns:
            Tuple of (is_valid, corrected_value)
            - is_valid: True if original or corrected value is valid
            - corrected_value: Corrected value if correction applied, None otherwise
        """
        # Check if original value is valid
        if self.is_valid_tag(tag_name, tag_value):
            return (True, None)

        # Try to correct
        corrected = self.correct_tag_value(tag_value)
        if corrected:
            # Verify correction is valid
            if self.is_valid_tag(tag_name, corrected):
                logger.info(f"Corrected tag: {tag_value} -> {corrected}")
                return (True, corrected)

        # No valid correction found
        return (False, None)

    def get_valid_values(self, tag_name: str) -> List[str]:
        """Get all valid values for a tag name.

        Args:
            tag_name: Tag name (e.g., "function-purpose")

        Returns:
            List of valid values, empty list if tag name unknown
        """
        if tag_name not in self.valid_tags:
            return []
        return sorted(list(self.valid_tags[tag_name]))

    def get_high_coverage_tags(self) -> Dict[str, List[str]]:
        """Get tags that provide high coverage in CPG.

        These are safe fallback tags that return many results.

        Returns:
            Dict of tag_name -> list of high-coverage values
        """
        # Based on analysis, these tags have high coverage
        high_coverage = {
            "function-purpose": [
                "general",
                "utilities",
                "memory-management",
                "error-handling"
            ],
            "domain-concept": [
                "vacuum",
                "mvcc",
                "replication"
            ],
            "data-structure": [
                "array",
                "buffer",
                "hash-table"
            ]
        }

        # Validate all are actually in CPG
        validated = {}
        for tag_name, values in high_coverage.items():
            validated[tag_name] = [
                v for v in values
                if self.is_valid_tag(tag_name, v)
            ]

        return validated

    def validate_enrichment(self, enrichment_data: Dict) -> Dict:
        """Validate all tags in enrichment data and provide corrections.

        Args:
            enrichment_data: Enrichment dict with 'tags' field

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "invalid_tags": List[Tuple[str, str]],
                "corrected_tags": Dict[Tuple[str, str], str],
                "suggestions": List[str]
            }
        """
        tags = enrichment_data.get("tags", {})

        invalid_tags = []
        corrected_tags = {}
        suggestions = []

        for tag_name, tag_values in tags.items():
            # Handle both single values and lists
            if not isinstance(tag_values, list):
                tag_values = [tag_values]

            for tag_value in tag_values:
                is_valid, corrected = self.validate_and_correct(tag_name, tag_value)

                if not is_valid:
                    invalid_tags.append((tag_name, tag_value))

                    # Get valid alternatives
                    valid_values = self.get_valid_values(tag_name)
                    if valid_values:
                        suggestions.append(
                            f"Invalid {tag_name}='{tag_value}'. Valid values: {', '.join(valid_values[:5])}"
                        )
                elif corrected:
                    corrected_tags[(tag_name, tag_value)] = corrected

        return {
            "valid": len(invalid_tags) == 0,
            "invalid_tags": invalid_tags,
            "corrected_tags": corrected_tags,
            "suggestions": suggestions
        }

    def filter_valid_tags(self, enrichment_data: Dict) -> Dict:
        """Filter enrichment data to keep only valid tags.

        Args:
            enrichment_data: Enrichment dict with 'tags' field

        Returns:
            Filtered enrichment data with only valid tags
        """
        tags = enrichment_data.get("tags", {})
        filtered_tags = {}

        for tag_name, tag_values in tags.items():
            # Handle both single values and lists
            if not isinstance(tag_values, list):
                tag_values = [tag_values]

            valid_values = []
            for tag_value in tag_values:
                is_valid, corrected = self.validate_and_correct(tag_name, tag_value)

                if is_valid:
                    # Use corrected value if available, otherwise original
                    valid_values.append(corrected if corrected else tag_value)

            if valid_values:
                filtered_tags[tag_name] = valid_values if len(valid_values) > 1 else valid_values[0]

        # Return copy with filtered tags
        result = enrichment_data.copy()
        result["tags"] = filtered_tags
        return result


# Global validator instance
_validator_instance: Optional[TagValidator] = None


def get_validator() -> TagValidator:
    """Get singleton TagValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = TagValidator()
    return _validator_instance


def validate_tag(tag_name: str, tag_value: str) -> bool:
    """Convenience function to validate a single tag.

    Args:
        tag_name: Tag name (e.g., "function-purpose")
        tag_value: Tag value (e.g., "wal-logging")

    Returns:
        True if valid
    """
    validator = get_validator()
    return validator.is_valid_tag(tag_name, tag_value)


def validate_enrichment(enrichment_data: Dict) -> Dict:
    """Convenience function to validate enrichment data.

    Args:
        enrichment_data: Enrichment dict with 'tags' field

    Returns:
        Validation results dict
    """
    validator = get_validator()
    return validator.validate_enrichment(enrichment_data)


def filter_valid_tags(enrichment_data: Dict) -> Dict:
    """Convenience function to filter to valid tags only.

    Args:
        enrichment_data: Enrichment dict with 'tags' field

    Returns:
        Filtered enrichment data
    """
    validator = get_validator()
    return validator.filter_valid_tags(enrichment_data)
