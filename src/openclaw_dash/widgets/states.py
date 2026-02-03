"""Widget state management for consistent loading, error, and empty states.

This module provides utilities for displaying consistent states across all
dashboard widgets including:
- Loading states with optional progress indicators
- Error states with actionable messages
- Empty states with helpful context
- Stale data warnings
- Connection status indicators
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from openclaw_dash.collectors.base import (
    CollectorState,
    get_collector_state,
    get_last_success,
    is_stale,
)
from openclaw_dash.widgets.ascii_art import STATUS_SYMBOLS


class WidgetState(Enum):
    """Visual state of a widget."""

    LOADING = "loading"
    LOADED = "loaded"
    EMPTY = "empty"
    ERROR = "error"
    STALE = "stale"
    DISCONNECTED = "disconnected"


@dataclass
class StateDisplay:
    """Configuration for displaying a widget state."""

    icon: str
    color: str
    message: str
    submessage: str = ""

    def render(self) -> str:
        """Render the state display as a Rich markup string."""
        if self.submessage:
            return f"[{self.color}]{self.icon} {self.message}[/]\n[dim]{self.submessage}[/]"
        return f"[{self.color}]{self.icon} {self.message}[/]"


# Default state displays
LOADING_STATE = StateDisplay(
    icon=STATUS_SYMBOLS.get("circle_dotted", "◌"),
    color="dim",
    message="Loading...",
)

ERROR_STATE = StateDisplay(
    icon=STATUS_SYMBOLS.get("cross", "✗"),
    color="red",
    message="Error loading data",
)

EMPTY_STATE = StateDisplay(
    icon=STATUS_SYMBOLS.get("circle_empty", "○"),
    color="dim",
    message="No data available",
)

STALE_STATE = StateDisplay(
    icon=STATUS_SYMBOLS.get("warning", "⚠"),
    color="yellow",
    message="Data may be stale",
)

DISCONNECTED_STATE = StateDisplay(
    icon=STATUS_SYMBOLS.get("disconnect", "⊘"),
    color="red",
    message="Disconnected",
)


def render_loading(
    message: str = "Loading...",
    context: str | None = None,
) -> str:
    """Render a loading state.

    Args:
        message: Primary loading message.
        context: Optional context about what's loading.

    Returns:
        Rich markup string for the loading state.
    """
    icon = STATUS_SYMBOLS.get("circle_dotted", "◌")
    result = f"[dim]{icon} {message}[/]"
    if context:
        result += f"\n[dim italic]{context}[/]"
    return result


def render_error(
    error: str | None = None,
    error_type: str | None = None,
    retry_hint: bool = True,
    collector_name: str | None = None,
    gateway_hint: str | None = None,
) -> str:
    """Render an error state.

    Args:
        error: Error message to display.
        error_type: Category/type of error.
        retry_hint: Whether to show a retry hint.
        collector_name: Name of collector for last-success lookup.
        gateway_hint: Optional hint about gateway status/commands.

    Returns:
        Rich markup string for the error state.
    """
    icon = STATUS_SYMBOLS.get("cross", "✗")
    lines = []

    # Main error message
    if error:
        # Truncate long errors
        display_error = error if len(error) <= 60 else error[:57] + "..."
        if error_type:
            lines.append(f"[red]{icon} [{error_type}] {display_error}[/]")
        else:
            lines.append(f"[red]{icon} {display_error}[/]")
    else:
        lines.append(f"[red]{icon} Failed to load data[/]")

    # Show last successful time if available
    if collector_name:
        last = get_last_success(collector_name)
        if last:
            ago = _format_time_ago(last)
            lines.append(f"[dim]Last success: {ago}[/]")

    # Show gateway hint if provided
    if gateway_hint:
        lines.append("")
        lines.append(f"[dim]{gateway_hint}[/]")
    # Otherwise show retry hint
    elif retry_hint:
        lines.append("[dim italic]Press 'r' to refresh[/]")

    return "\n".join(lines)


def render_empty(
    message: str = "No data available",
    hint: str | None = None,
    icon: str | None = None,
) -> str:
    """Render an empty state.

    Args:
        message: Primary empty state message.
        hint: Optional hint about why it's empty or what to do.
        icon: Custom icon to use (default: empty circle).

    Returns:
        Rich markup string for the empty state.
    """
    icon = icon or STATUS_SYMBOLS.get("circle_empty", "○")
    result = f"[dim]{icon} {message}[/]"
    if hint:
        result += f"\n[dim italic]{hint}[/]"
    return result


def render_stale(
    collector_name: str,
    data_display: str | None = None,
    max_age_seconds: float = 300,
) -> str:
    """Render a stale data warning.

    Args:
        collector_name: Name of the collector.
        data_display: Optional display of stale data.
        max_age_seconds: Maximum age before data is considered stale.

    Returns:
        Rich markup string with stale warning.
    """
    icon = STATUS_SYMBOLS.get("warning", "⚠")
    last = get_last_success(collector_name)

    lines = []

    # Show stale warning
    if last:
        ago = _format_time_ago(last)
        lines.append(f"[yellow]{icon} Data from {ago}[/]")
    else:
        lines.append(f"[yellow]{icon} Data may be outdated[/]")

    # Show the stale data if provided
    if data_display:
        lines.append("")
        lines.append(f"[dim]{data_display}[/]")

    return "\n".join(lines)


def render_disconnected(
    service_name: str = "service",
    hint: str | None = None,
    show_gateway_hint: bool = True,
) -> str:
    """Render a disconnected state.

    The gateway runs locally, so connection issues are typically either:
    - Gateway not started yet
    - A bug (unexpected timeout or hang)

    Args:
        service_name: Name of the disconnected service.
        hint: Optional hint about how to reconnect.
        show_gateway_hint: Whether to show gateway start hint.

    Returns:
        Rich markup string for the disconnected state.
    """
    icon = STATUS_SYMBOLS.get("disconnect", "⊘")

    # Check if hint mentions timeout (likely a bug since gateway is local)
    is_timeout = hint and ("timeout" in hint.lower() or "timed out" in hint.lower())

    if is_timeout:
        lines = [f"[red]{icon} Command timed out unexpectedly[/]"]
        lines.append("[dim italic]The gateway runs locally — this may be a bug[/]")
        lines.append("[dim]Please report: github.com/dlorp/openclaw-dash/issues[/]")
    else:
        lines = [f"[red]{icon} Cannot connect to {service_name}[/]"]

        if hint:
            lines.append(f"[dim italic]{hint}[/]")

        # Suggest starting the gateway for gateway-related disconnections
        if show_gateway_hint and service_name.lower() in ("gateway", "service"):
            lines.append("")
            lines.append("[dim]Try: openclaw gateway start[/]")

    return "\n".join(lines)


def render_unavailable(
    feature_name: str,
    reason: str | None = None,
) -> str:
    """Render an unavailable feature state.

    Args:
        feature_name: Name of the unavailable feature.
        reason: Optional reason why it's unavailable.

    Returns:
        Rich markup string for the unavailable state.
    """
    icon = STATUS_SYMBOLS.get("circle_empty", "○")
    lines = [f"[dim]{icon} {feature_name} unavailable[/]"]

    if reason:
        lines.append(f"[dim italic]{reason}[/]")

    return "\n".join(lines)


def check_and_render_state(
    collector_name: str,
    data: dict[str, Any],
    empty_check: str | list[str] | None = None,
    max_stale_seconds: float = 300,
) -> tuple[WidgetState, str | None]:
    """Check data state and return appropriate render if needed.

    This is a helper for widgets to consistently handle state checking.

    Args:
        collector_name: Name of the collector.
        data: Data from the collector.
        empty_check: Key(s) to check for empty state.
        max_stale_seconds: Maximum age before stale warning.

    Returns:
        Tuple of (state, render_string_or_none).
        If render_string is not None, widget should display it instead of data.
    """
    # Check for error in data
    if data.get("_error") or data.get("error"):
        error_msg = data.get("_error") or data.get("error")
        error_type = data.get("_error_type")
        hint = data.get("_hint")
        return (
            WidgetState.ERROR,
            render_error(
                error=error_msg,
                error_type=error_type,
                collector_name=collector_name,
                gateway_hint=hint,
            ),
        )

    # Check for unavailable
    if data.get("available") is False:
        reason = data.get("error", "Required dependencies not installed")
        return (
            WidgetState.DISCONNECTED,
            render_unavailable(collector_name, reason=reason),
        )

    # Check for empty data
    if empty_check:
        keys = [empty_check] if isinstance(empty_check, str) else empty_check
        all_empty = all(not data.get(key) for key in keys)
        if all_empty:
            return (
                WidgetState.EMPTY,
                None,  # Let widget handle empty display
            )

    # Check for stale data
    if is_stale(collector_name, max_stale_seconds):
        # Don't return a render - let widget show data with stale indicator
        return (WidgetState.STALE, None)

    return (WidgetState.LOADED, None)


def get_state_indicator(
    collector_name: str,
    max_stale_seconds: float = 300,
) -> str:
    """Get a compact state indicator for a collector.

    Useful for adding state info to panel titles or headers.

    Args:
        collector_name: Name of the collector.
        max_stale_seconds: Maximum age before stale warning.

    Returns:
        A short Rich markup indicator string.
    """
    state = get_collector_state(collector_name)

    if state is None:
        return ""

    if state.has_error:
        return "[red]●[/]"

    if is_stale(collector_name, max_stale_seconds):
        return "[yellow]●[/]"

    return "[green]●[/]"


def _format_time_ago(dt: datetime) -> str:
    """Format a datetime as a relative time string.

    Args:
        dt: Datetime to format.

    Returns:
        Human-readable relative time string.
    """
    delta = datetime.now() - dt
    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"


def format_collector_status_line(
    collector_name: str,
    include_duration: bool = False,
) -> str:
    """Format a status line for a collector.

    Useful for debug displays or status panels.

    Args:
        collector_name: Name of the collector.
        include_duration: Whether to include collection duration.

    Returns:
        Rich markup string with collector status.
    """
    state = get_collector_state(collector_name)

    if state is None:
        return f"[dim]{collector_name}: not collected[/]"

    status_colors = {
        CollectorState.OK: "green",
        CollectorState.ERROR: "red",
        CollectorState.TIMEOUT: "yellow",
        CollectorState.UNAVAILABLE: "dim",
        CollectorState.STALE: "yellow",
    }

    color = status_colors.get(state.state, "white")
    status = state.state.value

    parts = [f"[{color}]{collector_name}: {status}[/]"]

    if include_duration and state.duration_ms > 0:
        parts.append(f"[dim]({state.duration_ms:.0f}ms)[/]")

    if state.error:
        short_error = state.error[:30] + "..." if len(state.error) > 30 else state.error
        parts.append(f"[dim]{short_error}[/]")

    return " ".join(parts)
