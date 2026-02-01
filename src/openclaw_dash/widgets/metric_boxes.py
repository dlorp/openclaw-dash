"""Compact KPI metric boxes for dashboard header area.

A horizontal bar of key performance indicators that displays at a glance:
- Gateway status (✓/✗ + uptime)
- Cost today ($X.XX with mini sparkline)
- Error rate (% with mini bar)
- Streak/uptime days

Uses dlorp's brand colors:
- #636764 Granite Gray
- #FB8B24 Dark Orange
- #F4E409 Titanium Yellow
- #50D8D7 Medium Turquoise
- #3B60E4 Royal Blue Light
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from openclaw_dash.collectors import gateway
from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    sparkline,
)

# Brand colors (for Rich markup)
COLORS = {
    "granite": "#636764",
    "orange": "#FB8B24",
    "yellow": "#F4E409",
    "turquoise": "#50D8D7",
    "blue": "#3B60E4",
}


class MetricBox(Static):
    """A single compact metric display box."""

    DEFAULT_CSS = """
    MetricBox {
        width: auto;
        min-width: 14;
        max-width: 22;
        height: 3;
        padding: 0 1;
        margin: 0 1 0 0;
        border: round $primary;
        background: $surface;
    }

    MetricBox.status-ok {
        border: round $success;
    }

    MetricBox.status-error {
        border: round $error;
    }

    MetricBox.status-warning {
        border: round $warning;
    }

    MetricBox.collapsed {
        display: none;
    }
    """

    def __init__(
        self,
        label: str,
        value: str = "...",
        detail: str = "",
        status: str | None = None,
        box_id: str | None = None,
        priority: int = 1,
    ) -> None:
        """Initialize a metric box.

        Args:
            label: Short label for the metric
            value: Main value to display
            detail: Optional detail line (sparkline, bar, etc.)
            status: Status class (ok, error, warning) for border color
            box_id: Widget ID
            priority: Priority for responsive collapse (1=high, keep visible)
        """
        super().__init__(id=box_id)
        self._label = label
        self._value = value
        self._detail = detail
        self._status = status
        self._priority = priority
        if status:
            self.add_class(f"status-{status}")

    def update_metric(
        self,
        value: str,
        detail: str = "",
        status: str | None = None,
    ) -> None:
        """Update the metric display."""
        self._value = value
        self._detail = detail

        # Update status class
        for cls in ["status-ok", "status-error", "status-warning"]:
            self.remove_class(cls)
        if status:
            self._status = status
            self.add_class(f"status-{status}")

        self._render()

    def _render(self) -> None:
        """Render the metric content."""
        lines = [
            f"[bold {COLORS['turquoise']}]{self._label}[/]",
            f"[bold]{self._value}[/]",
        ]
        if self._detail:
            lines.append(f"[dim]{self._detail}[/]")
        self.update("\n".join(lines))

    def on_mount(self) -> None:
        self._render()


class MetricBoxesBar(Static):
    """Horizontal bar of compact KPI metric boxes."""

    DEFAULT_CSS = """
    MetricBoxesBar {
        width: 100%;
        height: auto;
        min-height: 5;
        max-height: 5;
        padding: 0 1;
        margin-bottom: 1;
    }

    MetricBoxesBar Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
    }

    /* Responsive breakpoints */
    MetricBoxesBar.compact MetricBox.priority-3 {
        display: none;
    }

    MetricBoxesBar.narrow MetricBox.priority-2,
    MetricBoxesBar.narrow MetricBox.priority-3 {
        display: none;
    }

    MetricBoxesBar.minimal MetricBox.priority-2,
    MetricBoxesBar.minimal MetricBox.priority-3,
    MetricBoxesBar.minimal #metric-streak {
        display: none;
    }
    """

    # Width thresholds for responsive layout
    COMPACT_WIDTH = 100
    NARROW_WIDTH = 80
    MINIMAL_WIDTH = 60

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield MetricBox(
                label="Gateway",
                value="...",
                box_id="metric-gateway",
                priority=1,
            )
            yield MetricBox(
                label="Cost Today",
                value="...",
                box_id="metric-cost",
                priority=1,
            )
            yield MetricBox(
                label="Error Rate",
                value="...",
                box_id="metric-errors",
                priority=2,
            )
            yield MetricBox(
                label="Streak",
                value="...",
                box_id="metric-streak",
                priority=3,
            )

    def on_mount(self) -> None:
        """Initial data load and setup priority classes."""
        # Add priority classes to boxes for CSS-based responsive hiding
        for box in self.query(MetricBox):
            box.add_class(f"priority-{box._priority}")
        self.refresh_data()

    def on_resize(self, event) -> None:
        """Handle terminal resize for responsive layout."""
        self._apply_responsive_classes(event.size.width)

    def _apply_responsive_classes(self, width: int) -> None:
        """Apply responsive CSS classes based on width."""
        self.remove_class("compact", "narrow", "minimal")

        if width < self.MINIMAL_WIDTH:
            self.add_class("minimal")
        elif width < self.NARROW_WIDTH:
            self.add_class("narrow")
        elif width < self.COMPACT_WIDTH:
            self.add_class("compact")

    def refresh_data(self) -> None:
        """Refresh all metric boxes with current data."""
        self._refresh_gateway()
        self._refresh_cost()
        self._refresh_errors()
        self._refresh_streak()

    def _refresh_gateway(self) -> None:
        """Refresh gateway status metric."""
        try:
            box = self.query_one("#metric-gateway", MetricBox)
            data = gateway.collect()

            if data.get("healthy"):
                uptime = data.get("uptime", "?")
                # Parse uptime for compact display
                if isinstance(uptime, str) and uptime != "?":
                    uptime_display = uptime[:10]  # Truncate if too long
                else:
                    uptime_display = uptime
                box.update_metric(
                    value=f"{STATUS_SYMBOLS['ok']} Online",
                    detail=f"↑ {uptime_display}",
                    status="ok",
                )
            else:
                error = data.get("error", "Offline")[:15]
                box.update_metric(
                    value=f"{STATUS_SYMBOLS['error']} Down",
                    detail=error,
                    status="error",
                )
        except Exception:
            pass

    def _refresh_cost(self) -> None:
        """Refresh cost today metric with sparkline."""
        try:
            box = self.query_one("#metric-cost", MetricBox)
            tracker = CostTracker()
            data = tracker.collect()

            today = data.get("today", {})
            trend = data.get("trend", {})

            cost = today.get("cost", 0)
            cost_display = f"${cost:.2f}" if cost >= 0.01 else f"${cost:.4f}"

            # Build mini sparkline from trend data
            costs = trend.get("costs", [])
            if costs and len(costs) > 1:
                # Reverse since trend is newest-first
                spark = sparkline(list(reversed(costs)), width=6)
                detail = spark
            else:
                detail = ""

            # Color based on cost level
            status = None
            if cost > 5.0:
                status = "warning"
            elif cost > 10.0:
                status = "error"

            box.update_metric(value=cost_display, detail=detail, status=status)
        except Exception:
            pass

    def _refresh_errors(self) -> None:
        """Refresh error rate metric with mini bar."""
        try:
            box = self.query_one("#metric-errors", MetricBox)
            perf = PerformanceMetrics()
            data = perf.collect()

            summary = data.get("summary", {})
            error_rate = summary.get("error_rate_pct", 0)
            total_errors = summary.get("total_errors", 0)

            # Error bar visualization
            bar = mini_bar(min(error_rate / 100, 1.0), width=6)

            # Status based on error rate
            if error_rate >= 10:
                status = "error"
            elif error_rate >= 5:
                status = "warning"
            else:
                status = "ok"

            box.update_metric(
                value=f"{error_rate:.1f}%",
                detail=f"{bar} ({total_errors})",
                status=status,
            )
        except Exception:
            pass

    def _refresh_streak(self) -> None:
        """Refresh streak/uptime days metric."""
        try:
            box = self.query_one("#metric-streak", MetricBox)
            gh = GitHubMetrics()
            data = gh.collect()

            streak = data.get("streak", {})
            streak_days = streak.get("streak_days", 0)

            # Fire emoji based on streak length
            if streak_days >= 30:
                icon = STATUS_SYMBOLS["fire"] * 3
            elif streak_days >= 7:
                icon = STATUS_SYMBOLS["fire"] * 2
            elif streak_days > 0:
                icon = STATUS_SYMBOLS["fire"]
            else:
                icon = STATUS_SYMBOLS["snowflake"]

            # Get recent commit activity for sparkline
            commit_history = data.get("commit_history", [])
            if commit_history and len(commit_history) > 1:
                commits = [d.get("commits", 0) for d in commit_history[-7:]]
                spark = sparkline(commits, width=5)
                detail = spark
            else:
                detail = ""

            box.update_metric(
                value=f"{streak_days}d {icon}",
                detail=detail,
            )
        except Exception:
            pass


def format_uptime_compact(uptime: str) -> str:
    """Format uptime string to compact display.

    Examples:
        "5h 23m 15s" -> "5h 23m"
        "2d 5h 23m" -> "2d 5h"
        "23m 15s" -> "23m"
    """
    if not uptime or uptime in ("?", "unknown"):
        return "?"

    # Keep first two components
    parts = uptime.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return uptime
