"""
DLP Pattern Registry - Manages patterns for sensitive data detection.

Supports:
- Regex patterns with named groups
- Keyword lists (blacklist/whitelist)
- Predefined patterns for common data types
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set, Tuple, Any
from enum import Enum

from ..config import (
    DLPConfig,
    DLPCategoryConfig,
    DLPPatternConfig,
    DLPAction,
    get_default_dlp_categories,
)

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    """Type of DLP match."""
    REGEX = "regex"
    KEYWORD = "keyword"


@dataclass
class DLPMatch:
    """
    Represents a DLP pattern match in content.

    Attributes:
        category: DLP category (credentials, pii, etc.)
        pattern_name: Name of the matched pattern
        match_type: Type of match (regex or keyword)
        matched_text: The actual matched text
        start: Start position in content
        end: End position in content
        action: Recommended action for this match
        mask_with: Replacement text for masking
        severity: Match severity (from category)
    """
    category: str
    pattern_name: str
    match_type: MatchType
    matched_text: str
    start: int
    end: int
    action: DLPAction
    mask_with: str = "[REDACTED]"
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category,
            "pattern_name": self.pattern_name,
            "match_type": self.match_type.value,
            "matched_text": self.matched_text[:50] + "..." if len(self.matched_text) > 50 else self.matched_text,
            "start": self.start,
            "end": self.end,
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "mask_with": self.mask_with,
            "severity": self.severity,
        }


@dataclass
class CompiledPattern:
    """A compiled regex pattern with metadata."""
    name: str
    category: str
    regex: Pattern
    action: DLPAction
    mask_with: str = "[REDACTED]"
    description: Optional[str] = None


class PatternRegistry:
    """
    Registry for DLP patterns.

    Manages:
    - Regex patterns compiled for efficient matching
    - Keyword lists for fast lookup
    - Category-based organization
    """

    def __init__(self, config: DLPConfig):
        """
        Initialize pattern registry from configuration.

        Args:
            config: DLP configuration
        """
        self._config = config
        self._patterns: Dict[str, List[CompiledPattern]] = {}  # category -> patterns
        self._keywords: Dict[str, Set[str]] = {}  # list_name -> keywords
        self._keyword_action = config.keywords_action

        self._load_patterns()
        self._load_keywords()

    def _load_patterns(self) -> None:
        """Load and compile regex patterns from config."""
        # Start with default patterns if categories not specified
        categories = self._config.categories
        if not categories:
            categories = get_default_dlp_categories()

        for category_name, category_config in categories.items():
            if not category_config.enabled:
                continue

            compiled_patterns = []
            for pattern_config in category_config.patterns:
                try:
                    compiled = re.compile(pattern_config.regex, re.IGNORECASE | re.MULTILINE)
                    compiled_patterns.append(CompiledPattern(
                        name=pattern_config.name,
                        category=category_name,
                        regex=compiled,
                        action=DLPAction(category_config.action) if isinstance(category_config.action, str) else category_config.action,
                        mask_with=pattern_config.mask_with,
                        description=pattern_config.description,
                    ))
                    logger.debug(f"Loaded pattern: {category_name}/{pattern_config.name}")
                except re.error as e:
                    logger.error(f"Invalid regex pattern {pattern_config.name}: {e}")

            if compiled_patterns:
                self._patterns[category_name] = compiled_patterns

        logger.info(f"Loaded {sum(len(p) for p in self._patterns.values())} patterns in {len(self._patterns)} categories")

    def _load_keywords(self) -> None:
        """Load keyword lists from config."""
        for list_name, keyword_config in self._config.keywords.items():
            words = set(keyword_config.words)
            if not keyword_config.case_sensitive:
                words = {w.lower() for w in words}
            self._keywords[list_name] = words
            logger.debug(f"Loaded keyword list: {list_name} ({len(words)} words)")

    def match_patterns(self, content: str) -> List[DLPMatch]:
        """
        Find all pattern matches in content.

        Args:
            content: Text content to scan

        Returns:
            List of DLPMatch objects
        """
        matches = []

        for category_name, patterns in self._patterns.items():
            for pattern in patterns:
                try:
                    for match in pattern.regex.finditer(content):
                        matches.append(DLPMatch(
                            category=category_name,
                            pattern_name=pattern.name,
                            match_type=MatchType.REGEX,
                            matched_text=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            action=pattern.action,
                            mask_with=pattern.mask_with,
                            severity=self._get_severity(pattern.action),
                        ))
                except Exception as e:
                    logger.error(f"Error matching pattern {pattern.name}: {e}")

        return matches

    def match_keywords(self, content: str) -> List[DLPMatch]:
        """
        Find all keyword matches in content.

        Args:
            content: Text content to scan

        Returns:
            List of DLPMatch objects
        """
        matches = []
        content_lower = content.lower()

        for list_name, keywords in self._keywords.items():
            for keyword in keywords:
                # Find all occurrences
                search_content = content_lower
                keyword_lower = keyword.lower()
                start = 0

                while True:
                    pos = search_content.find(keyword_lower, start)
                    if pos == -1:
                        break

                    matches.append(DLPMatch(
                        category="keywords",
                        pattern_name=list_name,
                        match_type=MatchType.KEYWORD,
                        matched_text=content[pos:pos + len(keyword)],
                        start=pos,
                        end=pos + len(keyword),
                        action=self._keyword_action,
                        mask_with="[KEYWORD]",
                        severity=self._get_severity(self._keyword_action),
                    ))

                    start = pos + 1

        return matches

    def match_all(self, content: str) -> List[DLPMatch]:
        """
        Find all matches (patterns and keywords) in content.

        Args:
            content: Text content to scan

        Returns:
            List of DLPMatch objects, sorted by start position
        """
        matches = self.match_patterns(content)

        if self._config.keywords:
            matches.extend(self.match_keywords(content))

        # Sort by position
        matches.sort(key=lambda m: m.start)

        return matches

    @staticmethod
    def _get_severity(action: DLPAction) -> str:
        """Map action to severity level."""
        severity_map = {
            DLPAction.BLOCK: "critical",
            DLPAction.MASK: "high",
            DLPAction.WARN: "medium",
            DLPAction.LOG_ONLY: "low",
        }
        return severity_map.get(action, "medium")

    def get_categories(self) -> List[str]:
        """Get list of enabled categories."""
        return list(self._patterns.keys())

    def get_pattern_count(self) -> int:
        """Get total number of loaded patterns."""
        return sum(len(p) for p in self._patterns.values())

    def get_keyword_count(self) -> int:
        """Get total number of keywords."""
        return sum(len(k) for k in self._keywords.values())

    def add_pattern(
        self,
        category: str,
        name: str,
        regex: str,
        action: DLPAction = DLPAction.WARN,
        mask_with: str = "[REDACTED]",
    ) -> bool:
        """
        Add a new pattern dynamically.

        Args:
            category: Category name
            name: Pattern name
            regex: Regex pattern string
            action: Action to take on match
            mask_with: Replacement text

        Returns:
            True if pattern was added successfully
        """
        try:
            compiled = re.compile(regex, re.IGNORECASE | re.MULTILINE)
            pattern = CompiledPattern(
                name=name,
                category=category,
                regex=compiled,
                action=action,
                mask_with=mask_with,
            )

            if category not in self._patterns:
                self._patterns[category] = []
            self._patterns[category].append(pattern)

            logger.info(f"Added pattern: {category}/{name}")
            return True

        except re.error as e:
            logger.error(f"Failed to add pattern {name}: {e}")
            return False

    def add_keywords(self, list_name: str, keywords: List[str], case_sensitive: bool = False) -> None:
        """
        Add keywords to a list.

        Args:
            list_name: Name of the keyword list
            keywords: Keywords to add
            case_sensitive: Whether keywords are case-sensitive
        """
        if list_name not in self._keywords:
            self._keywords[list_name] = set()

        if case_sensitive:
            self._keywords[list_name].update(keywords)
        else:
            self._keywords[list_name].update(w.lower() for w in keywords)

        logger.info(f"Added {len(keywords)} keywords to list: {list_name}")
