"""Test Enhanced Cache Implementation

This script tests the new enhanced cache features including:
1. Basic cache hit/miss tracking
2. TTL expiration
3. Cache invalidation
4. Metrics collection
5. Cache warming

Usage:
    conda activate llama.cpp
    python test_enhanced_cache.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.retrieval.retrieval_cache import RetrievalCache


def test_basic_operations():
    """Test basic cache get/set operations."""
    print("\n" + "="*80)
    print("TEST 1: Basic Cache Operations")
    print("="*80)

    cache = RetrievalCache(max_size=5, ttl_seconds=None, name="test_cache")

    # Test set and get
    key1 = ("question1", "domain", "intent", (), 3, 5)
    value1 = {"result": "data1"}

    print("\n✓ Setting key1...")
    cache.set(key1, value1)

    print("✓ Getting key1...")
    result = cache.get(key1)
    assert result == value1, "Value mismatch!"

    print("✓ Basic operations: PASS")


def test_hit_miss_tracking():
    """Test cache hit/miss metrics."""
    print("\n" + "="*80)
    print("TEST 2: Hit/Miss Tracking")
    print("="*80)

    cache = RetrievalCache(max_size=5, name="test_cache")

    keys = [
        ("q1", "d1", "i1", (), 3, 5),
        ("q2", "d2", "i2", (), 3, 5),
        ("q3", "d3", "i3", (), 3, 5),
    ]

    # Initial sets (all misses)
    for key in keys:
        cache.set(key, {"data": str(key)})
        cache.get(key)  # Trigger miss first

    # Test hits
    for key in keys:
        result = cache.get(key)
        assert result is not None, f"Cache miss for {key}"

    metrics = cache.get_metrics()
    print(f"\n📊 Metrics after {len(keys)} sets and gets:")
    print(f"  Hits:      {metrics['hits']}")
    print(f"  Misses:    {metrics['misses']}")
    print(f"  Hit Rate:  {metrics['hit_rate']:.2%}")

    assert metrics['hits'] >= len(keys), "Not enough hits recorded"
    print("\n✓ Hit/Miss tracking: PASS")


def test_lru_eviction():
    """Test LRU eviction policy."""
    print("\n" + "="*80)
    print("TEST 3: LRU Eviction")
    print("="*80)

    cache = RetrievalCache(max_size=3, name="test_cache")

    # Fill cache to capacity
    keys = [
        ("q1", "d1", "i1", (), 3, 5),
        ("q2", "d2", "i2", (), 3, 5),
        ("q3", "d3", "i3", (), 3, 5),
    ]

    for i, key in enumerate(keys):
        cache.set(key, {"data": f"value{i}"})

    print(f"\n📦 Cache filled: {len(cache)}/3")

    # Add one more (should evict LRU)
    new_key = ("q4", "d4", "i4", (), 3, 5)
    cache.set(new_key, {"data": "value4"})

    print(f"📦 Added new entry: {len(cache)}/3")

    # First key should be evicted
    result = cache.get(keys[0])
    assert result is None, "LRU entry should be evicted!"

    # New key should be present
    result = cache.get(new_key)
    assert result is not None, "New entry should be cached!"

    print("\n✓ LRU eviction: PASS")


def test_ttl_expiration():
    """Test TTL-based expiration."""
    print("\n" + "="*80)
    print("TEST 4: TTL Expiration")
    print("="*80)

    # Cache with 2-second TTL
    cache = RetrievalCache(max_size=5, ttl_seconds=2, name="test_cache")

    key = ("question", "domain", "intent", (), 3, 5)
    value = {"data": "test"}

    print("\n✓ Setting entry with 2s TTL...")
    cache.set(key, value)

    # Should be available immediately
    result = cache.get(key)
    assert result is not None, "Entry should be available immediately"
    print("✓ Entry available immediately")

    # Wait for expiration
    print("⏳ Waiting 3 seconds for TTL expiration...")
    time.sleep(3)

    # Should be expired now
    result = cache.get(key)
    assert result is None, "Entry should be expired!"
    print("✓ Entry expired after TTL")

    metrics = cache.get_metrics()
    print(f"\n📊 Evictions by TTL: {metrics['evictions_by_ttl']}")
    assert metrics['evictions_by_ttl'] > 0, "TTL eviction not recorded!"

    print("\n✓ TTL expiration: PASS")


def test_invalidation():
    """Test cache invalidation."""
    print("\n" + "="*80)
    print("TEST 5: Cache Invalidation")
    print("="*80)

    cache = RetrievalCache(max_size=10, name="test_cache")

    # Add entries with different patterns
    keys = [
        ("How does MVCC work?", "memory", "explain", (), 3, 5),
        ("What is vacuum?", "vacuum", "explain", (), 3, 5),
        ("How does WAL work?", "wal", "explain", (), 3, 5),
    ]

    for key in keys:
        cache.set(key, {"data": str(key)})

    print(f"\n📦 Cache size: {len(cache)}")

    # Invalidate by pattern (should match "vacuum")
    count = cache.invalidate_pattern("vacuum", key_index=0)
    print(f"✓ Invalidated {count} entries matching 'vacuum'")

    # Verify vacuum entry is gone
    result = cache.get(keys[1])
    assert result is None, "Invalidated entry should not be in cache!"

    # Other entries should still be present
    result = cache.get(keys[0])
    assert result is not None, "Other entries should remain!"

    print(f"📦 Cache size after invalidation: {len(cache)}")

    # Clear all
    count = cache.invalidate_all()
    print(f"✓ Cleared {count} remaining entries")
    assert len(cache) == 0, "Cache should be empty!"

    print("\n✓ Invalidation: PASS")


def test_metrics_collection():
    """Test comprehensive metrics collection."""
    print("\n" + "="*80)
    print("TEST 6: Metrics Collection")
    print("="*80)

    cache = RetrievalCache(max_size=5, name="test_cache")

    # Add 5 entries (fills cache)
    for i in range(5):
        key = (f"q{i}", f"d{i}", f"i{i}", (), 3, 5)
        cache.set(key, {"data": f"value{i}"})

    # Generate some hits
    for i in range(5):
        key = (f"q{i}", f"d{i}", f"i{i}", (), 3, 5)
        cache.get(key)  # Should hit

    # Generate some misses
    for i in range(10):
        key = (f"new_q{i}", f"new_d{i}", f"new_i{i}", (), 3, 5)
        cache.get(key)  # Should miss since key doesn't exist

    metrics = cache.get_metrics()

    print("\n📊 Comprehensive Metrics:")
    print(f"  Hits:        {metrics['hits']}")
    print(f"  Misses:      {metrics['misses']}")
    print(f"  Hit Rate:    {metrics['hit_rate']:.2%}")
    print(f"  Size:        {metrics['current_size']} / {metrics['max_size']}")
    print(f"  Utilization: {metrics['utilization']:.1%}")
    print(f"  Memory:      {metrics['memory_bytes'] / 1024:.2f} KB")
    print(f"  Avg Get:     {metrics['avg_get_time_ms']:.2f} ms")
    print(f"  Avg Set:     {metrics['avg_set_time_ms']:.2f} ms")
    print(f"  Evictions:   {metrics['evictions_by_size']}")

    assert metrics['hits'] > 0, "Should have cache hits!"
    assert metrics['misses'] > 0, "Should have cache misses!"
    assert 0 <= metrics['hit_rate'] <= 1, "Invalid hit rate!"
    assert metrics['utilization'] > 0, "Cache should have entries!"

    print("\n✓ Metrics collection: PASS")


def test_thread_safety():
    """Test thread-safe operations (basic)."""
    print("\n" + "="*80)
    print("TEST 7: Thread Safety (Basic)")
    print("="*80)

    import threading

    cache = RetrievalCache(max_size=100, name="test_cache")
    errors = []

    def worker(thread_id):
        try:
            for i in range(10):
                key = (f"t{thread_id}_q{i}", "domain", "intent", (), 3, 5)
                cache.set(key, {"thread": thread_id, "i": i})
                result = cache.get(key)
                assert result is not None, f"Thread {thread_id} failed to retrieve key!"
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

    print("\n🔄 Starting 5 threads with 10 operations each...")
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"✓ All threads completed")

    if errors:
        print(f"\n✗ Errors occurred: {errors}")
        raise errors[0]

    metrics = cache.get_metrics()
    print(f"\n📊 Final cache size: {len(cache)}")
    print(f"📊 Total operations: Hits={metrics['hits']}, Misses={metrics['misses']}")

    print("\n✓ Thread safety: PASS")


def run_all_tests():
    """Run all cache tests."""
    print("\n" + "="*80)
    print("ENHANCED CACHE TEST SUITE")
    print("="*80)

    tests = [
        test_basic_operations,
        test_hit_miss_tracking,
        test_lru_eviction,
        test_ttl_expiration,
        test_invalidation,
        test_metrics_collection,
        test_thread_safety,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
