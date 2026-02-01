"""Logs panel widget for the TUI dashboard."""

from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import logs


class LogsPanel(Static):
    """Log viewer panel showing recent gateway logs."""

    DEFAULT_CSS = """
    LogsPanel {
        height: 100%;
    }
    """

    def __init__(self, n_lines: int = 15, **kwargs) -> None:
        """Initialize the logs panel.

        Args:
            n_lines: Number of log lines to display
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.n_lines = n_lines

    def compose(self) -> ComposeResult:
        yield Static("Loading logs...", id="logs-content")

    def refresh_data(self) -> None:
        """Refresh log data from collector."""
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
        """Format ISO timestamp to short time string."""
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
    """Compact logs summary showing error/warning counts."""

    def compose(self) -> ComposeResult:
        yield Static("", id="logs-summary")

    def refresh_data(self) -> None:
        """Refresh logs summary."""
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
