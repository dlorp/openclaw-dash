"""Cron jobs panel widget for displaying scheduled jobs and their status."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import cron
from openclaw_dash.widgets.ascii_art import mini_bar, separator


def format_schedule(schedule: dict) -> str:
    """Format schedule dict into human-readable string."""
    if not schedule:
        return "?"

    kind = schedule.get("kind", "")
    if kind == "cron":
        expr = schedule.get("expr", "?")
        return f"⏰ {expr}"
    elif kind == "every":
        every_ms = schedule.get("everyMs", 0)
        if every_ms >= 3600000:
            return f"↻ {every_ms // 3600000}h"
        elif every_ms >= 60000:
            return f"↻ {every_ms // 60000}m"
        elif every_ms >= 1000:
            return f"↻ {every_ms // 1000}s"
        else:
            return f"↻ {every_ms}ms"
    elif kind == "at":
        at_time = schedule.get("at", "?")
        return f"@ {at_time}"
    else:
        return str(schedule)[:12]


def format_relative_time(iso_time: str | None) -> str:
    """Format ISO time as relative time string."""
    if not iso_time:
        return "never"

    try:
        # Handle both ISO format and timestamp
        if isinstance(iso_time, (int, float)):
            dt = datetime.fromtimestamp(iso_time / 1000 if iso_time > 1e10 else iso_time)
        else:
            # Remove 'Z' suffix and handle timezone
            clean_time = iso_time.replace("Z", "+00:00")
            if "+" not in clean_time and "-" not in clean_time[10:]:
                dt = datetime.fromisoformat(clean_time)
            else:
                dt = datetime.fromisoformat(clean_time).replace(tzinfo=None)

        now = datetime.now()
        delta = now - dt

        if delta.total_seconds() < 0:
            # Future time
            delta = -delta
            if delta.total_seconds() < 60:
                return f"in {int(delta.total_seconds())}s"
            elif delta.total_seconds() < 3600:
                return f"in {int(delta.total_seconds() // 60)}m"
            elif delta.total_seconds() < 86400:
                return f"in {int(delta.total_seconds() // 3600)}h"
            else:
                return f"in {int(delta.total_seconds() // 86400)}d"
        else:
            # Past time
            if delta.total_seconds() < 60:
                return f"{int(delta.total_seconds())}s ago"
            elif delta.total_seconds() < 3600:
                return f"{int(delta.total_seconds() // 60)}m ago"
            elif delta.total_seconds() < 86400:
                return f"{int(delta.total_seconds() // 3600)}h ago"
            else:
                return f"{int(delta.total_seconds() // 86400)}d ago"
    except (ValueError, TypeError):
        return "?"


def get_status_icon(status: str) -> str:
    """Get icon for job status."""
    icons = {
        "ok": "✓",
        "success": "✓",
        "running": "⟳",
        "failed": "✗",
        "error": "✗",
        "pending": "◐",
        "disabled": "○",
    }
    return icons.get(status.lower(), "?")


def get_status_color(status: str) -> str:
    """Get color for job status."""
    colors = {
        "ok": "green",
        "success": "green",
        "running": "cyan",
        "failed": "red",
        "error": "red",
        "pending": "yellow",
        "disabled": "dim",
    }
    return colors.get(status.lower(), "white")


class CronPanel(Static):
    """Panel displaying scheduled cron jobs and their execution status."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="cron-content")

    def refresh_data(self) -> None:
        """Refresh cron job data from collector."""
        data = cron.collect()
        content = self.query_one("#cron-content", Static)

        jobs = data.get("jobs", [])
        total = data.get("total", len(jobs))
        enabled = data.get("enabled", sum(1 for j in jobs if j.get("enabled", True)))

        if not jobs:
            content.update("[dim]No cron jobs scheduled[/]")
            return

        lines: list[str] = []

        # Header with counts
        ratio = enabled / total if total > 0 else 0
        bar = mini_bar(ratio, width=8)
        lines.append(f"[bold]{enabled}[/]/{total} enabled {bar}")
        lines.append(separator(30, "dotted"))

        # Display each job (limit for space)
        for job in jobs[:6]:
            job_name = job.get("name", job.get("id", "unnamed"))[:16]
            schedule = job.get("schedule", {})
            enabled_flag = job.get("enabled", True)

            # Handle both snake_case and camelCase from collector/mock
            last_run = job.get("last_run") or job.get("lastRun")
            next_run = job.get("next_run") or job.get("nextRun")

            # Determine status from last run
            last_status = job.get("last_status", job.get("lastStatus", "ok"))
            if not last_run:
                last_status = "pending"

            if not enabled_flag:
                status = "disabled"
            else:
                status = last_status

            # Format schedule
            schedule_str = format_schedule(schedule)

            # Status icon and color
            icon = get_status_icon(status)
            color = get_status_color(status)

            # Build job display
            lines.append(f"  [{color}]{icon}[/] [bold]{job_name}[/]")
            lines.append(f"    {schedule_str}")

            # Last run info
            if last_run:
                last_time = format_relative_time(last_run)
                status_str = f"[{color}]{last_status}[/]" if last_status else ""
                lines.append(f"    [dim]Last:[/] {last_time} {status_str}")
            else:
                lines.append("    [dim]Last: never[/]")

            # Next run info
            if next_run and enabled_flag:
                next_time = format_relative_time(next_run)
                lines.append(f"    [dim]Next:[/] {next_time}")

        # Show overflow indicator
        remaining = len(jobs) - 6
        if remaining > 0:
            lines.append(f"   [dim]... and {remaining} more[/]")

        content.update("\n".join(lines))


class CronSummaryPanel(Static):
    """Compact cron summary for metric boxes or header display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="cron-summary")

    def refresh_data(self) -> None:
        """Refresh cron summary."""
        data = cron.collect()
        content = self.query_one("#cron-summary", Static)

        jobs = data.get("jobs", [])
        total = len(jobs)

        if total == 0:
            content.update("[dim]No jobs[/]")
            return

        # Count enabled/disabled
        enabled = sum(1 for j in jobs if j.get("enabled", True))

        # Count by last status
        ok_count = 0
        failed_count = 0
        for job in jobs:
            last_status = job.get("last_status", job.get("lastStatus", ""))
            if last_status in ("ok", "success"):
                ok_count += 1
            elif last_status in ("failed", "error"):
                failed_count += 1

        parts = []
        parts.append(f"[bold]{enabled}[/]/{total}")
        if ok_count:
            parts.append(f"[green]✓{ok_count}[/]")
        if failed_count:
            parts.append(f"[red]✗{failed_count}[/]")

        content.update(" ".join(parts))
