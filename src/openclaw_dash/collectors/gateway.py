"""Gateway status collector."""

from datetime import datetime
from typing import Any

from openclaw_dash.collectors.cache import cached_collector
from openclaw_dash.collectors.openclaw_cli import get_openclaw_status, status_to_gateway_data
from openclaw_dash.demo import is_demo_mode, mock_gateway_status


def _collect_gateway_impl() -> dict[str, Any]:
    """Internal implementation of gateway collection."""
    # Try real CLI data first
    status = get_openclaw_status()
    if status is not None:
        return status_to_gateway_data(status)

    # Fallback - try HTTP health check
    try:
        import httpx

        resp = httpx.get("http://localhost:18789/health", timeout=5)
        if resp.status_code == 200:
            return {
                "healthy": True,
                "mode": "unknown",
                "url": "http://localhost:18789",
                "collected_at": datetime.now().isoformat(),
            }
    except Exception as e:
        # Re-raise with more context for error tracking
        raise ConnectionError(f"Gateway health check failed: {e}") from e

    return {
        "healthy": False,
        "error": "Cannot connect to gateway",
        "collected_at": datetime.now().isoformat(),
    }


@cached_collector(
    "gateway",
    ttl=10.0,  # Cache for 10 seconds
    default_on_error={
        "healthy": False,
        "error": "Collector failed",
        "collected_at": "",
    },
)
def _collect_cached() -> dict[str, Any]:
    """Cached gateway collection."""
    return _collect_gateway_impl()


def collect() -> dict[str, Any]:
    """Collect gateway status.

    Uses caching to avoid redundant CLI/HTTP calls.
    Returns stale data if fresh collection fails.
    """
    # Return mock data in demo mode (skip caching)
    if is_demo_mode():
        return mock_gateway_status()

    return _collect_cached()
