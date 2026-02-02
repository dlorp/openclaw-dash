"""Activity panel widget for displaying recent activity timeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import activity
from openclaw_dash.widgets.ascii_art import separator


class ActivityType(Enum):
    """Types of activity with associated icons."""

    GIT = "git"
    PR = "pr"
    CI = "ci"
    AGENT = "agent"
    TASK = "task"
    MESSAGE = "message"
    DEFAULT = "default"


# Icons for each activity type
ACTIVITY_ICONS = {
    ActivityType.GIT: "󰊢",      # git branch icon
    ActivityType.PR: "",       # pull request icon
    ActivityType.CI: "󰙨",       # test/CI icon
    ActivityType.AGENT: "󰚩",    # robot/agent icon
    ActivityType.TASK: "󰄬",     # checkbox/task icon
    ActivityType.MESSAGE: "󰍡",  # message icon
    ActivityType.DEFAULT: "●",   # bullet point
}

# Fallback ASCII icons for terminals without nerd fonts
ACTIVITY_ICONS_ASCII = {
    ActivityType.GIT: "⎇",       # branch symbol
    ActivityType.PR: "⤴",        # merge arrow
    ActivityType.CI: "⚙",        # gear
    ActivityType.AGENT: "◉",     # robot/agent
    ActivityType.TASK: "✓",      # checkmark
    ActivityType.MESSAGE: "✉",   # envelope
    ActivityType.DEFAULT: "●",   # bullet
}

# Colors for each activity type
ACTIVITY_COLORS = {
    ActivityType.GIT: "cyan",
    ActivityType.PR: "magenta",
    ActivityType.CI: "yellow",
    ActivityType.AGENT: "green",
    ActivityType.TASK: "blue",
    ActivityType.MESSAGE: "white",
    ActivityType.DEFAULT: "dim",
}


def get_activity_type(type_str: str | None) -> ActivityType:
    """Convert string type to ActivityType enum."""
    if not type_str:
        return ActivityType.DEFAULT
    try:
        return ActivityType(type_str.lower())
    except ValueError:
        return ActivityType.DEFAULT


def get_activity_icon(activity_type: ActivityType, ascii_mode: bool = True) -> str:
    """Get icon for activity type."""
    icons = ACTIVITY_ICONS_ASCII if ascii_mode else ACTIVITY_ICONS
    return icons.get(activity_type, ACTIVITY_ICONS_ASCII[ActivityType.DEFAULT])


def get_activity_color(activity_type: ActivityType) -> str:
    """Get color for activity type."""
    return ACTIVITY_COLORS.get(activity_type, "dim")


class ActivityPanel(Static):
    """Panel displaying recent activity timeline."""

    DEFAULT_CSS = """
    ActivityPanel {
        height: 100%;
    }
    """

    def __init__(self, max_items: int = 8, ascii_icons: bool = True, **kwargs) -> None:
        """Initialize the activity panel.

        Args:
            max_items: Maximum number of activity items to display
            ascii_icons: Use ASCII-compatible icons (default True)
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.max_items = max_items
        self.ascii_icons = ascii_icons

    def compose(self) -> ComposeResult:
        yield Static("Loading activity...", id="activity-content")

    def refresh_data(self) -> None:
        """Refresh activity data from collector."""
        data = activity.collect()
        content = self.query_one("#activity-content", Static)

        current_task = data.get("current_task")
        recent = data.get("recent", [])

        lines: list[str] = []

        # Show current task if exists
        if current_task:
            lines.append("[bold cyan]▶ Current Task[/]")
            # Truncate long tasks
            task_display = current_task[:40] + "…" if len(current_task) > 40 else current_task
            lines.append(f"  [white]{task_display}[/]")
            lines.append(separator(28, "dotted"))

        if not recent:
            if not current_task:
                content.update("[dim]No recent activity[/]")
                return
            content.update("\n".join(lines))
            return

        # Timeline header
        lines.append("[bold]Recent Activity[/]")
        lines.append("")

        # Display activity items with visual timeline
        for i, item in enumerate(recent[-self.max_items:][::-1]):  # Reverse to show newest first
            time_str = self._format_time(item.get("time", ""))
            action = item.get("action", "Unknown action")
            activity_type = get_activity_type(item.get("type"))

            icon = get_activity_icon(activity_type, self.ascii_icons)
            color = get_activity_color(activity_type)

            # Truncate long actions
            if len(action) > 35:
                action = action[:34] + "…"

            # Timeline connector
            is_last = i == min(len(recent), self.max_items) - 1
            connector = "└" if is_last else "│"

            # Build activity line with visual timeline
            lines.append(f"  [dim]{time_str}[/] [{color}]{icon}[/] {action}")
            if not is_last:
                lines.append(f"  [dim]       {connector}[/]")

        content.update("\n".join(lines))

    def _format_time(self, time_val: str | datetime) -> str:
        """Format time value for display.

        Args:
            time_val: Time as string (HH:MM or ISO format) or datetime

        Returns:
            Formatted time string (HH:MM)
        """
        if not time_val:
            return "??:??"

        # Handle datetime objects
        if isinstance(time_val, datetime):
            return time_val.strftime("%H:%M")

        # Handle string formats
        time_str = str(time_val)

        # Already in HH:MM format
        if len(time_str) == 5 and ":" in time_str:
            return time_str

        # ISO format: 2026-02-01T08:09:41.294Z or 2026-02-01T08:09:41
        if "T" in time_str:
            try:
                # Handle both Z suffix and no suffix
                clean_str = time_str.replace("Z", "+00:00")
                if "+" not in clean_str and len(clean_str) == 19:
                    clean_str = clean_str  # Local time, no TZ
                dt = datetime.fromisoformat(clean_str.split("+")[0])
                return dt.strftime("%H:%M")
            except (ValueError, TypeError):
                # Fallback: extract time portion
                time_part = time_str.split("T")[1][:5]
                return time_part

        return time_str[:5] if len(time_str) >= 5 else time_str


class ActivitySummaryPanel(Static):
    """Compact activity summary for metric boxes or header display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="activity-summary")

    def refresh_data(self) -> None:
        """Refresh activity summary."""
        data = activity.collect()
        content = self.query_one("#activity-summary", Static)

        current_task = data.get("current_task")
        recent = data.get("recent", [])

        if current_task:
            # Show truncated current task
            task_display = current_task[:25] + "…" if len(current_task) > 25 else current_task
            content.update(f"[cyan]▶[/] {task_display}")
            return

        if recent:
            # Show latest activity
            latest = recent[-1]
            action = latest.get("action", "")[:25]
            activity_type = get_activity_type(latest.get("type"))
            icon = get_activity_icon(activity_type)
            color = get_activity_color(activity_type)
            content.update(f"[{color}]{icon}[/] {action}")
            return

        content.update("[dim]No activity[/]")
