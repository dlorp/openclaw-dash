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


def _is_transient_error(exc: Exception) -> bool:
    """Check if an error is transient and worth retrying.

    Transient errors:
    - subprocess.TimeoutExpired (CLI timeout)
    - ConnectionError, OSError (network issues)

    Permanent errors (don't retry):
    - FileNotFoundError (openclaw CLI not installed)
    - Other exceptions (unknown, could be permanent)
    """
    return isinstance(exc, (subprocess.TimeoutExpired, ConnectionError, OSError))


def _get_openclaw_status_with_retry(timeout: int = 3) -> Any:
    """Get openclaw status with retry logic for transient failures.

    Retries up to 3 times with exponential backoff (0.5s, 1s, 2s).

    Args:
        timeout: Timeout in seconds for each CLI call

    Returns:
        OpenClawStatus or None if all attempts failed

    Raises:
        Exception: Re-raises the last exception if all retries fail
    """
    max_attempts = 3
    backoff_delays = [0.5, 1.0, 2.0]  # seconds

    last_exception = None

    for attempt in range(max_attempts):
        try:
            return get_openclaw_status(timeout=timeout)
        except Exception as e:
            last_exception = e

            # Don't retry on permanent errors
            if not _is_transient_error(e):
                logger.debug(
                    f"Permanent error on attempt {attempt + 1}/{max_attempts}: {type(e).__name__}: {e}"
                )
                raise

            # Log retry attempt
            if attempt < max_attempts - 1:  # Don't log on last attempt
                delay = backoff_delays[attempt]
                logger.info(
                    f"Transient error on attempt {attempt + 1}/{max_attempts}, "
                    f"retrying in {delay}s: {type(e).__name__}: {e}"
                )
                time.sleep(delay)
            else:
                logger.warning(
                    f"All {max_attempts} attempts failed. Last error: {type(e).__name__}: {e}"
                )

    # All retries exhausted, re-raise the last exception
    if last_exception:
        raise last_exception

    return None


def _collect_sessions_impl() -> dict[str, Any]:
    """Collect session information with error tracking.

    Returns:
        Dictionary containing session list and counts, with metadata
        about collection status.
    """
    start_time = time.time()

    # Try real CLI data with retry logic
    try:
        status = _get_openclaw_status_with_retry(timeout=3)
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
