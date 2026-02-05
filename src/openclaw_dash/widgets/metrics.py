"""Metrics panel widget for the TUI dashboard.

This module provides widgets for displaying various metrics including:
- Cost tracking and forecasting
- Performance metrics (latency, error rates)
- GitHub activity metrics (streaks, PR cycles)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors.billing import BillingCollector
from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    progress_bar,
    separator,
    sparkline,
    status_indicator,
)


def calculate_cost_forecast(
    daily_costs: list[dict[str, Any]], lookback_days: int = 7
) -> dict[str, Any]:
    """Calculate cost forecast based on recent spending patterns.

    Args:
        daily_costs: List of daily cost records with 'date' and 'cost' keys.
        lookback_days: Number of recent days to use for averaging.

    Returns:
        Dictionary with:
            - daily_avg: Average daily cost over the lookback period
            - projected_monthly: Projected cost for a 30-day month
            - trend: Trend indicator ('↑' increasing, '↓' decreasing, '→' stable)
            - trend_pct: Percentage change between periods
    """
    if not daily_costs:
        return {
            "daily_avg": 0.0,
            "projected_monthly": 0.0,
            "trend": "→",
            "trend_pct": 0.0,
        }

    # Sort by date descending and take recent days
    sorted_costs = sorted(daily_costs, key=lambda x: x.get("date", ""), reverse=True)

    # Get costs for recent period
    recent_costs = [d.get("cost", d.get("total_cost", 0)) for d in sorted_costs[:lookback_days]]

    # Get costs for prior period (for trend calculation)
    prior_costs = [
        d.get("cost", d.get("total_cost", 0))
        for d in sorted_costs[lookback_days : lookback_days * 2]
    ]

    # Calculate daily average from recent period
    daily_avg = sum(recent_costs) / len(recent_costs) if recent_costs else 0.0

    # Project to full month (30 days)
    projected_monthly = daily_avg * 30

    # Calculate trend by comparing recent vs prior period averages
    if prior_costs and recent_costs:
        prior_avg = sum(prior_costs) / len(prior_costs)
        if prior_avg > 0:
            trend_pct = ((daily_avg - prior_avg) / prior_avg) * 100
        else:
            trend_pct = 100.0 if daily_avg > 0 else 0.0
    else:
        trend_pct = 0.0

    # Determine trend indicator (5% threshold for stability)
    if trend_pct > 5:
        trend = "↑"
    elif trend_pct < -5:
        trend = "↓"
    else:
        trend = "→"

    return {
        "daily_avg": round(daily_avg, 4),
        "projected_monthly": round(projected_monthly, 2),
        "trend": trend,
        "trend_pct": round(trend_pct, 1),
    }


def get_days_in_current_month() -> int:
    """Get the number of days in the current month."""
    today = date.today()
    # Get first day of next month, then subtract one day
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    last_day = next_month.replace(day=1)
    return (last_day - today.replace(day=1)).days


class CostsPanel(Static):
    """Token costs display with API and estimated cost sources.

    Shows detailed cost information including:
    - Today's cost with source indicator (API or estimated)
    - Token counts (input/output)
    - API availability status
    - Cost forecast and projections
    - Cost breakdown by model
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying cost content.
        """
        yield Static("Loading...", id="costs-content")

    def refresh_data(self) -> None:
        """Refresh cost data from tracker and billing APIs."""
        tracker = CostTracker()
        data = tracker.collect()
        content = self.query_one("#costs-content", Static)

        today = data.get("today", {})
        summary = data.get("summary", {})
        daily_history = data.get("daily_costs", [])

        # If daily_costs not in data, try to get from tracker history
        if not daily_history:
            daily_history = tracker.get_history(days=14)

        # Try to fetch real billing data from APIs
        billing_collector = BillingCollector()
        billing_data = billing_collector.collect()
        has_api_data = billing_data.get("has_api_data", False)
        api_cost = billing_data.get("total_api_cost", 0.0)

        # Build sparkline from daily history if available
        cost_values = (
            [d.get("cost", d.get("total_cost", 0)) for d in daily_history[-14:]]
            if daily_history
            else []
        )

        lines = []

        # Today's cost with sparkline and source indicator
        today_cost = today.get("cost", 0)

        # Determine display cost and source
        if has_api_data and api_cost > 0:
            display_cost = api_cost
            source_indicator = "[green]API[/]"
        else:
            display_cost = today_cost
            source_indicator = "[yellow]Est[/]"

        if cost_values:
            spark = sparkline(cost_values, width=10)
            lines.append(
                f"[bold]{STATUS_SYMBOLS['diamond']} Today:[/] ${display_cost:.4f} "
                f"{source_indicator}  {spark}"
            )
        else:
            lines.append(
                f"[bold]{STATUS_SYMBOLS['diamond']} Today:[/] ${display_cost:.4f} {source_indicator}"
            )

        lines.append(
            f"  {STATUS_SYMBOLS['arrow_right']} Input: {today.get('input_tokens', 0):,} tokens"
        )
        lines.append(
            f"  {STATUS_SYMBOLS['arrow_right']} Output: {today.get('output_tokens', 0):,} tokens"
        )

        # Show API availability status
        api_status = billing_data.get("api_available", {})
        api_indicators = []
        if api_status.get("openai"):
            api_indicators.append("[green]OpenAI✓[/]")
        else:
            api_indicators.append("[dim]OpenAI[/]")
        # Anthropic never has API (no billing endpoint)
        api_indicators.append("[dim]Anthropic[/]")
        lines.append(f"  [dim]APIs:[/] {' '.join(api_indicators)}")

        lines.append(separator(30, style="dotted"))

        # Cost Forecast section with source-aware data
        forecast = calculate_cost_forecast(daily_history)
        forecast_source = "[green]API[/]" if has_api_data else "[yellow]Est[/]"
        lines.append(f"[bold] Forecast:[/] {forecast_source}")
        lines.append(f"  Proj/Mo: ${forecast['projected_monthly']:.2f} {forecast['trend']}")
        lines.append(f"  Avg/Day: ${forecast['daily_avg']:.2f}")

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
    """Performance metrics display.

    Shows system performance metrics including:
    - Total API call counts
    - Error rate with visual bar
    - Average latency with sparkline history
    - Slowest actions breakdown
    - Error-prone operations
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying performance content.
        """
        yield Static("Loading...", id="perf-content")

    def refresh_data(self) -> None:
        """Refresh performance metrics from collector."""
        perf = PerformanceMetrics()
        data = perf.collect()
        content = self.query_one("#perf-content", Static)

        summary = data.get("summary", {})
        latency_history = data.get("latency_history", [])

        # Build sparkline from latency history
        latency_values = (
            [d.get("avg_ms", 0) for d in latency_history[-12:]] if latency_history else []
        )

        lines = []

        # Calls with count indicator
        total_calls = summary.get("total_calls", 0)
        lines.append(f"{status_indicator('running', color=True)} [bold]Calls:[/] {total_calls:,}")

        # Error rate with visual bar
        error_rate = summary.get("error_rate_pct", 0)
        error_status = "ok" if error_rate < 5 else "warning" if error_rate < 15 else "error"
        error_bar = progress_bar(error_rate / 100, width=10, show_percent=False, style="block")
        lines.append(
            f"{status_indicator(error_status)} [bold]Errors:[/] {summary.get('total_errors', 0)} "
            f"({error_rate:.1f}%) {error_bar}"
        )

        # Latency with sparkline
        avg_latency = summary.get("avg_latency_ms", 0)
        if latency_values:
            spark = sparkline(latency_values, width=10)
            lines.append(
                f"{STATUS_SYMBOLS['lightning']} [bold]Latency:[/] {avg_latency:.0f}ms  {spark}"
            )
        else:
            lines.append(f"{STATUS_SYMBOLS['lightning']} [bold]Latency:[/] {avg_latency:.0f}ms")

        # Slowest actions
        slowest = data.get("slowest", [])[:3]
        if slowest:
            lines.append("")
            lines.append(separator(30, style="thin", label="Slowest"))
            max_latency = max(s.get("avg_ms", 1) for s in slowest)
            for item in slowest:
                ratio = item["avg_ms"] / max_latency if max_latency > 0 else 0
                bar = mini_bar(ratio, width=6)
                lines.append(f"  {bar} {item['name'][:15]}: {item['avg_ms']:.0f}ms")

        # Error-prone
        errors = data.get("error_prone", [])[:2]
        if errors:
            lines.append("")
            lines.append(separator(30, style="thin", label="Error Prone"))
            for item in errors:
                lines.append(
                    f"  {status_indicator('warning')} {item['name'][:15]}: {item['error_rate']:.1f}%"
                )

        content.update("\n".join(lines))


class GitHubPanel(Static):
    """GitHub metrics display.

    Shows GitHub activity metrics including:
    - Commit streak with fire emoji indicators
    - Commit activity sparkline
    - PR cycle time statistics
    - TODO trend tracking per repository
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying GitHub content.
        """
        yield Static("Loading...", id="github-content")

    def refresh_data(self) -> None:
        """Refresh GitHub metrics from collector."""
        gh = GitHubMetrics()
        data = gh.collect()
        content = self.query_one("#github-content", Static)

        streak = data.get("streak", {})
        pr = data.get("pr_metrics", {})
        commit_history = data.get("commit_history", [])

        # Streak display with fire emoji based on length
        streak_days = streak.get("streak_days", 0)
        if streak_days >= 30:
            streak_icon = (
                f"{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}"
            )
        elif streak_days >= 7:
            streak_icon = f"{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}"
        elif streak_days > 0:
            streak_icon = STATUS_SYMBOLS["fire"]
        else:
            streak_icon = STATUS_SYMBOLS["snowflake"]

        lines = []

        # Streak with sparkline of commit activity
        commit_counts = (
            [d.get("commits", 0) for d in commit_history[-14:]] if commit_history else []
        )
        if commit_counts:
            spark = sparkline(commit_counts, width=14)
            lines.append(
                f"[bold]{STATUS_SYMBOLS['star']} Streak:[/] {streak_days} days {streak_icon}"
            )
            lines.append(f"  {spark}")
        else:
            lines.append(
                f"[bold]{STATUS_SYMBOLS['star']} Streak:[/] {streak_days} days {streak_icon}"
            )

        if streak.get("username"):
            lines.append(f"  [dim]@{streak['username']}[/]")

        lines.append(separator(30, style="dotted"))

        # PR metrics with visual representation
        avg_cycle = pr.get("avg_cycle_hours", 0)
        fastest = pr.get("fastest_merge_hours", 0) or 0
        slowest = pr.get("slowest_merge_hours", 0) or 0

        lines.append(f"[bold]{STATUS_SYMBOLS['circle_full']} PR Cycle:[/] {avg_cycle:.1f}h avg")

        # Visual bar showing PR cycle range
        if slowest > 0:
            fast_ratio = fastest / slowest
            avg_cycle / slowest
            lines.append(
                f"  {STATUS_SYMBOLS['triangle_right']} Fastest: {fastest:.1f}h {mini_bar(fast_ratio, 6)}"
            )
            lines.append(
                f"  {STATUS_SYMBOLS['triangle_left']} Slowest: {slowest:.1f}h {mini_bar(1.0, 6)}"
            )
        else:
            lines.append(f"  {STATUS_SYMBOLS['arrow_right']} Fastest: {fastest:.1f}h")
            lines.append(f"  {STATUS_SYMBOLS['arrow_right']} Slowest: {slowest:.1f}h")

        # TODO trend summary with sparklines
        todos = data.get("todo_trends", {}).get("repos", {})
        if todos:
            lines.append("")
            lines.append(separator(30, style="thin", label="TODOs"))
            for repo, trend in list(todos.items())[:2]:
                if trend:
                    counts = [t.get("count", 0) for t in trend[-8:]]
                    latest = counts[-1] if counts else 0
                    spark = sparkline(counts, width=8) if len(counts) > 1 else ""
                    lines.append(f"  {STATUS_SYMBOLS['bullet']} {repo}: {latest} {spark}")

        content.update("\n".join(lines))


class MetricsPanel(Static):
    """Combined metrics panel for compact display.

    Provides a unified view of all key metrics (costs, performance, GitHub)
    in a compact format suitable for the main dashboard.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying the metrics summary.
        """
        yield Static("", id="metrics-summary")

    def refresh_data(self) -> None:
        """Refresh all metrics and update the combined display."""
        content = self.query_one("#metrics-summary", Static)

        lines = []

        # Costs summary with sparkline, forecast, and source indicator
        try:
            tracker = CostTracker()
            costs = tracker.collect()
            today_cost = costs.get("today", {}).get("cost", 0)
            daily_history = costs.get("daily_costs", [])
            if not daily_history:
                daily_history = tracker.get_history(days=14)
            cost_values = (
                [d.get("cost", d.get("total_cost", 0)) for d in daily_history[-10:]]
                if daily_history
                else []
            )

            # Try to fetch real billing data from APIs
            billing_collector = BillingCollector()
            billing_data = billing_collector.collect()
            has_api_data = billing_data.get("has_api_data", False)
            api_cost = billing_data.get("total_api_cost", 0.0)

            # Use API cost if available, otherwise estimated
            if has_api_data and api_cost > 0:
                display_cost = api_cost
                source_indicator = "[green]API[/]"
            else:
                display_cost = today_cost
                source_indicator = "[yellow]Est[/]"

            # Calculate forecast
            forecast = calculate_cost_forecast(daily_history)

            cost_line = f"[bold] Costs:[/] ${display_cost:.2f} {source_indicator}"
            if cost_values:
                cost_line += f"  {sparkline(cost_values, width=10)}"
            lines.append(cost_line)
            lines.append(f"  Proj/Mo: ${forecast['projected_monthly']:.2f} {forecast['trend']}")
        except Exception:
            lines.append(f"[dim]{STATUS_SYMBOLS['diamond']} Costs: unavailable[/]")

        lines.append(separator(50, style="dotted"))

        # Performance summary with error bar
        try:
            perf = PerformanceMetrics().collect()
            summary = perf.get("summary", {})
            error_rate = summary.get("error_rate_pct", 0)
            error_bar = progress_bar(error_rate / 100, width=8, show_percent=False, style="block")

            latency_history = perf.get("latency_history", [])
            latency_values = (
                [d.get("avg_ms", 0) for d in latency_history[-8:]] if latency_history else []
            )

            perf_line = (
                f"[bold]{STATUS_SYMBOLS['lightning']} Perf:[/] {summary.get('total_calls', 0)} calls, "
                f"{summary.get('avg_latency_ms', 0):.0f}ms avg"
            )
            if latency_values:
                perf_line += f" {sparkline(latency_values, width=8)}"
            perf_line += f", {error_rate:.1f}% err {error_bar}"
            lines.append(perf_line)
        except Exception:
            lines.append(f"[dim]{STATUS_SYMBOLS['lightning']} Perf: unavailable[/]")

        lines.append(separator(50, style="dotted"))

        # GitHub summary with streak visualization
        try:
            gh = GitHubMetrics().collect()
            streak = gh.get("streak", {}).get("streak_days", 0)
            cycle = gh.get("pr_metrics", {}).get("avg_cycle_hours", 0)
            streak_icon = STATUS_SYMBOLS["fire"] if streak > 0 else STATUS_SYMBOLS["snowflake"]

            commit_history = gh.get("commit_history", [])
            commit_values = (
                [d.get("commits", 0) for d in commit_history[-10:]] if commit_history else []
            )

            gh_line = f"[bold]{STATUS_SYMBOLS['star']} GitHub:[/] {streak}d streak {streak_icon}, {cycle:.1f}h PR cycle"
            if commit_values:
                gh_line += f"  {sparkline(commit_values, width=10)}"
            lines.append(gh_line)
        except Exception:
            lines.append(f"[dim]{STATUS_SYMBOLS['star']} GitHub: unavailable[/]")

        content.update("\n".join(lines))
