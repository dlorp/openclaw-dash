"""Metrics panel widget for the TUI dashboard."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    format_with_trend,
    mini_bar,
    progress_bar,
    separator,
    sparkline,
    status_indicator,
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

        lines.append(f"  {STATUS_SYMBOLS['arrow_right']} Input: {today.get('input_tokens', 0):,} tokens")
        lines.append(f"  {STATUS_SYMBOLS['arrow_right']} Output: {today.get('output_tokens', 0):,} tokens")

        lines.append(separator(30, style="dotted"))

        lines.append(f"[bold]{STATUS_SYMBOLS['star']} All time:[/] ${summary.get('total_cost', 0):.2f}")
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
        latency_history = data.get("latency_history", [])

        # Build sparkline from latency history
        latency_values = [d.get("avg_ms", 0) for d in latency_history[-12:]] if latency_history else []

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
            lines.append(f"{STATUS_SYMBOLS['lightning']} [bold]Latency:[/] {avg_latency:.0f}ms  {spark}")
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
    """GitHub metrics display."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="github-content")

    def refresh_data(self) -> None:
        gh = GitHubMetrics()
        data = gh.collect()
        content = self.query_one("#github-content", Static)

        streak = data.get("streak", {})
        pr = data.get("pr_metrics", {})
        commit_history = data.get("commit_history", [])

        # Streak display with fire emoji based on length
        streak_days = streak.get("streak_days", 0)
        if streak_days >= 30:
            streak_icon = f"{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}"
        elif streak_days >= 7:
            streak_icon = f"{STATUS_SYMBOLS['fire']}{STATUS_SYMBOLS['fire']}"
        elif streak_days > 0:
            streak_icon = STATUS_SYMBOLS["fire"]
        else:
            streak_icon = STATUS_SYMBOLS["snowflake"]

        lines = []

        # Streak with sparkline of commit activity
        commit_counts = [d.get("commits", 0) for d in commit_history[-14:]] if commit_history else []
        if commit_counts:
            spark = sparkline(commit_counts, width=14)
            lines.append(f"[bold]{STATUS_SYMBOLS['star']} Streak:[/] {streak_days} days {streak_icon}")
            lines.append(f"  {spark}")
        else:
            lines.append(f"[bold]{STATUS_SYMBOLS['star']} Streak:[/] {streak_days} days {streak_icon}")

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
            avg_ratio = avg_cycle / slowest
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
    """Combined metrics panel for compact display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="metrics-summary")

    def refresh_data(self) -> None:
        content = self.query_one("#metrics-summary", Static)

        lines = []

        # Costs summary with sparkline
        try:
            costs = CostTracker().collect()
            today_cost = costs.get("today", {}).get("cost", 0)
            total_cost = costs.get("summary", {}).get("total_cost", 0)
            daily_history = costs.get("daily_costs", [])
            cost_values = [d.get("cost", 0) for d in daily_history[-10:]] if daily_history else []

            cost_line = f"[bold]{STATUS_SYMBOLS['diamond']} Costs:[/] ${today_cost:.3f} today / ${total_cost:.2f} total"
            if cost_values:
                cost_line += f"  {sparkline(cost_values, width=10)}"
            lines.append(cost_line)
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
            latency_values = [d.get("avg_ms", 0) for d in latency_history[-8:]] if latency_history else []

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
            commit_values = [d.get("commits", 0) for d in commit_history[-10:]] if commit_history else []

            gh_line = f"[bold]{STATUS_SYMBOLS['star']} GitHub:[/] {streak}d streak {streak_icon}, {cycle:.1f}h PR cycle"
            if commit_values:
                gh_line += f"  {sparkline(commit_values, width=10)}"
            lines.append(gh_line)
        except Exception:
            lines.append(f"[dim]{STATUS_SYMBOLS['star']} GitHub: unavailable[/]")

        content.update("\n".join(lines))
