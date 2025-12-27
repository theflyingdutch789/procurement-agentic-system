"""
In-memory query cache for the MongoDB agent.

Caches query results to avoid repeated API calls for identical questions.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe in-memory cache for query results."""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600) -> None:
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries (default 1 hour)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: list[str] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _make_key(self, question: str, model: str, reasoning_effort: str) -> str:
        """Create a cache key from query parameters."""
        normalized = question.lower().strip()
        key_data = f"{normalized}|{model}|{reasoning_effort}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get(
        self,
        question: str,
        model: str = "gpt-5.2",
        reasoning_effort: str = "medium",
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached result if available and not expired.

        Returns:
            Cached result dict or None if not found/expired
        """
        key = self._make_key(question, model, reasoning_effort)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if time.time() - entry["timestamp"] > self._ttl_seconds:
                del self._cache[key]
                self._access_order.remove(key)
                self._misses += 1
                logger.debug("Cache entry expired for key %s", key[:8])
                return None

            self._hits += 1
            logger.info("Cache HIT for query: %s... (key: %s)", question[:50], key[:8])

            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            return entry["result"]

    def set(
        self,
        question: str,
        result: Dict[str, Any],
        model: str = "gpt-5.2",
        reasoning_effort: str = "medium",
    ) -> None:
        """
        Cache a query result.

        Args:
            question: The natural language question
            result: The query result to cache
            model: Model used for the query
            reasoning_effort: Reasoning effort level used
        """
        # Only cache successful results
        if not result.get("success", False):
            return

        key = self._make_key(question, model, reasoning_effort)

        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
                    logger.debug("Evicted cache entry: %s", oldest_key[:8])

            self._cache[key] = {
                "result": result,
                "timestamp": time.time(),
            }
            self._access_order.append(key)
            logger.info("Cached result for query: %s... (key: %s)", question[:50], key[:8])

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("Cache cleared")

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "ttl_seconds": self._ttl_seconds,
            }


# Global cache instance
_global_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryCache()
    return _global_cache
