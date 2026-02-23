#!/usr/bin/env python3
"""
cache_manager.py -- Global Unified Cache Manager for NLP/ML Modules

Provides multi-level caching (memory + disk) with thread-safe operations.
Designed for use across all v5.0 NLP modules (intent detection, priority ranking, etc.)

Features:
- Memory cache for session-level fast access
- Disk cache using JSONL (append-only, O(1) writes)
- Thread-safe operations with locking
- Cache statistics and management
- Embedding cache for transformer models
- Auto-migration from old JSON format
"""

import json
import hashlib
import logging
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics"""
    memory_size: int
    disk_size: int
    hits: int
    misses: int
    hit_rate: float


class CacheManager:
    """
    Unified Multi-Level Caching for NLP/ML Modules

    Implements a two-tier caching strategy:
    1. Memory cache (in-memory dict) -- fast, session-only
    2. Disk cache (JSONL file) -- persistent, append-only O(1) writes

    Thread-safe for use in parallel processing (ThreadPoolExecutor).
    """

    def __init__(self, cache_dir: str = "./nlp"):
        """
        Initialize Cache Manager

        Args:
            cache_dir: Directory for disk cache file
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Memory cache (session-level)
        self.memory_cache: Dict[str, Any] = {}

        # Disk cache paths (JSONL is primary, JSON is legacy)
        self.disk_cache_path = self.cache_dir / "cache.jsonl"
        self._legacy_cache_path = self.cache_dir / "cache.json"

        # Thread-safe lock
        self._lock = threading.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0

        # Auto-migrate from old JSON format if needed
        self._migrate_from_json()

        # Load existing disk cache on init
        self._load_disk_cache_to_memory()

        logger.info("CacheManager initialized: %d entries loaded from disk",
                     len(self.memory_cache))

    # -------------------------
    # Embedding Cache
    # -------------------------

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for text

        Args:
            text: Input text (hashed internally)

        Returns:
            Cached embedding as numpy array, or None if not found
        """
        text_hash = self._hash_text(text)

        with self._lock:
            if text_hash in self.memory_cache:
                embedding_data = self.memory_cache[text_hash]
                if isinstance(embedding_data, dict) and "embedding" in embedding_data:
                    self._hits += 1
                    return np.array(embedding_data["embedding"])

        self._misses += 1
        return None

    def set_embedding(self, text: str, embedding: np.ndarray):
        """
        Cache embedding for text

        Args:
            text: Input text
            embedding: Embedding vector as numpy array
        """
        text_hash = self._hash_text(text)

        with self._lock:
            value = {
                "embedding": embedding.tolist(),
                "text_preview": text[:50]
            }
            self.memory_cache[text_hash] = value
            self._append_to_disk_cache(text_hash, value)

    # -------------------------
    # Generic Cache Operations
    # -------------------------

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get cached value by key

        Args:
            key: Cache key
            namespace: Cache namespace (e.g., "intent", "priority")

        Returns:
            Cached value, or None if not found
        """
        full_key = f"{namespace}:{key}"

        with self._lock:
            if full_key in self.memory_cache:
                self._hits += 1
                return self.memory_cache[full_key]

        self._misses += 1
        return None

    def set(self, key: str, value: Any, namespace: str = "default"):
        """
        Set cached value by key

        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
        """
        full_key = f"{namespace}:{key}"

        with self._lock:
            self.memory_cache[full_key] = value
            self._append_to_disk_cache(full_key, value)

    # -------------------------
    # Cache Management
    # -------------------------

    def get_cache_stats(self) -> CacheStats:
        """
        Get cache statistics

        Returns:
            CacheStats with memory size, disk size, hit rate
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            disk_size = 0
            if self.disk_cache_path.exists():
                try:
                    with open(self.disk_cache_path, 'r', encoding='utf-8') as f:
                        disk_size = sum(1 for _ in f)
                except Exception as e:
                    logger.warning("Failed to count disk cache lines: %s", e)

            return CacheStats(
                memory_size=len(self.memory_cache),
                disk_size=disk_size,
                hits=self._hits,
                misses=self._misses,
                hit_rate=hit_rate
            )

    def clear_cache(self, memory: bool = True, disk: bool = False):
        """
        Clear caches

        Args:
            memory: Clear memory cache
            disk: Clear disk cache (permanent)
        """
        with self._lock:
            if memory:
                self.memory_cache.clear()
                self._hits = 0
                self._misses = 0
                logger.info("Memory cache cleared")

            if disk:
                if self.disk_cache_path.exists():
                    self.disk_cache_path.unlink()
                    logger.info("Disk cache cleared")

    def compact(self):
        """
        Compact JSONL file by removing duplicate keys (keeping latest).

        Reads all entries, deduplicates by key, rewrites file.
        Should be called periodically to prevent file growth.
        """
        if not self.disk_cache_path.exists():
            return

        with self._lock:
            entries = {}
            try:
                with open(self.disk_cache_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            entries[entry["k"]] = entry["v"]
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning("Skipping corrupted cache line: %s", e)

                # Rewrite compacted file
                with open(self.disk_cache_path, 'w', encoding='utf-8') as f:
                    for key, value in entries.items():
                        f.write(json.dumps({"k": key, "v": value}, ensure_ascii=False) + '\n')

                logger.info("Cache compacted: %d unique entries", len(entries))
            except Exception as e:
                logger.warning("Cache compaction failed: %s", e)

    # -------------------------
    # Internal Helpers
    # -------------------------

    def _hash_text(self, text: str) -> str:
        """Hash text for cache key"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _migrate_from_json(self):
        """Auto-migrate from old JSON format to JSONL if needed."""
        if not self._legacy_cache_path.exists():
            return
        if self.disk_cache_path.exists():
            return  # Already migrated

        try:
            with open(self._legacy_cache_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)

            if not old_data:
                return

            with open(self.disk_cache_path, 'w', encoding='utf-8') as f:
                for key, value in old_data.items():
                    f.write(json.dumps({"k": key, "v": value}, ensure_ascii=False) + '\n')

            logger.info("Migrated %d entries from JSON to JSONL format", len(old_data))
        except Exception as e:
            logger.warning("JSON to JSONL migration failed: %s", e)

    def _load_disk_cache_to_memory(self):
        """Load disk cache (JSONL) into memory on startup."""
        if not self.disk_cache_path.exists():
            return

        try:
            with open(self.disk_cache_path, 'r', encoding='utf-8') as f:
                with self._lock:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            self.memory_cache[entry["k"]] = entry["v"]
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning("Skipping corrupted cache line: %s", e)
        except Exception as e:
            logger.warning("Failed to load disk cache: %s", e)

    def _append_to_disk_cache(self, key: str, value: Any):
        """
        Append entry to disk cache (O(1) operation).

        Writes a single JSONL line instead of rewriting entire file.
        """
        try:
            with open(self.disk_cache_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"k": key, "v": value}, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning("Disk cache write failed for key=%s: %s", key, e)


# -------------------------
# Global Singleton Instance
# -------------------------

_global_cache: Optional[CacheManager] = None
_global_cache_lock = threading.Lock()


def get_global_cache() -> CacheManager:
    """
    Get global cache manager instance (singleton)

    Returns:
        Shared CacheManager instance
    """
    global _global_cache

    with _global_cache_lock:
        if _global_cache is None:
            _global_cache = CacheManager()

        return _global_cache


# -------------------------
# Convenience Functions
# -------------------------

def cache_embedding(text: str, embedding: np.ndarray):
    """Cache embedding using global cache manager"""
    cache = get_global_cache()
    cache.set_embedding(text, embedding)


def get_cached_embedding(text: str) -> Optional[np.ndarray]:
    """Get cached embedding using global cache manager"""
    cache = get_global_cache()
    return cache.get_embedding(text)


def get_cache_stats() -> CacheStats:
    """Get global cache statistics"""
    cache = get_global_cache()
    return cache.get_cache_stats()


def clear_global_cache(memory: bool = True, disk: bool = False):
    """Clear global cache"""
    cache = get_global_cache()
    cache.clear_cache(memory=memory, disk=disk)
