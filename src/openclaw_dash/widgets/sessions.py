"""Sessions panel widget for displaying active sessions with context burn rate."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import sessions
from openclaw_dash.widgets.ascii_art import mini_bar, separator


class SessionStatus(Enum):
    """Session status enum."""

    ACTIVE = "active"
    IDLE = "idle"
    SPAWNING = "spawning"
    UNKNOWN = "unknown"


def get_status_icon(status: str) -> str:
    """Get icon for session status."""
    icons = {
        "active": "●",
        "idle": "◐",
        "spawning": "◌",
        "unknown": "?",
    }
    return icons.get(status, "?")


def get_status_color(status: str) -> str:
    """Get color for session status."""
    colors = {
        "active": "green",
        "idle": "yellow",
        "spawning": "cyan",
        "unknown": "white",
    }
    return colors.get(status, "white")


def _calculate_time_active(updated_at_ms: float | None) -> str:
    """Calculate time active from updatedAt timestamp in milliseconds."""
    if updated_at_ms is None:
        return "?"

    try:
        updated_at = datetime.fromtimestamp(updated_at_ms / 1000)
        delta = datetime.now() - updated_at
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "just now"
        elif total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except (ValueError, OSError):
        return "?"


def _determine_status(session: dict[str, Any]) -> str:
    """Determine session status from session data."""
    if session.get("spawning"):
        return "spawning"
    if session.get("active", False):
        return "active"

    # Check last activity to determine idle vs active
    updated_at = session.get("updatedAt")
    if updated_at:
        try:
            updated = datetime.fromtimestamp(updated_at / 1000)
            idle_threshold = 300  # 5 minutes
            if (datetime.now() - updated).total_seconds() > idle_threshold:
                return "idle"
        except (ValueError, OSError):
            pass

    return "active"


def _calculate_context_pct(session: dict[str, Any]) -> float:
    """Calculate context usage percentage from session data."""
    # First check if already computed
    if "context_pct" in session:
        return session["context_pct"]

    # Calculate from tokens
    total_tokens = session.get("totalTokens", 0)
    context_tokens = session.get("contextTokens", 0)

    if context_tokens > 0:
        return (total_tokens / context_tokens) * 100

    # Fallback to contextUsage if available (0-1 scale)
    context_usage = session.get("contextUsage", 0)
    if context_usage:
        return context_usage * 100

    return 0.0


class SessionsPanel(Static):
    """Panel displaying active sessions with context burn rate."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="sessions-content")

    def refresh_data(self) -> None:
        """Refresh sessions data from collector."""
        data = sessions.collect()
        content = self.query_one("#sessions-content", Static)

        session_list = data.get("sessions", [])
        active = data.get("active", 0)
        total = data.get("total", 0)

        if not session_list:
            content.update("[dim]No active sessions[/]")
            return

        lines: list[str] = []

        # Header with count and ratio bar
        ratio = active / total if total > 0 else 0
        bar = mini_bar(ratio, width=8)
        lines.append(f"[bold]{active}[/]/{total} active {bar}")
        lines.append(separator(32, "dotted"))

        # Display each session (limit to first 8 for space)
        for session in session_list[:8]:
            status = _determine_status(session)
            name = session.get("displayName", session.get("key", "unknown"))

            # Truncate name if too long
            if len(name) > 18:
                name = name[:15] + "..."

            context_pct = _calculate_context_pct(session)
            time_active = _calculate_time_active(session.get("updatedAt"))
            kind = session.get("kind", "unknown")

            # Status icon and color
            icon = get_status_icon(status)
            color = get_status_color(status)

            # Context usage bar (visual)
            ctx_bar = mini_bar(context_pct / 100, width=10)

            # Build session line
            lines.append(f"  [{color}]{icon}[/] [bold]{name}[/]")
            lines.append(f"    Context: {ctx_bar} {context_pct:.1f}%")
            lines.append(f"    [dim]{kind} · ⏱ {time_active}[/]")

        # Show overflow indicator
        remaining = total - 8
        if remaining > 0:
            lines.append(f"   [dim]... and {remaining} more[/]")

        content.update("\n".join(lines))


class SessionsSummaryPanel(Static):
    """Compact sessions summary for metric boxes or header display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="sessions-summary")

    def refresh_data(self) -> None:
        """Refresh sessions summary."""
        data = sessions.collect()
        content = self.query_one("#sessions-summary", Static)

        total = data.get("total", 0)
        active = data.get("active", 0)

        if total == 0:
            content.update("[dim]No sessions[/]")
            return

        # Calculate average context usage
        session_list = data.get("sessions", [])
        if session_list:
            avg_ctx = sum(_calculate_context_pct(s) for s in session_list) / len(session_list)
        else:
            avg_ctx = 0

        # Color based on context usage
        if avg_ctx > 80:
            ctx_color = "red"
        elif avg_ctx > 60:
            ctx_color = "yellow"
        else:
            ctx_color = "green"

        bar = mini_bar(avg_ctx / 100, width=6)
        content.update(f"[green]●[/] {active}/{total} [{ctx_color}]{avg_ctx:.0f}%[/] {bar}")
