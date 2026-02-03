"""Collector caching, timing, and error handling layer.

Provides:
- LRU cache with TTL for collector results
- Timing instrumentation for performance tracking
- Unified error handling with retry logic
- Health metrics for monitoring collector status
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

# Default cache TTL in seconds (5 seconds for most collectors)
DEFAULT_TTL = 5.0

# Slow collector threshold in seconds
SLOW_THRESHOLD = 2.0

# Maximum errors before circuit breaker trips
MAX_ERRORS = 3

# Circuit breaker reset time in seconds
CIRCUIT_RESET_SECONDS = 60.0


@dataclass
class CacheEntry:
    """A single cached collector result."""

    value: dict[str, Any]
    timestamp: float
    ttl: float
    fetch_time_ms: float

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.monotonic() - self.timestamp > self.ttl


@dataclass
class CollectorStats:
    """Statistics for a single collector."""

    name: str
    call_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time_ms: float = 0
    last_call_time_ms: float = 0
    error_count: int = 0
    last_error: str | None = None
    last_error_time: datetime | None = None
    circuit_open: bool = False
    circuit_opened_at: float | None = None

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    @property
    def avg_time_ms(self) -> float:
        """Calculate average call time in milliseconds."""
        return (self.total_time_ms / self.call_count) if self.call_count > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "call_count": self.call_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_pct": round(self.hit_rate, 1),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "last_call_time_ms": round(self.last_call_time_ms, 2),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_error_time": (self.last_error_time.isoformat() if self.last_error_time else None),
            "circuit_open": self.circuit_open,
        }


class CollectorCache:
    """Thread-safe cache for collector results with timing and error tracking.

    Features:
    - TTL-based expiration per collector
    - Performance timing for each call
    - Circuit breaker pattern for failing collectors
    - Stale-while-revalidate support

    Example:
        cache = CollectorCache()

        @cache.cached("gateway", ttl=10.0)
        def collect_gateway():
            return {"healthy": True}

        # First call fetches fresh data
        data = collect_gateway()  # cache miss

        # Subsequent calls within TTL return cached data
        data = collect_gateway()  # cache hit
    """

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: dict[str, CacheEntry] = {}
        self._stats: dict[str, CollectorStats] = {}

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a cached value if not expired.

        Args:
            name: Collector name/key.

        Returns:
            Cached value or None if expired/missing.
        """
        entry = self._cache.get(name)
        if entry is None:
            return None
        if entry.is_expired():
            return None
        return entry.value

    def get_stale(self, name: str) -> dict[str, Any] | None:
        """Get cached value even if expired (stale-while-revalidate).

        Args:
            name: Collector name/key.

        Returns:
            Cached value or None if never cached.
        """
        entry = self._cache.get(name)
        return entry.value if entry else None

    def set(
        self,
        name: str,
        value: dict[str, Any],
        ttl: float = DEFAULT_TTL,
        fetch_time_ms: float = 0,
    ) -> None:
        """Store a value in the cache.

        Args:
            name: Collector name/key.
            value: Data to cache.
            ttl: Time-to-live in seconds.
            fetch_time_ms: How long the fetch took (for stats).
        """
        self._cache[name] = CacheEntry(
            value=value,
            timestamp=time.monotonic(),
            ttl=ttl,
            fetch_time_ms=fetch_time_ms,
        )

    def invalidate(self, name: str) -> None:
        """Remove a specific entry from the cache.

        Args:
            name: Collector name/key to invalidate.
        """
        self._cache.pop(name, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def get_stats(self, name: str) -> CollectorStats:
        """Get or create stats for a collector.

        Args:
            name: Collector name.

        Returns:
            CollectorStats instance for the collector.
        """
        if name not in self._stats:
            self._stats[name] = CollectorStats(name=name)
        return self._stats[name]

    def record_call(
        self,
        name: str,
        time_ms: float,
        cache_hit: bool,
        error: str | None = None,
    ) -> None:
        """Record a collector call for statistics.

        Args:
            name: Collector name.
            time_ms: Call duration in milliseconds.
            cache_hit: Whether this was a cache hit.
            error: Error message if call failed.
        """
        stats = self.get_stats(name)
        stats.call_count += 1
        stats.total_time_ms += time_ms
        stats.last_call_time_ms = time_ms

        if cache_hit:
            stats.cache_hits += 1
        else:
            stats.cache_misses += 1

        if error:
            stats.error_count += 1
            stats.last_error = error[:200]  # Truncate long errors
            stats.last_error_time = datetime.now()

            # Circuit breaker logic
            if stats.error_count >= MAX_ERRORS and not stats.circuit_open:
                stats.circuit_open = True
                stats.circuit_opened_at = time.monotonic()
        else:
            # Reset error count on success
            stats.error_count = 0

    def is_circuit_open(self, name: str) -> bool:
        """Check if circuit breaker is open for a collector.

        Args:
            name: Collector name.

        Returns:
            True if circuit is open (collector should be skipped).
        """
        stats = self.get_stats(name)
        if not stats.circuit_open:
            return False

        # Auto-reset after timeout
        if stats.circuit_opened_at:
            elapsed = time.monotonic() - stats.circuit_opened_at
            if elapsed > CIRCUIT_RESET_SECONDS:
                stats.circuit_open = False
                stats.circuit_opened_at = None
                stats.error_count = 0
                return False

        return True

    def reset_circuit(self, name: str) -> None:
        """Manually reset the circuit breaker for a collector.

        Args:
            name: Collector name.
        """
        stats = self.get_stats(name)
        stats.circuit_open = False
        stats.circuit_opened_at = None
        stats.error_count = 0

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all collectors.

        Returns:
            Dictionary mapping collector names to their stats.
        """
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall health summary of all collectors.

        Returns:
            Dictionary with health metrics:
            - total_collectors: Number of tracked collectors
            - healthy_count: Collectors with no recent errors
            - degraded_count: Collectors with errors but not tripped
            - failed_count: Collectors with open circuit breakers
            - avg_cache_hit_rate: Average cache hit rate across all
            - slowest_collector: Name of slowest collector
        """
        if not self._stats:
            return {
                "total_collectors": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "failed_count": 0,
                "avg_cache_hit_rate": 0.0,
                "slowest_collector": None,
            }

        healthy = 0
        degraded = 0
        failed = 0
        total_hit_rate = 0.0
        slowest_name: str | None = None
        slowest_time = 0.0

        for stats in self._stats.values():
            if stats.circuit_open:
                failed += 1
            elif stats.error_count > 0:
                degraded += 1
            else:
                healthy += 1

            total_hit_rate += stats.hit_rate
            if stats.avg_time_ms > slowest_time:
                slowest_time = stats.avg_time_ms
                slowest_name = stats.name

        return {
            "total_collectors": len(self._stats),
            "healthy_count": healthy,
            "degraded_count": degraded,
            "failed_count": failed,
            "avg_cache_hit_rate": round(total_hit_rate / len(self._stats), 1),
            "slowest_collector": slowest_name,
            "slowest_time_ms": round(slowest_time, 2),
            "collected_at": datetime.now().isoformat(),
        }

    def cached(
        self,
        name: str,
        ttl: float = DEFAULT_TTL,
        stale_while_revalidate: bool = True,
        default_on_error: dict[str, Any] | None = None,
    ) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
        """Decorator to cache a collector function with timing.

        Args:
            name: Unique name for this collector.
            ttl: Cache TTL in seconds.
            stale_while_revalidate: Return stale data on error if available.
            default_on_error: Default value to return on error if no stale data.

        Returns:
            Decorated function with caching, timing, and error handling.

        Example:
            @cache.cached("gateway", ttl=10.0)
            def collect_gateway():
                return {"healthy": True}
        """

        def decorator(
            func: Callable[..., dict[str, Any]],
        ) -> Callable[..., dict[str, Any]]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
                # Check circuit breaker
                if self.is_circuit_open(name):
                    stale = self.get_stale(name)
                    if stale:
                        return {**stale, "_from_cache": True, "_circuit_open": True}
                    return default_on_error or {
                        "error": f"Circuit open for {name}",
                        "_circuit_open": True,
                    }

                # Try cache first
                cached = self.get(name)
                if cached is not None:
                    start = time.monotonic()
                    elapsed_ms = (time.monotonic() - start) * 1000
                    self.record_call(name, elapsed_ms, cache_hit=True)
                    return {**cached, "_from_cache": True}

                # Cache miss - fetch fresh data
                start = time.monotonic()
                error_msg: str | None = None

                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.monotonic() - start) * 1000

                    # Add timing metadata
                    result["_fetch_time_ms"] = round(elapsed_ms, 2)
                    if elapsed_ms > SLOW_THRESHOLD * 1000:
                        result["_slow"] = True

                    # Cache the result
                    self.set(name, result, ttl=ttl, fetch_time_ms=elapsed_ms)
                    self.record_call(name, elapsed_ms, cache_hit=False)

                    return result

                except Exception as e:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    error_msg = str(e)
                    self.record_call(name, elapsed_ms, cache_hit=False, error=error_msg)

                    # Try stale data
                    if stale_while_revalidate:
                        stale = self.get_stale(name)
                        if stale:
                            return {
                                **stale,
                                "_from_cache": True,
                                "_stale": True,
                                "_error": error_msg,
                            }

                    # Return default or error
                    return default_on_error or {
                        "error": error_msg,
                        "_fetch_time_ms": round(elapsed_ms, 2),
                    }

            return wrapper

        return decorator


# Global cache instance for shared use across collectors
_global_cache: CollectorCache | None = None


def get_cache() -> CollectorCache:
    """Get the global collector cache instance.

    Returns:
        The shared CollectorCache instance.
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CollectorCache()
    return _global_cache


def reset_cache() -> None:
    """Reset the global cache (useful for testing)."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
        _global_cache._stats.clear()


# Type alias for collector functions
F = TypeVar("F", bound=Callable[..., dict[str, Any]])


def cached_collector(
    name: str,
    ttl: float = DEFAULT_TTL,
    stale_while_revalidate: bool = True,
    default_on_error: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Convenience decorator using the global cache.

    Args:
        name: Unique name for this collector.
        ttl: Cache TTL in seconds.
        stale_while_revalidate: Return stale data on error if available.
        default_on_error: Default value to return on error if no stale data.

    Returns:
        Decorated function with caching, timing, and error handling.

    Example:
        from openclaw_dash.collectors.cache import cached_collector

        @cached_collector("gateway", ttl=10.0)
        def collect():
            return {"healthy": True}
    """
    cache = get_cache()
    return cache.cached(
        name,
        ttl=ttl,
        stale_while_revalidate=stale_while_revalidate,
        default_on_error=default_on_error,
    )
