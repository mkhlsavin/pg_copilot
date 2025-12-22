"""Enrichment Agent Package.

Provides:
- EnrichmentAgent: Main agent for mapping questions to CPG enrichment tags
- Keyword matching functions
- Tag filter generation
- Coverage calculation
- Prompt formatting utilities
"""
from .agent import EnrichmentAgent
from .keyword_matchers import enhance_with_keywords
from .fallback import general_domain_fallback
from .tag_filters import generate_tag_filters
from .coverage import calculate_coverage, COVERAGE_KEYS
from .prompt_formatter import format_for_prompt, get_example_queries

__all__ = [
    'EnrichmentAgent',
    'enhance_with_keywords',
    'general_domain_fallback',
    'generate_tag_filters',
    'calculate_coverage',
    'COVERAGE_KEYS',
    'format_for_prompt',
    'get_example_queries',
]
