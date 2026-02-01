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

    args = parser.parse_args()

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
