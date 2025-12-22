"""
DLP Content Scanner - Scans content for sensitive data.

Provides pre-request and post-response scanning with configurable actions.
"""

import logging
from typing import List, Optional, Tuple, Any, Dict
from dataclasses import dataclass

from .patterns import PatternRegistry, DLPMatch, MatchType
from ..config import DLPConfig, DLPAction, get_default_dlp_categories

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """
    Result of a content scan.

    Attributes:
        has_matches: Whether any patterns matched
        matches: List of DLP matches found
        action: Highest-priority action to take
        modified_content: Content after masking (if applicable)
        blocked: Whether content should be blocked
    """
    has_matches: bool
    matches: List[DLPMatch]
    action: DLPAction
    modified_content: Optional[str]
    blocked: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "has_matches": self.has_matches,
            "match_count": len(self.matches),
            "action": self.action.value if isinstance(self.action, DLPAction) else self.action,
            "blocked": self.blocked,
            "matches": [m.to_dict() for m in self.matches[:10]],  # Limit for logging
        }


class ContentScanner:
    """
    Scans content for sensitive data and applies DLP actions.

    Usage:
        scanner = ContentScanner(dlp_config)

        # Pre-request scan
        result = scanner.scan_request(prompt_text)
        if result.blocked:
            raise DLPBlockedException(result.matches)
        elif result.action == DLPAction.MASK:
            prompt_text = result.modified_content

        # Post-response scan
        result = scanner.scan_response(response_text)
        if result.has_matches:
            response_text = result.modified_content
    """

    # Action priority (higher = more restrictive)
    ACTION_PRIORITY = {
        DLPAction.BLOCK: 4,
        DLPAction.MASK: 3,
        DLPAction.WARN: 2,
        DLPAction.LOG_ONLY: 1,
    }

    def __init__(self, config: DLPConfig):
        """
        Initialize content scanner.

        Args:
            config: DLP configuration
        """
        self._config = config
        self._enabled = config.enabled

        # Merge default patterns with config categories
        default_categories = get_default_dlp_categories()

        if not config.categories:
            # No categories configured - use all defaults
            config.categories = default_categories
        else:
            # Merge: use config settings but add default patterns if category has none
            for cat_name, default_cat in default_categories.items():
                if cat_name in config.categories:
                    cat = config.categories[cat_name]
                    # If category exists but has no patterns, use defaults
                    if not cat.patterns:
                        cat.patterns = default_cat.patterns
                else:
                    # Add missing default categories
                    config.categories[cat_name] = default_cat

        self._registry = PatternRegistry(config)

        logger.info(f"ContentScanner initialized: {self._registry.get_pattern_count()} patterns, "
                   f"{self._registry.get_keyword_count()} keywords")

    def scan(self, content: str) -> List[DLPMatch]:
        """
        Scan content for all DLP matches.

        Args:
            content: Text content to scan

        Returns:
            List of DLPMatch objects
        """
        if not self._enabled or not content:
            return []

        return self._registry.match_all(content)

    def scan_request(self, content: str) -> ScanResult:
        """
        Scan pre-request content (before sending to LLM).

        Uses pre_request configuration for action defaults.

        Args:
            content: Request content to scan

        Returns:
            ScanResult with action and optionally modified content
        """
        if not self._enabled or not self._config.pre_request.enabled:
            return ScanResult(
                has_matches=False,
                matches=[],
                action=DLPAction.LOG_ONLY,
                modified_content=None,
                blocked=False,
            )

        matches = self.scan(content)

        if not matches:
            return ScanResult(
                has_matches=False,
                matches=[],
                action=DLPAction.LOG_ONLY,
                modified_content=None,
                blocked=False,
            )

        # Determine highest-priority action
        action = self._get_highest_action(matches, self._config.pre_request.default_action)

        # Apply action
        blocked = action == DLPAction.BLOCK
        modified_content = None

        if action == DLPAction.MASK and not blocked:
            modified_content = self._mask_content(content, matches)

        return ScanResult(
            has_matches=True,
            matches=matches,
            action=action,
            modified_content=modified_content,
            blocked=blocked,
        )

    def scan_response(self, content: str) -> ScanResult:
        """
        Scan post-response content (from LLM).

        Uses post_response configuration for action defaults.
        Typically masks sensitive data in responses rather than blocking.

        Args:
            content: Response content to scan

        Returns:
            ScanResult with action and optionally modified content
        """
        if not self._enabled or not self._config.post_response.enabled:
            return ScanResult(
                has_matches=False,
                matches=[],
                action=DLPAction.LOG_ONLY,
                modified_content=None,
                blocked=False,
            )

        matches = self.scan(content)

        if not matches:
            return ScanResult(
                has_matches=False,
                matches=[],
                action=DLPAction.LOG_ONLY,
                modified_content=None,
                blocked=False,
            )

        # For responses, typically mask rather than block
        action = self._get_highest_action(matches, self._config.post_response.default_action)

        # Always mask for responses (don't block)
        modified_content = self._mask_content(content, matches)

        return ScanResult(
            has_matches=True,
            matches=matches,
            action=action,
            modified_content=modified_content,
            blocked=False,  # Never block responses
        )

    def _get_highest_action(self, matches: List[DLPMatch], default: DLPAction) -> DLPAction:
        """
        Get the highest-priority action from matches.

        Args:
            matches: List of DLP matches
            default: Default action if no matches specify action

        Returns:
            Highest-priority DLPAction
        """
        if not matches:
            return default

        highest = default
        highest_priority = self.ACTION_PRIORITY.get(default, 0)

        for match in matches:
            match_priority = self.ACTION_PRIORITY.get(match.action, 0)
            if match_priority > highest_priority:
                highest = match.action
                highest_priority = match_priority

        return highest

    def _mask_content(self, content: str, matches: List[DLPMatch]) -> str:
        """
        Mask matched content with replacement strings.

        Args:
            content: Original content
            matches: List of matches to mask

        Returns:
            Content with sensitive data masked
        """
        if not matches:
            return content

        # Sort matches by position in reverse order to avoid offset issues
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

        result = content
        for match in sorted_matches:
            result = result[:match.start] + match.mask_with + result[match.end:]

        return result

    def get_action(self, matches: List[DLPMatch]) -> DLPAction:
        """
        Determine the action to take based on matches.

        Args:
            matches: List of DLP matches

        Returns:
            Highest-priority DLPAction
        """
        return self._get_highest_action(matches, DLPAction.LOG_ONLY)

    def mask(self, content: str, matches: List[DLPMatch]) -> str:
        """
        Mask content based on matches.

        Args:
            content: Original content
            matches: Matches to mask

        Returns:
            Masked content
        """
        return self._mask_content(content, matches)

    @property
    def is_enabled(self) -> bool:
        """Check if scanner is enabled."""
        return self._enabled

    @property
    def pattern_count(self) -> int:
        """Get number of loaded patterns."""
        return self._registry.get_pattern_count()

    @property
    def categories(self) -> List[str]:
        """Get list of enabled categories."""
        return self._registry.get_categories()


class DLPBlockedException(Exception):
    """
    Exception raised when content is blocked by DLP.

    Attributes:
        matches: List of matches that triggered the block
        message: Human-readable message
    """

    def __init__(self, matches: List[DLPMatch], message: Optional[str] = None):
        self.matches = matches
        self.message = message or self._generate_message(matches)
        super().__init__(self.message)

    @staticmethod
    def _generate_message(matches: List[DLPMatch]) -> str:
        """Generate user-friendly error message."""
        categories = set(m.category for m in matches)
        return (f"Request blocked by DLP policy. "
                f"Detected {len(matches)} violation(s) in categories: {', '.join(categories)}. "
                f"Please remove sensitive data before retrying.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "error": "dlp_blocked",
            "message": self.message,
            "categories": list(set(m.category for m in self.matches)),
            "violation_count": len(self.matches),
        }
