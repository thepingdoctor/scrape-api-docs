"""
Advanced Caching Layer for Documentation Scraper
================================================

This module provides a multi-tier caching system to improve performance
and reduce redundant network requests.

Features:
- In-memory LRU cache for hot data
- Persistent disk cache with SQLite
- Content-based deduplication
- Automatic cache invalidation
- Cache statistics and monitoring
- Configurable TTL per cache tier

Usage:
    from cache_manager import CacheManager

    cache = CacheManager(max_memory_size=100, disk_cache_dir='.cache')

    # Check cache
    content = cache.get(url)
    if content is None:
        content = fetch_from_web(url)
        cache.set(url, content, ttl=3600)
"""

import hashlib
import json
import pickle
import sqlite3
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Any, Dict, Tuple
import threading
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe in-memory LRU (Least Recently Used) cache.

    Provides O(1) get and set operations with automatic eviction.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
        """
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Tuple[Any, float]]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Tuple of (value, timestamp) or None
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]

            self.misses += 1
            return None

    def set(self, key: str, value: Any, timestamp: float = None):
        """
        Set item in cache.

        Args:
            key: Cache key
            value: Value to cache
            timestamp: Optional timestamp (defaults to current time)
        """
        timestamp = timestamp or time.time()

        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache.move_to_end(key)
                self.cache[key] = (value, timestamp)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Evict oldest
                    self.cache.popitem(last=False)
                    self.evictions += 1

                self.cache[key] = (value, timestamp)

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self):
        """Clear all cached items."""
        with self.lock:
            self.cache.clear()

    def stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0

            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate
            }


class DiskCache:
    """
    Persistent disk-based cache using SQLite.

    Provides durable storage with automatic cleanup of expired entries.
    """

    def __init__(self, cache_dir: Path, db_name: str = 'cache.db'):
        """
        Initialize disk cache.

        Args:
            cache_dir: Directory for cache storage
            db_name: SQLite database filename
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / db_name
        self._init_db()

        self.hits = 0
        self.misses = 0
        self.lock = threading.Lock()

    def _init_db(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                content_hash TEXT,
                timestamp REAL,
                ttl INTEGER,
                size INTEGER,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON cache(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_hash
            ON cache(content_hash)
        ''')

        conn.commit()
        conn.close()

    def _get_content_hash(self, value: Any) -> str:
        """Generate content hash for deduplication."""
        content_bytes = pickle.dumps(value)
        return hashlib.sha256(content_bytes).hexdigest()

    def get(self, key: str) -> Optional[Tuple[Any, dict]]:
        """
        Get item from disk cache.

        Args:
            key: Cache key

        Returns:
            Tuple of (value, metadata) or None
        """
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT value, timestamp, ttl, content_hash,
                       access_count, size
                FROM cache
                WHERE key = ?
            ''', (key,))

            row = cursor.fetchone()

            if row:
                value_blob, timestamp, ttl, content_hash, access_count, size = row

                # Check if expired
                if ttl > 0 and time.time() - timestamp > ttl:
                    self.misses += 1
                    cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                    conn.commit()
                    conn.close()
                    return None

                # Update access stats
                cursor.execute('''
                    UPDATE cache
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE key = ?
                ''', (time.time(), key))

                conn.commit()
                conn.close()

                self.hits += 1
                value = pickle.loads(value_blob)

                metadata = {
                    'timestamp': timestamp,
                    'ttl': ttl,
                    'content_hash': content_hash,
                    'access_count': access_count + 1,
                    'size': size
                }

                return (value, metadata)

            conn.close()
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 0):
        """
        Set item in disk cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (0 = no expiration)
        """
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            value_blob = pickle.dumps(value)
            content_hash = self._get_content_hash(value)
            timestamp = time.time()
            size = len(value_blob)

            cursor.execute('''
                INSERT OR REPLACE INTO cache
                (key, value, content_hash, timestamp, ttl, size,
                 access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ''', (key, value_blob, content_hash, timestamp, ttl, size, timestamp))

            conn.commit()
            conn.close()

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
            deleted = cursor.rowcount > 0

            conn.commit()
            conn.close()

            return deleted

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            current_time = time.time()

            cursor.execute('''
                DELETE FROM cache
                WHERE ttl > 0 AND (? - timestamp) > ttl
            ''', (current_time,))

            removed = cursor.rowcount

            conn.commit()
            conn.close()

            return removed

    def find_duplicates(self) -> Dict[str, list]:
        """
        Find duplicate content by hash.

        Returns:
            Dictionary mapping content_hash to list of keys
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT content_hash, GROUP_CONCAT(key) as keys
            FROM cache
            GROUP BY content_hash
            HAVING COUNT(*) > 1
        ''')

        duplicates = {
            row[0]: row[1].split(',')
            for row in cursor.fetchall()
        }

        conn.close()
        return duplicates

    def stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as count,
                SUM(size) as total_size,
                AVG(access_count) as avg_accesses,
                SUM(CASE WHEN ttl > 0 AND (? - timestamp) > ttl
                    THEN 1 ELSE 0 END) as expired
            FROM cache
        ''', (time.time(),))

        row = cursor.fetchone()
        count, total_size, avg_accesses, expired = row

        conn.close()

        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            'count': count or 0,
            'total_size_bytes': total_size or 0,
            'avg_accesses': avg_accesses or 0,
            'expired': expired or 0,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }


class CacheManager:
    """
    Multi-tier cache manager with memory and disk layers.

    Provides unified interface for caching with automatic tier promotion.
    """

    def __init__(
        self,
        max_memory_size: int = 100,
        disk_cache_dir: str = '.cache',
        default_ttl: int = 3600
    ):
        """
        Initialize cache manager.

        Args:
            max_memory_size: Max items in memory cache
            disk_cache_dir: Directory for disk cache
            default_ttl: Default TTL in seconds
        """
        self.memory_cache = LRUCache(max_memory_size)
        self.disk_cache = DiskCache(Path(disk_cache_dir))
        self.default_ttl = default_ttl

        logger.info(
            f"Cache initialized: memory={max_memory_size}, "
            f"disk={disk_cache_dir}"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache (checks memory, then disk).

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Try memory cache first
        result = self.memory_cache.get(key)
        if result:
            value, timestamp = result
            logger.debug(f"Memory cache hit: {key}")
            return value

        # Try disk cache
        result = self.disk_cache.get(key)
        if result:
            value, metadata = result
            logger.debug(f"Disk cache hit: {key}")

            # Promote to memory cache
            self.memory_cache.set(key, value, metadata['timestamp'])
            return value

        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set item in both cache tiers.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (uses default if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        timestamp = time.time()

        # Store in both tiers
        self.memory_cache.set(key, value, timestamp)
        self.disk_cache.set(key, value, ttl)

        logger.debug(f"Cached: {key} (ttl={ttl}s)")

    def delete(self, key: str):
        """Delete item from all cache tiers."""
        self.memory_cache.delete(key)
        self.disk_cache.delete(key)

    def clear(self):
        """Clear all caches."""
        self.memory_cache.clear()
        # Note: Not clearing disk cache for safety
        logger.info("Memory cache cleared")

    def cleanup(self) -> int:
        """
        Cleanup expired entries.

        Returns:
            Number of entries removed
        """
        removed = self.disk_cache.cleanup_expired()
        logger.info(f"Cleaned up {removed} expired cache entries")
        return removed

    def stats(self) -> dict:
        """Get comprehensive cache statistics."""
        return {
            'memory': self.memory_cache.stats(),
            'disk': self.disk_cache.stats()
        }

    def find_duplicates(self) -> Dict[str, list]:
        """Find duplicate cached content."""
        return self.disk_cache.find_duplicates()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    cache = CacheManager(
        max_memory_size=50,
        disk_cache_dir='/tmp/doc_scraper_cache',
        default_ttl=3600
    )

    # Cache some data
    cache.set('https://example.com/page1', '<html>Content 1</html>')
    cache.set('https://example.com/page2', '<html>Content 2</html>', ttl=7200)

    # Retrieve from cache
    content = cache.get('https://example.com/page1')
    print(f"Retrieved: {content[:50]}...")

    # Print statistics
    print("\nCache Statistics:")
    stats = cache.stats()
    print(json.dumps(stats, indent=2))

    # Cleanup
    removed = cache.cleanup()
    print(f"\nCleaned up {removed} expired entries")
