"""CLI entry point."""

import argparse
import json
import sys
from typing import Any


def get_status() -> dict[str, Any]:
    """Collect current status from all sources."""
    from openclaw_dash.collectors import activity, cron, gateway, repos, sessions

    return {
        "gateway": gateway.collect(),
        "sessions": sessions.collect(),
        "cron": cron.collect(),
        "repos": repos.collect(),
        "activity": activity.collect(),
    }


def get_metrics() -> dict[str, Any]:
    """Collect all metrics."""
    from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics

    return {
        "costs": CostTracker().collect(),
        "performance": PerformanceMetrics().collect(),
        "github": GitHubMetrics().collect(),
    }


def print_metrics_text(metrics: dict[str, Any]) -> None:
    """Print metrics in human-readable format."""
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Costs panel
    costs = metrics.get("costs", {})
    today = costs.get("today", {})
    summary = costs.get("summary", {})

    if costs:
        costs_text = (
            f"[bold cyan]Today:[/] ${today.get('cost', 0):.4f}\n"
            f"  Input: {today.get('input_tokens', 0):,} tokens\n"
            f"  Output: {today.get('output_tokens', 0):,} tokens\n\n"
            f"[bold cyan]All time:[/] ${summary.get('total_cost', 0):.2f}\n"
            f"  Avg daily: ${summary.get('avg_daily_cost', 0):.2f}\n"
            f"  Days tracked: {summary.get('days_tracked', 0)}"
        )
        console.print(Panel(costs_text, title="💰 Token Costs", box=box.ROUNDED))

    # Performance panel
    perf = metrics.get("performance", {}).get("summary", {})
    if perf:
        perf_text = (
            f"[bold cyan]Total calls:[/] {perf.get('total_calls', 0):,}\n"
            f"[bold cyan]Errors:[/] {perf.get('total_errors', 0)} ({perf.get('error_rate_pct', 0):.1f}%)\n"
            f"[bold cyan]Avg latency:[/] {perf.get('avg_latency_ms', 0):.0f}ms"
        )
        console.print(Panel(perf_text, title="⚡ Performance", box=box.ROUNDED))

    # GitHub panel
    gh = metrics.get("github", {})
    if gh:
        streak = gh.get("streak", {})
        pr = gh.get("pr_metrics", {})

        streak_days = streak.get("streak_days", 0)
        streak_icon = "🔥" if streak_days > 0 else "❄️"

        gh_text = (
            f"[bold cyan]Contribution streak:[/] {streak_days} days {streak_icon}\n"
            f"[bold cyan]PR cycle time:[/] {pr.get('avg_cycle_hours', 0):.1f}h avg\n"
            f"  Fastest: {pr.get('fastest_merge_hours') or 0:.1f}h\n"
            f"  Slowest: {pr.get('slowest_merge_hours') or 0:.1f}h"
        )
        console.print(Panel(gh_text, title="🐙 GitHub", box=box.ROUNDED))

    # Cost trend table
    trend = costs.get("trend", {})
    if trend.get("dates"):
        table = Table(title="Cost Trend (last 7 days)", box=box.SIMPLE)
        table.add_column("Date")
        table.add_column("Cost", justify="right")
        for d, c in zip(trend["dates"], trend["costs"]):
            table.add_row(d, f"${c:.4f}")
        console.print(table)


def print_status_text(status: dict[str, Any]) -> None:
    """Print status in human-readable format."""
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Gateway
    gw = status["gateway"]
    gw_icon = "✓" if gw.get("healthy") else "✗"
    gw_color = "green" if gw.get("healthy") else "red"
    console.print(
        Panel(
            f"[{gw_color}]{gw_icon} {'ONLINE' if gw.get('healthy') else 'OFFLINE'}[/]\n"
            f"Context: {gw.get('context_pct', '?')}%\n"
            f"Uptime: {gw.get('uptime', 'unknown')}",
            title="Gateway",
            box=box.ROUNDED,
        )
    )

    # Current task / activity
    act = status.get("activity", {})
    if act.get("current_task"):
        console.print(
            Panel(
                f"[bold]{act['current_task']}[/]",
                title="Current Task",
                box=box.ROUNDED,
            )
        )

    # Recent activity
    if act.get("recent"):
        console.print("\n[bold]Recent Activity:[/]")
        for item in act["recent"][:5]:
            console.print(f"  ▸ {item.get('time', '?')} {item.get('action', '?')}")

    # Repos
    repos_data = status["repos"]
    if repos_data.get("repos"):
        table = Table(title="Repositories", box=box.SIMPLE)
        table.add_column("Repo")
        table.add_column("Health")
        table.add_column("PRs")
        for r in repos_data["repos"]:
            table.add_row(r.get("name", "?"), r.get("health", "?"), str(r.get("open_prs", 0)))
        console.print(table)


def run_tui() -> None:
    """Launch the TUI dashboard."""
    from openclaw_dash.app import DashboardApp

    app = DashboardApp()
    app.run()


def cmd_auto(args: argparse.Namespace) -> int:
    """Handle auto subcommands."""
    if args.auto_command == "merge":
        return cmd_auto_merge(args)
    elif args.auto_command == "cleanup":
        return cmd_auto_cleanup(args)
    elif args.auto_command == "deps":
        return cmd_auto_deps(args)
    elif args.auto_command == "backup":
        return cmd_auto_backup(args)
    else:
        print("Usage: openclaw-dash auto {merge|cleanup|deps|backup}")
        return 1


def cmd_auto_merge(args: argparse.Namespace) -> int:
    """Auto-merge approved PRs."""
    from pathlib import Path

    from openclaw_dash.automation.pr_auto import PRAutoMerger, format_merge_results

    repos = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
    if args.repo:
        repos = [args.repo]

    all_results = []
    for repo in repos:
        repo_path = Path.home() / "repos" / repo
        if not repo_path.exists():
            continue
        merger = PRAutoMerger(repo_path, dry_run=args.dry_run)
        results = merger.process_prs()
        all_results.extend(results)

    print(format_merge_results(all_results))
    return 0


def cmd_auto_cleanup(args: argparse.Namespace) -> int:
    """Clean up stale branches."""
    from pathlib import Path

    from openclaw_dash.automation.pr_auto import BranchCleaner, format_cleanup_results

    repos = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
    if args.repo:
        repos = [args.repo]

    all_results = []
    for repo in repos:
        repo_path = Path.home() / "repos" / repo
        if not repo_path.exists():
            continue
        cleaner = BranchCleaner(repo_path, dry_run=args.dry_run)
        results = cleaner.cleanup_branches()
        all_results.extend(results)

    print(format_cleanup_results(all_results))
    return 0


def cmd_auto_deps(args: argparse.Namespace) -> int:
    """Run dependency updates."""
    from openclaw_dash.automation.deps_auto import DependencyUpdater, format_update_results

    updater = DependencyUpdater(dry_run=args.dry_run)
    results = updater.run_updates()
    print(format_update_results(results))
    return 0


def cmd_auto_backup(args: argparse.Namespace) -> int:
    """Verify backup status."""
    import json

    from openclaw_dash.automation.backup import BackupVerifier, format_backup_report

    verifier = BackupVerifier()
    report = verifier.verify()

    if hasattr(args, "backup_json") and args.backup_json:
        print(json.dumps(report.__dict__, indent=2, default=str))
    else:
        print(format_backup_report(report))
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="openclaw-dash",
        description="At-a-glance dashboard for lorp's systems",
    )
    parser.add_argument("--status", action="store_true", help="Quick text status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__import__('openclaw_dash').__version__}"
    )

    # Subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Metrics subcommand
    metrics_parser = subparsers.add_parser(
        "metrics", help="Show metrics (costs, performance, github)"
    )
    metrics_parser.add_argument(
        "--json", dest="metrics_json", action="store_true", help="JSON output"
    )
    metrics_parser.add_argument("--costs", action="store_true", help="Show only costs")
    metrics_parser.add_argument("--performance", action="store_true", help="Show only performance")
    metrics_parser.add_argument("--github", action="store_true", help="Show only GitHub metrics")

    # Auto subcommand
    auto_parser = subparsers.add_parser("auto", help="Automation commands")
    auto_subparsers = auto_parser.add_subparsers(dest="auto_command", help="Auto commands")

    # auto merge
    merge_parser = auto_subparsers.add_parser("merge", help="Auto-merge approved PRs")
    merge_parser.add_argument("--dry-run", action="store_true", help="Preview without merging")
    merge_parser.add_argument("--repo", help="Specific repo to process")

    # auto cleanup
    cleanup_parser = auto_subparsers.add_parser("cleanup", help="Clean up stale branches")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    cleanup_parser.add_argument("--repo", help="Specific repo to process")

    # auto deps
    deps_parser = auto_subparsers.add_parser("deps", help="Run dependency updates")
    deps_parser.add_argument("--dry-run", action="store_true", help="Preview without creating PRs")

    # auto backup
    backup_parser = auto_subparsers.add_parser("backup", help="Verify backup status")
    backup_parser.add_argument(
        "--json", dest="backup_json", action="store_true", help="JSON output"
    )

    args = parser.parse_args()

    # Handle auto command
    if args.command == "auto":
        return cmd_auto(args)

    # Handle metrics command
    if args.command == "metrics":
        metrics = get_metrics()

        # Filter if specific metric requested
        if args.costs or args.performance or args.github:
            filtered = {}
            if args.costs:
                filtered["costs"] = metrics["costs"]
            if args.performance:
                filtered["performance"] = metrics["performance"]
            if args.github:
                filtered["github"] = metrics["github"]
            metrics = filtered

        if args.metrics_json:
            print(json.dumps(metrics, indent=2, default=str))
        else:
            print_metrics_text(metrics)
        return 0

    if args.status or args.json:
        status = get_status()
        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            print_status_text(status)
        return 0

    run_tui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
