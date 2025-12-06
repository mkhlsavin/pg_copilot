"""
Verdict Aggregation for Patch Review

Combines multiple verdicts into final review:
- Weighted score aggregation
- Policy-based recommendation determination
- Finding prioritization
"""

from .verdict_aggregator import VerdictAggregator, AggregationConfig

__all__ = [
    'VerdictAggregator',
    'AggregationConfig',
]
