"""Gateway status widget for displaying OpenClaw gateway health and metrics.

This module provides a Textual widget that displays real-time gateway
status including connection health, uptime, active sessions, model in use,
and total token usage. Uses a phosphor amber aesthetic on dark backgrounds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Static

from openclaw_dash.collectors import gateway, sessions
from openclaw_dash.widgets.ascii_art import STATUS_SYMBOLS, mini_bar, separator

# Phosphor amber colors for the aesthetic
AMBER = "#FFB000"  # Primary amber
AMBER_DIM = "#CC8800"  # Dimmed amber
AMBER_BRIGHT = "#FFD54F"  # Bright/highlight amber


class ConnectionStatus:
    """Connection status enum-like class."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"


def get_connection_icon(status: str) -> str:
    """Get icon for connection status.

    Args:
        status: The connection status string.

    Returns:
        A Unicode icon character representing the status.
    """
    icons = {
        ConnectionStatus.CONNECTED: "●",
        ConnectionStatus.DISCONNECTED: "○",
        ConnectionStatus.CONNECTING: "◐",
    }
    return icons.get(status, "?")


def get_connection_color(status: str) -> str:
    """Get color for connection status.

    Uses amber palette for connected states, red for disconnected.

    Args:
        status: The connection status string.

    Returns:
        A color string for Rich/Textual markup.
    """
    colors = {
        ConnectionStatus.CONNECTED: AMBER,
        ConnectionStatus.DISCONNECTED: "red",
        ConnectionStatus.CONNECTING: AMBER_DIM,
    }
    return colors.get(status, "white")


def _format_uptime(started_at: datetime | str | None) -> str:
    """Format uptime from a start timestamp.

    Args:
        started_at: When the gateway started, as datetime or ISO string.

    Returns:
        Human-readable uptime string (e.g., "2h 15m", "3d 4h").
    """
    if started_at is None:
        return "—"

    try:
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))

        delta = datetime.now() - started_at.replace(tzinfo=None)
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "just started"
        elif total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    except (ValueError, AttributeError, TypeError):
        return "—"


def _format_tokens(tokens: int) -> str:
    """Format token count for display.

    Args:
        tokens: Number of tokens.

    Returns:
        Formatted string (e.g., "45.2k", "1.2M").
    """
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1_000_000:
        return f"{tokens / 1000:.1f}k"
    else:
        return f"{tokens / 1_000_000:.2f}M"


def _calculate_total_tokens(sessions_data: dict[str, Any]) -> int:
    """Calculate total tokens used across all sessions.

    Args:
        sessions_data: Sessions data from collector.

    Returns:
        Total token count.
    """
    session_list = sessions_data.get("sessions", [])
    total = 0
    for session in session_list:
        total += session.get("totalTokens", 0)
    return total


class GatewayStatusWidget(Static):
    """Widget displaying OpenClaw gateway status with phosphor amber aesthetic.

    Polls the gateway API and displays:
    - Connection status (connected/disconnected)
    - Uptime
    - Active sessions count
    - Model in use
    - Total tokens used

    The widget refreshes at a configurable interval (default 10 seconds)
    and uses an amber-on-dark color scheme.
    """

    DEFAULT_CSS = """
    GatewayStatusWidget {
        background: #1A1A1A;
        color: #FFB000;
        padding: 1;
        border: solid #FFB000;
    }

    GatewayStatusWidget .title {
        text-style: bold;
        color: #FFD54F;
    }

    GatewayStatusWidget .dim {
        color: #CC8800;
    }

    GatewayStatusWidget .error {
        color: #FF5252;
    }
    """

    refresh_interval: reactive[float] = reactive(10.0)
    gateway_url: reactive[str] = reactive("localhost:18789")

    def __init__(
        self,
        refresh_interval: float = 10.0,
        gateway_url: str = "localhost:18789",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the gateway status widget.

        Args:
            refresh_interval: Seconds between refreshes (default 10).
            gateway_url: Gateway URL for display (default localhost:18789).
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        # Initialize instance attrs before super().__init__ to avoid
        # AttributeError from reactive watchers during initialization
        self._refresh_timer: Timer | None = None
        self._last_healthy_at: datetime | None = None
        super().__init__(name=name, id=id, classes=classes)
        self.refresh_interval = refresh_interval
        self.gateway_url = gateway_url

    def compose(self) -> ComposeResult:
        """Compose the widget's child widgets.

        Yields:
            A Static widget for displaying gateway status content.
        """
        yield Static("Loading...", id="gateway-status-content")

    def on_mount(self) -> None:
        """Handle widget mount - start the refresh timer."""
        self.refresh_data()
        self._refresh_timer = self.set_interval(
            self.refresh_interval,
            self.refresh_data,
        )

    def on_unmount(self) -> None:
        """Handle widget unmount - stop the refresh timer."""
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None

    def watch_refresh_interval(self, new_interval: float) -> None:
        """React to refresh interval changes.

        Args:
            new_interval: New refresh interval in seconds.
        """
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = self.set_interval(new_interval, self.refresh_data)

    def refresh_data(self) -> None:
        """Refresh gateway status data from collectors.

        Fetches gateway and session data, then updates the display
        with current status, metrics, and visual indicators.
        """
        gateway_data = gateway.collect()
        sessions_data = sessions.collect()
        content = self.query_one("#gateway-status-content", Static)

        # Determine connection status
        is_healthy = gateway_data.get("healthy", False)
        if is_healthy:
            connection_status = ConnectionStatus.CONNECTED
            self._last_healthy_at = datetime.now()
        else:
            connection_status = ConnectionStatus.DISCONNECTED

        lines: list[str] = []

        # Header with connection status
        icon = get_connection_icon(connection_status)
        color = get_connection_color(connection_status)
        status_text = "CONNECTED" if is_healthy else "DISCONNECTED"
        lines.append(f"[{color}]{icon}[/] [{AMBER_BRIGHT}]Gateway[/] [{color}]{status_text}[/]")
        lines.append(separator(36, "dotted"))

        if not is_healthy:
            # Show error state with helpful message
            error = gateway_data.get("error", "Cannot connect to gateway")
            hint = gateway_data.get("_hint", "")

            lines.append("")
            lines.append(f"[red]{STATUS_SYMBOLS.get('cross', '✗')} {error}[/]")

            if hint:
                lines.append(f"[dim]{hint}[/]")

            # Show last healthy time if available
            if self._last_healthy_at:
                uptime = _format_uptime(self._last_healthy_at)
                lines.append("")
                lines.append(f"[{AMBER_DIM}]Last seen: {uptime} ago[/]")

            content.update("\n".join(lines))
            return

        # Connected - show full status

        # Uptime (from last healthy or service start)
        uptime = _format_uptime(self._last_healthy_at)
        lines.append(f"  [{AMBER}]TIME[/]  Uptime      [{AMBER_BRIGHT}]{uptime}[/]")

        # Active sessions
        active = sessions_data.get("active", 0)
        total = sessions_data.get("total", 0)
        session_bar = mini_bar(active / max(total, 1), width=6)
        lines.append(
            f"  [{AMBER}]◉[/]  Sessions    [{AMBER_BRIGHT}]{active}[/]/{total} {session_bar}"
        )

        # Model in use
        model = gateway_data.get("default_model", "—")
        if len(model) > 20:
            model = model[:17] + "..."
        lines.append(f"  [{AMBER}]◆[/]  Model       [{AMBER_BRIGHT}]{model}[/]")

        # Total tokens used
        total_tokens = _calculate_total_tokens(sessions_data)
        tokens_display = _format_tokens(total_tokens)
        lines.append(f"  [{AMBER}]≡[/]  Tokens      [{AMBER_BRIGHT}]{tokens_display}[/]")

        # Gateway URL (dimmed)
        lines.append("")
        url = gateway_data.get("url", self.gateway_url)
        if url and len(url) > 30:
            url = url[:27] + "..."
        lines.append(f"[{AMBER_DIM}]└ {url}[/]")

        content.update("\n".join(lines))


class GatewayStatusSummary(Static):
    """Compact gateway status summary for metric boxes or headers.

    Provides a single-line view of gateway health suitable for
    inclusion in dashboard headers or compact displays.
    """

    refresh_interval: reactive[float] = reactive(10.0)

    def __init__(
        self,
        refresh_interval: float = 10.0,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the gateway status summary.

        Args:
            refresh_interval: Seconds between refreshes (default 10).
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        # Initialize instance attrs before super().__init__ to avoid
        # AttributeError from reactive watchers during initialization
        self._refresh_timer: Timer | None = None
        super().__init__(name=name, id=id, classes=classes)
        self.refresh_interval = refresh_interval

    def compose(self) -> ComposeResult:
        """Compose the widget's child widgets.

        Yields:
            A Static widget for displaying the summary.
        """
        yield Static("", id="gateway-summary")

    def on_mount(self) -> None:
        """Handle widget mount - start the refresh timer."""
        self.refresh_data()
        self._refresh_timer = self.set_interval(
            self.refresh_interval,
            self.refresh_data,
        )

    def on_unmount(self) -> None:
        """Handle widget unmount - stop the refresh timer."""
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None

    def refresh_data(self) -> None:
        """Refresh the gateway summary display.

        Collects gateway data and renders a compact summary with
        connection status and key metrics.
        """
        gateway_data = gateway.collect()
        sessions_data = sessions.collect()
        content = self.query_one("#gateway-summary", Static)

        is_healthy = gateway_data.get("healthy", False)
        icon = get_connection_icon(
            ConnectionStatus.CONNECTED if is_healthy else ConnectionStatus.DISCONNECTED
        )
        color = get_connection_color(
            ConnectionStatus.CONNECTED if is_healthy else ConnectionStatus.DISCONNECTED
        )

        if not is_healthy:
            content.update(f"[{color}]{icon}[/] Gateway offline")
            return

        # Show: icon sessions model tokens
        active = sessions_data.get("active", 0)
        model = gateway_data.get("default_model", "—")
        if len(model) > 12:
            model = model[:9] + "..."

        total_tokens = _calculate_total_tokens(sessions_data)
        tokens_display = _format_tokens(total_tokens)

        content.update(f"[{color}]{icon}[/] {active} sessions · {model} · {tokens_display}")
