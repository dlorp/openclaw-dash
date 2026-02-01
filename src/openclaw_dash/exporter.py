"""Export dashboard state to file."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def collect_all_data() -> dict[str, Any]:
    """Collect all dashboard data for export."""
    from openclaw_dash.collectors import activity, alerts, channels, cron, gateway, repos, sessions
    from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics

    return {
        "timestamp": datetime.now().isoformat(),
        "gateway": gateway.collect(),
        "sessions": sessions.collect(),
        "cron": cron.collect(),
        "repos": repos.collect(),
        "activity": activity.collect(),
        "channels": channels.collect(),
        "alerts": alerts.collect(),
        "metrics": {
            "costs": CostTracker().collect(),
            "performance": PerformanceMetrics().collect(),
            "github": GitHubMetrics().collect(),
        },
    }


def export_json(data: dict[str, Any]) -> str:
    """Export data as JSON string."""
    return json.dumps(data, indent=2, default=str)


def export_markdown(data: dict[str, Any]) -> str:
    """Export data as Markdown document."""
    lines = [
        "# OpenClaw Dashboard Export",
        "",
        f"**Generated:** {data.get('timestamp', 'unknown')}",
        "",
    ]

    # Gateway Status
    gw = data.get("gateway", {})
    status = "✅ ONLINE" if gw.get("healthy") else "❌ OFFLINE"
    lines.extend([
        "## Gateway Status",
        "",
        f"- **Status:** {status}",
        f"- **Uptime:** {gw.get('uptime', 'unknown')}",
        f"- **Context Usage:** {gw.get('context_pct', 0):.1f}%",
        f"- **Version:** {gw.get('version', 'unknown')}",
        "",
    ])

    # Sessions
    sessions_data = data.get("sessions", {})
    active = sessions_data.get("active", [])
    lines.extend([
        "## Active Sessions",
        "",
        f"**Total:** {len(active)}",
        "",
    ])
    if active:
        lines.append("| Channel | Model | Duration |")
        lines.append("|---------|-------|----------|")
        for s in active:
            lines.append(
                f"| {s.get('channel', '?')} | {s.get('model', '?')} | {s.get('duration', '?')} |"
            )
        lines.append("")

    # Cron Jobs
    cron_data = data.get("cron", {})
    jobs = cron_data.get("jobs", [])
    lines.extend([
        "## Cron Jobs",
        "",
        f"**Total:** {len(jobs)}",
        "",
    ])
    if jobs:
        lines.append("| Label | Schedule | Next Run |")
        lines.append("|-------|----------|----------|")
        for j in jobs:
            lines.append(
                f"| {j.get('label', '?')} | {j.get('schedule', '?')} | {j.get('next_run', '?')} |"
            )
        lines.append("")

    # Repos
    repos_data = data.get("repos", {})
    repos_list = repos_data.get("repos", [])
    lines.extend([
        "## Repositories",
        "",
    ])
    if repos_list:
        lines.append("| Repo | Branch | Open PRs | Health |")
        lines.append("|------|--------|----------|--------|")
        for r in repos_list:
            lines.append(
                f"| {r.get('name', '?')} | {r.get('branch', '?')} | {r.get('open_prs', 0)} | {r.get('health', '?')} |"
            )
        lines.append("")

    # Activity
    activity_data = data.get("activity", {})
    current = activity_data.get("current_task")
    recent = activity_data.get("recent", [])
    lines.extend([
        "## Activity",
        "",
    ])
    if current:
        lines.append(f"**Current Task:** {current}")
        lines.append("")
    if recent:
        lines.append("### Recent Activity")
        lines.append("")
        for item in recent[:10]:
            lines.append(f"- `{item.get('time', '?')}` {item.get('action', '?')}")
        lines.append("")

    # Alerts
    alerts_data = data.get("alerts", {})
    alert_list = alerts_data.get("alerts", [])
    if alert_list:
        lines.extend([
            "## Alerts",
            "",
        ])
        for a in alert_list:
            severity = a.get("severity", "info").upper()
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(a.get("severity"), "⚪")
            lines.append(f"- {icon} **{severity}:** {a.get('message', '?')}")
        lines.append("")

    # Metrics
    metrics = data.get("metrics", {})

    # Costs
    costs = metrics.get("costs", {})
    today = costs.get("today", {})
    summary = costs.get("summary", {})
    lines.extend([
        "## Metrics",
        "",
        "### Token Costs",
        "",
        f"- **Today:** ${today.get('cost', 0):.4f}",
        f"  - Input: {today.get('input_tokens', 0):,} tokens",
        f"  - Output: {today.get('output_tokens', 0):,} tokens",
        f"- **All Time:** ${summary.get('total_cost', 0):.2f}",
        f"- **Avg Daily:** ${summary.get('avg_daily_cost', 0):.2f}",
        "",
    ])

    # Performance
    perf = metrics.get("performance", {}).get("summary", {})
    lines.extend([
        "### Performance",
        "",
        f"- **Total Calls:** {perf.get('total_calls', 0):,}",
        f"- **Errors:** {perf.get('total_errors', 0)} ({perf.get('error_rate_pct', 0):.1f}%)",
        f"- **Avg Latency:** {perf.get('avg_latency_ms', 0):.0f}ms",
        "",
    ])

    # GitHub
    gh = metrics.get("github", {})
    streak = gh.get("streak", {})
    pr = gh.get("pr_metrics", {})
    streak_days = streak.get("streak_days", 0)
    lines.extend([
        "### GitHub",
        "",
        f"- **Contribution Streak:** {streak_days} days {'🔥' if streak_days > 0 else '❄️'}",
        f"- **Avg PR Cycle Time:** {pr.get('avg_cycle_hours', 0):.1f}h",
        "",
    ])

    # Channels
    channels_data = data.get("channels", {})
    channel_list = channels_data.get("channels", [])
    if channel_list:
        lines.extend([
            "## Channels",
            "",
        ])
        for c in channel_list:
            status_icon = "✅" if c.get("connected") else "❌"
            lines.append(f"- {status_icon} **{c.get('name', '?')}** ({c.get('type', '?')})")
        lines.append("")

    lines.append("---")
    lines.append("*Exported by openclaw-dash*")

    return "\n".join(lines)


def export_to_file(
    output_path: Path | str | None = None,
    format: str = "json",
) -> tuple[str, str]:
    """
    Export dashboard data to file.

    Args:
        output_path: Path to write to. If None, generates based on timestamp.
        format: Output format ('json' or 'md')

    Returns:
        Tuple of (filepath, content)
    """
    data = collect_all_data()

    if format == "md":
        content = export_markdown(data)
        ext = ".md"
    else:
        content = export_json(data)
        ext = ".json"

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = Path(f"openclaw-export-{timestamp}{ext}")
    else:
        output_path = Path(output_path)

    output_path.write_text(content)
    return str(output_path), content
