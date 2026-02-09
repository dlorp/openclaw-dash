"""Sessions collector."""

import logging
import subprocess
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
logger = logging.getLogger(__name__)


def _is_transient_error(error: Exception) -> bool:
    """Determine if an error is transient and worth retrying.

    Args:
        error: The exception to check

    Returns:
        True if the error is likely transient (timeout, connection issue),
        False if it's permanent (file not found, permission denied, etc.)
    """
    # Transient errors worth retrying
    if isinstance(error, subprocess.TimeoutExpired):
        return True
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        # Connection-related errors are often transient
        # but exclude FileNotFoundError (permanent)
        if isinstance(error, FileNotFoundError):
            return False
        return True

    # All other errors are considered permanent
    return False


def _collect_sessions_impl() -> dict[str, Any]:
    """Collect session information with error tracking.

    Returns:
        Dictionary containing session list and counts, with metadata
        about collection status.
    """
    start_time = time.time()

    # Retry configuration: 3 attempts with exponential backoff
    max_attempts = 3
    backoff_delays = [0.5, 1.0, 2.0]  # seconds between retries

    last_error = None
    status = None

    # Try real CLI data with retry logic
    for attempt in range(max_attempts):
        try:
            status = get_openclaw_status(timeout=3)
            break  # Success - exit retry loop

        except Exception as e:
            last_error = e

            # Check if this is the last attempt
            if attempt < max_attempts - 1:
                # Determine if we should retry
                if _is_transient_error(e):
                    delay = backoff_delays[attempt]
                    logger.warning(
                        f"Sessions collector attempt {attempt + 1}/{max_attempts} failed "
                        f"with transient error ({type(e).__name__}: {e}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    # Permanent error - don't retry
                    logger.error(
                        f"Sessions collector failed with permanent error ({type(e).__name__}: {e}). "
                        "Not retrying."
                    )
                    break
            else:
                # Last attempt failed
                logger.error(
                    f"Sessions collector failed after {max_attempts} attempts. "
                    f"Final error: {type(e).__name__}: {e}"
                )

    duration_ms = (time.time() - start_time) * 1000

    # Process successful result
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

    # Handle failure cases
    if last_error is not None:
        # Exception occurred - return error data
        error_data = {
            "sessions": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
            "error": str(last_error),
            "_error_type": type(last_error).__name__,
        }

        result = CollectorResult(
            data=error_data,
            state=CollectorState.ERROR,
            error=str(last_error),
            error_type=type(last_error).__name__,
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return error_data
    else:
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
