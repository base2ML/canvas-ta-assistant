"""
Caching service with TTL support.
Implements the same caching behavior as the original main.py for performance parity.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe TTL (Time-To-Live) cache implementation.
    Based on the original caching logic from main_original.py.
    """

    def __init__(self, max_size: int = 100):
        """Initialize cache with maximum size."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str, ttl: int) -> Optional[Any]:
        """
        Get cached value if it exists and hasn't expired.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached value or None if expired/missing
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            current_time = time.time()

            # Check if expired
            if current_time - timestamp > ttl:
                del self._cache[key]
                return None

            logger.debug(f"Cache hit for key: {key}")
            return value

    def get_stale_ok(
        self, key: str, ttl: int, stale_ttl: int
    ) -> Optional[Tuple[Any, bool]]:
        """
        Get cached value, allowing stale data within stale_ttl window.
        Implements stale-while-revalidate pattern.

        Args:
            key: Cache key
            ttl: Normal time-to-live in seconds
            stale_ttl: Extended TTL for stale data (total age allowed)

        Returns:
            Tuple of (value, is_stale) or None if beyond stale_ttl
            is_stale=True means data is older than ttl but within stale_ttl
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            current_time = time.time()
            age = current_time - timestamp

            # Beyond stale grace period, data is too old
            if age > (ttl + stale_ttl):
                del self._cache[key]
                logger.debug(f"Cache entry too stale for key: {key} (age: {age}s)")
                return None

            # Within normal TTL - fresh data
            if age <= ttl:
                logger.debug(f"Cache hit (fresh) for key: {key}")
                return (value, False)

            # Within stale grace period - stale but usable
            logger.debug(f"Cache hit (stale) for key: {key} (age: {age}s)")
            return (value, True)

    def get_age(self, key: str) -> Optional[float]:
        """
        Get the age of a cached entry in seconds.

        Args:
            key: Cache key

        Returns:
            Age in seconds or None if not cached
        """
        with self._lock:
            if key not in self._cache:
                return None

            _, timestamp = self._cache[key]
            return time.time() - timestamp

    def is_fresh(
        self, key: str, ttl: int, freshness_threshold: float = 0.8
    ) -> Optional[bool]:
        """
        Check if cache entry is fresh (below threshold of TTL).
        Useful for triggering background refresh.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds
            freshness_threshold: Percentage of TTL (0.8 = 80% of TTL)

        Returns:
            True if fresh, False if approaching expiration, None if not cached
        """
        age = self.get_age(key)
        if age is None:
            return None

        return age < (ttl * freshness_threshold)

    def set(self, key: str, value: Any) -> None:
        """
        Set cached value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = time.time()
            self._cache[key] = (value, current_time)

            # Simple cache size management (same as original)
            if len(self._cache) > self._max_size:
                # Remove oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                logger.debug(f"Cache evicted oldest entry: {oldest_key}")

            logger.debug(f"Cache set for key: {key}")

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared - removed {cleared_count} entries")

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            expired_count = 0

            for key, (_, timestamp) in self._cache.items():
                # Count expired entries (these would be removed on next access)
                if current_time - timestamp > 3600:  # Use 1 hour as default for stats
                    expired_count += 1

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "expired_entries": expired_count,
            }


# Global cache instances (matching original structure)
ta_groups_cache = TTLCache()
assignment_stats_cache = TTLCache()
assignments_cache = TTLCache()


def generate_cache_key(course_id: str, api_token: str) -> str:
    """
    Generate cache key from course_id and api_token hash.
    Same logic as original for compatibility.
    """
    return f"{course_id}_{hash(api_token)}"


def get_cached_ta_groups(
    course_id: str, api_token: str, ttl: int
) -> Optional[Tuple[Any, Any, Optional[str]]]:
    """
    Get cached TA groups data.
    Returns tuple of (ta_groups_data, course_data, error) or None if cache miss.
    """
    cache_key = generate_cache_key(course_id, api_token)
    return ta_groups_cache.get(cache_key, ttl)


def set_cached_ta_groups(
    course_id: str,
    api_token: str,
    ta_groups_data: Any,
    course_data: Any,
    error: Optional[str],
) -> None:
    """
    Cache TA groups data.
    Stores tuple of (ta_groups_data, course_data, error).
    """
    cache_key = generate_cache_key(course_id, api_token)
    ta_groups_cache.set(cache_key, (ta_groups_data, course_data, error))
    logger.info(f"Cached TA groups for course {course_id}")


def get_cached_assignment_stats(
    course_id: str, api_token: str, ttl: int
) -> Optional[Any]:
    """Get cached assignment stats data."""
    cache_key = generate_cache_key(course_id, api_token)
    return assignment_stats_cache.get(cache_key, ttl)


def set_cached_assignment_stats(
    course_id: str, api_token: str, assignment_stats: Any
) -> None:
    """Cache assignment stats data."""
    cache_key = generate_cache_key(course_id, api_token)
    assignment_stats_cache.set(cache_key, assignment_stats)
    logger.info(f"Cached assignment stats for course {course_id}")


def generate_assignments_cache_key(course_ids: list, api_token: str) -> str:
    """Generate cache key for assignments from multiple course IDs."""
    course_ids_str = "_".join(sorted(str(cid) for cid in course_ids))
    return f"assignments_{course_ids_str}_{hash(api_token)}"


def get_cached_assignments(
    course_ids: list, api_token: str, ttl: int
) -> Optional[Tuple[Any, Any, Any]]:
    """
    Get cached assignments data.
    Returns tuple of (assignments_data, courses_data, warnings) or None if cache miss.
    """
    cache_key = generate_assignments_cache_key(course_ids, api_token)
    return assignments_cache.get(cache_key, ttl)


def set_cached_assignments(
    course_ids: list,
    api_token: str,
    assignments_data: Any,
    courses_data: Any,
    warnings: Any,
) -> None:
    """
    Cache assignments data.
    Stores tuple of (assignments_data, courses_data, warnings).
    """
    cache_key = generate_assignments_cache_key(course_ids, api_token)
    assignments_cache.set(cache_key, (assignments_data, courses_data, warnings))
    logger.info(f"Cached assignments for courses {course_ids}")


def clear_all_caches() -> Dict[str, int]:
    """
    Clear all caches and return statistics.
    Used by the cache management endpoint.
    """
    ta_size = ta_groups_cache.size()
    assignment_stats_size = assignment_stats_cache.size()
    assignments_size = assignments_cache.size()

    ta_groups_cache.clear()
    assignment_stats_cache.clear()
    assignments_cache.clear()

    return {
        "ta_groups_cleared": ta_size,
        "assignment_stats_cleared": assignment_stats_size,
        "assignments_cleared": assignments_size,
        "total_cleared": ta_size + assignment_stats_size + assignments_size,
    }


def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    return {
        "ta_groups_cache": ta_groups_cache.stats(),
        "assignment_stats_cache": assignment_stats_cache.stats(),
        "assignments_cache": assignments_cache.stats(),
    }


# Stale-while-revalidate helper functions
def get_cached_ta_groups_stale_ok(
    course_id: str, api_token: str, ttl: int, stale_ttl: int
) -> Optional[Tuple[Tuple[Any, Any, Optional[str]], bool]]:
    """
    Get cached TA groups with stale-while-revalidate support.

    Returns:
        Tuple of ((ta_groups_data, course_data, error), is_stale) or None
        is_stale=True indicates data should be refreshed in background
    """
    cache_key = generate_cache_key(course_id, api_token)
    result = ta_groups_cache.get_stale_ok(cache_key, ttl, stale_ttl)
    return result


def get_cached_assignment_stats_stale_ok(
    course_id: str, api_token: str, ttl: int, stale_ttl: int
) -> Optional[Tuple[Any, bool]]:
    """
    Get cached assignment stats with stale-while-revalidate support.

    Returns:
        Tuple of (assignment_stats, is_stale) or None
        is_stale=True indicates data should be refreshed in background
    """
    cache_key = generate_cache_key(course_id, api_token)
    result = assignment_stats_cache.get_stale_ok(cache_key, ttl, stale_ttl)
    return result


def should_refresh_ta_groups_cache(course_id: str, api_token: str, ttl: int) -> bool:
    """
    Check if TA groups cache should be refreshed (approaching expiration).

    Returns:
        True if cache is approaching expiration and should refresh in background
    """
    cache_key = generate_cache_key(course_id, api_token)
    is_fresh = ta_groups_cache.is_fresh(cache_key, ttl, freshness_threshold=0.8)

    # If is_fresh is None (not cached) or False (approaching expiration), should refresh
    return is_fresh is None or not is_fresh


def should_refresh_assignment_stats_cache(
    course_id: str, api_token: str, ttl: int
) -> bool:
    """
    Check if assignment stats cache should be refreshed (approaching expiration).

    Returns:
        True if cache is approaching expiration and should refresh in background
    """
    cache_key = generate_cache_key(course_id, api_token)
    is_fresh = assignment_stats_cache.is_fresh(cache_key, ttl, freshness_threshold=0.8)

    # If is_fresh is None (not cached) or False (approaching expiration), should refresh
    return is_fresh is None or not is_fresh
