"""Logs panel widget for the TUI dashboard.

This module provides widgets for displaying gateway logs with color-coded
log levels and relative timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import logs


class LogsPanel(Static):
    """Log viewer panel showing recent gateway logs.

    Displays recent log entries with:
    - Color-coded log levels (error, warning, info, debug)
    - Timestamps formatted as time-only
    - Source tags
    - Truncated message content
    """

    DEFAULT_CSS = """
    LogsPanel {
        height: 100%;
    }
    """

    def __init__(self, n_lines: int = 15, **kwargs: Any) -> None:
        """Initialize the logs panel.

        Args:
            n_lines: Number of log lines to display.
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__(**kwargs)
        self.n_lines = n_lines

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying log content.
        """
        yield Static("Loading logs...", id="logs-content")

    def refresh_data(self) -> None:
        """Refresh log data from the collector.

        Fetches recent log entries and updates the display with
        color-coded levels and formatted timestamps.
        """
        data = logs.collect(n=self.n_lines)
        content = self.query_one("#logs-content", Static)

        entries = data.get("entries", [])

        if data.get("error"):
            content.update(f"[red]✗ {data['error']}[/]")
            return

        if not entries:
            content.update("[dim]No log entries[/]")
            return

        lines: list[str] = []

        # Show level summary in header
        levels = data.get("levels", {})
        summary_parts = []
        if levels.get("error", 0):
            summary_parts.append(f"[red]{levels['error']} err[/]")
        if levels.get("warning", 0):
            summary_parts.append(f"[yellow]{levels['warning']} warn[/]")
        if summary_parts:
            lines.append(" ".join(summary_parts))
            lines.append("")

        # Display log entries
        for entry in entries:
            timestamp = entry.get("timestamp", "")
            tag = entry.get("tag", "")
            message = entry.get("message", "")
            level = entry.get("level", "debug")

            # Format timestamp as time only
            time_str = self._format_time(timestamp)

            # Get styling
            color = logs.get_level_color(level)
            icon = logs.get_level_icon(level)

            # Truncate message for display
            max_msg_len = 50
            if len(message) > max_msg_len:
                message = message[: max_msg_len - 1] + "…"

            # Format line
            lines.append(
                f"[dim]{time_str}[/] [{color}]{icon}[/] "
                f"[bold dim]{tag[:12]}[/] [{color}]{message}[/]"
            )

        content.update("\n".join(lines))

    def _format_time(self, timestamp: str) -> str:
        """Format ISO timestamp to short time string.

        Args:
            timestamp: ISO format timestamp string (e.g., "2026-02-01T08:09:41.294Z").

        Returns:
            Short time string in HH:MM:SS format, or "??:??" if parsing fails.
        """
        if not timestamp:
            return "??:??"

        try:
            # Parse ISO format: 2026-02-01T08:09:41.294Z
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            # Fallback: extract time portion
            if "T" in timestamp:
                time_part = timestamp.split("T")[1][:8]
                return time_part
            return timestamp[:8]


class LogsSummaryPanel(Static):
    """Compact logs summary showing error/warning counts.

    Provides a condensed view of log status suitable for inclusion
    in dashboard headers, showing error and warning counts.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying the summary.
        """
        yield Static("", id="logs-summary")

    def refresh_data(self) -> None:
        """Refresh the logs summary display.

        Collects recent log data and renders a compact summary with
        error/warning counts and the most recent issue message.
        """
        data = logs.collect(n=50)
        content = self.query_one("#logs-summary", Static)

        if data.get("error"):
            content.update(f"[dim]✗ {data['error'][:20]}[/]")
            return

        levels = data.get("levels", {})
        errors = levels.get("error", 0)
        warnings = levels.get("warning", 0)

        if errors == 0 and warnings == 0:
            content.update("[green]✓ No issues[/]")
            return

        parts = []
        if errors:
            parts.append(f"[red]✗ {errors}[/]")
        if warnings:
            parts.append(f"[yellow]⚠ {warnings}[/]")

        # Show most recent error/warning
        entries = data.get("entries", [])
        for entry in reversed(entries):
            if entry.get("level") in ("error", "warning"):
                msg = entry.get("message", "")[:30]
                parts.append(f"[dim]→ {msg}[/]")
                break

        content.update(" ".join(parts))
