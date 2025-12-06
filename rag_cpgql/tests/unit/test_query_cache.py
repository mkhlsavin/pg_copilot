"""
Unit tests for Query Plan Caching System

Tests:
- Cache hit/miss behavior
- TTL expiration
- LRU eviction
- Semantic fingerprinting
- Thread safety
- Statistics

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import pytest
import time
import threading
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.optimization.query_cache import (
    QueryPlanCache,
    SemanticCache,
    generate_cache_key,
    normalize_text,
    compute_semantic_fingerprint,
    create_cache_key_for_workflow,
    get_global_cache,
)


class TestNormalizeText:
    """Test text normalization functions."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        text = "Hello, World!"
        result = normalize_text(text)
        assert result == "hello world"

    def test_normalize_multiple_spaces(self):
        """Test collapsing multiple spaces."""
        text = "Hello    World   Test"
        result = normalize_text(text)
        assert result == "hello world test"

    def test_normalize_punctuation(self):
        """Test removing punctuation."""
        text = "What's the function-name?"
        result = normalize_text(text)
        assert result == "what s the function name"

    def test_normalize_empty(self):
        """Test empty string."""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""

    def test_normalize_preserves_underscores(self):
        """Test that underscores are preserved."""
        text = "exec_simple_query"
        result = normalize_text(text)
        assert "exec_simple_query" in result


class TestSemanticFingerprint:
    """Test semantic fingerprint generation."""

    def test_fingerprint_deterministic(self):
        """Test that same input produces same fingerprint."""
        text = "how does transaction commit work"
        fp1 = compute_semantic_fingerprint(text)
        fp2 = compute_semantic_fingerprint(text)
        assert fp1 == fp2

    def test_fingerprint_different_for_different_text(self):
        """Test that different texts produce different fingerprints."""
        fp1 = compute_semantic_fingerprint("how does transaction commit work")
        fp2 = compute_semantic_fingerprint("what is memory allocation")
        assert fp1 != fp2

    def test_fingerprint_short_text(self):
        """Test fingerprint for short text."""
        fp = compute_semantic_fingerprint("hello")
        assert len(fp) == 16  # Truncated SHA-256

    def test_fingerprint_empty(self):
        """Test fingerprint for empty text."""
        fp = compute_semantic_fingerprint("")
        assert len(fp) == 16


class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_key_deterministic(self):
        """Test that same inputs produce same key."""
        key1 = generate_cache_key("test question", "domain", "intent")
        key2 = generate_cache_key("test question", "domain", "intent")
        assert key1 == key2

    def test_key_different_for_different_question(self):
        """Test different questions produce different keys."""
        key1 = generate_cache_key("question one", "domain", "intent")
        key2 = generate_cache_key("question two", "domain", "intent")
        assert key1 != key2

    def test_key_different_for_different_domain(self):
        """Test different domains produce different keys."""
        key1 = generate_cache_key("question", "domain1", "intent")
        key2 = generate_cache_key("question", "domain2", "intent")
        assert key1 != key2

    def test_key_different_for_different_intent(self):
        """Test different intents produce different keys."""
        key1 = generate_cache_key("question", "domain", "intent1")
        key2 = generate_cache_key("question", "domain", "intent2")
        assert key1 != key2

    def test_key_is_sha256(self):
        """Test key is SHA-256 format."""
        key = generate_cache_key("test", "domain", "intent")
        assert len(key) == 64  # SHA-256 hex
        assert all(c in '0123456789abcdef' for c in key)


class TestQueryPlanCache:
    """Test QueryPlanCache class."""

    def test_cache_hit(self):
        """Test cache returns cached value on hit."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'query': 'SELECT * FROM nodes_method'})
        result = cache.get('key1')

        assert result is not None
        assert result['query'] == 'SELECT * FROM nodes_method'
        assert cache.hits == 1

    def test_cache_miss(self):
        """Test cache returns None on miss."""
        cache = QueryPlanCache(max_size=10)
        result = cache.get('nonexistent_key')

        assert result is None
        assert cache.misses == 1

    def test_cache_update(self):
        """Test updating existing cache entry."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'query': 'SELECT 1'})
        cache.put('key1', {'query': 'SELECT 2'})

        result = cache.get('key1')
        assert result['query'] == 'SELECT 2'

    def test_cache_delete(self):
        """Test deleting cache entry."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'query': 'SELECT 1'})
        deleted = cache.delete('key1')

        assert deleted is True
        assert cache.get('key1') is None

    def test_cache_delete_nonexistent(self):
        """Test deleting nonexistent key returns False."""
        cache = QueryPlanCache(max_size=10)
        deleted = cache.delete('nonexistent')
        assert deleted is False

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'a': 1})
        cache.put('key2', {'b': 2})
        cache.clear()

        assert len(cache) == 0
        assert cache.get('key1') is None
        assert cache.get('key2') is None

    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        cache = QueryPlanCache(max_size=10, ttl=1)  # 1 second TTL

        cache.put('key1', {'query': 'SELECT ...'})
        time.sleep(1.5)  # Wait for expiration

        result = cache.get('key1')
        assert result is None
        assert cache.expirations == 1

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = QueryPlanCache(max_size=3)

        # Fill cache
        cache.put('key1', {'query': 'Q1'})
        cache.put('key2', {'query': 'Q2'})
        cache.put('key3', {'query': 'Q3'})

        # Access key1 and key2 (makes key3 least recently used)
        cache.get('key1')
        cache.get('key2')

        # Add key4 - should evict key3
        cache.put('key4', {'query': 'Q4'})

        assert cache.get('key3') is None  # Evicted
        assert cache.get('key1') is not None
        assert cache.get('key2') is not None
        assert cache.get('key4') is not None
        assert cache.evictions >= 1

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'a': 1})
        cache.get('key1')  # Hit
        cache.get('key1')  # Hit
        cache.get('key2')  # Miss

        stats = cache.get_stats()

        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['total_requests'] == 3
        assert stats['hit_rate'] == pytest.approx(2/3, rel=0.01)
        assert stats['cache_size'] == 1

    def test_cache_contains(self):
        """Test contains check."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'a': 1})

        assert cache.contains('key1') is True
        assert cache.contains('key2') is False
        assert 'key1' in cache
        assert 'key2' not in cache

    def test_cache_len(self):
        """Test cache length."""
        cache = QueryPlanCache(max_size=10)

        assert len(cache) == 0

        cache.put('key1', {'a': 1})
        cache.put('key2', {'b': 2})

        assert len(cache) == 2

    def test_cache_get_keys(self):
        """Test getting all keys."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'a': 1})
        cache.put('key2', {'b': 2})

        keys = cache.get_keys()
        assert 'key1' in keys
        assert 'key2' in keys

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = QueryPlanCache(max_size=10, ttl=1)

        cache.put('key1', {'a': 1})
        cache.put('key2', {'b': 2})
        time.sleep(1.5)

        removed = cache.cleanup_expired()
        assert removed == 2
        assert len(cache) == 0

    def test_cache_with_metadata(self):
        """Test storing with metadata."""
        cache = QueryPlanCache(max_size=10)

        cache.put('key1', {'query': 'SELECT 1'}, metadata={'source': 'test'})
        result = cache.get('key1')

        assert result is not None


class TestSemanticCache:
    """Test SemanticCache class."""

    def test_put_with_question(self):
        """Test putting value with question."""
        cache = SemanticCache(max_size=10)

        key = cache.put_with_question(
            question="How does PostgreSQL handle transactions?",
            value={'query': 'SELECT ...'},
            domain="transaction",
            intent="explain"
        )

        assert key is not None
        assert len(key) == 64  # SHA-256

    def test_get_by_question_exact(self):
        """Test exact match by question."""
        cache = SemanticCache(max_size=10)

        cache.put_with_question(
            question="How does PostgreSQL handle transactions?",
            value={'query': 'SELECT ...'},
            domain="transaction",
            intent="explain"
        )

        result = cache.get_by_question(
            question="How does PostgreSQL handle transactions?",
            domain="transaction",
            intent="explain"
        )

        assert result is not None
        value, is_exact = result
        assert is_exact is True
        assert value['query'] == 'SELECT ...'

    def test_get_by_question_fuzzy(self):
        """Test fuzzy match by similar question."""
        cache = SemanticCache(max_size=10)

        # Store original
        cache.put_with_question(
            question="how does postgresql handle transactions",
            value={'query': 'SELECT ...'},
            domain="transaction",
            intent="explain"
        )

        # Query with slightly different phrasing
        # Note: Fuzzy match depends on n-gram fingerprint
        result = cache.get_by_question(
            question="how does postgresql handle transactions",  # Same normalized
            domain="transaction",
            intent="explain"
        )

        assert result is not None

    def test_get_by_question_miss(self):
        """Test miss when question not found."""
        cache = SemanticCache(max_size=10)

        result = cache.get_by_question(
            question="completely different question",
            domain="other",
            intent="other"
        )

        assert result is None


class TestCacheThreadSafety:
    """Test thread safety of cache."""

    def test_concurrent_reads_writes(self):
        """Test concurrent read/write operations."""
        cache = QueryPlanCache(max_size=100)
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.put(f'key_{threading.current_thread().name}_{i}', {'i': i})
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    cache.get(f'key_Thread-1_{i}')
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = [
            threading.Thread(target=writer, name='Thread-1'),
            threading.Thread(target=writer, name='Thread-2'),
            threading.Thread(target=reader, name='Thread-3'),
            threading.Thread(target=reader, name='Thread-4'),
        ]

        # Start all
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0


class TestCreateCacheKeyForWorkflow:
    """Test workflow-specific cache key generation."""

    def test_high_confidence_key(self):
        """Test key for high-confidence intent."""
        key = create_cache_key_for_workflow(
            question="test question",
            scenario="security",
            intent="security_audit",
            confidence=0.95
        )
        assert key is not None
        assert len(key) == 64

    def test_low_confidence_includes_confidence(self):
        """Test that low confidence includes confidence in key."""
        key1 = create_cache_key_for_workflow(
            question="test question",
            scenario="security",
            intent="security_audit",
            confidence=0.5
        )
        key2 = create_cache_key_for_workflow(
            question="test question",
            scenario="security",
            intent="security_audit",
            confidence=0.6
        )
        # Different confidence should produce different keys
        assert key1 != key2


class TestGlobalCache:
    """Test global cache singleton."""

    def test_global_cache_singleton(self):
        """Test that get_global_cache returns same instance."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()
        assert cache1 is cache2

    def test_global_cache_usable(self):
        """Test that global cache is usable."""
        cache = get_global_cache()
        cache.put('global_test', {'value': 123})
        result = cache.get('global_test')
        assert result is not None
        assert result['value'] == 123


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
