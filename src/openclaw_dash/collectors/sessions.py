"""Sessions collector."""

import time
from datetime import datetime
from typing import Any

from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    update_collector_state,
)
from openclaw_dash.collectors.cache import cached_collector
from openclaw_dash.collectors.openclaw_cli import get_openclaw_status, status_to_sessions_data
from openclaw_dash.demo import is_demo_mode, mock_sessions

COLLECTOR_NAME = "sessions"


def _collect_sessions_impl() -> dict[str, Any]:
    """Collect session information with error tracking.

    Returns:
        Dictionary containing session list and counts, with metadata
        about collection status.
    """
    start_time = time.time()

    # Try real CLI data
    try:
        status = get_openclaw_status(timeout=3)
        duration_ms = (time.time() - start_time) * 1000

        if status is not None:
            data = status_to_sessions_data(status)
            data["collected_at"] = datetime.now().isoformat()

            result = CollectorResult(
                data=data,
                state=CollectorState.OK,
                duration_ms=duration_ms,
            )
            update_collector_state(COLLECTOR_NAME, result)
            return data

        # CLI returned None - gateway may be unavailable
        empty_data = {
            "sessions": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
            "_source": "fallback",
            "_reason": "Gateway status unavailable",
        }

        result = CollectorResult(
            data=empty_data,
            state=CollectorState.UNAVAILABLE,
            error="Gateway status unavailable",
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return empty_data

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Return empty with error info
        error_data = {
            "sessions": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
            "error": str(e),
            "_error_type": type(e).__name__,
        }

        result = CollectorResult(
            data=error_data,
            state=CollectorState.ERROR,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return error_data


@cached_collector(
    "sessions",
    ttl=10.0,  # Cache for 10 seconds
    default_on_error={
        "sessions": [],
        "total": 0,
        "active": 0,
        "error": "Collector failed",
        "collected_at": "",
    },
)
def _collect_cached() -> dict[str, Any]:
    """Cached sessions collection."""
    return _collect_sessions_impl()


def collect() -> dict[str, Any]:
    """Collect session information.

    Uses caching to avoid redundant CLI calls.
    """
    # Return mock data in demo mode (skip caching)
    if is_demo_mode():
        sessions = mock_sessions()
        return {
            "sessions": sessions,
            "total": len(sessions),
            "active": len(sessions),
            "collected_at": datetime.now().isoformat(),
        }

    return _collect_cached()
