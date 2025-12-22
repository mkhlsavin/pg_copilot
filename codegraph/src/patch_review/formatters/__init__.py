"""
Output Formatters for Patch Review

Formats review verdicts for different outputs:
- JSONFormatter: Machine-readable JSON for CI/CD
- MarkdownFormatter: Human-readable reports
- PRCommentFormatter: Inline comments for PRs
"""

from .json_formatter import JSONFormatter, ReviewJSONEncoder
from .markdown_formatter import MarkdownFormatter
from .pr_comment_formatter import PRCommentFormatter, InlineComment, ReviewComment

__all__ = [
    'JSONFormatter',
    'ReviewJSONEncoder',
    'MarkdownFormatter',
    'PRCommentFormatter',
    'InlineComment',
    'ReviewComment',
]
