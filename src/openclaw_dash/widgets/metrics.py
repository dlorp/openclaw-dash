"""Metrics panel widget for the TUI dashboard."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    separator,
    sparkline,
)


class CostsPanel(Static):
    """Token costs display."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="costs-content")

    def refresh_data(self) -> None:
        tracker = CostTracker()
        data = tracker.collect()
        content = self.query_one("#costs-content", Static)

        today = data.get("today", {})
        summary = data.get("summary", {})
        daily_history = data.get("daily_costs", [])

        # Build sparkline from daily history if available
        cost_values = [d.get("cost", 0) for d in daily_history[-14:]] if daily_history else []

        lines = []

        # Today's cost with sparkline
        today_cost = today.get("cost", 0)
        if cost_values:
            spark = sparkline(cost_values, width=12)
            lines.append(f"[bold]{STATUS_SYMBOLS['diamond']} Today:[/] ${today_cost:.4f}  {spark}")
        else:
            lines.append(f"[bold]{STATUS_SYMBOLS['diamond']} Today:[/] ${today_cost:.4f}")

        lines.append(
            f"  {STATUS_SYMBOLS['arrow_right']} Input: {today.get('input_tokens', 0):,} tokens"
        )
        lines.append(
            f"  {STATUS_SYMBOLS['arrow_right']} Output: {today.get('output_tokens', 0):,} tokens"
        )

        lines.append(separator(30, style="dotted"))

        lines.append(
            f"[bold]{STATUS_SYMBOLS['star']} All time:[/] ${summary.get('total_cost', 0):.2f}"
        )
        lines.append(f"  Avg daily: ${summary.get('avg_daily_cost', 0):.2f}")

        # Model breakdown with mini bars
        by_model = today.get("by_model", {})
        if by_model:
            lines.append("")
            lines.append(separator(30, style="thin", label="By Model"))
            total_model_cost = sum(s.get("cost", 0) for s in by_model.values())
            for model, stats in sorted(
                by_model.items(), key=lambda x: x[1].get("cost", 0), reverse=True
            )[:3]:
                cost = stats.get("cost", 0)
                ratio = cost / total_model_cost if total_model_cost > 0 else 0
                bar = mini_bar(ratio, width=6)
                lines.append(f"  {bar} {model}: ${cost:.4f}")

        content.update("\n".join(lines))


class PerformancePanel(Static):
    """Performance metrics display."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="perf-content")

    def refresh_data(self) -> None:
        perf = PerformanceMetrics()
        data = perf.collect()
        content = self.query_one("#perf-content", Static)

        summary = data.get("summary", {})

        lines = [
            f"[bold]Calls:[/] {summary.get('total_calls', 0):,}",
            f"[bold]Errors:[/] {summary.get('total_errors', 0)} ({summary.get('error_rate_pct', 0):.1f}%)",
            f"[bold]Avg latency:[/] {summary.get('avg_latency_ms', 0):.0f}ms",
        ]

        # Slowest actions
        slowest = data.get("slowest", [])[:3]
        if slowest:
            lines.append("")
            lines.append("[dim]Slowest:[/]")
            for item in slowest:
                lines.append(f"  {item['name']}: {item['avg_ms']:.0f}ms")

        # Error-prone
        errors = data.get("error_prone", [])[:2]
        if errors:
            lines.append("")
            lines.append("[dim]Error prone:[/]")
            for item in errors:
                lines.append(f"  [yellow]{item['name']}[/]: {item['error_rate']:.1f}%")

        content.update("\n".join(lines))


class GitHubPanel(Static):
    """GitHub metrics display."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="github-content")

    def refresh_data(self) -> None:
        gh = GitHubMetrics()
        data = gh.collect()
        content = self.query_one("#github-content", Static)

        streak = data.get("streak", {})
        pr = data.get("pr_metrics", {})

        # Streak display with fire emoji based on length
        streak_days = streak.get("streak_days", 0)
        if streak_days >= 30:
            streak_icon = "🔥🔥🔥"
        elif streak_days >= 7:
            streak_icon = "🔥🔥"
        elif streak_days > 0:
            streak_icon = "🔥"
        else:
            streak_icon = "❄️"

        lines = [
            f"[bold]Streak:[/] {streak_days} days {streak_icon}",
        ]

        if streak.get("username"):
            lines.append(f"  [dim]@{streak['username']}[/]")

        lines.extend(
            [
                "",
                f"[bold]PR Cycle:[/] {pr.get('avg_cycle_hours', 0):.1f}h avg",
                f"  Fastest: {pr.get('fastest_merge_hours', 0) or 0:.1f}h",
                f"  Slowest: {pr.get('slowest_merge_hours', 0) or 0:.1f}h",
            ]
        )

        # TODO trend summary
        todos = data.get("todo_trends", {}).get("repos", {})
        if todos:
            lines.append("")
            lines.append("[dim]TODOs:[/]")
            for repo, trend in list(todos.items())[:2]:
                if trend:
                    latest = trend[-1].get("count", 0)
                    lines.append(f"  {repo}: {latest}")

        content.update("\n".join(lines))


class MetricsPanel(Static):
    """Combined metrics panel for compact display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="metrics-summary")

    def refresh_data(self) -> None:
        content = self.query_one("#metrics-summary", Static)

        lines = []

        # Costs summary
        try:
            costs = CostTracker().collect()
            today_cost = costs.get("today", {}).get("cost", 0)
            total_cost = costs.get("summary", {}).get("total_cost", 0)
            lines.append(f"[bold]💰 Costs:[/] ${today_cost:.3f} today / ${total_cost:.2f} total")
        except Exception:
            lines.append("[dim]💰 Costs: unavailable[/]")

        # Performance summary
        try:
            perf = PerformanceMetrics().collect()
            summary = perf.get("summary", {})
            lines.append(
                f"[bold]⚡ Perf:[/] {summary.get('total_calls', 0)} calls, "
                f"{summary.get('avg_latency_ms', 0):.0f}ms avg, "
                f"{summary.get('error_rate_pct', 0):.1f}% errors"
            )
        except Exception:
            lines.append("[dim]⚡ Perf: unavailable[/]")

        # GitHub summary
        try:
            gh = GitHubMetrics().collect()
            streak = gh.get("streak", {}).get("streak_days", 0)
            cycle = gh.get("pr_metrics", {}).get("avg_cycle_hours", 0)
            streak_icon = "🔥" if streak > 0 else "❄️"
            lines.append(
                f"[bold]🐙 GitHub:[/] {streak}d streak {streak_icon}, {cycle:.1f}h PR cycle"
            )
        except Exception:
            lines.append("[dim]🐙 GitHub: unavailable[/]")

        content.update("\n".join(lines))
