"""Base collector module with consistent error handling and state tracking.

This module provides a foundation for all collectors with:
- Consistent error handling and reporting
- Data validation helpers
- Connection state tracking
- Last-successful-refresh timestamps
- Retry logic with exponential backoff
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CollectorState(Enum):
    """State of a collector's last operation."""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


@dataclass
class CollectorResult:
    """Result of a collection operation with metadata.

    Provides consistent structure for collector results including
    error information, timing, and state tracking.
    """

    data: dict[str, Any]
    state: CollectorState = CollectorState.OK
    error: str | None = None
    error_type: str | None = None
    collected_at: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    retry_count: int = 0

    @property
    def ok(self) -> bool:
        """Check if collection was successful."""
        return self.state == CollectorState.OK

    @property
    def has_error(self) -> bool:
        """Check if collection encountered an error."""
        return self.state in (CollectorState.ERROR, CollectorState.TIMEOUT)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        result = {
            **self.data,
            "_collector_state": self.state.value,
            "_collected_at": self.collected_at.isoformat(),
            "_duration_ms": self.duration_ms,
        }
        if self.error:
            result["_error"] = self.error
            result["_error_type"] = self.error_type
        if self.retry_count > 0:
            result["_retry_count"] = self.retry_count
        return result


# Global state tracking for collectors
_collector_states: dict[str, CollectorResult] = {}
_last_success: dict[str, datetime] = {}


def get_collector_state(collector_name: str) -> CollectorResult | None:
    """Get the last known state of a collector."""
    return _collector_states.get(collector_name)


def get_last_success(collector_name: str) -> datetime | None:
    """Get the timestamp of the last successful collection."""
    return _last_success.get(collector_name)


def is_stale(collector_name: str, max_age_seconds: float = 300) -> bool:
    """Check if a collector's data is stale.

    Args:
        collector_name: Name of the collector to check.
        max_age_seconds: Maximum age in seconds before data is considered stale.

    Returns:
        True if data is stale or never collected, False otherwise.
    """
    last = _last_success.get(collector_name)
    if last is None:
        return True
    age = (datetime.now() - last).total_seconds()
    return age > max_age_seconds


def update_collector_state(collector_name: str, result: CollectorResult) -> None:
    """Update the global state for a collector."""
    _collector_states[collector_name] = result
    if result.ok:
        _last_success[collector_name] = result.collected_at


def run_command(
    command: list[str],
    timeout: float = 15.0,
    cwd: str | None = None,
) -> tuple[str | None, str | None, CollectorState]:
    """Run a subprocess command with consistent error handling.

    Args:
        command: Command to run as list of strings.
        timeout: Timeout in seconds.
        cwd: Working directory for the command.

    Returns:
        Tuple of (stdout, error_message, state).
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout, None, CollectorState.OK
        else:
            error = result.stderr.strip() if result.stderr else f"Exit code {result.returncode}"
            return None, error, CollectorState.ERROR

    except subprocess.TimeoutExpired:
        return None, f"Command timed out after {timeout}s", CollectorState.TIMEOUT

    except FileNotFoundError:
        cmd_name = command[0] if command else "command"
        return None, f"Command not found: {cmd_name}", CollectorState.UNAVAILABLE

    except PermissionError:
        return None, "Permission denied", CollectorState.ERROR

    except OSError as e:
        return None, f"OS error: {e}", CollectorState.ERROR


def parse_json_output(
    output: str | None,
    default: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Parse JSON output with error handling.

    Args:
        output: JSON string to parse.
        default: Default value if parsing fails.

    Returns:
        Tuple of (parsed_data, error_message).
    """
    if output is None:
        return default or {}, "No output to parse"

    try:
        data = json.loads(output)
        if isinstance(data, dict):
            return data, None
        return {"data": data}, None

    except json.JSONDecodeError as e:
        return default or {}, f"Invalid JSON: {e}"


def safe_get(
    data: dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """Safely get nested dictionary value.

    Args:
        data: Dictionary to extract from.
        *keys: Keys to traverse.
        default: Default value if path not found.

    Returns:
        Value at path or default.
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def validate_data_shape(
    data: dict[str, Any],
    required_keys: list[str],
) -> tuple[bool, list[str]]:
    """Validate that required keys are present in data.

    Args:
        data: Data dictionary to validate.
        required_keys: List of required keys.

    Returns:
        Tuple of (is_valid, missing_keys).
    """
    missing = [key for key in required_keys if key not in data]
    return len(missing) == 0, missing


def with_retry(
    func: Callable[[], T],
    max_retries: int = 2,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
) -> tuple[T | None, int, str | None]:
    """Execute a function with retry logic.

    Args:
        func: Function to execute.
        max_retries: Maximum number of retry attempts.
        delay_seconds: Initial delay between retries.
        backoff_factor: Factor to multiply delay by after each retry.

    Returns:
        Tuple of (result, retry_count, error_message).
    """
    last_error: str | None = None
    delay = delay_seconds

    for attempt in range(max_retries + 1):
        try:
            result = func()
            return result, attempt, None
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor

    return None, max_retries, last_error


def collect_with_fallback(
    primary: Callable[[], dict[str, Any] | None],
    fallback: Callable[[], dict[str, Any] | None] | None = None,
    default: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Execute primary collector with optional fallback.

    Falls back if primary raises an exception or returns None.

    Args:
        primary: Primary collection function.
        fallback: Fallback function if primary fails or returns None.
        default: Default value if both fail.

    Returns:
        Collected data from primary, fallback, or default.
    """
    # Try primary
    try:
        result = primary()
        if result is not None:
            return result
    except Exception:
        pass

    # Try fallback
    if fallback is not None:
        try:
            result = fallback()
            if result is not None:
                return result
        except Exception:
            pass

    return default


def format_error_for_display(
    error: str | None,
    error_type: str | None = None,
    max_length: int = 50,
) -> str:
    """Format an error message for display in UI.

    Args:
        error: Error message to format.
        error_type: Type/category of error.
        max_length: Maximum length before truncation.

    Returns:
        Formatted error string suitable for display.
    """
    if not error:
        return "Unknown error"

    # Clean up common error prefixes
    prefixes_to_strip = [
        "Error: ",
        "ERROR: ",
        "error: ",
        "Exception: ",
    ]
    for prefix in prefixes_to_strip:
        if error.startswith(prefix):
            error = error[len(prefix) :]
            break

    # Truncate if too long
    if len(error) > max_length:
        error = error[: max_length - 1] + "…"

    # Add error type prefix if provided
    if error_type:
        return f"[{error_type}] {error}"

    return error
