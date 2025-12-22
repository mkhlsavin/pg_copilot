"""
Tests for DLP Content Scanner.

Tests for pattern matching, content scanning, masking, and blocking actions.
Updated to use actual config classes for proper compatibility.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict

from src.security.config import (
    DLPConfig,
    DLPCategoryConfig,
    DLPPatternConfig,
    DLPKeywordListConfig,
    DLPPreRequestConfig,
    DLPPostResponseConfig,
    DLPAction,
)


class TestPatternRegistry:
    """Tests for PatternRegistry class."""

    def test_load_patterns_from_config(self):
        """Test loading patterns from configuration."""
        from src.security.dlp.patterns import PatternRegistry

        config = DLPConfig(
            enabled=True,
            categories={
                "credentials": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.BLOCK,
                    patterns=[
                        DLPPatternConfig(
                            name="api_key",
                            regex=r"sk-[a-zA-Z0-9]{20,}",
                            mask_with="[API_KEY]",
                        ),
                    ],
                ),
            },
        )

        registry = PatternRegistry(config)

        assert registry.get_pattern_count() >= 1
        assert "credentials" in registry.get_categories()

    def test_match_patterns_finds_api_key(self):
        """Test pattern matching for API keys."""
        from src.security.dlp.patterns import PatternRegistry, MatchType

        config = DLPConfig(
            enabled=True,
            categories={
                "credentials": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.BLOCK,
                    patterns=[
                        DLPPatternConfig(
                            name="api_key",
                            regex=r"sk-[a-zA-Z0-9]{20,}",
                            mask_with="[API_KEY]",
                        ),
                    ],
                ),
            },
        )

        registry = PatternRegistry(config)

        content = "My API key is sk-abc123def456ghi789jkl01234567"
        matches = registry.match_patterns(content)

        assert len(matches) >= 1
        assert matches[0].pattern_name == "api_key"
        assert matches[0].match_type == MatchType.REGEX

    def test_match_keywords(self):
        """Test keyword matching."""
        from src.security.dlp.patterns import PatternRegistry, MatchType

        config = DLPConfig(
            enabled=True,
            keywords={
                "sensitive": DLPKeywordListConfig(
                    words=["password", "secret"],
                    case_sensitive=False,
                ),
            },
        )

        registry = PatternRegistry(config)

        content = "The password is stored in SECRET file"
        matches = registry.match_keywords(content)

        assert len(matches) == 2  # password and SECRET
        assert any(m.matched_text.lower() == "password" for m in matches)
        assert any(m.matched_text.lower() == "secret" for m in matches)

    def test_match_all_combines_patterns_and_keywords(self):
        """Test matching both patterns and keywords."""
        from src.security.dlp.patterns import PatternRegistry

        config = DLPConfig(
            enabled=True,
            categories={
                "credentials": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.MASK,
                    patterns=[
                        DLPPatternConfig(
                            name="api_key",
                            regex=r"sk-[a-zA-Z0-9]{20,}",
                        ),
                    ],
                ),
            },
            keywords={
                "sensitive": DLPKeywordListConfig(words=["password"]),
            },
        )

        registry = PatternRegistry(config)

        content = "password is sk-abc123def456ghi789jkl01234567"
        matches = registry.match_all(content)

        # Should find both password keyword and API key pattern
        assert len(matches) >= 2

    def test_add_pattern_dynamically(self):
        """Test adding pattern at runtime."""
        from src.security.dlp.patterns import PatternRegistry

        config = DLPConfig(enabled=True)
        registry = PatternRegistry(config)

        initial_count = registry.get_pattern_count()

        success = registry.add_pattern(
            category="custom",
            name="test_pattern",
            regex=r"TEST-\d{4}",
            action=DLPAction.WARN,
        )

        assert success is True
        assert registry.get_pattern_count() == initial_count + 1

    def test_add_invalid_pattern_fails(self):
        """Test that invalid regex pattern fails."""
        from src.security.dlp.patterns import PatternRegistry

        config = DLPConfig(enabled=True)
        registry = PatternRegistry(config)

        success = registry.add_pattern(
            category="custom",
            name="invalid",
            regex=r"[invalid(regex",  # Invalid regex
        )

        assert success is False


class TestContentScanner:
    """Tests for ContentScanner class."""

    def test_scanner_initialization(self):
        """Test scanner initializes with config."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(enabled=True)
        scanner = ContentScanner(config)

        assert scanner.is_enabled is True

    def test_scan_disabled_returns_empty(self):
        """Test scan returns empty when disabled."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(enabled=False)
        scanner = ContentScanner(config)

        matches = scanner.scan("sensitive content with password")

        assert matches == []

    def test_scan_request_blocks_on_block_action(self):
        """Test scan_request blocks content with BLOCK action."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(
            enabled=True,
            categories={
                "credentials": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.BLOCK,
                    patterns=[
                        DLPPatternConfig(
                            name="private_key",
                            regex=r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
                        ),
                    ],
                ),
            },
            pre_request=DLPPreRequestConfig(enabled=True, default_action=DLPAction.BLOCK),
        )

        scanner = ContentScanner(config)

        result = scanner.scan_request("Here is my -----BEGIN PRIVATE KEY-----")

        assert result.has_matches is True
        assert result.blocked is True
        assert result.action == DLPAction.BLOCK

    def test_scan_request_masks_content(self):
        """Test scan_request masks sensitive content."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(
            enabled=True,
            categories={
                "credentials": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.MASK,
                    patterns=[
                        DLPPatternConfig(
                            name="api_key",
                            regex=r"sk-[a-zA-Z0-9]{20,}",
                            mask_with="[API_KEY]",
                        ),
                    ],
                ),
            },
            pre_request=DLPPreRequestConfig(enabled=True, default_action=DLPAction.MASK),
        )

        scanner = ContentScanner(config)

        result = scanner.scan_request("Key: sk-abc123def456ghi789jkl01234567")

        assert result.has_matches is True
        assert result.blocked is False
        assert result.action == DLPAction.MASK
        assert "[API_KEY]" in result.modified_content

    def test_scan_response_always_masks_never_blocks(self):
        """Test scan_response always masks, never blocks."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(
            enabled=True,
            categories={
                "pii": DLPCategoryConfig(
                    enabled=True,
                    action=DLPAction.BLOCK,  # Even with block action
                    patterns=[
                        DLPPatternConfig(
                            name="email",
                            regex=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                            mask_with="[EMAIL]",
                        ),
                    ],
                ),
            },
            post_response=DLPPostResponseConfig(enabled=True),
        )

        scanner = ContentScanner(config)

        result = scanner.scan_response("Contact: user@example.com")

        assert result.has_matches is True
        assert result.blocked is False  # Never block responses
        assert "[EMAIL]" in result.modified_content

    def test_scan_request_disabled_returns_no_matches(self):
        """Test scan_request when pre_request is disabled."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(
            enabled=True,
            pre_request=DLPPreRequestConfig(enabled=False),
        )

        scanner = ContentScanner(config)

        result = scanner.scan_request("sensitive content")

        assert result.has_matches is False
        assert result.blocked is False

    def test_mask_content_preserves_non_matched_text(self):
        """Test that masking preserves non-matched content."""
        from src.security.dlp.scanner import ContentScanner
        from src.security.dlp.patterns import DLPMatch, MatchType

        config = DLPConfig(enabled=True)
        scanner = ContentScanner(config)

        content = "Hello world secret goodbye"
        matches = [
            DLPMatch(
                category="test",
                pattern_name="test",
                match_type=MatchType.KEYWORD,
                matched_text="secret",
                start=12,
                end=18,
                action=DLPAction.MASK,
                mask_with="[MASKED]",
            )
        ]

        result = scanner.mask(content, matches)

        assert result == "Hello world [MASKED] goodbye"


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_scan_result_to_dict(self):
        """Test ScanResult serialization."""
        from src.security.dlp.scanner import ScanResult
        from src.security.dlp.patterns import DLPMatch, MatchType

        match = DLPMatch(
            category="test",
            pattern_name="test_pattern",
            match_type=MatchType.REGEX,
            matched_text="secret123",
            start=0,
            end=9,
            action=DLPAction.MASK,
        )

        result = ScanResult(
            has_matches=True,
            matches=[match],
            action=DLPAction.MASK,
            modified_content="[MASKED]",
            blocked=False,
        )

        as_dict = result.to_dict()

        assert as_dict["has_matches"] is True
        assert as_dict["match_count"] == 1
        assert as_dict["blocked"] is False
        assert len(as_dict["matches"]) == 1


class TestDLPBlockedException:
    """Tests for DLPBlockedException."""

    def test_exception_message_generation(self):
        """Test exception generates user-friendly message."""
        from src.security.dlp.scanner import DLPBlockedException
        from src.security.dlp.patterns import DLPMatch, MatchType

        matches = [
            DLPMatch(
                category="credentials",
                pattern_name="api_key",
                match_type=MatchType.REGEX,
                matched_text="sk-test",
                start=0,
                end=7,
                action=DLPAction.BLOCK,
            ),
            DLPMatch(
                category="pii",
                pattern_name="email",
                match_type=MatchType.REGEX,
                matched_text="user@test.com",
                start=10,
                end=23,
                action=DLPAction.BLOCK,
            ),
        ]

        exc = DLPBlockedException(matches)

        assert "blocked by DLP" in exc.message
        assert "credentials" in exc.message
        assert "pii" in exc.message

    def test_exception_to_dict(self):
        """Test exception serialization for API response."""
        from src.security.dlp.scanner import DLPBlockedException
        from src.security.dlp.patterns import DLPMatch, MatchType

        matches = [
            DLPMatch(
                category="credentials",
                pattern_name="test",
                match_type=MatchType.REGEX,
                matched_text="secret",
                start=0,
                end=6,
                action=DLPAction.BLOCK,
            ),
        ]

        exc = DLPBlockedException(matches)
        as_dict = exc.to_dict()

        assert as_dict["error"] == "dlp_blocked"
        assert "credentials" in as_dict["categories"]
        assert as_dict["violation_count"] == 1


class TestDLPMatch:
    """Tests for DLPMatch dataclass."""

    def test_dlp_match_to_dict(self):
        """Test DLPMatch serialization."""
        from src.security.dlp.patterns import DLPMatch, MatchType

        match = DLPMatch(
            category="credentials",
            pattern_name="api_key",
            match_type=MatchType.REGEX,
            matched_text="sk-verylongsecretkey12345",
            start=10,
            end=35,
            action=DLPAction.MASK,
            mask_with="[API_KEY]",
            severity="high",
        )

        as_dict = match.to_dict()

        assert as_dict["category"] == "credentials"
        assert as_dict["pattern_name"] == "api_key"
        assert as_dict["match_type"] == "regex"
        assert as_dict["severity"] == "high"

    def test_dlp_match_truncates_long_text(self):
        """Test that long matched text is truncated in dict."""
        from src.security.dlp.patterns import DLPMatch, MatchType

        long_text = "a" * 100

        match = DLPMatch(
            category="test",
            pattern_name="test",
            match_type=MatchType.REGEX,
            matched_text=long_text,
            start=0,
            end=100,
            action=DLPAction.WARN,
        )

        as_dict = match.to_dict()

        # Should be truncated to 50 chars + "..."
        assert len(as_dict["matched_text"]) == 53
        assert as_dict["matched_text"].endswith("...")


class TestActionPriority:
    """Tests for action priority logic."""

    def test_block_is_highest_priority(self):
        """Test that BLOCK action has highest priority."""
        from src.security.dlp.scanner import ContentScanner
        from src.security.dlp.patterns import DLPMatch, MatchType

        config = DLPConfig(enabled=True)
        scanner = ContentScanner(config)

        matches = [
            DLPMatch(
                category="test1",
                pattern_name="p1",
                match_type=MatchType.REGEX,
                matched_text="t1",
                start=0,
                end=2,
                action=DLPAction.WARN,
            ),
            DLPMatch(
                category="test2",
                pattern_name="p2",
                match_type=MatchType.REGEX,
                matched_text="t2",
                start=3,
                end=5,
                action=DLPAction.BLOCK,
            ),
            DLPMatch(
                category="test3",
                pattern_name="p3",
                match_type=MatchType.REGEX,
                matched_text="t3",
                start=6,
                end=8,
                action=DLPAction.MASK,
            ),
        ]

        action = scanner.get_action(matches)

        assert action == DLPAction.BLOCK

    def test_empty_matches_returns_default(self):
        """Test that empty matches returns LOG_ONLY."""
        from src.security.dlp.scanner import ContentScanner

        config = DLPConfig(enabled=True)
        scanner = ContentScanner(config)

        action = scanner.get_action([])

        assert action == DLPAction.LOG_ONLY
