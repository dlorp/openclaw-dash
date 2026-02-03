"""Tests for the collector cache module."""

import time
from typing import Any

from openclaw_dash.collectors.cache import (
    CIRCUIT_RESET_SECONDS,
    MAX_ERRORS,
    SLOW_THRESHOLD,
    CollectorCache,
    CollectorStats,
    cached_collector,
    get_cache,
    reset_cache,
)


class TestCacheEntry:
    """Tests for cache entry behavior."""

    def test_cache_set_and_get(self) -> None:
        """Test basic cache set and get."""
        cache = CollectorCache()
        data = {"healthy": True, "value": 42}

        cache.set("test", data, ttl=10.0)
        result = cache.get("test")

        assert result == data

    def test_cache_expiration(self) -> None:
        """Test cache entry expires after TTL."""
        cache = CollectorCache()
        data = {"healthy": True}

        cache.set("test", data, ttl=0.01)  # Very short TTL
        time.sleep(0.02)  # Wait for expiration

        result = cache.get("test")
        assert result is None

    def test_get_stale_returns_expired_data(self) -> None:
        """Test get_stale returns data even after expiration."""
        cache = CollectorCache()
        data = {"healthy": True}

        cache.set("test", data, ttl=0.01)
        time.sleep(0.02)

        # Regular get returns None
        assert cache.get("test") is None
        # Stale get still returns data
        assert cache.get_stale("test") == data

    def test_invalidate_removes_entry(self) -> None:
        """Test invalidate removes a specific cache entry."""
        cache = CollectorCache()
        cache.set("test1", {"a": 1})
        cache.set("test2", {"b": 2})

        cache.invalidate("test1")

        assert cache.get("test1") is None
        assert cache.get("test2") == {"b": 2}

    def test_clear_removes_all_entries(self) -> None:
        """Test clear removes all cache entries."""
        cache = CollectorCache()
        cache.set("test1", {"a": 1})
        cache.set("test2", {"b": 2})

        cache.clear()

        assert cache.get("test1") is None
        assert cache.get("test2") is None


class TestCollectorStats:
    """Tests for collector statistics tracking."""

    def test_stats_initialization(self) -> None:
        """Test stats are initialized with defaults."""
        stats = CollectorStats(name="test")

        assert stats.name == "test"
        assert stats.call_count == 0
        assert stats.cache_hits == 0
        assert stats.error_count == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test cache hit rate calculation."""
        stats = CollectorStats(name="test")
        stats.cache_hits = 7
        stats.cache_misses = 3

        assert stats.hit_rate == 70.0

    def test_avg_time_calculation(self) -> None:
        """Test average time calculation."""
        stats = CollectorStats(name="test")
        stats.call_count = 4
        stats.total_time_ms = 100

        assert stats.avg_time_ms == 25.0

    def test_to_dict(self) -> None:
        """Test stats serialization to dictionary."""
        stats = CollectorStats(name="test")
        stats.call_count = 10
        stats.cache_hits = 5
        stats.cache_misses = 5

        result = stats.to_dict()

        assert result["name"] == "test"
        assert result["call_count"] == 10
        assert result["hit_rate_pct"] == 50.0


class TestCircuitBreaker:
    """Tests for circuit breaker functionality."""

    def test_circuit_opens_after_max_errors(self) -> None:
        """Test circuit breaker opens after repeated errors."""
        cache = CollectorCache()

        # Record errors up to threshold
        for _ in range(MAX_ERRORS):
            cache.record_call("test", 100, cache_hit=False, error="Connection failed")

        assert cache.is_circuit_open("test") is True

    def test_circuit_stays_closed_below_threshold(self) -> None:
        """Test circuit stays closed with fewer errors than threshold."""
        cache = CollectorCache()

        for _ in range(MAX_ERRORS - 1):
            cache.record_call("test", 100, cache_hit=False, error="Error")

        assert cache.is_circuit_open("test") is False

    def test_circuit_resets_on_success(self) -> None:
        """Test error count resets after successful call."""
        cache = CollectorCache()

        # Accumulate some errors (but not enough to trip)
        cache.record_call("test", 100, cache_hit=False, error="Error")
        cache.record_call("test", 100, cache_hit=False, error="Error")

        # Success resets the count
        cache.record_call("test", 100, cache_hit=False, error=None)

        stats = cache.get_stats("test")
        assert stats.error_count == 0

    def test_circuit_auto_resets_after_timeout(self) -> None:
        """Test circuit breaker auto-resets after timeout period."""
        cache = CollectorCache()

        # Trip the circuit
        for _ in range(MAX_ERRORS):
            cache.record_call("test", 100, cache_hit=False, error="Error")

        assert cache.is_circuit_open("test") is True

        # Simulate time passing
        stats = cache.get_stats("test")
        stats.circuit_opened_at = time.monotonic() - CIRCUIT_RESET_SECONDS - 1

        assert cache.is_circuit_open("test") is False

    def test_manual_circuit_reset(self) -> None:
        """Test manual circuit breaker reset."""
        cache = CollectorCache()

        # Trip the circuit
        for _ in range(MAX_ERRORS):
            cache.record_call("test", 100, cache_hit=False, error="Error")

        cache.reset_circuit("test")

        assert cache.is_circuit_open("test") is False
        assert cache.get_stats("test").error_count == 0


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    def test_decorator_caches_results(self) -> None:
        """Test decorator caches function results."""
        cache = CollectorCache()
        call_count = 0

        @cache.cached("test_fn", ttl=10.0)
        def collect_data() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"value": 42}

        # First call - cache miss
        result1 = collect_data()
        # Second call - cache hit
        result2 = collect_data()

        assert result1["value"] == 42
        assert result2["value"] == 42
        assert call_count == 1  # Only called once

    def test_decorator_adds_cache_metadata(self) -> None:
        """Test decorator adds _from_cache metadata on cache hit."""
        cache = CollectorCache()

        @cache.cached("test_fn", ttl=10.0)
        def collect_data() -> dict[str, Any]:
            return {"value": 42}

        collect_data()  # Populate cache
        result = collect_data()  # Cache hit

        assert result.get("_from_cache") is True

    def test_decorator_adds_timing_metadata(self) -> None:
        """Test decorator adds fetch time on cache miss."""
        cache = CollectorCache()

        @cache.cached("test_fn", ttl=10.0)
        def collect_data() -> dict[str, Any]:
            return {"value": 42}

        result = collect_data()  # Cache miss

        assert "_fetch_time_ms" in result
        assert isinstance(result["_fetch_time_ms"], float)

    def test_decorator_marks_slow_calls(self) -> None:
        """Test decorator marks slow collector calls."""
        cache = CollectorCache()

        @cache.cached("test_fn", ttl=10.0)
        def slow_collect() -> dict[str, Any]:
            time.sleep(SLOW_THRESHOLD + 0.1)
            return {"value": 42}

        result = slow_collect()

        assert result.get("_slow") is True

    def test_decorator_returns_stale_on_error(self) -> None:
        """Test decorator returns stale data when collection fails."""
        cache = CollectorCache()
        should_fail = False

        @cache.cached("test_fn", ttl=0.01, stale_while_revalidate=True)
        def flaky_collect() -> dict[str, Any]:
            if should_fail:
                raise ConnectionError("Failed")
            return {"value": 42}

        # First call succeeds
        result1 = flaky_collect()
        assert result1["value"] == 42

        # Wait for cache to expire
        time.sleep(0.02)

        # Now make it fail
        should_fail = True
        result2 = flaky_collect()

        # Should return stale data with metadata
        assert result2["value"] == 42
        assert result2.get("_stale") is True
        assert result2.get("_error") is not None

    def test_decorator_returns_default_on_error(self) -> None:
        """Test decorator returns default value when no stale data."""
        cache = CollectorCache()
        default = {"error": "unavailable", "healthy": False}

        @cache.cached("test_fn", ttl=10.0, default_on_error=default)
        def failing_collect() -> dict[str, Any]:
            raise ConnectionError("Always fails")

        result = failing_collect()

        assert result == default

    def test_decorator_respects_circuit_breaker(self) -> None:
        """Test decorator respects circuit breaker state."""
        cache = CollectorCache()

        # Trip the circuit
        for _ in range(MAX_ERRORS):
            cache.record_call("test_fn", 100, cache_hit=False, error="Error")

        @cache.cached("test_fn", ttl=10.0)
        def collect_data() -> dict[str, Any]:
            return {"value": 42}

        result = collect_data()

        assert result.get("_circuit_open") is True


class TestGlobalCache:
    """Tests for the global cache singleton."""

    def test_get_cache_returns_singleton(self) -> None:
        """Test get_cache returns the same instance."""
        reset_cache()

        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_reset_cache_clears_data(self) -> None:
        """Test reset_cache clears cache and stats."""
        cache = get_cache()
        cache.set("test", {"value": 1})
        cache.record_call("test", 100, cache_hit=False)

        reset_cache()

        assert cache.get("test") is None
        assert len(cache._stats) == 0

    def test_cached_collector_decorator(self) -> None:
        """Test the convenience cached_collector decorator."""
        reset_cache()

        @cached_collector("test_collector", ttl=10.0)
        def my_collector() -> dict[str, Any]:
            return {"data": "test"}

        result = my_collector()
        assert result["data"] == "test"

        # Should be cached
        cache = get_cache()
        stats = cache.get_stats("test_collector")
        assert stats.cache_misses == 1


class TestHealthSummary:
    """Tests for health summary generation."""

    def test_health_summary_empty_cache(self) -> None:
        """Test health summary with no collectors."""
        cache = CollectorCache()
        health = cache.get_health_summary()

        assert health["total_collectors"] == 0
        assert health["healthy_count"] == 0

    def test_health_summary_counts_states(self) -> None:
        """Test health summary counts collector states correctly."""
        cache = CollectorCache()

        # Healthy collector
        cache.record_call("healthy", 100, cache_hit=False)

        # Degraded collector (has errors but circuit not open)
        cache.record_call("degraded", 100, cache_hit=False, error="Error")

        # Failed collector (circuit open)
        for _ in range(MAX_ERRORS):
            cache.record_call("failed", 100, cache_hit=False, error="Error")

        health = cache.get_health_summary()

        assert health["total_collectors"] == 3
        assert health["healthy_count"] == 1
        assert health["degraded_count"] == 1
        assert health["failed_count"] == 1

    def test_health_summary_identifies_slowest(self) -> None:
        """Test health summary identifies slowest collector."""
        cache = CollectorCache()

        cache.record_call("fast", 50, cache_hit=False)
        cache.record_call("slow", 500, cache_hit=False)
        cache.record_call("medium", 200, cache_hit=False)

        health = cache.get_health_summary()

        assert health["slowest_collector"] == "slow"
        assert health["slowest_time_ms"] == 500.0


class TestIntegration:
    """Integration tests with real collector behavior."""

    def test_multiple_collectors_share_cache(self) -> None:
        """Test multiple collectors can share the global cache."""
        reset_cache()
        cache = get_cache()

        @cached_collector("collector_a", ttl=10.0)
        def collect_a() -> dict[str, Any]:
            return {"source": "a"}

        @cached_collector("collector_b", ttl=10.0)
        def collect_b() -> dict[str, Any]:
            return {"source": "b"}

        result_a = collect_a()
        result_b = collect_b()

        assert result_a["source"] == "a"
        assert result_b["source"] == "b"

        all_stats = cache.get_all_stats()
        assert "collector_a" in all_stats
        assert "collector_b" in all_stats

    def test_cache_survives_collector_failure(self) -> None:
        """Test cache remains usable after collector failures."""
        reset_cache()
        fail_count = 0

        @cached_collector("flaky", ttl=0.01, default_on_error={"fallback": True})
        def flaky_collector() -> dict[str, Any]:
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 2:
                raise RuntimeError("Temporary failure")
            return {"success": True}

        # First two calls fail
        result1 = flaky_collector()
        time.sleep(0.02)
        result2 = flaky_collector()
        time.sleep(0.02)

        # Third call succeeds
        result3 = flaky_collector()

        assert result1.get("fallback") is True
        assert result2.get("fallback") is True
        assert result3.get("success") is True
