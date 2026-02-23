"""
Unit tests for CacheManager (JSONL append-only)

Run: python3 -m pytest tests/test_cache_manager.py
Or: python3 tests/test_cache_manager.py
"""

import sys
import json
import tempfile
import threading
import shutil

sys.path.insert(0, '.')

from nlp.cache_manager import CacheManager


def _make_cache(tmp_dir=None):
    """Create a CacheManager using a temp directory."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
    return CacheManager(cache_dir=tmp_dir), tmp_dir


def test_get_set_basic():
    """Test basic get/set operations."""
    cache, tmp = _make_cache()
    try:
        # Miss
        assert cache.get("foo") is None

        # Set and hit
        cache.set("foo", {"bar": 42})
        result = cache.get("foo")
        assert result == {"bar": 42}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_namespace_isolation():
    """Test that different namespaces are isolated."""
    cache, tmp = _make_cache()
    try:
        cache.set("key", "value_a", namespace="ns_a")
        cache.set("key", "value_b", namespace="ns_b")

        assert cache.get("key", namespace="ns_a") == "value_a"
        assert cache.get("key", namespace="ns_b") == "value_b"
        assert cache.get("key", namespace="ns_c") is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cache_stats():
    """Test cache statistics tracking."""
    cache, tmp = _make_cache()
    try:
        cache.set("a", 1)
        cache.get("a")       # hit
        cache.get("a")       # hit
        cache.get("missing") # miss

        stats = cache.get_cache_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.memory_size >= 1
        assert 0.0 <= stats.hit_rate <= 1.0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_disk_persistence():
    """Test that data persists across CacheManager instances."""
    tmp = tempfile.mkdtemp()
    try:
        # Write with first instance
        cache1 = CacheManager(cache_dir=tmp)
        cache1.set("persist_key", "persist_value")

        # Read with new instance (simulates restart)
        cache2 = CacheManager(cache_dir=tmp)
        result = cache2.get("persist_key")
        assert result == "persist_value"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_jsonl_format():
    """Test that disk cache uses JSONL format (one JSON per line)."""
    cache, tmp = _make_cache()
    try:
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")

        cache_file = cache.disk_cache_path
        assert cache_file.exists()

        with open(cache_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert "k" in entry
            assert "v" in entry
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compaction():
    """Test that compact() deduplicates keys."""
    cache, tmp = _make_cache()
    try:
        # Write same key multiple times (simulates updates)
        cache.set("dup", "old_value")
        cache.set("dup", "new_value")
        cache.set("dup", "final_value")
        cache.set("unique", "stays")

        # Before compaction: 4 lines
        with open(cache.disk_cache_path, 'r') as f:
            lines_before = sum(1 for line in f if line.strip())
        assert lines_before == 4

        # Compact
        cache.compact()

        # After compaction: 2 lines (dup + unique)
        with open(cache.disk_cache_path, 'r') as f:
            lines_after = sum(1 for line in f if line.strip())
        assert lines_after == 2

        # Values should be latest
        cache2 = CacheManager(cache_dir=tmp)
        assert cache2.get("dup") == "final_value"
        assert cache2.get("unique") == "stays"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_thread_safety():
    """Test concurrent access from 10 threads."""
    cache, tmp = _make_cache()
    errors = []

    def worker(thread_id):
        try:
            for i in range(20):
                key = f"thread_{thread_id}_item_{i}"
                cache.set(key, thread_id * 100 + i)
                result = cache.get(key)
                assert result == thread_id * 100 + i, \
                    f"Thread {thread_id}: expected {thread_id * 100 + i}, got {result}"
        except Exception as e:
            errors.append(e)

    try:
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert cache.get_cache_stats().memory_size == 200  # 10 threads * 20 items
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clear_cache():
    """Test clearing memory and disk caches."""
    cache, tmp = _make_cache()
    try:
        cache.set("a", 1)
        cache.set("b", 2)

        # Clear memory only
        cache.clear_cache(memory=True, disk=False)
        assert cache.get("a") is None
        assert cache.disk_cache_path.exists()

        # Reload from disk
        cache2 = CacheManager(cache_dir=tmp)
        assert cache2.get("a") == 1  # Still on disk

        # Clear both
        cache2.clear_cache(memory=True, disk=True)
        assert cache2.get("a") is None
        assert not cache2.disk_cache_path.exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print("Running CacheManager tests...\n")

    tests = [
        ("Test 1: Basic get/set", test_get_set_basic),
        ("Test 2: Namespace isolation", test_namespace_isolation),
        ("Test 3: Cache stats", test_cache_stats),
        ("Test 4: Disk persistence", test_disk_persistence),
        ("Test 5: JSONL format", test_jsonl_format),
        ("Test 6: Compaction", test_compaction),
        ("Test 7: Thread safety (10 threads)", test_thread_safety),
        ("Test 8: Clear cache", test_clear_cache),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print("=" * 60)
        print(name)
        print("=" * 60)
        try:
            test_func()
            print("PASSED\n")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
