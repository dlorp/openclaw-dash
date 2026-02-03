"""CLI entry point."""

import argparse
import json
import sys
from typing import Any


def get_status() -> dict[str, Any]:
    """Collect current status from all sources.

    In offline mode, gateway-dependent collectors return placeholder data
    with helpful offline alternative suggestions.
    """
    from openclaw_dash.collectors import activity, cron, gateway, repos, sessions
    from openclaw_dash.offline import format_gateway_error_short, is_offline_mode

    if is_offline_mode():
        offline_hint = format_gateway_error_short()
        return {
            "gateway": {
                "healthy": False,
                "error": "Offline mode enabled",
                "_offline_hint": offline_hint,
            },
            "sessions": {
                "sessions": [],
                "total": 0,
                "_offline_hint": offline_hint,
            },
            "cron": cron.collect(),  # Cron may work partially offline
            "repos": repos.collect(),  # Repos work offline (local git)
            "activity": {
                "recent": [],
                "_offline_hint": offline_hint,
            },
        }

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
    """Print metrics in human-readable format.

    Args:
        metrics: Dictionary containing costs, performance, and github metrics.
    """
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Costs panel
    costs = metrics.get("costs", {})
    today = costs.get("today", {})
    summary = costs.get("summary", {})

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
    perf_text = (
        f"[bold cyan]Total calls:[/] {perf.get('total_calls', 0):,}\n"
        f"[bold cyan]Errors:[/] {perf.get('total_errors', 0)} ({perf.get('error_rate_pct', 0):.1f}%)\n"
        f"[bold cyan]Avg latency:[/] {perf.get('avg_latency_ms', 0):.0f}ms"
    )
    console.print(Panel(perf_text, title="⚡ Performance", box=box.ROUNDED))

    # GitHub panel
    gh = metrics.get("github", {})
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
        for date, cost in zip(trend["dates"], trend["costs"]):
            table.add_row(date, f"${cost:.4f}")
        console.print(table)


def print_status_text(status: dict[str, Any]) -> None:
    """Print status in human-readable format.

    Args:
        status: Dictionary containing gateway, sessions, repos, and activity data.
    """
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Gateway
    gw = status["gateway"]
    gw_icon = "✓" if gw.get("healthy") else "✗"
    gw_color = "green" if gw.get("healthy") else "red"

    gw_content = (
        f"[{gw_color}]{gw_icon} {'ONLINE' if gw.get('healthy') else 'OFFLINE'}[/]\n"
        f"Context: {gw.get('context_pct', '?')}%\n"
        f"Uptime: {gw.get('uptime', 'unknown')}"
    )

    # Add offline hint if present
    if gw.get("_offline_hint"):
        gw_content += f"\n\n[dim]{gw['_offline_hint']}[/]"

    console.print(
        Panel(
            gw_content,
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


def run_tui(refresh_interval: int | None = None) -> None:
    """Launch the TUI dashboard.

    Args:
        refresh_interval: Override refresh interval in seconds. If None, uses config default.
    """
    from openclaw_dash.app import DashboardApp

    app = DashboardApp(refresh_interval=refresh_interval)
    app.run()


def run_security_audit(deep: bool = False, fix: bool = False, json_output: bool = False) -> int:
    """Run security audit and optionally apply fixes."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from openclaw_dash.security import DependencyScanner, SecurityAudit, SecurityFixer

    console = Console()

    if not json_output:
        console.print("[bold]🔒 Running OpenClaw Security Audit...[/]\n")

    # Run config/secrets audit
    audit = SecurityAudit()
    audit_result = audit.run(deep=deep)

    # Run dependency scan
    scanner = DependencyScanner()
    dep_result = scanner.scan()

    if json_output:
        combined = {
            "audit": audit_result.to_dict(),
            "dependencies": dep_result.to_dict(),
        }
        if fix:
            fixer = SecurityFixer(dry_run=False)
            fix_result = fixer.fix_all(audit_result=audit_result, dep_result=dep_result)
            combined["fixes"] = fix_result.to_dict()
        print(json.dumps(combined, indent=2, default=str))
        return 1 if audit_result.critical_count > 0 else 0

    # Display audit results
    if audit_result.findings:
        table = Table(title="Security Findings", box=box.ROUNDED)
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Title")
        table.add_column("Path")

        severity_colors = {
            "critical": "red bold",
            "high": "red",
            "medium": "yellow",
            "low": "cyan",
            "info": "dim",
        }

        for f in sorted(
            audit_result.findings,
            key=lambda x: ["critical", "high", "medium", "low", "info"].index(x.severity),
        ):
            table.add_row(
                f"[{severity_colors.get(f.severity, '')}]{f.severity.upper()}[/]",
                f.category,
                f.title,
                f.path or "-",
            )

        console.print(table)
    else:
        console.print("[green]✓ No security issues found in configuration[/]")

    # Display dependency results
    if dep_result.vulnerabilities:
        console.print()
        table = Table(title="Vulnerable Dependencies", box=box.ROUNDED)
        table.add_column("Package")
        table.add_column("Version")
        table.add_column("Severity")
        table.add_column("Fix")
        table.add_column("ID")

        for v in sorted(
            dep_result.vulnerabilities,
            key=lambda x: ["critical", "high", "medium", "low"].index(x.severity),
        ):
            table.add_row(
                v.package,
                v.installed_version,
                v.severity.upper(),
                v.fix_version or "-",
                v.vulnerability_id[:30],
            )

        console.print(table)
    else:
        console.print("[green]✓ No vulnerable dependencies found[/]")

    if dep_result.errors:
        console.print(f"\n[dim]Scan notes: {', '.join(dep_result.errors)}[/]")

    # Apply fixes if requested
    if fix:
        console.print("\n[bold]🔧 Applying fixes...[/]\n")
        fixer = SecurityFixer(dry_run=False)
        fix_result = fixer.fix_all(audit_result=audit_result, dep_result=dep_result)

        for action in fix_result.actions:
            if action.action == "applied":
                console.print(f"[green]✓[/] {action.finding_title}: {action.description}")
            elif action.action == "suggested":
                console.print(f"[yellow]→[/] {action.finding_title}: {action.command}")
            elif action.action == "failed":
                console.print(f"[red]✗[/] {action.finding_title}: {action.error}")

        console.print(
            f"\n[bold]Summary:[/] {fix_result.applied_count} applied, {fix_result.suggested_count} suggested, {fix_result.failed_count} failed"
        )

    # Summary
    summary = audit_result.summary
    console.print(
        f"\n[bold]Audit Summary:[/] "
        f"[red]{summary['critical']} critical[/], "
        f"[red]{summary['high']} high[/], "
        f"[yellow]{summary['medium']} medium[/], "
        f"[cyan]{summary['low']} low[/]"
    )

    return 1 if audit_result.critical_count > 0 or audit_result.high_count > 0 else 0


def cmd_auto(args: argparse.Namespace) -> int:
    """Handle auto subcommands.

    Args:
        args: Parsed command-line arguments containing auto_command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
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
    """Auto-merge approved PRs.

    Args:
        args: Parsed arguments with dry_run and repo options.

    Returns:
        Exit code (0 for success).
    """
    from pathlib import Path

    from openclaw_dash.automation.pr_auto import (
        MergeConfig,
        PRAutomation,
        format_merge_results,
    )

    repos = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
    if args.repo:
        repos = [args.repo]

    config = MergeConfig(dry_run=args.dry_run)

    for repo in repos:
        repo_path = Path.home() / "repos" / repo
        if not repo_path.exists():
            continue
        automation = PRAutomation(repo_path)
        results = automation.auto_merge(config)
        print(format_merge_results(results, repo))

    return 0


def cmd_auto_cleanup(args: argparse.Namespace) -> int:
    """Clean up stale branches.

    Args:
        args: Parsed arguments with dry_run and repo options.

    Returns:
        Exit code (0 for success).
    """
    from pathlib import Path

    from openclaw_dash.automation.pr_auto import (
        CleanupConfig,
        PRAutomation,
        format_cleanup_results,
    )

    repos = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
    if args.repo:
        repos = [args.repo]

    config = CleanupConfig(dry_run=args.dry_run)

    for repo in repos:
        repo_path = Path.home() / "repos" / repo
        if not repo_path.exists():
            continue
        automation = PRAutomation(repo_path)
        results = automation.cleanup_branches(config)
        print(format_cleanup_results(results, repo))

    return 0


def cmd_auto_deps(args: argparse.Namespace) -> int:
    """Run dependency updates.

    Args:
        args: Parsed arguments with dry_run option.

    Returns:
        Exit code (0 for success).
    """
    from openclaw_dash.automation.deps_auto import (
        DepsAutomation,
        DepsConfig,
        format_deps_results,
    )

    config = DepsConfig(dry_run=args.dry_run)
    automation = DepsAutomation(config)
    results = automation.run_updates()
    print(format_deps_results(results))
    return 0


def cmd_auto_backup(args: argparse.Namespace) -> int:
    """Verify backup status.

    Args:
        args: Parsed arguments with backup_json option.

    Returns:
        Exit code (0 for success).
    """
    from openclaw_dash.automation.backup import BackupVerifier, format_backup_report

    verifier = BackupVerifier()
    report = verifier.verify()

    if hasattr(args, "backup_json") and args.backup_json:
        print(json.dumps(report.__dict__, indent=2, default=str))
    else:
        print(format_backup_report(report))
    return 0


def cmd_collectors(args: argparse.Namespace) -> int:
    """Show collector health and performance stats.

    Args:
        args: Parsed arguments with collectors_json, reset, warm options.

    Returns:
        Exit code (0 for success).
    """
    from openclaw_dash.collectors import (
        activity,
        cron,
        gateway,
        get_cache,
        repos,
        reset_cache,
        sessions,
    )

    cache = get_cache()

    # Handle reset
    if hasattr(args, "reset") and args.reset:
        reset_cache()
        print("Cache and circuit breakers reset.")
        return 0

    # Handle warm (run all collectors to populate cache)
    if hasattr(args, "warm") and args.warm:
        collectors = [
            ("gateway", gateway.collect),
            ("sessions", sessions.collect),
            ("cron", cron.collect),
            ("repos", repos.collect),
            ("activity", activity.collect),
        ]
        print("Warming cache...")
        for name, collect_fn in collectors:
            try:
                collect_fn()
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")
        print("Cache warmed.")
        return 0

    # Run collectors once to populate stats
    gateway.collect()
    sessions.collect()
    cron.collect()
    repos.collect()
    activity.collect()

    # Get stats
    all_stats = cache.get_all_stats()
    health = cache.get_health_summary()

    if hasattr(args, "collectors_json") and args.collectors_json:
        print(json.dumps({"health": health, "collectors": all_stats}, indent=2, default=str))
    else:
        print_collectors_text(health, all_stats)

    return 0


def print_collectors_text(health: dict[str, Any], stats: dict[str, Any]) -> None:
    """Print collector stats in human-readable format.

    Args:
        health: Health summary dictionary.
        stats: Per-collector statistics dictionary.
    """
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Health summary panel
    healthy = health.get("healthy_count", 0)
    degraded = health.get("degraded_count", 0)
    failed = health.get("failed_count", 0)

    status_icon = "✓" if failed == 0 else "⚠" if degraded > 0 else "✗"
    status_color = "green" if failed == 0 and degraded == 0 else "yellow" if failed == 0 else "red"

    health_text = (
        f"[{status_color}]{status_icon} Status:[/] "
        f"[green]{healthy}[/] healthy, "
        f"[yellow]{degraded}[/] degraded, "
        f"[red]{failed}[/] failed\n"
        f"[bold]Cache hit rate:[/] {health.get('avg_cache_hit_rate', 0):.1f}%\n"
        f"[bold]Slowest:[/] {health.get('slowest_collector', 'N/A')} "
        f"({health.get('slowest_time_ms', 0):.0f}ms)"
    )
    console.print(Panel(health_text, title="🔍 Collector Health", box=box.ROUNDED))

    # Detailed stats table
    if stats:
        table = Table(title="Collector Statistics", box=box.SIMPLE)
        table.add_column("Collector")
        table.add_column("Calls", justify="right")
        table.add_column("Cache %", justify="right")
        table.add_column("Avg (ms)", justify="right")
        table.add_column("Errors", justify="right")
        table.add_column("Status")

        for name, s in sorted(stats.items()):
            status = "✓" if not s.get("circuit_open") and s.get("error_count", 0) == 0 else "⚠"
            if s.get("circuit_open"):
                status = "[red]⛔[/]"
            elif s.get("error_count", 0) > 0:
                status = "[yellow]⚠[/]"
            else:
                status = "[green]✓[/]"

            table.add_row(
                name,
                str(s.get("call_count", 0)),
                f"{s.get('hit_rate_pct', 0):.0f}%",
                f"{s.get('avg_time_ms', 0):.1f}",
                str(s.get("error_count", 0)),
                status,
            )

        console.print(table)


def main() -> int:
    """Main entry point for openclaw-dash CLI.

    Parses command-line arguments and dispatches to appropriate handlers.
    Supports TUI mode, status queries, metrics, security audits, and automation.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        prog="openclaw-dash",
        description="TUI dashboard for OpenClaw gateway monitoring",
    )
    parser.add_argument("--status", action="store_true", help="Quick text status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch mode: auto-refresh every 5s instead of 30s",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__import__('openclaw_dash').__version__}"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with mock data (no gateway connection required)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run in offline mode (skip gateway-dependent features, show alternatives)",
    )

    # Subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Security subcommand
    security_parser = subparsers.add_parser("security", help="Run security audit")
    security_parser.add_argument(
        "--deep", action="store_true", help="Deep scan (includes workspace)"
    )
    security_parser.add_argument("--fix", action="store_true", help="Apply auto-fixes")
    security_parser.add_argument(
        "--json", dest="security_json", action="store_true", help="JSON output"
    )

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

    # Export subcommand
    export_parser = subparsers.add_parser("export", help="Export dashboard data to file")
    export_parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Output format (default: json)",
    )
    export_parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Output file path (default: auto-generated)",
    )

    # Collectors subcommand (timing/cache/health stats)
    collectors_parser = subparsers.add_parser(
        "collectors", help="Show collector health and performance stats"
    )
    collectors_parser.add_argument(
        "--json", dest="collectors_json", action="store_true", help="JSON output"
    )
    collectors_parser.add_argument(
        "--reset", action="store_true", help="Reset cache and circuit breakers"
    )
    collectors_parser.add_argument(
        "--warm", action="store_true", help="Warm the cache by running all collectors"
    )

    args = parser.parse_args()

    # Handle auto command
    if args.command == "auto":
        return cmd_auto(args)

    # Handle collectors command
    if args.command == "collectors":
        return cmd_collectors(args)

    # Handle export command
    if args.command == "export":
        from openclaw_dash.exporter import export_to_file

        filepath, _ = export_to_file(
            output_path=args.output,
            format=args.format,
        )
        print(f"Exported to: {filepath}")
        return 0

    # Handle security command
    if args.command == "security":
        return run_security_audit(
            deep=args.deep,
            fix=args.fix,
            json_output=args.security_json,
        )

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

    # Enable demo mode if requested
    if args.demo:
        from openclaw_dash.demo import enable_demo_mode

        enable_demo_mode()

    # Enable offline mode if requested
    if args.offline:
        from openclaw_dash.offline import enable_offline_mode

        enable_offline_mode()

    # Watch mode uses 5s refresh interval
    refresh_interval = 5 if args.watch else None
    run_tui(refresh_interval=refresh_interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
