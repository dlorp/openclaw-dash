"""Gateway status collector."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    collect_with_fallback,
    update_collector_state,
)
from openclaw_dash.collectors.cache import cached_collector
from openclaw_dash.collectors.openclaw_cli import get_openclaw_status, status_to_gateway_data
from openclaw_dash.demo import is_demo_mode, mock_gateway_status

COLLECTOR_NAME = "gateway"

# Connection state tracking
_connection_failures: int = 0
_last_healthy: datetime | None = None


def _try_cli_status() -> dict[str, Any] | None:
    """Try to get gateway status via CLI."""
    status = get_openclaw_status()
    if status is not None:
        return status_to_gateway_data(status)
    return None


def _try_http_health() -> dict[str, Any] | None:
    """Try HTTP health check as fallback."""
    try:
        import httpx

        resp = httpx.get("http://localhost:18789/health", timeout=3)
        if resp.status_code == 200:
            return {
                "healthy": True,
                "mode": "unknown",
                "url": "http://localhost:18789",
                "source": "http_fallback",
            }
        else:
            return {
                "healthy": False,
                "error": f"Health check returned {resp.status_code}",
                "source": "http_fallback",
            }
    except ImportError:
        # httpx not installed - not an error, just unavailable
        return None
    except Exception as e:
        # Connection refused, timeout, etc.
        error_msg = str(e)
        if "Connection refused" in error_msg:
            return {
                "healthy": False,
                "error": "Gateway not running",
                "error_type": "connection_refused",
            }
        elif "timed out" in error_msg.lower():
            return {
                "healthy": False,
                "error": "Gateway timed out unexpectedly (this may be a bug)",
                "error_type": "timeout",
            }
        return None


def _collect_gateway_impl() -> dict[str, Any]:
    """Collect gateway status with robust error handling.

    Attempts HTTP health check first (fast), then CLI status as fallback.
    HTTP typically responds in <100ms vs CLI taking 5-10s.
    Tracks connection state for better error reporting.

    Returns:
        Dictionary containing gateway status and health information.
    """
    global _connection_failures, _last_healthy

    start_time = time.time()

    # Try HTTP first (fast), then CLI fallback (slow but more detailed)
    data = collect_with_fallback(
        primary=lambda: _try_http_health(),
        fallback=lambda: _try_cli_status(),
    )

    duration_ms = (time.time() - start_time) * 1000

    if data and data.get("healthy"):
        # Success - reset failure counter
        _connection_failures = 0
        _last_healthy = datetime.now()

        data["collected_at"] = datetime.now().isoformat()
        data["_consecutive_failures"] = 0

        result = CollectorResult(
            data=data,
            state=CollectorState.OK,
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return data

    elif data and not data.get("healthy"):
        # Gateway responded but not healthy
        _connection_failures += 1

        data["collected_at"] = datetime.now().isoformat()
        data["_consecutive_failures"] = _connection_failures
        if _last_healthy:
            data["_last_healthy"] = _last_healthy.isoformat()

        result = CollectorResult(
            data=data,
            state=CollectorState.ERROR,
            error=data.get("error", "Gateway unhealthy"),
            error_type=data.get("error_type"),
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return data

    else:
        # Both methods failed
        _connection_failures += 1

        error_data = {
            "healthy": False,
            "error": "Cannot connect to gateway",
            "error_type": "connection_failed",
            "collected_at": datetime.now().isoformat(),
            "_consecutive_failures": _connection_failures,
        }
        if _last_healthy:
            error_data["_last_healthy"] = _last_healthy.isoformat()

        # Add helpful hints based on failure count
        # The gateway runs locally, so failures are unexpected
        if _connection_failures >= 5:
            error_data["_hint"] = "Run 'openclaw gateway start' to start the local gateway"
        elif _connection_failures >= 3:
            error_data["_hint"] = "Gateway may need to be started: openclaw gateway start"
        else:
            error_data["_hint"] = "Checking local gateway connection..."

        result = CollectorResult(
            data=error_data,
            state=CollectorState.UNAVAILABLE,
            error="Cannot connect to gateway",
            error_type="connection_failed",
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return error_data


def get_connection_state() -> dict[str, Any]:
    """Get current connection state information.

    Returns:
        Dictionary with connection state details.
    """
    return {
        "consecutive_failures": _connection_failures,
        "last_healthy": _last_healthy.isoformat() if _last_healthy else None,
        "is_healthy": _connection_failures == 0 and _last_healthy is not None,
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
    """Cached gateway collection with robust error handling."""
    return _collect_gateway_impl()


def collect() -> dict[str, Any]:
    """Collect gateway status.

    Uses caching to avoid redundant CLI/HTTP calls.
    Returns stale data if fresh collection fails.
    Includes robust error handling with connection state tracking.
    """
    # Return mock data in demo mode (skip caching)
    if is_demo_mode():
        return mock_gateway_status()

    return _collect_cached()
