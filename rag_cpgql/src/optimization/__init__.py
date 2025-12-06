"""
Optimization module for RAG-CPGQL system.

Components:
- QueryPlanCache: LRU cache for query plans with TTL
- SemanticFingerprint: Semantic similarity-based cache key generation
"""

from src.optimization.query_cache import (
    QueryPlanCache,
    generate_cache_key,
    normalize_text,
    compute_semantic_fingerprint,
)

__all__ = [
    'QueryPlanCache',
    'generate_cache_key',
    'normalize_text',
    'compute_semantic_fingerprint',
]
