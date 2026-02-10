"""Alerts panel widget for the TUI dashboard.

This module provides widgets for displaying system alerts and notifications
with color-coded severity levels (critical, high, medium, low).
"""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import alerts


class AlertsPanel(Static):
    """Alerts display panel with color-coded severity.

    Displays a list of system alerts with visual indicators for severity,
    source information, and relative timestamps.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying alert content.
        """
        yield Static("Loading...", id="alerts-content")

    def refresh_data(self) -> None:
        """Refresh alert data from collectors.

        Fetches the latest alerts and updates the display with
        severity-coded entries and summary counts.
        """
        data = alerts.collect()
        content = self.query_one("#alerts-content", Static)

        alert_list = data.get("alerts", [])
        summary = data.get("summary", {})

        if not alert_list:
            content.update("[green]✓ No alerts[/]")
            return

        lines: list[str] = []

        # Summary header
        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)

        summary_parts = []
        if critical:
            summary_parts.append(f"[red]{critical} critical[/]")
        if high:
            summary_parts.append(f"[red]{high} high[/]")
        if medium:
            summary_parts.append(f"[yellow]{medium} medium[/]")

        if summary_parts:
            lines.append(" • ".join(summary_parts))
            lines.append("")

        # Show alerts (limit to first 8 for space)
        for alert in alert_list[:8]:
            severity = alert.get("severity", "info")
            title = alert.get("title", "Unknown")[:40]
            source = alert.get("source", "?")
            timestamp = alert.get("timestamp", "")

            # Format timestamp as relative time
            time_str = self._format_time(timestamp)

            # Get color based on severity
            color = alerts.get_severity_color(severity)
            icon = alerts.get_severity_icon(severity)

            # Build alert line
            lines.append(f"{icon} [{color}]{title}[/]")
            lines.append(f"   [dim]{source} • {time_str}[/]")

        # Show overflow indicator
        remaining = len(alert_list) - 8
        if remaining > 0:
            lines.append(f"   [dim]... and {remaining} more[/]")

        content.update("\n".join(lines))

    def _format_time(self, timestamp: str) -> str:
        """Format timestamp as relative time.

        Args:
            timestamp: ISO format timestamp string.

        Returns:
            Human-readable relative time string (e.g., "5m ago", "2h ago").
        """
        if not timestamp:
            return "?"

        try:
            dt = datetime.fromisoformat(timestamp)
            now = datetime.now()
            delta = now - dt

            if delta.total_seconds() < 60:
                return "just now"
            elif delta.total_seconds() < 3600:
                mins = int(delta.total_seconds() / 60)
                return f"{mins}m ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                return f"{hours}h ago"
            else:
                days = int(delta.total_seconds() / 86400)
                return f"{days}d ago"
        except (ValueError, TypeError):
            return timestamp[:10] if len(timestamp) > 10 else timestamp


class AlertsSummaryPanel(Static):
    """Compact alerts summary for the main dashboard.

    Provides a condensed view of alert status suitable for inclusion
    in dashboard headers, showing counts by severity level.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying the summary.
        """
        yield Static("", id="alerts-summary")

    def refresh_data(self) -> None:
        """Refresh the alert summary display.

        Collects alert data and renders a compact summary with
        severity counts and the first alert title.
        """
        data = alerts.collect(
            include_ci=True,
            include_security=True,
            include_context=True,
        )
        content = self.query_one("#alerts-summary", Static)

        alert_list = data.get("alerts", [])
        summary = data.get("summary", {})

        if not alert_list:
            content.update("[green]✓ All clear[/]")
            return

        # Build compact summary
        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)

        parts = []
        if critical:
            parts.append(f"[bold red]CRITICAL {critical}[/]")
        if high:
            parts.append(f"[red]HIGH {high}[/]")
        if medium:
            parts.append(f"[yellow]MEDIUM {medium}[/]")

        # Show first alert title
        if alert_list:
            first = alert_list[0]
            title = first.get("title", "")[:35]
            parts.append(f"[dim]→ {title}[/]")

        content.update(" ".join(parts))
